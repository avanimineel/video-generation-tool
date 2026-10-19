"""Studio films: made in one go by an AI engine, then edited by hand, remixed by direction, and rendered.

Each film is a folder under studio_films/<id>/:
    job.json        state (status, stage, versions, render)
    brand_kit.json  what the site reader found; assets/ holds the brand's images
    BRIEF.md        the facts and images an engine may use
    film.json       the current film (the editor saves here)
    versions/v<n>.json  each version made by an engine, or saved by hand
    film.mp4        the last render
"""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.core.config import settings
from app.services.studio import composition

ROOT = settings.projects_dir.parent / 'studio_films'
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='studio')
_lock = Lock()
_running = set()
BUSY = ('reading', 'designing', 'remixing')


def folder(film_id):
    if not re.fullmatch(r'[a-z0-9-]{6,64}', film_id or ''): raise ValueError('Invalid film id')
    return ROOT / film_id


def _write(film_id, **changes):
    path = folder(film_id) / 'job.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    state.update(changes, updated=time.time())
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(state, indent=2, ensure_ascii=False)); temp.replace(path)
    return state


def status(film_id):
    path = folder(film_id) / 'job.json'
    if not path.exists(): return None
    state = json.loads(path.read_text())
    with _lock: alive = {k[1] for k in _running if k[0] == film_id}
    if state.get('worker') and state['worker'] != os.getpid() and _process_alive(state['worker']): alive |= {'make', 'render'}
    if state.get('status') in BUSY and 'make' not in alive:
        backup = folder(film_id) / 'film.before.json'
        if backup.exists(): backup.replace(folder(film_id) / 'film.json')  # Undo a remix that was cut off.
        state.update(status='interrupted' if not state.get('versions') else 'ready', error='The backend restarted while the film was being made.')
    render = state.get('render') or {}
    if render.get('status') == 'rendering' and 'render' not in alive:
        state['render'] = dict(render, status='failed', error='The backend restarted during the render.')
    return state


def _process_alive(pid):
    # Jobs started by another process (the command line, or a previous server) count while it lives.
    try:
        os.kill(int(pid), 0); return True
    except (OSError, ValueError, TypeError):
        return False


def list_films(limit=30):
    if not ROOT.exists(): return []
    films = [status(p.name) for p in ROOT.iterdir() if (p / 'job.json').exists()]
    return sorted([f for f in films if f], key=lambda f: f.get('created', 0), reverse=True)[:limit]


def _submit(film_id, kind, fn, *args):
    key = (film_id, kind)
    with _lock:
        if key in _running: raise ValueError('This film is already busy; wait for it to finish.')
        _running.add(key)

    _write(film_id, worker=os.getpid())

    def run():
        try: fn(*args)
        finally:
            with _lock: _running.discard(key)
    _executor.submit(run)


def _error(exc):
    from app.services.editorial_planner import safe_error
    return safe_error(exc)


# ---------- Making a film ----------

def create(url='', prompt='', aspect='16:9', engine='claude', duration=None):
    """Start a new film from a website, a written idea, or both. Returns its state."""
    from app.services.studio.agents import ENGINES
    url, prompt = (url or '').strip(), (prompt or '').strip()
    if not url and not prompt: raise ValueError('Give a website, an idea for the film, or both.')
    if engine not in ENGINES: raise ValueError('Engine must be claude or gemini.')
    if aspect not in ('16:9', '9:16', '1:1'): raise ValueError('Aspect must be 16:9, 9:16 or 1:1')
    if url:
        from app.services.brand_video.jobs import clean_url
        url = clean_url(url)
        slug = re.sub(r'[^a-z0-9]+', '-', re.sub(r'^https?://(www\.)?', '', url.lower())).strip('-')[:36]
    else:
        slug = re.sub(r'[^a-z0-9]+', '-', prompt.lower()).strip('-')[:36] or 'film'
    film_id = f'{slug}-{uuid4().hex[:6]}'
    state = _write(film_id, id=film_id, url=url, prompt=prompt, aspect=aspect, engine=engine, duration=duration,
                   status='reading' if url else 'designing', stage='Reading the website' if url else 'Designing the film',
                   created=time.time(), versions=[], title=prompt[:60] or url)
    _submit(film_id, 'make', _make, film_id)
    return state


def brief(kit, prompt):
    """The facts and images an engine may use, as Markdown."""
    lines = ['# Brief', '']
    if prompt: lines += ['## Direction from the person', prompt, '']
    if kit:
        copy = kit.get('copy') or {}
        lines += [f"## Brand: {kit.get('name')}", f"Website: {kit.get('domain') or kit.get('url')}", f"Industry: {kit.get('industry')}",
                  f"Description: {kit.get('description') or ''}", '',
                  f"Colours found on the site: {json.dumps({k: v for k, v in (kit.get('colors') or {}).items() if isinstance(v, str)})}",
                  f"Fonts found on the site: {json.dumps(kit.get('fonts') or {})} (use the Google Font names; if a font is not on Google Fonts pick the closest one that is)", '',
                  f"Hero line: {copy.get('hero') or ''}", f"Hero text: {copy.get('hero_body') or ''}", f"Call to action: {copy.get('cta') or ''}", '']
        for key in ('subheadings', 'paragraphs', 'features', 'steps', 'stats', 'testimonials'):
            items = copy.get(key) or []
            if items:
                lines.append(f'### {key.title()}')
                lines += [f'- {json.dumps(i, ensure_ascii=False) if not isinstance(i, str) else i}' for i in items[:14]]
                lines.append('')
        if kit.get('figures'):
            lines.append('### Numbers (only these may be shown)')
            lines += [f"- {f['value']} {f.get('label', '')}: \"{f.get('line', '')}\"" for f in kit['figures']]
            lines.append('')
    images = _images(kit)
    lines.append('## Images you may use (paths are relative to this folder)')
    lines += [f"- {i['src']} ({i['width']}x{i['height']}){': ' + i['note'] if i['note'] else ''}" for i in images] or ['- none: build the film from type, shapes, paths and particles']
    lines += ['', 'Look at site.png and the images with the Read tool before designing, when they exist.']
    return '\n'.join(lines) + '\n'


def _images(kit):
    from PIL import Image
    out = []
    for item in ([{'path': kit.get('logo'), 'alt': 'logo'}] if kit and kit.get('logo') else []) + list((kit or {}).get('images') or []):
        path = Path(item.get('path') or '')
        if not path.is_file() or path.suffix.lower() == '.svg' and item.get('alt') != 'logo': continue
        try:
            if path.suffix.lower() == '.svg': w, h = 400, 400
            else:
                with Image.open(path) as im: w, h = im.size
        except Exception:
            continue
        out.append({'src': f'assets/{path.name}', 'width': w, 'height': h, 'note': item.get('alt') or ''})
    return out


def _make(film_id):
    from app.services.studio import agents
    state = status(film_id); out = folder(film_id); kit = None
    try:
        if state['url']:
            from app.services.brand_video.site_reader import read_site
            kit = read_site(state['url'], out)
            _write(film_id, status='designing', stage='Designing the film', title=kit.get('name') or state['url'],
                   brand={'name': kit.get('name'), 'colors': kit.get('colors'), 'fonts': kit.get('fonts')})
        (out / 'BRIEF.md').write_text(brief(kit, state['prompt']))
        engine = 'Claude Code' if state['engine'] == 'claude' else 'Gemini'
        _write(film_id, stage=f'{engine} is designing the film')
        task = f"Design a {state['aspect']} film{' of about ' + str(state['duration']) + ' seconds' if state.get('duration') else ''}."
        film = agents.write(out, state['engine'], task=task)
        if film.aspect != state['aspect']: film.aspect = state['aspect']
        _save_version(film_id, film, f"Made by {engine}", state['engine'])
        _write(film_id, status='ready', stage='Ready to edit', error=None, title=film.title)
    except Exception as exc:
        _write(film_id, status='failed', stage='Failed', error=_error(exc))


def remix(film_id, instruction, engine=None):
    instruction = (instruction or '').strip()
    if not instruction: raise ValueError('Say how to remix the film.')
    state = status(film_id)
    if not state: raise FileNotFoundError(film_id)
    if not (folder(film_id) / 'film.json').exists(): raise ValueError('This film has nothing to remix yet.')
    engine = engine or state.get('engine') or 'claude'
    _write(film_id, status='remixing', stage=f"{'Claude Code' if engine == 'claude' else 'Gemini'} is remixing: {instruction[:80]}", error=None)
    _submit(film_id, 'make', _remix, film_id, instruction, engine)
    return status(film_id)


def _remix(film_id, instruction, engine):
    from app.services.studio import agents
    out = folder(film_id)
    before = (out / 'film.json').read_text()
    (out / 'film.before.json').write_text(before)
    try:
        film = agents.write(out, engine, instruction=instruction)
        _save_version(film_id, film, f'Remix: {instruction[:120]}', engine)
        _write(film_id, status='ready', stage='Ready to edit', error=None)
    except Exception as exc:
        (out / 'film.json').write_text(before)  # A failed remix leaves the film as it was.
        _write(film_id, status='ready', stage='Ready to edit', error='Remix failed: ' + _error(exc))
    finally:
        (out / 'film.before.json').unlink(missing_ok=True)


# ---------- Editing and versions ----------

def get_film(film_id):
    path = folder(film_id) / 'film.json'
    if not path.exists(): return None
    return composition.dump(composition.validate(json.loads(path.read_text()), folder(film_id)))


def put_film(film_id, data):
    """Save an edit from the editor. Returns the cleaned film."""
    state = status(film_id)
    if not state: raise FileNotFoundError(film_id)
    if state.get('status') in BUSY: raise ValueError('An engine is working on this film; wait for it to finish.')
    film = composition.validate(data, folder(film_id))
    clean = composition.dump(film)
    _atomic(folder(film_id) / 'film.json', clean)
    _write(film_id, edited=time.time(), title=film.title)
    return clean


def _atomic(path, data):
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(data, indent=1, ensure_ascii=False)); temp.replace(path)


def _save_version(film_id, film, note, engine=None):
    out = folder(film_id); (out / 'versions').mkdir(exist_ok=True)
    state = json.loads((out / 'job.json').read_text())
    versions = state.get('versions') or []
    n = (versions[-1]['n'] + 1) if versions else 1
    data = composition.dump(film)
    _atomic(out / 'versions' / f'v{n}.json', data); _atomic(out / 'film.json', data)
    versions.append({'n': n, 'note': note, 'engine': engine, 'created': time.time()})
    _write(film_id, versions=versions, version=n)
    return n


def save_version(film_id, note='Saved by hand'):
    film = composition.validate(json.loads((folder(film_id) / 'film.json').read_text()), folder(film_id))
    return _save_version(film_id, film, note or 'Saved by hand', 'hand')


def get_version(film_id, n):
    path = folder(film_id) / 'versions' / f'v{int(n)}.json'
    return json.loads(path.read_text()) if path.exists() else None


def restore(film_id, n):
    data = get_version(film_id, n)
    if data is None: raise FileNotFoundError(f'v{n}')
    return put_film(film_id, data)


# ---------- Preview and render ----------

def player(film_id, n=None):
    """The engine page for the current film (or version n), with paths relative to the film folder."""
    data = get_version(film_id, n) if n else json.loads((folder(film_id) / 'film.json').read_text())
    return composition.player_html(composition.validate(data, folder(film_id)))


def assets(film_id):
    """The film's images, for the editor's image picker."""
    base = folder(film_id) / 'assets'
    kinds = ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif')
    return sorted(f'assets/{p.name}' for p in base.iterdir() if p.suffix.lower() in kinds) if base.is_dir() else []


def asset(film_id, name):
    base = folder(film_id).resolve(); path = (base / name).resolve()
    if base not in path.parents or not path.is_file() or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif'):
        return None
    return path


def render(film_id):
    state = status(film_id)
    if not state: raise FileNotFoundError(film_id)
    if not (folder(film_id) / 'film.json').exists(): raise ValueError('There is no film to render yet.')
    _write(film_id, render={'status': 'rendering', 'progress': 0, 'started': time.time()})
    _submit(film_id, 'render', _render, film_id)
    return status(film_id)


def _render(film_id):
    from playwright.sync_api import sync_playwright
    from app.services.brand_video.renderer import record, finish
    out = folder(film_id)
    try:
        film = composition.validate(json.loads((out / 'film.json').read_text()), out)
        page = out / 'render.html'; page.write_text(composition.player_html(film))
        with sync_playwright() as p:
            chrome = p.chromium.launch(channel='chrome', headless=True, args=['--allow-file-access-from-files'])
            tab = chrome.new_page(); tab.goto(page.resolve().as_uri(), wait_until='load')
            cues = tab.evaluate('Array.isArray(window.CUES) ? window.CUES : []'); chrome.close()
        silent = out / 'film_silent.mp4'
        total = record(page, film.aspect, silent, progress=lambda q: _write(film_id, render={'status': 'rendering', 'progress': round(.95 * q, 3)}))
        mood = (film.music or {}).get('mood', 'cinematic')
        finish(out, silent, cues, total, mood if mood != 'none' else 'cinematic', mood != 'none')
        track = json.loads((out / 'music.json').read_text()) if mood != 'none' and (out / 'music.json').exists() else None
        _write(film_id, render={'status': 'complete', 'progress': 1, 'finished': time.time(), 'duration': round(total, 2),
                                'music': {k: track[k] for k in ('title', 'creator', 'license', 'attribution', 'credit_required')} if track else None})
    except Exception as exc:
        _write(film_id, render={'status': 'failed', 'error': _error(exc)})


def video_path(film_id):
    path = folder(film_id) / 'film.mp4'
    return path if path.is_file() else None
