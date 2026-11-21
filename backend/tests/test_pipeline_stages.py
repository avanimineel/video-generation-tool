"""Stage list: continue from the first unfinished step, or rerun from a chosen step."""
import json

from app.core.models import CaptionItem
from app.services.pipeline_stages import normalize_from_stage, pipeline_status


def test_continue_starts_after_finished_captions_and_translation(tmp_path):
    class State:
        id = "clip"
        captions = [CaptionItem(id="a", start=0, end=2, text="नमस्ते", translated_text="Hello")]
        graphics = []

    status = pipeline_status(State(), tmp_path)
    assert status["next_stage"] == "understanding"
    assert status["continue_label"] == "Continue from video understanding"
    assert status["stages"][0]["state"] == "done"
    assert status["stages"][1]["state"] == "done"


def test_changed_captions_make_the_visual_plan_out_of_date(tmp_path):
    editorial = tmp_path / "clip" / "editorial" / "run1"
    editorial.mkdir(parents=True)
    (editorial / "00_transcript.json").write_text(json.dumps([
        {"start_sec": 0, "end_sec": 2, "text": "Hello"},
    ]))
    (editorial / "03_schedule.json").write_text("[]")
    (editorial / "06_timeline.json").write_text("[]")

    class State:
        id = "clip"
        captions = [CaptionItem(id="a", start=0, end=2, text="Hello again", translated_text="Hello again")]
        graphics = []

    status = pipeline_status(State(), tmp_path)
    assert status["stages"][3]["state"] == "out_of_date"
    assert status["next_stage"] == "understanding"


def test_from_stage_names():
    assert normalize_from_stage("asset_review") == "pictures"
    assert normalize_from_stage("captions") == "captions"
    assert normalize_from_stage("nope") is None


def test_starting_at_captions_continues_into_visuals(monkeypatch, tmp_path):
    from app.core.config import settings
    from app.core.database import init_db
    from app.services.auto_production_service import auto_production_service
    from app.services.project_manager import project_manager
    from app.services.transcription_service import transcription_service
    from app.services import editorial_planner

    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    init_db()
    state = project_manager.create_project("stage_continue")
    source = tmp_path / "speech.mov"
    source.write_bytes(b"fixture")
    state.source_media_path = str(source)
    state.duration_seconds = 5
    state.captions = [CaptionItem(id="old", start=0, end=1, text="Old", translated_text="Old")]
    project_manager.save_project(state)
    monkeypatch.setattr(
        transcription_service,
        "transcribe_with_whisper",
        lambda *a, **k: ("en", [CaptionItem(id="fresh", start=0, end=2, text="Hello", translated_text="Hello")]),
    )
    calls = []
    monkeypatch.setattr(
        editorial_planner,
        "run_editorial",
        lambda *a, **k: calls.append(k.get("start_at")) or ([], [], {"status": "complete", "run_id": "planned", "errors": [], "inserted": 0, "outcome": "complete_with_gaps"}),
    )
    monkeypatch.setattr(
        "app.services.editorial_planner.configured_key",
        lambda name: "fixture-credential-value" if name == "GEMINI_API_KEY" else "",
    )

    result = auto_production_service.run_pipeline(state.id, mode="full", from_stage="captions")
    assert calls == ["understanding"]
    assert result["editorial_report"]["run_id"] == "planned"
    assert result["project"]["captions"][0]["text"] == "Hello"


def test_pictures_resume_keeps_the_plan_and_searches_again(tmp_path, monkeypatch):
    from app.services.editorial_planner import resume_saved_stage
    from app.services import editorial_planner as planner

    run = tmp_path / "clip" / "editorial" / "run1"
    run.mkdir(parents=True)
    (run / "00_transcript.json").write_text(json.dumps([
        {"start_sec": 0, "end_sec": 2, "text": "Hello"},
    ]))
    (run / "03_schedule.json").write_text(json.dumps([
        {"status": "rejected_assets", "strategy": "STOCK_IMAGE", "segment_id": "s1"},
        {"status": "no_intervention", "strategy": "NO_INTERVENTION", "segment_id": "s2"},
    ]))

    class State:
        id = "clip"
        captions = [CaptionItem(id="a", start=0, end=2, text="Hello", translated_text="Hello")]

    from app.core.config import settings
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    seen = []

    def execute(state, rows, run_dir):
        seen.extend(rows)
        return [], []

    monkeypatch.setattr(planner, "execute_plan", execute)
    monkeypatch.setattr(planner, "persist_evaluation_decisions", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.services.finished_reel_understanding.audit_plan",
        lambda *a, **k: {"scorecard": {"outcome": "complete_with_gaps"}},
    )
    report = {"run_id": "resume"}
    saved = []
    result = resume_saved_stage(State(), (), False, "pictures", tmp_path / "new-run", report, lambda: saved.append(1))
    assert result is not None
    assert seen[0]["status"] == "planned"
    assert seen[1]["status"] == "no_intervention"
