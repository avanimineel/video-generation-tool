"""Real upload/proxy/save/render path, with deterministic speech/planning fixtures.
External AI quality is deliberately NOT claimed by this integration test.
"""
import subprocess,time
from pathlib import Path
import av
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import init_db
from app.core.models import CaptionItem,WordTiming,MotionGraphicItem
from app.services import auto_jobs,editorial_planner
from app.services.transcription_service import transcription_service
from app.services.project_manager import project_manager
from app.services.proxy_generator import proxy_generator


def test_upload_through_render_preserves_audio_and_new_revision(monkeypatch,tmp_path):
    init_db();client=TestClient(app)
    clip=tmp_path/'raw.mp4'
    subprocess.run([settings.ffmpeg_bin,'-v','error','-y','-f','lavfi','-i','color=c=blue:s=180x320:r=10:d=2','-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t','2','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(clip)],check=True)
    monkeypatch.setattr(transcription_service,'transcribe_with_whisper',lambda *a,**kw:('en',[CaptionItem(id='speech',start=0,end=2,text='Exact spoken words',words=[WordTiming(word=w,start=i*.5,end=(i+1)*.5) for i,w in enumerate(['Exact','spoken','words'])])]))
    def plan(*a):
        g=MotionGraphicItem(id='title',start=.5,end=1.5,template_id='kinetic_typography',title='Exact spoken words',parameters={'headline':'Exact spoken words','title_style':'rise','editorial_generated':True,'sfx_muted':True})
        return [g],[],{'status':'complete','run_id':'fixture','errors':[]}
    monkeypatch.setattr(editorial_planner,'run_editorial',plan)
    p=client.post('/api/projects',json={'name':'workflow_fixture'}).json();pid=p['id']
    upload=client.post(f'/api/media/{pid}/upload',content=clip.read_bytes(),headers={'x-filename':'raw.mp4'})
    assert upload.status_code==200
    for _ in range(200):
        job=auto_jobs.status(pid)
        if job['status'] not in ('queued','running'):break
        time.sleep(.01)
    assert job['status']=='complete'
    saved=project_manager.get_project(pid)
    assert saved.captions[0].text=='Exact spoken words' and saved.graphics[0].id=='title'
    assert max(saved.waveform_data)==0 # Actual silent audio, not synthetic decoration.
    assert Path(saved.proxy_media_path).is_file()
    result=client.post(f'/api/media/{pid}/render-burnin',json={})
    assert result.status_code==200,result.text
    output=Path(result.json()['output_path']);container=av.open(str(output))
    assert {s.type for s in container.streams}=={'video','audio'}
    assert abs(container.duration/1e6-2)<.2
    frames=list(container.decode(video=0));container.close()
    assert len(frames)>=20 and frames[0].width>0
    assert client.post(f'/api/media/{pid}/render-burnin',json={}).json()['already_cached']
    saved.captions[0].text='Changed spoken words';project_manager.save_project(saved)
    # Cached file must no longer match after an edit; avoid a redundant second encode.
    from app.services.export_cache import cache_matches,fingerprint
    assert not cache_matches(output,fingerprint(saved,False))
    # Stale browser export is rejected, never silently rendered from older state.
    assert client.post(f'/api/media/{pid}/render-burnin',json={'project_state':p}).status_code==409
