"""Separate training step for accepted caption pairs.

The caption pass does not call this. A new video uses a promoted model only
after a held-out set of accepted lines does not get worse. Medical rules still
run after the model answers.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Sequence

from app.core.config import settings
from app.services.accepted_pairs import pairs_path


@dataclass(frozen=True)
class TrainingPair:
    source_text: str
    english: str
    domain: str = "general"


@dataclass(frozen=True)
class HoldoutSplit:
    train: tuple
    holdout: tuple


@dataclass(frozen=True)
class HoldoutScore:
    lines: int
    errors: int


@dataclass(frozen=True)
class TrainingReport:
    promoted: bool
    reason: str
    accepted_pairs: int
    train_count: int
    holdout_count: int
    baseline_errors: int
    candidate_errors: int
    promoted_pairs: int


class LineModel(Protocol):
    """One spoken line in, English out. None means the medical rules decide."""

    def translate(self, source: str, domain: str = "general") -> Optional[str]:
        ...


class Trainer(Protocol):
    def fit(self, train: Sequence[TrainingPair]) -> LineModel:
        ...


class NullModel:
    """The current medical rules, with no learned lines."""

    def translate(self, source: str, domain: str = "general") -> Optional[str]:
        return None


class ExemplarModel:
    """Exact spoken line to the accepted English. It does not guess a new sentence."""

    def __init__(self, learned: dict):
        self.learned = learned

    def translate(self, source: str, domain: str = "general") -> Optional[str]:
        return self.learned.get(_key(source))


class ExemplarTrainer:
    def fit(self, train: Sequence[TrainingPair]) -> ExemplarModel:
        return ExemplarModel({_key(pair.source_text): pair.english for pair in train})


def _key(text: str) -> str:
    return " ".join((text or "").split())


def _model_path():
    return settings.projects_dir / "promoted_translation_model.json"


def _status_path():
    return settings.projects_dir / "translation_training_status.json"


def load_accepted_pairs() -> list:
    path = pairs_path()
    if not path.exists():
        return []
    from app.services.translation_service import translation_service
    pairs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        source = _key(str(row.get("source_text") or ""))
        english = _key(str(row.get("english") or ""))
        if not source or not english or translation_service.is_devanagari(english):
            continue
        domain = str(row.get("domain") or "general")
        if translation_service.medical_english_is_unusable(source, english, domain=domain):
            continue
        pairs.append(TrainingPair(source, english, domain))
    return pairs


def split_pairs(pairs: Sequence[TrainingPair], holdout_ratio: float = 0.2) -> HoldoutSplit:
    """Hold at least one line back when there is more than one accepted line."""
    ordered = tuple(sorted(pairs, key=lambda pair: hashlib.sha256(pair.source_text.encode("utf-8")).hexdigest()))
    if len(ordered) < 2:
        return HoldoutSplit(train=ordered, holdout=())
    holdout_count = max(1, int(round(len(ordered) * holdout_ratio)))
    holdout_count = min(holdout_count, len(ordered) - 1)
    return HoldoutSplit(train=ordered[holdout_count:], holdout=ordered[:holdout_count])


def score_model(model: LineModel, holdout: Sequence[TrainingPair]) -> HoldoutScore:
    from app.services.translation_service import translation_service
    errors = 0
    for pair in holdout:
        predicted = model.translate(pair.source_text, pair.domain)
        if predicted is None:
            continue
        predicted = _key(predicted)
        if predicted != pair.english or translation_service.medical_english_is_unusable(
            pair.source_text, predicted, domain=pair.domain
        ):
            errors += 1
    return HoldoutScore(lines=len(holdout), errors=errors)


def run_training(
    pairs: Sequence[TrainingPair],
    trainer: Optional[Trainer] = None,
) -> TrainingReport:
    """Fit on the train lines and promote only when the held-out lines are not worse."""
    trainer = trainer or ExemplarTrainer()
    split = split_pairs(pairs)
    if not split.holdout:
        report = TrainingReport(
            promoted=False,
            reason="At least two accepted lines are needed so one can be held back.",
            accepted_pairs=len(pairs),
            train_count=len(split.train),
            holdout_count=0,
            baseline_errors=0,
            candidate_errors=0,
            promoted_pairs=0,
        )
        _write_status(report)
        return report
    baseline = score_model(NullModel(), split.holdout)
    candidate_model = trainer.fit(split.train)
    candidate = score_model(candidate_model, split.holdout)
    promoted_pairs = 0
    if candidate.errors > baseline.errors:
        promoted = False
        reason = "Held-back lines got worse, so the current medical fixes stay in place."
    else:
        promoted = True
        reason = "Held-back lines were not worse, so new videos can reuse the accepted lines."
        if isinstance(candidate_model, ExemplarModel):
            promoted_pairs = len(candidate_model.learned)
            _write_model(candidate_model.learned, candidate.errors, len(split.train))
    report = TrainingReport(
        promoted=promoted,
        reason=reason,
        accepted_pairs=len(pairs),
        train_count=len(split.train),
        holdout_count=len(split.holdout),
        baseline_errors=baseline.errors,
        candidate_errors=candidate.errors,
        promoted_pairs=promoted_pairs,
    )
    _write_status(report)
    return report


def training_status() -> dict:
    path = _status_path()
    status = {
        "accepted_pairs": len(load_accepted_pairs()) if pairs_path().exists() else 0,
        "promoted": _model_path().exists(),
        "reason": "",
        "train_count": 0,
        "holdout_count": 0,
        "baseline_errors": 0,
        "candidate_errors": 0,
        "promoted_pairs": 0,
    }
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            status.update({key: saved.get(key, status[key]) for key in status if key != "accepted_pairs"})
            status["accepted_pairs"] = len(load_accepted_pairs()) if pairs_path().exists() else 0
        except (OSError, ValueError):
            pass
    return status


def promoted_english(source: str) -> Optional[str]:
    path = _model_path()
    if not path.exists():
        return None
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    learned = saved.get("pairs") if isinstance(saved, dict) else None
    if not isinstance(learned, dict):
        return None
    value = learned.get(_key(source))
    return value if isinstance(value, str) and value.strip() else None


def _write_model(learned: dict, holdout_errors: int, train_count: int) -> None:
    path = _model_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "kind": "exemplar",
        "trained_at": datetime.utcnow().isoformat(),
        "holdout_errors": holdout_errors,
        "train_count": train_count,
        "pairs": learned,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_status(report: TrainingReport) -> None:
    path = _status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "promoted": report.promoted,
        "reason": report.reason,
        "accepted_pairs": report.accepted_pairs,
        "train_count": report.train_count,
        "holdout_count": report.holdout_count,
        "baseline_errors": report.baseline_errors,
        "candidate_errors": report.candidate_errors,
        "promoted_pairs": report.promoted_pairs,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
