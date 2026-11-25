from types import SimpleNamespace

from app.services.shortform_pipeline import build_story, run_shortform_agents


def _caption(start, end, text):
    return SimpleNamespace(start=start, end=end, text=text, translated_text=text, pos_y=0.82)


def _look(effect, start, title="Look"):
    return SimpleNamespace(id=f"{effect}-{start}", start=start, end=start + 1.5, template_id="look_effect", title=title, parameters={"effect": effect})


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


def test_remotion_composition_counts_frames_from_the_captions():
    captions = [_caption(0.0, 2.0, "Hello there")]
    state = SimpleNamespace(captions=captions, graphics=[], duration_seconds=2, settings=SimpleNamespace(domain_profile="education"), ai_ingestion={})
    _, report = run_shortform_agents(state, [], [], False, None)
    assert report["style_pack"] == "documentary"
    assert report["story"]["spine"]["hook"] == "Hello there"
