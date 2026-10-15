## 2026-09-24 — Understanding and editorial intelligence update

The attachment-driven changes are implemented in editorial_planner.py, twelve_labs_service.py and understanding_jobs.py, with UnderstandingReview.tsx in the editor toolbar. Twelve Labs returns semantic sections with timed visual observations, entities/concepts, speaker claims (explicitly unverified), narrative roles and uncertainties. Caption IDs and timing provenance link meaning to the saved transcript. Near caption boundaries are snapped within 80ms to avoid duplicated neighboring dialogue.

Gemini planning now receives uncertainty, editorial need, alternative treatments, comprehension time and full semantic context. The scheduler grounds repeated phrases near the requested occurrence, rejects invented anchors, computes rolling state at the actual intervention time, prevents stock from being used as proof, and rejects low-confidence/redundant interventions. Removed add_retention_motion and its fixed three-second zoom/fragment overrides; NO_INTERVENTION is now respected through execution. No global effect-count cap was added.

POST/GET /api/media/{project_id}/understanding-review creates a read-only understanding/planning report in projects/{id}/understanding/{run-id}. It never downloads assets or saves a timeline. The original upload path uses the upgraded planner. The UI exposes meaning, visual observations, unverified claims, uncertainties, decisions, timing and raw JSON. Unsupported advanced treatments remain proposals needing a source/renderer, not completed visuals.

Successful validated understanding is cached by video contents, transcript, duration and schema version in semantic_cache. Planning failures can retry without repeating successful video analysis. Existing historical runs are reused only if their revision/transcript match and source has not changed. Job status preserves the current report stage.

34 focused regression tests passed on Sep 24; frontend production build passed on Sep 23 after the new panel was added. Prior real run produced seven semantic sections and seven visual observations/uncertainties; Gemini then returned HTTP 503 for all three configured models. Sep 24 live verification completed successfully: six semantic sections, six editorial decisions, no provider errors, status review_ready. One typography treatment planned; five decisions retained the speaker (including unreadable-duration rejections). Video understanding cache written. Saved project revision unchanged, with 76 captions and 39 graphics preserved. No media downloads or timeline changes were made by this analysis. The completed report was verified in the live Understanding panel.


> **Verified 2026-09-23:** 21 regression tests; frontend build; live downloaded B-roll playback; H.264/AAC 720×1280 sample export, successful decode and visual frame review. Full-video export/Resolve transfer remain unverified.

> **2026-09-23 automatic-upload update (current):** The backend starts an automatic-edit job after upload; the browser polls it and reconnects to a running job on reload. Closing the browser does not cancel work. A backend restart marks unfinished jobs interrupted, requiring resume. Upload replacement preserves the previous project snapshot and original media under a unique filename. Generated captions are checkpointed before cloud visual planning. Autosave rejects stale revisions and all browser saves are blocked while a job owns the project. The frontend suppresses autosave during processing and updates server revisions after successful saves.
>
> Current user project: `new_1790101050`, name `111sub`, about 88 seconds. Its recovered verified timeline has **76 English subtitle blocks, 6 locally downloaded Pexels video clips, 6 typography highlights, and 27 source-camera movements**. Full snapshots are in its `recovery/` folder, including `verified-complete-edit.json`. Inspect latest state before applying edits. The real run completed Twelve Labs understanding, Gemini planning, strict visual review, and local downloads. Two unsuitable asset requests were rejected; no fabricated evidence replaced them.
>
> Dense mode removes total/repetition count caps; adjacent edits are allowed. Supplemental camera beats follow speech at three-second intervals; keyword punches quote transcript text and avoid other overlays. Preview camera and cutaway timing follow the playhead. Caption overlay coordinates now scale with preview width. Translation handles Roman-script Hinglish through the configured Gemini model; translated word times are estimates, not forced alignment. New uploads default to local Whisper small. Semantic grounding uses translated text consistently.
>
> Automatic report/article reconstruction and several advanced treatments still require verified sources/renderers; they are recorded as needing review rather than invented. Full Resolve transfer is not verified. Local and cloud processing takes time after upload; it is not instantaneous. The renderer now uses a project-local imageio-ffmpeg binary, tries VideoToolbox, and falls back to software H.264 when hardware encoding is unavailable. Install the portable runtime with `python3 -m pip install --target backend/vendor_runtime -r backend/requirements-runtime.txt`.

> **Credential update (2026-09-22):** The user supplied a working Gemini key; it was saved only to `backend/.env` and validated by HTTP 200 model listing and a successful structured-generation call. Google rejected `gemini-2.5-flash` for this new account (HTTP 404), directing it to `gemini-3.6-flash`. `EDITORIAL_MODEL=gemini-3.6-flash` now controls both the planner and vision reviewer. Two synthetic-image vision checks returned HTTP 503 high demand; live visual review and full video production remain unverified. The earlier placeholder-key blocker below is historical and resolved.

# Editorial planner implementation — 2026-09-22

## Entry points

Uploading a video invokes the staged planner through the existing auto-produce endpoint. The **Review automatic edit** button opens the new decision panel. **Plan visuals for this video** reruns planning while retaining existing captions and manual graphics. Existing auto-generated items from older versions are treated as manual because they have no reliable ownership marker.

The pipeline is now:

1. Preserve an existing transcript, or transcribe and translate a new upload. A transcription failure no longer produces placeholder speech.
2. Twelve Labs returns observations about the complete semantic timeline, not graphic recommendations. Segments contain meaning, entities, claims, narrative role, visible evidence and confidence. Spoken-content coverage and intervals are validated.
3. A separate Gemini request chooses intervention/no intervention, visual intent, treatment, asset description, negative constraints, scores and composition.
4. A deterministic scheduler grounds exact phrases in word timestamps when possible, applies adaptive readable durations, protects existing graphics, and limits repetition, density and excessive full-screen coverage.
5. Pexels → Pixabay → Wikimedia candidate retrieval. Each provider is actually tried before the next. Gemini reviews the full intent/asset description and may reject every candidate. A model error, missing key, unreadable thumbnail or low-confidence selection does not mean “use hit one”.
6. Chosen assets are saved locally through the existing downloader. The supported renderer creates editable timeline objects with retained provenance.
7. Before applying, compare the project update timestamp with the starting state. Concurrent changes leave the results on disk for review instead of overwriting the project. A per-process lock prevents concurrent automatic-edit runs.

## Inspectable artifacts

`backend/projects/<project-id>/editorial/<run-id>/` contains:

- `00_transcript.json`
- `01_understanding_raw.json` and `01_semantic_timeline.json`
- `02_editorial_decisions.json`
- `03_schedule.json`
- `04_asset_review.json` when stock retrieval runs
- `05_placement.json` and `06_timeline.json`
- `report.json`

`editorial/latest.json` supplies live stage/status. `GET /api/media/{project_id}/editorial-report` returns the report and available intermediate stages. The UI displays readable reasons plus expandable JSON. Pre-run recovery snapshots are under `recovery/before-auto-<id>.json`.

## Capability boundaries

Automatic execution currently supports B-roll video, stock images and exact-excerpt kinetic typography. Full-screen/split media uses existing renderers; typography was added to the burn-in overlay dispatcher. Original composition suggestions and realized composition are recorded separately. Overlay/PIP suggestions currently realize as the existing split-screen treatment; arbitrary composition/transition instructions are not claimed as implemented.

The planning schema can propose other treatments, including charts, diagrams, web/product screenshots, article/social-post reconstruction, maps, timelines, generated visuals and source reframing. They remain explicit `needs_source_or_renderer` items until a verified source and an appropriate execution adapter exist. The system does not invent research publishers, URLs, study quotations or chart data to make those items appear complete.

The rolling state describes planned interventions; failed later asset retrieval may leave more speaker time than estimated. Models can still misunderstand a scene. This is not a learned personalized editor, and no raw feedback ledger is injected into prompts automatically.

## Configuration and verification

The backend environment is authoritative; the root environment supplies fallback names. Keys remain server-side. Existing configured credentials were preserved. Environment files have owner-only permissions, and literal key values were removed from three documentation files.

Read-only live checks on 2026-09-22: Pexels HTTP 200; Pixabay HTTP 200; Twelve Labs index listing HTTP 200. **Gemini is configured with a test placeholder.** A real Gemini key is still required for cloud editorial planning and asset review. No user video was uploaded and no paid generation was run during this verification.

Validation: 15 focused planner tests plus existing health and project lifecycle tests, all 17 passing. Production frontend build passed using `npm run build -- --configLoader native` (the installed node_modules is a symlink outside the project, so the standard Vite config bundler cannot write its temporary file within the granted filesystem scope). The new panel was opened and checked in the live UI.

Cloud editorial quality on a real video remains unverified until Gemini is configured. Mocked stage tests verify software behavior, not semantic quality. Full MP4 export of a real generated edit was not run; the typography renderer received a focused drawing test.

Official API references checked during implementation:
- https://ai.google.dev/gemini-api/docs/generate-content/structured-output
- https://docs.twelvelabs.io/sdk-reference/python/analyze-videos/sync-analysis
