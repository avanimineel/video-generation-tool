"""Light coverage for structured logging config and pipeline error_detail."""
import json
import sys
from types import SimpleNamespace

import pytest


def test_configure_logging_emits_json_and_respects_level(capsys, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FORMAT", "json")
    from app.core import logging_setup

    logging_setup._CONFIGURED = False
    logging_setup.configure_logging(force=True)

    log = logging_setup.get_logger("test.structured")
    with logging_setup.log_context(
        project_id="proj_demo",
        job_stage="transcription_and_translation",
        run_id="run1",
    ):
        log.info("hello_ops", event="hello_ops", ffmpeg_bin="/usr/bin/ffmpeg")

    err = capsys.readouterr().err
    lines = [ln for ln in err.splitlines() if ln.strip().startswith("{")]
    assert lines, err
    payload = json.loads(lines[-1])
    assert payload["level"] == "INFO"
    assert payload["msg"] == "hello_ops"
    assert payload["project_id"] == "proj_demo"
    assert payload["job_stage"] == "transcription_and_translation"
    assert payload["run_id"] == "run1"
    assert payload["event"] == "hello_ops"
    assert payload["ffmpeg_bin"] == "/usr/bin/ffmpeg"
    assert "ts" in payload and "logger" in payload


def test_format_exception_detail_includes_type_message_and_cause():
    from app.core.logging_setup import format_exception_detail

    try:
        try:
            raise OSError(5, "Input/output error", "/missing/ffmpeg")
        except OSError as inner:
            raise RuntimeError("ffmpeg extract failed") from inner
    except RuntimeError as exc:
        detail = format_exception_detail(exc)

    assert detail["type"] == "RuntimeError"
    assert "ffmpeg extract failed" in detail["message"]
    assert detail["cause"]["type"] == "OSError"
    assert "Input/output error" in detail["cause"]["message"]


def test_failed_auto_job_persists_error_detail(monkeypatch, tmp_path):
    """A raised pipeline exception must land structured error_detail in auto_job.json."""
    from app.core.config import settings
    from app.services import auto_jobs

    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    pid = "job_log_demo"
    (tmp_path / pid).mkdir()

    monkeypatch.setattr(
        auto_jobs.project_manager,
        "get_project",
        lambda _pid: SimpleNamespace(id=pid),
    )

    class BoomService:
        def run_pipeline(self, *a, **k):
            raise OSError(5, "Input/output error")

    submitted = []

    def immediate(fn):
        submitted.append(fn)
        fn()
        return SimpleNamespace(done=lambda: True)

    monkeypatch.setattr(auto_jobs._executor, "submit", immediate)
    monkeypatch.setitem(
        sys.modules,
        "app.services.auto_production_service",
        SimpleNamespace(auto_production_service=BoomService()),
    )

    with auto_jobs._lock:
        auto_jobs._jobs.pop(pid, None)

    job = auto_jobs.start(pid, force=True, model_size="base")
    assert submitted, "worker was not submitted"
    assert job["status"] == "failed"
    detail = job["error_detail"]
    assert detail["type"] == "OSError"
    assert "Input/output error" in detail["message"]
    assert detail.get("errno") == 5

    on_disk = json.loads((tmp_path / pid / "auto_job.json").read_text())
    assert on_disk["status"] == "failed"
    assert on_disk["error_detail"]["type"] == "OSError"


def test_pipeline_result_error_detail_is_persisted(monkeypatch, tmp_path):
    """Non-raising failures that return error_detail are copied into auto_job.json."""
    from app.core.config import settings
    from app.services import auto_jobs

    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    pid = "job_detail_demo"
    (tmp_path / pid).mkdir()
    monkeypatch.setattr(
        auto_jobs.project_manager,
        "get_project",
        lambda _pid: SimpleNamespace(id=pid),
    )

    class FailService:
        def run_pipeline(self, *a, **k):
            return {
                "success": False,
                "error": "Speech transcription failed.",
                "error_detail": {
                    "type": "FileNotFoundError",
                    "message": "ffmpeg_bin missing or not executable: '/bad/ffmpeg'",
                },
            }

    def immediate(fn):
        fn()
        return SimpleNamespace(done=lambda: True)

    monkeypatch.setattr(auto_jobs._executor, "submit", immediate)
    monkeypatch.setitem(
        sys.modules,
        "app.services.auto_production_service",
        SimpleNamespace(auto_production_service=FailService()),
    )
    with auto_jobs._lock:
        auto_jobs._jobs.pop(pid, None)

    job = auto_jobs.start(pid, force=True, model_size="base")
    assert job["status"] == "failed"
    assert job["error_detail"]["type"] == "FileNotFoundError"
    assert "ffmpeg_bin missing" in job["error_detail"]["message"]


def test_ffmpeg_missing_logs_and_raises(monkeypatch, tmp_path):
    from app.core.config import settings
    from app.services.transcription_service import TranscriptionService

    media = tmp_path / "clip.mp4"
    media.write_bytes(b"fake")
    monkeypatch.setattr(settings, "ffmpeg_bin", str(tmp_path / "no-such-ffmpeg"))
    monkeypatch.setattr(
        TranscriptionService,
        "get_whisper_model",
        classmethod(lambda cls, size=None: object()),
    )

    svc = TranscriptionService()
    with pytest.raises(FileNotFoundError, match="ffmpeg_bin missing"):
        svc.transcribe_with_whisper(str(media), model_size="base")
