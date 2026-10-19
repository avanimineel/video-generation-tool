"""Studio films: the editable format, versions, preview pages and the API, with the AI engines stubbed."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.studio import agents, composition, films

FILM = {
    'title': 'Test', 'aspect': '16:9', 'duration': 10,
    'brand': {'colors': {'background': '#000', 'text': '#fff', 'accent': '#f80'}, 'fonts': {'heading': 'Inter'}},
    'blocks': [{'id': 'a', 'name': 'Hook', 'start': 0, 'end': 5}, {'id': 'b', 'name': 'End', 'start': 5, 'end': 10, 'origin': {'x': 2400, 'y': 0}}],
    'camera': [{'t': 0, 'block': 'a'}, {'t': 6, 'block': 'b', 'ease': 'expo'}],
    'layers': [
        {'id': 'h', 'type': 'text', 'block': 'a', 'start': .2, 'end': 5, 'x': 960, 'y': 540, 'text': 'Hello there', 'accent': [1],
         'in': {'effect': 'mask-up', 'duration': .6}, 'sound': {'in': 'pop'}},
        {'id': 'stars', 'type': 'particles', 'start': 0, 'end': 10, 'motion': 'drift', 'depth': .3},
        {'id': 'n', 'type': 'counter', 'block': 'b', 'start': 6, 'end': 30, 'value': '52M', 'in': {'effect': 'warp-speed'}},
        {'id': 'h', 'type': 'image', 'block': 'b', 'start': 6, 'end': 9, 'src': 'https://example.com/x.png'},
        {'id': 'pic', 'type': 'image', 'start': 1, 'end': 4, 'src': '../../secret.png'},
    ],
    'transitions': [{'at': 5, 'type': 'teleport'}, {'at': 99, 'type': 'whip'}],
}


def test_validate_cleans_whatever_arrives(tmp_path):
    film = composition.validate(FILM, tmp_path)
    ids = [layer.id for layer in film.layers]
    assert len(set(ids)) == len(ids)                          # Duplicate ids are renamed.
    stars = next(l for l in film.layers if l.id == 'stars')
    assert stars.flow == 'drift' and stars.motion == []       # A named particle motion becomes its flow.
    counter = next(l for l in film.layers if l.id == 'n')
    assert counter.end == 10 and counter.entrance.effect == 'fade'  # Clamped to the film; unknown effect replaced.
    assert all(l.type != 'image' for l in film.layers)        # Remote and escaping image paths are dropped.
    assert [t.type for t in film.transitions] == ['whip']     # Unknown type fixed; out-of-range removed.
    assert film.blocks[1].origin == {'x': 2400, 'y': 0}
    dumped = composition.dump(film)
    assert dumped['layers'][0]['in']['effect'] == 'mask-up'   # Written back with the format's own names.


def test_player_page_carries_film_and_engine():
    html = composition.player_html(composition.validate(FILM))
    assert 'window.FILM = ' in html and 'function mountFilm' in html and 'family=Inter' in html
    evil = dict(FILM, title='</script><script>alert(1)</script>')
    assert '</script><script>alert' not in composition.player_html(composition.validate(evil))


@pytest.fixture
def made(monkeypatch, tmp_path):
    """A film 'made' by a stubbed engine that writes FILM, without network or AI calls."""
    monkeypatch.setattr(films, 'ROOT', tmp_path / 'studio_films')
    calls = []

    def fake_write(folder, engine, task=None, instruction=None):
        calls.append((engine, task, instruction))
        data = json.loads(json.dumps(FILM))
        if instruction: data['title'] = 'Remixed'
        (folder / 'film.json').write_text(json.dumps(data))
        return composition.validate(data, folder)
    monkeypatch.setattr(agents, 'write', fake_write)
    monkeypatch.setattr(films, '_submit', lambda film_id, kind, fn, *args: fn(*args))  # Run jobs inline.
    return calls


def test_make_edit_remix_and_restore(made):
    state = films.create(prompt='A launch film for a rocket shop', engine='gemini')
    film_id = state['id']
    state = films.status(film_id)
    assert state['status'] == 'ready' and [v['n'] for v in state['versions']] == [1]
    brief = (films.folder(film_id) / 'BRIEF.md').read_text()
    assert 'A launch film for a rocket shop' in brief and 'none: build the film from type' in brief
    assert made[0][0] == 'gemini' and 'Design a 16:9 film' in made[0][1]

    film = films.get_film(film_id)
    film['layers'][0]['text'] = 'Edited by hand'
    saved = films.put_film(film_id, film)
    assert saved['layers'][0]['text'] == 'Edited by hand'
    assert films.save_version(film_id, 'my tweak') == 2

    films.remix(film_id, 'make it faster')
    assert films.get_film(film_id)['title'] == 'Remixed' and films.status(film_id)['version'] == 3
    films.restore(film_id, 2)
    assert films.get_film(film_id)['layers'][0]['text'] == 'Edited by hand'
    with pytest.raises(ValueError): films.remix(film_id, '  ')


def test_failed_remix_leaves_the_film_alone(made, monkeypatch):
    film_id = films.create(prompt='x film', engine='claude')['id']
    before = films.get_film(film_id)

    def broken(folder, engine, task=None, instruction=None):
        (folder / 'film.json').write_text('{broken')
        raise RuntimeError('engine died')
    monkeypatch.setattr(agents, 'write', broken)
    films.remix(film_id, 'ruin it')
    state = films.status(film_id)
    assert state['status'] == 'ready' and 'engine died' in state['error']
    assert films.get_film(film_id) == before


def test_assets_stay_inside_the_film(made):
    film_id = films.create(prompt='asset film')['id']
    (films.folder(film_id) / 'assets').mkdir()
    (films.folder(film_id) / 'assets' / 'logo.png').write_bytes(b'png')
    assert films.asset(film_id, 'assets/logo.png')
    assert films.asset(film_id, 'assets/../job.json') is None
    assert films.asset(film_id, 'film.json') is None
    with pytest.raises(ValueError): films.folder('../etc')


def test_api_round_trip(made):
    client = TestClient(app)
    assert client.post('/api/studio', json={}).status_code == 400
    assert client.post('/api/studio', json={'url': 'http://localhost:3000'}).status_code == 400
    film_id = client.post('/api/studio', json={'prompt': 'api film', 'engine': 'gemini'}).json()['id']
    assert client.get(f'/api/studio/{film_id}').json()['status'] == 'ready'
    film = client.get(f'/api/studio/{film_id}/film').json()
    film['layers'][0]['style'] = {'size': 140}
    assert client.put(f'/api/studio/{film_id}/film', json=film).json()['layers'][0]['style']['size'] == 140
    assert client.put(f'/api/studio/{film_id}/film', json={'duration': -3}).status_code == 400
    page = client.get(f'/api/studio/{film_id}/player')
    assert page.status_code == 200 and 'mountFilm' in page.text
    assert client.get(f'/api/studio/{film_id}/versions/1').status_code == 200
    assert client.get(f'/api/studio/{film_id}/video').status_code == 404
    assert 'whoosh' in [s['name'] for s in client.get('/api/studio/engines').json()['sounds']]


def test_checker_finds_text_off_screen(tmp_path):
    pytest.importorskip('playwright')
    from app.services.studio.check import inspect
    data = json.loads(json.dumps(FILM))
    data['camera'] = []
    data['layers'] = [{'id': 'wide', 'type': 'text', 'start': 0, 'end': 10, 'x': 1800, 'y': 540, 'anchor': 'left',
                       'text': 'This line runs far past the right edge', 'style': {'size': 120}, 'in': {'effect': 'none'}}]
    (tmp_path / 'film.json').write_text(json.dumps(data))
    try:
        problems, sheet = inspect(tmp_path, [1, 5])
    except Exception as exc:  # No Chrome on this machine.
        pytest.skip(str(exc)[:200])
    assert any('wide runs off the right' in p for p in problems) and sheet.exists()


def test_parallax_layers_sit_where_placed_when_camera_is_on_their_block(tmp_path):
    pytest.importorskip('playwright')
    from playwright.sync_api import sync_playwright
    film = {'duration': 6, 'blocks': [{'id': 'far', 'name': 'Far', 'start': 0, 'end': 6, 'origin': {'x': 8000, 'y': -3000}}],
            'camera': [{'t': 0, 'block': 'far'}],
            'layers': [{'id': f'd{i}', 'type': 'text', 'block': 'far', 'start': 0, 'end': 6, 'x': 400, 'y': 300, 'anchor': 'top-left',
                        'depth': depth, 'text': 'X', 'in': {'effect': 'none'}} for i, depth in enumerate((0, .4, 1, 1.5))]}
    page_path = tmp_path / 'p.html'; page_path.write_text(composition.player_html(composition.validate(film)))
    try:
        with sync_playwright() as p:
            chrome = p.chromium.launch(channel='chrome'); page = chrome.new_page(viewport={'width': 1920, 'height': 1080})
            page.goto(page_path.as_uri()); page.evaluate('window.seek(2)')
            boxes = page.evaluate("[...document.querySelectorAll('[data-layer]')].map(e => [e.getBoundingClientRect().left, e.getBoundingClientRect().top])")
            chrome.close()
    except Exception as exc:
        pytest.skip(str(exc)[:200])
    assert all(abs(x - 400) < 2 and abs(y - 300) < 2 for x, y in boxes), boxes


def test_remix_cut_off_by_a_restart_is_undone(made):
    film_id = films.create(prompt='restart film')['id']
    before = films.get_film(film_id)
    out = films.folder(film_id)
    # What a server restart mid-remix leaves behind: status remixing, a backup, and a half-written film.
    (out / 'film.before.json').write_text((out / 'film.json').read_text())
    (out / 'film.json').write_text(json.dumps(dict(before, title='half done')))
    films._write(film_id, status='remixing', worker=999999)
    assert films.status(film_id)['status'] == 'ready'
    assert films.get_film(film_id)['title'] == before['title'] and not (out / 'film.before.json').exists()


def test_engine_files_never_look_like_python_modules(tmp_path, monkeypatch):
    # The dev server reloads on .py changes under backend/; an engine run must not cause that.
    monkeypatch.setattr(agents, '_claude', lambda folder, prompt: (folder / 'film.json').write_text(json.dumps(FILM)))
    agents.write(tmp_path, 'claude', task='x')
    assert not list(tmp_path.glob('*.py')) and (tmp_path / 'check_film').exists()
