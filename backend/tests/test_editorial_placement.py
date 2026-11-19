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
from app.services.feedback_service import is_live_feedback
from app.services.timeline_import import fcpxml_to_eval_records, fcp_transform_to_center_rect, import_fcpxml, write_offline_bundle


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
    xml = '<fcpxml><title ref="kinetic_typography" name="Title" offset="30/30s" duration="15/30s"/></fcpxml>'
    records = fcpxml_to_eval_records(xml, fps=30)
    assert records[0]["template_id"] == "kinetic_typography"
    assert records[0]["start_sec"] == 1.0
    assert records[0]["end_sec"] == 1.5
    assert records[0]["template_family"] == "text_title"


def test_showinfo_parser_reads_pts_time():
    assert scene_cuts_from_showinfo("n:0 pts_time:1.5\nn:1 pts_time:4") == [1.5, 4.0]


def test_live_planner_does_not_import_the_timeline_parser():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    watched = [
        "backend/app/services/auto_production_service.py",
        "backend/app/services/editorial_planner.py",
        "backend/app/main.py",
        "backend/app/api/feedback.py",
        "backend/app/api/media.py",
    ]
    for relative in watched:
        assert "timeline_import" not in (root / relative).read_text()


_FCPXML = """<?xml version="1.0" encoding="UTF-8"?>
<fcpxml version="1.9">
  <resources>
    <format id="r1" frameDuration="1001/30000s" width="1920" height="1080"/>
    <effect id="e1" name="Lower Third"/>
    <effect id="e2" name="Fancy Wipe"/>
  </resources>
  <library><event><project><sequence format="r1">
    <spine>
      <asset-clip name="Interview" offset="0s" duration="10s">
        <title ref="e1" name="Lower Third" offset="30/30s" duration="60/30s" lane="1">
          <adjust-transform position="10 12" scale="100 100"/>
          <text><text-style>Hello</text-style></text>
        </title>
        <generator ref="e2" name="Fancy Wipe" offset="4s" duration="1s" lane="1"/>
      </asset-clip>
    </spine>
  </sequence></project></event></library>
</fcpxml>
"""


def test_fcp_position_uses_frame_height_and_flips_y():
    center_x, center_y, width, height = fcp_transform_to_center_rect(10, 12, 100, 100, 1920, 1080, 0.72 * 1920, 0.16 * 1080)
    assert abs(center_x - (0.5 + 0.1 * (1080 / 1920))) < 1e-6
    assert abs(center_y - 0.38) < 1e-6
    assert abs(width - 0.72) < 1e-6
    assert abs(height - 0.16) < 1e-6


def test_offline_import_skips_the_source_clip_and_keeps_unmapped_titles():
    imported = import_fcpxml(_FCPXML, project_id="p1", features={
        "shot_cuts": [1.2],
        "detection_frames": [{"time_sec": 1.2, "detections": [{"label": "face", "preview_rect": (0.5, 0.4, 0.2, 0.2)}]}],
        "words": [
            {"word": "hello", "start_sec": 1.0, "end_sec": 1.3, "emphasis": "high"},
            {"word": "gap", "start_sec": 8.0, "end_sec": 8.2, "emphasis": "high"},
        ],
    }, shadow_suggestions=[{"start_sec": 1.0, "end_sec": 2.8, "template_id": "kinetic_typography", "screen_rect": (0.5, 0.4, 0.2, 0.2), "avoid_rects": []}])
    names = [row["name"] for row in imported["placements"]]
    assert "Interview" not in names
    assert imported["unmapped"] == ["Fancy Wipe"]
    lower = imported["placements"][0]
    assert lower["template_family"] == "text_title"
    assert lower["crosses_cut"] is True
    assert lower["avoid_rects"]
    assert lower["text"] == "Hello"
    assert imported["feedback"][0]["source"] == "fcpxml_import"
    assert imported["feedback"][0]["final_decision"] == "keep"
    assert imported["feedback"][0]["edits"] == []
    assert imported["fps"] == round(30000 / 1001, 6)
    assert imported["scorecard"]["intervention_recall"] == 1.0
    assert any(row.get("reason") == "emphasis_without_overlay" for row in imported["training_rows"])
    assert not is_live_feedback(imported["feedback"][0])


def test_local_box_math_and_sample_times():
    from app.services.local_models import head_box, map_yolo_label, sample_times, xyxy_to_center
    center = xyxy_to_center((0, 0, 100, 50), 200, 100)
    assert center == (0.25, 0.25, 0.5, 0.5)
    assert map_yolo_label("sports ball") == "ball"
    assert map_yolo_label("person") == "face"
    assert head_box((0, 0, 10, 100))[3] == 42
    assert sample_times([], 10, limit=4)[0] == 0.0


def test_visual_query_comes_from_the_spoken_line():
    from app.services.local_editorial import visual_query
    query, alternates = visual_query("Lung cancer is the commonest cancer in men")
    assert query.startswith("lung cancer")
    assert "men" in query
    assert alternates
    assert visual_query("We are starting today") == ("", [])


def test_deterministic_planner_places_a_spoken_phrase_without_gemini():
    from app.services.editorial_planner import Segment
    from app.services.local_editorial import deterministic_decisions, note_provider_failure, provider_degraded
    segment = Segment(
        id="segment-1",
        start_sec=0,
        end_sec=6,
        transcript="We are starting a discussion of lung cancer",
        semantic_summary="We are starting a discussion of lung cancer",
        dialogue_beats=[{"start_sec": 0.3, "end_sec": 2.4, "text": "discussion of lung cancer"}],
        audio_cues=[{"id": 4, "word": "कैंसर", "start": 1.1, "usable": True}],
    )
    decisions = deterministic_decisions([segment])
    placed = [item for item in decisions if item.intervene]
    assert placed
    assert placed[0].display_text == "discussion of lung cancer"
    assert placed[0].audio_anchor_word == "कैंसर"
    assert placed[0].strategy == "STOCK_IMAGE"
    assert "lung" in placed[0].asset.retrieval_query and "cancer" in placed[0].asset.retrieval_query
    note_provider_failure("gemini", 401)
    assert provider_degraded("gemini")
    note_provider_failure("gemini", 500)
    assert provider_degraded("gemini")


def test_speech_only_understanding_groups_captions():
    from types import SimpleNamespace
    from app.services.editorial_planner import normalize_segments, speech_only_understanding
    captions = [
        SimpleNamespace(start=0.0, end=3.0, text="We are starting a", translated_text="We are starting a", id="a"),
        SimpleNamespace(start=3.0, end=9.0, text="discussion of lung cancer", translated_text="discussion of lung cancer", id="b"),
    ]
    raw = speech_only_understanding(captions, 12.0, window=8.0)
    segments = normalize_segments(raw, captions, 12.0)
    assert segments
    assert segments[0].observations == []
    assert "speech only" in segments[0].understanding_warnings[0]


def test_a_section_note_is_reused_for_a_similar_line():
    from app.services.domain_knowledge import match_example, remember
    remember({
        "domain_profile": "medical",
        "decision": "swap",
        "graphic_type": "split_screen_vertical",
        "project_id": "lung",
        "editor_notes": "show a chest x-ray on a lightbox",
        "transcript_context": "Lung cancer is the commonest cancer in men",
        "search_query": "chest xray lightbox",
        "selected_asset": {"url": "https://images.example/xray.jpg", "title": "Chest x-ray"},
    })
    hit = match_example("medical", "The commonest cancer in men is lung cancer")
    assert hit is not None
    assert hit["query"] == "chest xray lightbox"
    assert match_example("sports", "The commonest cancer in men is lung cancer") is None


def test_a_new_project_keeps_its_field_and_captions_keep_the_phrase():
    from app.core.database import init_db
    from app.services.project_manager import project_manager
    from app.services.transcription_service import TranscriptionService, caption_prompt
    init_db()
    medical = project_manager.create_project("Clinic", "9:16", domain_profile="medical")
    assert medical.settings.domain_profile == "medical"
    other = project_manager.create_project("Notes", domain_profile="cooking")
    assert other.settings.domain_profile == "general"
    words = [
        {"word": "Lung", "start": 0.0, "end": 0.3},
        {"word": "cancer", "start": 0.32, "end": 0.7},
        {"word": "is", "start": 0.72, "end": 0.9},
        {"word": "the", "start": 0.92, "end": 1.05},
        {"word": "commonest", "start": 1.08, "end": 1.5},
        {"word": "cancer", "start": 1.52, "end": 1.9},
        {"word": "in", "start": 1.92, "end": 2.05},
        {"word": "men.", "start": 2.08, "end": 2.4},
    ]
    phrases = TranscriptionService().chunk_spoken_phrases(words)
    assert len(phrases) == 1
    assert len(phrases[0]) == 8
    paused = words + [{"word": "Treatment", "start": 3.2, "end": 3.6}, {"word": "starts", "start": 3.62, "end": 4.0}]
    assert len(TranscriptionService().chunk_spoken_phrases(paused)) == 2
    assert "cancer" in caption_prompt("medical").lower()
    assert "goal" in caption_prompt("sports").lower()


def test_the_local_planner_defaults_to_qwen_3b(monkeypatch):
    from app.services.local_models import qwen_minimum_mib, qwen_model_name
    monkeypatch.delenv("QWEN_MODEL", raising=False)
    assert qwen_model_name() == "Qwen/Qwen2.5-3B-Instruct"
    assert qwen_minimum_mib() == 4000
    monkeypatch.setenv("QWEN_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    assert qwen_minimum_mib() == 7000


def test_qwen_skips_when_the_gpu_has_no_room_and_the_edit_continues(monkeypatch):
    from app.services.local_models import clear_planner_skip, planner_skip_reason, qwen_json
    loaded = {}

    def refuse_load():
        loaded["called"] = True
        raise AssertionError("Qwen must not load when the GPU is already full")

    monkeypatch.setattr("app.services.local_models.release_for_planner", lambda: None)
    monkeypatch.setattr("app.services.local_models._qwen_fits", lambda: False)
    monkeypatch.setattr("app.services.local_models._qwen", refuse_load)
    clear_planner_skip()
    assert qwen_json("plan this") is None
    assert "called" not in loaded
    assert "spoken lines" in planner_skip_reason()

    def out_of_memory():
        raise RuntimeError("CUDA out of memory. Tried to allocate 34.00 MiB.")

    monkeypatch.setattr("app.services.local_models._qwen_fits", lambda: True)
    monkeypatch.setattr("app.services.local_models._qwen", out_of_memory)
    monkeypatch.setattr("app.services.local_models.release_planner", lambda: None)
    assert qwen_json("plan this") is None
    assert "out of GPU memory" in planner_skip_reason()


def test_a_missing_ffmpeg_path_falls_back_to_a_real_binary(monkeypatch):
    from pathlib import Path
    from app.core.config import resolve_ffmpeg_bin
    monkeypatch.setenv("FFMPEG_BIN", "/home/developer/oonex/missing-ffmpeg")
    found = resolve_ffmpeg_bin()
    assert Path(found).is_file()
    assert found != "/home/developer/oonex/missing-ffmpeg"


def test_a_transcription_correction_is_reused_for_the_picture_search():
    from app.services.domain_knowledge import match_transcript, remember_transcript
    from app.services.editorial_planner import Segment
    from app.services.local_editorial import deterministic_decisions
    from app.services.local_models import usable_picture_index
    remember_transcript({
        "domain_profile": "medical",
        "project_id": "lung",
        "heard": "you fuck all",
        "correction": "chest xray scan",
        "issue": "wrong_words",
        "note": "misheard diagnosis",
        "start_sec": 30.38,
        "end_sec": 31.98,
    })
    hit = match_transcript("medical", "you fuck all the cases")
    assert hit is not None
    assert hit["correction"] == "chest xray scan"
    assert match_transcript("sports", "you fuck all the cases") is None
    segment = Segment(
        id="segment-1",
        start_sec=30,
        end_sec=36,
        transcript="you fuck all",
        semantic_summary="you fuck all",
        dialogue_beats=[{"start_sec": 30.2, "end_sec": 32.0, "text": "you fuck all", "emphasis": "high"}],
        audio_cues=[{"id": 9, "word": "all", "start": 31.0, "usable": True}],
    )
    placed = [item for item in deterministic_decisions([segment], {"domain": {"domain": "medical"}}) if item.intervene]
    assert placed
    assert placed[0].anchor_phrase == "you fuck all"
    assert "chest" in placed[0].asset.retrieval_query and "xray" in placed[0].asset.retrieval_query
    assert usable_picture_index({"shot_captions": [], "detection_frames": []}) is False
    assert usable_picture_index({"shot_captions": [{"time_sec": 0, "caption": "a doctor"}]})


def test_domain_memory_stays_inside_its_field():
    from app.services.domain_knowledge import for_planner, remember, same_domain
    remember({"domain_profile": "medical", "decision": "cut", "graphic_type": "stat_counter", "editor_notes": "do not cover the incision", "project_id": "lung"})
    remember({"domain_profile": "sports", "decision": "keep", "graphic_type": "youtube_insert", "editor_notes": "show the ball", "project_id": "match"})
    medical = for_planner("medical")
    assert "instrument" in medical["avoid_classes"]
    assert medical["notes"][0]["note"] == "do not cover the incision"
    assert all("ball" not in note["note"] for note in medical["notes"])
    assert same_domain({}, "general")
    assert not same_domain({}, "medical")


def test_offline_bundle_does_not_write_live_feedback(tmp_path):
    imported = import_fcpxml(_FCPXML)
    written = write_offline_bundle(imported, tmp_path)
    assert "editorial_feedback.json" not in " ".join(written.values())
    assert (tmp_path / "fcpxml_feedback.json").is_file()
    assert (tmp_path / "training_export.json").is_file()
    assert not (tmp_path / "scorecard_baseline.json").exists()
