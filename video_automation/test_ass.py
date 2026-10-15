import subprocess
from pathlib import Path

FFMPEG_BIN = "/Users/sushil/.gemini/antigravity/scratch/davinci-companion/backend/vendor_runtime/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"

ass_content = """[Script Info]
Title: Test Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\c&H00FFFF&}STOP{\\c&HFFFFFF&} SCROLLING RIGHT NOW
Dialogue: 0,0:00:02.00,0:00:04.00,Default,,0,0,0,,WATCH THIS {\\c&H00FFFF&}SECRET{\\c&HFFFFFF&} EDIT
"""

ass_file = Path("video_automation/test.ass")
ass_file.write_text(ass_content)

# Test rendering 1 frame using ffmpeg with ass filter
cmd = [
    FFMPEG_BIN, "-y",
    "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
    "-vf", f"ass='{ass_file.resolve()}'",
    "-vframes", "1",
    "video_automation/test_frame.png"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("FFmpeg return code:", res.returncode)
if res.returncode != 0:
    print("Stderr:", res.stderr)
else:
    print("Frame created successfully! Size:", Path("video_automation/test_frame.png").stat().st_size)
