"""Placement math: clamp, preview transform, snap, slots, scorecard, offline import."""

from types import SimpleNamespace

from app.services.editorial_features import scene_cuts_from_showinfo
from app.services.editorial_placement import (
    annotate_emphasis,
    effective_scale,
    find_next_free_slot,
    interval_avoid_rects,
    place_decision,
    quantize_incoming_frame,
    sample_hard_negatives,
    score_placement,
    snap_interval,
    visible_preview_rect,
)
from app.services.timeline_import import fcpxml_to_eval_records


def test_preview_transform_drops_mostly_offscreen_face():
    # A face on the far left is cropped away by a right-side reframe.
    kept = visible_preview_rect((0.9, 0.4, 0.15, 0.2), crop=(0.7, 0.5, 0.4, 0.8), zoom=1.0)
    dropped = visible_preview_rect((0.05, 0.4, 0.1, 0.2), crop=(0.7, 0.5, 0.4, 0.8), zoom=1.0)
    assert kept is not None
    assert dropped is None


def test_incoming_frame_stays_on_an_exact_cut():
    assert quantize_incoming_frame(1.0, 30) == 1.0
    assert quantize_incoming_frame(1.0004, 30) == 1.0


def test_snap_marks_a_cut_crossing_and_prefers_the_word_inside_the_shot():
    snapped = snap_interval(1.05, 2.2, cuts=[1.0, 2.0], gaps=[2.15], word_start=1.08, fps=30)
    assert snapped["start_snap"] == "word_start"
    assert snapped["start_sec"] == 1.08
    assert snapped["crosses_cut"] is True
    assert snapped["end_snap"] == "shot_cut_next_frame"


def test_wide_graphic_has_no_slot_and_a_clear_cell_is_clamped_inside_reels():
    assert find_next_free_slot((0.5, 0.5, 0.95, 0.2), [], "reels") is None
    slot = find_next_free_slot((0.5, 0.5, 0.2, 0.12), [(0.5, 0.45, 0.3, 0.3)], "reels")
    assert slot is not None
    center_x, center_y, width, height = slot
    assert center_x - width / 2 >= 0.04 - 1e-6
    assert center_x + width / 2 <= 0.86 + 1e-6
    assert center_y - height / 2 >= 0.12 - 1e-6


def test_interval_envelope_unions_motion_and_ignores_other_domains():
    frames = [
        {"time_sec": 1.0, "detections": [{"label": "face", "preview_rect": (0.4, 0.4, 0.2, 0.2)}]},
        {"time_sec": 2.4, "detections": [{"label": "face", "preview_rect": (0.55, 0.45, 0.2, 0.2)}]},
        {"time_sec": 1.2, "detections": [{"label": "ball", "preview_rect": (0.1, 0.1, 0.2, 0.2)}]},
    ]
    rects = interval_avoid_rects(frames, 1.0, 2.0, "general")
    assert len(rects) == 1
    assert rects[0][2] > 0.3
    assert len(interval_avoid_rects(frames, 1.0, 2.0, "sports")) == 2


def test_emphasis_ignores_energy_outside_the_word():
    words = [
        {"word": "twelve", "start_sec": 1.0, "end_sec": 1.2},
        {"word": "and", "start_sec": 1.4, "end_sec": 1.6},
    ]
    samples = [(1.1, 0.9), (1.5, 0.2), (0.2, 5.0)]
    marked = annotate_emphasis(words, samples)
    assert marked[0]["emphasis"] == "high"


def test_scale_cannot_exceed_the_box():
    assert effective_scale(2.0, (0.5, 0.5, 0.4, 0.2), (1000, 1000), (500, 400)) == 0.5


def test_scorecard_counts_family_and_recall():
    suggestions = [
        {"start_sec": 0, "end_sec": 2, "template_id": "stat_counter", "screen_rect": (0.5, 0.5, 0.2, 0.2), "avoid_rects": [(0.5, 0.5, 0.2, 0.2)]},
        {"start_sec": 5, "end_sec": 6, "template_id": "youtube_insert", "screen_rect": (0.2, 0.2, 0.1, 0.1), "avoid_rects": []},
    ]
    human = [{"start_sec": 0.2, "end_sec": 1.8, "template_id": "dimension_callout"}]
    score = score_placement(suggestions, human)
    assert score["family_template_match"] == 1.0
    assert score["exact_template_match"] == 0.0
    assert score["avoid_collision_rate"] == 0.5
    assert score["intervention_recall"] == 1.0
    assert score["intervention_precision"] == 0.5


def test_hard_negatives_keep_a_bounded_ratio():
    rows = [{"intervene": True, "human": "keep"}]
    rows += [{"intervene": False, "human": "left_clear", "hard": True, "id": i} for i in range(6)]
    rows += [{"intervene": False, "human": "left_clear", "hard": False}]
    exported = sample_hard_negatives(rows, ratio=2)
    assert sum(1 for row in exported if row.get("intervene")) == 1
    assert sum(1 for row in exported if not row.get("intervene")) == 2


def test_place_decision_writes_center_rect_and_snaps_off_the_cut():
    state = SimpleNamespace(settings=SimpleNamespace(aspect_ratio="9:16", brand_preset="documentary_minimalist", domain_profile="general"), fps=30, captions=[], ai_ingestion={"shot_cuts": [1.0], "detection_frames": []})
    row = {"start_sec": 1.05, "end_sec": 1.8, "composition": {"layout": "text_overlay", "position": [0.5, 0.4]}, "anchor_phrase": ""}
    graphic = SimpleNamespace(template_id="kinetic_typography", start=1.05, end=1.8, pos_x=0.5, pos_y=0.5, parameters={})
    placement = place_decision(row, graphic, state)
    assert placement["start_snap"] == "shot_cut_next_frame"
    assert graphic.pos_x == placement["screen_rect"][0]
    assert graphic.parameters["screen_rect"][0] == graphic.pos_x
    assert graphic.parameters["max_scale"] == 1.0


def test_fcpxml_import_is_eval_records_only():
    xml = '<fcpxml><asset-clip ref="kinetic_typography" name="Title" offset="30/30s" duration="15/30s"/></fcpxml>'
    records = fcpxml_to_eval_records(xml, fps=30)
    assert records == [{"template_id": "kinetic_typography", "start_sec": 1.0, "end_sec": 1.5, "name": "Title"}]


def test_showinfo_parser_reads_pts_time():
    assert scene_cuts_from_showinfo("n:0 pts_time:1.5\nn:1 pts_time:4") == [1.5, 4.0]


def test_live_planner_does_not_import_the_timeline_parser():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    source = (root / "backend/app/services/auto_production_service.py").read_text()
    planner = (root / "backend/app/services/editorial_planner.py").read_text()
    assert "timeline_import" not in source
    assert "timeline_import" not in planner
