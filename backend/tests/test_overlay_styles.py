from types import SimpleNamespace

from app.services.overlay_styles import (
    add_look_overlays,
    add_punch_ins,
    apply_kinetic_captions,
    constrain_decisions,
    paint_look_effect,
    recommended_ids,
    styles_for_domain,
)


def test_finance_recommends_numbers_and_not_a_product_shot():
    recommended = set(recommended_ids("finance"))
    assert "data_callouts" in recommended
    assert "kinetic_captions" in recommended
    assert "product_swap" not in recommended
    assert {row["id"] for row in styles_for_domain("real estate")} >= {"location_maps", "data_callouts"}


def test_unselected_kinetic_title_is_left_out():
    decision = SimpleNamespace(strategy="KINETIC_TYPOGRAPHY", intervene=True, rationale="", asset=SimpleNamespace())
    constrain_decisions([decision], ["punch_in"], True)
    assert decision.strategy == "NO_INTERVENTION"
    assert decision.intervene is False


def test_a_chosen_place_becomes_a_map_search():
    asset = SimpleNamespace(retrieval_query="", alternate_queries=[], desired_visual_description="")
    decision = SimpleNamespace(strategy="MAP", intervene=True, rationale="", anchor_phrase="Mumbai", display_text="", intent="ILLUSTRATE", asset=asset)
    constrain_decisions([decision], ["location_maps"], True)
    assert decision.strategy == "STOCK_IMAGE"
    assert "Mumbai" in asset.retrieval_query


def test_kinetic_choice_highlights_the_spoken_word():
    style = SimpleNamespace(has_highlight=False, highlight_bounce=False, highlight_active_color="", highlight_scale=1, font_weight="400", animation_type="none")
    caption = SimpleNamespace(style=style)
    state = SimpleNamespace(captions=[caption])
    apply_kinetic_captions(state, ["kinetic_captions"], True)
    assert style.has_highlight is True
    assert style.highlight_bounce is True
    assert style.highlight_active_color == "#F5E642"


def test_looks_stay_separate_and_follow_the_domain():
    ids = {row["id"] for row in styles_for_domain("general")}
    for key in ("camera", "confetti", "paper", "fog", "film", "streaming", "glitch", "storm", "light_leak", "space"):
        assert key in ids
    assert "look_effects" not in ids
    finance = set(recommended_ids("finance"))
    sports = set(recommended_ids("sports"))
    education = set(recommended_ids("education"))
    assert "paper" in finance and "confetti" not in finance
    assert "storm" in sports and "confetti" in sports
    assert "space" in education and "glitch" not in education


def test_each_selected_look_is_its_own_overlay():
    state = SimpleNamespace(duration_seconds=24, captions=[])
    graphics = add_look_overlays(state, [], ["film", "camera"], True)
    assert [item.parameters["effect"] for item in graphics[:2]] == ["camera", "film"]
    assert all(item.template_id == "look_effect" for item in graphics)
    kept = add_look_overlays(state, graphics, ["camera"], True)
    assert {item.parameters["effect"] for item in kept} == {"camera"}


def test_a_look_paints_onto_the_frame():
    from PIL import Image
    image = Image.new("RGB", (64, 96), (8, 8, 8))
    paint_look_effect(image, "light_leak", 1.0)
    assert image.getpixel((4, 4)) != (8, 8, 8)


def test_punch_in_adds_a_short_zoom_on_a_number():
    caption = SimpleNamespace(start=2.0, end=4.0, text="Save 20 percent", translated_text="Save 20 percent")
    state = SimpleNamespace(captions=[caption])
    graphics = add_punch_ins(state, [], ["punch_in"], True)
    assert len(graphics) == 1
    assert graphics[0].template_id == "source_reframe"
    assert graphics[0].parameters["end_scale"] == 1.15
