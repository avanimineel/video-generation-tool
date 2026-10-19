"""Record the brand film: pose the HTML stage at each frame in Chrome and encode the frames with ffmpeg.

Every frame is a pure function of time (window.seek), so the same plan always renders the same film.
"""
import json
import subprocess
import wave
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np

from app.core.config import settings
from app.services import music_service

STAGE = Path(__file__).with_name('stage.html')
SIZES = {'16:9': (1920, 1080), '9:16': (1080, 1920), '1:1': (1080, 1080)}
FPS = 30
# Each art direction gets a fitting music mood.
MOODS = {'editorial': 'cinematic', 'clean': 'corporate', 'tech': 'electronic', 'bold': 'upbeat'}


def font_links(kit):
    """Google Fonts for the brand's own type when Google serves it; system fallbacks otherwise."""
    families = []
    heading, body = kit['fonts'].get('heading_google'), kit['fonts'].get('body_google')
    if heading: families.append(f'family={quote_plus(heading)}:ital@0;1')
    if body and body != heading: families.append(f'family={quote_plus(body)}:wght@400;500;600')
    families.append('family=JetBrains+Mono:wght@400;500')
    return f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{"&".join(families)}&display=block">'


def stage_html(kit, plan, folder):
    colors, fonts = kit['colors'], kit['fonts']
    heading = f"'{fonts['heading']}', Georgia, serif" if fonts.get('heading') else "Georgia, serif"
    body = f"'{fonts['body']}', 'Helvetica Neue', Arial, sans-serif" if fonts.get('body') else "'Helvetica Neue', Arial, sans-serif"
    accent = colors['accent'].lstrip('#'); r, g, b = (int(accent[i:i + 2], 16) for i in (0, 2, 4))
    on_accent = '#111111' if (.2126 * r + .7152 * g + .0722 * b) / 255 > .55 else '#ffffff'  # Readable text on the brand colour.
    tokens = (f"<style>:root{{--bg:{colors['background']};--text:{colors['text']};--accent:{colors['accent']};--on-accent:{on_accent};"
              f"--heading:{heading};--body:{body};}}</style>")
    # Paths become relative to the stage file so Chrome can load the brand's own images.
    def local(path):
        return Path(path).resolve().relative_to(folder.resolve()).as_posix() if path and Path(path).resolve().is_relative_to(folder.resolve()) else path
    scenes = []
    for scene in plan['scenes']:
        scene = dict(scene)
        if scene['type'] == 'wall': scene['images'] = [local(p) for p in scene['images']]
        if scene['type'] == 'photo': scene['image'] = local(scene['image'])
        if scene['type'] == 'end' and scene.get('logo'): scene['logo'] = local(scene['logo'])
        scenes.append(scene)
    # Brand tokens go after the stage's defaults so the brand always wins.
    html = STAGE.read_text().replace('<!--FONTS-->', font_links(kit)).replace('<!--TOKENS-->', tokens)
    return html.replace('/*PLAN*/null', json.dumps(dict(plan, scenes=scenes), ensure_ascii=False))


def plan_cues(plan):
    """Sound cues for a template film: whooshes on hand-overs, pops on key presses and counters."""
    cues, cursor = [], 0.0
    for index, scene in enumerate(plan['scenes']):
        if index: cues.append({'t': cursor - .2, 'kind': 'whoosh', 'gain': 1.4 if scene.get('transition_in') == 'whip' else .8})
        if scene['type'] == 'cards':
            per = (scene['duration'] - 1.0) / max(1, len(scene['items']))
            cues += [{'t': cursor + .7 + step * per + .03, 'kind': 'pop', 'gain': .9} for step in range(len(scene['items']))]
        if scene['type'] == 'counters':
            cues += [{'t': cursor + .3 + i * .55, 'kind': 'pop'} for i in range(len(scene['items']))]
        cursor += scene['duration']
    return cues


def sound_track(cues, total, path, rate=24000):
    """Mix the tool's own synthesised cues (whoosh, pop, paper, typewriter, highlight) into one WAV."""
    from app.services.automatic_sfx import cue_samples
    samples = np.zeros(int(total * rate) + rate, dtype=np.float32)
    for cue in cues:
        try: sound = cue_samples(cue.get('kind', 'pop')) * float(cue.get('gain', 1.0))
        except Exception: continue
        start = int(max(0, float(cue['t'])) * rate); n = min(len(sound), len(samples) - start)
        if n > 0: samples[start:start + n] += sound[:n]
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate)
        out.writeframes((np.clip(samples, -.3, .3) * 32767).astype('<i2').tobytes())
    return path


def record(page_path, aspect, output, progress=None):
    """Step any film page through time in Chrome (window.seek) and encode the frames. Returns its length."""
    from playwright.sync_api import sync_playwright
    width, height = SIZES.get(aspect, SIZES['16:9'])
    encoder = subprocess.Popen([settings.ffmpeg_bin, '-v', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(FPS), '-i', '-',
                                '-vf', 'scale=in_range=pc:out_range=tv', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-movflags', '+faststart', str(output)],
                               stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with sync_playwright() as p:
            chrome = p.chromium.launch(channel='chrome', headless=True, args=['--allow-file-access-from-files'])
            page = chrome.new_page(viewport={'width': width, 'height': height})
            page.goto(Path(page_path).resolve().as_uri(), wait_until='load')
            page.evaluate('document.fonts.ready.then(() => true)')
            page.wait_for_timeout(400)
            total = float(page.evaluate('window.TOTAL')); frames = int(total * FPS)
            for frame in range(frames):
                page.evaluate(f'window.seek({frame / FPS})')
                encoder.stdin.write(page.screenshot(type='jpeg', quality=92))
                if progress and frame % 15 == 0: progress(frame / frames)
            chrome.close()
    finally:
        encoder.stdin.close(); encoder.wait()
    if encoder.returncode != 0:
        raise RuntimeError('Video encoding failed: ' + encoder.stderr.read().decode(errors='replace')[-400:])
    return total


def finish(folder, silent, cues, total, mood='cinematic', music=True):
    """Add the cue sounds and a licensed music bed to a silent recording; writes film.mp4 and its credits."""
    folder = Path(folder); output = folder / 'film.mp4'
    audio = sound_track(cues, total, folder / 'sound.wav')
    inputs, graph = ['-i', str(silent), '-i', str(audio)], None
    picked = music_service.pick(mood, total) if music else None
    if picked:
        track, path = picked
        inputs += ['-i', str(path)]
        text, bed, _ = music_service.bed_filter(2, 0, total, .55)
        graph = f"{text};[1:a]aformat=sample_rates=48000:channel_layouts=stereo[fx];[fx]{bed}amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]"
        (folder / 'music.json').write_text(json.dumps(track, indent=2, ensure_ascii=False))
        (folder / 'CREDITS.txt').write_text(f"Music: {track['attribution']}\n" + ('' if track['credit_required'] else '(CC0: credit not required.)\n'))
    mapping = ['-filter_complex', graph, '-map', '0:v', '-map', '[a]'] if graph else ['-map', '0:v', '-map', '1:a']
    subprocess.run([settings.ffmpeg_bin, '-v', 'error', '-y', *inputs, *mapping, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', str(output)], check=True, capture_output=True)
    Path(silent).unlink(missing_ok=True)
    return output


def render(kit, plan, folder, progress=None, music=True):
    """Write stage.html for a template film, record it, and add sound and music."""
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    page_path = folder / 'stage.html'; page_path.write_text(stage_html(kit, plan, folder))
    silent = folder / 'film_silent.mp4'
    total = record(page_path, plan.get('aspect', '16:9'), silent, progress)
    return finish(folder, silent, plan_cues(plan), total, MOODS.get(plan.get('direction'), 'cinematic'), music)
