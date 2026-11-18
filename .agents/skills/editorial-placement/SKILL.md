---
name: editorial-placement
description: >-
  Deterministic safe placement for editorial graphics. Use when changing cue
  timing, screen position, safe zones, avoid boxes, keep/cut/swap telemetry,
  the placement scorecard, or the offline timeline importer.
---

# Editorial placement

Place graphics with measured picture and audio features, then a deterministic snap. Do not fine-tune a video model until the scorecard has been run on real edits. Do not import FCPXML or Resolve timelines into the live planner.

## Order

1. Feature JSON. Shot cuts, Whisper word gaps, speech RMS emphasis, and preview-space avoid boxes.
2. Union safe zone for the cue interval, then snap, then a 3×3 slot.
3. Four-metric scorecard on finished edits.
4. A fine-tune only after that scorecard exists. It is not part of this module.

When Gemini or Twelve Labs returns 401 or 403, mark that provider degraded in `provider_health.json` and do not keep retrying it. Picture indexing then uses ffmpeg shot cuts, YOLO11n avoid boxes, Florence-2 captions, and SigLIP embeddings from `local_models.py`. Planning tries in-process Qwen2.5-7B, then `LOCAL_PLANNER_URL`, then the deterministic spoken-title planner. Weights stay in the Hugging Face cache and `/data/developer/oonex/models/yolo11n.pt`. One GPU model is loaded at a time.

`timeline_import.py` is an offline CLI. It parses FCPXML, converts center-origin positions into `screen_rect`, maps generator names onto the four families, and attaches shot cuts and avoid boxes supplied from the feature probes. It writes `fcpxml_placements.json`, `fcpxml_feedback.json`, `training_export.json`, and, when a separate shadow plan is passed, `scorecard_baseline.json`. Those rows use `source: fcpxml_import`. The live feedback endpoint rejects that source, and `planning_feedback` ignores it.

`auto_production_service.py`, `editorial_planner.py`, and the API routers must not import `timeline_import`. Run it as `python -m app.services.timeline_import timeline.fcpxml --out <dir>`. Unmapped generator names stay in the export with `unmapped: true`.

## Contracts

- `screen_rect` is `[center_x, center_y, w, h]` in 0–1 preview space. `pos_x` and `pos_y` are that center.
- Clamp the center so `center - size/2` stays inside `safe_bounds` before the collision test. If the graphic is larger than the safe bounds, there is no slot.
- Preview transform order: reframe crop, zoom about the center, pan, then drop a box whose remaining area inside the frame is under 10% of its area.
- `cut_sec` is the first frame of the incoming shot. Snap with `round(cut_sec * fps) / fps`. Do not use `ceil`.
- The canvas box is `w` by `h` of the frame, centered, `overflow: hidden`. Painted scale is `min(user_scale, auto_fit)`.
- Avoid outlines draw only while a graphic is selected and playback is paused, and only for boxes near that graphic or touching it.
- Feedback keeps one row per cue and appends `edits`. `editor_notes` is human text. A geometric hint is not a confirmed reason.
- Review stores every `intervene: false` cue. The training export samples hard negatives at about 2.5 per kept graphic.
- Batch-accept applies only to cues whose placement is `clear` (no avoid hit, no raw cut crossing).

## Code

| Piece | Location |
| --- | --- |
| Snap, envelope, slot, scorecard | `backend/app/services/editorial_placement.py` |
| Shot-cut and RMS probes | `backend/app/services/editorial_features.py` |
| Live stamp onto a graphic | `editorial_planner.execute_plan` → `place_decision` |
| Append-only edits | `feedback_service.record_decision` |
| Offline FCPXML import | `python -m app.services.timeline_import` |
| Preview clamp and avoid outlines | `frontend/src/components/viewer/CanvasOverlay.tsx` |
| Next slot and accept-clear | `frontend/src/services/safePlacement.ts`, `EditorialPlanPanel.tsx` |

Domain classes are `general` (face, hand), `medical` (plus instrument), and `sports` (plus ball). A project's `settings.domain_profile` selects the class. Each live keep, cut, or swap is filed in `domain_knowledge/<domain>.json`. The next video in that field receives those counts and notes. Other fields do not. Rows with no domain stay in `general`. This is editing memory, not a fine-tune.

Template families are `text_title`, `callout`, `split_broll`, and `article_card`. Family match and exact match are both reported.
