"""Surface Whisper failure causes without importing the full FastAPI app stack."""
import json
import time
from pathlib import Path

from app.core.config import settings
from app.core.database import init_db
from app.core.models import ProjectState
from app.services import auto_jobs
from app.services.auto_production_service import auto_production_service
from app.services.project_manager import project_manager
from app.services.transcription_service import transcription_service


def _seed(name: str, tmp_path: Path) -> ProjectState:
    init_db()
    state = project_manager.create_project(name)
    source = tmp_path / 'speech.mov'
    source.write_bytes(b'fixture')
    state.source_media_path = str(source)
    state.duration_seconds = 5
    project_manager.save_project(state)
    return project_manager.get_project(state.id)


def test_whisper_exception_surfaces_underlying_error_in_result(monkeypatch, tmp_path):
    state = _seed('whisper_surface_error', tmp_path)
    monkeypatch.setattr(
        transcription_service,
        'transcribe_with_whisper',
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('cudaErrorMemoryAllocation: simulated OOM')),
    )
    result = auto_production_service.run_pipeline(state.id, True)
    assert not result['success']
    assert 'Speech transcription failed' in result['error']
    assert 'Underlying error:' in result['error']
    assert result['error_cause'] == 'cudaErrorMemoryAllocation: simulated OOM'
    assert result['stage'] == 'whisper_transcribe'
    assert result['error_detail']['type'] == 'RuntimeError'
    detail = json.loads((settings.projects_dir / state.id / 'transcription' / 'last_failure.json').read_text())
    assert detail['stage'] == 'whisper_transcribe'
    assert detail['error_cause'] == 'cudaErrorMemoryAllocation: simulated OOM'


def test_empty_whisper_segments_fail_closed_with_cause(monkeypatch, tmp_path):
    state = _seed('whisper_empty_segments', tmp_path)
    monkeypatch.setattr(transcription_service, 'transcribe_with_whisper', lambda *a, **kw: ('en', []))
    result = auto_production_service.run_pipeline(state.id, True)
    assert not result['success']
    assert result['stage'] == 'whisper_empty_segments'
    assert 'empty_asr_segments' in result['error_cause']
    assert result['error_detail']['type'] == 'EmptyASRSegments'
    native = json.loads((settings.projects_dir / state.id / 'transcription' / 'native_source.json').read_text())
    assert native['caption_count'] == 0
    assert project_manager.get_project(state.id).captions == []


def test_whisper_failure_persists_error_detail_on_auto_job(monkeypatch, tmp_path):
    state = _seed('whisper_job_detail', tmp_path)
    monkeypatch.setattr(
        transcription_service,
        'transcribe_with_whisper',
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('ct2::CudaError during decode')),
    )
    auto_jobs.start(state.id, force=True)
    for _ in range(100):
        job = auto_jobs.status(state.id)
        if job['status'] not in ('queued', 'running'):
            break
        time.sleep(0.01)
    assert job['status'] == 'failed'
    assert job['stage'] == 'whisper_transcribe'
    assert job['error_cause'] == 'ct2::CudaError during decode'
    assert 'Underlying error:' in job['error']
    assert job['error_detail']['type'] == 'RuntimeError'
