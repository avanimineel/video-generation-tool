"""Captions-only mode and cloud opt-in flags."""
import pytest

from app.services.auto_produce_mode import (
    CAPTIONS_ONLY_MESSAGE,
    cloud_readiness,
    feature_flags,
    resolve_auto_produce_mode,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "full"),
        ("full", "full"),
        ("captions_only", "captions_only"),
        ("captions-only", "captions_only"),
        ("offline_captions", "captions_only"),
        ("bogus", "full"),
    ],
)
def test_resolve_auto_produce_mode(value, expected, monkeypatch):
    monkeypatch.delenv("AUTO_PRODUCE_MODE", raising=False)
    assert resolve_auto_produce_mode(value) == expected


def test_env_mode_when_request_absent(monkeypatch):
    monkeypatch.setenv("AUTO_PRODUCE_MODE", "captions_only")
    assert resolve_auto_produce_mode(None) == "captions_only"
    assert resolve_auto_produce_mode("full") == "full"  # request wins


def test_feature_flags_defaults_and_off(monkeypatch):
    monkeypatch.delenv("ENABLE_TWELVE_LABS", raising=False)
    monkeypatch.delenv("ENABLE_GEMINI_EDITORIAL", raising=False)
    monkeypatch.delenv("ENABLE_STOCK_SEARCH", raising=False)
    assert feature_flags() == {
        "twelve_labs": True,
        "gemini_editorial": True,
        "stock_search": True,
    }
    monkeypatch.setenv("ENABLE_STOCK_SEARCH", "0")
    assert feature_flags()["stock_search"] is False


def test_cloud_readiness_reports_blockers(monkeypatch):
    monkeypatch.setenv("ENABLE_TWELVE_LABS", "1")
    monkeypatch.setenv("ENABLE_GEMINI_EDITORIAL", "1")
    monkeypatch.setenv("ENABLE_STOCK_SEARCH", "1")
    monkeypatch.setattr(
        "app.services.editorial_planner.configured_key",
        lambda name: "",
    )
    ok, blockers = cloud_readiness()
    assert ok is False
    assert any("TWELVE_LABS" in b for b in blockers)
    assert any("GEMINI" in b for b in blockers)


def _seed_project(monkeypatch, tmp_path, name="captions_proj"):
    from app.core.config import settings
    from app.core.database import init_db
    from app.services.project_manager import project_manager

    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    init_db()
    state = project_manager.create_project(name)
    source = tmp_path / "speech.mov"
    source.write_bytes(b"fixture")
    state.source_media_path = str(source)
    state.duration_seconds = 5
    project_manager.save_project(state)
    return state


def test_captions_only_pipeline_skips_editorial(monkeypatch, tmp_path):
    from app.core.models import CaptionItem
    from app.services.auto_production_service import auto_production_service
    from app.services.transcription_service import transcription_service
    from app.services.translation_service import translation_service
    from app.services import editorial_planner

    state = _seed_project(monkeypatch, tmp_path, "captions_only_mode")
    monkeypatch.setattr(
        transcription_service,
        "transcribe_with_whisper",
        lambda *a, **k: (
            "en",
            [CaptionItem(id="spoken", start=0, end=2, text="Hello world", translated_text="Hello world")],
        ),
    )
    monkeypatch.setattr(
        translation_service,
        "translate_captions_list",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("English must not translate")),
    )
    monkeypatch.setattr(
        editorial_planner,
        "run_editorial",
        lambda *a: (_ for _ in ()).throw(AssertionError("editorial must be skipped")),
    )

    result = auto_production_service.run_pipeline(state.id, mode="captions_only")
    assert result["success"] is True
    assert result["editorial_report"]["stage"] == "captions_only_complete"
    assert result["editorial_report"]["outcome"] == "captions_only"
    assert CAPTIONS_ONLY_MESSAGE in result["editorial_report"]["errors"]
    assert result["ingestion"]["status"] == "completed"
    assert result["ingestion"]["summary"]["auto_produce_mode"] == "captions_only"
    assert result["project"]["captions"][0]["text"] == "Hello world"


def test_full_mode_without_cloud_finishes_captions_clearly(monkeypatch, tmp_path):
    from app.core.models import CaptionItem
    from app.services.auto_production_service import auto_production_service
    from app.services.transcription_service import transcription_service
    from app.services import editorial_planner

    state = _seed_project(monkeypatch, tmp_path, "full_no_cloud")
    monkeypatch.setattr(
        transcription_service,
        "transcribe_with_whisper",
        lambda *a, **k: (
            "en",
            [CaptionItem(id="spoken", start=0, end=2, text="Speech", translated_text="Speech")],
        ),
    )
    monkeypatch.setattr(
        "app.services.auto_produce_mode.cloud_readiness",
        lambda: (False, ["TWELVE_LABS_API_KEY is missing or a test placeholder"]),
    )
    monkeypatch.setattr(
        editorial_planner,
        "run_editorial",
        lambda *a: (_ for _ in ()).throw(AssertionError("must not call editorial")),
    )

    result = auto_production_service.run_pipeline(state.id, mode="full")
    assert result["success"] is True
    assert result["editorial_report"]["stage"] == "captions_only_complete"
    assert any("TWELVE_LABS" in e for e in result["editorial_report"]["errors"])
