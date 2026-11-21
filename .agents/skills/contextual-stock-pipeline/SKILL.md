---
name: contextual-stock-pipeline
description: >-
  Transcript-driven stock image/B-roll finding and overlay for DaVinci Resolve Companion.
  Use when optimizing or debugging media search, vision rerank, retrieve_asset, asset_review,
  editorial planning queries, auto-produce stock stages, or placing cutaways from captions.
---

# Contextual stock pipeline (transcript → brief → image → overlay)

Canonical reference for context-aware stock acquisition. Complements `davinci-companion`.
Cursor rule `.cursor/rules/contextual-stock-image-pipeline.mdc` is alwaysApply and points here.

## When transcription is already done

Treat captions (text + word timings + translation) as source of truth:

1. Segment into beats (`dialogue_beats` / `planning_windows`), not the whole clip.
2. Classify each beat:
   - Concrete noun/action/place → `BROLL_VIDEO` / `STOCK_IMAGE`
   - Number / emphatic phrase → kinetic / stat (no stock)
   - Abstract / greeting / credentials → `NO_INTERVENTION`
3. Write an industry visual brief: subject + action + setting + `required_entities` + `negative_constraints`.
4. Search with `retrieval_query` + up to 2 `alternate_queries`.
5. Vision-approve thumbnails **against the brief** (`stock_visual_brief` → `rerank_candidates_with_vision`, strict).
6. Overlay at word onset (`anchor_phrase` / `audio_anchor_*`), split or fullscreen.

Industry pattern: script/transcript-driven B-roll. Stock illustrates; evidence role + Wikimedia/metadata gates only when proving identity/authenticity.

## Code map

| Piece | Location |
|-------|----------|
| Visual brief | `editorial_planner.stock_visual_brief` |
| Parallel query search + claim | `editorial_planner.retrieve_asset`, `SharedUsed` |
| Parallel cue prefetch | `editorial_planner.execute_plan` (`STOCK_PARALLEL_CUES`) |
| Planner prompt (briefs required) | `editorial_planner.editorial_decisions` (`PROMPT_VERSION` v4.1) |
| Vision rerank | `media_search_service.rerank_candidates_with_vision` |
| Provider waterfall | `media_search_service.search_media` — Pexels → Pixabay → Wikimedia |
| Legacy keyword path (not auto-produce) | `generate_search_queries` / `auto_match_for_caption` |
| Feedback URLs / notes | `feedback_service.planning_feedback` → `used` + brief negatives |

## Auto-produce flow (live)

```
Whisper captions → Twelve Labs (optional) → planning_windows
  → editorial_decisions (Gemini) → schedule
  → asset_review: prefetch stock (parallel) → place overlays → 04..06 JSON

A missing Twelve Labs key does not stop this. Planning continues from the spoken captions.
```

Inspect: `backend/projects/<id>/editorial/<run>/02_editorial_decisions.json`, `04_asset_review.json`.

## Status

**P0 done:** slim brief, parallel queries, parallel cues + `SharedUsed.claim`, planner brief fields, vision scores brief.

**P1 remaining:** modality ladder (rejected video → image); merge top-N across providers before one vision call; stronger cut-reason → query rewrite.

**P2 remaining:** unify legacy `auto_match_for_caption` onto `retrieve_asset`; env knobs `VISION_RERANK_TIMEOUT`, `STOCK_CANDIDATE_LIMIT`.

## Do not

- Prefer medical keyword buckets for auto-produce queries.
- Reorder Wikimedia ahead of Pexels/Pixabay.
- Fall back to Candidate #1 under strict vision.
- Document stage as `stock_search` or vision timeout as 6s.
- Retry rejected stock with looser substitute pools that approve unrelated media.

## Env

- `STOCK_PARALLEL_CUES` — parallel stock cue workers (default 3, max 8; set 1 for serial).
- `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `GEMINI_API_KEY` / `GOOGLE_API_KEY`, `EDITORIAL_MODEL`.

## Tests

```bash
cd backend && PYTHONPATH=. python3 -m pytest tests/test_media_review_speed.py tests/test_editorial_planner.py -q
```
