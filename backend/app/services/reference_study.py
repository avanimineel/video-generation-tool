"""Reference study pipeline.

A daily pass measures clips the editor has placed in the reference inbox and
appends those measurements for a later trainer. It does not download films,
follow a channel, or write model weights.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.services.overlay_styles import LOOKS

FPS = 30
HIT_FRAMES = (12, 24)
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}

# The study assignment. Names only. The cron never fetches these sources.
STUDY_SOURCES = (
    {"id": "ben_marriott", "name": "Ben Marriott", "look": "paper_craft", "lesson": "Paper texture, torn edges, and a held pose."},
    {"id": "motion_design_school", "name": "Motion Design School", "look": "kinetic", "lesson": "A rig and an expression, reused instead of redrawn."},
    {"id": "jake_bartlett", "name": "Jake Bartlett", "look": "kinetic", "lesson": "One overshoot curve on the active word."},
    {"id": "vox", "name": "Vox", "look": "infographic", "lesson": "A claim, then a number, then a map."},
    {"id": "johnny_harris", "name": "Johnny Harris", "look": "infographic", "lesson": "A map that moves only when the sentence names a place."},
    {"id": "kurzgesagt", "name": "Kurzgesagt", "look": "flat_vector", "lesson": "One metaphor on screen at a time."},
    {"id": "eye_on_design", "name": "Eye on Design", "look": "collage", "lesson": "A few scraps and a type-led title."},
    {"id": "its_nice_that", "name": "It's Nice That", "look": "collage", "lesson": "Collage, scrapbook, and a title set in type."},
    {"id": "aescripts", "name": "Aescripts", "look": "kinetic", "lesson": "Repeated keyframes become one curve. The plugin stays outside this pipeline."},
)

_PTS = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")
_LOOK_IDS = {str(item["id"]) for item in LOOKS}
_SOURCE_IDS = {item["id"] for item in STUDY_SOURCES}


def inbox_dir() -> Path:
    path = settings.projects_dir / "reference_inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ledger_path() -> Path:
    return settings.projects_dir / "reference_audits.jsonl"


def study_catalog() -> list:
    return [dict(item) for item in STUDY_SOURCES]


def scene_times(showinfo: str) -> list:
    found = []
    for line in (showinfo or "").splitlines():
        if "showinfo" not in line and "pts_time" not in line:
            continue
        match = _PTS.search(line)
        if match:
            found.append(float(match.group(1)))
    return sorted(set(found))


def shots_from_cuts(cuts, duration: float) -> list:
    duration = max(0.0, float(duration or 0))
    marks = [0.0]
    for cut in cuts or []:
        cut = float(cut)
        if 0.05 < cut < duration - 0.05:
            marks.append(cut)
    marks.append(duration)
    shots = []
    for start, end in zip(marks, marks[1:]):
        if end - start >= 0.05:
            shots.append({"start": round(start, 3), "end": round(end, 3), "kind": "shot"})
    return shots


def _peak_layers(events) -> int:
    points = []
    for event in events:
        points.append((float(event["start"]), 1))
        points.append((float(event["end"]), -1))
    points.sort(key=lambda item: (item[0], item[1]))
    current = peak = 0
    for _time, delta in points:
        current += delta
        peak = max(peak, current)
    return peak


def measure_timeline(events, duration: float = 0) -> dict:
    events = [dict(event) for event in events or []]
    shots = [event for event in events if event.get("kind") == "shot"]
    lengths = [float(event["end"]) - float(event["start"]) for event in shots]
    punches = sorted(float(event["start"]) for event in events if event.get("kind") == "punch")
    intervals = [round(punches[index] - punches[index - 1], 3) for index in range(1, len(punches))]
    hit_frames = [
        int(round((float(event["end"]) - float(event["start"])) * FPS))
        for event in events
        if event.get("kind") == "hit"
    ]
    return {
        "duration": round(float(duration or (shots[-1]["end"] if shots else 0)), 3),
        "asl": round(sum(lengths) / len(lengths), 3) if lengths else None,
        "shot_count": len(shots),
        "zoom_intervals": intervals,
        "layer_count": _peak_layers(events) if events else 0,
        "hit_frames": hit_frames,
        "hits_in_band": all(HIT_FRAMES[0] <= frames <= HIT_FRAMES[1] for frames in hit_frames),
    }


def _clean_events(raw) -> list:
    cleaned = []
    for event in raw or []:
        if not isinstance(event, dict):
            continue
        kind = str(event.get("kind") or "shot")
        if kind not in ("shot", "punch", "hit", "layer"):
            continue
        try:
            start = float(event.get("start"))
            end = float(event.get("end"))
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        cleaned.append({"start": round(start, 3), "end": round(end, 3), "kind": kind})
    return cleaned


def _spoken(raw) -> list:
    lines = []
    for row in raw or []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        try:
            start = float(row.get("start") or 0)
            end = float(row.get("end") or start)
        except (TypeError, ValueError):
            continue
        lines.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return lines


def load_sidecar(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def audit_clip(video: Path | None, sidecar: dict, showinfo: str = "", duration: float | None = None) -> dict:
    look = str(sidecar.get("look") or "")
    if look not in _LOOK_IDS:
        raise ValueError(f"A reference needs a look. Got {look or 'none'}.")
    source = str(sidecar.get("source") or "inbox")
    if source not in _SOURCE_IDS:
        source = "inbox"
    events = _clean_events(sidecar.get("events"))
    if not events and showinfo:
        events = shots_from_cuts(scene_times(showinfo), float(duration or sidecar.get("duration") or 0))
    if not events:
        raise ValueError("This reference has no shots to measure.")
    span = float(duration if duration is not None else sidecar.get("duration") or 0)
    if span <= 0:
        span = max(float(event["end"]) for event in events)
    measured = measure_timeline(events, span)
    return {
        "source": source,
        "look": look,
        "file": video.name if video else str(sidecar.get("file") or ""),
        "spoken": _spoken(sidecar.get("spoken")),
        "events": events,
        **measured,
    }


def _file_id(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _seen_ids() -> set:
    path = ledger_path()
    if not path.is_file():
        return set()
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("id"):
            found.add(row["id"])
    return found


def _append(row: dict) -> None:
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _probe(video: Path, runner) -> tuple:
    """Return (showinfo text, duration). `runner` is a test double or ffmpeg."""
    return runner(video)


_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def ffmpeg_probe(video: Path) -> tuple:
    import subprocess

    binary = settings.ffmpeg_bin
    info = subprocess.run(
        [binary, "-i", str(video)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    duration = 0.0
    match = _DURATION.search(info.stderr or "")
    if match:
        hours, minutes, seconds = match.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    shown = subprocess.run(
        [binary, "-i", str(video), "-filter:v", "select='gt(scene,0.35)',showinfo", "-f", "null", "-"],
        capture_output=True, text=True, timeout=180, check=False,
    )
    return (shown.stderr or "") + (shown.stdout or ""), duration


def training_examples(look: str = "", limit: int = 8) -> list:
    path = ledger_path()
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if look and row.get("look") != look:
            continue
        if not row.get("shot_count"):
            continue
        rows.append({
            "look": row.get("look"),
            "source": row.get("source"),
            "asl": row.get("asl"),
            "zoom_intervals": row.get("zoom_intervals") or [],
            "layer_count": row.get("layer_count"),
            "hit_frames": row.get("hit_frames") or [],
            "hits_in_band": row.get("hits_in_band"),
        })
    return rows[-limit:]


def run_inbox(runner=None) -> dict:
    """Measure new inbox clips. Leave the produce pass untouched."""
    inbox = inbox_dir()
    done = inbox / "done"
    done.mkdir(parents=True, exist_ok=True)
    seen = _seen_ids()
    report = {"catalog": [item["id"] for item in STUDY_SOURCES], "kept": [], "skipped": [], "fetched": []}
    files = [path for path in inbox.iterdir() if path.is_file()]
    videos = sorted(path for path in files if path.suffix.lower() in VIDEO_SUFFIXES)
    video_stems = {path.stem for path in videos}
    notes = sorted(
        path for path in files
        if path.suffix == ".json" and path.stem not in video_stems
    )
    for path in videos + notes:
        video = path if path.suffix.lower() in VIDEO_SUFFIXES else None
        sidecar_path = path.with_suffix(".json") if video is not None else path
        sidecar = load_sidecar(sidecar_path)
        identity_path = video or path
        try:
            file_id = _file_id(identity_path)
        except OSError as exc:
            report["skipped"].append({"file": path.name, "reason": str(exc)})
            continue
        if file_id in seen:
            report["skipped"].append({"file": path.name, "reason": "already measured"})
            continue
        showinfo = ""
        duration = None
        if video is not None and not _clean_events(sidecar.get("events")):
            try:
                showinfo, duration = _probe(video, runner or ffmpeg_probe)
            except (OSError, ValueError) as exc:
                report["skipped"].append({"file": path.name, "reason": str(exc)})
                continue
        try:
            measured = audit_clip(video, sidecar, showinfo, duration)
        except ValueError as exc:
            report["skipped"].append({"file": path.name, "reason": str(exc)})
            continue
        row = {
            "id": file_id,
            "measured_at": datetime.now(timezone.utc).isoformat(),
            **measured,
        }
        _append(row)
        seen.add(file_id)
        report["kept"].append({"file": path.name, "look": measured["look"], "asl": measured["asl"]})
        target = done / path.name
        if target.exists():
            target = done / f"{path.stem}-{file_id[:8]}{path.suffix}"
        shutil.move(str(path), str(target))
        if video is not None and sidecar_path.is_file() and sidecar_path.resolve() != path.resolve():
            side_target = done / sidecar_path.name
            if side_target.exists():
                side_target = done / f"{sidecar_path.stem}-{file_id[:8]}{sidecar_path.suffix}"
            shutil.move(str(sidecar_path), str(side_target))
    return report


def main() -> None:
    print(json.dumps(run_inbox(), ensure_ascii=False))


if __name__ == "__main__":
    main()
