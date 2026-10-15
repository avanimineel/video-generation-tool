from pathlib import Path
from PIL import Image,ImageDraw
from app.core.models import MotionGraphicItem
from app.core.config import settings
from app.services.subject_layers import mask_frame_path
from app.services.burnin_renderer import render_editorial_text,FontManager

def test_background_title_does_not_paint_over_person(monkeypatch,tmp_path):
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    assets=tmp_path/'fixture/assets';assets.mkdir(parents=True)
    inverse=Image.new('RGBA',(360,640),'white');ImageDraw.Draw(inverse).rectangle((140,0,220,640),fill=(255,255,255,0));inverse.save(assets/'subject_test_00000.png')
    g=MotionGraphicItem(id='g',title='PREVENTION',start=0,end=3,template_id='kinetic_typography',pos_x=.5,pos_y=.3,parameters={'title_style':'behind_subject','title_lines':[{'text':'PREVENTION','offset':0}],'subject_mask':{'prefix':'/api/media/fixture/asset/subject_test_','count':1,'fps':24,'start':0}})
    background=Image.new('RGB',(360,640),'#243548');result=background.copy();render_editorial_text(result,g,360,640,FontManager(),1)
    assert result.crop((140,0,220,640)).tobytes()==background.crop((140,0,220,640)).tobytes()
    assert result.tobytes()!=background.tobytes()
    assert mask_frame_path(g,100)==assets/'subject_test_00000.png'

def test_mask_path_cannot_escape_assets(monkeypatch,tmp_path):
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    g=MotionGraphicItem(id='g',title='x',start=0,end=1,template_id='kinetic_typography',parameters={'subject_mask':{'prefix':'/api/media/fixture/asset/../../secret','count':1,'fps':24,'start':0}})
    assert mask_frame_path(g,0) is None


def title(style='bold_pop',pos_y=.5):
    return MotionGraphicItem(id='t',title='A million',start=4,end=6,template_id='kinetic_typography',pos_y=pos_y,parameters={'title_style':style})


def test_head_band_is_measured_from_the_person_matte():
    from app.services.subject_layers import head_band_from_mask,face_safe_y
    mask=Image.new('L',(180,320),0);draw=ImageDraw.Draw(mask)
    draw.ellipse((60,64,120,150),fill=255);draw.rectangle((20,150,160,320),fill=255) # Head, then shoulders to the frame bottom.
    top,bottom=head_band_from_mask(mask)
    assert abs(top-.2)<.02 and .48<bottom<.52
    assert bottom<face_safe_y((top,bottom))<=.72 # Title sits below the head.
    assert head_band_from_mask(Image.new('L',(180,320),0)) is None
    assert face_safe_y((.3,.8))<.3 # Close-up: the title goes above the head.
    assert face_safe_y(None)==.68


def test_automatic_titles_move_off_the_face_but_manual_positions_stay(monkeypatch):
    from app.services import subject_layers
    monkeypatch.setattr(subject_layers,'speaker_head_band',lambda state,t:(.2,.5))
    moved,manual,behind=title(),title(pos_y=.3),title('behind_subject')
    subject_layers.place_titles_face_safe(object(),[moved,manual,behind])
    assert moved.pos_y==.59 and moved.parameters['face_safe']['head_band']==(.2,.5)
    assert manual.pos_y==.3 and behind.pos_y==.5
    monkeypatch.setattr(subject_layers,'speaker_head_band',lambda state,t:None)
    fallback=title();subject_layers.place_titles_face_safe(object(),[fallback])
    assert fallback.pos_y==.68 and fallback.parameters['face_safe']['basis']=='default lower third'


def test_cutaway_crop_centres_the_subject_not_the_frame():
    from app.services.subject_layers import subject_center,object_position
    wide=Image.new('RGB',(1600,900),(90,90,90));draw=ImageDraw.Draw(wide)
    for x in range(1180,1480,12):draw.line((x,250,x,650),fill='white',width=4) # Detailed subject on the right.
    cx,cy=subject_center(wide,matte=Image.new('L',(10,10),0))
    assert cx>.6 and .35<cy<.65
    pos_x,pos_y=object_position((cx,cy),wide.size,9/16)
    crop=900*9/16;left=pos_x*(1600-crop)
    assert left<cx*1600<left+crop and pos_y==.5 # The subject is inside the vertical crop.
    assert object_position((.5,.5),wide.size,9/16)==(.5,.5)
    assert object_position((.02,.5),wide.size,9/16)[0]==0 # Clamped at the frame edge.
    person=Image.new('L',(160,90),0);ImageDraw.Draw(person).ellipse((20,10,40,30),fill=255);ImageDraw.Draw(person).rectangle((10,30,50,90),fill=255)
    hx,hy=subject_center(wide,matte=person)
    assert hx<.3 and hy<.4 # A visible person's head wins over busy detail elsewhere.


def test_placed_stock_records_its_subject_crop(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from app.core.models import CaptionItem,WordTiming
    from app.services import editorial_planner as e, subject_layers
    asset=tmp_path/'clip.jpg';Image.new('RGB',(1600,900)).save(asset)
    selected=dict(provider='pexels',media_type='image',url='https://x.test/a',local=dict(media_url='/api/media/p/asset/downloaded/a.jpg',local_path=str(asset)))
    monkeypatch.setattr(e,'retrieve_asset',lambda *a:(selected,[]))
    seen=[]
    monkeypatch.setattr(subject_layers,'media_focus',lambda path,kind,aspect:seen.append(round(aspect,4)) or (.81,.5))
    text='I always work on my laptop at night'
    words=[WordTiming(word=w,start=4+i*.5,end=4.5+i*.5) for i,w in enumerate(text.split())]
    caps=[CaptionItem(id='c',start=4,end=10,text=text,words=words)]
    seg=e.Segment(id='segment-1',start_sec=0,end_sec=10,transcript=text,semantic_summary='Work habits')
    d=e.Decision(segment_id='segment-1',intervene=True,strategy='STOCK_IMAGE',rationale='Show the laptop',anchor_phrase='laptop',display_text='laptop',cue_kind='object',
                 start_sec=4,end_sec=10,composition={'layout':'fullscreen'},asset={'semantic_target':'laptop','retrieval_query':'laptop at night','alternate_queries':[],'required_entities':['laptop']},
                 scores={k:.95 for k in ['semantic_relevance','visual_value','information_gain','evidence_value','attention_value','confidence']}|dict(redundancy=.05,visual_fatigue=.05))
    rows=e.schedule([seg],[d],caps)
    graphics,_=e.execute_plan(SimpleNamespace(id='p',captions=caps,graphics=[]),rows,tmp_path)
    assert graphics[0].parameters['media_pos_x']==.81 and seen==[round(9/16,4)]
