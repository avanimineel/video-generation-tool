"""Designed sound effects from code (Earshot recipes), rendered once and cached."""
import pytest
from app.services import sound_library


def test_designed_sounds_render_cache_and_fall_back(monkeypatch, tmp_path):
    if not sound_library.available(): pytest.skip('Earshot is not installed')
    monkeypatch.setenv('COMPANION_DESIGNED_SFX', '1')
    monkeypatch.setattr(sound_library, 'CACHE', tmp_path)
    first = sound_library.path('click', 0)
    assert first and first.exists() and first.stat().st_size > 1000
    assert sound_library.path('click', 0) == first  # Cached: the same file, not re-rendered.
    audio = sound_library.load('click', 0, rate=24000, mono=True)
    assert audio.ndim == 1 and 0.2 < abs(audio).max() <= 0.9
    assert sound_library.name_of('highlight') == 'shimmer' and sound_library.name_of('nonsense') is None
    assert sound_library.path('nonsense') is None and sound_library.path('click', '../x') is None
    monkeypatch.setenv('COMPANION_DESIGNED_SFX', '0')
    assert sound_library.path('pop', 0) is None  # Switched off: callers use the built-in cues.
