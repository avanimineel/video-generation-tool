import pytest
from app.core.models import CaptionItem
from app.services.translation_service import translation_service as service
from app.services import editorial_planner as planner

HINDI = "अदेलोग उसको टीवे माणके टीवे की दवाई चालू कर देते"


def test_a_spelled_hindi_fragment_is_not_usable_english():
    assert service.is_transliteration_fragment(HINDI, "Adelog would turn")
    assert service.is_transliteration_fragment(HINDI, "The Adelog considered")
    assert not service.is_transliteration_fragment(HINDI, "They start TB medicine for half the people")


def test_hindi_slices_are_translated_together_and_the_english_is_kept(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "local")
    monkeypatch.setattr("app.core.config.get_provider_key", lambda name: "")
    seen = []

    def translate(lines):
        seen.extend(lines)
        return ["They start TB medicine for half the people" for _ in lines]

    captions = [
        CaptionItem(id="a", start=10.0, end=11.0, text="अदेलोग उसको टीवे"),
        CaptionItem(id="b", start=11.0, end=12.0, text="माणके टीवे की"),
        CaptionItem(id="c", start=12.0, end=13.4, text="दवाई चालू कर देते"),
    ]
    joined = service.join_hindi_clauses(captions)
    result = service.translate_captions_list(joined, local_fn=translate)
    assert seen == [HINDI]
    assert len(result) == 1
    assert result[0].translated_text == "They start TB medicine for half the people"
    assert result[0].start == 10.0 and result[0].end == 13.4


def test_a_hindi_clause_is_not_cut_into_three_word_boxes_before_translation():
    from app.services.transcription_service import TranscriptionService
    words = []
    start = 10.0
    for word in HINDI.split():
        words.append({"word": word, "start": start, "end": start + 0.3})
        start += 0.3
    chunks = TranscriptionService().chunk_spoken_phrases(words)
    assert len(chunks) == 1
    assert " ".join(word["word"] for word in chunks[0]) == HINDI


def test_a_spelled_fragment_is_not_stored_as_the_english(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "local")
    monkeypatch.setattr("app.core.config.get_provider_key", lambda name: "")

    def translate(lines):
        return ["Adelog would turn" for _ in lines]

    with pytest.raises(ValueError, match="converting the whole line"):
        service.translate_captions_list(
            [CaptionItem(id="a", start=0, end=4, text=HINDI)],
            local_fn=translate,
        )

def test_reordered_and_missing_lines_retry_only_missing(monkeypatch):
    calls=[]
    responses=[{'lines':[{'id':2,'text':'Test negative'},{'id':0,'text':'The doctor said'}]}, {'lines':[{'id':1,'text':'Get a biopsy'}]}]
    def generate(prompt,*a,**kw):
        calls.append(prompt);return responses.pop(0)
    monkeypatch.setattr(planner,'gemini_json',generate)
    assert service.translate_with_gemini(['डॉक्टर ने कहा','बायोप्सी कराओ','जांच नेगेटिव'])==['The doctor said','Get a biopsy','Test negative']
    import json
    assert json.loads(calls[1].split(' REQUESTED: ')[1])==[{'id':1,'text':'बायोप्सी कराओ'}]

def test_duplicate_ids_and_untranslated_rows_not_accepted(monkeypatch):
    outputs=iter([{'lines':[{'id':0,'text':'One'},{'id':0,'text':'Two'},{'id':1,'text':'हिंदी'}]}, {'lines':[{'id':0,'text':'First'},{'id':1,'text':'Second'}]}])
    monkeypatch.setattr(planner,'gemini_json',lambda *a,**k:next(outputs))
    assert service.translate_with_gemini(['पहला','दूसरा'])==['First','Second']

def test_missing_lines_fail_bounded_without_shifting_subtitles(monkeypatch):
    calls=[]
    def generate(*a,**k):calls.append(1);return {'lines':[{'id':99,'text':'Wrong ID'}]}
    monkeypatch.setattr(planner,'gemini_json',generate)
    with pytest.raises(ValueError,match='after retries'):service.translate_with_gemini(['पहला'])
    assert len(calls)==3


def test_translation_resume_reuses_valid_rows_after_provider_failure(monkeypatch, tmp_path):
    checkpoint=tmp_path/'translation.json'
    responses=iter([{'lines':[{'id':0,'text':'First'}]}, RuntimeError('Provider HTTP 503')])
    def fail(*a,**kw):
        item=next(responses)
        if isinstance(item,Exception):raise item
        return item
    monkeypatch.setattr(planner,'gemini_json',fail)
    with pytest.raises(RuntimeError):service.translate_with_gemini(['पहला','दूसरा'],checkpoint)
    calls=[]
    def recover(prompt,*a,**kw):
        calls.append(prompt);return {'lines':[{'id':1,'text':'Second'}]}
    monkeypatch.setattr(planner,'gemini_json',recover)
    assert service.translate_with_gemini(['पहला','दूसरा'],checkpoint)==['First','Second']
    import json
    assert json.loads(calls[0].split(' REQUESTED: ')[1])==[{'id':1,'text':'दूसरा'}]
    monkeypatch.setattr(planner,'gemini_json',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('No repeated requests')))
    assert service.translate_with_gemini(['पहला','दूसरा'],checkpoint)==['First','Second']
