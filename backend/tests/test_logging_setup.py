"""Safe logging handlers must not raise or spam on broken sinks (errno 5)."""
from __future__ import annotations

import errno
import io
import logging
from pathlib import Path

import pytest

from app.core import logging_setup
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


def test_safe_stream_handler_swallows_eio_without_handleerror_spam(capsys):
    handler = SafeStreamHandler(_BrokenStream())
    handler.setFormatter(logging.Formatter("%(message)s"))
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='127.0.0.1 - "GET /health HTTP/1.1" 200',
        args=(),
        exc_info=None,
    )
    handler.emit(record)
    handler.emit(record)
    # Critical: must not print --- Logging error --- to stderr (the flood vector
    # when stderr is shell-redirected into LOG_FILE).
    captured = capsys.readouterr()
    assert "--- Logging error ---" not in captured.err
    assert "Input/output error" not in captured.err


def test_is_eio():
    assert is_eio(OSError(errno.EIO, "Input/output error"))
    assert not is_eio(OSError(errno.ENOSPC, "No space left"))
    assert not is_eio(ValueError("nope"))


def test_configure_logging_writes_log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    log_path = tmp_path / "resolve-companion.log"
    monkeypatch.setenv("LOG_FILE", str(log_path))
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.delenv("LOG_TO_STDERR", raising=False)
    configure_logging(force=True)
    logging.getLogger("app.test").info("app_line_ok")
    assert log_path.exists()
    assert "app_line_ok" in log_path.read_text(encoding="utf-8")


def test_access_logger_uses_file_handler_not_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    log_path = tmp_path / "resolve-companion.log"
    monkeypatch.setenv("LOG_FILE", str(log_path))
    monkeypatch.delenv("LOG_TO_STDERR", raising=False)
    configure_logging(force=True)

    access = logging.getLogger("uvicorn.access")
    assert access.propagate is False
    assert any(isinstance(h, SafeRotatingFileHandler) for h in access.handlers)
    assert not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in access.handlers
    )
    access.info('127.0.0.1 - "GET /health HTTP/1.1" 200')
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
    handler.emit(record)


def test_default_prefers_var_log_when_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fake_var = tmp_path / "varlog" / "resolve-companion.log"
    monkeypatch.setattr(logging_setup, "_VAR_LOG_FILE", fake_var)
    monkeypatch.delenv("LOG_FILE", raising=False)
    assert logging_setup._resolve_log_file() == fake_var
