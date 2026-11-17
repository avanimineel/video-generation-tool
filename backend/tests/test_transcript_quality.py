from app.core.models import CaptionItem
from app.services.transcript_quality import (
    drop_unreadable_captions,
    has_enough_usable_speech,
    is_readable_speech,
    transcript_issues,
)
from app.services.translation_service import translation_service
import pytest


def cap(text,start=0,end=1):
    return CaptionItem(id='q',text=text,start=start,end=end)


def test_corrupt_marks_replacement_and_reversed_timing_detected():
    issues=transcript_issues([cap('ू़ी। , ु'),cap('� pressed',1,2),cap('syn',27.61,7.57)])
    assert len(issues)==3
    assert 'invalid time interval' in issues[-1]


def test_valid_hindi_and_numbers_are_not_corruption():
    assert transcript_issues([cap('७'),cap('कैंसर का इलाज',1,2),cap('CAR T-cell therapy',2,3)])==[]


def test_punctuation_only_hindi_danda_is_unreadable():
    assert not is_readable_speech('। । ।')
    assert not is_readable_speech('। ।')
    assert is_readable_speech('कैंसर का इलाज')


def test_drop_punctuation_only_captions_keeps_readable_hindi():
    """Podcast intro silence often yields danda-only Whisper lines before real speech."""
    captions = [
        cap('। । ।', 0.0, 0.8),
        cap('। ।', 0.8, 1.2),
        cap('। । ।', 1.2, 1.6),
        cap('नमस्ते दोस्तों', 2.0, 3.0),
        cap('आज हम बात करेंगे', 3.0, 4.5),
    ]
    kept, dropped = drop_unreadable_captions(captions)
    assert len(dropped) == 3
    assert all('no letters or digits' in d['reason'] for d in dropped)
    assert [c.text for c in kept] == ['नमस्ते दोस्तों', 'आज हम बात करेंगे']
    assert transcript_issues(kept) == []
    assert has_enough_usable_speech(len(kept), len(captions))


def test_drop_unreadable_fails_closed_when_almost_nothing_remains():
    captions = [cap('। । ।'), cap('�'), cap('ू़ी।')]
    kept, dropped = drop_unreadable_captions(captions)
    assert kept == []
    assert len(dropped) == 3
    assert not has_enough_usable_speech(len(kept), len(captions))


def test_translation_does_not_send_corrupt_text_to_provider(monkeypatch):
    from app.services import editorial_planner
    monkeypatch.setattr(editorial_planner,'gemini_json',lambda *a,**k:pytest.fail('Corrupt text sent'))
    with pytest.raises(ValueError,match='retranscription'):
        translation_service.translate_captions_list([cap('॑')])


def test_whisper_hallucinations_are_dropped_but_real_speech_is_kept():
    from types import SimpleNamespace
    from app.services.transcription_service import hallucinated
    seg=lambda text,**kw:SimpleNamespace(text=text,**({'no_speech_prob':.05,'avg_logprob':-.3,'compression_ratio':1.4}|kw))
    assert hallucinated(seg('Thanks for watching!',no_speech_prob=.7,avg_logprob=-.9))
    assert hallucinated(seg('the the the the the the the the the the',compression_ratio=3.1))
    assert hallucinated(seg('you',no_speech_prob=.8,avg_logprob=-1.3))
    assert hallucinated(seg('So please subscribe to the channel'))is None # A creator really saying it, clearly.
    assert hallucinated(seg('I have worked with channels with 3,000 subscribers'))is None
