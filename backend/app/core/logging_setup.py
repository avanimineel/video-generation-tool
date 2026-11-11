"""Resilient logging for EC2 / shell-redirected log files.

Classic failure mode on Amazon Linux EC2
----------------------------------------
Operators often start uvicorn with::

    python3 -m uvicorn ... >>/var/log/resolve-companion.log 2>&1

Uvicorn's access logger uses a StreamHandler on stderr. When that stream
hit EIO (dead tty residue, flaky sink, etc.), ``emit`` raises
``OSError: [Errno 5] Input/output error``. Python's default ``handleError``
then writes a huge ``--- Logging error ---`` traceback to **stderr** —
which is the *same* redirected file. ``tail -f /var/log/resolve-companion.log``
fills with access-log failure noise while HTTP still returns 200/206.

This module:
  * prefers a SafeRotatingFileHandler on LOG_FILE (default
    ``/var/log/resolve-companion.log`` when writable, else ``backend/logs/``)
  * SafeStreamHandler / SafeRotatingFileHandler swallow OSError/IOError on
    emit and override ``handleError`` so lastResort never floods the file
  * strips uvicorn's fragile StreamHandlers; access is either disabled
    (``--no-access-log``, recommended) or file-only via the safe FileHandler

Env:
  LOG_FILE              Rotatable app log path. Default: /var/log/resolve-companion.log
                        if writable, else backend/logs/companion.log.
                        Empty / "none" / "off" / "-" disables the file sink.
  LOG_TO_STDERR         If "1", also attach SafeStreamHandler to stderr
                        (off by default when a file sink is active — avoids
                        duplicating into a shell-redirected LOG_FILE).
  LOG_LEVEL             Default INFO
  LOG_FORMAT            json (default for structured events) | kv | printf pattern
  LOG_DATEFMT           Only used for classic printf LOG_FORMAT patterns
  LOG_FILE_MAX_BYTES / LOG_FILE_BACKUP_COUNT
  UVICORN_ACCESS_LOG    Consumed by start_companion.sh (1 = enable access log).

Structured events (via get_logger)::kwargs)::

    logger.info("media_upload_received", event="media_upload_received", media_id=..., filename=...)
"""
from __future__ import annotations

import errno
import json
import logging
import os
import sys
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

_CONFIGURED = False
_BROKEN_SINK_LOGGED = False
_ACTIVE_LOG_FILE: Optional[Path] = None

_VAR_LOG_FILE = Path("/var/log/resolve-companion.log")
_FALLBACK_LOG_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "companion.log"

_project_id: ContextVar[Optional[str]] = ContextVar("log_project_id", default=None)
_job_stage: ContextVar[Optional[str]] = ContextVar("log_job_stage", default=None)
_run_id: ContextVar[Optional[str]] = ContextVar("log_run_id", default=None)

_SECRET_MARKERS = ("API_KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL")
_MAX_FIELD = 500


def truncate(value: Any, limit: int = _MAX_FIELD) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def redact_secrets(text: str) -> str:
    out = text
    for key, value in os.environ.items():
        if any(m in key.upper() for m in _SECRET_MARKERS) and value and len(value) > 5:
            out = out.replace(value, "[REDACTED]")
    return out


def bind_context(
    *,
    project_id: Optional[str] = None,
    job_stage: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    tokens: Dict[str, Any] = {}
    if project_id is not None:
        tokens["project_id"] = _project_id.set(project_id)
    if job_stage is not None:
        tokens["job_stage"] = _job_stage.set(job_stage)
    if run_id is not None:
        tokens["run_id"] = _run_id.set(run_id)
    return tokens


def reset_context(tokens: Dict[str, Any]) -> None:
    if "project_id" in tokens:
        _project_id.reset(tokens["project_id"])
    if "job_stage" in tokens:
        _job_stage.reset(tokens["job_stage"])
    if "run_id" in tokens:
        _run_id.reset(tokens["run_id"])


@contextmanager
def log_context(
    *,
    project_id: Optional[str] = None,
    job_stage: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Iterator[None]:
    tokens = bind_context(project_id=project_id, job_stage=job_stage, run_id=run_id)
    try:
        yield
    finally:
        reset_context(tokens)


def current_context() -> Dict[str, str]:
    ctx: Dict[str, str] = {}
    pid = _project_id.get()
    stage = _job_stage.get()
    rid = _run_id.get()
    if pid:
        ctx["project_id"] = pid
    if stage:
        ctx["job_stage"] = stage
    if rid:
        ctx["run_id"] = rid
    return ctx


class StructuredFormatter(logging.Formatter):
    """One JSON object per line (CloudWatch / journald / LOG_FILE friendly)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": redact_secrets(record.getMessage()),
        }
        payload.update(current_context())
        extras = getattr(record, "structured", None)
        if isinstance(extras, dict):
            for key, value in extras.items():
                if key in payload:
                    continue
                if isinstance(value, (str, int, float, bool)) or value is None:
                    payload[key] = truncate(value) if isinstance(value, str) else value
                else:
                    payload[key] = truncate(value)
        if record.exc_info:
            payload["exc_type"] = (
                record.exc_info[0].__name__ if record.exc_info[0] else None
            )
            payload["traceback"] = redact_secrets(
                "".join(traceback.format_exception(*record.exc_info))
            )[:4000]
        return json.dumps(payload, ensure_ascii=False, default=str)


class KeyValueFormatter(logging.Formatter):
    """Compact key=value lines when LOG_FORMAT=kv."""

    def format(self, record: logging.LogRecord) -> str:
        parts = [
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            record.levelname,
            record.name,
            redact_secrets(record.getMessage()),
        ]
        for key, value in {
            **current_context(),
            **(getattr(record, "structured", None) or {}),
        }.items():
            parts.append(
                f"{key}={truncate(value)!r}" if isinstance(value, str) else f"{key}={value}"
            )
        if record.exc_info:
            parts.append(
                "traceback="
                + redact_secrets("".join(traceback.format_exception(*record.exc_info)))[:2000]
            )
        return " ".join(str(p) for p in parts)


class StructuredAdapter(logging.LoggerAdapter):
    """Logger that accepts kwargs as structured fields (not % formatting)."""

    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        structured = dict(extra.get("structured") or {})
        for key in list(kwargs.keys()):
            if key in ("exc_info", "stack_info", "stacklevel", "extra"):
                continue
            structured[key] = kwargs.pop(key)
        if structured:
            extra["structured"] = structured
        return msg, kwargs


def get_logger(name: str) -> StructuredAdapter:
    return StructuredAdapter(logging.getLogger(name), {})


class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that swallows broken-pipe / EIO emit failures without spam."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self.stream is None:
                return
            super().emit(record)
        except (OSError, IOError) as exc:
            self._disable_broken_stream(exc)
        except Exception:
            # Never fall through to Handler.handleError → stderr flood.
            return

    def handleError(self, record: logging.LogRecord) -> None:
        # Default handleError writes "--- Logging error ---" to sys.stderr.
        # When stderr is shell-redirected to LOG_FILE, that *is* the flood.
        return

    def _disable_broken_stream(self, exc: BaseException) -> None:
        global _BROKEN_SINK_LOGGED
        try:
            self.stream = open(os.devnull, "w", encoding="utf-8")
        except OSError:
            self.stream = None  # type: ignore[assignment]
        _BROKEN_SINK_LOGGED = True
        # Do not write to sys.stderr here — it is often the same redirected
        # LOG_FILE the operator is tailing. Stay fully silent after disable.
        _ = exc  # retained for call-site clarity / future metrics


class SafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that swallows disk/stream I/O failures without spam."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except (OSError, IOError):
            return
        except Exception:
            return

    def handleError(self, record: logging.LogRecord) -> None:
        return


def _path_writable(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return os.access(path, os.W_OK)
        # Probe create+unlink in the parent directory.
        probe = path.parent / f".companion-log-probe-{os.getpid()}"
        with open(probe, "a", encoding="utf-8") as fh:
            fh.write("")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _default_log_file() -> Path:
    """Prefer /var/log/resolve-companion.log when the process can write it."""
    if _path_writable(_VAR_LOG_FILE):
        return _VAR_LOG_FILE
    return _FALLBACK_LOG_FILE


def _resolve_log_file() -> Optional[Path]:
    raw = os.getenv("LOG_FILE")
    if raw is None:
        return _default_log_file()
    raw = raw.strip()
    if not raw or raw.lower() in ("-", "none", "off", "stderr"):
        return None
    return Path(raw).expanduser()


def _want_stderr_handler(file_active: bool) -> bool:
    flag = (os.getenv("LOG_TO_STDERR") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    # Default: stderr only when there is no file sink (avoid duplicate stream
    # into a shell-redirected copy of LOG_FILE).
    return not file_active


def _build_formatter() -> logging.Formatter:
    fmt = (os.getenv("LOG_FORMAT") or "json").strip()
    fmt_lower = fmt.lower()
    if fmt_lower in ("json", "structured"):
        return StructuredFormatter()
    if fmt_lower in ("kv", "keyvalue", "text"):
        return KeyValueFormatter()
    # Classic printf-style pattern (e.g. "%(asctime)s %(levelname)s %(message)s").
    datefmt = os.getenv("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")
    return logging.Formatter(fmt=fmt, datefmt=datefmt)


def _make_stream_handler(level: int, formatter: logging.Formatter) -> SafeStreamHandler:
    handler = SafeStreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler._companion_safe = True  # type: ignore[attr-defined]
    return handler


def _make_file_handler(
    path: Path, level: int, formatter: logging.Formatter
) -> Optional[SafeRotatingFileHandler]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = SafeRotatingFileHandler(
            filename=str(path),
            maxBytes=int(os.getenv("LOG_FILE_MAX_BYTES", str(10 * 1024 * 1024))),
            backupCount=int(os.getenv("LOG_FILE_BACKUP_COUNT", "5")),
            encoding="utf-8",
            delay=True,
        )
        handler.setLevel(level)
        handler.setFormatter(formatter)
        handler._companion_safe = True  # type: ignore[attr-defined]
        return handler
    except OSError:
        return None


def _close_remove(logger: logging.Logger, handler: logging.Handler) -> None:
    logger.removeHandler(handler)
    try:
        handler.close()
    except Exception:
        pass


def _strip_fragile_and_companion_handlers(logger: logging.Logger) -> None:
    for existing in list(logger.handlers):
        if getattr(existing, "_companion_safe", False):
            _close_remove(logger, existing)
            continue
        # Drop default StreamHandlers that write to a fragile stderr/tty.
        if isinstance(existing, logging.StreamHandler) and not isinstance(
            existing, logging.FileHandler
        ):
            _close_remove(logger, existing)


def configure_logging(force: bool = False) -> Optional[Path]:
    """Idempotent root + uvicorn logger setup. Returns active LOG_FILE path or None."""
    global _CONFIGURED, _ACTIVE_LOG_FILE
    if _CONFIGURED and not force:
        return _ACTIVE_LOG_FILE

    level_name = (os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = _build_formatter()

    handlers: List[logging.Handler] = []
    log_file = _resolve_log_file()
    active_file: Optional[Path] = None
    file_handler: Optional[SafeRotatingFileHandler] = None

    if log_file is not None:
        file_handler = _make_file_handler(log_file, level, formatter)
        if file_handler is not None:
            handlers.append(file_handler)
            active_file = log_file
        elif log_file != _FALLBACK_LOG_FILE and _path_writable(_FALLBACK_LOG_FILE):
            # /var/log preferred but failed at open time — fall back.
            file_handler = _make_file_handler(_FALLBACK_LOG_FILE, level, formatter)
            if file_handler is not None:
                handlers.append(file_handler)
                active_file = _FALLBACK_LOG_FILE

    if _want_stderr_handler(file_active=active_file is not None):
        handlers.append(_make_stream_handler(level, formatter))

    if not handlers:
        # Last resort: safe stderr so configure_logging never leaves root mute
        # without a sink (still swallows EIO).
        handlers.append(_make_stream_handler(level, formatter))

    root = logging.getLogger()
    root.setLevel(level)
    _strip_fragile_and_companion_handlers(root)
    for handler in handlers:
        root.addHandler(handler)

    # Strip uvicorn StreamHandlers. Propagate error loggers to root.
    # Access: dedicated Safe FileHandler (never a fragile/duplicate stream) so
    # shell-redirected stderr cannot receive access emit failures + handleError.
    for name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.setLevel(level)
        _strip_fragile_and_companion_handlers(uv_logger)
        uv_logger.propagate = True

    access = logging.getLogger("uvicorn.access")
    access.setLevel(level)
    _strip_fragile_and_companion_handlers(access)
    if active_file is not None:
        access_file = _make_file_handler(active_file, level, formatter)
        if access_file is not None:
            access.addHandler(access_file)
            access.propagate = False
        else:
            access.propagate = True
    else:
        # No file sink: propagate to root's SafeStreamHandler only.
        access.propagate = True

    # Keep noisy HTTP client libraries quiet unless the process is at DEBUG.
    if level > logging.DEBUG:
        for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
    _ACTIVE_LOG_FILE = active_file
    get_logger(__name__).info(
        "logging_configured",
        event="logging_configured",
        log_level=level_name,
        log_format=(os.getenv("LOG_FORMAT") or "json"),
        log_file=str(active_file) if active_file else None,
        stderr=_want_stderr_handler(file_active=active_file is not None),
    )
    return active_file


def is_eio(exc: BaseException) -> bool:
    """True when exc looks like the classic broken-tty / dead-redirect EIO."""
    return isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.EIO
