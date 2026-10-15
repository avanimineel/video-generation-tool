"""
========================================================================================
🎬 PRODUCTION 9:16 SHORT-FORM VIDEO AUTOMATION ENGINE
========================================================================================
Automated composition pipeline for viral split-screen reels (1080x1920):
1. Split-screen Layout: Top half B-roll (1080x960), Bottom half Speaker (1080x960).
2. Dynamic B-roll Sequencer: Timestamp-accurate video & image cuts with ambient fallback.
3. Rapid Dynamic Subtitles: ASS generator with dead-center positioning and yellow/white pop.
4. Audio Pipeline & CTA: Enhanced audio replacement, high-impact CTA card & social outro.
5. FastAPI integration & standalone CLI executable.
========================================================================================
"""

import os
import re
import sys
import json
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("ReelComposer")

# --------------------------------------------------------------------------------------
# 1. DATA MODELS & SCHEMAS
# --------------------------------------------------------------------------------------

class BRollCue(BaseModel):
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    asset_filename: str = Field(..., description="Filename of video or image in B-roll folder")
    visual_type: Optional[str] = Field("broll_video", description="broll_video, article_headline, demonstration, etc.")
    description: Optional[str] = Field("", description="Editorial intent or scene summary")
    motion_style: Optional[str] = Field("cut", description="cut, slow_zoom_in, or pan")

class SubtitleItem(BaseModel):
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    text: str = Field(..., description="Caption text (1-4 words recommended)")
    highlight_words: Optional[List[str]] = Field(default_factory=list, description="Words highlighted in bold yellow")

class CTABannerConfig(BaseModel):
    enabled: bool = True
    start_time: float = 11.0
    end_time: float = 14.5
    keyword: str = "TEST"
    headline: str = 'COMMENT "TEST"'
    subtext: str = "TO RECEIVE THE OFFICIAL BLUEPRINT"

class EndScreenConfig(BaseModel):
    enabled: bool = True
    duration_seconds: float = 2.5
    creator_handle: str = "@CREATOR"
    action_prompt: str = "LIKE • SHARE • FOLLOW FOR MORE"

class ReelConfig(BaseModel):
    output_width: int = 1080
    output_height: int = 1920
    split_height: int = 960
    fps: int = 30
    crf: int = 18
    preset: str = "fast"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "256k"
    ffmpeg_bin: Optional[str] = None

# --------------------------------------------------------------------------------------
# 2. SUBSTATION ALPHA (.ASS) SUBTITLE GENERATOR
# --------------------------------------------------------------------------------------

def format_ass_timestamp(seconds: float) -> str:
    """Converts float seconds to ASS timestamp format: H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"

def generate_ass_subtitles(
    subtitles: List[SubtitleItem],
    output_path: Path,
    font_name: str = "Arial Black",
    font_size: int = 70,
    outline_width: int = 7,
    shadow_depth: int = 3
) -> Path:
    """
    Generates a .ass subtitle file with:
    - Dead-center positioning (Alignment=5) on a 1080x1920 canvas.
    - Word-level alternating bold yellow (&H0000FFFF&) and crisp white (&H00FFFFFF&).
    - Heavy black outline and shadow for maximum readability over busy visuals.
    """
    # ASS Colors are specified as &HAABBGGRR in hexadecimal:
    # Yellow (RGB 255, 255, 0)   -> &H0000FFFF&
    # White  (RGB 255, 255, 255) -> &H00FFFFFF&
    # Black  (RGB 0, 0, 0)       -> &H00000000&
    
    header = f"""[Script Info]
Title: Viral 9:16 Kinetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline_width},{shadow_depth},5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for item in subtitles:
        t_start = format_ass_timestamp(item.start_time)
        t_end = format_ass_timestamp(item.end_time)
        
        # Split text into tokens and apply yellow/white contrast styling
        raw_words = item.text.strip().split()
        if not raw_words:
            continue
            
        highlight_set = {re.sub(r'[^A-Za-z0-9]', '', w).upper() for w in (item.highlight_words or [])}
        
        formatted_words = []
        for idx, word in enumerate(raw_words):
            clean_word = re.sub(r'[^A-Za-z0-9]', '', word).upper()
            
            # Highlight if explicitly tagged or on alternating cadence when no tags are provided
            is_highlighted = (clean_word in highlight_set) if highlight_set else (idx % 2 == 0 and len(raw_words) > 1)
            
            if is_highlighted:
                # Yellow text
                formatted_words.append(r"{\c&H00FFFF&}" + word.upper() + r"{\c&HFFFFFF&}")
            else:
                # White text
                formatted_words.append(r"{\c&HFFFFFF&}" + word.upper())
                
        line_text = " ".join(formatted_words)
        events.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{line_text}")

    output_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    logger.info(f"Generated ASS subtitle file with {len(events)} cues at: {output_path}")
    return output_path

# --------------------------------------------------------------------------------------
# 3. ADVANCED FFMPEG FILTERGRAPH GENERATOR
# --------------------------------------------------------------------------------------

def find_ffmpeg_binary(configured_bin: Optional[str] = None) -> str:
    """Locates the FFmpeg executable across common bundled and system paths."""
    candidates = [
        configured_bin,
        os.getenv("FFMPEG_BIN"),
        str(Path(__file__).resolve().parents[1] / "backend" / "vendor_runtime" / "imageio_ffmpeg" / "binaries" / "ffmpeg-macos-aarch64-v7.1"),
        shutil.which("ffmpeg"),
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg"
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return str(c)
    return "ffmpeg"

def build_ffmpeg_filtergraph(
    speaker_input_idx: int,
    broll_inputs: List[Tuple[int, BRollCue, bool]],  # (ffmpeg_input_idx, cue, is_image)
    ass_subtitle_path: Optional[Path],
    cta_banner: Optional[CTABannerConfig],
    end_screen: Optional[EndScreenConfig],
    video_duration: float,
    config: ReelConfig
) -> Tuple[str, str]:
    """
    Constructs the complete FFmpeg -filter_complex string and returns (filter_str, final_v_label).
    
    Layout Pipeline:
    1. [spk_bottom]: Crop & scale speaker to bottom half (1080x960).
    2. [top_bg]: Ambient blurred speaker crop to serve as background plate (no black void).
    3. [base_canvas]: vstack [top_bg] + [spk_bottom] into 1080x1920.
    4. [c0]: Subtle 3px divider line at y=960.
    5. [c1..cN]: Sequentially overlay B-roll clips on top half (0,0) based on timestamps.
    6. [c_sub]: Burn in ASS subtitles dead center.
    7. [c_cta]: Render high-contrast CTA card ("COMMENT 'TEST'").
    8. [final_v]: Render social outro / end-screen plate during final 2.5s.
    """
    filters = []
    
    # --- 1. Bottom Speaker Half (1080x960) ---
    # Scales to fill 1080 width, center crops 960 height, forces SAR 1:1
    filters.append(
        f"[{speaker_input_idx}:v]scale={config.output_width}:{config.output_height}:force_original_aspect_ratio=increase,"
        f"crop={config.output_width}:{config.split_height}:(in_w-{config.output_width})/2:(in_h-{config.split_height})/2,"
        f"setsar=1,fps={config.fps}[spk_bottom]"
    )
    
    # --- 2. Ambient Top Half Plate (1080x960) ---
    # Blurred, darkened speaker video that fills the top half whenever no B-roll is active
    filters.append(
        f"[{speaker_input_idx}:v]scale={config.output_width}:{config.split_height}:force_original_aspect_ratio=increase,"
        f"crop={config.output_width}:{config.split_height}:(in_w-{config.output_width})/2:(in_h-{config.split_height})/2,"
        f"boxblur=25:5,eq=brightness=-0.18,setsar=1,fps={config.fps}[top_bg]"
    )
    
    # --- 3. Base Split-Screen Canvas ---
    filters.append(f"[top_bg][spk_bottom]vstack=inputs=2[base_canvas]")
    
    # --- 4. Sleek Horizontal Divider Line ---
    divider_y = config.split_height - 2
    filters.append(f"[base_canvas]drawbox=x=0:y={divider_y}:w={config.output_width}:h=4:color=white@0.35:t=fill[c_base]")
    
    # --- 5. Dynamic B-Roll Overlay Sequence ---
    current_stream = "c_base"
    
    for idx, (in_idx, cue, is_image) in enumerate(broll_inputs):
        broll_label = f"broll_{idx}"
        next_stream = f"c_broll_{idx}"
        clip_dur = max(0.2, cue.end_time - cue.start_time)
        
        # Scale & center crop B-roll to exactly 1080x960
        scale_crop = (
            f"scale={config.output_width}:{config.split_height}:force_original_aspect_ratio=increase,"
            f"crop={config.output_width}:{config.split_height}:(in_w-{config.output_width})/2:(in_h-{config.split_height})/2,"
            f"setsar=1,fps={config.fps}"
        )
        
        # Trim and retime overlay PTS to match master timeline t
        filters.append(
            f"[{in_idx}:v]{scale_crop},trim=duration={clip_dur:.3f},"
            f"setpts=PTS-STARTPTS+{cue.start_time:.3f}/TB[{broll_label}]"
        )
        
        # Overlay on the top half (x=0, y=0) enabled strictly between start and end timestamps
        filters.append(
            f"[{current_stream}][{broll_label}]overlay=x=0:y=0:"
            f"enable='between(t,{cue.start_time:.3f},{cue.end_time:.3f})':eof_action=pass[{next_stream}]"
        )
        current_stream = next_stream

    # --- 6. ASS Subtitles Filter ---
    if ass_subtitle_path and ass_subtitle_path.exists():
        # Escape path for FFmpeg filter syntax (escape backslashes and single quotes)
        safe_ass_path = str(ass_subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")
        sub_stream = "c_sub"
        filters.append(f"[{current_stream}]ass='{safe_ass_path}'[{sub_stream}]")
        current_stream = sub_stream

    # --- 7. Call-To-Action (CTA) Overlay ---
    if cta_banner and cta_banner.enabled:
        cta_stream = "c_cta"
        cta_st = cta_banner.start_time
        cta_et = cta_banner.end_time
        enable_expr = f"between(t,{cta_st:.2f},{cta_et:.2f})"
        
        # High-impact yellow card with bold black text in the lower third
        card_w, card_h = 880, 150
        card_x = int((config.output_width - card_w) / 2)
        card_y = 1520
        
        cta_filters = [
            f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:color=0xFFFF00@0.95:t=fill:enable='{enable_expr}'",
            f"drawbox=x={card_x+6}:y={card_y+6}:w={card_w-12}:h={card_h-12}:color=black@0.15:t=fill:enable='{enable_expr}'",
            f"drawtext=text='{cta_banner.headline}':fontcolor=black:fontsize=46:x=(w-text_w)/2:y={card_y+24}:enable='{enable_expr}'",
            f"drawtext=text='{cta_banner.subtext}':fontcolor=black:fontsize=26:x=(w-text_w)/2:y={card_y+86}:enable='{enable_expr}'"
        ]
        filters.append(f"[{current_stream}]{','.join(cta_filters)}[{cta_stream}]")
        current_stream = cta_stream

    # --- 8. Final Social End-Screen Outro ---
    if end_screen and end_screen.enabled:
        outro_stream = "c_outro"
        outro_st = max(0.0, video_duration - end_screen.duration_seconds)
        outro_et = video_duration
        enable_expr = f"between(t,{outro_st:.2f},{outro_et:.2f})"
        
        # Darkening scrim over entire video + social brand plate
        outro_filters = [
            f"drawbox=x=0:y=0:w={config.output_width}:h={config.output_height}:color=black@0.75:t=fill:enable='{enable_expr}'",
            f"drawbox=x=120:y=760:w={config.output_width - 240}:h=400:color=white@0.10:t=fill:enable='{enable_expr}'",
            f"drawtext=text='{end_screen.creator_handle}':fontcolor=0x00FFFF:fontsize=64:x=(w-text_w)/2:y=840:enable='{enable_expr}'",
            f"drawtext=text='{end_screen.action_prompt}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=960:enable='{enable_expr}'",
            f"drawbox=x=340:y=1040:w=400:h=60:color=0xFFFF00:t=fill:enable='{enable_expr}'",
            f"drawtext=text='FOLLOW':fontcolor=black:fontsize=28:x=(w-text_w)/2:y=1055:enable='{enable_expr}'"
        ]
        filters.append(f"[{current_stream}]{','.join(outro_filters)}[{outro_stream}]")
        current_stream = outro_stream

    return ";\n".join(filters), current_stream

# --------------------------------------------------------------------------------------
# 4. MEDIA PROBE UTILITY
# --------------------------------------------------------------------------------------

def probe_video_duration(ffmpeg_bin: str, file_path: Path) -> float:
    """Extracts media duration in seconds via FFmpeg probe."""
    cmd = [ffmpeg_bin, "-i", str(file_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if m:
        h, m_min, s = m.groups()
        return int(h) * 3600 + int(m_min) * 60 + float(s)
    return 15.0

# --------------------------------------------------------------------------------------
# 5. MASTER RENDER PIPELINE
# --------------------------------------------------------------------------------------

def render_reel(
    speaker_video: Path,
    enhanced_audio: Path,
    broll_timeline_json: Path,
    subtitles_json: Path,
    broll_assets_dir: Path,
    output_video: Path,
    cta_config_json: Optional[Path] = None,
    config: Optional[ReelConfig] = None
) -> Dict[str, Any]:
    """
    Main orchestration function:
    - Parses input data.
    - Resolves B-roll files (video vs image).
    - Generates .ass subtitle file.
    - Executes complex FFmpeg filtergraph.
    - Replaces audio with enhanced .wav track.
    - Produces broadcast-ready 1080x1920 MP4 reel.
    """
    config = config or ReelConfig()
    ffmpeg_bin = find_ffmpeg_binary(config.ffmpeg_bin)
    logger.info(f"Using FFmpeg binary: {ffmpeg_bin}")

    # Validate mandatory inputs
    if not speaker_video.exists():
        raise FileNotFoundError(f"Speaker video not found: {speaker_video}")
    if not enhanced_audio.exists():
        raise FileNotFoundError(f"Enhanced audio not found: {enhanced_audio}")
    if not broll_timeline_json.exists():
        raise FileNotFoundError(f"Timeline JSON not found: {broll_timeline_json}")
    if not subtitles_json.exists():
        raise FileNotFoundError(f"Subtitles JSON not found: {subtitles_json}")

    # Probe duration
    speaker_duration = probe_video_duration(ffmpeg_bin, speaker_video)
    audio_duration = probe_video_duration(ffmpeg_bin, enhanced_audio)
    reel_duration = min(speaker_duration, audio_duration) if audio_duration > 0 else speaker_duration
    logger.info(f"Video timeline duration: {reel_duration:.2f}s")

    # Load B-Roll Timeline
    timeline_raw = json.loads(broll_timeline_json.read_text(encoding="utf-8"))
    cues = [BRollCue(**item) for item in timeline_raw]
    cues = sorted(cues, key=lambda c: c.start_time)

    # Load Subtitles
    subs_raw = json.loads(subtitles_json.read_text(encoding="utf-8"))
    sub_items = [SubtitleItem(**item) for item in subs_raw]

    # Load CTA & Outro Configuration
    cta_banner = None
    end_screen = None
    if cta_config_json and cta_config_json.exists():
        cta_data = json.loads(cta_config_json.read_text(encoding="utf-8"))
        if "cta_banner" in cta_data:
            cta_banner = CTABannerConfig(**cta_data["cta_banner"])
        if "end_screen" in cta_data:
            end_screen = EndScreenConfig(**cta_data["end_screen"])
    else:
        # Default CTA 3 seconds before end
        cta_banner = CTABannerConfig(start_time=max(0.0, reel_duration - 4.5), end_time=max(0.0, reel_duration - 1.5))
        end_screen = EndScreenConfig(duration_seconds=2.5)

    # Generate ASS Subtitles
    ass_path = output_video.parent / f"{output_video.stem}_subtitles.ass"
    generate_ass_subtitles(sub_items, ass_path)

    # Prepare FFmpeg inputs
    # Input 0: Speaker video
    # Input 1: Enhanced audio
    # Inputs 2..N: B-Roll assets
    cmd = [ffmpeg_bin, "-y"]
    cmd.extend(["-i", str(speaker_video.resolve())])
    cmd.extend(["-i", str(enhanced_audio.resolve())])

    broll_inputs: List[Tuple[int, BRollCue, bool]] = []
    current_input_idx = 2
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    for cue in cues:
        asset_path = broll_assets_dir / cue.asset_filename
        if not asset_path.exists():
            logger.warning(f"B-roll asset not found: {asset_path}. Skipping.")
            continue

        is_image = asset_path.suffix.lower() in image_extensions
        if is_image:
            # Static image input requires looping to act as a continuous video stream
            cmd.extend(["-loop", "1", "-t", f"{reel_duration:.2f}", "-i", str(asset_path.resolve())])
        else:
            # Video asset input
            cmd.extend(["-i", str(asset_path.resolve())])

        broll_inputs.append((current_input_idx, cue, is_image))
        current_input_idx += 1

    # Generate the complex filtergraph
    filter_graph, final_v_label = build_ffmpeg_filtergraph(
        speaker_input_idx=0,
        broll_inputs=broll_inputs,
        ass_subtitle_path=ass_path,
        cta_banner=cta_banner,
        end_screen=end_screen,
        video_duration=reel_duration,
        config=config
    )

    cmd.extend(["-filter_complex", filter_graph])
    
    # Map final composited video and primary enhanced audio track (input 1)
    cmd.extend([
        "-map", f"[{final_v_label}]",
        "-map", "1:a",
        "-c:v", config.video_codec,
        "-preset", config.preset,
        "-crf", str(config.crf),
        "-pix_fmt", "yuv420p",
        "-c:a", config.audio_codec,
        "-b:a", config.audio_bitrate,
        "-t", f"{reel_duration:.3f}",
        "-movflags", "+faststart",
        str(output_video.resolve())
    ])

    logger.info(f"Executing FFmpeg render pipeline for '{output_video.name}'...")
    logger.debug("FFmpeg Command: " + " ".join(cmd))

    # Run FFmpeg process
    process = subprocess.run(cmd, capture_output=True, text=True)
    if process.returncode != 0:
        logger.error("FFmpeg render failed!")
        logger.error(process.stderr)
        raise RuntimeError(f"FFmpeg render error: {process.stderr[-2000:]}")

    logger.info(f"Render completed successfully! Output: {output_video} ({output_video.stat().st_size / (1024*1024):.2f} MB)")
    
    return {
        "success": True,
        "output_path": str(output_video.resolve()),
        "duration_seconds": reel_duration,
        "file_size_bytes": output_video.stat().st_size,
        "cues_composited": len(broll_inputs),
        "subtitles_rendered": len(sub_items)
    }

# --------------------------------------------------------------------------------------
# 6. FASTAPI ASYNC ENDPOINT INTEGRATION SNIPPET
# --------------------------------------------------------------------------------------

def get_fastapi_router():
    """Returns a plug-and-play FastAPI router for video automation workers."""
    try:
        from fastapi import APIRouter, HTTPException, BackgroundTasks
    except ImportError:
        logger.info("FastAPI not installed; skipping router factory.")
        return None

    router = APIRouter(prefix="/api/reels", tags=["Reels Automation"])

    class ReelRenderRequest(BaseModel):
        speaker_video_path: str
        enhanced_audio_path: str
        broll_dir: str
        timeline_json_path: str
        subtitles_json_path: str
        output_path: str
        cta_config_path: Optional[str] = None

    @router.post("/render")
    async def create_reel_endpoint(req: ReelRenderRequest):
        try:
            result = render_reel(
                speaker_video=Path(req.speaker_video_path),
                enhanced_audio=Path(req.enhanced_audio_path),
                broll_timeline_json=Path(req.timeline_json_path),
                subtitles_json=Path(req.subtitles_json_path),
                broll_assets_dir=Path(req.broll_dir),
                output_video=Path(req.output_path),
                cta_config_json=Path(req.cta_config_path) if req.cta_config_path else None
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

# --------------------------------------------------------------------------------------
# 7. COMMAND LINE INTERFACE (CLI)
# --------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Automate 9:16 Viral Split-Screen Reels with FFmpeg")
    parser.add_argument("--speaker", required=True, type=Path, help="Path to primary speaking video (.mp4/.mov)")
    parser.add_argument("--audio", required=True, type=Path, help="Path to enhanced audio track (.wav/.m4a)")
    parser.add_argument("--broll-dir", required=True, type=Path, help="Directory containing B-roll video and image assets")
    parser.add_argument("--timeline", required=True, type=Path, help="Path to B-roll timeline JSON")
    parser.add_argument("--subtitles", required=True, type=Path, help="Path to subtitle cues JSON")
    parser.add_argument("--output", required=True, type=Path, help="Path for rendered output reel (.mp4)")
    parser.add_argument("--cta", required=False, type=Path, default=None, help="Optional CTA & end-screen config JSON")
    parser.add_argument("--crf", type=int, default=18, help="H.264 CRF quality (default: 18)")
    parser.add_argument("--preset", type=str, default="fast", help="H.264 encoding preset (default: fast)")

    args = parser.parse_args()

    cfg = ReelConfig(crf=args.crf, preset=args.preset)
    
    try:
        res = render_reel(
            speaker_video=args.speaker,
            enhanced_audio=args.audio,
            broll_timeline_json=args.timeline,
            subtitles_json=args.subtitles,
            broll_assets_dir=args.broll_dir,
            output_video=args.output,
            cta_config_json=args.cta,
            config=cfg
        )
        print("\n" + "="*60)
        print("✅ REEL COMPOSITION COMPLETE!")
        print(f"File:     {res['output_path']}")
        print(f"Duration: {res['duration_seconds']:.2f}s")
        print(f"Size:     {res['file_size_bytes'] / (1024*1024):.2f} MB")
        print("="*60)
    except Exception as exc:
        logger.error(f"Execution failed: {exc}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
