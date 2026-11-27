import json

from app.services.paper_purple_scenes import (
    accept_scene,
    card_from_cues,
    load_lexicon,
    parse_scene_reply,
    plan_paper_scenes,
    read_cues,
    scene_prompt,
    usable_model_cards,
)


def _row(index, start, end, text):
    return {"index": index, "start": start, "end": end, "text": text}


def test_a_greeting_keeps_the_people_and_a_farewell_stays_in_the_same_scene(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.paper_purple_scenes.lexicon_path", lambda: tmp_path / "lex.json")
    lines = [
        _row(0, 0.2, 3.0, "Here are five non-negotiable traditional values."),
        _row(1, 9.74, 14.2, "Number one, when you walk into a room, greet everyone in it, and when you leave,"),
        _row(2, 14.7, 18.0, "make sure you say goodbye to everyone individually."),
        _row(3, 20.86, 23.9, "If an elder comes into a room and you're seated,"),
        _row(4, 23.98, 27.4, "and there are no more seats, get up and offer your seat."),
        _row(5, 92.4, 96.0, "we pray together as a family"),
        _row(6, 145.18, 149.0, "billion dollar businesses"),
    ]
    scenes = plan_paper_scenes(lines, lexicon=load_lexicon())
    by_start = {round(scene["start"], 2): scene for scene in scenes}
    greet = by_start[9.74]
    assert greet["place"] == "house"
    assert [member["action"] for member in greet["cast"]] == ["wave", "wave"]
    assert "goodbye" in " ".join(greet["lines"])
    elder = by_start[20.86]
    assert elder["cast"][0] == {"style": "elder", "action": "walk"}
    assert elder["cast"][1]["action"] == "offer"
    assert "chair" in elder["props"]
    assert [member["action"] for member in by_start[92.4]["cast"]] == ["pray", "pray"]
    assert by_start[145.18]["subject"] == "bill"
    assert by_start[145.18]["cast"] == []
    money = plan_paper_scenes([
        _row(0, 145.18, 150.0, "billion dollar businesses"),
        _row(1, 150.34, 152.0, "a kind person on"),
        _row(2, 152.1, 155.0, "their team than the most talented person"),
    ], lexicon=load_lexicon())
    assert money[0]["subject"] == "bill" and money[0]["cast"] == []
    assert money[1]["cast"][0]["style"] == "woman"
    assert len(money[1]["cast"]) == 2


def test_a_kept_word_is_used_on_the_next_scene_and_an_unknown_word_stays_pending(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.paper_purple_scenes.lexicon_path", lambda: tmp_path / "lex.json")
    monkeypatch.setattr("app.services.paper_purple_scenes.ledger_path", lambda: tmp_path / "cards.jsonl")
    saved = accept_scene(
        ["We visit the village house"],
        {"place": "house", "cast": [{"style": "elder", "action": "walk"}], "props": []},
        [{"word": "village", "place": "house"}, {"word": "gift", "prop": "gift"}],
        project_id="demo",
    )
    assert saved["kept"] is True
    assert saved["aliases"]["village"]["place"] == "house"
    assert "gift" in saved["pending"]
    again = accept_scene(
        ["We visit the village house"],
        {"place": "house", "cast": [{"style": "elder", "action": "walk"}], "props": []},
    )
    assert again["kept"] is False
    cues = read_cues("The village is quiet", load_lexicon())
    card = card_from_cues(cues)
    assert card["place"] == "house"
    assert "gift" not in card["props"]
    ledger = [json.loads(line) for line in (tmp_path / "cards.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(ledger) == 1
    assert "village" in scene_prompt([{"id": 0, "text": "A later beat"}], ledger)


def test_a_new_room_stays_its_own_scene_and_two_daughters_match():
    lines = [
        _row(0, 0.2, 4.0, "values I incorporate into my parenting"),
        _row(1, 5.74, 9.2, "raised in a Bangladeshi family"),
        _row(2, 9.74, 13.4, "when you walk into a room, greet everyone"),
        _row(3, 108.0, 112.0, "My daughters will pray for them"),
    ]
    scenes = plan_paper_scenes(lines, lexicon=load_lexicon())
    starts = [round(scene["start"], 2) for scene in scenes]
    parent = next(scene for scene in scenes if scene["start"] < 1)
    assert "family" in " ".join(parent["lines"])
    assert parent["cast"][0]["style"] == "woman"
    assert parent["props"] == []
    assert 9.74 in starts
    daughters = next(scene for scene in scenes if scene["start"] > 100)
    assert [member["style"] for member in daughters["cast"]] == ["girl", "girl"]
    assert daughters["cast"][0]["action"] == "pray"


def test_a_model_card_drops_a_prop_the_painter_cannot_draw():
    parsed = parse_scene_reply('{"cards":[{"id":1,"place":"stage","cast":[{"style":"elder","action":"dance"},{"style":"robot","action":"walk"}],"props":["gift","chair"]}]}')
    assert parsed[0]["id"] == 1
    assert parsed[0]["card"]["place"] == ""
    assert parsed[0]["card"]["cast"] == [{"style": "elder", "action": "stand"}]
    assert parsed[0]["card"]["props"] == ["chair"]
    assert "gift" in parsed[0]["rejected"]
    assert parse_scene_reply("no json") == []
    found, rejected = usable_model_cards(parsed, [3])
    assert found == {}
    assert rejected == []


def test_an_empty_reply_does_not_invent_a_scene():
    try:
        accept_scene(["Hello"], {"place": "", "cast": [], "props": []})
    except ValueError as exc:
        assert "nothing" in str(exc)
    else:
        raise AssertionError("empty card was kept")
