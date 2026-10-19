---
name: brand-film
description: Make or remix a brand film in the app's Studio (editable film.json), from a website or an idea. Use when asked to make a brand film, launch film, promo or explainer video.
---

# Brand film, made in the Studio

Films are made in the app's Studio so the person can edit every part afterwards (layers, camera, blocks,
transitions, sounds, music) and remix them by direction. Do not hand-write HTML films; write the Studio
format instead.

## Make one

From `backend/` (needs network for the site reader; Claude Code runs headless under the person's sign-in):

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from app.services.studio import films
films._submit = lambda film_id, kind, fn, *args: fn(*args)
print(films.create(url='<website>', prompt='<direction, optional>', aspect='16:9', engine='claude')['id'])
"
```

Or, inside the app: **Studio** button in the top bar, then New film. Engines: `claude` (Claude Code, the
person's subscription) or `gemini` (API key, billed: ask before using it).

The film lands in `backend/studio_films/<id>/`: `film.json` (current), `versions/`, `BRIEF.md` (the facts),
`FORMAT.md` (the format), `check/sheet.png` (contact sheet).

## Edit or design by hand

Read `backend/app/services/studio/FORMAT.md`, edit `film.json` in the film folder, then run
`python3 check_film` there. Fix every problem it lists and look at `check/sheet.png` as an art director.

## Remix and render

`films.remix(id, 'direction')` writes a new version; `films.render(id)` records `film.mp4` with sound cues
and a licensed music bed (credit in `job.json` → `render.music`). Both are also buttons in the Studio.

## Craft

Every claim and number comes from the brief. One canvas, a camera that travels between blocks, two or more
devices specific to the brand, varied entrances, text held long enough to read.
