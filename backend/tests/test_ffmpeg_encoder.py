"""Unit tests for NVENC / VideoToolbox / libx264 encoder selection."""
import pytest

from app.services.ffmpeg_encoder import (
    encoder_args,
    replace_video_codec_args,
    resolve_video_encoder,
)


def test_encoder_args_nvenc_and_libx264():
    assert encoder_args("h264_nvenc", bitrate="4M")[:4] == ["-c:v", "h264_nvenc", "-preset", "p4"]
    soft = encoder_args("libx264", crf="19")
    assert soft[:2] == ["-c:v", "libx264"]
    assert "-crf" in soft and "19" in soft
    vt = encoder_args("h264_videotoolbox", bitrate="10M")
    assert vt == ["-c:v", "h264_videotoolbox", "-b:v", "10M"]


def test_auto_prefers_nvenc_when_available(monkeypatch):
    monkeypatch.setenv("FFMPEG_VIDEO_ENCODER", "auto")

    def probe(_bin, codec):
        return codec == "h264_nvenc"

    codec, args, reason = resolve_video_encoder("/usr/bin/ffmpeg", probe=probe)
    assert codec == "h264_nvenc"
    assert args[1] == "h264_nvenc"
    assert reason is None


def test_auto_falls_back_to_videotoolbox(monkeypatch):
    monkeypatch.setenv("FFMPEG_VIDEO_ENCODER", "auto")

    def probe(_bin, codec):
        return codec == "h264_videotoolbox"

    codec, args, reason = resolve_video_encoder("/usr/bin/ffmpeg", probe=probe)
    assert codec == "h264_videotoolbox"
    assert reason is None


def test_auto_falls_back_to_libx264(monkeypatch):
    monkeypatch.setenv("FFMPEG_VIDEO_ENCODER", "auto")

    def probe(_bin, codec):
        return False

    codec, args, reason = resolve_video_encoder("/usr/bin/ffmpeg", probe=probe, crf="23")
    assert codec == "libx264"
    assert reason == "no_hw_encoder_probed"
    assert "-crf" in args


def test_forced_nvenc_falls_back_when_missing(monkeypatch):
    monkeypatch.setenv("FFMPEG_VIDEO_ENCODER", "h264_nvenc")

    def probe(_bin, codec):
        return codec == "libx264"  # only software "available" via explicit check path

    # libx264 is never probed in forced path; availability short-circuits on name.
    codec, args, reason = resolve_video_encoder("/ff", preference="h264_nvenc", probe=probe)
    assert codec == "libx264"
    assert reason == "h264_nvenc_unavailable"


def test_forced_libx264_skips_probe(monkeypatch):
    monkeypatch.delenv("FFMPEG_VIDEO_ENCODER", raising=False)
    calls = []

    def probe(_bin, codec):
        calls.append(codec)
        return True

    codec, args, reason = resolve_video_encoder("/ff", preference="libx264", probe=probe)
    assert codec == "libx264"
    assert reason is None
    assert calls == []


def test_replace_video_codec_args_swaps_codec():
    argv = ["-map", "0:v", "-c:v", "h264_videotoolbox", "-b:v", "4000k", "-pix_fmt", "yuv420p", "out.mp4"]
    out = replace_video_codec_args(argv, ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "4000k"])
    assert "h264_videotoolbox" not in out
    assert out[out.index("-c:v") + 1] == "h264_nvenc"
    assert out[-1] == "out.mp4"
