"""Local HI→EN translation backend selection and Gemini fallback (mocked model)."""
import json
from types import SimpleNamespace

import pytest

from app.services.translation_service import TranslationService, translation_service as service
from app.core.models import CaptionItem, CaptionStyle, WordTiming


def _cap(text, start=0.0, end=1.0):
    return CaptionItem(
        id=f"c_{text[:8]}",
        start=start,
        end=end,
        text=text,
        pos_x=0.5,
        pos_y=0.8,
        words=[WordTiming(word=w, start=start, end=end) for w in text.split()[:3] or ["x"]],
        style=CaptionStyle(
            font_family="Montserrat",
            font_weight="bold",
            font_size=42,
            text_color="#FFFFFF",
            has_background=True,
            background_color="#000000",
            background_opacity=0.75,
            corner_radius=16,
            padding_x=20,
            padding_y=10,
            animation_type="none",
            highlight_active_color="#CCFF00",
            highlight_past_color="#B0B0B0",
            highlight_future_color="#FFFFFF",
            highlight_scale=1.0,
        ),
        source_language="hi",
    )


def test_translate_with_local_uses_injected_fn_and_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "local")
    checkpoint = tmp_path / "t.json"
    calls = []

    def local_fn(texts):
        calls.append(list(texts))
        return ["Lung cancer", "Biopsy"]

    out = service.translate_with_local(
        ["फेफड़े का कैंसर", "बायोप्सी"],
        checkpoint,
        translate_fn=local_fn,
    )
    assert out == ["Lung cancer", "Biopsy"]
    assert len(calls) == 1
    cached = json.loads(checkpoint.read_text())
    assert cached["backend"] == "local"
    assert cached["accepted"]["0"] == "Lung cancer"

    # Resume: no second model call
    out2 = service.translate_with_local(
        ["फेफड़े का कैंसर", "बायोप्सी"],
        checkpoint,
        translate_fn=lambda *_: (_ for _ in ()).throw(AssertionError("should not call")),
    )
    assert out2 == ["Lung cancer", "Biopsy"]


def test_auto_falls_back_to_gemini_when_local_fails(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "real-looking-gemini-key-not-placeholder")
    from app.services import editorial_planner as planner
    from app.core import config as cfg

    monkeypatch.setattr(cfg, "get_provider_key", lambda name: "real-looking-gemini-key-not-placeholder")
    monkeypatch.setattr(
        planner,
        "gemini_json",
        lambda *a, **k: {"lines": [{"id": 0, "text": "Doctor said"}, {"id": 1, "text": "Get biopsy"}]},
    )

    def boom(_texts):
        raise RuntimeError("transformers missing")

    chunk = service._translate_chunk(
        ["डॉक्टर ने कहा", "बायोप्सी कराओ"],
        local_fn=boom,
    )
    assert chunk == ["Doctor said", "Get biopsy"]


def test_local_backend_does_not_call_gemini(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "local")
    monkeypatch.setenv("GEMINI_API_KEY", "real-looking-gemini-key-not-placeholder")
    from app.services import editorial_planner as planner

    monkeypatch.setattr(
        planner,
        "gemini_json",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("gemini must not run")),
    )

    out = service._translate_chunk(
        ["कैंसर"],
        local_fn=lambda texts: ["cancer"],
    )
    assert out == ["cancer"]


def test_gemini_backend_without_key_errors(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "gemini")
    from app.core import config as cfg

    monkeypatch.setattr(cfg, "get_provider_key", lambda name: "")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        service._translate_chunk(["कैंसर"], local_fn=lambda t: ["x"])


def test_translate_captions_list_local_backend(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "local")
    from app.services.transcript_quality import transcript_issues

    monkeypatch.setattr(
        "app.services.transcript_quality.transcript_issues",
        lambda caps: [],
    )
    caps = [_cap("फेफड़े का कैंसर", 0, 1), _cap("इलाज", 1, 2)]
    out = service.translate_captions_list(
        caps,
        local_fn=lambda texts: ["lung cancer", "treatment"],
    )
    assert [c.translated_text for c in out] == ["lung cancer", "treatment"]


def test_latin_passthrough_in_local_helper():
    from app.services.local_translation import translate_lines_local

    assert translate_lines_local(
        ["already english", "also fine"],
        translate_fn=lambda s: (_ for _ in ()).throw(AssertionError("no model")),
    ) == ["already english", "also fine"]


def test_devanagari_uses_translate_fn():
    from app.services.local_translation import translate_lines_local

    assert translate_lines_local(["कैंसर"], translate_fn=lambda s: "cancer") == ["cancer"]
