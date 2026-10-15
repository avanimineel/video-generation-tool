"""Cached, local ONNX person mattes for true behind-speaker compositing."""
import hashlib,json,math,subprocess,tempfile,threading
from pathlib import Path
from PIL import Image,ImageOps,ImageFilter
from app.core.config import settings

_BUILD_LOCK=threading.Lock()

def segmentation_session():
    import onnxruntime as ort
    ort.disable_telemetry_events()
    import requests
    from functools import lru_cache
    model=Path(__file__).resolve().parents[2]/'models/u2net_human_seg.onnx'
    with _BUILD_LOCK:
        if not model.is_file():
            model.parent.mkdir(parents=True,exist_ok=True)
            temporary=model.with_suffix('.download')
            try:
                with requests.get('https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx',stream=True,timeout=(15,120)) as response:
                    response.raise_for_status()
                    with temporary.open('wb') as output:
                        for chunk in response.iter_content(1024*1024):output.write(chunk)
                if hashlib.md5(temporary.read_bytes()).hexdigest()!='c09ddc2e0104f800e3e1bb4652583d1f':
                    raise ValueError('Speaker segmentation model checksum does not match the published model.')
                temporary.replace(model)
            finally:temporary.unlink(missing_ok=True)
    options=ort.SessionOptions();options.intra_op_num_threads=4
    return ort.InferenceSession(str(model),sess_options=options,providers=['CPUExecutionProvider'])

from functools import lru_cache
segmentation_session=lru_cache(maxsize=1)(segmentation_session)

def person_matte(image):
    """Greyscale person matte the size of the image, from the local segmentation model."""
    import numpy as np
    session=segmentation_session()
    rgb=np.asarray(image.convert('RGB').resize((320,320),Image.Resampling.LANCZOS),dtype=np.float32)
    rgb=rgb/max(float(rgb.max()),1e-6)
    normalized=(rgb-np.array([.485,.456,.406],dtype=np.float32))/np.array([.229,.224,.225],dtype=np.float32)
    prediction=session.run(None,{session.get_inputs()[0].name:normalized.transpose(2,0,1)[None].astype(np.float32)})[0][0,0]
    low,high=float(prediction.min()),float(prediction.max())
    matte=(prediction-low)/max(high-low,1e-6)
    return Image.fromarray(np.uint8(np.clip(matte,0,1)*255)).resize(image.size,Image.Resampling.LANCZOS)


def segment_frames(frames,masks):
    masks.mkdir(exist_ok=True)
    for file in sorted(frames.glob('*.png')):
        with Image.open(file) as image:
            person_matte(image).save(masks/file.name)

def prepare_subject_layer(state,graphic):
    source=Path(state.source_media_path or '')
    if not source.is_file(): raise ValueError('Original video is missing; relink it to prepare the speaker cutout.')
    fps=min(24,float(state.fps or 24));width,height=(360,640) if state.settings.aspect_ratio=='9:16' else (640,360)
    duration=max(.01,graphic.end-graphic.start)
    identity=f'{source.resolve()}:{source.stat().st_size}:{source.stat().st_mtime_ns}:{graphic.start}:{graphic.end}:{width}:{height}:{fps}:u2net-human-v2'
    digest=hashlib.sha256(identity.encode()).hexdigest()[:16]
    folder=settings.projects_dir/state.id/'assets';folder.mkdir(parents=True,exist_ok=True)
    prefix=f'subject_{digest}'
    metadata=folder/f'{prefix}.json'
    if metadata.exists():
        result=json.loads(metadata.read_text())
        if all((folder/f'{prefix}_{i:05d}.png').is_file() for i in range(result['count'])):
            graphic.parameters['subject_mask']=result;return result
    with tempfile.TemporaryDirectory(prefix='companion-matte-') as tmp:
        root=Path(tmp);frames=root/'frames';frames.mkdir();masks=root/'masks'
        subprocess.run([settings.ffmpeg_bin,'-v','error','-y','-ss',str(graphic.start),'-i',str(source),'-t',str(duration),'-vf',f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}','-start_number','0',str(frames/'%05d.png')],check=True,capture_output=True,timeout=90)
        segment_frames(frames,masks)
        files=sorted(masks.glob('*.png'))
        if not files:raise ValueError('No speaker masks were generated.')
        coverages=[]
        for i,file in enumerate(files):
            mask=Image.open(file).convert('L').resize((width,height),Image.Resampling.BILINEAR)
            hist=mask.histogram();coverage=sum(hist[128:])/(width*height);coverages.append(coverage)
            # Alpha stores the BACKGROUND: title is invisible wherever the person is.
            alpha=ImageOps.invert(mask).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.45)) if .03<coverage<.95 else Image.new('L',(width,height),0)
            inverse=Image.new('RGBA',(width,height),'white');inverse.putalpha(alpha);inverse.save(folder/f'{prefix}_{i:05d}.png')
        if not any(.03<v<.95 for v in coverages):raise ValueError('No reliable person silhouette detected; keep this title in front.')
        result={'prefix':f'/api/media/{state.id}/asset/{prefix}_','count':len(files),'fps':fps,'start':graphic.start,'width':width,'height':height,'source_fingerprint':digest,'quality':'u2net-human-local'}
        metadata.write_text(json.dumps(result,indent=2));graphic.parameters['subject_mask']=result
        return result


def prepare_subject_layers(state,graphics):
    for graphic in graphics:
        style = graphic.parameters.get('title_style')
        behind = bool(graphic.parameters.get('behind_subject'))
        template = getattr(graphic, 'template_id', '')
        if style not in ('behind_subject', 'cards_broll') and not behind and template not in ('behind_subject',):
            continue
        try:
            prepare_subject_layer(state,graphic);graphic.parameters.pop('subject_mask_error',None)
        except Exception as error:
            graphic.parameters['subject_mask_error']=str(error)[:250]
            graphic.parameters.pop('subject_mask',None)


def mask_frame_path(graphic,t):
    info=graphic.parameters.get('subject_mask') or {}
    if not info or not info.get('count'):return None
    from urllib.parse import urlparse
    index=min(info['count']-1,max(0,int((t-info.get('start',graphic.start))*info['fps'])))
    parts=urlparse(info['prefix']).path.split('/')
    if len(parts)!=6 or parts[1:3]!=['api','media'] or parts[4]!='asset':return None
    root=(settings.projects_dir/parts[3]/'assets').resolve()
    path=(root/f'{parts[5]}{index:05d}.png').resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


# Title styles drawn as a block over the picture. Styles that frame or sit behind
# the speaker (behind_subject, staircase, cards_broll, flame_subject) place themselves.
FACE_SAFE_STYLES=('editorial','rise','script','dual','typewriter','paper','bold_pop','cooked_badge','mixed_typography')
DEFAULT_TITLE_Y=.68


def speaker_head_band(state,t):
    """(top, bottom) of the speaker's head as fractions of frame height at time t, from the local person matte."""
    source=Path(getattr(state,'source_media_path',None) or '')
    if not source.is_file():return None
    portrait=getattr(getattr(state,'settings',None),'aspect_ratio','9:16')=='9:16'
    width,height=(180,320) if portrait else (320,180)
    try:
        with tempfile.TemporaryDirectory(prefix='companion-face-') as tmp:
            root=Path(tmp);frames=root/'frames';frames.mkdir();masks=root/'masks'
            subprocess.run([settings.ffmpeg_bin,'-v','error','-y','-ss',str(max(0,t)),'-i',str(source),'-frames:v','1','-vf',f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}',str(frames/'00000.png')],check=True,capture_output=True,timeout=30)
            segment_frames(frames,masks)
            with Image.open(masks/'00000.png') as image:mask=image.convert('L').resize((width,height),Image.Resampling.BILINEAR)
    except Exception:
        return None
    return head_band_from_mask(mask)


def head_band_from_mask(mask):
    width,height=mask.size;pixels=mask.load()
    rows=[y for y in range(height) if sum(pixels[x,y]>128 for x in range(width))>=width*.06]
    if not rows or rows[-1]-rows[0]<height*.2:return None
    top,bottom=rows[0],rows[-1]
    # Head and neck are roughly the top 38% of a seated, shoulders-up silhouette.
    return round(top/height,3),round((top+(bottom-top)*.38)/height,3)


def face_safe_y(band):
    if not band:return DEFAULT_TITLE_Y
    top,bottom=band
    # Never higher than the chest line: a head touching the frame top under-measures the band.
    if bottom+.09<=.72:return round(max(bottom+.09,.56),3)
    if top-.09>=.12:return round(top-.09,3)
    return .72


def place_titles_face_safe(state,titles):
    """Move centred automatic titles off the speaker's face; manual positions are left alone."""
    for graphic in titles:
        if graphic.parameters.get('behind_subject') or graphic.parameters.get('title_style') not in FACE_SAFE_STYLES or graphic.pos_y!=.5:continue
        band=speaker_head_band(state,(graphic.start+graphic.end)/2)
        graphic.pos_y=face_safe_y(band)
        graphic.parameters['face_safe']={'head_band':band,'basis':'u2net-human-local' if band else 'default lower third'}



def subject_center(image,matte=None):
    """(x, y) fractions of the main subject: a visible person's head, otherwise the most detailed region."""
    import numpy as np
    small=image.convert('RGB').resize((160,max(1,int(160*image.height/max(1,image.width)))),Image.Resampling.BILINEAR)
    if matte is None:
        try:matte=person_matte(small)
        except Exception:matte=None
    if matte is not None:
        person=np.asarray(matte.convert('L').resize(small.size,Image.Resampling.BILINEAR))>128
        if .02<person.mean()<.9:
            rows=np.where(person.any(axis=1))[0];top,bottom=rows[0],rows[-1]
            head=person[top:top+max(1,int((bottom-top)*.3))+1]
            ys,xs=np.nonzero(head)
            return round(float(xs.mean())/small.width,3),round(float(top+ys.mean())/small.height,3)
    gray=np.asarray(small.convert('L'),dtype=np.float32)
    energy=np.zeros_like(gray)
    energy[:,1:]+=np.abs(np.diff(gray,axis=1));energy[1:,:]+=np.abs(np.diff(gray,axis=0))
    threshold=float(np.percentile(energy,90))
    ys,xs=np.nonzero(energy>threshold if threshold>0 else energy>0)
    if not len(xs):return .5,.5
    # Lean a quarter of the way back to centre so one busy corner cannot pull the crop off the frame.
    return round(.75*float(xs.mean())/small.width+.125,3),round(.75*float(ys.mean())/small.height+.125,3)


def object_position(center,size,target_aspect):
    """The crop position (CSS object-position semantics, used by preview and export) that centres `center`."""
    width,height=size;cx,cy=center
    if width/height>target_aspect:
        crop=height*target_aspect
        return round(min(1,max(0,(cx*width-crop/2)/max(1e-6,width-crop))),3),.5
    crop=width/target_aspect
    return .5,round(min(1,max(0,(cy*height-crop/2)/max(1e-6,height-crop))),3)


def media_focus(path,media_type,target_aspect):
    """Crop position that keeps a cutaway's subject in the vertical frame, or None if the file cannot be read."""
    path=Path(path)
    try:
        if media_type=='video':
            with tempfile.TemporaryDirectory(prefix='companion-focus-') as tmp:
                still=Path(tmp)/'frame.png'
                subprocess.run([settings.ffmpeg_bin,'-v','error','-y','-ss','0.8','-i',str(path),'-frames:v','1',str(still)],check=True,capture_output=True,timeout=30)
                with Image.open(still) as image:return object_position(subject_center(image),image.size,target_aspect)
        with Image.open(path) as image:return object_position(subject_center(image),image.size,target_aspect)
    except Exception:
        return None
