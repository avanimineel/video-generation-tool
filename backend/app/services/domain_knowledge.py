"""Per-field editing memory.

Each keep, cut, or swap is stored under the project's domain. The next video
in that field sees those notes. A section note also becomes a training example
for the same kind of spoken section. A medical cut does not teach a sports video.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.editorial_placement import DOMAIN_CLASSES, family_of

DOMAINS = ("general", "medical", "sports")


def normalize_domain(value: Optional[str]) -> str:
    token = (value or "").strip().lower()
    return token if token in DOMAINS else "general"


def project_domain(project_id: str) -> str:
    path = settings.projects_dir / project_id / "project.json"
    if not path.is_file():
        return "general"
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "general"
    snap = meta.get("snapshot") if isinstance(meta.get("snapshot"), dict) else meta
    project_settings = snap.get("settings") if isinstance(snap, dict) else {}
    if not isinstance(project_settings, dict):
        return "general"
    if project_settings.get("domain_profile"):
        return normalize_domain(str(project_settings.get("domain_profile")))
    if project_settings.get("brand_preset") == "medical_evidence":
        return "medical"
    return "general"


def same_domain(row: Dict[str, Any], domain: str) -> bool:
    return normalize_domain(row.get("domain_profile")) == normalize_domain(domain)


def remember(entry: Dict[str, Any]) -> Dict[str, Any]:
    domain = normalize_domain(entry.get("domain_profile"))
    path = _path(domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = _load(path)
    family = family_of(str(entry.get("graphic_type") or ""))
    decision = str(entry.get("decision") or "keep").lower()
    profile["counts"][decision] = int(profile["counts"].get(decision, 0)) + 1
    families = profile["families"].setdefault(family, {"keep": 0, "cut": 0, "swap": 0, "manual_add": 0})
    if decision in families:
        families[decision] += 1
    note = str(entry.get("editor_notes") or "").strip()
    if note:
        profile["notes"].insert(0, {"project_id": entry.get("project_id"), "decision": decision, "note": note[:240], "at": datetime.utcnow().isoformat()})
        profile["notes"] = profile["notes"][:40]
    transcript = str(entry.get("transcript_context") or "").strip()
    query = str(entry.get("search_query") or "").strip()
    if transcript and (note or query):
        asset = entry.get("selected_asset") if isinstance(entry.get("selected_asset"), dict) else {}
        example = {
            "project_id": entry.get("project_id"),
            "transcript": transcript[:240],
            "note": note[:240],
            "query": query[:160],
            "words": section_words(transcript + " " + note),
            "asset_url": asset.get("url") or asset.get("media_url") or "",
            "asset_title": str(asset.get("title") or "")[:120],
            "at": datetime.utcnow().isoformat(),
        }
        profile.setdefault("examples", [])
        profile["examples"].insert(0, example)
        profile["examples"] = profile["examples"][:80]
        _append_training(domain, example)
    profile["updated_at"] = datetime.utcnow().isoformat()
    _save(path, profile)
    return for_planner(domain)


def for_planner(domain: str) -> Dict[str, Any]:
    domain = normalize_domain(domain)
    profile = _load(_path(domain))
    ranked = sorted(profile["families"].items(), key=lambda item: item[1].get("keep", 0) - item[1].get("cut", 0), reverse=True)
    return {
        "domain": domain,
        "avoid_classes": sorted(DOMAIN_CLASSES[domain]),
        "decision_counts": profile["counts"],
        "family_counts": profile["families"],
        "preferred_families": [name for name, counts in ranked if counts.get("keep", 0) > counts.get("cut", 0)][:4],
        "notes": profile["notes"][:8],
        "examples": profile.get("examples", [])[:12],
        "transcripts": profile.get("transcripts", [])[:12],
    }


def _path(domain: str):
    return settings.projects_dir / "domain_knowledge" / f"{normalize_domain(domain)}.json"


_STOP = {
    "this", "that", "with", "from", "your", "have", "been", "were", "they", "them",
    "their", "about", "after", "before", "there", "here", "into", "over", "under",
    "very", "just", "also", "than", "then", "will", "would", "could", "should",
    "what", "when", "where", "which", "while", "because", "today", "starting",
    "start", "discussion", "discuss", "talking", "video", "people", "something", "really",
}


def section_words(text: str) -> list[str]:
    found: list[str] = []
    for word in re.findall(r"[A-Za-z]{3,}", text or ""):
        token = word.lower()
        if token in _STOP or token in found:
            continue
        found.append(token)
    return found[:8]


def remember_transcript(entry: Dict[str, Any]) -> Dict[str, Any]:
    """A heard line and the editor's correction. Stored for the next similar section."""
    domain = normalize_domain(entry.get("domain_profile") or project_domain(str(entry.get("project_id") or "")))
    heard = str(entry.get("heard") or "").strip()
    correction = str(entry.get("correction") or "").strip()
    note = str(entry.get("note") or "").strip()
    if not heard or not (correction or note):
        raise ValueError("A transcription note needs the heard line and a correction or a note.")
    issue = str(entry.get("issue") or "wrong_words")
    if issue not in {"wrong_words", "unreadable", "bad_timing"}:
        issue = "wrong_words"
    example = {
        "project_id": entry.get("project_id"),
        "heard": heard[:240],
        "correction": correction[:240],
        "issue": issue,
        "note": note[:240],
        "start_sec": entry.get("start_sec"),
        "end_sec": entry.get("end_sec"),
        "words": section_words(heard),
        "at": datetime.utcnow().isoformat(),
    }
    path = _path(domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = _load(path)
    profile.setdefault("transcripts", [])
    profile["transcripts"].insert(0, example)
    profile["transcripts"] = profile["transcripts"][:80]
    profile["updated_at"] = datetime.utcnow().isoformat()
    _save(path, profile)
    _append_transcript(domain, example)
    return example


def match_transcript(domain: str, text: str) -> Optional[Dict[str, Any]]:
    """The saved hearing that matches this line. An exact phrase wins, then two shared words."""
    folded = " ".join((text or "").casefold().split())
    wanted = set(section_words(text))
    best = None
    score = 1
    for example in _load(_path(normalize_domain(domain))).get("transcripts") or []:
        heard = " ".join(str(example.get("heard") or "").casefold().split())
        if heard and folded and (heard == folded or heard in folded or folded in heard):
            return example
        shared = wanted & set(example.get("words") or [])
        if len(shared) > score:
            best = example
            score = len(shared)
    return best


def match_example(domain: str, text: str) -> Optional[Dict[str, Any]]:
    """The saved section whose words overlap this line. Two shared words is the minimum."""
    wanted = set(section_words(text))
    best = None
    score = 1
    for example in _load(_path(normalize_domain(domain))).get("examples") or []:
        shared = wanted & set(example.get("words") or [])
        if len(shared) > score:
            best = example
            score = len(shared)
    return best


def _append_transcript(domain: str, example: Dict[str, Any]) -> None:
    path = settings.projects_dir / "domain_knowledge" / f"{normalize_domain(domain)}_transcription.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"domain": normalize_domain(domain), "kind": "transcription", **example}, ensure_ascii=False) + "\n")


def _append_training(domain: str, example: Dict[str, Any]) -> None:
    path = settings.projects_dir / "domain_knowledge" / f"{normalize_domain(domain)}_training.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"domain": normalize_domain(domain), **example}, ensure_ascii=False) + "\n")


def _empty() -> Dict[str, Any]:
    return {"counts": {}, "families": {}, "notes": [], "examples": [], "transcripts": [], "updated_at": None}


def _load(path) -> Dict[str, Any]:
    if not path.is_file():
        return _empty()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _empty()
    loaded.setdefault("counts", {})
    loaded.setdefault("families", {})
    loaded.setdefault("notes", [])
    loaded.setdefault("examples", [])
    loaded.setdefault("transcripts", [])
    return loaded


def _save(path, profile: Dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    temporary.replace(path)
