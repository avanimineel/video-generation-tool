import hashlib,json
from types import SimpleNamespace
from app.services import audio_cue_alignment as a
from app.services.transcription_service import transcription_service
from app.core.models import CaptionItem,WordTiming


def test_matching_native_audit_avoids_second_asr(tmp_path,monkeypatch):
    source=tmp_path/'video.mov';source.write_bytes(b'video')
    audit=tmp_path/'p'/'transcription';audit.mkdir(parents=True)
    caption=CaptionItem(id='native',start=0,end=1,text='इलाज',words=[WordTiming(word='इलाज',start=0,end=1)])
    (audit/'native_source.json').write_text(json.dumps({'video_hash':hashlib.sha256(b'video').hexdigest(),'language':'hi','captions':[caption.model_dump()]}))
    monkeypatch.setattr(a,'settings',SimpleNamespace(projects_dir=tmp_path))
    def forbidden(*args,**kwargs):raise AssertionError('Second ASR was called')
    monkeypatch.setattr(transcription_service,'transcribe_with_whisper',forbidden)
    result=a.source_audio_cues('p',source)
    assert result['words'][0]['word']=='इलाज' and result['words'][0]['usable']
    assert result['source']=='transcription/native_source.json'


def test_different_video_never_reuses_native_audit(tmp_path,monkeypatch):
    source=tmp_path/'video.mov';source.write_bytes(b'new video')
    audit=tmp_path/'p'/'transcription';audit.mkdir(parents=True)
    (audit/'native_source.json').write_text(json.dumps({'video_hash':'different','captions':[]}))
    monkeypatch.setattr(a,'settings',SimpleNamespace(projects_dir=tmp_path))
    caption=CaptionItem(id='new',start=0,end=1,text='New',words=[WordTiming(word='New',start=0,end=1)])
    calls=[]
    def transcribe(*args,**kwargs):calls.append(1);return 'en',[caption]
    monkeypatch.setattr(transcription_service,'transcribe_with_whisper',transcribe)
    result=a.source_audio_cues('p',source)
    assert calls==[1] and result['words'][0]['word']=='New'
