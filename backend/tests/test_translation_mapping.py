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
    assert seen == [service.normalize_medical_asr(HINDI)]
    assert len(result) == 1
    assert result[0].translated_text == "They start TB medicine for half the people"
    assert result[0].start == 10.0 and result[0].end == 13.4


def test_short_captions_join_into_the_spoken_sentence():
    slices = [
        CaptionItem(id="a", start=12.45, end=13.55, text="बुट आपको आश्चर्रे हो गए जानके", translated_text="you'd be surprised"),
        CaptionItem(id="b", start=13.55, end=14.40, text="बुट आपको आश्चर्रे हो गए जानके", translated_text="to learn that"),
        CaptionItem(id="c", start=14.40, end=15.35, text="बुट आपको आश्चर्रे हो गए जानके", translated_text="in our country,"),
    ]
    joined = service.restore_sentences(slices)
    assert len(joined) == 1
    assert joined[0].translated_text == "you'd be surprised to learn that in our country,"
    assert joined[0].text == "बुट आपको आश्चर्रे हो गए जानके"


def test_an_edited_line_is_not_translated_again(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "local")
    monkeypatch.setattr("app.core.config.get_provider_key", lambda name: "")
    edited = CaptionItem(
        id="kept",
        start=0,
        end=2,
        text="अदेलोग उसको टीवे माणके टीवे की दवाई चालू कर देते",
        translated_text="They start TB medicine",
        editor_locked=True,
    )
    fresh = CaptionItem(id="new", start=2, end=4, text="फेफड़े का कैंसर")

    def translate(lines):
        assert lines == [service.normalize_medical_asr("फेफड़े का कैंसर")]
        return ["Lung cancer"]

    result = service.translate_captions_list([edited, fresh], local_fn=translate)
    assert result[0].translated_text == "They start TB medicine"
    assert result[1].translated_text == "Lung cancer"


def test_a_bad_saved_line_is_replaced_by_the_medical_meaning():
    source = "आदिय लोग उसको टीवी मान के टीवी की दवाई चालू कर देते"
    captions = [
        CaptionItem(id="a", start=23.7, end=27.1, text=source, translated_text="him a thief"),
        CaptionItem(id="c", start=28.0, end=29.0, text="next line", translated_text="The next sentence stays."),
    ]
    updated = service.apply_saved_edits(captions, [
        {"start_sec": 23.72, "end_sec": 27.13, "spoken_text": "TV-like TV drug, people make him", "source_text": source},
    ])
    kept = next(caption for caption in updated if caption.id == "a")
    assert kept.translated_text == "him a thief"
    choices = " ".join(item["text"] for item in service.caption_choices(source, kept.translated_text))
    assert "TB-like" in choices
    assert any(caption.translated_text == "The next sentence stays." for caption in updated)


def test_lung_cancer_is_not_left_as_a_cough():
    source = "फेफड़े का कैंसर वाले मरीज़ बिना जांच के"
    assert service.medical_english_is_unusable(source, "patients without lung coughs")
    repaired = service.repair_medical_english(source)
    assert repaired == "The disease is lung cancer."
    assert not service.medical_english_is_unusable(source, "Lung cancer is the commonest cancer in the world.")


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


SPOKEN = (
    "hota hai. आदिय लोग उसको टीवी मान के टीवी की दवाई चालूँ कर देते हैं, "
    "आदिय लोग उसकोलंग् इन्फेक्षन मान के कोई दवाई नहीं चालूँ कर थे है,"
)


def test_tv_like_in_a_medical_line_is_rewritten_as_tb_like():
    english = "hota hai. People make him a TV-like TV drug, people make him"
    assert service.medical_english_is_unusable(SPOKEN, english)
    repaired = service.repair_medical_english(SPOKEN)
    assert "TB-like" in repaired
    assert "TV" not in repaired
    assert "television" not in repaired.casefold()
    assert "lung infection" in repaired.casefold()
    assert "no medicine is started" in repaired.casefold()
    assert "half the people" in repaired.casefold()


def test_a_later_section_offers_tb_from_the_earlier_lung_line():
    earlier = "यह लंग कैंसर है"
    later = "उसको टीवी बताया"
    offered = service.caption_choices(later, "They called it a TV.", domain="medical", earlier_lines=[earlier])
    assert any(item["text"] == "It is taken as TB-like." for item in offered)


def test_an_earlier_lung_line_makes_a_later_tv_line_tb(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "local")
    monkeypatch.setattr("app.core.config.get_provider_key", lambda name: "")
    captions = [
        CaptionItem(id="earlier", start=1, end=3, text="यह लंग कैंसर है", translated_text="This is lung cancer."),
        CaptionItem(id="later", start=4, end=7, text="उसको टीवी बताया", translated_text=""),
    ]

    def translate(lines):
        assert lines == ["उसको टीबी बताया"]
        return ["They called it a TV."]

    result = service.translate_captions_list(captions, local_fn=translate, domain="medical")
    later = next(caption for caption in result if caption.id == "later")
    assert later.translated_text == "It is taken as TB-like."
    assert result[0].translated_text == "This is lung cancer."


def test_a_locked_saved_tv_like_line_is_replaced_when_the_project_is_read():
    caption = CaptionItem(
        id="edit_23720",
        start=23.72,
        end=27.13,
        text=SPOKEN,
        translated_text="hota hai. People make him a TV-like TV drug, people make him",
        editor_locked=True,
    )
    assert caption.translated_text.startswith("hota hai. People make him a TV-like")
    offered = " ".join(item["text"] for item in service.caption_choices(caption.text, caption.translated_text, domain="medical"))
    assert "TB-like" in offered
    assert "lung infection" in offered.casefold()
    mappings = [
        {"start_sec": 23.72, "end_sec": 24.51, "spoken_text": "hota hai. People", "source_text": SPOKEN},
        {"start_sec": 24.51, "end_sec": 25.21, "spoken_text": "make him a", "source_text": SPOKEN},
        {"start_sec": 25.21, "end_sec": 26.19, "spoken_text": "TV-like TV drug,", "source_text": SPOKEN},
        {"start_sec": 26.19, "end_sec": 27.13, "spoken_text": "people make him", "source_text": SPOKEN},
    ]
    restored = service.apply_saved_edits([caption], mappings)
    assert [item.id for item in restored] == ["edit_23720"]
    assert restored[0].translated_text.startswith("hota hai. People make him a TV-like")


PAIN = "और जाथ पेशेन्द बिना किसी ददॉन आथे है।"
BREATH = "ना पेशेनको और सास में दिकचात होता हैं।"


def test_a_spelled_patient_line_becomes_patients_without_pain():
    english = "And the Jath Profesand comes without any Dadon."
    assert service.medical_english_is_unusable(PAIN, english)
    assert service.repair_medical_english(PAIN) == "And most patients come without any pain."


def test_saas_after_lung_cancer_means_breathing_not_a_mother_in_law():
    captions = [
        CaptionItem(id="lung", start=1, end=3, text="यह लंग कैंसर है", translated_text="This is lung cancer."),
        CaptionItem(id="pain", start=40.24, end=43.32, text=PAIN, translated_text="And the Jath Profesand comes without any Dadon."),
        CaptionItem(
            id="breath",
            start=43.38,
            end=45.32,
            text=BREATH,
            translated_text="There is no disagreement between a professional and a mother - in - law.",
        ),
    ]
    assert captions[1].translated_text == "And the Jath Profesand comes without any Dadon."
    assert "mother" in captions[2].translated_text.casefold()
    pain = service.caption_choices(captions[1].text, captions[1].translated_text, domain="medical")
    breath = service.caption_choices(captions[2].text, captions[2].translated_text, domain="medical")
    assert any(item["text"] == "And most patients come without any pain." for item in pain)
    assert any(item["text"] == "The patient does not have difficulty breathing." for item in breath)
    assert captions[0].translated_text == "This is lung cancer."


def test_a_family_saas_stays_a_mother_in_law():
    source = "मेरी सास ने कहा"
    english = "My mother-in-law said so."
    assert not service.medical_english_is_unusable(source, english, domain="medical")
    assert service.repair_medical_english(source, domain="medical") == ""


def test_watching_television_stays_television_after_a_lung_line():
    captions = [
        CaptionItem(id="earlier", start=1, end=3, text="यह लंग कैंसर है", translated_text="This is lung cancer."),
        CaptionItem(id="screen", start=4, end=7, text="मरीज़ टीवी पर मैच देख रहा था", translated_text="The patient was watching the match on TV."),
    ]
    updated = service.correct_medical_lines(captions, domain="medical")
    screen = next(caption for caption in updated if caption.id == "screen")
    assert screen.translated_text == "The patient was watching the match on TV."


def test_a_spelled_fragment_is_replaced_with_the_medical_meaning(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "local")
    monkeypatch.setattr("app.core.config.get_provider_key", lambda name: "")

    def translate(lines):
        return ["Adelog would turn" for _ in lines]

    result = service.translate_captions_list(
        [CaptionItem(id="a", start=0, end=4, text=HINDI)],
        local_fn=translate,
    )
    assert "TB" in result[0].translated_text
    assert "half the people" in result[0].translated_text.casefold()
    assert "Adelog" not in result[0].translated_text

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
