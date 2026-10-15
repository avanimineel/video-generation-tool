import os
from pathlib import Path
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECTS_DIR = Path(os.getenv("COMPANION_DATA", str(BASE_DIR / "projects")))
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# Provider credentials have one authoritative, private store. Tests select an
# isolated store before importing this module and never touch developer secrets.
import json
import tempfile
import threading
import fcntl
from contextlib import contextmanager

CREDENTIAL_KEYS = {'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'PEXELS_API_KEY', 'PIXABAY_API_KEY', 'TWELVE_LABS_API_KEY'}
CREDENTIAL_FILE = Path(os.getenv('COMPANION_CREDENTIAL_FILE', str(BASE_DIR / '.private' / 'credentials.json')))
_CONFIG_LOCK = threading.RLock()

def usable_key(value):
    value = (value or '').strip()
    return bool(value) and not any(marker in value.lower() for marker in
        ('testmock', 'placeholder', 'your_', 'test-key', 'test_key', 'working-fixture'))

@contextmanager
def credential_lock():
    CREDENTIAL_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with _CONFIG_LOCK, open(CREDENTIAL_FILE.with_suffix('.lock'), 'a') as lock:
        os.chmod(lock.name, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)

def read_credentials():
    if not CREDENTIAL_FILE.exists():
        return {}
    try:
        data = json.loads(CREDENTIAL_FILE.read_text())
        if not isinstance(data, dict):
            raise ValueError()
        return {k: v for k, v in data.items() if k in CREDENTIAL_KEYS and isinstance(v, str) and usable_key(v)}
    except (ValueError, OSError):
        raise RuntimeError('Saved provider credentials could not be read. Repair the private credential file; it has not been overwritten.') from None

def write_credentials(data):
    # Atomic replacement preserves the old file if writing fails or is interrupted.
    fd, filename = tempfile.mkstemp(dir=CREDENTIAL_FILE.parent, prefix='.credentials-')
    try:
        with os.fdopen(fd, 'w') as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(filename, CREDENTIAL_FILE)
    finally:
        if os.path.exists(filename):
            os.unlink(filename)

def reload_env():
    values = {}
    if os.getenv('COMPANION_TEST_MODE') != '1':
        for candidate in (BASE_DIR.parent / '.env', BASE_DIR / '.env'):
            if candidate.exists():
                for line in candidate.read_text().splitlines():
                    line = line.strip().removeprefix('export ')
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k, v = k.strip(), v.strip().strip('"').strip("'")
                        if k not in CREDENTIAL_KEYS or usable_key(v):
                            values[k] = v
    with credential_lock():
        saved = read_credentials()
        # One-time migration: placeholders can never replace a valid value.
        for key in CREDENTIAL_KEYS:
            candidate = os.getenv(key, '') if usable_key(os.getenv(key)) else values.get(key, '')
            if key not in saved and usable_key(candidate) and os.getenv('COMPANION_TEST_MODE') != '1':
                saved[key] = candidate
        if saved and not CREDENTIAL_FILE.exists():
            write_credentials(saved)
        elif saved and read_credentials() != saved:
            write_credentials(saved)
        values.update(saved)
        for key, value in values.items():
            os.environ[key] = value

def get_provider_key(name):
    reload_env()
    names = ('GEMINI_API_KEY', 'GOOGLE_API_KEY') if name == 'GEMINI_API_KEY' else (name,)
    return next((os.getenv(k, '').strip() for k in names if usable_key(os.getenv(k))), '')

def save_env_key(key: str, value: str):
    key, value = key.strip(), value.strip()
    if key not in CREDENTIAL_KEYS:
        raise ValueError('Unsupported provider credential name.')
    if not value:
        return  # Empty settings inputs do not clear an existing key.
    if not usable_key(value) or any(c in value for c in '\r\n'):
        raise ValueError('A placeholder or test API key cannot replace saved credentials. Enter a real provider key.')
    with credential_lock():
        saved = read_credentials()
        saved[key] = value
        write_credentials(saved)
        os.environ[key] = value  # Only update memory after a successful save.

reload_env()


# Prefer the tool's full FFmpeg distribution over unrelated application bundles.
import shutil
try:
    import imageio_ffmpeg
    DEFAULT_FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    bundled=list((Path(__file__).resolve().parents[2]/'vendor_runtime'/'imageio_ffmpeg'/'binaries').glob('ffmpeg-*'))
    DEFAULT_FFMPEG=str(bundled[0]) if bundled else (shutil.which('ffmpeg') or '/Applications/Free Download Manager.app/Contents/MacOS/ffmpeg')

RESOLVE_SCRIPT_MODULES = "/Applications/DaVinci Resolve.app/Contents/Resources/Developer/Scripting/Modules"
RESOLVE_FUSION_LIB = "/Applications/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
RESOLVE_SCRIPT_API = "/Applications/DaVinci Resolve.app/Contents/Resources/Developer/Scripting"

class Settings(BaseModel):
    app_name: str = "Resolve AI Editing Companion"
    version: str = "1.0.0"
    projects_dir: Path = PROJECTS_DIR
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/resolve_companion.db")
    )
    ffmpeg_bin: str = Field(default_factory=lambda: os.getenv("FFMPEG_BIN", DEFAULT_FFMPEG))
    resolve_modules_dir: str = RESOLVE_SCRIPT_MODULES
    resolve_fusion_lib: str = RESOLVE_FUSION_LIB
    resolve_script_api: str = RESOLVE_SCRIPT_API
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "*"
    ]

settings = Settings()
