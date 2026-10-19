"""Licensed music beds: search filtering, licence keeping, and ducking under speech (real ffmpeg, no network)."""
import subprocess
import numpy as np
from app.core.config import settings
from app.services import music_service


def result(id_, title, license_, seconds, filetype='mp3'):
    return {'id': id_, 'title': title, 'creator': 'someone', 'license': license_, 'license_version': '1.0', 'license_url': '',
            'attribution': f'"{title}" by someone', 'duration': seconds * 1000, 'url': 'https://cdn.test/a.mp3', 'filetype': filetype,
            'source': 'freesound', 'foreign_landing_url': ''}


def test_search_keeps_long_instrumental_tracks_cc0_first(monkeypatch, tmp_path):
    monkeypatch.setattr(music_service, 'CACHE', tmp_path)
    rows = [result('a', 'Bright Day', 'by', 120), result('b', 'Swoosh', 'cc0', 2), result('c', 'Calm Piano', 'cc0', 90),
            result('d', 'Song with vocals', 'cc0', 200), result('e', 'Short loop', 'cc0', 25)]
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {'results': rows}
    calls = []
    monkeypatch.setattr(music_service.requests, 'get', lambda *a, **kw: calls.append(kw['params']) or Response())
    tracks = music_service.search(mood='calm', min_seconds=30)
    assert [t['title'] for t in tracks] == ['Bright Day', 'Calm Piano'] # Relevance order kept; effects, vocals and short loops dropped.
    assert tracks[0]['credit_required'] and not tracks[1]['credit_required'] and tracks[0]['attribution'] # CC BY needs a credit; CC0 does not.
    assert calls[0]['license_type'] == 'commercial,modification' and calls[0]['page_size'] <= 20 and calls[0]['source'] == 'jamendo'
    music_service.search(mood='calm', min_seconds=30)
    assert len(calls) == 2 # Jamendo, then the whole index; repeats come from the cache, sparing the free daily limit.


def test_music_bed_fades_in_and_ducks_under_speech(tmp_path):
    voice, bed, out = tmp_path / 'voice.wav', tmp_path / 'bed.wav', tmp_path / 'out.raw'
    subprocess.run([settings.ffmpeg_bin, '-v', 'error', '-y', '-f', 'lavfi', '-i', "aevalsrc='0.3*sin(2*PI*300*t)*lt(mod(t,2),1)':s=48000:d=8", str(voice)], check=True)
    subprocess.run([settings.ffmpeg_bin, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=f=880:sample_rate=48000:d=8', str(bed)], check=True)
    def music_levels(duck):
        text, label, voice_out = music_service.bed_filter(1, 0, 8, .5, '0:a' if duck else None)
        graph = text + (f';{voice_out}anullsink' if voice_out else '') + f';{label}lowpass=f=1500,highpass=f=600[m]'
        subprocess.run([settings.ffmpeg_bin, '-v', 'error', '-y', '-i', str(voice), '-i', str(bed), '-filter_complex', graph,
                        '-map', '[m]', '-ac', '1', '-ar', '16000', '-f', 's16le', str(out)], check=True)
        m = np.fromfile(out, dtype='<i2').astype(float) / 32768
        db = lambda a, b: 20 * np.log10(np.sqrt(np.mean(m[int(a * 16000):int(b * 16000)] ** 2)) + 1e-9)
        return db(2.3, 2.9), db(3.5, 3.95), db(0, .1)
    talking, pause, start = music_levels(True)
    plain_talking, plain_pause, _ = music_levels(False)
    assert 6 < pause - talking < 20 # Clearly lower under speech, not muted.
    assert abs(pause - plain_pause) < 1.5 and abs(plain_talking - plain_pause) < 1 # Full level again in pauses.
    assert start < pause - 15 # Fades in rather than starting at full level.
