from app.core.models import ProjectState, CaptionItem
from app.services.quality_preview import phrase_captions,make_plan,compose,FontManager
from PIL import Image


def cap(start,end,text):return CaptionItem(id=str(start),start=start,end=end,text=text)

def test_fragments_rejoin_without_losing_words_or_filling_silence():
    captions=[cap(0,.4,'Cancer is increasing'),cap(.4,.8,'day'),cap(.8,2,'by day.'),cap(5,7,'A separate sentence.')]
    result=phrase_captions(captions,10)
    assert result[0]['text']=='Cancer is increasing day by day.'
    assert result[0]['end']==2 and result[1]['start']==5
    assert ' '.join(p['text'] for p in result)==' '.join(c.text for c in captions)


def test_phrase_boundaries_respect_grammar_and_preserve_order():
    captions=[cap(0,3,'Sumayana, you are absolutely right,'),cap(3,6,'In India, even now, many doctors,'),cap(6,9,'believe that young people cannot get cancer.')]
    result=phrase_captions(captions,10)
    assert all(not p['text'].lower().endswith((' in',' the',' a')) for p in result)
    assert result[0]['text']=='Sumayana, you are absolutely right,'
    assert ' '.join(p['text'] for p in result)==' '.join(c.text for c in captions)


def test_plan_is_non_destructive_and_frame_renders():
    project=ProjectState(id='sample',name='sample',created_at='x',updated_at='x',duration_seconds=8,captions=[cap(0,4,'A complete phrase.'),cap(4,8,'Another complete phrase.')])
    before=project.model_dump_json()
    plan=make_plan(project)
    assert project.model_dump_json()==before
    assert plan['width']==1080 and plan['duration']==8
    assert len(plan['pushes'])==1
    frame=compose(Image.new('RGB',(1080,1920),'gray'),plan,1,FontManager(),{})
    assert frame.size==(1080,1920)
    assert frame.getpixel((540,400))==(128,128,128)
    assert frame.getpixel((540,1540))!=(128,128,128)
