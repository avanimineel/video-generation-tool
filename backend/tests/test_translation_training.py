import json

from app.core.config import settings
from app.core.models import CaptionItem
from app.services.translation_service import translation_service
from app.services.translation_training import (
    ExemplarTrainer,
    TrainingPair,
    load_accepted_pairs,
    promoted_english,
    run_training,
    split_pairs,
)


class WorseModel:
    def translate(self, source: str, domain: str = "general") -> str:
        return "There is no disagreement between a professional and a mother-in-law."


class WorseTrainer:
    def fit(self, train):
        return WorseModel()


def _pairs():
    return [
        TrainingPair("और जाथ पेशेन्द बिना किसी ददॉन आथे है।", "And most patients come without any pain.", "medical"),
        TrainingPair("ना पेशेनको और सास में दिकचात होता हैं।", "The patient does not have difficulty breathing.", "medical"),
        TrainingPair("लंग कैंसर दुनिया में सबसे आम कैंसर है", "Lung cancer is the commonest cancer in the world.", "medical"),
    ]


def test_one_line_is_held_back_and_a_clean_model_is_promoted(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    report = run_training(_pairs())
    assert report.holdout_count >= 1
    assert report.train_count >= 1
    assert report.promoted
    assert report.candidate_errors == 0
    saved = json.loads((tmp_path / "promoted_translation_model.json").read_text(encoding="utf-8"))
    assert report.holdout_count + len(saved["pairs"]) == len(_pairs())
    held = split_pairs(_pairs()).holdout
    for pair in held:
        assert pair.source_text not in saved["pairs"]


def test_a_model_that_hurts_held_back_lines_is_not_promoted(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    report = run_training(_pairs(), trainer=WorseTrainer())
    assert not report.promoted
    assert report.candidate_errors > report.baseline_errors
    assert not (tmp_path / "promoted_translation_model.json").exists()


def test_a_new_video_uses_a_promoted_line_and_still_rejects_a_bad_one(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    run_training(_pairs())
    saved = json.loads((tmp_path / "promoted_translation_model.json").read_text(encoding="utf-8"))
    source, learned = next(iter(saved["pairs"].items()))
    assert promoted_english(source) == learned
    caption = CaptionItem(
        id="new",
        start=1,
        end=4,
        text=source,
        translated_text="There is no disagreement between a professional and a mother - in - law.",
    )
    updated = translation_service.correct_medical_lines([caption], domain="medical")
    assert updated[0].translated_text == learned


def test_a_bad_stored_pair_is_not_trainable(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    path = tmp_path / "accepted_translation_pairs.jsonl"
    path.write_text(json.dumps({
        "source_text": "आदिय लोग उसको टीवी मान के टीवी की दवाई चालू कर देते",
        "english": "TV-like TV drug",
        "domain": "medical",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    assert load_accepted_pairs() == []


def test_two_lines_are_required_before_promotion(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    report = run_training(_pairs()[:1], trainer=ExemplarTrainer())
    assert not report.promoted
    assert report.holdout_count == 0
