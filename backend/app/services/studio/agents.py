"""The two AI engines that write and remix films: Claude Code (headless, in the film folder) and Gemini.

Both receive the same task, the format reference (FORMAT.md) and the brief (BRIEF.md), and both must
produce a film.json that composition.validate() accepts. Claude Code also looks at its own work with the
folder's check_film and fixes what it sees; Gemini gets one repair round with the checker's problems.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

from app.services.studio import composition
from app.services.studio.check import inspect

FORMAT = Path(__file__).with_name('FORMAT.md')
ENGINES = ('claude', 'gemini')
CLAUDE_TIMEOUT = int(os.getenv('STUDIO_CLAUDE_TIMEOUT', '1500'))


def claude_bin():
    found = shutil.which('claude') or str(Path.home() / '.local/bin/claude')
    return found if Path(found).exists() else None


def available():
    from app.services.editorial_planner import configured_key
    return {'claude': bool(claude_bin()), 'gemini': bool(configured_key('GEMINI_API_KEY'))}


DESIGN = """You are a motion designer making a brand film in the Studio film format.

Read FORMAT.md (the format and craft rules) and BRIEF.md (the brand, its words, numbers and images).
{task}

Then write the whole film to film.json in this folder. Use only facts from BRIEF.md and only image files
listed there. Run `python3 check_film` to draw the film: fix every problem it prints, then look at
check/sheet.png (and frames in check/) and judge them as an art director: is the brand recognisable, is
every line readable and inside the screen, does the camera travel through one space rather than cutting
between slides, is any moment empty? Improve the film and check again, up to three rounds. Finish when
check_film prints OK and the sheet looks right. Do not create other files."""

REMIX = """You are a motion designer remixing a film in the Studio film format.

Read FORMAT.md (the format and craft rules), BRIEF.md (the brand facts) and film.json (the current film).
Change the film according to this direction: {instruction}

Keep what the direction does not ask to change, keep every layer id that still exists so edits stay
traceable, and keep facts to those in BRIEF.md. Write the result to film.json. Run `python3 check_film`,
fix every problem it prints, look at check/sheet.png and improve until it prints OK and looks right
(up to three rounds). Do not create other files."""


def _claude(folder, prompt):
    binary = claude_bin()
    if not binary: raise RuntimeError('Claude Code is not installed on this computer (the `claude` command was not found).')
    env = dict(os.environ)
    env.pop('ANTHROPIC_API_KEY', None)  # Use the person's Claude Code sign-in, not a paid API key.
    tools = 'Read,Write,Edit,Bash(python3 check_film),Bash(python3 check_film *)'
    run = subprocess.run([binary, '-p', prompt, '--allowedTools', tools, '--permission-mode', 'acceptEdits', '--output-format', 'json'],
                         cwd=folder, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT)
    (Path(folder) / 'agent.log').write_text((run.stdout or '')[-20000:] + '\n' + (run.stderr or '')[-4000:])
    if run.returncode != 0:
        detail = (run.stderr or run.stdout or '').strip()[-400:]
        raise RuntimeError(f'Claude Code stopped with an error: {detail or run.returncode}')
    try:
        result = json.loads(run.stdout)
        if result.get('is_error'): raise RuntimeError(f"Claude Code could not finish: {str(result.get('result'))[:400]}")
    except json.JSONDecodeError:
        pass


def _gemini(folder, prompt):
    from app.services.editorial_planner import gemini_json
    folder = Path(folder)
    current = (folder / 'film.json').read_text() if (folder / 'film.json').exists() else ''
    text = (prompt.replace('Run `python3 check_film`', 'A checker will draw your film afterwards; aim for')
            + '\n\nReturn only the film JSON.\n\n# FORMAT.md\n' + FORMAT.read_text()
            + '\n\n# BRIEF.md\n' + (folder / 'BRIEF.md').read_text()
            + (f'\n\n# film.json (current)\n{current}' if current else ''))
    film = gemini_json(text, timeout=240)
    (folder / 'film.json').write_text(json.dumps(film, indent=1, ensure_ascii=False))
    problems, _ = inspect(folder)
    if problems:
        fix = (text + '\n\n# Your previous film.json\n' + json.dumps(film, ensure_ascii=False)
               + '\n\n# Problems the checker found; return the corrected film JSON\n- ' + '\n- '.join(problems))
        film = gemini_json(fix, timeout=240)
        (folder / 'film.json').write_text(json.dumps(film, indent=1, ensure_ascii=False))


def write(folder, engine, task=None, instruction=None):
    """Have an engine design (task) or remix (instruction) the film in `folder`; returns the validated film."""
    if engine not in ENGINES: raise ValueError(f'Unknown engine {engine}; choose claude or gemini.')
    folder = Path(folder)
    shutil.copy(FORMAT, folder / 'FORMAT.md')
    backend = Path(__file__).resolve().parents[3]
    # No .py suffix: the dev server reloads on .py changes under backend/, which would kill the run.
    (folder / 'check_film').write_text(f'import sys\nsys.path.insert(0, {str(backend)!r})\nfrom app.services.studio.check import main\nmain()\n')
    prompt = REMIX.format(instruction=instruction) if instruction else DESIGN.format(task=task or 'Design the film.')
    (_claude if engine == 'claude' else _gemini)(folder, prompt)
    path = folder / 'film.json'
    if not path.exists(): raise RuntimeError('The engine finished without writing film.json.')
    return composition.validate(json.loads(path.read_text()), folder)
