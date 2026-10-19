"""Designed sound effects from code (Earshot recipes, MIT): every sample is synthesised, nothing recorded.

Earshot's recipes render from their own tuned defaults without its analysis models, so only the light
part is used. Each (sound, variant) renders once and is cached as a 48 kHz stereo WAV; some recipes take
seconds to render. When Earshot is not installed, callers fall back to the tool's simpler built-in cues.
"""
import importlib
import os
import re
from pathlib import Path

import numpy as np

from app.core.config import settings

CACHE = settings.projects_dir.parent / 'sound_cache'
RATE = 48000

# What each sound is for, so editors and the AI can choose by meaning.
SOUNDS = {
    'whoosh': 'fast air pass-by for a cut or a camera move',
    'swish': 'short soft swish for a small element sliding in',
    'swipe': 'swipe for a card or panel moving across',
    'impact': 'deep hit for a big reveal or a number landing',
    'sting': 'short musical sting for a logo or a key line',
    'riser': 'rising build into a reveal (about 2.6 s)',
    'downlifter': 'falling sweep out of a peak (about 2.6 s)',
    'subdrop': 'low sub boom under a cut',
    'shimmer': 'bright sparkle for a highlight or a logo shine',
    'pop': 'small pop for a dot or icon appearing',
    'popin': 'UI pop for an element appearing',
    'click': 'tiny UI click',
    'toggle': 'switch toggle',
    'keypress': 'single keyboard key press',
    'typing': 'one typing tick, repeated for text being typed',
    'notify': 'notification chime',
    'pluck': 'plucked tonal note',
    'glitch': 'digital glitch burst',
    'hover': 'soft UI hover tick',
    'zip': 'zip-like fast sweep',
}
# Names used by the tool before the library existed.
ALIASES = {'paper': 'swish', 'highlight': 'shimmer', 'typewriter': 'typing'}


def available():
    try:
        importlib.import_module('earshot.forge.recipes.whoosh')
        return True
    except Exception:
        return False


def name_of(kind):
    kind = ALIASES.get(kind, kind)
    return kind if kind in SOUNDS else None


def path(kind, variant=0):
    """The cached WAV for a sound, rendering it on first use; None when the sound cannot be made."""
    name = name_of(kind)
    if not name or not re.fullmatch(r'\d{1,3}', str(variant)) or os.getenv('COMPANION_DESIGNED_SFX') == '0': return None
    out = CACHE / f'{name}_{int(variant)}.wav'
    if out.exists(): return out
    try:
        import soundfile
        recipe = importlib.import_module(f'earshot.forge.recipes.{name}')
        audio = np.asarray(recipe.render(dict(recipe.DEFAULTS), np.random.default_rng(int(variant) + 1)), dtype=np.float32)
    except Exception:
        return None
    if audio.ndim == 1: audio = np.stack([audio, audio], axis=1)
    if audio.shape[0] <= 2 and audio.shape[1] > 2: audio = audio.T
    rate = getattr(recipe, 'SR', RATE)
    if rate != RATE:
        import soxr
        audio = soxr.resample(audio, rate, RATE)
    peak = float(np.max(np.abs(audio))) or 1.0
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = out.with_suffix('.part.wav')
    soundfile.write(temp, (audio / peak * .89).astype(np.float32), RATE, subtype='PCM_16')
    temp.replace(out)
    (CACHE / 'SOURCE.txt').write_text('Sounds synthesised in code by Earshot recipes (MIT, github.com/Leonxlnx/earshot). No recorded audio.\n')
    return out


def load(kind, variant=0, rate=RATE, mono=False):
    """A sound as float samples at `rate`, or None."""
    wav = path(kind, variant)
    if not wav: return None
    import soundfile
    audio, sr = soundfile.read(wav, dtype='float32', always_2d=True)
    if sr != rate:
        import soxr
        audio = soxr.resample(audio, sr, rate)
    return audio.mean(axis=1) if mono else audio


def catalogue():
    return [{'name': name, 'use': use} for name, use in SOUNDS.items()]
