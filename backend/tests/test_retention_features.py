import io,zipfile,wave
from PIL import Image,ImageDraw
from app.core.models import MotionGraphicItem
from app.services.burnin_renderer import render_split_50_50,FontManager
from app.services.automatic_sfx import prepare_sfx
from app.core.config import settings

def graphic(**kw):
    return MotionGraphicItem(id='g',title='fixture',start=.2,end=1,template_id='split_screen_vertical',parameters={'editorial_generated':True,'media_url':'fixture'},**kw)

def test_split_still_image_is_identical_at_different_times():
    source=Image.new('RGB',(200,300),'blue');image=Image.new('RGB',(200,200),'white');ImageDraw.Draw(image).rectangle((0,0,60,60),fill='red')
    g=graphic(animation='slow_zoom_in')
    first=render_split_50_50(source,g,200,300,FontManager(),{'fixture':image},{},.25)
    last=render_split_50_50(source,g,200,300,FontManager(),{'fixture':image},{},.9)
    assert first.tobytes()==last.tobytes()

def test_sfx_is_local_quiet_and_full_length(monkeypatch,tmp_path):
    import numpy as np
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    gs=[graphic()];gs[0].parameters['highlight_animation']=True;path=prepare_sfx('fixture',gs,2)
    with wave.open(str(path)) as f:
        assert f.getnframes()==48000
        samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
        assert samples.max()>0 and abs(samples.astype(float)).max()<10000
        assert not samples[:4000].any()
    assert '/asset/automatic_sfx.wav' in gs[0].parameters['sfx_track_url']

def test_bulk_zip_contains_state_and_media_not_hidden_files(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import projects as api
    from app.core.models import ProjectState
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    state=ProjectState(id='fixture',name='Demo',created_at='now',updated_at='now')
    monkeypatch.setattr(api.project_manager,'get_project',lambda _:state)
    from app.services import auto_jobs
    monkeypatch.setattr(auto_jobs,'active',lambda _:False)
    root=tmp_path/'fixture';root.mkdir();(root/'clip.mp4').write_bytes(b'video');(root/'.env').write_text('secret')
    response=TestClient(app).post('/api/projects/bulk/download',json={'project_ids':['fixture']})
    assert response.status_code==200
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        assert 'fixture/project-state.json' in z.namelist()
        assert 'fixture/clip.mp4' in z.namelist()
        assert not any('.env' in n for n in z.namelist())
    assert TestClient(app).post('/api/projects/bulk/download',json={'project_ids':['../escape']}).status_code==400

def test_stock_is_silent_and_stale_track_is_removed(monkeypatch,tmp_path):
    monkeypatch.setattr(settings,'projects_dir',tmp_path)
    g=graphic();g.parameters.update(sfx_track_url='old.wav',sfx_cues=[{}])
    assert prepare_sfx('fixture',[g],2) is None
    assert 'sfx_track_url' not in g.parameters and 'sfx_cues' not in g.parameters

def test_sounds_match_actual_animation():
    from app.services.automatic_sfx import sound_cues
    gs=[]
    for index,style in enumerate(('rise','script','dual','paper','typewriter','bold_pop')):
        g=graphic();g.id=style;g.start=index;g.end=index+.8;g.template_id='kinetic_typography';g.parameters.update(title_style=style,headline='TEST')
        gs.append(g)
    cues=sound_cues(gs,7)
    assert {c['kind'] for c in cues}=={'paper','typewriter','pop'}
    assert not any(c['graphic_id'] in ('rise','script','dual') for c in cues)
    gs[0].parameters['highlight_animation']=True
    assert sound_cues(gs,7)[0]['kind']=='highlight'

def test_title_keeps_authored_words_and_no_invented_yes():
    from app.services.title_styles import arrange_title
    from app.core.models import CaptionItem
    g=graphic();g.parameters['headline']='Medicine costs';g.title='Medicine costs'
    arrange_title(g,'paper',[CaptionItem(id='c',start=0,end=2,text='A very long sentence about medicine costs today')])
    assert g.parameters['headline']=='Medicine costs'
    assert [w['text'] for w in g.parameters['timed_words']]==['Medicine','costs']
    g.parameters['headline']='Cost';arrange_title(g,'paper')
    assert len(g.parameters['title_lines'])==1


def test_title_pops_and_punch_in_whooshes_stay_sparse():
    from app.core.models import MotionGraphicItem
    from app.services.automatic_sfx import sound_cues
    def title(start):return MotionGraphicItem(id=f't{start}',start=start,end=start+1.5,template_id='kinetic_typography',title='x',parameters={'title_style':'editorial'})
    def punch(start):return MotionGraphicItem(id=f'p{start}',start=start,end=start+2,template_id='source_reframe',title='Punch-in',parameters={'motion_curve':'hold','retention_camera':True})
    cues=sound_cues([title(1),title(1.6),punch(3),title(8)],20)
    assert [(c['start'],c['kind']) for c in cues]==[(1,'pop'),(3,'whoosh'),(8,'pop')]


def test_cutaways_get_moves_and_hand_overs_that_fit():
    from app.core.models import MotionGraphicItem
    from app.services.cutaway_motion import choose_motion
    def cut(id_, start, end, kind='image', **p):
        return MotionGraphicItem(id=id_, start=start, end=end, template_id='youtube_insert', title=id_, placement_mode='insert', media_type=kind,
                                 parameters={'editorial_generated': True, **p})
    a = cut('a', 4, 6.5, media_pos_x=.8); b = cut('b', 6.8, 8.0); c = cut('c', 14, 16, 'video', cue_kind='action'); d = cut('d', 20, 21, 'video')
    choose_motion([d, c, b, a])
    assert (a.parameters['animation'], a.parameters['transition_in'], a.parameters['transition_out']) == ('push_in', 'dissolve', 'whip')
    assert (b.parameters['animation'], b.parameters['transition_in']) == ('pan_left', 'whip') or b.parameters['animation'] in ('pan_left', 'pan_right', 'tilt_up')
    assert b.parameters['transition_in'] == 'whip' # Back-to-back cutaways whip.
    assert (c.parameters['speed'], c.parameters['animation'], c.parameters['transition_in']) == ('speed_ramp', 'slow_zoom_in', 'dissolve')
    assert (d.parameters['speed'], d.parameters['transition_in']) == ('normal', 'cut') # Short cutaways cut.
    manual = cut('m', 30, 33, animation='pan_right', motion_chosen=True); choose_motion([manual])
    assert manual.parameters['animation'] == 'pan_right' and 'transition_in' not in manual.parameters # Editor choices are kept.


def test_camera_moves_speed_and_transitions_render():
    from PIL import Image, ImageDraw
    from app.services.burnin_renderer import apply_ken_burns, camera_pose, cutaway_time, transition_mix
    still = Image.new('RGB', (400, 300), 'gray'); ImageDraw.Draw(still).rectangle((180, 120, 220, 180), fill='red')
    frames = {m: apply_ken_burns(still, m, .5, 180, 320, seconds=1.0) for m in ('push_in', 'pan_left', 'tilt_up', 'crane_up', 'dutch', 'handheld')}
    assert all(f.size == (180, 320) for f in frames.values())
    assert camera_pose('pan_left', 0)[1] > camera_pose('pan_left', 1)[1] and camera_pose('tilt_up', 0)[2] > camera_pose('tilt_up', 1)[2]
    assert camera_pose('handheld', 0, 1.0) != camera_pose('handheld', 0, 1.3) and camera_pose('dutch', 1)[3] > camera_pose('dutch', 0)[3]
    assert cutaway_time('slow_motion', 2, 4) == 1 and cutaway_time('freeze_end', 3.9, 4) == cutaway_time('freeze_end', 3.0, 4)
    assert cutaway_time('speed_ramp', 1, 5) == 2 and cutaway_time('speed_ramp', 3, 5) < 5
    a, b = Image.new('RGB', (100, 100), 'black'), Image.new('RGB', (100, 100), 'white')
    assert transition_mix(a, b, 'dissolve', .5, True).getpixel((50, 50))[0] in range(110, 146)
    wipe = transition_mix(a, b, 'wipe', .5, True)
    assert wipe.getpixel((10, 50)) == (255, 255, 255) and wipe.getpixel((90, 50)) == (0, 0, 0)
    assert transition_mix(a, b, 'flash', 0, True).getpixel((50, 50))[0] > 200 and transition_mix(a, b, 'cut', .2, True) is a
