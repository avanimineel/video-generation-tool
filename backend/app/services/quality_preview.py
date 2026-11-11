"""Versioned, non-destructive documentary previews. The MP4 is the preview and export."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib, json, math, re, subprocess, threading, time
import av
from PIL import Image, ImageDraw
from app.core.config import settings
from app.services.burnin_renderer import FontManager, crop_to_aspect, resolve_media_file

_pool = ThreadPoolExecutor(max_workers=1)
_lock = threading.Lock()
_jobs = {}
VERSION = 2


def phrase_captions(captions, duration):
    """Join old fragment boundaries, preserving spoken order and explicit silence gaps.

    Translated words use estimated timing, so this style deliberately reveals phrases,
    never pretending those timestamps are acoustic karaoke alignment.
    """
    sentences, pending = [], []
    for cap in sorted(captions, key=lambda c: c.start):
        if cap.start >= duration: break
        text = cap.translated_text or cap.text
        tokens = text.split()
        if pending and cap.start - pending[-1]['end'] > .65:
            sentences.append(pending); pending = []
        for i, token in enumerate(tokens):
            start = cap.start + (cap.end-cap.start)*i/max(1,len(tokens))
            end = min(duration, cap.start+(cap.end-cap.start)*(i+1)/max(1,len(tokens)))
            if start >= duration: break
            pending.append(dict(text=token,start=start,end=end))
            if re.search(r'[.!?]$', token):
                sentences.append(pending); pending=[]
    if pending: sentences.append(pending)
    phrases=[]
    for sentence in sentences:
        # Minimize awkward grammatical breaks rather than cutting every N words.
        n=len(sentence); costs=[float('inf')]*(n+1); cuts=[0]*(n+1);costs[n]=0
        bad_end={'a','an','the','in','of','to','its','our','this','that','is','are','gen','one','accelerated','previous'}
        for i in range(n-1,-1,-1):
            for j in range(i+1,min(n,i+9)+1):
                count=j-i; last=sentence[j-1]['text'].lower().strip(',.!?')
                cost=(count-6)**2*.35 + (18 if count<3 and n>3 else 0)
                if j<n:
                    cost+=16 if last in bad_end else 0
                    if re.search(r'[,;:]$',sentence[j-1]['text']):cost-=5
                score=cost+costs[j]
                if score<costs[i]:costs[i]=score;cuts[i]=j
        i=0
        while i<n:
            j=cuts[i];words=sentence[i:j]
            phrases.append(dict(start=words[0]['start'],end=words[-1]['end'],text=' '.join(w['text'] for w in words)))
            i=j
    return phrases


def make_plan(project, duration=30):
    duration=min(duration,project.duration_seconds)
    boundaries=[c.end for c in project.captions if c.end<=duration and re.search(r'[.!?]$',c.translated_text or c.text)]
    if boundaries and boundaries[-1] > duration-5: duration=boundaries[-1]
    phrases=phrase_captions(project.captions,duration)
    scenes=[]
    for g in project.graphics:
        if g.start>=duration: continue
        raw=g.parameters.get('media_url') or g.media_url
        if raw and g.template_id in ('youtube_insert','split_screen_vertical'):
            path=resolve_media_file(raw,project.id,settings.projects_dir/project.id/'media'/'downloaded')
            if path and path.exists():
                scenes.append(dict(kind='broll',start=g.start,end=min(g.end,duration),path=str(path),source=g.source_name or 'Stock footage',source_url=g.source_url,license=g.license))
        elif g.template_id=='kinetic_typography':
            title=g.parameters.get('headline') or g.title
            if 2<=len(title.split())<=5 and not re.search(r'\b(is|are|the|a|and|of|to)\s*$',title,re.I):
                scenes.append(dict(kind='concept',start=g.start,end=min(duration,max(g.end,g.start+3)),text=title))
    # Subtle pushes at sentence starts, not a repeating three-second metronome.
    pushes=[]
    for p in phrases:
        if not pushes or p['start']-pushes[-1]['start']>=9:
            pushes.append(dict(start=p['start'],end=min(duration,p['start']+5),amount=.055))
    return dict(version=VERSION,style='medical_documentary',duration=duration,width=1080,height=1920,fps=30,
                captions=phrases,scenes=scenes,pushes=pushes,timing='phrase timing estimated from existing caption boundaries',
                source_revision=project.updated_at,source_path=project.source_media_path)


def wrap(text, font, max_width):
    lines=[]; line=''
    for word in text.split():
        test=(line+' '+word).strip()
        if font.getlength(test)>max_width and line: lines.append(line);line=word
        else: line=test
    if line: lines.append(line)
    return lines


class Clip:
    def __init__(self,path):
        self.container=av.open(path); self.stream=self.container.streams.video[0]
        self.frames=self.container.decode(self.stream); self.next=None; self.last=None
        self.origin=float(self.stream.start_time or 0)*float(self.stream.time_base)
    def at(self,t):
        while self.next is None or self.next[0]<=t:
            if self.next: self.last=self.next[1]
            try:
                frame=next(self.frames)
                self.next=(float(frame.time or 0)-self.origin,frame.to_image())
            except StopIteration: break
        return self.last or (self.next[1] if self.next else None)
    def close(self): self.container.close()


def compose(base,plan,t,fonts,clips):
    w,h=plan['width'],plan['height']; s=w/1080
    # Motion eases in/out and returns between sections; never compounds crops.
    zoom=1
    for push in plan['pushes']:
        if push['start']<=t<push['end']:
            u=(t-push['start'])/(push['end']-push['start'])
            zoom=1+push['amount']*math.sin(math.pi*u)**2
    base=crop_to_aspect(base,w,h)
    if zoom>1:
        dx=int(w*(1-1/zoom)/2);dy=int(h*(1-1/zoom)/2)
        base=base.crop((dx,dy,w-dx,h-dy)).resize((w,h),Image.Resampling.LANCZOS)
    canvas=base.convert('RGB'); d=ImageDraw.Draw(canvas)
    scene=next((v for v in plan['scenes'] if v['kind']=='broll' and v['start']<=t<v['end']),None)
    if scene:
        image=clips[scene['path']].at(t-scene['start'])
        if image:
            canvas=Image.new('RGB',(w,h),'#F2F0E9');d=ImageDraw.Draw(canvas)
            canvas.paste(crop_to_aspect(image,int(w*.92),int(h*.47)),(int(w*.04),int(h*.04)))
            canvas.paste(crop_to_aspect(base,w,int(h*.47),focus_y=.35),(0,int(h*.53)))
            d.text((w*.06,h*.515),'ILLUSTRATIVE FOOTAGE',font=fonts.get_font('bold',int(22*s)),fill='#285F5B',anchor='lm')
    # One stable caption size and baseline across every scene.
    phrase=next((p for p in plan['captions'] if p['start']<=t<p['end']),None)
    if phrase:
        font=fonts.get_font('bold',int(54*s)); lines=wrap(phrase['text'],font,w*.84)
        line_h=int(69*s); top=int(h*(.925 if scene else .805))-len(lines)*line_h//2
        overlay=Image.new('RGBA',(w,h));od=ImageDraw.Draw(overlay)
        for i,line in enumerate(lines):
            tw=font.getlength(line); y=top+i*line_h
            od.rounded_rectangle((w/2-tw/2-22*s,y-9*s,w/2+tw/2+22*s,y+59*s),radius=int(10*s),fill=(13,27,32,228))
            od.text((w/2,y),line,font=font,anchor='mt',fill='#FFFFFF')
        canvas=Image.alpha_composite(canvas.convert('RGBA'),overlay).convert('RGB')
    concept=next((v for v in plan['scenes'] if v['kind']=='concept' and v['start']<=t<v['end']),None)
    if concept and not scene:
        u=min(1,(t-concept['start'])/.35); eased=1-(1-u)**3
        overlay=Image.new('RGBA',(w,h));od=ImageDraw.Draw(overlay)
        y=h*.625+(1-eased)*35*s
        od.rounded_rectangle((w*.06,y,w*.94,y+180*s),radius=int(18*s),fill=(241,239,231,round(248*eased)))
        od.rectangle((w*.06,y+24*s,w*.068,y+156*s),fill='#2B7168')
        od.text((w*.1,y+28*s),'KEY CONCEPT',font=fonts.get_font('bold',int(22*s)),fill='#2B7168')
        font=fonts.get_font('bold',int(48*s))
        lines=wrap(concept['text'].capitalize(),font,w*.8)
        for i,line in enumerate(lines[:2]):od.text((w*.1,y+(67+i*53)*s),line,font=font,fill='#142E34')
        canvas=Image.alpha_composite(canvas.convert('RGBA'),overlay).convert('RGB')
    return canvas


def render(project,plan,folder,progress=lambda _:None):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'scene-plan.json').write_text(json.dumps(plan,indent=2))
    (folder/'source-project.json').write_text(project.model_dump_json(indent=2))
    target=folder/'preview.mp4'; temporary=folder/'rendering.mp4'
    source=Path(project.source_media_path or '')
    if not source.is_absolute():source=settings.projects_dir/project.id/source
    clips={}; main=None; proc=None
    try:
        main=Clip(str(source))
        for scene in plan['scenes']:
            if scene['kind']=='broll' and scene['path'] not in clips:clips[scene['path']]=Clip(scene['path'])
        ff=settings.ffmpeg_bin
        from app.services.ffmpeg_encoder import resolve_video_encoder
        _codec,codec,_reason=resolve_video_encoder(ff,bitrate='10M',crf='19',probe_size=(1080,1920))
        with (folder/'render.log').open('w') as log:
            proc=subprocess.Popen([ff,'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f"{plan['width']}x{plan['height']}",'-r',str(plan['fps']),'-i','pipe:0','-i',str(source),'-map','0:v','-map','1:a?','-t',str(plan['duration']),*codec,'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(temporary)],stdin=subprocess.PIPE,stderr=log)
            fonts=FontManager(); total=math.ceil(plan['duration']*plan['fps'])
            for n in range(total):
                t=n/plan['fps'];base=main.at(t)
                if base is None:raise ValueError('Source video has no decodable frames')
                frame=compose(base,plan,t,fonts,clips)
                proc.stdin.write(frame.tobytes())
                if n%30==0:progress(round(100*n/total))
            proc.stdin.close();code=proc.wait()
            if code:raise RuntimeError(f'Render failed ({code}); see render.log')
        temporary.replace(target)
        return target
    finally:
        if proc and proc.poll() is None:proc.kill();proc.wait()
        if main:main.close()
        for clip in clips.values():clip.close()


def start(project):
    if not project.captions:raise ValueError('Generate captions before creating a style preview.')
    plan=make_plan(project)
    key=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()[:16]
    folder=settings.projects_dir/project.id/'quality'/key
    with _lock:
        if (folder/'preview.mp4').exists():
            _jobs[project.id]=dict(status='complete',revision=key,percent=100);return _jobs[project.id]
        if _jobs.get(project.id,{}).get('status')=='rendering':return _jobs[project.id]
        job=dict(status='rendering',revision=key,percent=0);_jobs[project.id]=job
    def work():
        try:
            render(project,plan,folder,lambda p:job.update(percent=p))
            job.update(status='complete',percent=100)
        except Exception as e:job.update(status='failed',error=str(e))
    _pool.submit(work)
    return job


def status(project_id):
    if project_id in _jobs:return dict(_jobs[project_id])
    folder=settings.projects_dir/project_id/'quality'
    complete=sorted(folder.glob('*/preview.mp4'),key=lambda p:p.stat().st_mtime,reverse=True)
    return dict(status='complete',revision=complete[0].parent.name,percent=100) if complete else dict(status='not_run')
