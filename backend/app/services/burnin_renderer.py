import os
import re
import math
import hashlib
import urllib.request
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import io
import av
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import resvg_py
from app.core.config import settings
from app.core.models import ProjectState, CaptionItem, MotionGraphicItem

MEDICAL_CONDITIONS = {
    'cancer', 'diabetes', 'hypertension', 'stroke', 'tumor', 'inflammation',
    'alzheimer', "alzheimer's", 'arrhythmia', 'sepsis', 'infection', 'dementia',
    'cholesterol', 'sclerosis', 'syndrome', 'disease', 'chronic', 'acute',
    'myocardial', 'infarction', 'cardiovascular', 'osteoporosis', 'arthritis'
}

ORGANS = {
    'heart', 'brain', 'gut', 'liver', 'kidney', 'kidneys', 'lungs', 'lung',
    'pancreas', 'artery', 'arteries', 'neurons', 'neuron', 'mitochondria',
    'spine', 'vessels', 'vessel', 'blood', 'cells', 'cell', 'microbiome'
}

EMOTIONAL_TRIGGERS = {
    'fatal', 'lethal', 'danger', 'breakthrough', 'miracle', 'critical',
    'emergency', 'toxic', 'cure', 'alert', 'warning', 'deadly', 'shocking',
    'secret', 'destroy', 'boost', 'protect'
}

def hex_to_rgb(hex_str: Optional[str], default: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    if not hex_str:
        return default
    clean = hex_str.lstrip('#')
    if len(clean) >= 6:
        try:
            return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
        except Exception:
            return default
    return default

def check_is_keyword(word_str: str) -> Tuple[bool, Optional[str], Tuple[int, int, int]]:
    clean = re.sub(r'[^a-z0-9%]', '', word_str.lower())
    if re.search(r'\d+[%xXmgkK]?', word_str) or clean in ['double', 'triple', 'half', 'percent', 'zero']:
        return (True, 'metric', (0, 240, 255))  # Cyan
    if clean in MEDICAL_CONDITIONS or any(c in clean for c in ['cancer', 'diabet', 'inflam', 'hyperten', 'stroke', 'tumor']):
        return (True, 'condition', (255, 77, 77))  # Red
    if clean in ORGANS or any(o in clean for o in ['cardio', 'neuro', 'mitochondr']):
        return (True, 'organ', (204, 255, 0))  # Lime
    if clean in EMOTIONAL_TRIGGERS:
        return (True, 'impact', (255, 184, 0))  # Amber
    return (False, None, (255, 255, 255))

def render_bounding_box_svg(
    box_w: int,
    box_h: int,
    stroke_color: str = "#E04F26",
    stroke_width: int = 2,
    handle_size: int = 8,
    padding: int = 4
) -> Image.Image:
    """Renders a 2px wireframe bounding box with 4 corner handle squares using resvg-py."""
    handle_half = handle_size / 2.0
    w = int(box_w + padding * 2 + handle_size)
    h = int(box_h + padding * 2 + handle_size)

    rx = padding + handle_half
    ry = padding + handle_half
    rw = box_w
    rh = box_h

    tl_x, tl_y = rx - handle_half, ry - handle_half
    tr_x, tr_y = rx + rw - handle_half, ry - handle_half
    bl_x, bl_y = rx - handle_half, ry + rh - handle_half
    br_x, br_y = rx + rw - handle_half, ry + rh - handle_half

    svg = f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="none" stroke="{stroke_color}" stroke-width="{stroke_width}"/>
  <rect x="{tl_x}" y="{tl_y}" width="{handle_size}" height="{handle_size}" fill="{stroke_color}"/>
  <rect x="{tr_x}" y="{tr_y}" width="{handle_size}" height="{handle_size}" fill="{stroke_color}"/>
  <rect x="{bl_x}" y="{bl_y}" width="{handle_size}" height="{handle_size}" fill="{stroke_color}"/>
  <rect x="{br_x}" y="{br_y}" width="{handle_size}" height="{handle_size}" fill="{stroke_color}"/>
</svg>"""

    png_bytes = resvg_py.svg_to_bytes(svg)
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


class FontManager:
    def __init__(self):
        self._cache: Dict[Tuple[str, int], ImageFont.ImageFont] = {}
        self.arial_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        self.arial_black_path = "/System/Library/Fonts/Supplemental/Arial Black.ttf" if os.path.exists("/System/Library/Fonts/Supplemental/Arial Black.ttf") else "/System/Library/Fonts/Supplemental/Impact.ttf"
        self.georgia_path = "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf"
        self.mono_path = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"
        self.regular_path = "/System/Library/Fonts/Supplemental/Arial.ttf"

    def get_font(self, font_type: str, size: int) -> ImageFont.ImageFont:
        key = (font_type, size)
        if key in self._cache:
            return self._cache[key]

        path = self.arial_path
        if font_type in ('display', 'display_bold', 'geometric_bold'):
            path = self.arial_black_path
        elif font_type in ('serif', 'italic_serif'):
            path = self.georgia_path
        elif font_type == 'script':
            path='/System/Library/Fonts/Supplemental/SnellRoundhand.ttc'
        elif font_type == 'mono':
            path = self.mono_path
        elif font_type == 'regular':
            path = self.regular_path
        # Editorial pair: a medium grotesque with a high-contrast italic serif accent.
        index = 0
        if font_type == 'editorial_sans' and os.path.exists('/System/Library/Fonts/HelveticaNeue.ttc'):
            path, index = '/System/Library/Fonts/HelveticaNeue.ttc', 10
        elif font_type == 'editorial_serif':
            # A semibold italic keeps its thin strokes readable over skin and light walls.
            if os.path.exists('/System/Library/Fonts/Supplemental/Baskerville.ttc'):
                path, index = '/System/Library/Fonts/Supplemental/Baskerville.ttc', 5
            else:
                path = self.georgia_path

        try:
            if os.path.exists(path):
                font = ImageFont.truetype(path, size, index=index)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        self._cache[key] = font
        return font

class VideoClipPlayer:
    """Pre-decodes and caches video frames for smooth, zero-seek B-roll compositing."""
    def __init__(self, filepath: str, target_w: int, target_h: int):
        self.filepath = filepath
        self.target_w = target_w
        self.target_h = target_h
        self.frames: List[Image.Image] = []
        self._load()

    def _load(self):
        try:
            container = av.open(self.filepath)
            video_stream = container.streams.video[0]
            for frame in container.decode(video_stream):
                img = frame.to_image()
                cropped = crop_to_aspect(img, self.target_w, self.target_h)
                self.frames.append(cropped)
                if len(self.frames) >= 900:  # Cap to 30s @ 30fps
                    break
        except Exception as e:
            print(f"[VideoClipPlayer] Failed to load {self.filepath}: {e}")

    def get_frame(self, relative_t: float, fps: float = 30.0) -> Optional[Image.Image]:
        if not self.frames:
            return None
        idx = int(relative_t * fps)
        if idx < 0:
            idx = 0
        idx = idx % len(self.frames)
        return self.frames[idx]

def resolve_media_file(raw_url: Optional[str], project_id: str, download_dir: Path) -> Optional[Path]:
    if not raw_url:
        return None
    p = Path(raw_url)
    if p.exists() and p.is_file():
        return p
    pdir = settings.projects_dir / project_id
    if (pdir / raw_url).exists() and (pdir / raw_url).is_file():
        return pdir / raw_url
    
    # Custom uploads directory
    if (pdir / "assets" / raw_url).exists() and (pdir / "assets" / raw_url).is_file():
        return pdir / "assets" / raw_url

    # Check by filename across local asset directories
    fname = raw_url.split('/')[-1].split('?')[0]
    for check_dir in [pdir / "assets", download_dir, pdir]:
        cand = check_dir / fname
        if cand.exists() and cand.is_file():
            return cand

    # Handle local API endpoints: /api/media/{project_id}/asset/{fname}
    if '/asset/' in raw_url:
        for check_dir in [pdir / "assets", download_dir]:
            cand = check_dir / fname
            if cand.exists() and cand.is_file():
                return cand

    if raw_url.startswith(('http://', 'https://')):
        # If it's a localhost link to uploaded assets, resolve locally
        if 'localhost' in raw_url or '127.0.0.1' in raw_url:
            for check_dir in [pdir / "assets", download_dir]:
                cand = check_dir / fname
                if cand.exists() and cand.is_file():
                    return cand

        url_hash = hashlib.md5(raw_url.encode()).hexdigest()
        for ext in ['.mp4', '.mov', '.webm', '.jpg', '.jpeg', '.png', '.webp']:
            cand = download_dir / f"cache_{url_hash}{ext}"
            if cand.exists():
                return cand
        try:
            import requests
            ext = '.mp4' if any(ve in raw_url.lower() for ve in ['.mp4', 'video', '.mov', '.webm']) else '.jpg'
            cached_file = download_dir / f"cache_{url_hash}{ext}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(raw_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                with open(cached_file, 'wb') as f:
                    f.write(resp.content)
                return cached_file
        except Exception as e:
            print(f"[BurnInRenderer] Media download skipped for {raw_url[:50]}: {e}")
    return None

def crop_to_aspect(img: Image.Image, target_w: int, target_h: int, focus_y: float = 0.5, focus_x: float = 0.5) -> Image.Image:
    """Crops and resizes image to fill target_w x target_h with CSS object-position exact parity."""
    src_w, src_h = img.size
    target_aspect = target_w / target_h
    src_aspect = src_w / src_h

    if src_aspect > target_aspect:
        crop_w = int(src_h * target_aspect)
        crop_x = int(focus_x * (src_w - crop_w))
        crop_x = max(0, min(src_w - crop_w, crop_x))
        img_cropped = img.crop((crop_x, 0, crop_x + crop_w, src_h))
    else:
        crop_h = int(src_w / target_aspect)
        crop_y = int(focus_y * (src_h - crop_h))
        crop_y = max(0, min(src_h - crop_h, crop_y))
        img_cropped = img.crop((0, crop_y, src_w, crop_y + crop_h))

    return img_cropped.resize((target_w, target_h), Image.Resampling.BILINEAR)

def apply_source_reframe(image, graphics, t):
    item=next((g for g in graphics if g.template_id=='source_reframe'),None)
    if item is None:return image
    progress=max(0,min(1,(t-item.start)/max(.001,item.end-item.start)))
    if item.parameters.get('motion_curve') == 'pulse':
        import math
        progress = math.sin(math.pi * progress) ** 2
    elif item.parameters.get('motion_curve') == 'smoothstep':
        progress = progress * progress * (3 - 2 * progress)
    a=float(item.parameters.get('start_scale',1));b=float(item.parameters.get('end_scale',1.13))
    if item.parameters.get('motion_curve') == 'pulse': b = 1.08
    scale=max(1,min(1.5,a+(b-a)*progress))
    w,h=image.size;cw,ch=w/scale,h/scale
    # Zoom toward the speaker's face when a focus is given; the centre otherwise.
    left=min(max(0,w*float(item.parameters.get('focus_x',.5))-cw/2),w-cw)
    top=min(max(0,h*float(item.parameters.get('focus_y',.5))-ch/2),h-ch)
    return image.crop((left,top,left+cw,top+ch)).resize((w,h),Image.Resampling.LANCZOS)


def camera_pose(animation: str, progress: float, seconds: float = 0.0):
    """(scale, shift_x, shift_y, rotate_degrees) of the virtual camera on a cutaway. Shifts are fractions of
    the frame; a positive shift moves the view right or down. Shared by export and preview so they match."""
    eased = progress * progress * (3 - 2 * progress)
    if animation == "slow_zoom_in": return 1.0 + progress * 0.15, 0.0, 0.0, 0.0
    if animation == "slow_zoom_out": return 1.15 - progress * 0.15, 0.0, 0.0, 0.0
    if animation == "push_in": return 1.0 + 0.22 * (1 - (1 - progress) ** 3), 0.0, 0.0, 0.0  # Dolly in, decelerating.
    if animation == "pan_left": return 1.10, (0.5 - progress) * 0.08, 0.0, 0.0  # Camera turns left: the view travels left.
    if animation == "pan_right": return 1.10, (progress - 0.5) * 0.08, 0.0, 0.0
    if animation == "tilt_up": return 1.10, 0.0, (0.5 - progress) * 0.08, 0.0
    if animation == "tilt_down": return 1.10, 0.0, (progress - 0.5) * 0.08, 0.0
    if animation == "crane_up": return 1.08 + 0.06 * eased, 0.0, (0.5 - eased) * 0.07, 0.0  # Rises while easing in.
    if animation == "dutch": return 1.16, 0.0, 0.0, 2.5 + 2.0 * eased  # Tilted frame, slowly leaning further.
    if animation == "handheld":
        # A slight, deliberate shake: layered slow sines, not random jitter, so frames are reproducible.
        dx = (math.sin(seconds * 2.1) + 0.6 * math.sin(seconds * 5.3 + 1.3)) * 0.004
        dy = (math.sin(seconds * 1.7 + .4) + 0.5 * math.sin(seconds * 4.7)) * 0.004
        return 1.06, dx, dy, 0.25 * math.sin(seconds * 1.3)
    return 1.0, 0.0, 0.0, 0.0


def apply_ken_burns(img: Image.Image, animation: str, progress: float, target_w: int, target_h: int, focus_x: float = 0.5, focus_y: float = 0.5, seconds: float = 0.0) -> Image.Image:
    base = crop_to_aspect(img, target_w, target_h, focus_x=focus_x, focus_y=focus_y)
    if not animation or animation == "none":
        return base
    scale, shift_x, shift_y, rotate = camera_pose(animation, max(0.0, min(1.0, progress)), seconds)
    if rotate:
        base = base.rotate(rotate, resample=Image.Resampling.BICUBIC, expand=False)

    new_w = max(target_w, int(target_w * scale))
    new_h = max(target_h, int(target_h * scale))
    scaled = base.resize((new_w, new_h), Image.Resampling.BILINEAR)
    cx = new_w // 2 + int(shift_x * target_w)
    cy = new_h // 2 + int(shift_y * target_h)
    x0 = max(0, min(new_w - target_w, cx - target_w // 2))
    y0 = max(0, min(new_h - target_h, cy - target_h // 2))
    return scaled.crop((x0, y0, x0 + target_w, y0 + target_h))

TRANSITION_SECONDS = {'dissolve': .3, 'whip': .22, 'wipe': .3, 'flash': .25}


def cutaway_time(speed: str, local: float, duration: float) -> float:
    """Source time inside a video cutaway for its speed treatment. Shared with the preview."""
    if speed == 'slow_motion': return local * 0.5
    if speed == 'speed_ramp':  # Fast, then suddenly slow.
        knee = duration * 0.4
        return local * 2.0 if local < knee else knee * 2.0 + (local - knee) * 0.5
    if speed == 'freeze_end':  # Motion stops for the last third.
        return min(local, duration * 0.66)
    return local


def transition_mix(speaker: Image.Image, cutaway: Image.Image, kind: str, p: float, entering: bool) -> Image.Image:
    """Blend speaker and cutaway during a hand-over. p runs 0..1 from speaker to cutaway when entering,
    and from cutaway to speaker when leaving."""
    p = max(0.0, min(1.0, p)); eased = p * p * (3 - 2 * p)
    a, b = (speaker, cutaway) if entering else (cutaway, speaker)
    w, h = a.size
    if kind == 'dissolve':
        return Image.blend(a.convert('RGB'), b.convert('RGB'), eased)
    if kind == 'wipe':
        out = a.convert('RGB').copy(); edge = int(w * eased)
        if edge > 0: out.paste(b.convert('RGB').crop((0, 0, edge, h)), (0, 0))
        return out
    if kind == 'whip':
        # Fast swing: both shots travel sideways with motion blur, the new one arriving from the right.
        shift = int(w * eased)
        out = Image.new('RGB', (w, h))
        out.paste(a.convert('RGB'), (-shift, 0)); out.paste(b.convert('RGB'), (w - shift, 0))
        blur = max(0.0, 1 - abs(eased - .5) * 2) * w * .012
        return out.filter(ImageFilter.BoxBlur(blur)) if blur > .5 else out
    if kind == 'flash':
        # Smash cut with a white flash that decays on the new shot.
        flash = Image.new('RGB', (w, h), 'white')
        return Image.blend(b.convert('RGB'), flash, max(0.0, .85 * (1 - eased)))
    return b if p >= .5 else a


def compose_cutaway(insert, speaker: Image.Image, t: float, canvas_w: int, canvas_h: int, fonts, cached_images, video_players) -> Image.Image:
    """A full-screen cutaway at time t: its camera move, its speed treatment, and its hand-over in and out."""
    params = insert.parameters
    raw_url = params.get('media_url') or insert.media_url
    duration = max(0.1, insert.end - insert.start); local = t - insert.start
    progress = max(0.0, min(1.0, local / duration))
    anim = params.get('animation') or insert.animation or "none"
    focal_x = float(params.get('media_pos_x', insert.pos_x if insert.pos_x is not None else 0.5))
    focal_y = float(params.get('media_pos_y', insert.pos_y if insert.pos_y is not None else 0.5))
    frame = None
    if raw_url and raw_url in video_players:
        frame = video_players[raw_url].get_frame(cutaway_time(params.get('speed', 'normal'), local, duration))
    elif raw_url and raw_url in cached_images:
        frame = cached_images[raw_url]
    if not frame:
        return speaker
    cut = apply_ken_burns(frame, anim, progress, canvas_w, canvas_h, focus_x=focal_x, focus_y=focal_y, seconds=local)
    if params.get('scanlines') is not False:
        cut = apply_scanlines(cut, opacity=0.35)
    render_cutaway_badges(cut, insert, canvas_w, canvas_h, fonts)
    speaker_frame = crop_to_aspect(speaker, canvas_w, canvas_h) if speaker.size != (canvas_w, canvas_h) else speaker
    into, out_of = params.get('transition_in', 'cut'), params.get('transition_out', 'cut')
    if into in TRANSITION_SECONDS and local < TRANSITION_SECONDS[into]:
        return transition_mix(speaker_frame, cut, into, local / TRANSITION_SECONDS[into], True)
    left = insert.end - t
    if out_of in TRANSITION_SECONDS and left < TRANSITION_SECONDS[out_of]:
        return transition_mix(speaker_frame, cut, out_of, 1 - left / TRANSITION_SECONDS[out_of], False)
    return cut


def apply_scanlines(img: Image.Image, opacity: float = 0.35) -> Image.Image:
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    alpha = int(opacity * 255)
    for y in range(0, img.height, 4):
        d.line([(0, y), (img.width, y)], fill=(0, 0, 0, alpha), width=2)
    base = img.convert('RGBA')
    base.alpha_composite(overlay)
    return base.convert('RGB')

def render_split_50_50(
    speaker_frame: Image.Image,
    graphic: MotionGraphicItem,
    canvas_w: int,
    canvas_h: int,
    fonts: FontManager,
    cached_images: Dict[str, Optional[Image.Image]],
    video_players: Dict[str, VideoClipPlayer],
    current_time: float
) -> Image.Image:
    split_ratio = float(graphic.parameters.get('split_ratio', 0.50))
    top_h = int(canvas_h * split_ratio)
    bot_h = canvas_h - top_h
    canvas = Image.new('RGB', (canvas_w, canvas_h), (15, 15, 15))

    # 1. Bottom Half: Speaker Video framed on upper third (focus_y=0.28) matching CSS object-position exactly!
    speaker_focus = float(graphic.parameters.get('speaker_focus_y', 0.28))
    speaker_crop = crop_to_aspect(speaker_frame, canvas_w, bot_h, focus_y=speaker_focus, focus_x=0.5)
    canvas.paste(speaker_crop, (0, top_h))

    # 2. Top Half: B-Roll Video or Image with Ken Burns animation
    raw_url = graphic.parameters.get('media_url') or graphic.media_url
    top_crop = None
    dur = max(0.1, graphic.end - graphic.start)
    prog = max(0.0, min(1.0, (current_time - graphic.start) / dur))
    anim = "none" # Half-screen media appears without added transforms.

    media_focal_x = float(graphic.parameters.get('media_pos_x', graphic.pos_x if graphic.pos_x is not None else 0.5))
    media_focal_y = float(graphic.parameters.get('media_pos_y', graphic.pos_y if graphic.pos_y is not None else 0.5))

    if raw_url and raw_url in video_players:
        vf = video_players[raw_url].get_frame(current_time - graphic.start)
        if vf:
            top_crop = apply_ken_burns(vf, anim, prog, canvas_w, top_h, focus_x=media_focal_x, focus_y=media_focal_y)
    elif raw_url and raw_url in cached_images and cached_images[raw_url]:
        # Force slow_zoom_in for images in 50-50 if no animation specified
        img_anim = "none"
        top_crop = apply_ken_burns(cached_images[raw_url], img_anim, prog, canvas_w, top_h, focus_x=media_focal_x, focus_y=media_focal_y)

    if top_crop:
        canvas.paste(top_crop, (0, 0))
        # Smooth filmic alpha gradient (NO HARD BLACK BARS!)
        shade = Image.new('RGBA', (canvas_w, top_h), (0, 0, 0, 0))
        d_shade = ImageDraw.Draw(shade)
        for gy in range(45):
            a = int(90 * (1.0 - gy / 45.0))
            d_shade.line([(0, gy), (canvas_w, gy)], fill=(0, 0, 0, a))
        for gy in range(55):
            a = int(120 * (gy / 55.0))
            d_shade.line([(0, top_h - 55 + gy), (canvas_w, top_h - 55 + gy)], fill=(0, 0, 0, a))
        canvas.paste(shade, (0, 0), shade)
    else:
        # High-fidelity documentary motion grid fallback
        top_fallback = Image.new('RGB', (canvas_w, top_h), (25, 28, 35))
        d_fall = ImageDraw.Draw(top_fallback)
        for gx in range(0, canvas_w, 30):
            d_fall.line([(gx, 0), (gx, top_h)], fill=(38, 43, 52))
        for gy in range(0, top_h, 30):
            d_fall.line([(0, gy), (canvas_w, gy)], fill=(38, 43, 52))
        broll_t = graphic.parameters.get('broll_topic') or graphic.parameters.get('broll_title') or graphic.title
        d_fall.text((canvas_w // 2, top_h // 2), broll_t.upper(), font=fonts.get_font('bold', 20), fill=(204, 255, 0), anchor='mm')
        canvas.paste(top_fallback, (0, 0))

    # 3. Horizontal Divider Line (2px)
    d = ImageDraw.Draw(canvas)
    div_color = hex_to_rgb(graphic.parameters.get('divider_color', '#FFFFFF'))
    d.line([(0, top_h), (canvas_w, top_h)], fill=div_color, width=2)

    # Clean split screen without badges or topic pills

    return canvas

def render_article_reconstruction(
    base_frame: Image.Image,
    graphic: MotionGraphicItem,
    canvas_w: int,
    canvas_h: int,
    fonts: FontManager,
    t: float
) -> Image.Image:
    canvas = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))
    d = ImageDraw.Draw(canvas)

    pos_x = graphic.pos_x if graphic.pos_x is not None else 0.5
    pos_y = graphic.pos_y if graphic.pos_y is not None else 0.5
    scale = graphic.scale if graphic.scale is not None else 1.0

    duration = max(0.6, graphic.end - graphic.start)
    elapsed = t - graphic.start

    pad_x = int(canvas_w * 0.08)
    cur_y = int(canvas_h * 0.14)
    content_w = canvas_w - pad_x * 2

    # Publisher Masthead (Logo or Text)
    pub_logo_url = graphic.parameters.get('publisher_logo')
    pub_text = graphic.parameters.get('publisher', '').strip()

    georgia_bold = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
    georgia = "/System/Library/Fonts/Supplemental/Georgia.ttf"

    logo_drawn = False
    if pub_logo_url:
        logo_path = pub_logo_url
        if logo_path.startswith('/api/media/') or '8002/api/media/' in logo_path:
            clean_part = logo_path.split('/api/media/')[-1]
            parts = clean_part.split('/')
            if len(parts) >= 3 and parts[1] == 'asset':
                logo_path = os.path.join('backend', 'projects', parts[0], 'assets', parts[2])
                if not os.path.exists(logo_path):
                    logo_path = str(settings.projects_dir / parts[0] / 'assets' / parts[2])
        if not os.path.exists(logo_path) and os.path.isabs(pub_logo_url):
            logo_path = pub_logo_url

        if os.path.exists(logo_path):
            try:
                max_lw = int(content_w * 0.55)
                max_lh = 85
                if logo_path.lower().endswith('.svg'):
                    with open(logo_path, 'r', encoding='utf-8') as f:
                        s_svg = f.read()
                    s_svg = s_svg.replace('fill:#fff', 'fill:#0f172a').replace('fill:#ffffff', 'fill:#0f172a').replace('fill:white', 'fill:#0f172a')
                    png_bytes = resvg_py.svg_to_bytes(svg_string=s_svg, width=max_lw)
                    logo_img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
                else:
                    logo_img = Image.open(logo_path).convert('RGBA')
                    logo_img.thumbnail((max_lw, max_lh))

                canvas.paste(logo_img, (pad_x, cur_y), logo_img)
                cur_y += logo_img.height + 25
                d.line([(pad_x, cur_y), (canvas_w - pad_x, cur_y)], fill=(225, 225, 225), width=2)
                cur_y += 45
                logo_drawn = True
            except Exception as e:
                print(f"[render_article_reconstruction] Error loading logo: {e}")

    if not logo_drawn and pub_text:
        try:
            fnt_mast = ImageFont.truetype(georgia_bold, 36) if os.path.exists(georgia_bold) else fonts.get_font('bold', 36)
        except Exception:
            fnt_mast = fonts.get_font('bold', 36)
        d.text((pad_x, cur_y), pub_text.upper(), font=fnt_mast, fill=(20, 20, 20))
        cur_y += 55
        d.line([(pad_x, cur_y), (canvas_w - pad_x, cur_y)], fill=(225, 225, 225), width=2)
        cur_y += 45

    # Headline (word-wrapped)
    headline = (graphic.parameters.get('headline') or graphic.title or '').strip()
    if headline:
        s = canvas_w / 380.0
        head_size = int(graphic.parameters.get('headline_size', 22) * s)
        try:
            fnt_head = ImageFont.truetype(georgia_bold, head_size) if os.path.exists(georgia_bold) else fonts.get_font('bold', head_size)
        except Exception:
            fnt_head = fonts.get_font('bold', head_size)

        head_words = headline.split()
        head_lines = []
        curr_hl = []
        curr_hl_w = 0
        h_space_w = fnt_head.getbbox(' ')[2] - fnt_head.getbbox(' ')[0]
        for hw in head_words:
            hbbox = fnt_head.getbbox(hw)
            hw_w = hbbox[2] - hbbox[0]
            if curr_hl_w + hw_w > content_w and curr_hl:
                head_lines.append(" ".join(curr_hl))
                curr_hl = []
                curr_hl_w = 0
            curr_hl.append(hw)
            curr_hl_w += hw_w + h_space_w
        if curr_hl:
            head_lines.append(" ".join(curr_hl))

        head_line_h = int(head_size * 1.35)
        for hline in head_lines:
            d.text((pad_x, cur_y), hline, font=fnt_head, fill=(15, 23, 42))
            cur_y += head_line_h
        cur_y += 25

    # Body Paragraph with inline kinetic highlighter sweep
    para = (graphic.parameters.get('paragraph') or '').strip()
    if para:
        s = canvas_w / 380.0
        para_size = int(graphic.parameters.get('paragraph_size', 16) * s)
        try:
            fnt_para = ImageFont.truetype(georgia, para_size) if os.path.exists(georgia) else fonts.get_font('regular', para_size)
        except Exception:
            fnt_para = fonts.get_font('regular', para_size)

        show_highlight = graphic.parameters.get('show_highlight') is not False
        quote = (graphic.parameters.get('highlight_quote') or '').strip()
        if show_highlight and not quote:
            m = re.match(r'^([^.!?]+[.!?]?)', para)
            quote = m.group(1) if m else para[:80]

        hl_start = para.lower().find(quote.lower()) if (show_highlight and quote) else -1
        hl_end = hl_start + len(quote) if hl_start != -1 else -1

        words = para.split()
        space_w = fnt_para.getbbox(' ')[2] - fnt_para.getbbox(' ')[0]
        char_pos = 0

        p_lines = []
        curr_pl = []
        curr_pl_w = 0
        for w in words:
            w_len = len(w)
            w_start = char_pos
            w_end = char_pos + w_len
            is_hl = (hl_start != -1 and w_start < hl_end and w_end > hl_start)
            bbox = fnt_para.getbbox(w)
            w_w = bbox[2] - bbox[0]
            if curr_pl_w + w_w > content_w and curr_pl:
                p_lines.append(curr_pl)
                curr_pl = []
                curr_pl_w = 0
            curr_pl.append((w, is_hl, w_w))
            curr_pl_w += w_w + space_w
            char_pos += w_len + 1
        if curr_pl:
            p_lines.append(curr_pl)

        line_h = int(para_size * 1.5)
        marker_hex = graphic.parameters.get('marker_color', '#FB923C')
        marker_rgb = hex_to_rgb(marker_hex, (251, 146, 60))
        sweep_progress = min(1.0, max(0.0, (elapsed - 0.2) / max(0.6, duration * 0.6)))

        for line in p_lines:
            x = pad_x
            hl_segments = []
            seg_start = None
            for w, is_hl, w_w in line:
                if is_hl:
                    if seg_start is None:
                        seg_start = x
                else:
                    if seg_start is not None:
                        hl_segments.append((seg_start, x - space_w + 6))
                        seg_start = None
                x += w_w + space_w
            if seg_start is not None:
                hl_segments.append((seg_start, x - space_w + 6))

            for sx, ex in hl_segments:
                seg_w = ex - sx
                cur_sweep_w = int(seg_w * sweep_progress)
                if cur_sweep_w > 0:
                    d.rounded_rectangle([sx - 6, cur_y - 4, sx + cur_sweep_w, cur_y + line_h - 10], radius=6, fill=marker_rgb)

            x = pad_x
            for w, is_hl, w_w in line:
                d.text((x, cur_y), w, font=fnt_para, fill=(15, 23, 42))
                x += w_w + space_w
            cur_y += line_h

    # Attached Figure Image UNDER THE TEXT
    raw_media_url = graphic.parameters.get('media_url') or graphic.media_url
    show_image = graphic.parameters.get('show_image') is not False and bool(raw_media_url)
    if show_image and raw_media_url:
        img_path = raw_media_url
        if img_path.startswith('/api/media/') or '8002/api/media/' in img_path:
            clean_part = img_path.split('/api/media/')[-1]
            parts = clean_part.split('/')
            if len(parts) >= 3 and parts[1] == 'asset':
                if parts[2] == 'downloaded' and len(parts) >= 4:
                    img_path = os.path.join('backend', 'projects', parts[0], 'media', 'downloaded', parts[3])
                    if not os.path.exists(img_path):
                        img_path = str(settings.projects_dir / parts[0] / 'media' / 'downloaded' / parts[3])
                else:
                    img_path = os.path.join('backend', 'projects', parts[0], 'assets', parts[2])
                    if not os.path.exists(img_path):
                        img_path = str(settings.projects_dir / parts[0] / 'assets' / parts[2])
        if not os.path.exists(img_path) and os.path.isabs(raw_media_url):
            img_path = raw_media_url

        if os.path.exists(img_path):
            try:
                cur_y += 45
                if img_path.lower().endswith('.svg'):
                    with open(img_path, 'r', encoding='utf-8') as f:
                        s_svg = f.read()
                    png_bytes = resvg_py.svg_to_bytes(svg_string=s_svg, width=content_w)
                    fig_img = Image.open(io.BytesIO(png_bytes)).convert('RGB')
                else:
                    fig_img = Image.open(img_path).convert('RGB')

                max_fig_w = content_w
                max_fig_h = max(250, min(580, canvas_h - cur_y - 200))
                contained_fig = ImageOps.contain(fig_img, (max_fig_w, max_fig_h))
                fig_x = pad_x + (content_w - contained_fig.width) // 2
                canvas.paste(contained_fig, (fig_x, cur_y))
                d.rectangle([fig_x, cur_y, fig_x + contained_fig.width, cur_y + contained_fig.height], outline=(220, 220, 220), width=2)
                cur_y += contained_fig.height + 30
            except Exception as e:
                print(f"[render_article_reconstruction] Error rendering attached image: {e}")

    return canvas

def render_cutaway_badges(canvas: Image.Image, graphic: MotionGraphicItem, canvas_w: int, canvas_h: int, fonts: FontManager):
    return

def render_medical_endcard(canvas: Image.Image, graphic: MotionGraphicItem, canvas_w: int, canvas_h: int, fonts: FontManager) -> Image.Image:
    """Renders clean clinical 3-second end screen matching CanvasOverlay.tsx."""
    params = graphic.parameters or {}
    s = canvas_w / 380.0

    # Base dark clinical canvas
    card_w = int(320 * s)
    card_h = int(280 * s)
    card_x = (canvas_w - card_w) // 2
    card_y = (canvas_h - card_h) // 2

    # Draw dark backing card
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle(
        [card_x, card_y, card_x + card_w, card_y + card_h],
        radius=int(18 * s),
        fill=(10, 10, 12),
        outline=(204, 255, 0),
        width=int(2.5 * s)
    )

    # Avatar circle
    avatar_r = int(28 * s)
    avatar_cx = canvas_w // 2
    avatar_cy = card_y + int(45 * s)
    d.ellipse(
        [avatar_cx - avatar_r, avatar_cy - avatar_r, avatar_cx + avatar_r, avatar_cy + avatar_r],
        fill=(25, 25, 30),
        outline=(204, 255, 0),
        width=int(2 * s)
    )

    # Doctor title
    doc_name = params.get("doctor_name", "The Cancer Doctor")
    fnt_title = fonts.get_font('bold', max(16, int(18 * s)))
    d.text((avatar_cx, avatar_cy + avatar_r + int(18 * s)), doc_name, font=fnt_title, fill=(255, 255, 255), anchor='mm')

    # Tagline
    tagline = params.get("tagline", "Evidence-Based Oncology Updates")
    fnt_sub = fonts.get_font('regular', max(10, int(11 * s)))
    d.text((avatar_cx, avatar_cy + avatar_r + int(38 * s)), tagline, font=fnt_sub, fill=(160, 160, 160), anchor='mm')

    # Social handle
    handle = params.get("handle") or params.get("social_yt") or "@the_cancer_doctor"
    fnt_mono = fonts.get_font('mono', max(11, int(12 * s)))
    d.text((avatar_cx, avatar_cy + avatar_r + int(58 * s)), handle, font=fnt_mono, fill=(204, 255, 0), anchor='mm')

    # CTA Button
    btn_w = int(card_w * 0.82)
    btn_h = int(36 * s)
    btn_x = (canvas_w - btn_w) // 2
    btn_y = card_y + card_h - btn_h - int(18 * s)
    d.rounded_rectangle(
        [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
        radius=int(10 * s),
        fill=(204, 255, 0)
    )
    cta_text = params.get("cta_text", "Follow @the_cancer_doctor")
    fnt_btn = fonts.get_font('bold', max(11, int(12 * s)))
    d.text((canvas_w // 2, btn_y + btn_h // 2), cta_text, font=fnt_btn, fill=(0, 0, 0), anchor='mm')

    return canvas

from functools import lru_cache

@lru_cache(maxsize=3)
def title_card_video(path):
    with av.open(path) as container:
        fps = float(container.streams.video[0].average_rate or 30)
        frames = []
        for frame in container.decode(video=0):
            frames.append(ImageOps.fit(frame.to_image(), (320,260)))
            if len(frames) >= min(300, int(fps*8)): break
    return frames, fps

@lru_cache(maxsize=32)
def title_card_still(path):
    return Image.open(path).convert('RGB')

def title_card_image(url, relative_time=0):
    """Only project-local assets; never fetch external content during export."""
    from urllib.parse import urlparse, unquote
    parts = unquote(urlparse(url).path).split('/')
    if len(parts) < 6 or parts[1:3] != ['api','media'] or parts[4] != 'asset': return None
    root = settings.projects_dir / parts[3]
    path = root / ('media/downloaded' if parts[5] == 'downloaded' else 'assets') / parts[-1]
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file(): return None
    try:
        if path.suffix.lower() in ('.mp4','.mov','.webm'):
            frames, fps = title_card_video(str(path))
            return frames[int(max(0,relative_time)*fps)%len(frames)] if frames else None
        return title_card_still(str(path))
    except (OSError, ValueError, StopIteration): return None

def counting_number(word, elapsed):
    """A spoken figure counts up to its value as it lands ("100,000" runs from 0); years and plain words are unchanged."""
    match = re.fullmatch(r'(\D*?)(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(\D*)', word)
    if not match: return word
    prefix, number, suffix = match.groups()
    digits = number.replace(',', '')
    if re.fullmatch(r'(19|20)\d\d', digits) or float(digits) < 2: return word
    progress = max(0.0, min(1.0, elapsed / COUNT_UP_SECONDS))
    value = float(digits) * (1 - (1 - progress) ** 3)
    decimals = len(digits.split('.')[1]) if '.' in digits else 0
    shown = f'{value:,.{decimals}f}' if ',' in number else f'{value:.{decimals}f}'
    return prefix + shown + suffix


COUNT_UP_SECONDS = .55


def render_editorial_text(canvas, graphic, width, height, fonts, t=None):
    params = graphic.parameters
    lines = params.get('title_lines') or [{'text': params.get('headline', ''), 'offset': 0}]
    timed_words = params.get('timed_words') or []
    duration = float(params.get('title_reveal_seconds') or 0.45)
    if t is None: t = graphic.start + duration
    exit = max(0.0, min(1.0, (graphic.end - t) / 0.2))
    style = params.get('title_style', 'rise')
    longest = max((len(str(line.get('text', ''))) for line in lines), default=1)
    base_size = max(12, min(int(width * .065), int(width * .82 / max(1, longest * .57))))
    elapsed_total = max(0.0, t - graphic.start)

    # Word-by-word pacing helper for backend burnin renderer
    def filter_visible_words(full_text: str):
        full_tokens = str(full_text).split()
        if not timed_words:
            return full_tokens
        visible = []
        for w_idx, tok in enumerate(full_tokens):
            clean_tok = re.sub(r'[^a-zA-Z0-9]', '', tok).lower()
            match = next((tw for tw in timed_words if re.sub(r'[^a-zA-Z0-9]', '', str(tw.get('text', ''))).lower() == clean_tok), None)
            offset = float(match.get('offset', 0)) if match else (w_idx * 0.18)
            if elapsed_total >= offset:
                visible.append(tok)
        return visible if visible else full_tokens[:1] if elapsed_total > 0 else []

    if style == 'stat_pair' and params.get('stat_cards'):
        cx,cy=int(width*graphic.pos_x),int(height*graphic.pos_y)
        box_w,box_h=int(width*.86),int(width*.34)
        layer=Image.new('RGBA',canvas.size,(0,0,0,0));draw=ImageDraw.Draw(layer)
        left,top=cx-box_w//2,cy-box_h//2
        draw.rounded_rectangle((left,top,left+box_w,top+box_h),radius=max(2,int(width*.016)),fill=(17,25,28,225))
        draw.text((left+width*.045,top+width*.04),'INDIA · EACH YEAR',font=fonts.get_font('regular',int(width*.026)),fill='#faf7ee')
        for index,stat in enumerate(params['stat_cards'][:2]):
            progress=max(0.,min(1.,(elapsed_total-float(stat.get('offset',0)))/.3))
            x=left+width*.045+index*box_w*.5;y=top+width*.13+(1-progress)*width*.02
            draw.text((x,y),str(stat['value']),font=fonts.get_font('bold',int(width*.075)),fill=(238,210,155,int(255*progress)) if index else (255,255,255,int(255*progress)))
            draw.text((x,y+width*.105),str(stat['label']).upper(),font=fonts.get_font('regular',int(width*.026)),fill=(250,247,238,int(255*progress)))
        canvas.paste(layer,(0,0),layer.getchannel('A').point(lambda v:int(v*exit)))
        return

    # 0. EDITORIAL (lowercase grotesque, one key word in gold italic serif, soft shadow, no box)
    if style == 'editorial':
        accents = {re.sub(r'[^\w]', '', str(w)).casefold() for w in (params.get('accent_words') or [])}
        size = max(14, min(int(width * .092), int(width * .88 / max(1, longest * .5))))
        sans = fonts.get_font('editorial_sans', size)
        serif = fonts.get_font('editorial_serif', int(size * 1.2))
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0)); shade = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer); shade_draw = ImageDraw.Draw(shade)
        line_h = int(size * 1.1); space = size * .24
        top = height * graphic.pos_y - (len(lines) - 1) * line_h / 2
        reveal = iter(timed_words) if sum(len(str(l.get('text', '')).split()) for l in lines) == len(timed_words) else None
        for row, line in enumerate(lines):
            words = str(line.get('text', '')).lower().split()
            faces = [serif if re.sub(r'[^\w]', '', w).casefold() in accents else sans for w in words]
            widths = [draw.textlength(w, font=f) for w, f in zip(words, faces)]
            x = width * graphic.pos_x - (sum(widths) + space * max(0, len(words) - 1)) / 2
            for word, face, word_w in zip(words, faces, widths):
                offset = float(next(reveal).get('offset', 0)) if reveal else float(line.get('offset', 0))
                progress = max(0.0, min(1.0, (elapsed_total - offset) / .14))
                if progress > 0:
                    eased = 1 - (1 - progress) ** 3
                    y = top + row * line_h + (1 - eased) * size * .18
                    alpha = int(255 * min(progress, exit))
                    edge = max(2, int(size * .07))
                    word = counting_number(word, elapsed_total - offset)
                    shade_draw.text((x, y + size * .04), word, font=face, fill=(0, 0, 0, int(alpha * .9)), anchor='lm', stroke_width=edge, stroke_fill=(0, 0, 0, int(alpha * .9)))
                    draw.text((x, y), word, font=face, fill=(255, 214, 92, alpha) if face is serif else (255, 255, 255, alpha), anchor='lm')
                x += word_w + space
        shade = shade.filter(ImageFilter.GaussianBlur(max(2, size * .12)))
        canvas.paste(shade, (0, 0), shade); canvas.paste(layer, (0, 0), layer)
        return

    # 0B. MIXED_TYPOGRAPHY (Geometric Sans-Serif Bold setup + 1.25x Italic Serif/Script punchword in transform wireframe box)
    if style == 'mixed_typography':
        from app.services.subject_layers import mask_frame_path
        from PIL import ImageChops

        setup_t = str(params.get('setup_text') or (lines[0].get('text', '') if lines else '')).strip().upper()
        accent_t = str(params.get('accent_text') or (lines[1].get('text', '') if len(lines) > 1 else (lines[0].get('text', '') if not setup_t else ''))).strip()

        setup_color_hex = params.get('setup_color', '#FFFFFF')
        accent_color_hex = params.get('accent_color', '#E04F26')
        setup_rgb = hex_to_rgb(setup_color_hex, (255, 255, 255))
        accent_rgb = hex_to_rgb(accent_color_hex, (224, 79, 38))

        box_rotation = float(params.get('box_rotation', -3.0))
        show_box = bool(params.get('bounding_box_highlight', True))

        cx, cy = int(width * graphic.pos_x), int(height * graphic.pos_y)
        prog = max(0.0, min(1.0, elapsed_total / duration))
        alpha_factor = min(prog, exit)

        setup_size = max(16, int(base_size * 0.95))
        f_setup = fonts.get_font('display_bold', setup_size)
        accent_size = int(setup_size * 1.25)
        f_accent = fonts.get_font('italic_serif', accent_size)

        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        bbox_setup = draw.textbbox((0, 0), setup_t, font=f_setup) if setup_t else (0, 0, 0, 0)
        setup_w = bbox_setup[2] - bbox_setup[0]
        setup_h = bbox_setup[3] - bbox_setup[1]

        bbox_accent = draw.textbbox((0, 0), accent_t, font=f_accent) if accent_t else (0, 0, 0, 0)
        accent_w = bbox_accent[2] - bbox_accent[0]
        accent_h = bbox_accent[3] - bbox_accent[1]

        vertical_overlap = int(accent_size * 0.18) if (setup_t and accent_t) else 0
        total_h = setup_h + accent_h - vertical_overlap

        setup_y = cy - total_h // 2 + setup_h // 2 if setup_t else cy
        accent_y = (setup_y + setup_h // 2 + accent_h // 2 - vertical_overlap) if setup_t else cy

        if setup_t:
            shadow_alpha = int(180 * alpha_factor)
            text_alpha = int(255 * alpha_factor)
            draw.text((cx, setup_y + max(2, int(setup_size * 0.05))), setup_t, font=f_setup, fill=(0, 0, 0, shadow_alpha), anchor='mm')
            draw.text((cx, setup_y), setup_t, font=f_setup, fill=(setup_rgb[0], setup_rgb[1], setup_rgb[2], text_alpha), anchor='mm')

        if accent_t:
            pad_x = int(accent_size * 0.32)
            pad_y = int(accent_size * 0.18)
            bw = accent_w + pad_x * 2
            bh = accent_h + pad_y * 2

            sub_w = bw + 32
            sub_h = bh + 32
            sub_img = Image.new('RGBA', (sub_w, sub_h), (0, 0, 0, 0))
            sub_draw = ImageDraw.Draw(sub_img)
            sub_cx = sub_w // 2
            sub_cy = sub_h // 2

            if show_box:
                box_img = render_bounding_box_svg(bw, bh, stroke_color=accent_color_hex, stroke_width=2, handle_size=8, padding=4)
                bx = sub_cx - box_img.width // 2
                by = sub_cy - box_img.height // 2
                sub_img.paste(box_img, (bx, by), box_img)

            sub_draw.text((sub_cx, sub_cy + max(1, int(accent_size * 0.04))), accent_t, font=f_accent, fill=(0, 0, 0, int(150 * alpha_factor)), anchor='mm')
            sub_draw.text((sub_cx, sub_cy), accent_t, font=f_accent, fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha_factor)), anchor='mm')

            rotated_sub = sub_img.rotate(box_rotation, resample=Image.Resampling.BICUBIC, expand=True)
            r_alpha = rotated_sub.getchannel('A').point(lambda v: int(v * alpha_factor))

            px = cx - rotated_sub.width // 2
            py = accent_y - rotated_sub.height // 2
            layer.paste(rotated_sub, (px, py), r_alpha)

        mask_path = mask_frame_path(graphic, t)
        alpha = layer.getchannel('A')
        if mask_path and (params.get('behind_subject') or style == 'behind_subject'):
            with Image.open(mask_path) as matte:
                inverse = matte.getchannel('A').resize(canvas.size, Image.Resampling.BILINEAR)
            alpha = ImageChops.multiply(alpha, inverse)

        canvas.paste(layer, (0, 0), alpha)
        return

    # 1. DUAL (Bold sans-serif + flowing red cursive script)
    if style == 'dual':
        top_text = lines[0].get('text', '') if len(lines) > 0 else params.get('headline', 'YOU CARRY ON')
        bot_text = lines[1].get('text', '') if len(lines) > 1 else ''
        
        vis_top = ' '.join(filter_visible_words(top_text))
        vis_bot = ' '.join(filter_visible_words(bot_text))
        
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        cx = int(width * graphic.pos_x)
        cy = int(height * graphic.pos_y)

        f_top = fonts.get_font('bold', int(base_size * 0.95))
        f_bot = fonts.get_font('script', int(base_size * 1.55))

        y0 = cy - int(base_size * 0.6)
        y1 = cy + int(base_size * 0.5)

        if vis_top:
            draw.text((cx, y0), vis_top.upper(), font=f_top, fill=(255, 255, 255, 255), anchor='mm', stroke_width=max(1, int(width/900)), stroke_fill=(0, 0, 0, 240))
        if vis_bot:
            draw.text((cx, y1), vis_bot, font=f_bot, fill=(239, 68, 68, 255), anchor='mm', stroke_width=max(1, int(width/900)), stroke_fill=(0, 0, 0, 200))
        
        alpha = layer.getchannel('A').point(lambda v: int(v * exit))
        canvas.paste(layer, (0, 0), alpha)
        return

    # 2. FLAME_SUBJECT (Fiery glow aura + burning handwriting script)
    if style == 'flame_subject':
        text = lines[0].get('text', '') if len(lines) > 0 else params.get('headline', 'burnt out.')
        prog = max(0.0, min(1.0, elapsed_total / duration))
        
        # Fire ambient glow
        flame_layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        f_draw = ImageDraw.Draw(flame_layer)
        fx = int(width * graphic.pos_x)
        fy = int(height * graphic.pos_y)
        fa = int(255 * min(prog, exit))
        for rad, col in [
            (int(base_size * 3.5), (255, 60, 0, int(fa * 0.35))),
            (int(base_size * 2.2), (255, 140, 0, int(fa * 0.60))),
            (int(base_size * 1.2), (255, 230, 80, int(fa * 0.85)))
        ]:
            f_draw.ellipse((fx - rad, fy - rad, fx + rad, fy + rad), fill=col)
        flame_layer = flame_layer.filter(ImageFilter.GaussianBlur(max(2, width*.025)))
        canvas.paste(flame_layer, (0, 0), flame_layer)

        # Text layer
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        f_script = fonts.get_font('script', int(base_size * 1.8))
        draw.text((fx, fy), str(text), font=f_script, fill=(255, 255, 255, 255), anchor='mm', stroke_width=0, stroke_fill=(0, 0, 0, 0))
        alpha = layer.getchannel('A').point(lambda v: int(v * min(prog, exit)))
        canvas.paste(layer, (0, 0), alpha)
        return

    # 3. SCRIPT (Pure white elegant cursive script across frame)
    if style == 'script':
        text = lines[0].get('text', '') if len(lines) > 0 else params.get('headline', 'the reason that people can go')
        prog = max(0.0, min(1.0, elapsed_total / duration))
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        cx = int(width * graphic.pos_x)
        cy = int(height * graphic.pos_y) + int((1 - prog) * 15)
        f_script = fonts.get_font('script', int(base_size * 1.45))
        draw.text((cx, cy), str(text), font=f_script, fill=(255, 255, 255, 255), anchor='mm', stroke_width=max(1, int(width/900)), stroke_fill=(0, 0, 0, 220))
        alpha = layer.getchannel('A').point(lambda v: int(v * min(prog, exit)))
        canvas.paste(layer, (0, 0), alpha)
        return

    # 4. CARDS_BROLL (Title with floating B-roll mini-cards in background)
    if style == 'cards_broll':
        from app.services.subject_layers import mask_frame_path
        from PIL import ImageChops
        prog = max(0.0, min(1.0, elapsed_total / duration))
        cx = int(width * graphic.pos_x)
        cy = int(height * graphic.pos_y)
        card_layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(card_layer)

        # Translucent black backdrop band behind speaker
        band_y1 = cy - int(height * 0.15)
        band_y2 = cy + int(height * 0.15)
        c_draw.rectangle([0, band_y1, width, band_y2], fill=(0, 0, 0, int(135 * prog * exit)))

        for index, card in enumerate(params.get('card_media', [])[:3]):
            image = title_card_image(str(card.get('url', '')), elapsed_total)
            if image is None: continue
            cw, ch = int(width * 0.28), int(width * 0.22)
            thumb = ImageOps.fit(image, (cw, ch)).convert('RGBA')
            thumb = ImageOps.expand(thumb, border=max(2, int(width / 200)), fill='white')
            if params.get('bounding_box_highlight'):
                box_card = render_bounding_box_svg(thumb.width, thumb.height, stroke_color=params.get('accent_color', '#E04F26'), stroke_width=2, handle_size=8, padding=2)
                card_composite = Image.new('RGBA', (box_card.width, box_card.height), (0, 0, 0, 0))
                card_composite.paste(thumb, ((box_card.width - thumb.width) // 2, (box_card.height - thumb.height) // 2))
                card_composite.paste(box_card, (0, 0), box_card)
                thumb = card_composite
            thumb = thumb.rotate([7, -7, 3][index], resample=Image.Resampling.BICUBIC, expand=True)
            x = int(cx + [-0.32, 0.32, 0][index] * width - thumb.width / 2)
            y = int(cy + [-0.22, -0.17, 0.25][index] * width - thumb.height / 2)
            card_layer.paste(thumb, (x, y), thumb)

        # Mask backdrop band and Polaroid cards behind speaker if subject mask available
        mask_path = mask_frame_path(graphic, t)
        if mask_path:
            with Image.open(mask_path) as matte:
                inverse = matte.getchannel('A').resize(canvas.size, Image.Resampling.BILINEAR)
            c_alpha = ImageChops.multiply(card_layer.getchannel('A'), inverse)
            canvas.paste(card_layer, (0, 0), c_alpha)
        else:
            canvas.paste(card_layer, (0, 0), card_layer)

        # Foreground text
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        top_t = lines[0].get('text', '') if len(lines) > 0 else ''
        mid_t = lines[1].get('text', '') if len(lines) > 1 else ''
        bot_t = lines[2].get('text', '') if len(lines) > 2 else ''
        
        f_top = fonts.get_font('regular', int(base_size * 0.75))
        f_mid = fonts.get_font('bold', int(base_size * 1.05))
        f_bot = fonts.get_font('script', int(base_size * 1.5))
        
        draw.text((cx, cy - int(base_size * 1.1)), str(top_t), font=f_top, fill=(240, 240, 240, 255), anchor='mm', stroke_width=2, stroke_fill=(0, 0, 0, 240))
        draw.text((cx, cy - int(base_size * 0.3)), str(mid_t).upper(), font=f_mid, fill=(255, 255, 255, 255), anchor='mm', stroke_width=1, stroke_fill=(0, 0, 0, 100))
        draw.text((cx, cy + int(base_size * 0.8)), str(bot_t), font=f_bot, fill=(251, 191, 36, 255), anchor='mm', stroke_width=0, stroke_fill=(0, 0, 0, 0))
        
        alpha = layer.getchannel('A').point(lambda v: int(v * min(prog, exit)))
        canvas.paste(layer, (0, 0), alpha)
        return

    # 5. BEHIND_SUBJECT (Massive uppercase block typography layered in backdrop)
    if style == 'behind_subject':
        from app.services.subject_layers import mask_frame_path
        from PIL import ImageChops
        cx, cy = int(width*graphic.pos_x), int(height*graphic.pos_y)
        layer = Image.new('RGBA',canvas.size,(0,0,0,0));draw=ImageDraw.Draw(layer)
        for index,line in enumerate(lines[:2]):
            text=str(line.get('text',''))
            progress=max(0.,min(1.,(elapsed_total-float(line.get('offset',0)))/.3))
            size=int(min(width*.16,width*.94/max(1,len(text)*.55))*(graphic.scale or 1))
            font=fonts.get_font('display',max(12,size))
            # Actual glyph width, not character count alone, is the final fit constraint.
            while draw.textlength(text,font=font)>width*.94 and size>12:
                size-=1;font=fonts.get_font('display',size)
            y=cy+int((index-(min(2,len(lines))-1)/2)*size*.96+(1-progress)*width*.026)
            draw.text((cx,y),text,font=font,fill=(255,250,241,int(255*progress*exit)),anchor='mm')
        mask_path=mask_frame_path(graphic,t)
        alpha=layer.getchannel('A')
        if mask_path:
            with Image.open(mask_path) as matte:
                inverse=matte.getchannel('A').resize(canvas.size,Image.Resampling.BILINEAR)
            alpha=ImageChops.multiply(alpha,inverse)
        canvas.paste(layer,(0,0),alpha)
        if len(lines)>2 and lines[2].get('text') and elapsed_total>=float(lines[2].get('offset',0)):
            front=Image.new('RGBA',canvas.size,(0,0,0,0));fd=ImageDraw.Draw(front)
            fd.text((cx,int(height*min(.82,graphic.pos_y+.19))),str(lines[2]['text']),font=fonts.get_font('script',int(width*.1)),fill=(239,219,162,int(255*exit)),anchor='mm')
            canvas.paste(front,(0,0),front.getchannel('A'))
        return

    # 6. RISE (Clean minimalist stacked sans-serif, left-aligned - Image 1 Panel 6)
    if style == 'rise':
        lx = max(int(width * 0.08), int(width * graphic.pos_x - width * 0.35))
        for index, line in enumerate(lines):
            progress = max(0., min(1., (elapsed_total - float(line.get('offset', 0))) / duration))
            if progress <= 0: continue
            eased = 1 - (1 - progress)**3
            layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)
            cy = int(height * graphic.pos_y + (index - (len(lines) - 1) / 2) * base_size * 1.15 + (1 - eased) * width * .025)
            font = fonts.get_font('bold', int(base_size * 1.05))
            draw.text((lx, cy), str(line.get('text', '')).upper(), font=font, fill='white', anchor='lm', stroke_width=1, stroke_fill=(0, 0, 0, 160))
            canvas.paste(layer, (0, 0), layer.getchannel('A').point(lambda v: int(v * min(progress, exit))))
        return

    # 7. PAPER (Torn paper banner background with dark serif font & cyan YES badge - Image 1 Panel 7)
    if style == 'paper':
        prog = max(0.0, min(1.0, elapsed_total / duration))
        cx = int(width * graphic.pos_x)
        cy = int(height * graphic.pos_y)
        
        main_t = lines[0].get('text', '') if len(lines) > 0 else 'YOU CAN MAKE HOOKS'
        badge_t = lines[1].get('text', '') if len(lines) > 1 else 'YES'
        
        f_serif = fonts.get_font('serif', int(base_size * 0.95))
        f_badge = fonts.get_font('bold', int(base_size * 0.8))
        
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        
        # Calculate bounding box
        bbox_main = draw.textbbox((0, 0), str(main_t).upper(), font=f_serif)
        bbox_badge = draw.textbbox((0, 0), str(badge_t).upper(), font=f_badge)
        tw = (bbox_main[2] - bbox_main[0]) + (bbox_badge[2] - bbox_badge[0]) + int(width * 0.10)
        th = max(bbox_main[3] - bbox_main[1], bbox_badge[3] - bbox_badge[1]) + int(width * 0.06)
        
        bx0 = cx - tw // 2
        by0 = cy - th // 2
        bx1 = cx + tw // 2
        by1 = cy + th // 2
        
        # Torn paper banner rectangle with fibrous ragged jagged edges
        edge = max(2, int(width * .009))
        top = [(x, by0 + (edge if i % 2 else 0)) for i, x in enumerate(range(bx0, bx1, max(2, edge * 2)))]
        bottom = [(x, by1 - (edge if i % 2 else 0)) for i, x in enumerate(range(bx1, bx0, -max(2, edge * 2)))]
        draw.polygon(top + [(bx1, by0)] + bottom + [(bx0, by1)], fill=(250, 246, 238, 255))
        
        # Draw dark serif text
        tx = bx0 + int(width * 0.04) + (bbox_main[2] - bbox_main[0]) // 2
        draw.text((tx, cy), str(main_t).upper(), font=f_serif, fill=(24, 24, 27, 255), anchor='mm')
        
        # Draw cyan punch badge
        badgex = bx1 - int(width * 0.035) - (bbox_badge[2] - bbox_badge[0]) // 2
        badgew = (bbox_badge[2] - bbox_badge[0]) + int(width * 0.035)
        badgeh = int(th * 0.65)
        draw.rounded_rectangle((badgex - badgew // 2, cy - badgeh // 2, badgex + badgew // 2, cy + badgeh // 2), radius=3, fill=(2, 132, 199, 255))
        draw.text((badgex, cy), str(badge_t).upper(), font=f_badge, fill=(255, 255, 255, 255), anchor='mm')
        
        alpha = layer.getchannel('A').point(lambda v: int(v * min(prog, exit)))
        canvas.paste(layer, (0, 0), alpha)
        return

    # 8. TYPEWRITER (Retro card substrate with typewriter font & blinking cursor - Image 1 Panel 8)
    if style == 'typewriter':
        import textwrap
        cx,cy=int(width*graphic.pos_x),int(height*graphic.pos_y)
        full=str(params.get('headline') or lines[0].get('text','')).rstrip('|').replace(' | ','\n')
        rows=[line for paragraph in full.split('\n') for line in textwrap.wrap(paragraph,width=23)] or ['']
        wrapped='\n'.join(rows)
        progress=min(1.,elapsed_total/max(.4,(graphic.end-graphic.start)*.65))
        typed=wrapped[:math.ceil(len(wrapped)*progress)]+('|' if int(t*3)%2==0 else ' ')
        font=fonts.get_font('mono',max(12,int(width*.058)))
        layer=Image.new('RGBA',canvas.size,(0,0,0,0));draw=ImageDraw.Draw(layer)
        box_w=int(width*.92);box_h=int(width*(.085+.074*len(rows)))
        draw.rounded_rectangle((cx-box_w//2,cy-box_h//2,cx+box_w//2,cy+box_h//2),radius=3,fill=(250,248,245,255))
        draw.multiline_text((cx-box_w//2+width*.045,cy-box_h//2+width*.032),typed,font=font,spacing=int(width*.008),fill=(20,20,20,255))
        canvas.paste(layer,(0,0),layer.getchannel('A').point(lambda v:int(v*exit)))
        return

    # 9. BOLD_POP (Dark cyber-grid container + massive block typography + circular upward arrow badge - Image 1 Panel 9)
    if style == 'bold_pop':
        prog = max(0.0, min(1.0, elapsed_total / duration))
        eased = 1 - (1 - prog)**3
        cx = int(width * graphic.pos_x)
        cy = int(height * graphic.pos_y)
        
        full_t = lines[0].get('text', '') if len(lines) > 0 else params.get('headline', 'LAUNCH')
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        cw, ch = int(width * .88), int(width * .22)
        draw.rounded_rectangle((cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2), radius=6, fill=(15, 16, 21, 245))
        for xx in range(cx - cw // 2, cx + cw // 2, max(4, int(width * .06))):
            draw.line((xx, cy - ch // 2, xx, cy + ch // 2), fill=(30, 45, 55, 160), width=1)
        # Keep the whole title inside the card, as the preview does: wrap a long
        # title onto two balanced lines, then shrink until the widest line fits.
        label = str(full_t).upper()
        size = int(base_size * 1.25 * (.94 + .06 * eased))
        f_giant = fonts.get_font('bold', size)
        words_in_title = label.split()
        if draw.textlength(label, font=f_giant) > cw * .9 and len(words_in_title) > 1:
            split = min(range(1, len(words_in_title)), key=lambda i: abs(len(' '.join(words_in_title[:i])) - len(' '.join(words_in_title[i:]))))
            label = ' '.join(words_in_title[:split]) + '\n' + ' '.join(words_in_title[split:])
        while size > 8 and (max(draw.textlength(line, font=f_giant) for line in label.split('\n')) > cw * .9
                            or ('\n' in label and size * 2.3 > ch)):
            size -= 1
            f_giant = fonts.get_font('bold', size)
        draw.multiline_text((cx, cy), label, font=f_giant, fill='white', anchor='mm', align='center', spacing=max(2, size // 6))
        
        # Circular Pop-out Upward Arrow Badge in light peach/pink (#FFE4E6)
        brad = max(10, int(width * 0.045))
        bx = cx + cw // 2 - int(width * 0.06)
        by = cy - ch // 2
        draw.ellipse((bx - brad, by - brad, bx + brad, by + brad), fill=(255, 228, 230, 255), outline=(251, 113, 133, 255), width=max(1, int(width / 500)))
        f_arr = fonts.get_font('bold', int(brad * 1.3))
        draw.text((bx, by), '↑', font=f_arr, fill=(15, 16, 21, 255), anchor='mm')
        
        alpha = layer.getchannel('A').point(lambda v: int(v * min(prog, exit)))
        canvas.paste(layer, (0, 0), alpha)
        return

    # 10. STAIRCASE (Words stepping in a halo body arch framing the protagonist - Image 1 Panel 10)
    if style == 'staircase':
        words_list = lines if len(lines) > 1 else [{'text': w} for w in str(lines[0].get('text', '') if lines else '').split() if w]
        total = max(1, len(words_list))
        f_size = int(base_size * (0.82 if total > 8 else 0.95 if total > 5 else 1.1))
        f_step = fonts.get_font('bold', f_size)
        timed_w = params.get('timed_words') or []
        
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for idx, item in enumerate(words_list):
            w_text = str(item.get('text', '')).strip()
            if not w_text: continue
            
            # Lookup timed word
            tw_match = next((tw for tw in timed_w if tw.get('text', '').lower() == w_text.lower()), None)
            step_offset = float(tw_match.get('offset', idx * 0.26)) if tw_match else float(item.get('offset', idx * 0.26))
            step_dur = float(tw_match.get('duration', 0.28)) if tw_match else 0.28
            
            word_start = graphic.start + step_offset
            word_end = word_start + step_dur
            is_active = (t >= word_start and t <= word_end)
            has_spoken = (t >= word_start)
            if not has_spoken: continue
            
            w_prog = max(0.0, min(1.0, (elapsed_total - step_offset) / max(0.1, step_dur)))
            
            # Halo body arch formula: idx 0 (left ear/shoulder) -> center (crown over head) -> last (right)
            t_step = idx / max(1, total - 1)
            arch_angle = (t_step - 0.5) * math.pi * 0.65
            wx = int(width * 0.50 + width * 0.38 * math.sin(arch_angle))
            wy = int(height * 0.22 - height * 0.15 * (math.cos(arch_angle) - 1))
            
            text_color = (255, 230, 0, int(255 * exit)) if is_active else (255, 255, 255, int(255 * exit))
            draw.text((wx, wy), w_text.upper(), font=f_step, fill=text_color, anchor='mm', stroke_width=max(1, int(width / 750)), stroke_fill=(0, 0, 0, int(220 * exit)))
            
        alpha = layer.getchannel('A').point(lambda v: int(v * exit))
        canvas.paste(layer, (0, 0), alpha)
        return

    # 11. COOKED_BADGE (Massive expressive red cursive script + solid dark pill badges - Image 1 Panel 11)
    if style == 'cooked_badge':
        prog = max(0.0, min(1.0, elapsed_total / duration))
        cx = int(width * graphic.pos_x)
        cy = int(height * graphic.pos_y)
        
        script_head = lines[0].get('text', '') if len(lines) > 0 else 'Cooked'
        sub_words = [w for w in (lines[1].get('text', '') if len(lines) > 1 else '').split(' ') if w.strip()]
        
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        
        # Giant red cursive header
        f_script = fonts.get_font('script', int(base_size * 2.3))
        draw.text((cx, cy - int(base_size * 0.8)), str(script_head), font=f_script, fill=(220, 38, 38, 255), anchor='mm', stroke_width=0, stroke_fill=(0, 0, 0, 0))
        
        # Solid dark pill badges underneath
        f_badge = fonts.get_font('bold', int(base_size * 0.78))
        pill_y = cy + int(base_size * 0.95)
        total_pills = len(sub_words)
        if total_pills > 0:
            pill_widths = [draw.textlength(w.upper(), font=f_badge) + width * .045 for w in sub_words]
            gap = width * .015
            start_px = cx - (sum(pill_widths) + gap * max(0, total_pills - 1)) / 2
            
            for p_idx, word in enumerate(sub_words):
                px = start_px + sum(pill_widths[:p_idx]) + gap * p_idx + pill_widths[p_idx] / 2
                bbox = draw.textbbox((px, pill_y), word.upper(), font=f_badge, anchor='mm')
                pw = (bbox[2] - bbox[0]) + int(width * 0.04)
                ph = int(base_size * 1.05)
                draw.rounded_rectangle((px - pw // 2, pill_y - ph // 2, px + pw // 2, pill_y + ph // 2), radius=10, fill=(24, 24, 27, 245), outline=(255, 255, 255, 50), width=1)
                draw.text((px, pill_y), word.upper(), font=f_badge, fill=(255, 255, 255, 255), anchor='mm')
            
        alpha = layer.getchannel('A').point(lambda v: int(v * min(prog, exit)))
        canvas.paste(layer, (0, 0), alpha)
        return

    # Default fallback
    for i, line in enumerate(lines):
        text = str(line.get('text', '')).strip()
        if not text: continue
        progress = max(0.0, min(1.0, (t - graphic.start - float(line.get('offset', 0))) / duration))
        eased = 1 - (1 - progress)**3
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        font = fonts.get_font('bold', base_size)
        x = width * graphic.pos_x
        y = height * graphic.pos_y + (i - (len(lines) - 1) / 2) * base_size * 1.2 + (1 - eased) * width * 0.04
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255), anchor='mm', stroke_width=2, stroke_fill=(0, 0, 0, 255))
        alpha = layer.getchannel('A').point(lambda v: int(v * min(progress, exit)))
        canvas.paste(layer, (0, 0), alpha)

def render_dimension_callout(
    canvas: Image.Image,
    graphic: MotionGraphicItem,
    canvas_w: int,
    canvas_h: int,
    fonts: FontManager
) -> None:
    params = graphic.parameters
    color_hex = params.get('color', '#00F0FF')
    color_rgb = hex_to_rgb(color_hex, (0, 240, 255))
    meas_text = str(params.get('measurement_text', '14 FEET LONG')).upper()
    subtext = str(params.get('subtext', '')).upper() if params.get('subtext') else None

    s = canvas_w / 380.0
    callout_w = min(int(320 * s), int(canvas_w * 0.88))
    center_x = int((graphic.pos_x or 0.5) * canvas_w)
    center_y = int((graphic.pos_y or 0.5) * canvas_h)

    left_x = center_x - callout_w // 2
    right_x = center_x + callout_w // 2
    line_y = center_y

    overlay = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    tick_h = int(14 * s)
    stroke_w = max(2, int(2.5 * s))

    # Left & right end-cap ticks
    d.line([(left_x, line_y - tick_h), (left_x, line_y + tick_h)], fill=(*color_rgb, 255), width=stroke_w)
    d.line([(right_x, line_y - tick_h), (right_x, line_y + tick_h)], fill=(*color_rgb, 255), width=stroke_w)

    # Measurement text font & pill size
    fnt_meas = fonts.get_font('mono', max(12, int(13 * s)))
    bbox_m = fnt_meas.getbbox(meas_text)
    mw = bbox_m[2] - bbox_m[0]
    mh = bbox_m[3] - bbox_m[1]

    pill_pad_x = int(16 * s)
    pill_pad_y = int(8 * s)
    pill_w = mw + pill_pad_x * 2
    pill_h = mh + pill_pad_y * 2
    pill_left = center_x - pill_w // 2
    pill_top = center_y - pill_h // 2

    # Left dashed line & arrowhead
    dash_len = max(4, int(6 * s))
    gap_len = max(3, int(4 * s))
    cur = left_x + int(4 * s)
    end_seg1 = pill_left - int(8 * s)
    while cur < end_seg1:
        d.line([(cur, line_y), (min(cur + dash_len, end_seg1), line_y)], fill=(*color_rgb, 220), width=max(1, int(2 * s)))
        cur += dash_len + gap_len
    arrow_size = int(8 * s)
    d.polygon([(left_x + 2, line_y), (left_x + 2 + arrow_size, line_y - int(5 * s)), (left_x + 2 + arrow_size, line_y + int(5 * s))], fill=(*color_rgb, 255))

    # Right dashed line & arrowhead
    cur = pill_left + pill_w + int(8 * s)
    while cur < right_x - int(4 * s):
        d.line([(cur, line_y), (min(cur + dash_len, right_x - int(4 * s)), line_y)], fill=(*color_rgb, 220), width=max(1, int(2 * s)))
        cur += dash_len + gap_len
    d.polygon([(right_x - 2, line_y), (right_x - 2 - arrow_size, line_y - int(5 * s)), (right_x - 2 - arrow_size, line_y + int(5 * s))], fill=(*color_rgb, 255))

    # Center pill
    d.rounded_rectangle([pill_left, pill_top, pill_left + pill_w, pill_top + pill_h], radius=pill_h // 2, fill=(10, 15, 20, 245), outline=(*color_rgb, 255), width=max(1, int(2 * s)))
    d.ellipse([pill_left + int(12 * s) - 3, center_y - 3, pill_left + int(12 * s) + 3, center_y + 3], fill=(*color_rgb, 255))
    d.text((pill_left + int(20 * s), center_y), meas_text, font=fnt_meas, fill=(*color_rgb, 255), anchor='lm')

    if subtext:
        fnt_sub = fonts.get_font('mono', max(9, int(10 * s)))
        bbox_s = fnt_sub.getbbox(subtext)
        sw = bbox_s[2] - bbox_s[0]
        sh = bbox_s[3] - bbox_s[1]
        spill_w = sw + int(14 * s)
        spill_h = sh + int(8 * s)
        spill_top = pill_top + pill_h + int(6 * s)
        spill_left = center_x - spill_w // 2
        d.rounded_rectangle([spill_left, spill_top, spill_left + spill_w, spill_top + spill_h], radius=int(4 * s), fill=(10, 10, 10, 210), outline=(80, 80, 80, 200), width=1)
        d.text((center_x, spill_top + spill_h // 2), subtext, font=fnt_sub, fill=(210, 210, 210, 255), anchor='mm')

    canvas.paste(overlay, (0, 0), overlay)

def render_corner_bug(canvas: Image.Image, settings_obj: Any, canvas_w: int, fonts: FontManager):
    return
    text = getattr(settings_obj, 'corner_bug_text', '') or "ARCHIVE DOCS"
    font = fonts.get_font('mono', 12)
    bbox = font.getbbox(text)
    pw = bbox[2] - bbox[0] + 28
    ph = bbox[3] - bbox[1] + 14

    pill = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(pill)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=6, fill=(0, 0, 0, 200), outline=(255, 255, 255, 60))
    d.ellipse([8, ph // 2 - 3, 14, ph // 2 + 3], fill=(255, 255, 255, 255))
    d.text((20, ph // 2), text, font=font, fill=(255, 255, 255, 255), anchor='lm')
    canvas.paste(pill, (canvas_w - pw - 16, 16), pill)

def render_caption_overlay(
    canvas: Image.Image,
    caption: CaptionItem,
    t: float,
    canvas_w: int,
    canvas_h: int,
    is_split_active: bool,
    fonts: FontManager,
    brand_preset: str = "documentary_minimalist"
) -> None:
    style = caption.style
    text = caption.translated_text if caption.translated_text else caption.text
    if style.is_uppercase:
        text = text.upper()

    # Respect style.has_background unconditionally!
    is_doc_minimalist = not style.has_background

    s = canvas_w / 380.0

    if is_split_active:
        pos_y = caption.pos_y_during_graphic if caption.pos_y_during_graphic is not None else 0.90
    else:
        pos_y = caption.pos_y if caption.pos_y is not None else 0.82

    pos_x = caption.pos_x if caption.pos_x is not None else 0.50
    center_x = int(pos_x * canvas_w)
    center_y = int(pos_y * canvas_h)

    base_size = max(14, int(style.font_size * s))
    font_sans = fonts.get_font('bold', base_size)
    font_serif = fonts.get_font('serif', base_size)

    has_active_word_highlight = getattr(style, 'has_highlight', True) is not False
    has_keyword_emp = getattr(style, 'has_keyword_emphasis', True) is not False
    default_text_col = hex_to_rgb(style.text_color or style.highlight_future_color or '#FFFFFF', (255, 255, 255))
    act_col = hex_to_rgb(style.highlight_active_color, (56, 189, 248))
    past_col = hex_to_rgb(style.highlight_past_color, (176, 176, 176))
    future_col = default_text_col

    word_items: List[Tuple[str, ImageFont.ImageFont, Tuple[int, int, int]]] = []

    if caption.words and len(caption.words) > 0:
        for w in caption.words:
            w_str = w.word.upper() if style.is_uppercase else w.word
            word_items.append((w_str, font_sans, default_text_col))
    else:
        raw_words = text.split()
        for rw in raw_words:
            is_kw, kw_cat, kw_color = check_is_keyword(rw)
            w_is_kw = has_keyword_emp and is_kw
            fnt = font_serif if (w_is_kw and kw_cat in ['condition', 'organ']) else font_sans
            col = default_text_col
            if w_is_kw:
                col = hex_to_rgb(kw_color, kw_color)
            word_items.append((rw, fnt, col))

    if not word_items:
        return

    space_w = font_sans.getbbox(' ')[2] - font_sans.getbbox(' ')[0]
    total_text_w = 0
    word_widths = []
    max_h = 0

    for w_str, fnt, _ in word_items:
        bbox = fnt.getbbox(w_str)
        ww = bbox[2] - bbox[0]
        wh = bbox[3] - bbox[1]
        word_widths.append(ww)
        total_text_w += ww
        if wh > max_h:
            max_h = wh
    total_text_w += (len(word_items) - 1) * space_w

    pad_x = int(style.padding_x * s) if not is_doc_minimalist else int(6 * s)
    pad_y = int(style.padding_y * s) if not is_doc_minimalist else int(3 * s)
    box_w = total_text_w + pad_x * 2
    box_h = max_h + pad_y * 2
    left = center_x - box_w // 2
    top = center_y - box_h // 2

    # Draw rounded background box / pill
    if style.has_background:
        pill = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
        d_pill = ImageDraw.Draw(pill)
        bg_rgb = hex_to_rgb(style.background_color, (0, 0, 0))
        bg_alpha = int(style.background_opacity * 255)
        radius = box_h // 2 if style.contrast_block_mode == 'pill' else min(box_h // 2, int(style.corner_radius * s))
        d_pill.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=radius, fill=(*bg_rgb, bg_alpha))
        canvas.paste(pill, (left, top), pill)

    # Draw styled words with shadow & outline
    d = ImageDraw.Draw(canvas)
    cur_x = left + pad_x

    outline_w = int(getattr(style, 'outline_width', 0) * s)
    outline_col = hex_to_rgb(getattr(style, 'outline_color', '#000000'), (0, 0, 0))
    has_shadow = getattr(style, 'has_shadow', True) is not False

    for idx, (w_str, fnt, col) in enumerate(word_items):
        if has_shadow:
            shadow_off_x = max(1, int(getattr(style, 'shadow_offset_x', 0) * s))
            shadow_off_y = max(2, int(getattr(style, 'shadow_offset_y', 2) * s))
            d.text((cur_x + shadow_off_x, center_y + shadow_off_y), w_str, font=fnt, fill=(0, 0, 0), anchor='lm')

        if outline_w > 0:
            for ox in [-outline_w, outline_w]:
                for oy in [-outline_w, outline_w]:
                    d.text((cur_x + ox, center_y + oy), w_str, font=fnt, fill=outline_col, anchor='lm')

        d.text((cur_x, center_y), w_str, font=fnt, fill=col, anchor='lm')
        cur_x += word_widths[idx] + space_w

class BurnInRenderer:
    def __init__(self, ffmpeg_bin: str = settings.ffmpeg_bin):
        self.ffmpeg_bin = ffmpeg_bin
        self.progress: Dict[str, Dict[str, Any]] = {}

    def get_progress(self, project_id: str) -> Dict[str, Any]:
        return self.progress.get(project_id, {"percent": 0, "status": "idle"})

    def render_burned_video(self, project: ProjectState, subtitles_only: bool = False) -> Dict[str, Any]:
        pdir = settings.projects_dir / project.id
        export_dir = pdir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        download_dir = pdir / "media" / "downloaded"
        download_dir.mkdir(parents=True, exist_ok=True)
        target_filename = f"{project.name}_subtitled.mp4" if subtitles_only else f"{project.name}_burned.mp4"
        output_mp4 = export_dir / target_filename

        self.progress[project.id] = {
            "percent": 0,
            "status": "starting",
            "frame": 0,
            "total_frames": max(1, int((project.duration_seconds or 10.0) * 30.0)),
            "mode": "subtitles_only" if subtitles_only else "full"
        }

        is_916 = project.settings.aspect_ratio == "9:16"
        canvas_w = 720 if is_916 else 1280
        canvas_h = 1280 if is_916 else 720

        # Resolve real source video path accurately
        source_path = project.source_media_path
        if source_path and not os.path.isabs(source_path):
            if (pdir / source_path).exists():
                source_path = str(pdir / source_path)
            elif (settings.projects_dir / project.id / source_path).exists():
                source_path = str(settings.projects_dir / project.id / source_path)
        if (not source_path or not os.path.exists(source_path)):
            for cand in ["sub.mov", "sub.mp4", "uploaded_video.mp4"]:
                if (pdir / cand).exists():
                    source_path = str(pdir / cand)
                    break

        has_real_source = bool(source_path and os.path.exists(source_path))
        fonts = FontManager()

        # Pre-cache graphic media images and video decoders
        cached_images: Dict[str, Optional[Image.Image]] = {}
        video_players: Dict[str, VideoClipPlayer] = {}

        if not subtitles_only:
            for g in project.graphics:
                raw_url = g.parameters.get('media_url') or g.media_url
                if not raw_url:
                    continue
                if raw_url in cached_images or raw_url in video_players:
                    continue

                local_file = resolve_media_file(raw_url, project.id, download_dir)
                if local_file and local_file.exists():
                    is_insert = getattr(g, 'placement_mode', 'overlay') == 'insert' or g.template_id == 'youtube_insert'
                    split_ratio = float(g.parameters.get('split_ratio', 0.50))
                    target_media_h = canvas_h if is_insert else int(canvas_h * split_ratio)
                    is_vid = any(ve in local_file.suffix.lower() for ve in ['.mp4', '.mov', '.webm', '.m4v', '.avi']) or g.parameters.get('media_type') == 'video' or g.media_type == 'video'
                    if is_vid:
                        try:
                            video_players[raw_url] = VideoClipPlayer(str(local_file), canvas_w, target_media_h)
                        except Exception as e:
                            print(f"[BurnInRenderer] Video preload error: {e}")
                    else:
                        try:
                            img = Image.open(local_file).convert('RGB')
                            cached_images[raw_url] = crop_to_aspect(img, canvas_w, target_media_h)
                        except Exception as e:
                            print(f"[BurnInRenderer] Image preload error: {e}")
                else:
                    cached_images[raw_url] = None

        fps = float(project.fps or 30.0)

        if has_real_source:
            input_args = [
                "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{canvas_w}x{canvas_h}", "-pix_fmt", "rgb24", "-r", str(fps), "-i", "-",
                "-i", source_path,
                "-map", "0:v", "-map", "1:a?",
                "-c:v", "h264_videotoolbox", "-b:v", "4000k",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(output_mp4)
            ]
        else:
            duration = max(3.0, project.duration_seconds or 10.0)
            input_args = [
                "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{canvas_w}x{canvas_h}", "-pix_fmt", "rgb24", "-r", str(fps), "-i", "-",
                "-c:v", "h264_videotoolbox", "-b:v", "4000k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-t", str(duration),
                str(output_mp4)
            ]

        # Audio: the speaker's voice, generated sound effects and a licensed music bed, mixed once.
        # The bed fades in and out and is pushed down under speech (sidechain ducking).
        extra_inputs, labels, filters = [], [], []
        has_audio = False
        if has_real_source:
            with av.open(source_path) as source_container: has_audio = bool(source_container.streams.audio)
        first_extra = 2 if has_real_source else 1
        voice = '[1:a]' if has_audio else None
        if not subtitles_only and any(g.parameters.get('sfx_track_url') and not g.parameters.get('sfx_muted') for g in project.graphics):
            from app.services.automatic_sfx import prepare_sfx
            sfx_path = prepare_sfx(project.id, project.graphics, project.duration_seconds)
            if sfx_path:
                labels.append(f'[{first_extra + len(extra_inputs)}:a]'); extra_inputs.append(str(sfx_path))
        if not subtitles_only:
            from app.services.music_service import local_file, bed_filter
            for track in (t for t in getattr(project, 'audio_tracks', []) if t.type == 'music' and t.music_id):
                path = local_file(track.music_id)
                if not path: continue
                index = first_extra + len(extra_inputs); extra_inputs.append(str(path))
                length = max(.5, min(track.duration or project.duration_seconds, (project.duration_seconds or track.duration) - track.start))
                text, bed, voice_out = bed_filter(index, track.start, length, track.volume, voice[1:-1] if (voice and track.duck_under_speech) else None)
                filters.append(text); labels.append(bed)
                if voice_out: voice = voice_out
        if extra_inputs:
            position = input_args.index('-map') if '-map' in input_args else input_args.index('-c:v')
            for path in reversed(extra_inputs): input_args[position:position] = ['-i', path]
            parts = ([voice] if voice else []) + labels
            if len(parts) == 1 and not filters:
                mix_label = parts[0].strip('[]')
            else:
                filters.append(f"{''.join(parts)}amix=inputs={len(parts)}:duration=longest:normalize=0,alimiter=limit=0.95:level=0[mixed]")
                mix_label = '[mixed]'
                input_args[-1:-1] = ['-filter_complex', ';'.join(filters), '-shortest']
            if '1:a?' in input_args: input_args[input_args.index('1:a?')] = mix_label
            else: input_args[-1:-1] = ['-map', '0:v', '-map', mix_label, '-c:a', 'aac']

        # VideoToolbox can be installed yet unavailable (busy/headless session).
        probe=subprocess.run([self.ffmpeg_bin,'-hide_banner','-loglevel','error','-f','lavfi','-i',f'color=black:s={canvas_w}x{canvas_h}:r=30','-frames:v','1','-c:v','h264_videotoolbox','-f','null','-'],capture_output=True,timeout=15)
        if probe.returncode:
            input_args[input_args.index('h264_videotoolbox')]='libx264'
            input_args[-1:-1]=['-preset','veryfast','-threads','4']
        cmd = [self.ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y", *input_args]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            total_frames = max(1, int((project.duration_seconds or 10.0) * fps))
            sorted_captions = sorted(project.captions, key=lambda c: c.start)

            if has_real_source:
                container = av.open(source_path)
                video_stream = container.streams.video[0]
                frame_idx = 0

                for frame in container.decode(video_stream):
                    t = frame_idx / fps
                    frame_idx += 1

                    if frame_idx % 15 == 0 or frame_idx == 1:
                        pct = min(99, int((frame_idx / total_frames) * 100))
                        self.progress[project.id] = {
                            "percent": pct,
                            "frame": frame_idx,
                            "total_frames": total_frames,
                            "status": "rendering",
                            "mode": "subtitles_only" if subtitles_only else "full"
                        }

                    base_speaker_frame = frame.to_image()

                    # Find all active graphics at timecode t
                    active_graphics = []
                    if not subtitles_only:
                        for g in project.graphics:
                            if g.start <= t <= g.end:
                                active_graphics.append(g)

                    base_speaker_frame = apply_source_reframe(base_speaker_frame, active_graphics, t)
                    active_split = next((g for g in active_graphics if g.template_id == "split_screen_vertical" or g.split_layout == "split_50_50_vertical" or g.parameters.get("split_layout") == "split_50_50_vertical"), None)
                    active_article = next((g for g in active_graphics if g.template_id == "article_reconstruction"), None)
                    active_insert = next((g for g in active_graphics if getattr(g, 'placement_mode', 'overlay') == 'insert' or g.template_id == 'youtube_insert'), None)
                    active_endcard = next((g for g in active_graphics if g.template_id == "medical_endcard" or g.template_id == "documentary_outro"), None)

                    # 1. Base Layer Composition
                    if active_endcard:
                        base = crop_to_aspect(base_speaker_frame, canvas_w, canvas_h)
                        canvas = render_medical_endcard(base, active_endcard, canvas_w, canvas_h, fonts)
                    elif active_article:
                        canvas = render_article_reconstruction(base_speaker_frame, active_article, canvas_w, canvas_h, fonts, t)
                    elif active_split:
                        canvas = render_split_50_50(base_speaker_frame, active_split, canvas_w, canvas_h, fonts, cached_images, video_players, t)
                    elif active_insert:
                        canvas = compose_cutaway(active_insert, base_speaker_frame, t, canvas_w, canvas_h, fonts, cached_images, video_players)
                    else:
                        canvas = crop_to_aspect(base_speaker_frame, canvas_w, canvas_h)

                    # 2. Overlays (Dimension Callouts, Article Cards on top of split, etc.)
                    for ov in active_graphics:
                        if ov.template_id == "caption_cover":
                            top=float(ov.parameters.get('top',.675));height=float(ov.parameters.get('height',.05))
                            ImageDraw.Draw(canvas).rectangle((0,round(top*canvas_h),canvas_w,round((top+height)*canvas_h)),fill=ov.parameters.get('color','#111315'))
                        if ov.template_id == "kinetic_typography":
                            render_editorial_text(canvas, ov, canvas_w, canvas_h, fonts, t)
                        if ov.template_id == "dimension_callout":
                            render_dimension_callout(canvas, ov, canvas_w, canvas_h, fonts)


                    # 3. Corner Bug Watermark
                    if not subtitles_only:
                        render_corner_bug(canvas, project.settings, canvas_w, fonts)

                    # 4. Active Caption with GAP PERSISTENCE
                    active_cap = None
                    for i, cap in enumerate(sorted_captions):
                        if cap.start <= t < cap.end:
                            active_cap = cap
                            break

                    is_title_active = any(
                        (getattr(g, 'parameters', {}) or {}).get("suppress_subtitles") is True or
                        getattr(g, 'template_id', '') == "kinetic_typography" or
                        bool((getattr(g, 'parameters', {}) or {}).get("title_style")) or
                        getattr(g, 'track', '') == "V5"
                        for g in active_graphics
                    )
                    if active_cap and not is_title_active:
                        render_caption_overlay(canvas, active_cap, t, canvas_w, canvas_h, bool(active_split), fonts, project.settings.brand_preset)

                    proc.stdin.write(canvas.tobytes())

            else:
                fallback_base = Image.new('RGB', (canvas_w, canvas_h), (20, 20, 25))

                for frame_idx in range(total_frames):
                    t = frame_idx / fps

                    if frame_idx % 15 == 0 or frame_idx == 1:
                        pct = min(99, int((frame_idx / total_frames) * 100))
                        self.progress[project.id] = {
                            "percent": pct,
                            "frame": frame_idx,
                            "total_frames": total_frames,
                            "status": "rendering",
                            "mode": "subtitles_only" if subtitles_only else "full"
                        }

                    base_speaker_frame = fallback_base.copy()

                    active_graphics = []
                    if not subtitles_only:
                        for g in project.graphics:
                            if g.start <= t <= g.end:
                                active_graphics.append(g)

                    base_speaker_frame = apply_source_reframe(base_speaker_frame, active_graphics, t)
                    active_split = next((g for g in active_graphics if g.template_id == "split_screen_vertical" or g.split_layout == "split_50_50_vertical" or g.parameters.get("split_layout") == "split_50_50_vertical"), None)
                    active_article = next((g for g in active_graphics if g.template_id == "article_reconstruction"), None)
                    active_insert = next((g for g in active_graphics if getattr(g, 'placement_mode', 'overlay') == 'insert' or g.template_id == 'youtube_insert'), None)
                    active_endcard = next((g for g in active_graphics if g.template_id == "medical_endcard" or g.template_id == "documentary_outro"), None)

                    if active_endcard:
                        base = fallback_base.copy()
                        canvas = render_medical_endcard(base, active_endcard, canvas_w, canvas_h, fonts)
                    elif active_article:
                        canvas = render_article_reconstruction(base_speaker_frame, active_article, canvas_w, canvas_h, fonts, t)
                    elif active_split:
                        canvas = render_split_50_50(base_speaker_frame, active_split, canvas_w, canvas_h, fonts, cached_images, video_players, t)
                    elif active_insert:
                        canvas = compose_cutaway(active_insert, base_speaker_frame, t, canvas_w, canvas_h, fonts, cached_images, video_players)
                    else:
                        canvas = base_speaker_frame

                    for ov in active_graphics:
                        if ov.template_id == "caption_cover":
                            top=float(ov.parameters.get('top',.675));height=float(ov.parameters.get('height',.05))
                            ImageDraw.Draw(canvas).rectangle((0,round(top*canvas_h),canvas_w,round((top+height)*canvas_h)),fill=ov.parameters.get('color','#111315'))
                        if ov.template_id == "kinetic_typography":
                            render_editorial_text(canvas, ov, canvas_w, canvas_h, fonts, t)
                        if ov.template_id == "dimension_callout":
                            render_dimension_callout(canvas, ov, canvas_w, canvas_h, fonts)

                    if not subtitles_only:
                        render_corner_bug(canvas, project.settings, canvas_w, fonts)

                    active_cap = None
                    for i, cap in enumerate(sorted_captions):
                        if cap.start <= t < cap.end:
                            active_cap = cap
                            break

                    is_title_active = any(
                        (getattr(g, 'parameters', {}) or {}).get("suppress_subtitles") is True or
                        getattr(g, 'template_id', '') == "kinetic_typography" or
                        bool((getattr(g, 'parameters', {}) or {}).get("title_style")) or
                        getattr(g, 'track', '') == "V5"
                        for g in active_graphics
                    )
                    if active_cap and not is_title_active:
                        render_caption_overlay(canvas, active_cap, t, canvas_w, canvas_h, bool(active_split), fonts, project.settings.brand_preset)

                    proc.stdin.write(canvas.tobytes())

            proc.stdin.close()
            proc.wait()

            if proc.returncode != 0:
                err = proc.stderr.read().decode('utf-8', errors='ignore')
                print("[BurnInRenderer Error]", err)
                self.progress[project.id] = {"percent": 0, "status": "error", "error": err}
                return {"success": False, "error": err}

            self.progress[project.id] = {
                "percent": 100,
                "status": "completed",
                "output_path": str(output_mp4),
                "file_size": os.path.getsize(output_mp4)
            }
            return {
                "success": True,
                "output_path": str(output_mp4),
                "file_size": os.path.getsize(output_mp4)
            }

        except Exception as e:
            if proc.stdin and not proc.stdin.closed:
                try:proc.stdin.close()
                except BrokenPipeError:pass
            proc.kill()
            proc.stdin=None
            _,stderr=proc.communicate()
            e=RuntimeError((stderr or b'').decode('utf-8',errors='replace')[-3000:] or str(e))
            print("[BurnInRenderer Exception]", e)
            self.progress[project.id] = {"percent": 0, "status": "error", "error": str(e)}
            return {"success": False, "error": str(e)}

burnin_renderer = BurnInRenderer()
