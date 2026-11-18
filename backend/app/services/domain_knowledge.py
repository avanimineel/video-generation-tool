"""Per-field editing memory.

Each keep, cut, or swap is stored under the project's domain. The next video
in that field sees those notes. A medical cut does not teach a sports video,
and this file is not a fine-tune.
"""

from __future__ import annotations

import json
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
    }


def _path(domain: str):
    return settings.projects_dir / "domain_knowledge" / f"{normalize_domain(domain)}.json"


def _empty() -> Dict[str, Any]:
    return {"counts": {}, "families": {}, "notes": [], "updated_at": None}


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
    return loaded


def _save(path, profile: Dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    temporary.replace(path)
