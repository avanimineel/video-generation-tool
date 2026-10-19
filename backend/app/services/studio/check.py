"""Look at a film the way a viewer would: draw it in Chrome, list what is wrong, and save a contact sheet.

    python3 check_film          (inside a film folder; that small script calls main())

Problems found: console errors, and text, counters or logos that run off the screen while fully on.
"""
import json
import sys
from pathlib import Path

from app.services.studio import composition

SIZES = {'16:9': (1920, 1080), '9:16': (1080, 1920), '1:1': (1080, 1080)}

# For every text-like layer: where its box is on the screen once its entrance has finished.
_MEASURE = """(film) => {
  const out = [];
  for (const L of film.layers) {
    if (!['text', 'counter', 'logo'].includes(L.type)) continue;
    const t = Math.min(L.end - .05, L.start + ((L.in && L.in.duration) || .5) + .6 + (String(L.text || '').split(/\\s+/).length * ((L.in && L.in.stagger) || .09)));
    window.seek(t);
    const el = document.querySelector(`[data-layer="${CSS.escape(L.id)}"]`);
    if (!el || el.style.display === 'none') continue;
    const r = el.getBoundingClientRect();
    out.push({id: L.id, t: Math.round(t * 100) / 100, left: r.left, top: r.top, right: r.right, bottom: r.bottom});
  }
  return out;
}"""


def inspect(folder, moments=None):
    """(problems, sheet path) for the film.json in `folder`."""
    from playwright.sync_api import sync_playwright
    from PIL import Image
    folder = Path(folder)
    problems = []
    try:
        film = composition.validate(json.loads((folder / 'film.json').read_text()), folder)
    except FileNotFoundError:
        return ['film.json does not exist yet.'], None
    except Exception as exc:
        return [f'film.json is not a valid film: {str(exc)[:600]}'], None
    page_path = folder / 'player.html'
    page_path.write_text(composition.player_html(film))
    width, height = SIZES[film.aspect]
    out = folder / 'check'; out.mkdir(exist_ok=True)
    for old in out.glob('frame_*.png'): old.unlink()
    shots, errors = [], []
    with sync_playwright() as p:
        chrome = p.chromium.launch(channel='chrome', headless=True, args=['--allow-file-access-from-files'])
        page = chrome.new_page(viewport={'width': width, 'height': height})
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(page_path.resolve().as_uri(), wait_until='load')
        page.evaluate('document.fonts.ready.then(() => true)'); page.wait_for_timeout(300)
        margin = 24
        for box in page.evaluate(_MEASURE, composition.dump(film)):
            over = [side for side, bad in (('left', box['left'] < -margin), ('top', box['top'] < -margin),
                                           ('right', box['right'] > width + margin), ('bottom', box['bottom'] > height + margin)) if bad]
            if over:
                problems.append(f"Layer {box['id']} runs off the {' and '.join(over)} edge of the screen at {box['t']}s "
                                f"(box {box['left']:.0f},{box['top']:.0f} to {box['right']:.0f},{box['bottom']:.0f}; screen {width}x{height}).")
        total = film.duration
        moments = moments or [round(total * f, 2) for f in (.04, .14, .26, .38, .5, .62, .74, .86, .95, .99)]
        for t in moments:
            page.evaluate(f'window.seek({t})')
            path = out / f'frame_{t:06.2f}.png'; page.screenshot(path=str(path)); shots.append(path)
        chrome.close()
    problems += [f'Console error: {e}' for e in errors[:5]]
    thumbs = [Image.open(s).convert('RGB') for s in shots]
    w = 480 if width >= height else 270; h = int(w * height / width); cols = 5 if width >= height else 6
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new('RGB', (w * cols, h * rows), 'black')
    for i, im in enumerate(thumbs): sheet.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
    sheet_path = out / 'sheet.png'; sheet.save(sheet_path)
    return problems, sheet_path


def main(folder='.'):
    moments = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 and sys.argv[1].strip() else None
    problems, sheet = inspect(folder, moments)
    print('OK' if not problems else 'PROBLEMS:\n- ' + '\n- '.join(problems))
    if sheet: print(f'Contact sheet: {sheet} (frames are in check/)')
    sys.exit(1 if problems else 0)
