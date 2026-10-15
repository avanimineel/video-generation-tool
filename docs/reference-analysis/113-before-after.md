# What a finished reel needs: sub.mov → 113.mov

The user identified `sub.mov` as before and `113.mov` as after. This comparison uses local frame inspection: samples every four seconds across both videos, and selected one-second detail samples in the finished video. It is not a frame-accurate edit list. Music, sound effects and exact animation curves were not assessed.

Both files are portrait 1080×1920, 30 fps. Before is 121.32 seconds; after is 122.83 seconds. A coarse audio-envelope comparison peaks at zero offset with correlation 0.978, supporting approximate correspondence of the spoken timeline, but not exact word alignment. Opening images differ substantially; the before already contains some introductory imagery. Do not interpret it as an entirely untouched camera original.

The main difference is editorial purpose and composition, not simply more overlays. The finished video alternates the presenter with a visual that answers the current audience question. Some presenter passages remain uninterrupted for several seconds. Article cards persist for reading, unlike the old universal one-second limit.

| Approximate after time | Observed treatment | Understanding requirement |
|---|---|---|
| 0–9s | Named-person imagery above presenter; larger opening name text | Identify the named person and use a verified identity asset. A generic stock person is wrong. |
| 12–15s | Full-screen contextual medicine imagery | Illustrate the topic without presenting generic imagery as proof of the specific incident. |
| 16–21s | Medical canvas, publisher masthead, article title/body, yellow highlight | Find the correct article and supporting passage; retain attribution and enough reading time. |
| 24–36s | Presenter with small phrase captions | Let the explanation carry the scene when additional visuals add little. |
| 39–42s | Pills followed by medicine vials | Show concrete objects corresponding to the changing spoken concepts. |
| 44–46s | Contextual imagery above presenter | Keep face and illustration visible together; distinguish a conceptual crime illustration from actual evidence. |
| 53–55s | Closer framing and large yellow key phrase | Emphasis typography is separate from subtitles, uses few words and stays legible. |
| 69–73s | Second article on a consistent medical canvas | Reuse design, not facts; retrieve the source for the new claim. |
| 80–95s | Mix of presenter, person imagery and contextual cutaways/split screens | Select identity versus illustration explicitly; preserve context and action. |
| 100–106s | Numbered verification steps accumulate over presenter | Use a real progressive checklist, retaining earlier steps as later ones arrive. |
| 108–110s | Phone/QR-code demonstration | The asset must depict the action and target object together. |
| 112–115s | Large comment-keyword CTA | Derive the exact call to action from this video's speech. Do not reuse the reference keyword elsewhere. |
| 121–122.83s | Portrait, medical background and social handle | Closing needs supplied branding and a dedicated end-card treatment. |

Ordinary subtitles in the after use short yellow phrases on green contrast blocks, while the opening hook, key emphasis, checklist and CTA have their own hierarchy. A finished-reel planner must distinguish these layers. Copying a whole sentence into a huge subtitle card does not satisfy a checklist, evidence or identity requirement.

## Implemented understanding changes

- A versioned reference profile stores observed examples, requirements, source hashes and analysis limits.
- Every semantic section gets a finished-reel brief: meaning, existing picture/treatments, uncertainty and questions to answer before selecting assets.
- Planner decisions now distinguish viewer need, visual role, treatment of existing edits and source requirement.
- Generic stock cannot satisfy an identity/evidence requirement. Adequate existing treatments must not receive duplicate overlays.
- Checklists and branded outros remain named requirements when their renderer/assets are unavailable; they are not silently converted into oversized text.
- Reports audit unresolved requirements separately from inserted visuals. Insert count alone never certifies a finished reel.
- The exact after-video hash is recognised as a finished reference and protected from automatic raw-video processing. Other files are not classified by filename alone.
- The Understanding panel displays this reference comparison locally, plus per-video briefs and gaps when analysis runs.

## Limits

This is reference-informed planning, not model training or full style replication. A dedicated checklist/outro renderer and verified source acquisition remain separate implementation needs. No claim is made that the current renderer can reproduce every observed treatment. The supplied files and current saved timeline were not replaced by this work.

[Before contact sheet](sub-sheet.jpg) · [After contact sheet](113-sheet.jpg) · [After detail samples](after-detail.jpg)
