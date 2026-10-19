"""Never run test fixtures against the user's projects or SQLite index."""
import os
import tempfile
from pathlib import Path
_TEST_DIR=Path(tempfile.mkdtemp(prefix='davinci-tests-'))
os.environ['COMPANION_DATA']=str(_TEST_DIR/'projects')
os.environ['DATABASE_URL']='sqlite:///'+str(_TEST_DIR/'tests.sqlite3')

os.environ['COMPANION_TEST_MODE']='1'
os.environ['COMPANION_CREDENTIAL_FILE']=str(_TEST_DIR/'private'/'credentials.json')
# Test processes must not inherit real provider secrets from the launching shell.
for _key in ('GEMINI_API_KEY','GOOGLE_API_KEY','PEXELS_API_KEY','PIXABAY_API_KEY','TWELVE_LABS_API_KEY'):
    os.environ.pop(_key, None)
# Designed sound effects render slowly on first use; tests use the built-in cues unless they opt in.
os.environ['COMPANION_DESIGNED_SFX']='0'
