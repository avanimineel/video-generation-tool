import time
from threading import Event
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db
from app.services.project_manager import project_manager
from app.core.models import CaptionItem,MotionGraphicItem
from app.services import auto_jobs
from app.services.auto_production_service import auto_production_service
from app.services.proxy_generator import proxy_generator

client=TestClient(app)
def new_project(name):
    init_db()
    return client.post('/api/projects',json={'name':name}).json()

def test_stale_autosave_cannot_erase_generated_captions():
    old=new_project('stale_save_regression')
    state=project_manager.get_project(old['id']);state.captions=[CaptionItem(id='new',start=0,end=1,text='Saved speech')];project_manager.save_project(state)
    response=client.post(f"/api/projects/{state.id}/autosave",json=old)
    assert response.status_code==409
    assert project_manager.get_project(state.id).captions[0].text=='Saved speech'
    latest=client.get(f'/api/projects/{state.id}').json();latest['captions'][0]['text']='Edited speech'
    assert client.post(f'/api/projects/{state.id}/autosave',json=latest).status_code==200

def test_upload_starts_one_server_owned_job_and_preserves_old_media(monkeypatch):
    old=new_project('upload_job_regression');pid=old['id'];started=Event();release=Event();calls=[]
    def pipeline(project_id,force,model_size):
        calls.append(project_id);started.set();assert release.wait(5)
        p=project_manager.get_project(project_id);p.captions=[CaptionItem(id='generated',start=0,end=1,text='Uploaded speech')];project_manager.save_project(p)
        return {'success':True,'project':p.model_dump()}
    monkeypatch.setattr(auto_production_service,'run_pipeline',pipeline)
    monkeypatch.setattr(proxy_generator,'extract_waveform_and_duration',lambda path:(3,[]))
    monkeypatch.setattr(proxy_generator,'generate_proxy',lambda *a:{'success':False})
    result=client.post(f'/api/media/{pid}/upload',content=b'test video',headers={'x-filename':'source.mp4'})
    assert result.status_code==200 and started.wait(2)
    try:
        assert client.post(f'/api/projects/{pid}/autosave',json=old).status_code==409
        assert client.post(f'/api/media/{pid}/auto-produce',json={}).json()['job']['status']=='running'
        assert len(calls)==1
    finally:release.set()
    for _ in range(100):
        job=auto_jobs.status(pid)
        if job['status']=='complete':break
        time.sleep(.01)
    assert job['status']=='complete' and job['result']['project']['captions'][0]['text']=='Uploaded speech'
    assert 'source.mp4' in job['result']['project']['source_media_path']

def test_source_zoom_changes_pixels_and_keeps_output_size():
    from PIL import Image,ImageDraw
    from app.services.burnin_renderer import apply_source_reframe
    img=Image.new('RGB',(100,160),'black');ImageDraw.Draw(img).rectangle((25,40,75,120),fill='white')
    g=MotionGraphicItem(id='camera',start=0,end=3,template_id='source_reframe',title='Zoom',parameters={'start_scale':1,'end_scale':1.13})
    a=apply_source_reframe(img,[g],0);b=apply_source_reframe(img,[g],3)
    assert a.size==b.size==(100,160) and a.tobytes()!=b.tobytes()


def test_blocked_graphics_are_not_reported_complete(monkeypatch):
    p=new_project('blocked_graphics_regression')
    result={'success':True,'project':p,'editorial_report':{'status':'blocked','errors':['Planner HTTP 503']}}
    monkeypatch.setattr(auto_production_service,'run_pipeline',lambda *args:result)
    auto_jobs.start(p['id'])
    for _ in range(100):
        job=auto_jobs.status(p['id'])
        if job['status'] not in ('queued','running'):break
        time.sleep(.01)
    assert job['status']=='needs_attention'
    assert job['error']=='Planner HTTP 503'
    assert job['result']['project']==p


def test_new_upload_uses_local_english_without_cloud_translation(monkeypatch,tmp_path):
    p=new_project('local_english_upload')
    state=project_manager.get_project(p['id'])
    source=tmp_path/'speech.mov';source.write_bytes(b'fixture')
    state.source_media_path=str(source);state.duration_seconds=5
    project_manager.save_project(state)
    calls=[]
    from app.services.transcription_service import transcription_service
    from app.services.translation_service import translation_service
    from app.services import editorial_planner
    def transcribe(*args,**kwargs):
        calls.append(kwargs)
        return 'en',[CaptionItem(id='spoken',start=0,end=2,text='Actual translated speech',translated_text='Actual translated speech')]
    monkeypatch.setattr(transcription_service,'transcribe_with_whisper',transcribe)
    monkeypatch.setattr(translation_service,'translate_captions_list',lambda *a:(_ for _ in ()).throw(AssertionError('English must not require cloud translation')))
    monkeypatch.setattr(editorial_planner,'run_editorial',lambda *a:([],[],{'status':'blocked','run_id':'offline-test','errors':['Cloud unavailable']}))
    result=auto_production_service.run_pipeline(state.id)
    assert calls[0]['task']=='transcribe'
    assert result['project']['captions'][0]['translated_text']=='Actual translated speech'
    assert result['editorial_report']['status']=='blocked'


def test_export_dispatches_render_off_api_event_loop(monkeypatch):
    from app.api import media
    p=new_project('export_thread_regression')
    calls=[]
    async def dispatch(fn,*args,**kwargs):
        calls.append(fn)
        return {'success':True,'output_path':'/tmp/test.mp4','file_size':123}
    monkeypatch.setattr(media,'run_in_threadpool',dispatch)
    response=client.post(f"/api/media/{p['id']}/render-burnin",json={'force_rerender':True})
    assert response.status_code==200
    assert calls==[media.burnin_renderer.render_burned_video]


def test_finished_reference_is_not_processed_as_raw(monkeypatch,tmp_path):
    from app.services import finished_reel_understanding as f
    p=new_project('finished_reference_guard')
    state=project_manager.get_project(p['id'])
    source=tmp_path/'reference.mov';source.write_bytes(b'fixture reference')
    state.source_media_path=str(source);project_manager.save_project(state)
    monkeypatch.setattr(f,'source_role',lambda **kw:'finished_reference')
    before=project_manager.get_project(p['id']).model_dump()
    result=auto_production_service.run_pipeline(p['id'],True)
    assert not result['success'] and 'finished reference' in result['error']
    assert project_manager.get_project(p['id']).model_dump()==before


def test_feedback_cut_during_generation_is_not_overwritten(monkeypatch, tmp_path):
    from app.services import editorial_planner
    from app.core.models import MotionGraphicItem
    p=new_project('concurrent_cut')
    state=project_manager.get_project(p['id'])
    source=tmp_path/'source.mov';source.write_bytes(b'fixture')
    state.source_media_path=str(source);state.duration_seconds=5
    state.captions=[CaptionItem(id='spoken',start=0,end=5,text='Actual English speech',translated_text='Actual English speech')]
    state.graphics=[MotionGraphicItem(id='old-generated',start=1,end=3,template_id='kinetic_typography',title='Actual English speech',parameters={'editorial_generated':True})]
    project_manager.save_project(state)
    def plan(*args):
        latest=project_manager.get_project(state.id)
        latest.graphics=[]  # User cuts an AI item while the new job is running.
        project_manager.save_project(latest)
        return [], [], {'status':'complete','run_id':'conflict-test','errors':[]}
    monkeypatch.setattr(editorial_planner,'run_editorial',plan)
    result=auto_production_service.run_pipeline(state.id,True)
    assert result['editorial_report']['status']=='conflict'
    assert project_manager.get_project(state.id).graphics==[]


def test_hindi_upload_retains_native_speech_and_blocks_graphics_if_translation_fails(monkeypatch,tmp_path):
    from app.services.transcription_service import transcription_service
    from app.services.translation_service import translation_service
    from app.services import editorial_planner
    p=new_project('native_hindi')
    state=project_manager.get_project(p['id'])
    source=tmp_path/'hindi.mov';source.write_bytes(b'fixture')
    state.source_media_path=str(source);state.duration_seconds=5
    project_manager.save_project(state)
    def transcribe(*args,**kwargs):
        assert kwargs['task']=='transcribe'
        return 'hi',[CaptionItem(id='native',start=0,end=3,text='मेरी जीभ',source_language='hi')]
    monkeypatch.setattr(transcription_service,'transcribe_with_whisper',transcribe)
    monkeypatch.setattr(translation_service,'translate_captions_list',lambda *a,**kw:(_ for _ in ()).throw(ValueError('Provider unavailable')))
    monkeypatch.setattr(editorial_planner,'run_editorial',lambda *a:(_ for _ in ()).throw(AssertionError('Do not plan from untranslated speech')))
    result=auto_production_service.run_pipeline(state.id,True)
    assert not result['success'] and result['editorial_report']['stage']=='translation'
    assert result['project']['captions'][0]['text']=='मेरी जीभ'


def test_corrupt_saved_transcript_retries_stronger_model_before_translation(monkeypatch,tmp_path):
    p=new_project('corrupt_speech_recovery')
    state=project_manager.get_project(p['id'])
    source=tmp_path/'speech.mov';source.write_bytes(b'corrupt-recovery-fixture')
    state.source_media_path=str(source);state.duration_seconds=5;state.detected_language='hi'
    state.captions=[CaptionItem(id='corrupt',start=0,end=1,text='॑')]
    project_manager.save_project(state)
    from app.services.transcription_service import transcription_service
    from app.services.translation_service import translation_service
    from app.services import editorial_planner
    calls=[]
    def transcribe(*a,**kw):
        calls.append(kw['model_size'])
        return 'hi',[CaptionItem(id='repaired',start=0,end=2,text='कैंसर का इलाज')]
    def translate(captions, **kwargs):
        assert captions[0].text=='कैंसर का इलाज'
        captions[0].translated_text='Treatment for cancer'
        return captions
    monkeypatch.setattr(transcription_service,'transcribe_with_whisper',transcribe)
    monkeypatch.setattr(translation_service,'translate_captions_list',translate)
    monkeypatch.setattr(editorial_planner,'run_editorial',lambda *a:([],[],{'status':'blocked','run_id':'offline-test','errors':['Cloud unavailable']}))
    result=auto_production_service.run_pipeline(state.id)
    assert calls==['medium']
    assert result['project']['captions'][0]['translated_text']=='Treatment for cancer'


def test_conflicting_job_is_not_reported_complete(monkeypatch):
    p=new_project('job_conflict')
    monkeypatch.setattr(auto_production_service,'run_pipeline',lambda *a:{'success':True,'project':p,'editorial_report':{'status':'conflict','stage':'subtitles','errors':['Timeline changed']}})
    auto_jobs.start(p['id'])
    for _ in range(100):
        job=auto_jobs.status(p['id'])
        if job['status'] not in ('queued','running'):break
        time.sleep(.01)
    assert job['status']=='needs_attention' and job['stage']=='subtitles'


def test_skipped_ideas_do_not_flag_a_successful_edit(monkeypatch):
    p=new_project('skipped_ideas')
    outcomes=[]
    for inserted in (4,0):
        report={'status':'complete','stage':'timeline_ready','errors':[],'inserted':inserted,'needs_review':2}
        monkeypatch.setattr(auto_production_service,'run_pipeline',lambda *a,report=report:{'success':True,'project':p,'editorial_report':report})
        auto_jobs.start(p['id'])
        for _ in range(100):
            job=auto_jobs.status(p['id'])
            if job['status'] not in ('queued','running'):break
            time.sleep(.01)
        outcomes.append(job['status'])
    assert outcomes==['complete','needs_attention']
