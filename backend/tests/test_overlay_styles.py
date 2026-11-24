from types import SimpleNamespace

from app.services.overlay_styles import (
    add_punch_ins,
    apply_kinetic_captions,
    constrain_decisions,
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


def test_punch_in_adds_a_short_zoom_on_a_number():
    caption = SimpleNamespace(start=2.0, end=4.0, text="Save 20 percent", translated_text="Save 20 percent")
    state = SimpleNamespace(captions=[caption])
    graphics = add_punch_ins(state, [], ["punch_in"], True)
    assert len(graphics) == 1
    assert graphics[0].template_id == "source_reframe"
    assert graphics[0].parameters["end_scale"] == 1.15
