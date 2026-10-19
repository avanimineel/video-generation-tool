# Studio film format (film.json)

A film is one JSON document. The Studio editor shows every field as an editable control, and the engine
draws the film from it at any moment, so everything you write stays editable. Write only JSON fields
described here; no HTML, CSS or code.

## The idea: one canvas, a camera, blocks

Do not build slides. A film is a single large canvas. Each **block** is a section of the film (hook, what
they do, proof, call to action...) with its own spot on the canvas (`origin`). The **camera** flies between
blocks, pushes in, drifts and rotates, so the viewer travels through one space instead of watching cuts.
Layers sit on the canvas at a **depth**: 1 moves with the canvas, 0 stays fixed on the screen, values in
between give parallax (0.3 for far stars, 1.4 for near foreground). A good film keeps the camera moving
gently even inside a block, overlaps entrances, and hands each block to the next with motion.

Screen sizes: 16:9 is 1920 x 1080, 9:16 is 1080 x 1920, 1:1 is 1080 x 1080. A layer's `x`/`y` is measured
inside its block like an ordinary screen: with the camera on that block (`{"block": "proof"}`), a layer at
x 960, y 540 is in the middle of the screen (16:9). Place blocks far enough apart that they do not overlap,
for example origins x 0, 2600, 5200 or diagonal steps like {x: 2400, y: -900}.

## Top level

```json
{
  "title": "Brand: concept",
  "aspect": "16:9",
  "duration": 24,
  "brand": {"colors": {"background": "#0b0b0d", "text": "#ffffff", "accent": "#ff8a2a", "muted": "rgba(255,255,255,.6)"},
            "fonts": {"heading": "Inter", "body": "Inter", "mono": "JetBrains Mono"}},
  "background": {"color": "background", "texture": "none | dots | grid | guides | vignette", "lineColor": "rgba(255,255,255,.12)"},
  "blocks": [{"id": "hook", "name": "Hook", "start": 0, "end": 6, "origin": {"x": 0, "y": 0}}],
  "camera": [{"t": 0, "block": "hook", "zoom": 1}, {"t": 5.5, "block": "hook", "x": 60, "zoom": 1.06},
             {"t": 7, "block": "offer", "ease": "expo"}],
  "layers": [ ... ],
  "transitions": [{"at": 6.2, "type": "whip", "duration": 0.6}],
  "sounds": [{"t": 0.1, "name": "subdrop", "gain": 0.8}],
  "music": {"mood": "cinematic", "volume": 0.5}
}
```

- Colours anywhere may be a brand colour name (`background`, `text`, `accent`, `muted`, or any key you add
  to `brand.colors`) or a CSS colour. Fonts may be a brand font name (`heading`, `body`, `mono`) or a Google
  Font family.
- `duration`: 15 to 40 seconds for a brand film. Every layer's `start`/`end` must fit inside it.

## Camera keyframes

`{"t", "block"?, "x"?, "y"?, "zoom"?, "rotate"?, "ease"?}`. With `block`, `x`/`y` are small offsets from that
block's spot; without it they are absolute canvas positions. Zoom 1 is normal, 1.1 a slow push-in, 0.85 a
pull-back that reveals more of the canvas. `rotate` in degrees (keep within ±6). `ease` shapes the move
arriving at this key: `linear`, `out`, `in`, `inOut` (default), `expo` (fast then settles; good for flights
between blocks), `back`, `elastic`.

## Layers

Common fields:

| field | meaning |
|---|---|
| `id` | unique, short (`headline`, `stat-1`) |
| `type` | `text`, `image`, `shape`, `path`, `particles`, `counter`, `logo` |
| `block` | the block it sits in (its x/y are inside that block) |
| `name` | label shown in the editor |
| `start`, `end` | seconds in the film |
| `x`, `y` | position of the anchor point in the block |
| `anchor` | `center` (default), `top-left`, `top`, `top-right`, `left`, `right`, `bottom-left`, `bottom`, `bottom-right` |
| `width`, `height` | box size (text wraps at `width`) |
| `depth` | 1 canvas (default), 0 screen-fixed, between or above for parallax |
| `z` | stacking order |
| `opacity`, `scale`, `rotate` | base values |
| `in` | entrance `{"effect", "duration", "stagger"?, "ease"?}` |
| `out` | exit `{"effect", "duration"}`: `fade`, `rise`, `blur`, `scale`, `none` |
| `motion` | keyframes relative to the layer's start: `[{"t": 0, "dx": 0}, {"t": 3, "dx": -80, "scale": 1.05, "rotate": 2, "opacity": 1, "ease": "inOut"}]` |
| `sound` | `{"in": "pop", "gain": 0.8}` plays a sound as it enters |

Entrances for every layer: `fade`, `rise`, `scale`, `zoom-in`, `pop`, `blur`, `mask-circle`, `wipe-left`, `none`.
Text and counters also have per-word or per-letter entrances: `rise-words` (default for text), `mask-up`,
`blur-in`, `scale-pop`, `type`, `letters-rise`, `letters-scatter`.

### text
`text` (use `\n` for line breaks), `accent`: word indices (0-based, counting words across the whole text)
drawn in the accent style, and `style`:
`{"font": "heading", "size": 96, "weight": 800, "color": "text", "lineHeight": 1.02, "tracking": -0.03,
"align": "left|center|right", "case": "upper|lower", "italic": false, "accentColor": "accent",
"accentStyle": "color|italic|underline|highlight|outline"}`.
Sizes for 1920 wide: headline 110 to 170, statement 72 to 96, supporting line 34 to 44, label 22 to 28 (mono, upper, tracking 0.12).

### image
`src` must be a file in the film folder, e.g. `assets/hero.jpg` (only the files listed in the brief exist).
`width`, `height`, `fit` (`cover`/`contain`), `focus` (`"50% 30%"`), `radius`, `mask: "circle"`,
`filter: "grayscale" | "duotone"`, `kenburns: "push_in" | "pull_out" | "pan_left" | "pan_right"`.

### shape
`shape`: `rect`, `circle`, `ellipse`, `ring`, `line`; `width`, `height`, `fill`, `stroke`, `strokeWidth`,
`radius`, `dash` (`"6 10"`), `draw: true` draws the outline on over `in.duration`.

### path
A drawn line across the block: `d` is an SVG path in the block's screen coordinates (1920 x 1080 for 16:9),
`stroke`, `width`, `glow`, `head` (a bright travelling point), `sparks`, `in.duration` (draw time), `in.ease`.

### particles
`count` (up to 400), `size` [min, max], `color`, `opacity`, `seed`, `area` {x, y, w, h},
`flow`: `drift`, `rise`, `orbit`, `burst`. Use depth 0.2 to 0.5 for background star fields.

### counter
`value` such as `"52M"`, `"3,400+"`, `"98%"`; counts up over `in.duration`. Styled like text.

### logo
`src` of the logo file, or `text` for a wordmark.

## Transitions

`{"at", "type", "duration", "color"?, "sound"?}`: `whip` (fast blurred slide), `zoom-through`, `flash`,
`wipe` (colour sweep), `dip` (to a colour). A whoosh plays under each one unless `"sound": "none"`.
Use them sparingly; most hand-overs should be camera moves.

## Sounds and music

`sounds`: `{"t", "name", "gain"}`. Names: whoosh, swish, swipe, impact, sting, riser, downlifter, subdrop,
shimmer, pop, popin, click, toggle, keypress, typing, notify, pluck, glitch, hover, zip.
Put an `impact` or `sting` on the key number or the logo, a `riser` 2.5 s before a big reveal.
`music.mood`: cinematic, inspiring, corporate, electronic, upbeat, lofi, calm, or `none`.

## Craft rules

- Every claim, name and number comes from the brief. Trim; never invent.
- One idea per block, 4 to 7 blocks, hook first and logo + call to action + domain last.
- Hold text long enough to read: about 0.3 s per word after it lands.
- Two or more devices specific to this brand (a path that traces their idea, a particle system, image
  treatments, typographic layouts), not generic centred text on a plain background.
- Keep text inside the screen: leave 120 px margins, and give long lines a `width`.
- Vary entrances and hand-overs; overlap them a little so motion never stops.
- Depth is measured from the layer's block: when the camera is on that block, every layer sits exactly
  where you placed it, whatever its depth. Depth only changes how layers drift while the camera moves.
