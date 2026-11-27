from types import SimpleNamespace

from PIL import Image

from app.services.overlay_styles import load_creator_preset, save_creator_preset
from app.services.picture_finish import VOICE_CLEANUP, export_preset, grade_frame
from app.services.shortform_pipeline import build_story, run_shortform_agents


def _caption(start, end, text):
    return SimpleNamespace(start=start, end=end, text=text, translated_text=text, pos_y=0.82)


def _look(effect, start, title="Look"):
    return SimpleNamespace(id=f"{effect}-{start}", start=start, end=start + 1.5, template_id="look_effect", title=title, parameters={"effect": effect})


def test_neighboring_captions_join_into_one_beat_without_rewriting():
    captions = [
        _caption(0.2, 2.0, "When you grow old, your health deteriorates"),
        _caption(2.1, 4.0, "in old age medical bills increase"),
        _caption(8.0, 9.5, "Start now"),
    ]
    story = build_story(captions, beats=[[0, 1], [2]])
    assert story["beat_source"] == "given"
    assert story["beats"][0]["lines"] == [
        "When you grow old, your health deteriorates",
        "in old age medical bills increase",
    ]
    assert story["beats"][0]["text"] == "When you grow old, your health deteriorates in old age medical bills increase"
    assert story["beats"][0]["end"] == 4.0
    assert story["beats"][1]["lines"] == ["Start now"]
    assert story["lines"][0]["text"] == "When you grow old, your health deteriorates"
    assert story["lines"][1]["beat"] == story["lines"][0]["index"]


def test_story_uses_spoken_lines_and_names_viral_patterns():
    captions = [
        _caption(0.2, 2.0, "What if you saved 20 percent"),
        _caption(4.0, 6.0, "The study showed a real drop"),
        _caption(8.0, 10.0, "Then the family waited"),
        _caption(12.0, 14.0, "Start now"),
    ]
    story = build_story(captions)
    assert story["spine"]["hook"] == "What if you saved 20 percent"
    assert story["spine"]["proof"] == "The study showed a real drop"
    assert story["spine"]["cta"] == "Start now"
    patterns = {item["text"]: item["patterns"] for item in story["inferences"]}
    assert "specific_number" in patterns["What if you saved 20 percent"]
    assert "direct_address" in patterns["What if you saved 20 percent"]
    assert "stakes" in patterns["What if you saved 20 percent"]


def test_mood_gate_and_gap_run_when_overlays_were_chosen():
    captions = [_caption(0.0, 3.0, "The rate is 20 percent"), _caption(6.0, 8.0, "We win this launch")]
    graphics = [_look("storm", 0.2), _look("confetti", 0.4), _look("confetti", 6.2)]
    state = SimpleNamespace(captions=captions, graphics=[], duration_seconds=12, settings=SimpleNamespace(domain_profile="finance"), ai_ingestion={})
    kept, report = run_shortform_agents(state, graphics, ["storm", "confetti"], True, None)
    effects = [item.parameters["effect"] for item in kept]
    assert effects == ["confetti"]
    assert report["style_pack"] == "direct_response"
    assert report["acceptance"]["gap_ok"] is True
    assert report["remotion"]["fps"] == 30
    assert state.captions[0].pos_y == 0.76
    assert state.ai_ingestion["shortform"]["hook"].startswith("The rate")


def test_emphasis_and_entity_use_the_spoken_line():
    captions = [_caption(0.4, 2.4, "Save 20 percent in Mumbai")]
    state = SimpleNamespace(
        captions=captions,
        graphics=[],
        duration_seconds=8,
        settings=SimpleNamespace(domain_profile="finance", overlay_product_note=""),
        ai_ingestion={},
    )
    chosen = ["punch_in", "data_callouts", "location_maps", "kinetic_captions", "sfx"]
    kept, report = run_shortform_agents(state, [], chosen, True, None)
    titles = [item.title for item in kept]
    assert "20" in titles
    assert "Mumbai" in titles
    punch = next(item for item in kept if item.template_id == "source_reframe")
    assert punch.parameters["end_scale"] == 1.15
    assert punch.parameters["easing"] == "easing.bezier"
    assert report["agents"] == [
        "story", "brief", "caption", "emphasis", "entity", "relevance", "interrupt", "density",
        "paper_purple", "motion", "stock_vfx", "sound", "platform", "remotion", "measure",
    ]
    assert report["sound"]["status"] == "marked"
    assert report["stock_vfx"]["fallback"] == "procedural"


def test_paper_purple_draws_a_bill_and_keeps_the_camera_locked():
    captions = [
        _caption(0.3, 2.4, "The medical bill grows"),
        _caption(4.0, 6.0, "Hello again"),
    ]
    state = SimpleNamespace(
        captions=captions,
        graphics=[],
        duration_seconds=8,
        settings=SimpleNamespace(domain_profile="medical", overlay_product_note=""),
        ai_ingestion={},
    )
    kept, report = run_shortform_agents(state, [], ["paper_purple", "punch_in"], True, None)
    scenes = [item for item in kept if item.parameters.get("effect") == "paper_purple" and not item.parameters.get("badge")]
    assert scenes[0].parameters["subject"] == "bill"
    assert scenes[0].start < 3
    assert scenes[0].parameters["transition"] == "cut"
    assert any(item.parameters.get("badge") for item in kept)
    assert not any(item.template_id == "source_reframe" for item in kept)
    assert report["paper_purple"]["scenes"] == 1
    assert report["emphasis"]["status"] == "locked"
    assert captions[0].text == "The medical bill grows"
    from app.services.automatic_sfx import sound_cues
    kinds = [cue["kind"] for cue in sound_cues(scenes, 8)]
    assert kinds[0] == "swipe"
    assert "click" in kinds


def test_a_weak_opening_punches_the_strongest_line_inside_seven_seconds():
    captions = [
        _caption(0.2, 2.0, "Hello there"),
        _caption(3.0, 5.0, "You save 20 percent"),
        _caption(12.0, 14.0, "The study showed a real drop"),
    ]
    state = SimpleNamespace(captions=captions, graphics=[], duration_seconds=16, settings=SimpleNamespace(domain_profile="finance", overlay_product_note=""), ai_ingestion={})
    kept, report = run_shortform_agents(state, [], ["punch_in"], True, None)
    punches = [item for item in kept if item.template_id == "source_reframe"]
    assert punches[0].start == 3.0
    assert punches[0].parameters["opening"] is True
    assert punches[0].parameters["focus_y"] == 0.35
    assert report["emphasis"]["opening"]["weak"] is True
    assert all(item.start < 7 or item.start >= 12 for item in punches)


def test_a_look_in_a_pause_is_dropped_and_a_long_gap_gets_a_speech_look():
    captions = [_caption(0.2, 1.4, "Hello there"), _caption(9.0, 11.0, "Then the family waited")]
    state = SimpleNamespace(captions=captions, graphics=[], duration_seconds=12, settings=SimpleNamespace(domain_profile="general"), ai_ingestion={})
    look = SimpleNamespace(id="paper-gap", start=4.0, end=6.0, template_id="look_effect", title="Crumpled paper", parameters={"effect": "paper"})
    kept, report = run_shortform_agents(state, [look], ["paper", "film"], True, None)
    assert "paper-gap" not in [item.id for item in kept]
    assert any(getattr(item, "parameters", {}).get("interrupt") for item in kept)
    assert report["interrupt"]["dropped"][0]["reason"] == "pause"


def test_pause_tighten_closes_the_gap_and_keeps_the_words():
    from app.services.shortform_pipeline import apply_pause_tighten
    first = _caption(0.0, 1.0, "Hello there")
    second = _caption(3.0, 4.0, "Save now")
    second.words = [SimpleNamespace(start=3.1, end=3.4)]
    graphic = SimpleNamespace(start=3.0, end=3.8)
    apply_pause_tighten([first, second], [graphic], 0.6, 0.12)
    assert first.text == "Hello there" and second.text == "Save now"
    assert second.start == 1.12
    assert second.words[0].start == 1.22
    assert graphic.start == 1.12


def test_remotion_composition_counts_frames_from_the_captions():
    captions = [_caption(0.0, 2.0, "Hello there")]
    state = SimpleNamespace(captions=captions, graphics=[], duration_seconds=2, settings=SimpleNamespace(domain_profile="education"), ai_ingestion={})
    _, report = run_shortform_agents(state, [], [], False, None)
    assert report["style_pack"] == "documentary"
    assert report["story"]["spine"]["hook"] == "Hello there"


def test_grade_warms_direct_response_and_export_is_vertical_1080():
    image = Image.new("RGB", (8, 8), (140, 120, 110))
    warm = grade_frame(image, "direct_response")
    plain = grade_frame(image.copy(), "documentary")
    assert warm.getpixel((4, 4))[0] > plain.getpixel((4, 4))[0]
    assert export_preset(True)["width"] == 1080
    assert export_preset(True)["height"] == 1920
    assert "loudnorm=I=-14" in VOICE_CLEANUP


def test_creator_preset_is_reused_for_the_same_domain(tmp_path):
    state = SimpleNamespace(settings=SimpleNamespace(
        domain_profile="finance",
        overlay_choice_made=True,
        overlay_styles=["punch_in", "kinetic_captions"],
        caption_highlight_color="#F5E642",
        punch_scale=1.12,
    ))
    save_creator_preset(state, tmp_path)
    saved = load_creator_preset("finance", tmp_path)
    assert saved["styles"] == ["punch_in", "kinetic_captions"]
    assert saved["punch_scale"] == 1.12
    assert load_creator_preset("medical", tmp_path) == {}
