"""Licensed background music from Openverse (free, no key: about 20 searches a minute, 200 a day).

Only tracks that allow commercial use and editing (CC0, CC BY, CC BY-SA) are offered. Every download
keeps its licence and credit line next to the file, so exports can carry a correct attribution.
"""
import hashlib
import json
import re
import time
from pathlib import Path

import requests

from app.core.config import settings

API = 'https://api.openverse.org/v1/audio/'  # Anonymous requests may ask for at most 20 results per page.
CACHE = settings.projects_dir.parent / 'music_cache'
SEARCH_TTL = 7 * 24 * 3600
HEADERS = {'User-Agent': 'ResolveCompanion/1.0 (local video editor)'}

# Moods map to search phrases that reliably return instrumental beds.
# Moods are plain genre words: Jamendo (finished music) matches them directly.
MOODS = {mood: mood for mood in ('cinematic', 'inspiring', 'corporate', 'electronic', 'upbeat', 'lofi', 'calm')}


# Titles that mark a track as unusable under a brand or talking-head edit.
UNSUITABLE = re.compile(r'\b(vocals?|singing|lyrics|voice|speech|horror|scary|creepy|thriller|evil|curse|witch|demon|death|battle|war|scream|glitch|noise|'
                        r'field recording|underwater|stream|rain|wind|birds?|forest|ocean|waves|traffic|crowd|drone|siren|alarm|sfx|effect)\b', re.I)


def credit_required(license_code):
    return license_code != 'cc0'


def _track(result):
    return {'id': result['id'], 'title': result.get('title') or 'Untitled', 'creator': result.get('creator') or 'Unknown',
            'license': result.get('license'), 'license_version': result.get('license_version'), 'license_url': result.get('license_url'),
            'attribution': result.get('attribution') or '', 'credit_required': credit_required(result.get('license')),
            'duration': round((result.get('duration') or 0) / 1000, 1), 'preview_url': result.get('url'),
            'filetype': result.get('filetype'), 'source': result.get('source'), 'landing_url': result.get('foreign_landing_url')}


def search(query=None, mood=None, min_seconds=0, limit=12):
    """Instrumental tracks for a phrase or mood that allow commercial use and modification, CC0 first."""
    phrase = (query or MOODS.get(mood or '', '') or MOODS['cinematic']).strip()[:80]
    key = hashlib.sha1(f'v2|{phrase}|{min_seconds}'.encode()).hexdigest()[:16]  # Bump the prefix when search rules change.
    cached = CACHE / 'searches' / f'{key}.json'
    if cached.exists() and time.time() - cached.stat().st_mtime < SEARCH_TTL:
        results = json.loads(cached.read_text())
    else:
        # Jamendo first (finished music), then the whole index. Openverse's category filter misses most
        # tracks, so length and title separate music beds from effects and recordings.
        results = []
        for source in ('jamendo', None):
            params = {'q': phrase, 'license_type': 'commercial,modification', 'page_size': 20, 'mature': 'false'}
            if source: params['source'] = source
            response = requests.get(API, params=params, headers=HEADERS, timeout=20)
            if response.status_code == 429:
                raise RuntimeError('The free music search limit was reached; try again in a minute.')
            response.raise_for_status()
            results += [_track(r) for r in response.json().get('results', []) if r.get('url') and r['id'] not in {t['id'] for t in results}]
        cached.parent.mkdir(parents=True, exist_ok=True); cached.write_text(json.dumps(results))
    # Jamendo reports MP3 as "mp32"; Wikimedia audio is mostly recorded speech and interviews.
    usable = [t for t in results if t['duration'] >= max(min_seconds, 20) and (t['filetype'] or 'mp3')[:3] in ('mp3', 'ogg', 'wav', 'fla')
              and t['source'] != 'wikimedia_audio' and not UNSUITABLE.search(t['title'])]
    # Jamendo hosts finished music; sound libraries mostly hold recordings and effects.
    usable.sort(key=lambda t: t['source'] != 'jamendo')  # Stable: Openverse's relevance order is kept within each source.
    return usable[:limit]


def lookup(track_id):
    """Track details from Openverse by id, used before downloading a choice made in the editor."""
    if not re.fullmatch(r'[0-9a-f-]{36}', track_id or ''): raise ValueError('Invalid music id')
    response = requests.get(f'{API}{track_id}/', headers=HEADERS, timeout=20)
    response.raise_for_status()
    return _track(response.json())


def download(track):
    """The track's local file, downloading it once. Its licence and credit are kept beside it."""
    if not re.fullmatch(r'[0-9a-f-]{36}', track.get('id') or ''): raise ValueError('Invalid music id')
    folder = CACHE / 'tracks'; folder.mkdir(parents=True, exist_ok=True)
    kind = (track.get('filetype') or 'mp3')[:3]
    suffix = {'mp3': '.mp3', 'ogg': '.ogg', 'wav': '.wav', 'fla': '.flac'}.get(kind, '.mp3')
    path = folder / (track['id'] + suffix)
    if not path.exists():
        response = requests.get(track['preview_url'], headers=HEADERS, timeout=60)
        response.raise_for_status()
        if not response.content or len(response.content) < 10000: raise RuntimeError('Music file could not be downloaded.')
        temp = path.with_suffix('.part'); temp.write_bytes(response.content); temp.replace(path)
    (folder / (track['id'] + '.json')).write_text(json.dumps(track, indent=2, ensure_ascii=False))
    return path


def local_file(track_id):
    if not re.fullmatch(r'[0-9a-f-]{36}', track_id or ''): return None
    return next((p for p in (CACHE / 'tracks').glob(track_id + '.*') if p.suffix not in ('.json', '.part')), None)


def pick(mood, seconds):
    """The first usable track for a mood that covers `seconds`, downloaded; None if the search fails."""
    try:
        for track in search(mood=mood, min_seconds=seconds) or search(mood=mood):
            try: return track, download(track)
            except (requests.RequestException, RuntimeError): continue
    except (requests.RequestException, RuntimeError):
        return None
    return None


def bed_filter(index, start, length, volume, duck_source=None):
    """ffmpeg filter for one music bed: trimmed, placed, faded in and out, and lowered under speech.
    Returns (filter_text, output_label). `duck_source` is the label of the speech to duck under."""
    fade_out = max(0.0, length - 1.5)
    chain = (f'[{index}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{length:.3f},asetpts=PTS-STARTPTS,'
             f'afade=t=in:d=0.6,afade=t=out:st={fade_out:.3f}:d=1.5,volume={volume:.3f},adelay={int(start * 1000)}|{int(start * 1000)}')
    if duck_source:
        # Sidechain: the voice pushes the music down about 10 dB while someone is talking.
        return (f'{chain}[bed{index}];[{duck_source}]asplit=2[voice{index}][key{index}];'
                f'[bed{index}][key{index}]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350[ducked{index}]',
                f'[ducked{index}]', f'[voice{index}]')
    return f'{chain}[bed{index}]', f'[bed{index}]', None
