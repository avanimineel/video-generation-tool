from PIL import Image
from app.core.models import MotionGraphicItem
from app.services.burnin_renderer import render_editorial_text, FontManager

def test_phrase_reveal_changes_smoothly_and_second_line_waits():
    g=MotionGraphicItem(id='title',start=10,end=14,template_id='kinetic_typography',title='Hectic postings are still left',pos_x=.5,pos_y=.5,parameters={'title_lines':[{'text':'Hectic postings','offset':0},{'text':'are still left','offset':1.84}],'contrast_block':False,'title_reveal_seconds':.45})
    fonts=FontManager()
    def frame(t):
        im=Image.new('RGBA',(540,960),(0,0,0,0));render_editorial_text(im,g,540,960,fonts,t);return im
    assert frame(10).getbbox() is None
    early=[frame(10+i/30).tobytes() for i in range(1,13)]
    assert len(set(early))==12
    first=frame(11).getbbox(); both=frame(12.5).getbbox()
    assert both[3]>first[3]
    assert frame(14).getbbox() is None


def test_long_boxed_title_stays_inside_its_card_in_the_export():
    def white_columns(text):
        g=MotionGraphicItem(id='t',start=0,end=4,template_id='kinetic_typography',title=text,pos_x=.5,pos_y=.5,
                            parameters={'title_style':'bold_pop','title_lines':[{'text':text,'offset':0}],'headline':text})
        im=Image.new('RGBA',(540,960),(0,0,0,0));render_editorial_text(im,g,540,960,FontManager(),2)
        columns=[x for x in range(540) if any(im.getpixel((x,y))[:3]==(255,255,255) and im.getpixel((x,y))[3]>200 for y in range(380,580,2))]
        assert columns,'title text was not drawn'
        return min(columns),max(columns)
    card_left,card_right=270-int(540*.88)//2,270+int(540*.88)//2
    for text in ('Brand deals','a million subscribers.','eight business models','ten thousand one hundred thousand subscribers'):
        left,right=white_columns(text)
        assert card_left<left and right<card_right,(text,left,right)


def test_editorial_title_sets_short_lines_and_accents_the_key_word():
    from app.services.title_styles import arrange_title,accent_words,editorial_lines
    assert accent_words('there are eight business models'.split())==['eight']
    assert accent_words('a million subscribers'.split())==['million']
    assert accent_words('make money on YouTube'.split())==['youtube']
    assert accent_words(['Brand','deals'])==['brand']
    g=MotionGraphicItem(id='t',start=0,end=4,template_id='kinetic_typography',title='there are eight business models',parameters={'headline':'there are eight business models'})
    arrange_title(g,'editorial')
    assert [l['text'] for l in g.parameters['title_lines']]==['there are','eight','business','models'] or all(len(l['text'])<=13 for l in g.parameters['title_lines'])
    assert ' '.join(l['text'] for l in g.parameters['title_lines'])=='there are eight business models' # No word lost or invented.
    assert g.parameters['accent_words']==['eight'] and g.parameters['title_style']=='editorial'


def test_editorial_title_exports_white_text_with_a_gold_accent_and_no_box():
    from app.services.title_styles import arrange_title
    g=MotionGraphicItem(id='t',start=0,end=4,template_id='kinetic_typography',title='a million subscribers',pos_x=.5,pos_y=.6,parameters={'headline':'a million subscribers'})
    arrange_title(g,'editorial')
    im=Image.new('RGBA',(540,960),(40,60,90,255));render_editorial_text(im,g,540,960,FontManager(),3)
    pixels=[im.getpixel((x,y)) for x in range(0,540,2) for y in range(480,680,2)]
    assert any(p[0]>235 and p[1]>235 and p[2]>235 for p in pixels) # White sans words.
    assert any(p[0]>235 and 190<p[1]<230 and p[2]<130 for p in pixels) # Gold accent word.
    assert im.getpixel((20,576))[:3]==(40,60,90) and im.getpixel((520,576))[:3]==(40,60,90) # No card behind the text.
    hidden=Image.new('RGBA',(540,960),(40,60,90,255));render_editorial_text(hidden,g,540,960,FontManager(),0)
    assert hidden.tobytes()==Image.new('RGBA',(540,960),(40,60,90,255)).tobytes() # Words arrive with the speech.


def test_spoken_figures_count_up_as_they_land():
    from app.services.burnin_renderer import counting_number,COUNT_UP_SECONDS
    assert counting_number('100,000,',0)=='0,'
    middle=counting_number('100,000,',COUNT_UP_SECONDS/2)
    assert middle.endswith(',') and 50000<int(middle.rstrip(',').replace(',',''))<100000
    assert counting_number('100,000,',COUNT_UP_SECONDS)=='100,000,'
    assert counting_number('2.5',COUNT_UP_SECONDS)=='2.5' and counting_number('100%',0)=='0%'
    assert counting_number('2009',0)=='2009' and counting_number('subscribers',0)=='subscribers' # Years and words do not count.
