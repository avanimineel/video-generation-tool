import subprocess
from pathlib import Path

FFMPEG_BIN = "/Users/sushil/.gemini/antigravity/scratch/davinci-companion/backend/vendor_runtime/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"

# 1. Generate synthetic speaker video (5s, green background with a moving circle)
subprocess.run([
    FFMPEG_BIN, "-y",
    "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30:duration=6",
    "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
    "video_automation/dummy_speaker.mp4"
], capture_output=True)

# 2. Generate enhanced audio track (6s of 880Hz tone)
subprocess.run([
    FFMPEG_BIN, "-y",
    "-f", "lavfi", "-i", "sine=frequency=880:duration=6",
    "-c:a", "pcm_s16le",
    "video_automation/dummy_enhanced_audio.wav"
], capture_output=True)

# 3. Generate B-roll 1 (video, 2s red)
subprocess.run([
    FFMPEG_BIN, "-y",
    "-f", "lavfi", "-i", "color=c=red:s=1280x720:d=3:r=30",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "video_automation/broll_1.mp4"
], capture_output=True)

# 4. Generate B-roll 2 (image, blue 1920x1080)
subprocess.run([
    FFMPEG_BIN, "-y",
    "-f", "lavfi", "-i", "color=c=blue:s=1920x1080:d=1:r=30",
    "-vframes", "1",
    "video_automation/broll_2.jpg"
], capture_output=True)

print("Created synthetic test assets.")
