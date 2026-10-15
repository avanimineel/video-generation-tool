from app.core.models import CaptionItem,WordTiming
from app.services.editorial_planner import Segment,Decision,Scores,schedule,ground,planning_windows

def sample():
    starts=[14.42,15.25,16.08,16.92]
    names=['Gujarat','UP','MP','Mizoram']
    cap=CaptionItem(id='list',start=12.8,end=17.82,text='Gujarat UP MP Mizoram',words=[WordTiming(word=n,start=t,end=t+.3) for n,t in zip(names,starts)])
    seg=Segment(id='list',start_sec=12.8,end_sec=21.5,transcript=cap.text,semantic_summary='Four Indian states',confidence=.95)
    scores=Scores(semantic_relevance=1,visual_value=1,information_gain=1,evidence_value=1,attention_value=1,confidence=1,redundancy=0,visual_fatigue=0)
    ds=[Decision(segment_id='list',intervene=True,rationale='Show the named place',strategy='STOCK_IMAGE',intent='LOCATE',anchor_phrase=n,cue_kind='place',start_sec=t,end_sec=17.82,scores=scores) for n,t in zip(names,starts)]
    return cap,seg,ds

def test_four_states_have_four_exact_onsets_and_sequential_ends():
    cap,seg,ds=sample();rows=schedule([seg],ds,[cap])
    assert all(r['status']=='planned' for r in rows)
    assert [r['start_sec'] for r in rows]==[14.42,15.25,16.08,16.92]
    assert [r['end_sec'] for r in rows]==[15.25,16.08,16.92,17.82]

def test_noun_does_not_fall_back_to_sentence_start():
    cap,seg,ds=sample();cap.words[0].end=cap.words[0].start
    timing,reason=ground(ds[0],seg,[cap])
    assert timing is None and 'word timestamps' in reason

def test_planner_receives_individual_word_timings():
    cap,seg,ds=sample()
    windows=planning_windows([seg],[cap])
    words=[w for part in windows for w in part.word_cues]
    assert [w['word'] for w in words]==['Gujarat','UP','MP','Mizoram']
    assert words[0]['start']==14.42

def test_native_anchor_overrides_early_translated_word():
    cap,seg,ds=sample()
    seg.audio_cues=[{'id':10,'word':'गुजरात','start':14.7,'end':15.1,'usable':True}]
    ds[0].audio_anchor_id=10;ds[0].audio_anchor_word='गुजरात'
    assert ground(ds[0],seg,[cap])[0][0]==14.7
    ds[0].audio_anchor_word='unrelated'
    assert ground(ds[0],seg,[cap])[0] is None

def test_native_cues_cache_reuses_same_source_and_invalidates_changes(monkeypatch,tmp_path):
    from app.services.audio_cue_alignment import source_audio_cues
    from app.services.transcription_service import transcription_service
    from app.core.config import settings
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    source=tmp_path/'source.mov';source.write_bytes(b'first')
    calls=[]
    def transcribe(*a,**kw):
        calls.append(kw['task']);return 'hi',[sample()[0]]
    monkeypatch.setattr(transcription_service,'transcribe_with_whisper',transcribe)
    assert source_audio_cues('project',source)==source_audio_cues('project',source)
    assert calls==['transcribe']
    source.write_bytes(b'changed video')
    source_audio_cues('project',source)
    assert len(calls)==2

def test_failed_coverage_retry_preserves_first_pass(monkeypatch):
    from app.services import editorial_planner as e
    cap,seg,ds=sample()
    other=seg.model_copy(update={'id':'other'})
    calls=[]
    def generate(*a,**kw):
        calls.append(1)
        if len(calls)==1:return {'decisions':[ds[0].model_dump()]}
        raise ValueError('provider unavailable')
    monkeypatch.setattr(e,'gemini_json',generate)
    result=e.editorial_decisions([seg,other])
    assert any(d.segment_id=='list' and d.intervene for d in result)
    assert any(d.segment_id=='other' and not d.intervene for d in result)

def test_function_word_cannot_anchor_a_visual_noun():
    cap,seg,ds=sample()
    seg.audio_cues=[{'id':10,'word':'अगर','start':14.7,'end':15.1,'usable':True}]
    ds[0].audio_anchor_id=10;ds[0].audio_anchor_word='अगर'
    timing,reason=ground(ds[0],seg,[cap])
    assert timing is None and 'grammatical word' in reason
