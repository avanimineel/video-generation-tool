"""Local, deterministic transition sounds; no stock licensing or cloud dependency."""
import wave
import numpy as np
from app.core.config import settings

RATE=24000

def cue_samples(kind):
    # Designed sounds from the sound library when available; the simple synths below are the fallback.
    from app.services import sound_library
    designed = sound_library.load(kind, rate=RATE, mono=True) if sound_library.name_of(kind) else None
    if designed is not None:
        return designed * .32
    return _builtin_samples(kind)


def _builtin_samples(kind):
    if kind == 'highlight':
        length = .26
        t = np.arange(int(RATE * length)) / RATE
        envelope = np.exp(-t * 16)
        # Harmonious bright glass chime (E6 1318.5Hz + B6 1975.5Hz) with subtle initial transient
        tone = 0.65 * np.sin(2 * np.pi * 1318.5 * t) + 0.35 * np.sin(2 * np.pi * 1975.5 * t)
        noise = np.random.default_rng(17).normal(0, 0.04, len(t)) * np.exp(-t * 40)
        return (tone + noise) * envelope * .085
    elif kind in ('whoosh', 'paper'):
        length = {'whoosh': .32, 'paper': .18}[kind]
        t = np.arange(int(RATE * length)) / RATE
        envelope = np.sin(np.pi * t / length) ** 2
        noise = np.random.default_rng(17).normal(0, 1, len(t))
        return np.convolve(noise, np.ones(3 if kind == 'paper' else 15) / (3 if kind == 'paper' else 15), mode='same') * envelope * .085
    elif kind == 'typewriter':
        length = .08
        t = np.arange(int(RATE * length)) / RATE
        envelope = np.exp(-t * 80)
        return (np.sin(2 * np.pi * 1400 * t) * 0.5 + np.random.default_rng(42).normal(0, 0.4, len(t))) * envelope * .06
    elif kind == 'pop':
        length = .10
        t = np.arange(int(RATE * length)) / RATE
        envelope = np.exp(-t * 50)
        return np.sin(2 * np.pi * (600 - 400 * t / length) * t) * envelope * .07
    else:  # tap
        length = .12
        t = np.arange(int(RATE * length)) / RATE
        envelope = np.sin(np.pi * t / length) ** 2
        return np.sin(2 * np.pi * (700 * t - 900 * t * t)) * envelope * .055

def sound_cues(graphics, duration):
    """Sound follows an identifiable animation, never the mere presence of media.
    A highlight SFX must ONLY occur when a highlight animation is there."""
    cues = []
    for g in sorted(graphics, key=lambda g: g.start):
        p = g.parameters
        if p.get('sfx_muted'): continue
        style = p.get('title_style')
        events = []
        if p.get('highlight_animation') is True or p.get('highlight_active') is True or (g.template_id == 'article_reconstruction' and p.get('show_highlight') is not False and not p.get('show_full_page_image') and bool(p.get('paragraph') or p.get('highlight_quote'))):
            events = [(g.start + float(p.get('highlight_offset', 0)), 'highlight')]
        elif g.template_id == 'kinetic_typography':
            if style == 'typewriter':
                text = str(p.get('headline') or g.title).rstrip('|')
                typing = max(.4, (g.end - g.start) * .65)
                events = [(g.start + i * .11, 'typewriter') for i in range(int(typing / .11))]
            elif style == 'paper': events = [(g.start, 'paper')]
            elif style in ('bold_pop', 'editorial'): events = [(g.start, 'pop')]
        elif g.template_id == 'source_reframe' and p.get('motion_curve') == 'hold':
            events = [(g.start, 'whoosh')]  # A hard punch-in is a cut the viewer can hear.
        for at, kind in events:
            if 0 <= at < min(g.end, duration):
                cues.append({'start': round(at, 3), 'kind': kind, 'graphic_id': g.id})
    # Avoid stacked sounds from overlapping visual layers.
    result = []
    for cue in sorted(cues, key=lambda c: c['start']):
        if result and cue['start'] - result[-1]['start'] < .08: continue
        # Pops and whooshes stay sparse; a sound on every change is noise.
        previous = next((c for c in reversed(result) if c['kind'] in ('pop', 'whoosh')), None)
        if cue['kind'] in ('pop', 'whoosh') and previous and cue['start'] - previous['start'] < 1.5: continue
        result.append(cue)
    return result


def prepare_sfx(project_id, graphics, duration):
    cues = sound_cues(graphics, duration)
    for g in graphics:
        g.parameters.pop('sfx_track_url', None)
        g.parameters.pop('sfx_cues', None)
    if not cues: return None
    path = settings.projects_dir / project_id / 'assets' / 'automatic_sfx.wav'
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.zeros(max(1, int(duration * RATE)), dtype=np.float32)
    for cue in cues:
        start = max(0, int(cue['start'] * RATE))
        sound = cue_samples(cue['kind'])
        n = min(len(sound), len(samples) - start)
        if n > 0: samples[start:start + n] += sound[:n]
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((np.clip(samples, -.28, .28) * 32767).astype('<i2').tobytes())
    import hashlib
    version = hashlib.sha256(str(cues).encode()).hexdigest()[:12]
    url = f'/api/media/{project_id}/asset/automatic_sfx.wav?v={version}'
    for g in graphics:
        g.parameters.pop('sfx_track_url', None)
    graphics[0].parameters['sfx_track_url'] = url
    graphics[0].parameters['sfx_cues'] = cues
    return path
