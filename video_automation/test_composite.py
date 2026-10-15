import subprocess
from pathlib import Path

FFMPEG_BIN = "/Users/sushil/.gemini/antigravity/scratch/davinci-companion/backend/vendor_runtime/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
ass_path = Path("video_automation/test.ass").resolve()

filter_complex = (
    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:960:(in_w-1080)/2:(in_h-960)/2,setsar=1[spk_bottom];"
    "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960:(in_w-1080)/2:(in_h-960)/2,boxblur=20:5,eq=brightness=-0.2,setsar=1[top_bg];"
    "[top_bg][spk_bottom]vstack=inputs=2[base_canvas];"
    "[base_canvas]drawbox=x=0:y=958:w=1080:h=4:color=white@0.3:t=fill[c0];"
    "[2:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960:(in_w-1080)/2:(in_h-960)/2,setsar=1,fps=30,trim=duration=2.0,setpts=PTS-STARTPTS+1.0/TB[broll0];"
    "[c0][broll0]overlay=0:0:enable='between(t,1.0,3.0)':eof_action=pass[c1];"
    "[3:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960:(in_w-1080)/2:(in_h-960)/2,setsar=1,fps=30,trim=duration=2.0,setpts=PTS-STARTPTS+3.0/TB[broll1];"
    "[c1][broll1]overlay=0:0:enable='between(t,3.0,5.0)':eof_action=pass[c2];"
    f"[c2]ass='{ass_path}'[c3];"
    "[c3]drawbox=x=140:y=1550:w=800:h=120:color=yellow:t=fill:enable='between(t,4.5,5.8)',"
    "drawtext=text='COMMENT \"TEST\" FOR BLUEPRINT':fontcolor=black:fontsize=40:x=(w-text_w)/2:y=1590:enable='between(t,4.5,5.8)'[final_v]"
)

cmd = [
    FFMPEG_BIN, "-y",
    "-i", "video_automation/dummy_speaker.mp4",
    "-i", "video_automation/dummy_enhanced_audio.wav",
    "-i", "video_automation/broll_1.mp4",
    "-loop", "1", "-t", "6", "-i", "video_automation/broll_2.jpg",
    "-filter_complex", filter_complex,
    "-map", "[final_v]",
    "-map", "1:a",
    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    "-t", "6",
    "video_automation/output_reel.mp4"
]

res = subprocess.run(cmd, capture_output=True, text=True)
print("FFmpeg return code:", res.returncode)
if res.returncode != 0:
    print("Stderr:", res.stderr)
else:
    out_file = Path("video_automation/output_reel.mp4")
    print(f"Output reel generated successfully! File: {out_file}, Size: {out_file.stat().st_size} bytes")
