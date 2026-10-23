"""Resilient logging for EC2 / detached-SSH / broken-tty hosts.

Uvicorn's default StreamHandler writes to stderr. When that sink is dead
(SSH tty closed after detach, broken redirect, disk I/O), every access-log
line raises OSError errno 5 and Python's logging lastResort prints a huge
"--- Logging error ---" block — while HTTP handlers still return 200/206.

This module:
  * wraps stream/file handlers so emit failures (especially EIO) are silent
    and do not recurse into handleError spam
  * mirrors logs to a rotatable LOG_FILE by default (backend/logs/companion.log)
  * rebinds uvicorn.access / uvicorn.error onto the same safe handlers

Env:
  LOG_FILE     Path for rotatable app/access logs. Default: backend/logs/companion.log.
               Set empty / "none" / "off" / "-" to disable the file sink.
  LOG_LEVEL    Default INFO
  LOG_FORMAT   logging format string (optional)
  LOG_DATEFMT  logging date format (optional)
  LOG_FILE_MAX_BYTES / LOG_FILE_BACKUP_COUNT  rotation knobs
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

_DEFAULT_LOG_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "companion.log"


class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that swallows broken-pipe / EIO emit failures without spam."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self.stream is None:
                return
            super().emit(record)
        except (OSError, IOError) as exc:
            self._disable_broken_stream(exc)

    def handleError(self, record: logging.LogRecord) -> None:
        # Default handleError writes to sys.stderr and triggers lastResort loops
        # when stderr itself is the broken sink. Stay silent.
        return

    def _disable_broken_stream(self, exc: BaseException) -> None:
        global _BROKEN_SINK_LOGGED
        err_no = getattr(exc, "errno", None)
        try:
            self.stream = open(os.devnull, "w", encoding="utf-8")
        except OSError:
            self.stream = None  # type: ignore[assignment]
        if _BROKEN_SINK_LOGGED:
            return
        _BROKEN_SINK_LOGGED = True
        msg = (
            f"logging stream sink failed ({type(exc).__name__}"
            f"{f' errno={err_no}' if err_no is not None else ''}); "
            "suppressing further stream emit errors. "
            "Set LOG_FILE for durable logs.\n"
        )
        try:
            if sys.__stderr__ is not None:
                sys.__stderr__.write(msg)
        except Exception:
            pass


class SafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that swallows disk/stream I/O failures without spam."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except (OSError, IOError):
            # Drop the record; do not call handleError (avoids --- Logging error ---).
            return

    def handleError(self, record: logging.LogRecord) -> None:
        return


def _resolve_log_file() -> Optional[Path]:
    raw = os.getenv("LOG_FILE")
    if raw is None:
        return _DEFAULT_LOG_FILE
    raw = raw.strip()
    if not raw or raw.lower() in ("-", "none", "off", "stderr"):
        return None
    return Path(raw).expanduser()


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
    except OSError as exc:
        try:
            if sys.__stderr__ is not None:
                sys.__stderr__.write(
                    f"LOG_FILE={path} not writable ({exc}); continuing with stream only.\n"
                )
        except Exception:
            pass
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

    handlers: List[logging.Handler] = [_make_stream_handler(level, formatter)]

    log_file = _resolve_log_file()
    active_file: Optional[Path] = None
    if log_file is not None:
        file_handler = _make_file_handler(log_file, level, formatter)
        if file_handler is not None:
            handlers.append(file_handler)
            active_file = log_file

    root = logging.getLogger()
    root.setLevel(level)
    _strip_fragile_and_companion_handlers(root)
    for handler in handlers:
        root.addHandler(handler)

    # Uvicorn installs its own StreamHandlers; strip them and propagate to root
    # so access/error lines use the same safe sinks (no shared-handler close races).
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.setLevel(level)
        _strip_fragile_and_companion_handlers(uv_logger)
        uv_logger.propagate = True

    if level > logging.DEBUG:
        for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
    _ACTIVE_LOG_FILE = active_file
    logging.getLogger(__name__).info(
        "logging configured level=%s log_file=%s",
        level_name,
        str(active_file) if active_file else "(stream only)",
    )
    return active_file


def is_eio(exc: BaseException) -> bool:
    """True when exc looks like the classic broken-tty / dead-redirect EIO."""
    return isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.EIO
