"""Caption-to-timeline examples saved from the captions review."""
from app.core.config import settings
from app.services.caption_mappings import list_mappings, save_mapping, transcription_prompt


def test_a_mapping_replaces_the_same_caption_and_reaches_the_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    first = save_mapping({
        "project_id": "lung",
        "caption_id": "cap-1",
        "start_sec": 81.69,
        "end_sec": 83.65,
        "source_text": "अगर तुब आप",
        "spoken_text": "If you are here",
    })
    assert first["spoken_text"] == "If you are here"
    save_mapping({
        "project_id": "lung",
        "caption_id": "cap-1",
        "start_sec": 81.69,
        "end_sec": 86.2,
        "source_text": "अगर तुब आप",
        "spoken_text": "Lung cancer is the commonest cancer in the world",
    })
    rows = list_mappings("lung")
    assert len(rows) == 1
    assert rows[0]["end_sec"] == 86.2
    prompt = transcription_prompt("Transcribe the spoken dialogue faithfully.")
    assert "Lung cancer is the commonest cancer in the world" in prompt
    assert "81.69-86.2s" in prompt


def test_an_accepted_line_is_kept_for_training_and_a_tv_line_is_not(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    monkeypatch.delenv("COMPANION_TEST_MODE", raising=False)
    source = "आदिय लोग उसको टीवी मान के टीवी की दवाई चालू कर देते"
    save_mapping({
        "project_id": "lung",
        "caption_id": "bad",
        "start_sec": 23.72,
        "end_sec": 27.13,
        "source_text": source,
        "spoken_text": "TV-like TV drug, people make him",
    })
    save_mapping({
        "project_id": "lung",
        "caption_id": "good",
        "start_sec": 10,
        "end_sec": 14,
        "source_text": "लंग कैंसर दुनिया में सबसे आम कैंसर है",
        "spoken_text": "Lung cancer is the commonest cancer in the world.",
    })
    saved = list_mappings("lung")
    assert {row["caption_id"] for row in saved} == {"bad", "good"}
    ledger = (tmp_path / "accepted_translation_pairs.jsonl").read_text(encoding="utf-8")
    assert "Lung cancer is the commonest cancer in the world." in ledger
    assert "TV-like" not in ledger
    save_mapping({
        "project_id": "lung",
        "caption_id": "good-again",
        "start_sec": 14,
        "end_sec": 18,
        "source_text": "लंग कैंसर दुनिया में सबसे आम कैंसर है",
        "spoken_text": "Lung cancer is the commonest cancer in the world.",
    })
    assert ledger.count("commonest cancer") == (tmp_path / "accepted_translation_pairs.jsonl").read_text(encoding="utf-8").count("commonest cancer")


def test_a_mapping_needs_a_spoken_line_and_a_forward_time(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    try:
        save_mapping({"project_id": "lung", "start_sec": 1, "end_sec": 2, "spoken_text": ""})
        raised = False
    except ValueError:
        raised = True
    assert raised
    try:
        save_mapping({"project_id": "lung", "start_sec": 4, "end_sec": 4, "spoken_text": "cancer"})
        raised = False
    except ValueError:
        raised = True
    assert raised
