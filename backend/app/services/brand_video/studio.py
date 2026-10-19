"""Studio: tools for hand-designed brand films, written by Claude Code (see .claude/skills/brand-film).

    python3 -m app.services.brand_video.studio new <website> [--aspect 16:9|9:16|1:1]
        Reads the site into a film folder: brand_kit.json, site.png, assets/, stage-kit.js.
    python3 -m app.services.brand_video.studio check <film-id> [--frames 0,2.5,6]
        Loads film.html in Chrome and checks the contract: TOTAL and seek exist, no console errors,
        no CSS animations or timers, and every checked moment renders the same picture twice.
        Writes check/frame_<t>.png and check/sheet.png to look at.
    python3 -m app.services.brand_video.studio render <film-id> [--mood cinematic] [--no-music]
        Records film.html to film.mp4 with its sound cues and a licensed music bed, and lists the
        film in the app's Brand film panel.
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

from app.services.brand_video import jobs
from app.services.brand_video.renderer import SIZES, FPS, record, finish

KIT_JS = Path(__file__).with_name('stage-kit.js')
FORBIDDEN = ('requestAnimationFrame', 'setInterval', 'setTimeout', 'Math.random', 'animation:', '@keyframes', 'transition:')


def visibly_different(a, b):
    """True when two screenshots differ by more than anti-aliasing noise: over 0.05% of pixels off by 24+ levels."""
    import io
    from PIL import Image, ImageChops
    diff = ImageChops.difference(Image.open(io.BytesIO(a)).convert('RGB'), Image.open(io.BytesIO(b)).convert('RGB')).convert('L')
    counts = diff.histogram()
    return sum(counts[24:]) > diff.width * diff.height * .0005


def new(url, aspect='16:9'):
    from app.services.brand_video.site_reader import read_site
    state = jobs.create(url, aspect, status='designing', stage='Designing with Claude Code')
    folder = jobs.folder(state['id'])
    kit = read_site(state['url'], folder)
    shutil.copy(KIT_JS, folder / 'stage-kit.js')
    jobs.update(state['id'], brand={'name': kit['name'], 'colors': kit['colors'], 'fonts': kit['fonts'], 'cta': kit['copy']['cta']}, custom=True)
    return state['id'], folder, kit


def check(film_id, moments=None):
    """Problems with a film page, and a contact sheet of the checked moments."""
    from playwright.sync_api import sync_playwright
    from PIL import Image
    folder = jobs.folder(film_id); page_path = folder / 'film.html'
    if not page_path.exists(): return [f'{page_path} does not exist yet.'], None
    source = page_path.read_text()
    problems = [f'Uses "{word}": every frame must come from window.seek(t) alone.' for word in FORBIDDEN if word in source]
    meta = json.loads((folder / 'job.json').read_text())
    width, height = SIZES.get(meta.get('aspect', '16:9'), SIZES['16:9'])
    out = folder / 'check'; shutil.rmtree(out, ignore_errors=True); out.mkdir()
    shots = []
    with sync_playwright() as p:
        chrome = p.chromium.launch(channel='chrome', headless=True, args=['--allow-file-access-from-files'])
        page = chrome.new_page(viewport={'width': width, 'height': height})
        errors = []
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(page_path.resolve().as_uri(), wait_until='load')
        page.evaluate('document.fonts.ready.then(() => true)'); page.wait_for_timeout(400)
        total = page.evaluate('typeof window.TOTAL === "number" ? window.TOTAL : null')
        if not total or total <= 0: problems.append('window.TOTAL must be the film length in seconds.')
        if not page.evaluate('typeof window.seek === "function"'): problems.append('window.seek(t) is missing.')
        if not problems or total:
            moments = moments or [round(total * f, 2) for f in (0.02, .15, .3, .45, .6, .75, .9, .99)]
            for t in moments:
                page.evaluate(f'window.seek({t})'); first = page.screenshot(type='png')
                page.evaluate(f'window.seek({min(t + 1.3, total * .98)})'); page.evaluate(f'window.seek({t})'); again = page.screenshot(type='png')
                if hashlib.md5(first).digest() != hashlib.md5(again).digest() and visibly_different(first, again):
                    problems.append(f'Moment {t}s looks different when revisited: something depends on more than t.')
                path = out / f'frame_{t:06.2f}.png'; path.write_bytes(first); shots.append(path)
        problems += [f'Console error: {e}' for e in errors[:5]]
        chrome.close()
    sheet = None
    if shots:
        thumbs = [Image.open(s).convert('RGB') for s in shots]
        w = 480; h = int(w * thumbs[0].height / thumbs[0].width); cols = 4; rows = (len(thumbs) + cols - 1) // cols
        sheet_img = Image.new('RGB', (w * cols, h * rows), 'black')
        for i, im in enumerate(thumbs): sheet_img.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
        sheet = out / 'sheet.png'; sheet_img.save(sheet)
    return problems, sheet


def render(film_id, mood='cinematic', music=True):
    folder = jobs.folder(film_id); page_path = folder / 'film.html'
    problems, _ = check(film_id)
    if problems: raise SystemExit('Fix these before recording:\n- ' + '\n- '.join(problems))
    meta = json.loads((folder / 'job.json').read_text())
    jobs.update(film_id, status='recording', stage='Recording the film', progress=.1)
    from playwright.sync_api import sync_playwright
    width, height = SIZES.get(meta.get('aspect', '16:9'), SIZES['16:9'])
    with sync_playwright() as p:
        chrome = p.chromium.launch(channel='chrome', headless=True, args=['--allow-file-access-from-files'])
        page = chrome.new_page(viewport={'width': width, 'height': height})
        page.goto(page_path.resolve().as_uri(), wait_until='load')
        cues = page.evaluate('Array.isArray(window.CUES) ? window.CUES : []'); chrome.close()
    silent = folder / 'film_silent.mp4'
    total = record(page_path, meta.get('aspect', '16:9'), silent, progress=lambda q: jobs.update(film_id, progress=round(.1 + .8 * q, 3)))
    finish(folder, silent, cues, total, mood, music)
    track = json.loads((folder / 'music.json').read_text()) if music and (folder / 'music.json').exists() else None
    jobs.update(film_id, status='complete', stage='Ready', progress=1, duration=round(total, 2),
                music={k: track[k] for k in ('title', 'creator', 'license', 'attribution', 'credit_required', 'landing_url')} if track else None)
    return folder / 'film.mp4'


def main(argv=None):
    parser = argparse.ArgumentParser(prog='studio', description='Hand-designed brand films.')
    commands = parser.add_subparsers(dest='command', required=True)
    a = commands.add_parser('new'); a.add_argument('url'); a.add_argument('--aspect', default='16:9')
    b = commands.add_parser('check'); b.add_argument('film_id'); b.add_argument('--frames', default='')
    c = commands.add_parser('render'); c.add_argument('film_id'); c.add_argument('--mood', default='cinematic'); c.add_argument('--no-music', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'new':
        film_id, folder, kit = new(args.url, args.aspect)
        print(json.dumps({'film_id': film_id, 'folder': str(folder), 'name': kit['name'], 'industry': kit['industry'],
                          'colors': kit['colors'], 'fonts': kit['fonts'], 'hero_image': kit.get('hero_image'), 'logo': kit.get('logo')}, indent=2))
    elif args.command == 'check':
        moments = [float(x) for x in args.frames.split(',') if x.strip()] or None
        problems, sheet = check(args.film_id, moments)
        print('OK' if not problems else 'PROBLEMS:\n- ' + '\n- '.join(problems)); print('sheet:', sheet)
        sys.exit(1 if problems else 0)
    else:
        print(render(args.film_id, args.mood, not args.no_music))


if __name__ == '__main__':
    main()
