"""Central structured logging for EC2 / uvicorn operators.

Configure once at app startup. Prefer LOG_LEVEL=DEBUG on the host when
debugging auto-produce failures (missing ffmpeg, Whisper retries, Google 429).

  # journald / nohup example
  LOG_LEVEL=DEBUG python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8002
  # or: journalctl -u resolve-companion -f
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

_project_id: ContextVar[Optional[str]] = ContextVar("log_project_id", default=None)
_job_stage: ContextVar[Optional[str]] = ContextVar("log_job_stage", default=None)
_run_id: ContextVar[Optional[str]] = ContextVar("log_run_id", default=None)

_CONFIGURED = False

# Redact common secret env key fragments; never log credential values.
_SECRET_MARKERS = ("API_KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL")
_MAX_FIELD = 500
_MAX_STDERR = 800


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


def format_exception_detail(exc: BaseException, *, limit: int = 1500) -> Dict[str, Any]:
    """Structured exception payload for auto_job.json / status (not only str(exc))."""
    detail: Dict[str, Any] = {
        "type": type(exc).__name__,
        "message": truncate(redact_secrets(str(exc)), limit),
    }
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if isinstance(cause, BaseException) and cause is not exc:
        detail["cause"] = {
            "type": type(cause).__name__,
            "message": truncate(redact_secrets(str(cause)), limit),
        }
    # OSError / errno chain is often what operators need on EC2.
    errno = getattr(exc, "errno", None)
    if errno is not None:
        detail["errno"] = errno
    filename = getattr(exc, "filename", None)
    if filename:
        detail["filename"] = truncate(filename, 200)
    return detail


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
    """One JSON object per line (CloudWatch / journald friendly)."""

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
        for key, value in {**current_context(), **(getattr(record, "structured", None) or {})}.items():
            parts.append(f"{key}={truncate(value)!r}" if isinstance(value, str) else f"{key}={value}")
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
        # Pull known context kwargs out of logger.info(..., project_id=...) style calls.
        for key in (
            "project_id",
            "job_stage",
            "run_id",
            "ffmpeg_bin",
            "media_path",
            "model_size",
            "force",
            "captions_existed",
            "returncode",
            "stderr_tail",
            "output_path",
            "event",
            "stage",
            "error_detail",
        ):
            if key in kwargs:
                structured[key] = kwargs.pop(key)
        # Any remaining non-standard kwargs become structured fields.
        for key in list(kwargs.keys()):
            if key in ("exc_info", "stack_info", "stacklevel", "extra"):
                continue
            structured[key] = kwargs.pop(key)
        if structured:
            extra["structured"] = structured
        return msg, kwargs


def get_logger(name: str) -> StructuredAdapter:
    return StructuredAdapter(logging.getLogger(name), {})


def configure_logging(force: bool = False) -> None:
    """Idempotent root logger setup. Call from FastAPI lifespan / CLI entrypoints."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    level_name = (os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt_name = (os.getenv("LOG_FORMAT") or "json").lower()
    formatter: logging.Formatter = (
        KeyValueFormatter() if fmt_name in ("kv", "keyvalue", "text") else StructuredFormatter()
    )

    root = logging.getLogger()
    root.setLevel(level)
    # Replace only our previous handlers; leave pytest / uvicorn custom handlers alone when forcing.
    for handler in list(root.handlers):
        if getattr(handler, "_companion_structured", False):
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler._companion_structured = True  # type: ignore[attr-defined]
    root.addHandler(handler)

    # Keep noisy third-party libraries quieter unless explicitly DEBUG.
    if level > logging.DEBUG:
        for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "faster_whisper", "openai"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
    get_logger(__name__).info(
        "logging_configured",
        event="logging_configured",
        log_level=level_name,
        log_format=fmt_name,
    )


def stderr_tail(text: Any, limit: int = _MAX_STDERR) -> str:
    raw = redact_secrets("" if text is None else str(text)).strip()
    if len(raw) <= limit:
        return raw
    return "..." + raw[-limit:]
