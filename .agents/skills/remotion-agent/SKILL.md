---
name: remotion-agent
description: >-
  Render a short-form timeline with Remotion from the composition written by the
  short-form pipeline. Use when asked to add a Remotion render, read remotion_composition.json,
  or change how story, captions, and overlays become a 9:16 React composition.
---

# Remotion agent

The pipeline already decides the story and the overlays. Remotion only draws that decision. The spoken captions stay the words. FFmpeg burn-in remains the export that ships today. Remotion reads the same composition so a second renderer cannot invent a different edit.

Read this skill before adding a Remotion project, a composition component, or a render script.

Before writing any Remotion component, also read the official Remotion skills installed from `remotion-dev/skills`:

- `.agents/skills/remotion-markup/timing.md` for motion. Drive every value with `interpolate()` over an explicit frame range. Ease with `Easing.spring` or `Easing.bezier`, and clamp both sides. Do not invent a CSS animation or a custom spring.
- `.agents/skills/remotion-captions/SKILL.md` and `display-captions.md` for captions. Use the `@remotion/captions` `Caption` type (`text`, `startMs`, `endMs`, `timestampMs`). Word timing comes from that file, not from a guessed delay.
- `.agents/skills/remotion-best-practices/SKILL.md` when the task is broader than timing or captions.

## Where the composition comes from

`backend/app/services/shortform_pipeline.py` writes `remotion_composition.json` next to the editorial run, and a copy of the story on the project under `ai_ingestion.shortform`.

The story agent builds that file from captions:

- Each spoken line is tagged hook, claim, proof, story, or cta.
- Viral inferences are patterns already in the line: a specific number, an open question, a contrast, a direct address, or stakes. The agent records the pattern and the line. It does not write a new sentence.
- The spine copies one spoken line into hook, claim, proof, story, and CTA. A missing role stays empty.

## Composition fields

- `fps` is 30. `width` 1080. `height` 1920.
- `durationInFrames` is the video length at 30 fps.
- `stylePack` is `direct_response`, `documentary`, or `explainer`. One pack for the whole video.
- `story` is the spine. Render those strings only if they also appear in the captions.
- `tracks[]` has `id`, `template`, `from`, `durationInFrames`, `effect`, and `title`. Frame math is `from = round(start * 30)`.

## Draw rules

- One React component per `template`. `look_effect` switches on `effect`.
- Captions sit above the bottom 18 percent. Cards stay out of the top 12 percent and the bottom 18 percent.
- Do not render the word LIVE. A streaming track is a frame and a lower bar.
- Punch-in scale eases from 1.0 to 1.15. Paper-craft and scrapbook step at 12 fps inside the 30 fps composition.
- Fog, rain, confetti, and light leak prefer an alpha clip. A missing licensed clip uses the procedural layer already in the preview.
- Sound stays on the FFmpeg mix. Remotion does not add a second sound bed.

## Do not

- Generate a new script, a new number, or a new place inside Remotion.
- Reorder tracks to chase retention. The density agent already applied the 700 ms gap and the punch-in cap.
- Start a Remotion render from the website brand script. That script is a different film. This composition is the captioned video.
