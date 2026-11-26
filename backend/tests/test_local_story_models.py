from app.services.local_story_models import (
    caption_moments,
    collapse_beats,
    frame_shows_subject,
    groups_from_ids,
    normalize_groups,
    parse_beat_ids,
    subject_phrase,
)


def test_model_reply_joins_only_neighbors():
    assert parse_beat_ids('{"beat":[0,0,1]}', 3) == [0, 0, 1]
    assert groups_from_ids([0, 0, 1]) == [[0, 1], [2]]
    assert parse_beat_ids("not json", 2) is None
    assert parse_beat_ids('{"beat":[0,2]}', 2) is None
    assert parse_beat_ids('{"beat":[1,1]}', 2) is None
    assert normalize_groups(4, [[0, 1], [3, 5]]) == [[0, 1], [2], [3]]


def test_a_frame_match_needs_the_subject_not_only_a_person():
    assert frame_shows_subject("hospital bill<loc_10>", "a person speaking", "hospital bill")
    assert frame_shows_subject("", "a paper hospital bill on a desk", "hospital bill")
    assert not frame_shows_subject("", "a doctor speaking to the camera", "hospital bill")
    assert frame_shows_subject("", "a doctor in a white coat", "doctor")
    assert subject_phrase({"asset": {"required_entities": ["hospital bill"], "retrieval_query": "desk"}}) == "hospital bill"


def test_one_moment_per_caption_inside_the_cue():
    from types import SimpleNamespace
    state = SimpleNamespace(captions=[
        SimpleNamespace(start=0.0, end=2.0, text="health deteriorates", translated_text=""),
        SimpleNamespace(start=2.0, end=4.0, text="medical bills increase", translated_text=""),
        SimpleNamespace(start=9.0, end=10.0, text="Start now", translated_text=""),
    ])
    assert caption_moments(state, {"start_sec": 0, "end_sec": 4}) == [1.0, 3.0]
    assert collapse_beats(
        [{"start_sec": 0, "end_sec": 2, "text": "health deteriorates"}, {"start_sec": 2, "end_sec": 4, "text": "medical bills increase"}],
        [0, 0],
    ) == [{"start_sec": 0, "end_sec": 4, "text": "health deteriorates medical bills increase"}]
