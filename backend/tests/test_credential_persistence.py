import json
import os
import stat
import pytest
from app.core import config

@pytest.fixture
def vault(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'CREDENTIAL_FILE', tmp_path/'private'/'credentials.json')
    monkeypatch.setattr(config, 'BASE_DIR', tmp_path/'backend')
    monkeypatch.setenv('COMPANION_TEST_MODE', '1')
    for key in config.CREDENTIAL_KEYS:
        monkeypatch.setenv(key, "")
    return config.CREDENTIAL_FILE


def test_saved_key_survives_reload_and_placeholder_env(vault, monkeypatch):
    config.save_env_key('GEMINI_API_KEY','real-fixture-secret-123')
    monkeypatch.setenv('GEMINI_API_KEY','AIzaTestMockKey')
    assert config.get_provider_key('GEMINI_API_KEY')=='real-fixture-secret-123'
    assert stat.S_IMODE(vault.stat().st_mode)==0o600


def test_bad_or_empty_save_does_not_replace(vault):
    config.save_env_key('GEMINI_API_KEY','real-fixture-secret-123')
    before=vault.read_bytes()
    config.save_env_key('GEMINI_API_KEY','')
    with pytest.raises(ValueError):config.save_env_key('GEMINI_API_KEY','AIzaTestMockKey')
    assert vault.read_bytes()==before


def test_failed_write_preserves_file_and_memory(vault,monkeypatch):
    config.save_env_key('GEMINI_API_KEY','real-fixture-secret-123')
    before=vault.read_bytes()
    def fail(*args):raise OSError('disk full')
    monkeypatch.setattr(config.os,'replace',fail)
    with pytest.raises(OSError):config.save_env_key('GEMINI_API_KEY','replacement-real-secret')
    assert vault.read_bytes()==before
    assert os.environ['GEMINI_API_KEY']=='real-fixture-secret-123'


def test_legacy_migration_skips_backend_placeholder(vault, monkeypatch):
    monkeypatch.setenv('COMPANION_TEST_MODE','0')
    config.BASE_DIR.mkdir()
    (config.BASE_DIR.parent/'.env').write_text('GEMINI_API_KEY="legacy-real-secret"\n')
    (config.BASE_DIR/'.env').write_text('GEMINI_API_KEY="AIzaTestMockKey"\n')
    assert config.get_provider_key('GEMINI_API_KEY')=='legacy-real-secret'
    (config.BASE_DIR.parent/'.env').unlink()
    monkeypatch.delenv('GEMINI_API_KEY')
    assert config.get_provider_key('GEMINI_API_KEY')=='legacy-real-secret'


def test_corrupt_store_is_not_silently_overwritten(vault):
    vault.parent.mkdir();vault.write_text('{broken')
    with pytest.raises(RuntimeError):config.save_env_key('GEMINI_API_KEY','real-fixture-secret')
    assert vault.read_text()=='{broken'


def test_google_alias_and_provider_share_lookup(vault):
    from app.services.media_providers.google_ai import GoogleAIProvider
    config.save_env_key('GOOGLE_API_KEY','alias-real-secret')
    assert GoogleAIProvider().get_api_key()==config.get_provider_key('GEMINI_API_KEY')=='alias-real-secret'


def test_fresh_process_reads_saved_key_without_dotenv(vault):
    import subprocess
    import sys
    from pathlib import Path
    config.save_env_key('GEMINI_API_KEY', 'restart-fixture-secret')
    env = dict(os.environ, COMPANION_CREDENTIAL_FILE=str(vault), COMPANION_TEST_MODE='1')
    env.pop('GEMINI_API_KEY', None)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run([sys.executable, '-c',
        "from app.core.config import get_provider_key; print(bool(get_provider_key('GEMINI_API_KEY')))"],
        env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == 'True'
