#!/usr/bin/env python3
"""
Baseline Video Evaluation Runner
Runs the editorial decision pipeline across baseline videos and ensures decisions are persisted
to evaluation/runs/<run_id>/decisions.json for evaluation and observability.
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add backend to PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.config import settings
from app.services.project_manager import project_manager
from app.services.editorial_planner import run_editorial, PROMPT_VERSION

BASELINE_PROJECT_CANDIDATES = [
    {
        "slot": 1,
        "name": "111sub (Cancer Analysis / Clinical Dialogue)",
        "project_id": "new_1790101050",
        "description": "88s talking head documentary video with clinical numbers and claims."
    },
    {
        "slot": 2,
        "name": "112 (Medical Intern Stipend / Dr. Shubham Garg)",
        "project_id": "new_1790229958",
        "description": "144s Hindi/Hinglish speech on doctor shifts and MP stipend decision."
    },
    {
        "slot": 3,
        "name": "make_the_video (Rapid Medical Discussion)",
        "project_id": "nr_1790068698",
        "description": "10s concise video discussing clinical concepts and diagnostics."
    },
    {
        "slot": 4,
        "name": "Podcast_James_01 (Short Clinical Excerpt)",
        "project_id": "Podcast_James_01_1789413330",
        "description": "7.4s dialogue excerpt with rapid speech and keyword punches."
    },
    {
        "slot": 5,
        "name": "sub (Extended Healthcare Lecture)",
        "project_id": "proj_sub_1789738370603",
        "description": "140s multi-topic clinical podcast commentary."
    }
]

def list_baselines():
    print("\nAvailable Baseline Videos:")
    print("=" * 70)
    for b in BASELINE_PROJECT_CANDIDATES:
        pid = b["project_id"]
        p = project_manager.get_project(pid)
        status = "Ready" if p and p.source_media_path and Path(p.source_media_path).exists() else "Needs Relink/Missing"
        dur = f"{p.duration_seconds:.1f}s" if p and p.duration_seconds else "N/A"
        caps = len(p.captions) if p and p.captions else 0
        print(f"[{b['slot']}] {b['name']}")
        print(f"    Project ID:   {pid}")
        print(f"    Status:       {status} (Duration: {dur}, Captions: {caps})")
        print(f"    Description:  {b['description']}")
        print("-" * 70)

def run_baseline(project_id: str, plan_only: bool = False):
    project = project_manager.get_project(project_id)
    if not project:
        print(f"[Error] Project {project_id} not found in database or projects dir.")
        return None

    media_file = project.source_media_path
    if not media_file or not Path(media_file).exists():
        pdir = settings.projects_dir / project_id
        for cand in ["111sub.mp4", "06fff4a7_112.mov", "14c28d4b_112.mov", "make_the_video.mp4", "sub.mov", "sub.mp4"]:
            if (pdir / cand).exists():
                media_file = str(pdir / cand)
                break

    if not media_file or not Path(media_file).exists():
        print(f"[Error] Source video file not found for project {project_id}.")
        return None

    if not project.captions:
        print(f"[*] Transcribing dialogue with Whisper for project {project_id}...")
        from app.services.transcription_service import transcription_service
        from app.services.translation_service import translation_service
        _, captions = transcription_service.transcribe_with_whisper(media_file, words_per_caption=4, model_size="small")
        project.captions = translation_service.translate_captions_list(captions)
        project_manager.save_project(project)

    print(f"\n[*] Launching baseline run for: {project.name or project_id} ({project_id})")
    print(f"    Media: {Path(media_file).name} ({project.duration_seconds:.1f}s, {len(project.captions)} captions)")
    print(f"    Mode:  {'plan_only (understanding + editorial decisions)' if plan_only else 'full pipeline (decisions + asset retrieval + placement)'}")

    protected = [g for g in project.graphics if not g.parameters.get("editorial_generated")]
    graphics, logs, report = run_editorial(project, media_file, protected=protected, plan_only=plan_only)

    run_id = report.get("run_id")
    eval_file = ROOT_DIR / "evaluation" / "runs" / run_id / "decisions.json"

    print("\n" + "=" * 70)
    print(f"[Baseline Run Complete] Run ID: {run_id}")
    print(f"Status:       {report.get('status')}")
    print(f"Decisions Log: {eval_file}")
    
    if eval_file.exists():
        records = json.loads(eval_file.read_text())
        print(f"Total Decisions Captured: {len(records)}")
        interventions = sum(1 for r in records if r.get("intervene"))
        retained = sum(1 for r in records if not r.get("intervene"))
        print(f"Breakdown:    {interventions} visual interventions | {retained} retained speaker (no_intervention)")
        print("\nDecision Excerpts:")
        for idx, r in enumerate(records[:5]):
            print(f"  [{idx+1}] {r['start_time']}s - {r['end_time']}s | {r['proposed_visual_type']:<20} | Status: {r['status']}")
            print(f"      Transcript: \"{r['source_transcript'][:60]}\"")
            print(f"      Reasoning:  \"{r.get('model_reasoning', '')[:80]}...\"")
    print("=" * 70 + "\n")
    return eval_file

def main():
    parser = argparse.ArgumentParser(description="Run baseline evaluation videos and persist decision logs.")
    parser.add_argument("--list", action="store_true", help="List baseline candidate videos and project IDs.")
    parser.add_argument("--project-id", type=str, help="Run baseline pipeline for a specific project ID.")
    parser.add_argument("--slot", type=int, choices=[1, 2, 3, 4, 5], help="Run a baseline by its slot number (1-5).")
    parser.add_argument("--plan-only", action="store_true", help="Run decisions and schedule only (no stock downloads).")
    parser.add_argument("--all", action="store_true", help="Run all 5 baseline videos sequentially.")

    args = parser.parse_args()

    if args.list:
        list_baselines()
        return

    if args.slot:
        target = BASELINE_PROJECT_CANDIDATES[args.slot - 1]
        run_baseline(target["project_id"], plan_only=args.plan_only)
        return

    if args.project_id:
        run_baseline(args.project_id, plan_only=args.plan_only)
        return

    if args.all:
        for b in BASELINE_PROJECT_CANDIDATES:
            run_baseline(b["project_id"], plan_only=args.plan_only)
        return

    # Default action if no args provided: show help and list
    parser.print_help()
    list_baselines()

if __name__ == "__main__":
    main()
