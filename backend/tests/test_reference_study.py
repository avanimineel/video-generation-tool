import json

from app.services.reference_study import (
    STUDY_SOURCES,
    audit_clip,
    measure_timeline,
    run_inbox,
    scene_times,
    shots_from_cuts,
    study_catalog,
    training_examples,
)


def test_the_study_list_names_the_sources_and_does_not_fetch_them():
    catalog = study_catalog()
    by_id = {item["id"]: item for item in catalog}
    assert by_id["vox"]["look"] == "infographic"
    assert by_id["kurzgesagt"]["look"] == "flat_vector"
    assert by_id["ben_marriott"]["look"] == "paper_craft"
    assert by_id["eye_on_design"]["look"] == "collage"
    assert by_id["aescripts"]["lesson"]
    for item in STUDY_SOURCES:
        assert "http" not in json.dumps(item)


def test_scene_cuts_become_shots_and_the_measures_match_the_bible():
    times = scene_times("frame pts_time:0\n[Parsed_showinfo_1] n:1 pts_time:2.5\n")
    shots = shots_from_cuts(times, 5)
    assert shots[0]["end"] == 2.5
    assert shots[-1]["end"] == 5
    measured = measure_timeline(
        shots + [
            {"start": 1, "end": 1.4, "kind": "punch"},
            {"start": 4, "end": 4.4, "kind": "punch"},
            {"start": 3, "end": 3.5, "kind": "hit"},
        ],
        5,
    )
    assert measured["shot_count"] == 2
    assert measured["zoom_intervals"] == [3.0]
    assert measured["hit_frames"] == [15]
    assert measured["hits_in_band"] is True
    assert measured["layer_count"] >= 2


def test_a_sidecar_is_measured_once_and_becomes_a_training_example(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.reference_study.settings.projects_dir", tmp_path)
    note = {
        "look": "infographic",
        "source": "vox",
        "spoken": [{"start": 0, "end": 2, "text": "The claim, then the number."}],
        "events": [
            {"start": 0, "end": 2, "kind": "shot"},
            {"start": 2, "end": 4, "kind": "shot"},
            {"start": 4, "end": 4.4, "kind": "punch"},
            {"start": 6, "end": 6.5, "kind": "hit"},
        ],
    }
    (tmp_path / "reference_inbox").mkdir()
    (tmp_path / "reference_inbox" / "vox.json").write_text(json.dumps(note), encoding="utf-8")
    first = run_inbox(runner=lambda _path: ("", 0))
    assert first["fetched"] == []
    assert first["kept"][0]["look"] == "infographic"
    assert first["kept"][0]["asl"] == 2
    saved = (tmp_path / "reference_audits.jsonl").read_text(encoding="utf-8")
    assert "The claim, then the number." in saved
    assert not (tmp_path / "reference_inbox" / "vox.json").exists()
    second = run_inbox(runner=lambda _path: ("", 0))
    assert second["kept"] == []
    examples = training_examples("infographic")
    assert examples[0]["source"] == "vox"
    assert examples[0]["hit_frames"] == [15]
    assert training_examples("paper_craft") == []


def test_a_clip_without_a_look_stays_in_the_inbox(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.reference_study.settings.projects_dir", tmp_path)
    inbox = tmp_path / "reference_inbox"
    inbox.mkdir()
    (inbox / "loose.json").write_text(json.dumps({"events": [{"start": 0, "end": 1, "kind": "shot"}]}), encoding="utf-8")
    report = run_inbox()
    assert report["kept"] == []
    assert "look" in report["skipped"][0]["reason"].lower()
    assert (inbox / "loose.json").exists()
    row = audit_clip(None, {"look": "flat_vector", "source": "kurzgesagt", "duration": 2, "events": [{"start": 0, "end": 2, "kind": "shot"}]})
    assert row["source"] == "kurzgesagt"
    assert row["asl"] == 2
