from app.services.feedback_service import FeedbackService
from app.core.config import settings


def test_feedback_upsert_persists_and_is_project_scoped(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'projects_dir', tmp_path)
    service = FeedbackService()
    args = dict(project_id='one', cue_id='moment', decision='swap', reasoning='Use an injection close-up', strength=.8,
                graphic_type='missing_visual', start_sec=10, end_sec=15, search_query='', editor_notes='Show the action')
    first = service.record_decision(**args)
    args['editor_notes'] = 'Use a vial and syringe, not a hospital exterior'
    second = service.record_decision(**args)
    assert first['id'] == second['id']
    reloaded = FeedbackService()
    assert reloaded.planning_feedback('one')['decisions'][0]['editor_notes'] == args['editor_notes']
    assert len(reloaded.planning_feedback('one')['decisions']) == 1
    assert reloaded.planning_feedback('two')['decisions'] == []


def test_understanding_retries_truncated_json_without_accepting_partial(monkeypatch):
    from app.services.twelve_labs_service import twelve_labs_service as service
    from app.services import twelve_labs_service as module
    monkeypatch.setattr(service, '_get_api_key', lambda: 'fixture')
    prompts = []
    class Response:
        status_code = 200
        def json(self):
            return {'data': '[{"start_sec":' if len(prompts) == 1 else '[{"start_sec":0,"end_sec":20,"existing_treatments":["none"]}]'}
    def post(*args, **kwargs):
        prompts.append(kwargs['json']['prompt'])
        return Response()
    monkeypatch.setattr(module.requests, 'post', post)
    assert service.get_semantic_timeline('fixture', 'dialogue') == [{'start_sec':0,'end_sec':20,'existing_treatments':['none']}]
    assert len(prompts) == 2 and 'ENTIRE video' in prompts[1]


def test_understanding_recovers_timeout_using_same_asset(monkeypatch):
    from app.services.twelve_labs_service import twelve_labs_service as service
    from app.services import twelve_labs_service as module
    monkeypatch.setattr(service,'_get_api_key',lambda:'fixture')
    monkeypatch.setattr(module.time,'sleep',lambda _:None)
    calls=[]
    class Response:
        status_code=200
        def json(self):return {'data':'[{"existing_treatments":["none"]}]'}
    def post(*a,**kw):
        calls.append(kw)
        if len(calls)==1:raise module.requests.exceptions.ReadTimeout('slow')
        return Response()
    monkeypatch.setattr(module.requests,'post',post)
    assert service.get_semantic_timeline('already-uploaded','dialogue')
    assert len(calls)==2
    assert all(c['json']['video']['asset_id']=='already-uploaded' for c in calls)
    assert all(c['timeout']==(10,180) for c in calls)


def test_understanding_timeout_is_bounded_and_actionable(monkeypatch):
    import pytest
    from app.services.twelve_labs_service import twelve_labs_service as service
    from app.services import twelve_labs_service as module
    monkeypatch.setattr(service,'_get_api_key',lambda:'fixture')
    monkeypatch.setattr(module.time,'sleep',lambda _:None)
    calls=[]
    def post(*a,**kw):
        calls.append(kw);raise module.requests.exceptions.ReadTimeout('raw internal message')
    monkeypatch.setattr(module.requests,'post',post)
    with pytest.raises(ValueError,match='no re-upload is needed'):
        service.get_semantic_timeline('asset','dialogue')
    assert len(calls)==2


def test_understanding_does_not_retry_auth_failure(monkeypatch):
    import pytest
    from app.services.twelve_labs_service import twelve_labs_service as service
    from app.services import twelve_labs_service as module
    monkeypatch.setattr(service,'_get_api_key',lambda:'fixture')
    calls=[]
    class Response:status_code=401;text='Unauthorized'
    def post(*a,**kw):calls.append(kw);return Response()
    monkeypatch.setattr(module.requests,'post',post)
    with pytest.raises(ValueError,match='HTTP 401'):service.get_semantic_timeline('asset','dialogue')
    assert len(calls)==1


def test_global_and_project_guidance_are_both_used(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'projects_dir', tmp_path)
    svc = FeedbackService()
    svc.save_guidance('global', 'Use exact complete phrases')
    svc.save_guidance('one', 'This speaker is discussing recovery')
    guidance = svc.planning_feedback('one')['guidance']
    assert 'exact complete phrases' in guidance and 'discussing recovery' in guidance


def test_other_video_feedback_teaches_preferences_without_becoming_current_decisions(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'projects_dir', tmp_path)
    svc = FeedbackService()
    svc.record_decision('old', 'cue', 'cut', '', .8, 'title', 0, 3, '',
                        editor_notes='Never strip words out of a sentence')
    feedback = svc.planning_feedback('new')
    assert feedback['decisions'] == []
    assert feedback['cross_project_examples'][0]['project_id'] == 'old'
    assert 'strip words' in feedback['cross_project_examples'][0]['editor_notes']


def test_corrupt_feedback_is_not_silently_discarded(monkeypatch, tmp_path):
    import pytest
    monkeypatch.setattr(settings, 'projects_dir', tmp_path)
    svc = FeedbackService()
    svc.global_feedback_file.write_text('{broken')
    with pytest.raises(RuntimeError, match='refusing to edit'):
        svc.planning_feedback('one')


def test_concurrent_feedback_submissions_are_all_retained(monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(settings, 'projects_dir', tmp_path)
    svc = FeedbackService()
    def record(i):
        return svc.record_decision('one', str(i), 'cut', '', .8, 'title', i, i+1, '')
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(record, range(12)))
    assert len(svc.planning_feedback('one')['decisions']) == 12
