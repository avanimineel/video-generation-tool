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


def test_explainer_styles_are_separate_overlay_choices():
    ids = {row["id"] for row in styles_for_domain("education")}
    for key in ("flat_vector", "scrapbook", "flat_infographic", "paper_craft"):
        assert key in ids
    education = set(recommended_ids("education"))
    sports = set(recommended_ids("sports"))
    legal = set(recommended_ids("legal"))
    assert {"flat_vector", "scrapbook", "flat_infographic", "paper_craft"} <= education
    assert "flat_infographic" in sports and "scrapbook" not in sports
    assert "flat_infographic" in legal and "paper_craft" not in legal


def test_each_selected_look_is_its_own_overlay():
    state = SimpleNamespace(duration_seconds=24, captions=[])
    graphics = add_look_overlays(state, [], ["film", "camera"], True)
    assert [item.parameters["effect"] for item in graphics[:2]] == ["camera", "film"]
    assert all(item.template_id == "look_effect" for item in graphics)
    kept = add_look_overlays(state, graphics, ["camera"], True)
    assert {item.parameters["effect"] for item in kept} == {"camera"}


def test_paper_purple_draws_the_spoken_thing_and_keeps_evidence():
    from app.services.overlay_styles import apply_paper_purple_captions
    style = SimpleNamespace(
        font_family="Montserrat", font_weight="700", text_color="#FFFFFF",
        highlight_active_color="", highlight_past_color="", highlight_future_color="",
        has_highlight=False, highlight_bounce=True, highlight_scale=1.08, animation_type="pop",
        has_background=True, background_color="#000000", background_opacity=0.7, corner_radius=16,
        padding_x=8, padding_y=4, outline_width=2, has_shadow=True, shadow_blur=4,
        is_uppercase=True, max_lines=1, contrast_block_mode="pill", letter_spacing=1,
    )
    caption = SimpleNamespace(style=style, text="The medical bill grows", translated_text="The medical bill grows")
    state = SimpleNamespace(captions=[caption])
    assert apply_paper_purple_captions(state, ["paper_purple"], True) == 1
    assert caption.text == "The medical bill grows"
    assert style.font_family == "Special Elite"
    assert style.text_color == "#4F4947"
    assert style.highlight_future_color == "#C3BCB8"
    assert style.highlight_bounce is False
    assert style.contrast_block_mode == "paper_purple"
    illustrated = SimpleNamespace(strategy="STOCK_IMAGE", intervene=True, rationale="", visual_role="illustration", asset=SimpleNamespace())
    evidence = SimpleNamespace(strategy="STOCK_IMAGE", intervene=True, rationale="", visual_role="evidence", asset=SimpleNamespace())
    constrain_decisions([illustrated, evidence], ["paper_purple"], True)
    assert illustrated.strategy == "NO_INTERVENTION"
    assert illustrated.intervene is False
    assert evidence.strategy == "STOCK_IMAGE"


def test_a_look_paints_onto_the_frame():
    from PIL import Image
    image = Image.new("RGB", (64, 96), (8, 8, 8))
    paint_look_effect(image, "light_leak", 1.0)
    assert image.getpixel((4, 4)) != (8, 8, 8)
    craft = Image.new("RGB", (120, 180), (8, 8, 8))
    paint_look_effect(craft, "paper_craft", 1.0)
    assert craft.getpixel((40, 80)) != (8, 8, 8)
    paper = Image.new("RGB", (120, 180), (8, 8, 8))
    paint_look_effect(paper, "paper_purple", 0.4, {"subject": "bill", "badge": False})
    corner = paper.getpixel((2, 2))
    assert corner[0] > 180 and corner[1] > 170
    samples = [paper.getpixel((x, y)) for x in range(0, 120, 6) for y in range(40, 140, 8)]
    assert any(pixel[2] > pixel[0] and pixel[2] > 140 for pixel in samples)


def test_punch_in_adds_a_short_zoom_on_a_number():
    caption = SimpleNamespace(start=2.0, end=4.0, text="Save 20 percent", translated_text="Save 20 percent")
    state = SimpleNamespace(captions=[caption])
    graphics = add_punch_ins(state, [], ["punch_in"], True)
    assert len(graphics) == 1
    assert graphics[0].template_id == "source_reframe"
    assert graphics[0].parameters["end_scale"] == 1.15
