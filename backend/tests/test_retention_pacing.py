from types import SimpleNamespace
from app.core.models import MotionGraphicItem
from app.services.retention_pacing import add_camera_beats

def test_each_gap_has_continuous_one_second_beats_without_touching_stock():
    stock=MotionGraphicItem(id='reviewed',start=3,end=5,template_id='split_screen_vertical',title='Stock',animation='none')
    before=stock.model_dump();state=SimpleNamespace(duration_seconds=10)
    result,audit=add_camera_beats(state,[stock])
    beats=[g for g in result if g.parameters.get('retention_camera')]
    assert len(beats)==8 and audit['camera_seconds']==8
    assert all(g.end-g.start<=1.001 for g in beats)
    assert all(g.end<=3 or g.start>=5 for g in beats)
    assert stock.model_dump()==before
    for left,right in zip(beats,beats[1:]):
        if left.end==right.start:
            assert left.parameters['end_scale']==right.parameters['start_scale']
    again,_=add_camera_beats(state,result)
    assert [g.model_dump() for g in again]==[g.model_dump() for g in result]

def test_manual_graphics_remain_uncovered_and_short_gap_is_pulse():
    manual=MotionGraphicItem(id='manual',start=.75,end=4,template_id='kinetic_typography',title='Exact words')
    result,_=add_camera_beats(SimpleNamespace(duration_seconds=4),[],[manual])
    assert len(result)==1 and result[0].end==.75
    assert result[0].parameters['motion_curve']=='pulse'

def test_export_pulse_moves_and_returns_to_original_frame():
    from PIL import Image
    from app.services.burnin_renderer import apply_source_reframe
    image=Image.new('RGB',(100,100))
    image.putdata([(x*2,y*2,0) for y in range(100) for x in range(100)])
    items,_=add_camera_beats(SimpleNamespace(duration_seconds=.8),[])
    assert apply_source_reframe(image,items,0).tobytes()==image.tobytes()
    assert apply_source_reframe(image,items,.4).tobytes()!=image.tobytes()
    assert apply_source_reframe(image,items,.8).tobytes()==image.tobytes()
