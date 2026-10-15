"""
Editor Feedback & Training Data Service
Tracks every human editorial override (Keep, Cut, Swap/Modify) on Pegasus/AI suggestions.
Maintains structured training logs, statistics, and generates few-shot prompt exports.
"""

import json
import uuid
import fcntl
from functools import wraps
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.core.config import settings

def serialized_feedback_write(fn):
    """Keep simultaneous feedback submissions from overwriting each other."""
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        lock_path = self.global_feedback_file.with_suffix('.lock')
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                return fn(self, *args, **kwargs)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
    return wrapped


class FeedbackService:
    def __init__(self):
        self.global_feedback_file = settings.projects_dir / "editorial_feedback.json"
        self._ensure_feedback_file()

    def _ensure_feedback_file(self):
        if not self.global_feedback_file.exists():
            try:
                with open(self.global_feedback_file, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
            except Exception as e:
                print(f"[FeedbackService] Warning: Could not init feedback file: {e}")

    def _load_all(self) -> List[Dict[str, Any]]:
        if self.global_feedback_file.exists():
            try:
                return json.loads(self.global_feedback_file.read_text(encoding="utf-8"))
            except (ValueError, OSError) as exc:
                raise RuntimeError("Saved editorial feedback could not be read; refusing to edit without your corrections.") from exc
        return []

    def _save_all(self, decisions: List[Dict[str, Any]]):
        self.global_feedback_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.global_feedback_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(decisions, indent=2), encoding='utf-8')
        tmp.replace(self.global_feedback_file)

    def get_guidance(self, project_id: str = "global") -> str:
        paths = [("All projects", settings.projects_dir / "editorial_guidance.json")]
        if project_id and project_id != "global":
            paths.append(("This project", settings.projects_dir / project_id / "editorial_guidance.json"))
        parts = []
        for label, path in paths:
            if path.exists():
                text = json.loads(path.read_text(encoding="utf-8")).get("guidance", "").strip()
                if text:
                    parts.append(f"{label}: {text}")
        return "\n\n".join(parts)

    def save_guidance(self, project_id: str, guidance: str) -> Dict[str, Any]:
        p_dir = settings.projects_dir / project_id if project_id and project_id != "global" else settings.projects_dir
        p_dir.mkdir(parents=True, exist_ok=True)
        target = p_dir / "editorial_guidance.json"
        content = {"project_id": project_id, "guidance": guidance.strip(), "updated_at": datetime.utcnow().isoformat()}
        target.write_text(json.dumps(content, indent=2), encoding="utf-8")
        return content

    def planning_feedback(self, project_id):
        rows = self.query_decisions(project_id=project_id, limit=500)['decisions']
        rows.sort(key=lambda r:r.get('updated_at',''), reverse=True)
        decisions_summary = [{k:r.get(k) for k in ('id','cue_id','decision','start_sec','end_sec','transcript_context','graphic_type','selected_asset','editor_notes','reasoning','swap_details')} for r in rows[:100]]
        # Other projects teach editing preferences, not facts about this speaker.
        others = [r for r in self._load_all() if r.get('project_id') != project_id and r.get('editor_notes')]
        others.sort(key=lambda r:r.get('updated_at',''), reverse=True)
        examples = [{k:r.get(k) for k in ('project_id','decision','transcript_context','editor_notes','graphic_type')} for r in others[:30]]
        guidance = self.get_guidance(project_id)
        return {
            'decisions': decisions_summary,
            'guidance': guidance,
            'cross_project_examples': examples
        }

    @serialized_feedback_write
    def record_decision(
        self,
        project_id: str,
        cue_id: str,
        decision: str,  # 'keep' | 'cut' | 'swap'
        reasoning: str,
        strength: float,
        graphic_type: str,
        start_sec: float,
        end_sec: float,
        search_query: str,
        transcript_context: str = "",
        selected_asset: Optional[Dict[str, Any]] = None,
        swap_details: Optional[Dict[str, Any]] = None,
        final_decision: Optional[Dict[str, Any]] = None,
        editor_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Records or updates an editor's Keep, Cut, or Swap judgment.
        """
        all_decisions = self._load_all()

        # Check if this cue_id for this project already has a logged decision
        existing_idx = -1
        for idx, d in enumerate(all_decisions):
            if d.get("project_id") == project_id and d.get("cue_id") == cue_id:
                existing_idx = idx
                break

        now_iso = datetime.utcnow().isoformat()
        decision_id = all_decisions[existing_idx]["id"] if existing_idx >= 0 else f"dec_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}"

        entry = {
            "id": decision_id,
            "project_id": project_id,
            "cue_id": cue_id,
            "decision": decision.lower().strip(),  # 'keep' | 'cut' | 'swap'
            "transcript_context": transcript_context,
            "reasoning": reasoning,
            "strength": round(float(strength), 2),
            "graphic_type": graphic_type,
            "start_sec": round(float(start_sec), 2),
            "end_sec": round(float(end_sec), 2),
            "search_query": search_query,
            "selected_asset": selected_asset or {},
            "swap_details": swap_details or {},
            "final_decision": final_decision or {},
            "editor_notes": editor_notes,
            "created_at": all_decisions[existing_idx]["created_at"] if existing_idx >= 0 else now_iso,
            "updated_at": now_iso
        }

        if existing_idx >= 0:
            all_decisions[existing_idx] = entry
        else:
            all_decisions.insert(0, entry)

        self._save_all(all_decisions)

        # Also write to project-level directory
        try:
            p_file = settings.projects_dir / project_id / "editorial_feedback.json"
            p_file.parent.mkdir(parents=True, exist_ok=True)
            p_decisions = [d for d in all_decisions if d.get("project_id") == project_id]
            p_file.write_text(json.dumps(p_decisions, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[FeedbackService] Warning saving project feedback: {e}")

        return entry

    def query_decisions(
        self,
        decision_filter: Optional[str] = None,
        graphic_type: Optional[str] = None,
        min_strength: Optional[float] = None,
        max_strength: Optional[float] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        all_decisions = self._load_all()

        filtered = []
        for d in all_decisions:
            if decision_filter and decision_filter.lower() != "all" and d.get("decision") != decision_filter.lower():
                continue
            if graphic_type and graphic_type.lower() != "all" and d.get("graphic_type") != graphic_type:
                continue
            if project_id and project_id.lower() != "all" and d.get("project_id") != project_id:
                continue
            if min_strength is not None and float(d.get("strength", 0.0)) < min_strength:
                continue
            if max_strength is not None and float(d.get("strength", 1.0)) > max_strength:
                continue
            filtered.append(d)

        total_matching = len(filtered)
        paged = filtered[offset : offset + limit]

        return {
            "total": total_matching,
            "offset": offset,
            "limit": limit,
            "decisions": paged
        }

    def get_statistics(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates aggregated totals and breakdown ratios:
        e.g. '124 decisions -> 71 kept | 31 cut | 22 modified'
        """
        all_decisions = self._load_all()
        if project_id and project_id != "all":
            all_decisions = [d for d in all_decisions if d.get("project_id") == project_id]

        total = len(all_decisions)
        kept = sum(1 for d in all_decisions if d.get("decision") == "keep")
        cut = sum(1 for d in all_decisions if d.get("decision") == "cut")
        swapped = sum(1 for d in all_decisions if d.get("decision") == "swap")

        by_graphic_type: Dict[str, Dict[str, int]] = {}
        for d in all_decisions:
            gt = d.get("graphic_type", "unknown")
            if gt not in by_graphic_type:
                by_graphic_type[gt] = {"total": 0, "keep": 0, "cut": 0, "swap": 0}
            by_graphic_type[gt]["total"] += 1
            dec = d.get("decision", "keep")
            if dec in by_graphic_type[gt]:
                by_graphic_type[gt][dec] += 1

        avg_strength = round(sum(float(d.get("strength", 0.0)) for d in all_decisions) / max(1, total), 2)

        return {
            "total_decisions": total,
            "kept": kept,
            "cut": cut,
            "swapped": swapped,
            "keep_rate_pct": round((kept / max(1, total)) * 100.0, 1),
            "cut_rate_pct": round((cut / max(1, total)) * 100.0, 1),
            "swap_rate_pct": round((swapped / max(1, total)) * 100.0, 1),
            "avg_strength": avg_strength,
            "summary_text": f"{total} decisions → {kept} kept | {cut} cut | {swapped} modified",
            "by_graphic_type": by_graphic_type
        }

    def generate_few_shot_export(self, decision_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Converts selected feedback examples into the clean few-shot prompt format:
        Positive example: Context -> reasoning -> decision -> KEEP
        Negative example: Context -> reasoning -> decision -> CUT -> why/what should have happened
        Modified example: Context -> original decision -> editor's final decision
        """
        all_decisions = self._load_all()
        selected = all_decisions
        if decision_ids:
            sel_set = set(decision_ids)
            selected = [d for d in all_decisions if d.get("id") in sel_set]

        positive_examples = []
        negative_examples = []
        modified_examples = []

        for d in selected:
            context = d.get("transcript_context") or f"Timestamp: {d.get('start_sec')}s - {d.get('end_sec')}s"
            reasoning = d.get("reasoning", "No reasoning specified")
            g_type = d.get("graphic_type", "split_screen_vertical")
            query = d.get("search_query", "")
            notes = d.get("editor_notes", "")

            if d.get("decision") == "keep":
                positive_examples.append(
                    f"### POSITIVE EXAMPLE (KEEP)\n"
                    f"- Context: \"{context}\"\n"
                    f"- Reasoning: {reasoning}\n"
                    f"- Decision: [{g_type}] Query: \"{query}\" (Strength: {d.get('strength')})\n"
                    f"- Verdict: KEEP — Accurate visual enhancement."
                )
            elif d.get("decision") == "cut":
                why = notes or "Unnecessary distraction; visual broke talking head connection."
                negative_examples.append(
                    f"### NEGATIVE EXAMPLE (CUT)\n"
                    f"- Context: \"{context}\"\n"
                    f"- Reasoning: {reasoning}\n"
                    f"- Proposed Decision: [{g_type}] Query: \"{query}\" (Strength: {d.get('strength')})\n"
                    f"- Verdict: CUT\n"
                    f"- Why/Correction: {why}"
                )
            elif d.get("decision") == "swap":
                swap_info = d.get("swap_details", {})
                final_info = d.get("final_decision", {})
                orig_desc = f"[{g_type}] '{query}'"
                final_desc = f"[{final_info.get('graphic_type', g_type)}] '{final_info.get('search_query', query)}'"
                modified_examples.append(
                    f"### MODIFIED EXAMPLE (SWAP)\n"
                    f"- Context: \"{context}\"\n"
                    f"- Original Suggestion: {orig_desc} (Strength: {d.get('strength')})\n"
                    f"- Editor Final Choice: {final_desc}\n"
                    f"- Adjustment Rationale: {notes or swap_info.get('reason', 'Swapped for superior visual clarity.')}"
                )

        full_markdown = (
            "# FEW-SHOT PROMPT TRAINING EXAMPLES (Manual Curation View)\n"
            "DO NOT inject automatically into production. Review and select high-value examples manually.\n\n"
            "## 1. Positive Examples (High-Authority Placements)\n"
            + ("\n\n".join(positive_examples) if positive_examples else "_No positive examples logged yet._")
            + "\n\n## 2. Negative Examples (False Positives to Avoid)\n"
            + ("\n\n".join(negative_examples) if negative_examples else "_No negative examples logged yet._")
            + "\n\n## 3. Modified / Swapped Examples (Execution Adjustments)\n"
            + ("\n\n".join(modified_examples) if modified_examples else "_No modified examples logged yet._")
        )

        return {
            "total_exported": len(selected),
            "positive_count": len(positive_examples),
            "negative_count": len(negative_examples),
            "modified_count": len(modified_examples),
            "markdown": full_markdown
        }

feedback_service = FeedbackService()
