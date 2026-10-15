from types import SimpleNamespace
from app.services.finished_reel_understanding import load_profile, source_role, build_brief, source_requirement, audit_plan
from app.services import editorial_planner as e


def test_reference_roles_use_content_not_filename():
    p=load_profile()
    assert source_role(digest=p['sources']['after']['sha256'])=='finished_reference'
    assert source_role(digest=p['sources']['before']['sha256'])=='before_source'
    assert source_role(digest='unrelated')=='unclassified_source'


def test_understanding_brief_preserves_existing_treatments_and_uncertainty():
    s=e.Segment(id='s1',start_sec=0,end_sec=8,transcript='According to reports',semantic_summary='Reported medicine investigation',claims=['A reported incident'],existing_treatments=['article_card'],current_visual_context='Highlighted article',uncertainties=['Publisher text unclear'],narrative_role='CLAIM')
    b=build_brief([s])['beats'][0]
    assert b['existing_treatments']==['article_card']
    assert b['uncertainties']==['Publisher text unclear']
    assert any('source' in q for q in b['questions'])


def test_identity_and_evidence_cannot_be_fulfilled_by_generic_stock():
    for role in ['identity','evidence']:
        assert 'verified specific source' in source_requirement({'visual_role':role,'strategy':'STOCK_IMAGE'})
    assert source_requirement({'visual_role':'illustration','strategy':'STOCK_IMAGE'}) is None


def test_preserve_prevents_duplicate_overlay():
    assert 'duplicate' in source_requirement({'existing_treatment_action':'preserve','intervene':True})


def test_finish_audit_does_not_call_missing_renderer_complete():
    rows=[dict(segment_id='s1',start_sec=10,end_sec=15,visual_role='checklist',viewer_need='Show steps in order',strategy='CHECKLIST',status='needs_source_or_renderer',decision_reason='Checklist renderer required',intervene=True)]
    audit=audit_plan(rows)
    assert not audit['complete_finished_reel']
    assert audit['unresolved_requirements'][0]['role']=='checklist'


def test_reference_prompt_enters_actual_planner(monkeypatch):
    prompts=[]
    def response(prompt,*args):
        prompts.append(prompt)
        return {'decisions':[{'segment_id':'s1','intervene':False,'rationale':'Existing article already communicates claim','strategy':'NO_INTERVENTION','visual_role':'evidence','existing_treatment_action':'preserve','start_sec':0,'end_sec':5,'scores':{k:.5 for k in e.Scores.model_fields}}]}
    monkeypatch.setattr(e,'gemini_json',response)
    seg=e.Segment(id='s1',start_sec=0,end_sec=5,transcript='A reported claim',semantic_summary='Report')
    ds=e.editorial_decisions([seg],finish_brief=build_brief([seg]))
    assert 'FINISHED-REEL REFERENCE' in prompts[0] and 'numbered medicine-verification checklist' in prompts[0]
    assert ds[0].existing_treatment_action=='preserve'


def test_provider_treatment_labels_normalize_to_observation_kinds():
    row=dict(start_sec=0,end_sec=5,transcript='',semantic_summary='Existing cutaway',observations=[dict(start_sec=0,end_sec=5,kind='broll',description='Medicine footage',confidence=.9)])
    assert e.normalize_segments([row],[],5)[0].observations[0].kind=='scene'


def test_editor_reference_does_not_transfer_identity_to_other_sources(tmp_path, monkeypatch):
    import hashlib, json
    from app.services import finished_reel_understanding as f
    source = tmp_path/'same_filename.mov'
    source.write_bytes(b'original reference source')
    profile = tmp_path/'reference.json'
    profile.write_text(json.dumps({'id':'test','provenance':'written breakdown','rules':['No camera filler'],
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'scenes':[{'description':'Lisa Ray portrait','reference_seconds':[8,9]}]}))
    monkeypatch.setattr(f,'EDITOR_REFERENCE',profile)
    assert f.editor_reference(source)['scenes'][0]['description']=='Lisa Ray portrait'
    source.write_bytes(b'different upload with same filename')
    assert 'scenes' not in f.editor_reference(source)
    assert 'Lisa Ray' not in json.dumps(f.editor_reference())


def test_automatic_camera_reframe_is_not_a_meaningful_scene():
    assert 'disabled' in source_requirement({'strategy':'SOURCE_VIDEO_REFRAME'})


def test_editor_style_preserves_static_subtitles_and_scenes():
    from app.services.finished_reel_understanding import editor_reference
    rules=' '.join(editor_reference()['rules'])
    assert 'subtitles remain static' in rules
    assert 'Half-screen imagery remains still' in rules
    assert 'eight seconds' in rules


def row(status,start,end,layout='text_overlay',**extra):
    return dict(segment_id=f's{start}',start_sec=start,end_sec=end,strategy='KINETIC_TYPOGRAPHY',status=status,intervene=True,realized_composition={'layout':layout},**extra)


def test_scorecard_measures_the_timeline_and_sets_the_outcome():
    from app.services.finished_reel_understanding import scorecard, audit_plan
    clean=scorecard([row('inserted',2,4),row('inserted',8,10,'fullscreen'),row('no_intervention',12,13)],16)
    assert clean['outcome']=='complete' and clean['visual_coverage']==.25 and clean['speaker_visible_ratio']==.875 and clean['longest_static_sec']==6
    assert scorecard([row('inserted',2,4),row('inserted',8,10)],17)['outcome']=='complete_with_gaps' # 7s static tail.
    gaps=scorecard([row('inserted',2,4),row('rejected_assets',8,10),row('needs_source_or_renderer',12,14)],20)
    assert gaps['outcome']=='complete_with_gaps' and gaps['unresolved']==2 and gaps['rejected_assets']==1
    static=scorecard([row('inserted',2,4)],40)
    assert static['outcome']=='complete_with_gaps' and 'no on-screen change' in static['reasons'][0]
    nothing=scorecard([row('rejected_assets',2,4)],20)
    assert nothing['outcome']=='needs_attention'
    substituted=scorecard([row('inserted',2,4,requested_strategy='DIAGRAM')],10)
    assert substituted['outcome']=='complete_with_gaps' and 'DIAGRAM' in substituted['reasons'][0]
    assert audit_plan([row('inserted',2,4)],10)['complete_finished_reel'] is True


def test_scorecard_explains_an_already_edited_source():
    from app.services.finished_reel_understanding import scorecard
    captioned={'semantic_context':{'existing_treatments':['burned_in_captions']}}
    skipped=dict(row('no_intervention',2,4),preserved_existing=True,**captioned)
    card=scorecard([skipped,dict(row('no_intervention',6,8),preserved_existing=True,**captioned)],10)
    assert card['outcome']=='complete_with_gaps' and card['preserved_existing']==2
    assert any('already edited' in r for r in card['reasons']) and any('burned-in captions' in r for r in card['reasons'])


def test_camera_cuts_count_as_on_screen_changes():
    from app.services.finished_reel_understanding import scorecard
    rows=[row('inserted',2,4)]
    assert scorecard(rows,20)['outcome']=='complete_with_gaps'
    paced=scorecard(rows,20,changes=[8,12,16])
    assert paced['outcome']=='complete' and paced['longest_static_sec']==4 and paced['camera_cuts']==3 and paced['visual_coverage']==.1
