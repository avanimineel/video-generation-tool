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
  LOG_FORMAT / LOG_DATEFMT
  LOG_FILE_MAX_BYTES / LOG_FILE_BACKUP_COUNT
  UVICORN_ACCESS_LOG    Consumed by start_companion.sh (1 = enable access log).
"""
from __future__ import annotations

import errno
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional

_CONFIGURED = False
_BROKEN_SINK_LOGGED = False
_ACTIVE_LOG_FILE: Optional[Path] = None

_VAR_LOG_FILE = Path("/var/log/resolve-companion.log")
_FALLBACK_LOG_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "companion.log"


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
    fmt = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
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

    if level > logging.DEBUG:
        for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
    _ACTIVE_LOG_FILE = active_file
    logging.getLogger(__name__).info(
        "logging configured level=%s log_file=%s stderr=%s",
        level_name,
        str(active_file) if active_file else "(none)",
        _want_stderr_handler(file_active=active_file is not None),
    )
    return active_file


def is_eio(exc: BaseException) -> bool:
    """True when exc looks like the classic broken-tty / dead-redirect EIO."""
    return isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.EIO
