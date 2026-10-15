from faster_whisper import WhisperModel
import json

audio_path = "backend/projects/proj_sub_black_1789484112699/sub black.mp4"
model = WhisperModel("small", device="cpu", compute_type="int8")

print("Transcribing Hindi from 21.0s to 32.0s...")
segments, info = model.transcribe(audio_path, language="hi", task="transcribe", word_timestamps=True)

for seg in segments:
    if 20.0 <= seg.start <= 33.0 or 20.0 <= seg.end <= 33.0:
        print(f"[{seg.start:.2f} - {seg.end:.2f}] {seg.text}")
        for w in seg.words:
            print(f"    {w.start:.2f} - {w.end:.2f}: {w.word}")
