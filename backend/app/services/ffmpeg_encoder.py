"""Pick an H.264 encoder: NVENC on EC2/T4, VideoToolbox on macOS, else libx264."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from app.core.logging_setup import get_logger

logger = get_logger(__name__)

# Preference order for FFMPEG_VIDEO_ENCODER=auto
_AUTO_CANDIDATES = ("h264_nvenc", "h264_videotoolbox", "libx264")


def _probe_encoder(
    ffmpeg_bin: str,
    codec: str,
    *,
    width: int = 64,
    height: int = 64,
    runner: Optional[Callable[..., Any]] = None,
) -> bool:
    run = runner or subprocess.run
    try:
        result = run(
            [
                ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=black:s={width}x{height}:r=30",
                "-frames:v",
                "1",
                "-c:v",
                codec,
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            timeout=20,
        )
        return getattr(result, "returncode", 1) == 0
    except Exception:
        return False


def encoder_args(
    codec: str,
    *,
    bitrate: str = "4000k",
    crf: Optional[str] = None,
) -> List[str]:
    """Return ffmpeg argv fragments for the chosen video codec."""
    if codec == "h264_nvenc":
        # p4 is a good T4 default: faster than p5/p6, still visually solid for burn-in.
        args = ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", bitrate]
        if crf is not None:
            args.extend(["-cq", crf])
        return args
    if codec == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-b:v", bitrate]
    # Software fallback
    args = ["-c:v", "libx264", "-preset", "veryfast", "-threads", "4"]
    if crf is not None:
        args.extend(["-crf", crf])
    else:
        args.extend(["-b:v", bitrate])
    return args


def resolve_video_encoder(
    ffmpeg_bin: str,
    preference: Optional[str] = None,
    *,
    bitrate: str = "4000k",
    crf: Optional[str] = None,
    probe_size: Tuple[int, int] = (64, 64),
    runner: Optional[Callable[..., Any]] = None,
    probe: Optional[Callable[[str, str], bool]] = None,
) -> Tuple[str, List[str], Optional[str]]:
    """Select video encoder and return ``(codec, argv_fragment, fallback_reason)``.

    Env:
      FFMPEG_VIDEO_ENCODER=auto|h264_nvenc|h264_videotoolbox|libx264
    """
    requested = (preference or os.getenv("FFMPEG_VIDEO_ENCODER") or "auto").strip().lower()
    if requested not in ("auto", "h264_nvenc", "h264_videotoolbox", "libx264"):
        requested = "auto"

    width, height = probe_size

    def available(codec: str) -> bool:
        if probe is not None:
            return bool(probe(ffmpeg_bin, codec))
        return _probe_encoder(ffmpeg_bin, codec, width=width, height=height, runner=runner)

    reason: Optional[str] = None
    if requested == "auto":
        chosen = None
        for candidate in _AUTO_CANDIDATES:
            if available(candidate):
                chosen = candidate
                break
        if chosen is None:
            chosen = "libx264"
            reason = "no_hw_encoder_probed"
    elif requested == "libx264":
        chosen = "libx264"
    else:
        if available(requested):
            chosen = requested
        else:
            # Fall through auto order excluding the failed request, always ending at libx264.
            chosen = None
            for candidate in _AUTO_CANDIDATES:
                if candidate == requested:
                    continue
                if candidate == "libx264" or available(candidate):
                    chosen = candidate
                    break
            chosen = chosen or "libx264"
            reason = f"{requested}_unavailable"

    args = encoder_args(chosen, bitrate=bitrate, crf=crf if chosen == "libx264" or crf is not None else None)
    # For libx264 prefer CRF when caller did not force bitrate-only software path.
    if chosen == "libx264" and crf is None and bitrate:
        # Keep bitrate mode when explicitly used by burn-in; quality_preview passes crf.
        pass

    logger.info(
        "ffmpeg_encoder_selected",
        event="ffmpeg_encoder_selected",
        codec=chosen,
        fallback_reason=reason,
        ffmpeg_video_encoder_env=requested,
        ffmpeg_bin=ffmpeg_bin,
    )
    return chosen, args, reason


def replace_video_codec_args(argv: Sequence[str], new_codec_args: Sequence[str]) -> List[str]:
    """Replace an existing ``-c:v <name>`` (+ optional trailing encode knobs) with new args.

    Conservative: swaps only the ``-c:v`` value and strips known companion flags that
    belonged to the previous codec so callers can rebuild from ``encoder_args``.
    Prefer building argv with ``resolve_video_encoder`` instead of mutate-in-place.
    """
    out = list(argv)
    if "-c:v" not in out:
        # Insert before output path (last element) when possible.
        insert_at = max(0, len(out) - 1)
        return out[:insert_at] + list(new_codec_args) + out[insert_at:]

    idx = out.index("-c:v")
    # Drop -c:v and the following codec name.
    del out[idx : idx + 2]
    # Strip common leftover encode knobs that may conflict.
    strip_flags = {
        "-preset",
        "-b:v",
        "-crf",
        "-cq",
        "-threads",
        "-rc",
        "-profile:v",
    }
    i = 0
    cleaned: List[str] = []
    while i < len(out):
        tok = out[i]
        if tok in strip_flags and i + 1 < len(out) and not out[i + 1].startswith("-"):
            i += 2
            continue
        cleaned.append(tok)
        i += 1
    insert_at = cleaned.index("-c:v") if "-c:v" in cleaned else (
        cleaned.index("-pix_fmt") if "-pix_fmt" in cleaned else max(0, len(cleaned) - 1)
    )
    if "-c:v" in cleaned:
        # Should not happen after delete; keep safe.
        return cleaned
    return cleaned[:insert_at] + list(new_codec_args) + cleaned[insert_at:]


def describe_selection(codec: str, reason: Optional[str] = None) -> Dict[str, Any]:
    return {
        "codec": codec,
        "fallback_reason": reason,
        "ffmpeg_video_encoder_env": (os.getenv("FFMPEG_VIDEO_ENCODER") or "auto").strip().lower() or "auto",
    }
