from fastapi import APIRouter

from app.services.translation_training import load_accepted_pairs, run_training, training_status

router = APIRouter(prefix="/api/training", tags=["training"])


@router.get("")
def get_training_status():
    return training_status()


@router.post("/run")
def run_training_job():
    report = run_training(load_accepted_pairs())
    return {
        "promoted": report.promoted,
        "reason": report.reason,
        "accepted_pairs": report.accepted_pairs,
        "train_count": report.train_count,
        "holdout_count": report.holdout_count,
        "baseline_errors": report.baseline_errors,
        "candidate_errors": report.candidate_errors,
        "promoted_pairs": report.promoted_pairs,
    }
