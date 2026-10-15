"""Cached original-language ASR anchors, separate from translated subtitles."""
import hashlib
import json
from pathlib import Path
from app.core.config import settings

def source_audio_cues(project_id, source):
    source=Path(source)
    # Translation changes caption words. Reuse the original speech audit only
    # when its video content hash matches, never the current translated timeline.
    native_path=settings.projects_dir/project_id/'transcription'/'native_source.json'
    if native_path.exists():
        native=json.loads(native_path.read_text())
        with source.open('rb') as stream:
            source_hash=hashlib.file_digest(stream,'sha256').hexdigest()
        if native.get('video_hash') == source_hash:
            from app.core.models import CaptionItem
            from app.services.transcript_quality import transcript_issues
            captions=[CaptionItem.model_validate(c) for c in native.get('captions',[])]
            if captions and not transcript_issues(captions):
                words=[]
                for caption in captions:
                    for word in caption.words:
                        words.append({'id':len(words),'word':word.word,'start':word.start,'end':word.end,
                                      'usable':word.end>word.start and caption.start<=word.start<caption.end})
                if any(w['usable'] for w in words):
                    return {'language':native.get('language','unknown'),
                            'basis':'saved original-language ASR; acoustic tolerance not independently verified',
                            'source':'transcription/native_source.json','words':words}
    stat=source.stat()
    digest=hashlib.sha256(f'{source.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:native-small-v1'.encode()).hexdigest()[:24]
    folder=settings.projects_dir/project_id/'alignment'
    path=folder/f'{digest}.json'
    if path.exists():
        return json.loads(path.read_text())
    from app.services.transcription_service import transcription_service
    language,captions=transcription_service.transcribe_with_whisper(str(source),task='transcribe',model_size='small',words_per_caption=3)
    words=[]
    for caption in captions:
        for word in caption.words:
            words.append({'id':len(words),'word':word.word,'start':word.start,'end':word.end,'usable':word.end>word.start})
    if not words:raise ValueError('Original-language ASR produced no word anchors')
    result={'language':language,'basis':'original-language Whisper ASR; acoustic tolerance not independently verified','words':words}
    folder.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False));temp.replace(path)
    return result
