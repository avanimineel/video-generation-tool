"""Brand films run in the background and survive page navigation; state is kept on disk per film."""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse
from uuid import uuid4

from app.core.config import settings

ROOT = settings.projects_dir.parent / 'brand_videos'
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='brand-video')
_lock = Lock()
_running = set()


def folder(film_id):
    if not re.fullmatch(r'[a-z0-9-]{6,64}', film_id or ''): raise ValueError('Invalid brand film id')
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
    with _lock: alive = film_id in _running
    if state.get('status') in ('reading', 'writing', 'recording') and not alive:
        state.update(status='interrupted', error='The backend restarted during this film. Start it again.')
    return state


def list_films(limit=20):
    if not ROOT.exists(): return []
    films = [status(p.name) for p in ROOT.iterdir() if (p / 'job.json').exists()]
    return sorted([f for f in films if f], key=lambda f: f.get('created', 0), reverse=True)[:limit]


def update(film_id, **changes):
    return _write(film_id, **changes)


def clean_url(url):
    """A public http(s) website address, or ValueError."""
    url = url.strip()
    if not urlparse(url).scheme: url = 'https://' + url
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or '.' not in parsed.netloc:
        raise ValueError('Enter a public website address, for example oonex.in')
    if parsed.hostname in ('localhost', '127.0.0.1') or (parsed.hostname or '').endswith('.local'):
        raise ValueError('Only public websites can be read.')
    return url


def create(url, aspect='16:9', status='reading', stage='Reading the website'):
    """A new film folder and its job record, after checking the address and format."""
    url = clean_url(url); parsed = urlparse(url)
    if aspect not in ('16:9', '9:16', '1:1'): raise ValueError('Aspect must be 16:9, 9:16 or 1:1')
    film_id = re.sub(r'[^a-z0-9]+', '-', parsed.netloc.lower().removeprefix('www.')).strip('-')[:40] + '-' + uuid4().hex[:6]
    return _write(film_id, id=film_id, url=url, aspect=aspect, status=status, stage=stage, progress=0, created=time.time())


def start(url, aspect='16:9'):
    state = create(url, aspect); film_id, url = state['id'], state['url']
    with _lock: _running.add(film_id)
    _executor.submit(_run, film_id, url, aspect)
    return status(film_id)


def _run(film_id, url, aspect):
    from app.services.brand_video.site_reader import read_site
    from app.services.brand_video.script import compose
    from app.services.brand_video.renderer import render
    from app.services.editorial_planner import safe_error
    out = folder(film_id)
    try:
        kit = read_site(url, out)
        _write(film_id, status='writing', stage='Writing the script', progress=.1,
               brand={'name': kit['name'], 'colors': kit['colors'], 'fonts': kit['fonts'], 'cta': kit['copy']['cta']})
        plan = compose(kit, aspect)
        (out / 'plan.json').write_text(json.dumps(plan, indent=2, ensure_ascii=False))
        _write(film_id, status='recording', stage='Recording the film', progress=.15, scenes=[s['type'] for s in plan['scenes']], duration=plan['total'])
        render(kit, plan, out, progress=lambda p: _write(film_id, progress=round(.15 + .8 * p, 3)))
        music = json.loads((out / 'music.json').read_text()) if (out / 'music.json').exists() else None
        _write(film_id, status='complete', stage='Ready', progress=1,
               music={k: music[k] for k in ('title', 'creator', 'license', 'attribution', 'credit_required', 'landing_url')} if music else None)
    except Exception as exc:
        _write(film_id, status='failed', stage='Failed', error=safe_error(exc))
    finally:
        with _lock: _running.discard(film_id)


def film_path(film_id):
    path = folder(film_id) / 'film.mp4'
    return path if path.is_file() else None
