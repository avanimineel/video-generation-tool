# 113.mov understanding-layer cloud test — 2 October 2026

User explicitly approved sending 113.mov to Twelve Labs and its transcript/analysis to Gemini. This is a read-only reference test, not regeneration of the current timeline.

## Verified result

Final run: `20261002T132109-db0c8593`, status `review_ready`, no pipeline errors. Twelve Labs returned 11 semantic sections; Gemini returned 30 editorial decisions. These are proposals, not 30 inserted graphics. The project remains identical to its pre-test snapshot: 109 captions and 14 existing graphics.

The analysis identified the split-screen opening, both article-card sections, medicine B-roll, QR demonstration, TEST emphasis and a distinct branded ending. Gemini identified identity, evidence, illustration, emphasis, checklist, demonstration, CTA, outro and presenter roles. The source-specific guard rejected generic stock as a substitute for a named person or evidence. Existing article/QR/CTA/outro treatments marked preserve were not scheduled as duplicates.

## Quality limitations found by comparison with local frame review

- Twelve Labs described milk/food-adulteration footage at 80–85 seconds. The earlier sampled frame review shows person/context imagery there; treat that description as unverified, not a learned reference fact.
- It described 96–106 seconds as emphasis text rather than identifying the accumulating three-item checklist specifically.
- It missed the distinct precious-treatment-time emphasis and gave coarse B-roll timings. Exact timing is not verified.
- Gemini still proposed extra illustrative treatments despite this being a finished reference. The reference-hash upload guard and read-only review mode protect this project, but the proposals are not a gold-standard edit plan.
- Several proposals failed scheduling because of duration, topic boundaries or spoken-anchor mismatch. Checklist and branded-outro reproduction remain incomplete renderer capabilities.
- The overall audit correctly reports `complete_finished_reel: false`.

## Repairs made during testing

Known provider observation-kind aliases (for example broll → scene) are normalized, while unknown kinds remain invalid. The prompt now requests compact complete JSON with explicit existing-treatment labels and distinct ending observations, avoiding duplicated transcript output. The cache schema is updated so older analysis lacking those fields is not silently reused. Invalid observation intervals remain rejected; diagnostics now include the offending interval and preserve raw provider output for inspection before cache acceptance. No timestamp validation was weakened to force success.

Earlier attempts exposed an unknown observation label, incomplete responses and an invalid interval. The final successful response passed strict interval and transcript-coverage checks. This demonstrates an operational provider chain, not consistently accurate visual understanding.

Validation: 52 focused backend tests passed. Final result displayed in the live Understanding panel. No new MP4 was rendered by this test.
