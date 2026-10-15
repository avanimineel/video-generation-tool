import json
from types import SimpleNamespace
import pytest
from app.services import editorial_planner as e
from app.core.models import CaptionItem, WordTiming, MotionGraphicItem

def cap(start=0,end=5,text='Sales increased 240 percent today.'):
    return CaptionItem(id='c',start=start,end=end,text=text,words=[WordTiming(word='Sales',start=0,end=.6),WordTiming(word='increased',start=.6,end=1),WordTiming(word='240',start=1,end=1.5),WordTiming(word='percent',start=1.5,end=2)])

def segment(i=1,start=0,end=5):
    return e.Segment(id=f'segment-{i}',start_sec=start,end_sec=end,transcript='Sales increased 240 percent today.',semantic_summary='Growth metric')

def decision(i=1,start=0,end=5,**overrides):
    data=dict(segment_id=f'segment-{i}',intervene=True,rationale='Make the number legible',intent='QUANTIFY',strategy='KINETIC_TYPOGRAPHY',anchor_phrase='240 percent',start_sec=start,end_sec=end,display_text='240 percent',scores={k:.95 for k in ['semantic_relevance','visual_value','information_gain','evidence_value','attention_value','confidence']}|dict(redundancy=.05,visual_fatigue=.05))
    data.update(overrides);return e.Decision(**data)

def test_word_grounding_and_readable_duration():
    timing,method=e.ground(decision(),segment(),[cap()])
    assert timing==(1,5) and method=='exact word timestamps'

def test_short_segment_is_rejected_not_extended_over_next_topic():
    assert e.ground(decision(end=.5,anchor_phrase=''),segment(end=.5),[cap(end=.5)])[0] is None

def test_unknown_or_invented_model_transcript_is_replaced():
    raw=[segment().model_dump()|{'transcript':'made up claim'}]
    assert e.normalize_segments(raw,[cap()],5)[0].transcript==cap().text

def test_missing_speech_coverage_rejected():
    with pytest.raises(ValueError,match='omitted'):
        e.normalize_segments([segment(end=1).model_dump()],[cap()],5)

def test_no_intervention_and_redundancy():
    d=decision(intervene=False,strategy='NO_INTERVENTION')
    assert e.schedule([segment()],[d],[cap()])[0]['status']=='no_intervention'
    d=decision();d.scores.redundancy=.9
    assert e.schedule([segment()],[d],[cap()])[0]['status']=='no_intervention'

def test_manual_graphic_protected():
    g=MotionGraphicItem(id='manual',start=2,end=3,template_id='dimension_callout',title='Manual')
    assert e.schedule([segment()],[decision()],[cap()],[g])[0]['decision_reason']=='Preserved existing manual graphic'

def test_repeated_visuals_get_breathing_room():
    segs=[segment(i+1,i*3,i*3+3) for i in range(3)]
    ds=[decision(i+1,i*3,i*3+2,anchor_phrase='') for i in range(3)]
    rows=e.schedule(segs,ds,[])
    assert rows[-1]['status']=='planned'
    assert rows[-1]['editorial_state']['repeated_asset_types']==2

def test_placeholder_key_blocks_without_any_request(monkeypatch):
    import app.core.config as config
    monkeypatch.setattr(config, 'reload_env', lambda: None)
    monkeypatch.setenv('GEMINI_API_KEY','AIzaTestMockKey')
    monkeypatch.setattr(e.requests,'post',lambda *a,**k:pytest.fail('No network for placeholder'))
    with pytest.raises(ValueError,match='placeholder'):e.gemini_json('test')

def test_no_fabricated_evidence_or_substitution(tmp_path):
    row=e.schedule([segment()],[decision(strategy='ARTICLE_RECONSTRUCTION',anchor_phrase='')],[cap()])[0]
    # Sufficient interval for a research card; execution still requires verified evidence.
    row['status']='planned'
    graphics,logs=e.execute_plan(SimpleNamespace(id='test',captions=[cap()]),[row],tmp_path)
    assert not graphics and not logs and row['status']=='needs_source_or_renderer'

def test_numeric_text_must_exist_in_spoken_words(tmp_path):
    row=e.schedule([segment()],[decision(display_text='999 percent')],[cap()])[0]
    graphics,_=e.execute_plan(SimpleNamespace(id='test',captions=[cap()]),[row],tmp_path)
    assert not graphics and row['status']=='needs_review'

def test_provider_order_after_rejection_and_local_import(monkeypatch,tmp_path):
    from app.services.media_search_service import media_search_service as m
    from app.services.asset_downloader import asset_downloader as downloader
    calls=[]
    def search(q,**kw):
        calls.append(kw['provider']);return [dict(id=kw['provider'],url='https://example.test/'+kw['provider'],media_type='image')]
    monkeypatch.setattr(m,'search_media',search)
    monkeypatch.setattr(m,'rerank_candidates_with_vision',lambda cs,*a,**k: (cs[0],'accepted') if cs[0]['id']=='pixabay' else ({},'unrelated'))
    file=tmp_path/'asset.png';file.write_bytes(b'local')
    monkeypatch.setattr(downloader,'download_asset',lambda *a:dict(success=True,local_path=str(file),media_url='/local.png'))
    row=decision(strategy='STOCK_IMAGE').model_dump();row['asset']['retrieval_query']='hospital'
    chosen,attempts=e.retrieve_asset(row,'test',set())
    assert calls==['pexels','pixabay'] and chosen['local']['media_url']=='/local.png'
    assert attempts[0]['review']=='unrelated'

def test_strict_review_never_uses_first_hit_without_key(monkeypatch):
    from app.services.media_search_service import media_search_service as m
    monkeypatch.setattr(m.google_ai,'get_api_key',lambda:None)
    chosen,reason=m.rerank_candidates_with_vision([{'title':'irrelevant'}],'medical anatomy','anatomy',strict=True)
    assert not chosen and 'unavailable' in reason

def test_full_stage_pipeline_writes_reviewable_records(monkeypatch,tmp_path):
    from app.core.config import settings
    from app.services.twelve_labs_service import twelve_labs_service as tl
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    monkeypatch.setenv('GEMINI_API_KEY','fixture-credential-value');monkeypatch.setenv('TWELVE_LABS_API_KEY','fixture-credential-value')
    monkeypatch.setattr(tl,'analyze_video',lambda *a:dict(asset_id='cached',status='ready'))
    monkeypatch.setattr(tl,'get_semantic_timeline',lambda *a:[segment().model_dump()])
    monkeypatch.setattr(e,'editorial_decisions',lambda *a:[decision(display_text='Sales increased 240 percent today.')])
    state=SimpleNamespace(id='isolated',captions=[cap()],duration_seconds=5)
    graphics,logs,report=e.run_editorial(state,'unused.mp4')
    assert report['status']=='complete' and len([g for g in graphics if g.template_id=='kinetic_typography'])==1
    folder=tmp_path/'isolated'/'editorial'/report['run_id']
    assert all((folder/f).exists() for f in ['00_transcript.json','01_semantic_timeline.json','02_editorial_decisions.json','03_schedule.json','05_placement.json','06_timeline.json'])
    text=next(g for g in graphics if g.template_id=='kinetic_typography')
    assert text.start==1 and text.end==5 and logs[0]['cue_category']=='QUANTIFY'

def test_generation_failure_does_not_claim_completion(monkeypatch,tmp_path):
    import app.core.config as config
    monkeypatch.setattr(config, 'reload_env', lambda: None)
    from app.core.config import settings
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    monkeypatch.setenv('GEMINI_API_KEY','TestMockKey')
    gs,logs,report=e.run_editorial(SimpleNamespace(id='isolated',captions=[],duration_seconds=5),'unused')
    assert not gs and report['status']=='blocked' and 'placeholder' in report['errors'][0]

def test_exported_typography_draws_real_text(tmp_path):
    from PIL import Image
    from app.services.burnin_renderer import render_editorial_text,FontManager
    image=Image.new('RGB',(1080,1920),'black')
    g=MotionGraphicItem(id='t',start=0,end=4,template_id='kinetic_typography',title='240 percent',parameters={'headline':'240 percent'},pos_y=.3)
    render_editorial_text(image,g,1080,1920,FontManager())
    assert image.getbbox() is not None

def test_adjacent_edits_are_allowed_for_dense_pacing():
    segs=[segment(1,0,3),segment(2,3,6)]
    ds=[decision(1,0,3,anchor_phrase=''),decision(2,3,6,anchor_phrase='')]
    assert all(r['status']=='planned' for r in e.schedule(segs,ds,[]))

def test_translation_timing_is_not_reported_as_acoustically_exact():
    c=cap();c.translated_text='Translated meaning'
    assert e.ground(decision(),segment(),[c])[1]=='translated word timing (estimated)'

def test_repeated_anchor_uses_nearest_proposed_occurrence():
    c=cap(end=10)
    c.words += [WordTiming(word='240',start=7,end=7.5),WordTiming(word='percent',start=7.5,end=8)]
    timing,_=e.ground(decision(start=6,end=10),segment(end=10),[c])
    assert timing[0]==7

def test_invented_anchor_is_rejected():
    timing,reason=e.ground(decision(anchor_phrase='made up words'),segment(),[cap()])
    assert timing is None and 'does not occur' in reason

def test_state_uses_decision_time_within_same_long_segment():
    seg=segment(end=30)
    ds=[decision(start=t,end=t+2,anchor_phrase='') for t in (0,12,24)]
    rows=e.schedule([seg],ds,[])
    assert rows[-1]['editorial_state']['interventions_last_10_sec']==0
    assert rows[-1]['editorial_state']['time_since_last_intervention']==10

def test_stock_cannot_prove_claim():
    row=e.schedule([segment()],[decision(intent='PROVE',strategy='BROLL_VIDEO',anchor_phrase='')],[cap()])[0]
    assert row['status']=='no_intervention' and 'cannot serve as evidence' in row['decision_reason']

def test_low_understanding_confidence_retains_speaker():
    seg=segment();seg.confidence=.2
    assert e.schedule([seg],[decision()],[cap()])[0]['status']=='no_intervention'

def test_observation_interval_and_claim_provenance():
    raw=segment().model_dump()|dict(claims=['Sales increased'],claims_status='verified truth',observations=[dict(start_sec=0,end_sec=4,kind='subject',description='Talking head',confidence=.8)])
    seg=e.normalize_segments([raw],[cap()],5)[0]
    assert seg.claims_status=='speaker claims, not externally verified' and seg.source_caption_ids==['c']
    raw['observations'][0]['end_sec']=8
    with pytest.raises(ValueError,match='observation'):e.normalize_segments([raw],[cap()],5)

def test_reading_time_does_not_extend_into_next_topic():
    assert e.ground(decision(comprehension_seconds=6,anchor_phrase=''),segment(),[cap()])[0] is None

def test_no_intervention_survives_complete_pipeline(monkeypatch,tmp_path):
    from app.core.config import settings
    from app.services.twelve_labs_service import twelve_labs_service as tl
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    monkeypatch.setenv('GEMINI_API_KEY','fixture-credential-value');monkeypatch.setenv('TWELVE_LABS_API_KEY','fixture-credential-value')
    monkeypatch.setattr(tl,'analyze_video',lambda *a:dict(asset_id='cached',status='ready'))
    monkeypatch.setattr(tl,'get_semantic_timeline',lambda *a:[segment().model_dump()])
    monkeypatch.setattr(e,'editorial_decisions',lambda *a:[decision(intervene=False,strategy='NO_INTERVENTION')])
    state=SimpleNamespace(id='isolated',captions=[cap()],duration_seconds=5)
    graphics,_,report=e.run_editorial(state,'unused')
    assert report['status']=='complete' and [g for g in graphics if not g.parameters.get('retention_camera')] == []
    monkeypatch.setattr(e,'execute_plan',lambda *a:pytest.fail('Analysis must not retrieve or insert assets'))
    _,_,review=e.run_editorial(state,'unused',plan_only=True)
    assert review['status']=='review_ready'
    assert (tmp_path/'isolated'/'understanding'/review['run_id']/'02_opportunities.json').exists()

def test_deliberately_planned_edits_have_no_global_count_cap():
    segs=[segment(i+1,i*4,i*4+4) for i in range(40)]
    ds=[decision(i+1,i*4,i*4+3,anchor_phrase='') for i in range(40)]
    assert sum(r['status']=='planned' for r in e.schedule(segs,ds,[]))==40

def test_understanding_cache_retries_planning_without_video_request(monkeypatch,tmp_path):
    from app.core.config import settings
    from app.services.twelve_labs_service import twelve_labs_service as tl
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    monkeypatch.setenv('GEMINI_API_KEY','fixture-credential-value');monkeypatch.setenv('TWELVE_LABS_API_KEY','fixture-credential-value')
    source=tmp_path/'source.mp4';source.write_bytes(b'fixture video')
    calls=[]
    monkeypatch.setattr(tl,'analyze_video',lambda *a:dict(asset_id='cached',status='ready'))
    def understand(*a):calls.append(1);return [segment().model_dump()]
    monkeypatch.setattr(tl,'get_semantic_timeline',understand)
    monkeypatch.setattr(e,'editorial_decisions',lambda *a:(_ for _ in ()).throw(ValueError('provider unavailable')))
    state=SimpleNamespace(id='isolated',captions=[cap()],duration_seconds=5)
    assert e.run_editorial(state,str(source),plan_only=True)[2]['status']=='blocked'
    monkeypatch.setattr(e,'editorial_decisions',lambda *a:[decision(display_text='Sales increased 240 percent today.')])
    report=e.run_editorial(state,str(source),plan_only=True)[2]
    assert report['status']=='review_ready' and report['understanding_reused'] and len(calls)==1
    source.write_bytes(b'changed video')
    e.run_editorial(state,str(source),plan_only=True)
    assert len(calls)==2

def test_near_caption_boundary_does_not_duplicate_whole_previous_caption():
    cs=[cap(0,2,'First sentence.'),cap(2,5,'Second sentence.')]
    segs=e.normalize_segments([segment(1,0,1.99).model_dump(),segment(2,1.99,5).model_dump()],cs,5)
    assert segs[0].end_sec==segs[1].start_sec==2
    assert segs[1].transcript=='Second sentence.'

def test_persist_evaluation_decisions_captures_minimum_fields(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'projects_dir', tmp_path)
    state = SimpleNamespace(id='test_vid_01', captions=[cap()], duration_seconds=5)
    row = e.schedule([segment()], [decision(strategy='BROLL_VIDEO', anchor_phrase='240 percent')], [cap()])[0]
    eval_file, records = e.persist_evaluation_decisions(state, 'run_123', [row], model_name='gemini-3.6-flash')

    assert eval_file.exists()
    assert eval_file == tmp_path / 'evaluation' / 'runs' / 'run_123' / 'decisions.json'
    saved = json.loads(eval_file.read_text())
    assert len(saved) == 1
    d = saved[0]

    # Verify all minimum required fields
    assert d['video_id'] == 'test_vid_01'
    assert d['run_id'] == 'run_123'
    assert d['decision_id'] == 'run_123_dec_001'
    assert d['start_time'] == 1.0
    assert d['end_time'] == 4.0
    assert d['source_transcript'] == '240 percent'
    assert d['model_reasoning'] == 'Make the number legible'
    assert d['proposed_visual_type'] == 'BROLL_VIDEO'
    assert 'proposed_asset_query' in d
    assert d['confidence'] == 0.95
    assert d['model_name'] == 'gemini-3.6-flash'
    assert d['prompt_version'] == e.PROMPT_VERSION

def test_gemini_json_retries_on_503_and_falls_back(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-credential-abc123')
    monkeypatch.setattr(e.time, 'sleep', lambda *_: None)
    call_log = []

    class MockResp:
        def __init__(self, status_code, data_or_text):
            self.status_code = status_code
            self._val = data_or_text
            self.text = data_or_text if isinstance(data_or_text, str) else json.dumps(data_or_text)
        def json(self):
            return self._val

    def mock_post(url, **kwargs):
        call_log.append(url)
        # First 2 calls return 503 (model 1 attempt 0 & 1)
        if len(call_log) <= 2:
            return MockResp(503, '{"error": {"code": 503, "message": "High demand spike"}}')
        # Third call succeeds on fallback model
        return MockResp(200, {'candidates': [{'content': {'parts': [{'text': json.dumps({'ok': True})}]}}]})

    monkeypatch.setattr(e.requests, 'post', mock_post)
    res = e.gemini_json('test prompt')
    assert res == {'ok': True}
    assert len(call_log) == 3



def test_kept_generated_graphic_survives_next_iteration(monkeypatch,tmp_path):
    from app.core.config import settings
    from app.services.twelve_labs_service import twelve_labs_service as tl
    from app.services.feedback_service import feedback_service
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    monkeypatch.setenv('GEMINI_API_KEY','fixture-credential-value')
    monkeypatch.setenv('TWELVE_LABS_API_KEY','fixture-credential-value')
    monkeypatch.setattr(tl,'analyze_video',lambda *a:dict(asset_id='cached',status='ready'))
    monkeypatch.setattr(tl,'get_semantic_timeline',lambda *a:[segment().model_dump()])
    monkeypatch.setattr(e,'editorial_decisions',lambda *a:[decision(display_text='Sales increased 240 percent today.')])
    g=MotionGraphicItem(id='approved',start=0,end=5,template_id='kinetic_typography',title='Keep me',parameters={'editorial_generated':True})
    monkeypatch.setattr(feedback_service,'planning_feedback',lambda _: {'decisions':[{'id':'feedback1','cue_id':'approved','decision':'keep'}]})
    state=SimpleNamespace(id='isolated',captions=[cap()],graphics=[g],duration_seconds=5)
    graphics,_,report=e.run_editorial(state,'unused.mp4')
    assert report['status']=='complete'
    assert [x.id for x in graphics if not x.parameters.get('retention_camera')]==['approved'] # Camera punch-ins are a separate layer.
    assert report['retained_kept']==1 and report['feedback_applied']==['feedback1']


def test_rejected_local_asset_resolves_original_download_url(monkeypatch,tmp_path):
    from app.core.config import settings
    from app.services.feedback_service import feedback_service
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    folder=tmp_path/'isolated'/'media'/'downloaded';folder.mkdir(parents=True)
    (folder/'pexels_123.json').write_text(json.dumps({'url':'https://stock.test/video.mp4'}))
    monkeypatch.setattr(feedback_service,'planning_feedback',lambda _: {'decisions':[{'decision':'swap','selected_asset':{'url':'https://creator.test','media_url':'/api/media/isolated/asset/downloaded/pexels_123.mp4'}}]})
    observed=[]
    def retrieve(row,pid,used):
        observed.append(set(used));return None,[]
    monkeypatch.setattr(e,'retrieve_asset',retrieve)
    row=e.schedule([segment()],[decision(strategy='STOCK_IMAGE')],[cap()])[0]
    e.execute_plan(SimpleNamespace(id='isolated',captions=[cap()]),[row],tmp_path)
    assert 'https://stock.test/video.mp4' in observed[0]


def test_long_topic_is_reviewed_at_each_dialogue_window():
    cs=[cap(i,i+2,f'Phrase {i}') for i in range(0,24,2)]
    windows=e.planning_windows([segment(end=24)],cs)
    assert len(windows)>4
    assert all(w.end_sec-w.start_sec<=2 for w in windows if w.start_sec<15)
    assert windows[0].start_sec==0 and windows[-1].end_sec==24
    assert all(a.end_sec==b.start_sec for a,b in zip(windows,windows[1:]))
    assert all(w.semantic_summary=='Growth metric' for w in windows)
    assert len({w.id for w in windows})==len(windows)


def test_missing_planner_sections_are_retried_without_losing_valid_edits(monkeypatch):
    calls=[]
    def respond(prompt,*args):
        calls.append(prompt)
        return {'decisions':[decision(1 if len(calls)==1 else 2).model_dump()]}
    monkeypatch.setattr(e,'gemini_json',respond)
    result=e.editorial_decisions([segment(1),segment(2)])
    assert {d.segment_id for d in result}=={'segment-1','segment-2'}
    assert len(calls)==2 and 'omitted sections' in calls[1]


def test_persistent_planner_omission_is_explicit_not_total_failure(monkeypatch):
    monkeypatch.setattr(e,'gemini_json',lambda *a:{'decisions':[decision().model_dump()]})
    result=e.editorial_decisions([segment(1),segment(2)])
    omitted=next(d for d in result if d.segment_id=='segment-2')
    assert not omitted.intervene and 'after retry' in omitted.rationale


def test_planning_window_is_not_a_false_topic_boundary():
    seg=segment(end=5);seg.topic_end_sec=10
    timing,_=e.ground(decision(start=4,end=7,anchor_phrase='',strategy='BROLL_VIDEO'),seg,[])
    assert timing==(4,7)
    seg.topic_end_sec=5
    assert e.ground(decision(start=4,end=7,anchor_phrase='',comprehension_seconds=2),seg,[])[0] is None


def test_structured_provider_claim_preserves_qualifications_and_input():
    import copy
    detail={'claim':'Medical interventions require verification', 'verification':'Cannot establish from visual evidence alone.'}
    raw=segment().model_dump() | {'claims':[detail,'An ordinary claim',{'text':'Another claim'}], 'claims_status':'verified'}
    before=copy.deepcopy(raw)
    result=e.normalize_segments([raw],[cap()],5)[0]
    assert result.claims==['Medical interventions require verification','An ordinary claim','Another claim']
    assert result.claim_details==[detail,{'text':'Another claim'}]
    assert result.claims_status=='speaker claims, not externally verified'
    assert raw==before
    repeated=e.normalize_segments([result.model_dump()],[cap()],5)[0]
    assert repeated.claim_details==result.claim_details


@pytest.mark.parametrize('claim',[{'confidence':.8},{'claim':123},123])
def test_unreadable_claim_is_rejected_with_actionable_message(claim):
    raw=segment().model_dump() | {'claims':[claim]}
    with pytest.raises(ValueError,match='Retry understanding'):
        e.normalize_segments([raw],[cap()],5)


def test_segment_model_validates_dict_claims_and_entities_directly():
    raw = {
        'id': 'seg-test',
        'start_sec': 0.0,
        'end_sec': 5.0,
        'transcript': 'hello world',
        'semantic_summary': 'intro',
        'claims': [{'claim': 'Medical interns protested in Bhopal.'}],
        'entities': [{'name': 'Bhopal'}],
        'concepts': [{'concept': 'Healthcare'}],
        'uncertainties': [{'uncertainty': 'Unconfirmed timeline'}]
    }
    seg = e.Segment.model_validate(raw)
    assert seg.claims == ['Medical interns protested in Bhopal.']
    assert seg.entities == ['Bhopal']
    assert seg.concepts == ['Healthcare']
    assert seg.uncertainties == ['Unconfirmed timeline']


@pytest.fixture(autouse=True)
def isolate_provider_environment(monkeypatch):
    # Tests supply their own credentials; never reload the user's .env over them.
    from app.core import config
    monkeypatch.setattr(config, 'reload_env', lambda: None)
    from app.services import audio_cue_alignment
    monkeypatch.setattr(audio_cue_alignment, 'source_audio_cues', lambda *a: {'words': [], 'language': 'en'})


def test_collision_does_not_move_spoken_cue():
    first=decision(); second=decision()
    rows=e.schedule([segment()],[first,second],[cap()])
    assert rows[0]['start_sec']==rows[1]['start_sec']==1
    assert rows[1]['status']=='no_intervention'
    assert 'do not delay' in rows[1]['decision_reason']


def test_paraphrased_title_is_rejected(tmp_path):
    row=e.schedule([segment()],[decision(display_text='Explosive sales growth')],[cap()])[0]
    graphics,_=e.execute_plan(SimpleNamespace(id='verbatim',captions=[cap()]),[row],tmp_path)
    assert not graphics and row['status']=='needs_review'


def test_static_caption_defaults_and_strict_chunk_size():
    from app.core.models import CaptionStyle
    from app.services.transcription_service import TranscriptionService
    style=CaptionStyle()
    assert style.animation_type=='none'
    assert not style.has_highlight and not style.has_keyword_emphasis and not style.highlight_bounce
    words=[{'word':str(i),'start':i,'end':i+1} for i in range(7)]
    chunks=TranscriptionService().chunk_segment_words(words,3)
    assert [len(c) for c in chunks]==[3,3,1]
    assert [w for c in chunks for w in c]==words


def test_multi_segment_observation_redistribution_prevents_crash():
    # Replicates user bug: LLM returns observation 55-59s inside segment-4 (39-55s) instead of segment-5 (55-68s)
    seg4 = segment().model_dump() | {
        'id': 'segment-4',
        'start_sec': 38.94,
        'end_sec': 55.0,
        'observations': [{'start_sec': 55.0, 'end_sec': 59.0, 'kind': 'scene', 'description': 'Montage of healthy foods', 'confidence': 0.9}]
    }
    seg5 = segment().model_dump() | {
        'id': 'segment-5',
        'start_sec': 55.0,
        'end_sec': 68.0,
        'observations': [{'start_sec': 60.0, 'end_sec': 64.0, 'kind': 'scene', 'description': 'Visuals of traffic', 'confidence': 0.9}]
    }
    caps = [cap(start=38.94, end=55.0), cap(start=55.0, end=68.0)]
    normalized = e.normalize_segments([seg4, seg5], caps, 70.0)
    assert len(normalized) == 2
    # Observation 55-59s was cleanly redistributed into segment 5
    obs_times = [(o.start_sec, o.end_sec) for o in normalized[1].observations]
    assert (55.0, 59.0) in obs_times


def test_tail_speech_boundary_extension_prevents_false_omitted_rejection():
    # Model rounds final segment to 76.0s but speech continues to 76.8s in a 77.3s video
    seg = segment().model_dump() | {
        'id': 'segment-7',
        'start_sec': 68.0,
        'end_sec': 76.0,
        'observations': []
    }
    caps = [cap(start=68.0, end=75.5), cap(start=76.0, end=76.8, text='Doctor advice.')]
    normalized = e.normalize_segments([seg], caps, 77.3)
    assert normalized[0].end_sec == 76.8
    assert 'Doctor advice.' in normalized[0].transcript




@pytest.mark.parametrize('bad', ['ABLE SPEAK LIKE WAY', 'GET DISEASE GET DISEASE', 'is negative'])
def test_actual_feedback_broken_titles_are_rejected(tmp_path, bad):
    caption = cap(text='If I am able to speak today it is because of my wife. The PET scan is negative.')
    row=e.schedule([segment()],[decision(display_text=bad)],[caption])[0]
    row['status']='planned'
    graphics,_=e.execute_plan(SimpleNamespace(id='regression',captions=[caption],graphics=[]),[row],tmp_path)
    assert not graphics and row['status']=='needs_review'


def test_adjacent_title_keeps_audio_cue_without_artificial_gap(tmp_path, monkeypatch):
    from app.services.subject_layers import prepare_subject_layers
    monkeypatch.setattr('app.services.subject_layers.prepare_subject_layers', lambda *a: None)
    caption=cap(text='I can speak today because of my wife')
    kept=MotionGraphicItem(id='manual',start=0,end=1,template_id='kinetic_typography',title='Previous exact phrase')
    row=e.schedule([segment()],[decision(display_text='I can speak today')],[caption])[0]
    row.update(status='planned',start_sec=1.1,end_sec=4)
    graphics,_=e.execute_plan(SimpleNamespace(id='gap',captions=[caption],graphics=[kept]),[row],tmp_path)
    assert len(graphics)==1 and graphics[0].start==1.1
    assert row['start_sec']==1.1


@pytest.mark.parametrize('text', ['I eat any of the vegetables', 'The jeep is outside', 'Research on TB', 'The whole place was completed'])
def test_no_global_phonetic_rewriting(text):
    from app.services.translation_service import translation_service
    assert translation_service.sanitize_english_subtitles(text)==text


def test_connected_process_diagram_can_last_eight_seconds():
    d=decision(end=9,strategy='DIAGRAM',anchor_phrase='240 percent')
    timing,_=e.ground(d,segment(end=10),[cap(end=10)])
    assert timing == (1,9)


def test_stale_planned_camera_row_cannot_reintroduce_zoom(tmp_path):
    row=decision(strategy='SOURCE_VIDEO_REFRAME').model_dump()
    row.update(status='planned',timing_method='old cached plan')
    graphics,_=e.execute_plan(SimpleNamespace(id='isolated',captions=[cap()],graphics=[]),[row],tmp_path)
    assert graphics == []
    assert row['status']=='needs_review'
    assert 'disabled' in row['decision_reason']


def test_strategy_schema_and_formatting():
    schema=e.Decision.model_json_schema()['properties']['strategy']
    # The planner is only offered strategies the renderer can draw.
    assert schema['enum']==e.PLANNABLE and set(e.PLANNABLE)<=set(e.STRATEGIES)
    assert decision(strategy=' stock-image ').strategy=='STOCK_IMAGE'
    assert decision(strategy='invented composition').strategy=='invented composition'


def test_unknown_strategy_does_not_discard_other_planner_decisions(monkeypatch):
    unknown=decision(strategy='ARCHIVAL_IDENTITY_MONTAGE')
    valid=decision(i=2,start=5,end=10,anchor_phrase='')
    monkeypatch.setattr(e,'gemini_json',lambda *a,**kw:{'decisions':[unknown.model_dump(),valid.model_dump()]})
    segs=[segment(),segment(2,5,10)]
    ds=e.editorial_decisions(segs)
    rows=e.schedule(segs,ds,[])
    assert rows[0]['status']=='needs_source_or_renderer'
    assert 'ARCHIVAL_IDENTITY_MONTAGE' in rows[0]['decision_reason']
    assert rows[1]['status']=='planned'
    assert rows[0]['strategy']=='ARCHIVAL_IDENTITY_MONTAGE'


def test_two_word_heading_is_not_subject_to_subtitle_word_count(tmp_path, monkeypatch):
    monkeypatch.setattr('app.services.subject_layers.prepare_subject_layers',lambda *a:None)
    caption=cap(text='The first one is brand deals')
    row=e.schedule([segment()],[decision(display_text='brand deals')],[caption])[0]
    graphics,_=e.execute_plan(SimpleNamespace(id='short-title',captions=[caption],graphics=[]),[row],tmp_path)
    assert len(graphics)==1 and graphics[0].title=='brand deals'


def test_no_intervention_strategy_is_reviewed_even_with_intervene_true(monkeypatch):
    calls=[]
    def planner(prompt,*args):
        calls.append(prompt)
        d=decision(strategy='NO_INTERVENTION',rationale='Presenter maintains direct engagement') if len(calls)==1 else decision(strategy='BROLL_VIDEO')
        return {'decisions':[d.model_dump()]}
    monkeypatch.setattr(e,'gemini_json',planner)
    result=e.editorial_decisions([segment()])
    assert len(calls)==2 and result[0].strategy=='BROLL_VIDEO'


def test_unsupported_plans_do_not_count_as_usable_coverage(monkeypatch):
    seg=segment(end=12)
    old=decision(end=12,strategy='DIAGRAM',anchor_phrase='')
    calls=[]
    def repair(prompt,*args):
        calls.append(prompt)
        return {'decisions':[decision(end=3,strategy='BROLL_VIDEO',anchor_phrase='').model_dump()]}
    monkeypatch.setattr(e,'gemini_json',repair)
    result=e.repair_sparse_schedule([seg],[old],[cap(end=12)])
    assert calls and result[0].strategy=='BROLL_VIDEO'


def test_opening_seconds_keep_the_speaker_instead_of_fullscreen_stock():
    early=decision(strategy='BROLL_VIDEO',composition={'layout':'fullscreen'})
    row=e.schedule([segment()],[early],[cap()])[0]
    assert row['status']=='no_intervention' and 'Opening seconds' in row['decision_reason']
    words=[WordTiming(word=w,start=4+i*.5,end=4.5+i*.5) for i,w in enumerate('Sales increased 240 percent'.split())]
    later=e.schedule([segment(end=10)],[decision(end=10,strategy='BROLL_VIDEO',composition={'layout':'fullscreen'})],[CaptionItem(id='c',start=4,end=10,text='Sales increased 240 percent today.',words=words)])[0]
    assert later['status']=='planned' and later['start_sec']>=e.OPENING_SPEAKER_SECONDS
    title=e.schedule([segment()],[decision()],[cap()])[0]
    assert title['status']=='planned' # Titles may still open the video.


def test_digit_title_for_spoken_number_word_is_accepted():
    text='There are eight business models today.'
    words=[WordTiming(word=w,start=i*.5,end=i*.5+.5) for i,w in enumerate(text.split())]
    seg=e.Segment(id='segment-1',start_sec=0,end_sec=5,transcript=text,semantic_summary='Roadmap')
    row=e.schedule([seg],[decision(anchor_phrase='eight business models',display_text='8 BUSINESS MODELS')],[CaptionItem(id='c',start=0,end=5,text=text,words=words)])[0]
    assert row['status']=='planned' and row['display_text']=='8 BUSINESS MODELS'


def spoken(text,**overrides):
    words=[WordTiming(word=w,start=i*.5,end=i*.5+.5) for i,w in enumerate(text.split())]
    seg=e.Segment(id='segment-1',start_sec=0,end_sec=10,transcript=text,semantic_summary='Test')
    return [seg],[decision(end=10,**overrides)],[CaptionItem(id='c',start=0,end=10,text=text,words=words)]


def test_number_forms_are_the_same_spoken_text():
    same=[('1,000,000 subscribers','even a million subscribers'),('1 million','a million'),('8 models','eight models'),
          ('250,000','two hundred fifty thousand'),('3,000','3 ,000'.replace(' ','')),('25','twenty five'),('2.5 million','2.5 million'),('10 lakh','ten lakh')]
    for title,speech in same:assert e.verbatim_text(title,speech),(title,speech)
    different=[('2,000,000 subscribers','a million subscribers'),('9 models','eight models'),('999 percent','240 percent'),('a model','eight models')]
    for title,speech in different:assert not e.verbatim_text(title,speech),(title,speech)


def test_stat_counter_can_show_digits_for_a_spoken_number(tmp_path):
    segs,ds,caps=spoken('I have helped even a million subscribers grow.',strategy='STAT_COUNTER',anchor_phrase='even a million subscribers',display_text='1,000,000 subscribers')
    row=e.schedule(segs,ds,caps)[0]
    graphics,_=e.execute_plan(SimpleNamespace(id='numbers',captions=caps,graphics=[]),[row],tmp_path)
    assert row['status']=='inserted' and graphics[0].parameters['headline']=='1,000,000 subscribers'


def test_checklist_renders_as_spoken_staircase_title(tmp_path):
    segs,ds,caps=spoken('Today I will rank them all for you.',strategy='CHECKLIST',visual_role='checklist',anchor_phrase='rank them all',display_text='Ranking 8 YouTube Business Models')
    row=e.schedule(segs,ds,caps)[0]
    assert row['status']=='planned' and row['display_text']=='rank them all'
    graphics,_=e.execute_plan(SimpleNamespace(id='checklist',captions=caps,graphics=[]),[row],tmp_path)
    assert row['status']=='inserted' and graphics[0].parameters['title_style']=='staircase'
    assert [line['text'] for line in graphics[0].parameters['title_lines']]==['rank','them','all']


def test_unrenderable_request_falls_back_to_spoken_title_not_stock(tmp_path,monkeypatch):
    monkeypatch.setattr(e,'retrieve_asset',lambda *a:(_ for _ in ()).throw(AssertionError('stock must not be searched')))
    segs,ds,caps=spoken('The process has three clear stages today.',strategy='DIAGRAM',anchor_phrase='three clear stages',display_text='Process overview')
    row=e.schedule(segs,ds,caps)[0]
    assert (row['strategy'],row['requested_strategy'],row['display_text'])==('KINETIC_TYPOGRAPHY','DIAGRAM','three clear stages')
    graphics,_=e.execute_plan(SimpleNamespace(id='fallback',captions=caps,graphics=[]),[row],tmp_path)
    assert row['status']=='inserted' and graphics[0].template_id=='kinetic_typography'


def test_evidence_request_is_never_replaced_by_a_title(tmp_path):
    segs,ds,caps=spoken('The court ruling was published last year.',strategy='ARTICLE_RECONSTRUCTION',visual_role='evidence',anchor_phrase='court ruling',display_text='court ruling')
    row=e.schedule(segs,ds,caps)[0]
    graphics,_=e.execute_plan(SimpleNamespace(id='evidence',captions=caps,graphics=[]),[row],tmp_path)
    assert not graphics and row['strategy']=='ARTICLE_RECONSTRUCTION' and row['status']=='needs_source_or_renderer'


def test_back_to_back_fullscreen_stock_returns_to_the_speaker():
    text='Open the laptop now then pour the coffee slowly then walk outside into traffic today'
    words=[WordTiming(word=w,start=4+i*.5,end=4.5+i*.5) for i,w in enumerate(text.split())]
    seg=e.Segment(id='segment-1',start_sec=0,end_sec=14,transcript=text,semantic_summary='Routine')
    full={'layout':'fullscreen'}
    ds=[decision(end=14,strategy='BROLL_VIDEO',anchor_phrase='laptop',display_text='laptop',cue_kind='noun',composition=full,comprehension_seconds=1),
        decision(end=14,strategy='BROLL_VIDEO',anchor_phrase='coffee',display_text='coffee',cue_kind='noun',composition=full,comprehension_seconds=1)]
    rows=e.schedule([seg],ds,[CaptionItem(id='c',start=4,end=14,text=text,words=words)])
    planned=[r for r in rows if r['status']=='planned']
    assert len(planned)==2 and planned[0]['end_sec']<=planned[1]['start_sec']
    assert [r['composition']['layout'] for r in planned]==['fullscreen','split_screen']


def test_planning_prompt_is_domain_neutral_and_offers_only_renderable_strategies(monkeypatch):
    prompts=[]
    monkeypatch.setattr(e,'gemini_json',lambda prompt,*a,**kw:prompts.append(prompt) or {'decisions':[decision().model_dump()]})
    e.editorial_decisions([segment()])
    head=prompts[0].split('FINISHED-REEL REFERENCE')[0]
    assert 'RETENTION PACING WITH PURPOSE' in head and 'HIGH VISUAL DENSITY' not in head
    assert not any(word in head for word in ('pills','cancer type','between wards'))
    allowed=prompts[0].split('Allowed strategies: ')[1].split('\n')[0]
    assert allowed==', '.join(e.PLANNABLE) and 'DIAGRAM' not in allowed


def test_static_stretch_is_repaired_even_when_other_parts_are_busy(monkeypatch):
    assert e.static_stretches([dict(start_sec=2,end_sec=4),dict(start_sec=5,end_sec=7)],0,20)==[(7,20)]
    assert e.static_stretches([dict(start_sec=2,end_sec=4)],0,9)==[]
    segs=[segment(i+1,i*3,i*3+3) for i in range(6)] # 18 seconds of three-second beats.
    busy=[decision(i+1,i*3,i*3+2,anchor_phrase='') for i in range(2)]
    quiet=[decision(i+1,i*3,i*3+3,anchor_phrase='',intervene=False,strategy='NO_INTERVENTION') for i in range(2,6)]
    asked=[]
    def planner(prompt,*a,**kw):
        asked.append(prompt)
        return {'decisions':[decision(5,12,14,anchor_phrase='').model_dump()]}
    monkeypatch.setattr(e,'gemini_json',planner)
    repaired=e.repair_sparse_schedule(segs,busy+quiet,[])
    assert len(asked)==1 and '"id": "segment-5"' in asked[0] and '"id": "segment-1"' not in asked[0]
    assert next(d for d in repaired if d.segment_id=='segment-5').intervene
    asked.clear()
    assert e.repair_sparse_schedule(segs[:3],[decision(i+1,i*3,i*3+2,anchor_phrase='') for i in range(3)],[])
    assert not asked # No static stretch, no extra planner call.


def test_late_cue_may_finish_just_past_its_topic_but_keeps_full_reading_time():
    seg=segment(end=5);seg.topic_end_sec=5
    timing,_=e.ground(decision(start=3.9,end=5,anchor_phrase='',comprehension_seconds=1.5),seg,[])
    assert timing==(3.9,5.4) # 0.4s past the boundary instead of being dropped.
    assert e.ground(decision(start=4.5,end=5,anchor_phrase='',comprehension_seconds=1.5),seg,[])[0] is None # Would need 1.0s of overhang.


def edited(treatments=(),kind='scene',description='Doctor speaking to camera',context='Doctor speaking'):
    seg=e.Segment(id='segment-1',start_sec=0,end_sec=10,transcript='Sales increased 240 percent today.',semantic_summary='Growth',
                  existing_treatments=list(treatments),current_visual_context=context,
                  observations=[e.Observation(start_sec=0,end_sec=10,kind=kind,description=description)])
    words=[WordTiming(word=w,start=4+i*.5,end=4.5+i*.5) for i,w in enumerate('Sales increased 240 percent'.split())]
    return seg,[CaptionItem(id='c',start=4,end=10,text='Sales increased 240 percent today.',words=words)]


def test_source_that_is_already_edited_is_not_edited_over():
    stock=dict(strategy='BROLL_VIDEO',composition={'layout':'fullscreen'})
    seg,caps=edited(['burned_in_captions'])
    title=e.schedule([seg],[decision(end=10)],caps)[0]
    assert title['status']=='no_intervention' and title['preserved_existing'] and 'duplicate' in title['decision_reason']
    assert e.schedule([seg],[decision(end=10,**stock)],caps)[0]['status']=='planned' # Captions alone do not block a cutaway.
    for seg,caps in (edited(['broll']),edited(description='Doctor with a diagram illustrating the transplant process'),edited(kind='existing_evidence'),edited(context='Photos of the actress in a collage')):
        row=e.schedule([seg],[decision(end=10,**stock)],caps)[0]
        assert row['status']=='no_intervention' and row['preserved_existing'] and 'preserved' in row['decision_reason']
    seg,caps=edited(kind='onscreen_text',description='Text overlay listing symptoms')
    assert e.schedule([seg],[decision(end=10)],caps)[0]['preserved_existing']
    raw,caps=edited(['none'])
    assert [e.schedule([raw],[d],caps)[0]['status'] for d in (decision(end=10),decision(end=10,**stock))]==['planned','planned']


def spoken_caps(*sentences):
    caps=[];t=0.0
    for i,(text,length) in enumerate(sentences):
        caps.append(CaptionItem(id=f'c{i}',start=t,end=t+length,text=text));t+=length
    return caps,t


def test_punch_ins_alternate_on_sentence_beats_and_anchor_on_the_face():
    from app.services.retention_pacing import add_punch_ins,sentence_beats
    caps,total=spoken_caps(('I have worked with many channels.',3),('Most videos show',1.5),('only a few ways.',1.5),('But there are eight models.',3),('Today I rank them.',2))
    assert sentence_beats(caps,total)==[(0.0,3.0),(3.0,6.0),(6.0,9.0),(9.0,11.0)]
    state=SimpleNamespace(captions=caps,duration_seconds=total)
    graphics,camera=add_punch_ins(state,[],head_band=lambda state,t:(.2,.5))
    punches=[g for g in graphics if g.template_id=='source_reframe']
    assert [(g.start,g.end) for g in punches]==[(3.0,6.0),(9.0,11.0)] # Opens wide, then alternates.
    assert all(g.parameters['start_scale']==g.parameters['end_scale']==1.14 and g.parameters['focus_y']==.35 for g in punches)
    assert camera['cut_times']==[3.0,6.0,9.0,11.0]
    cutaway=MotionGraphicItem(id='b',start=3,end=6,template_id='youtube_insert',title='b',placement_mode='insert')
    graphics,_=add_punch_ins(state,[cutaway],head_band=lambda state,t:None)
    assert [(g.start,g.end) for g in graphics if g.template_id=='source_reframe']==[(9.0,11.0)] # No zoom hidden under a cutaway.
    low,_=add_punch_ins(state,[],head_band=lambda state,t:(.6,.9))
    assert all(g.parameters['focus_y']==.36 for g in low if g.template_id=='source_reframe') # Implausible head position is ignored.
    again,_=add_punch_ins(state,graphics,head_band=lambda state,t:None)
    assert len(again)==len(graphics) # Re-running replaces the camera layer instead of stacking it.


def test_punch_in_zooms_toward_the_focus_point():
    from PIL import Image
    from app.services.burnin_renderer import apply_source_reframe
    frame=Image.new('RGB',(100,200),'black');frame.paste('white',(40,20,60,40)) # A "face" high in the frame.
    punch=MotionGraphicItem(id='p',start=0,end=2,template_id='source_reframe',title='Punch-in',parameters={'start_scale':1.5,'end_scale':1.5,'motion_curve':'hold','focus_x':.5,'focus_y':.15})
    zoomed=apply_source_reframe(frame,[punch],1)
    assert zoomed.size==frame.size and zoomed.getpixel((50,45))==(255,255,255) and zoomed.getpixel((50,150))==(0,0,0)
    centred=apply_source_reframe(frame,[MotionGraphicItem(id='c',start=0,end=2,template_id='source_reframe',title='c',parameters={'start_scale':1.5,'end_scale':1.5})],1)
    assert centred.getpixel((50,45))==(0,0,0) # Without a focus the centre crop pushes the face out of that spot.


def test_rapid_counts_keep_every_number_and_original_onset():
    seg=segment(end=8)
    seg.audio_cues=[{'id':i,'word':word,'start':t,'end':t+.3,'usable':True} for i,(word,t) in enumerate([
        ('3',1),(',000,',1.3),('5',1.7),(',000,',2),('10',2.4),(',000,',2.7),('100',3.1),(',000,',3.4)])]
    out=e.preserve_number_enumerations([seg],[])
    assert [d.display_text for d in out]==['3,000','5,000','10,000','100,000']
    assert [d.start_sec for d in out]==[1,1.7,2.4,3.1]
    assert out[0].end_sec==out[1].start_sec
    assert e.verbatim_text('3,000','with 3 ,000, subscribers')


def test_every_significant_spoken_figure_gets_a_counter():
    text='She was diagnosed at 37 years of age and given 5 years.'
    words=text.split()
    seg=segment(end=10);seg.transcript=text
    seg.audio_cues=[{'id':i,'word':word,'start':i*.5,'end':i*.5+.4,'usable':True} for i,word in enumerate(words)]
    caps=[CaptionItem(id='c',start=0,end=10,text=text)]
    out=e.add_spoken_figures([seg],[],caps)
    assert [(d.display_text,d.start_sec,d.strategy) for d in out]==[('37 years',2.0,'STAT_COUNTER')] # "5" is too small to be a statistic.
    covered=e.add_spoken_figures([seg],[decision(start=2.2,end=4)],caps)
    assert len(covered)==1 # The planner already put something there.
    pct=segment(end=4);pct.audio_cues=[{'id':0,'word':'100%','start':1,'end':1.4,'usable':True}]
    assert [d.display_text for d in e.add_spoken_figures([pct],[],[CaptionItem(id='c',start=0,end=4,text='Not a 100% cure')])]==['100% cure']


def test_stock_runs_only_for_pictures_the_speech_names(monkeypatch,tmp_path):
    caps=[CaptionItem(id='a',start=0,end=2,text="Hi comrades, I've"),CaptionItem(id='b',start=10,end=12,text='big creators are making money')]
    row=lambda start,target,query:dict(start_sec=start,end_sec=start+1.5,asset=dict(semantic_target=target,retrieval_query=query,required_entities=['desk']))
    assert e.stock_grounding(row(.3,'creator workspace','youtube creator desk setup'),caps) # A greeting names no picture.
    assert e.stock_grounding(row(10.2,'content creator editing','creator editing video at desk'),caps) is None # "creators" ~ "creator".
    searched=[]
    monkeypatch.setattr(e,'retrieve_asset',lambda *a:searched.append(1) or (None,[]))
    planned=dict(row(.3,'creator workspace','youtube creator desk setup'),strategy='BROLL_VIDEO',status='planned',segment_id='s',composition={'layout':'fullscreen'},
                 anchor_phrase='comrades',timing_method='exact',display_text='Hi comrades',intent='ILLUSTRATE',rationale='r',decision_reason='r')
    graphics,_=e.execute_plan(SimpleNamespace(id='g',captions=caps,graphics=[]),[planned],tmp_path)
    assert not graphics and not searched and planned['status']=='no_intervention' # Not even searched.


def test_figure_title_takes_a_noun_not_a_name_or_another_number():
    def figures(text):
        seg=segment(end=10);seg.transcript=text
        seg.audio_cues=[{'id':i,'word':w,'start':i*.5,'end':i*.5+.4,'usable':True} for i,w in enumerate(text.split())]
        return [d.display_text for d in e.add_spoken_figures([seg],[],[CaptionItem(id='c',start=0,end=10,text=text)])]
    assert figures('In 2009 Lisa was diagnosed')==['2009']
    assert figures('with 3,000 5,000 viewers')[0]=='3,000'
    assert figures('it costs 250 rupees')==['250 rupees']
