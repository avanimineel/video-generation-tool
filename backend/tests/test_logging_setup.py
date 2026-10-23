"""Safe logging handlers must not raise or spam on broken sinks (errno 5)."""
from __future__ import annotations

import errno
import io
import logging
import os
from pathlib import Path

import pytest

from app.core.logging_setup import (
    SafeRotatingFileHandler,
    SafeStreamHandler,
    configure_logging,
    is_eio,
)


class _BrokenStream(io.StringIO):
    def write(self, s: str) -> int:
        raise OSError(errno.EIO, "Input/output error")

    def flush(self) -> None:
        raise OSError(errno.EIO, "Input/output error")


def test_safe_stream_handler_swallows_eio():
    handler = SafeStreamHandler(_BrokenStream())
    handler.setFormatter(logging.Formatter("%(message)s"))
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello access",
        args=(),
        exc_info=None,
    )
    # Must not raise; must not call into lastResort spam.
    handler.emit(record)
    handler.emit(record)


def test_is_eio():
    assert is_eio(OSError(errno.EIO, "Input/output error"))
    assert not is_eio(OSError(errno.ENOSPC, "No space left"))
    assert not is_eio(ValueError("nope"))


def test_configure_logging_writes_log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    log_path = tmp_path / "companion.log"
    monkeypatch.setenv("LOG_FILE", str(log_path))
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    configure_logging(force=True)
    logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /health HTTP/1.1" 200')
    # RotatingFileHandler with delay=True creates on first emit.
    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "GET /health" in text


def test_safe_rotating_handler_swallows_write_errors(tmp_path: Path):
    path = tmp_path / "x.log"
    handler = SafeRotatingFileHandler(str(path), maxBytes=1024, backupCount=1)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.stream = _BrokenStream()  # type: ignore[assignment]
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="still ok",
        args=(),
        exc_info=None,
    )
    handler.emit(record)  # must not raise
