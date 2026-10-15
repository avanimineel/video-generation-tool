from types import SimpleNamespace
import pytest
from app.services import editorial_planner as e

def test_alternate_queries_use_one_review_per_provider(monkeypatch,tmp_path):
    from app.services.media_search_service import media_search_service as media
    from app.services.asset_downloader import asset_downloader
    calls=[];reviews=[]
    def search(query,**kw):
        calls.append((kw['provider'],query))
        return [dict(id=query+str(i),url='https://example.test/'+query+str(i),title='Hospital in India',media_type='image') for i in range(10)]
    def review(pool,*args,**kwargs):
        reviews.append(pool)
        return pool[0],'matches'
    monkeypatch.setattr(media,'search_media',search)
    monkeypatch.setattr(media,'rerank_candidates_with_vision',review)
    asset=tmp_path/'local.jpg';asset.write_bytes(b'asset')
    monkeypatch.setattr(asset_downloader,'download_asset',lambda *a:dict(success=True,local_path=str(asset),media_url='/local.jpg'))
    row=dict(strategy='STOCK_IMAGE',intent='ILLUSTRATE',rationale='India setting',asset=dict(retrieval_query='india',alternate_queries=['clinic','hospital'],required_entities=[]))
    selected,attempts=e.retrieve_asset(row,'test',set())
    assert selected and len(calls)==3 and len(reviews)==1
    assert all(provider=='pexels' for provider,_ in calls)
    assert [x['id'] for x in reviews[0]][:3]==['india0','clinic0','hospital0']
    assert len(reviews[0])==8


def test_visual_review_request_budget(monkeypatch):
    monkeypatch.setattr(e,'configured_key',lambda *a:'fixture-credential')
    monkeypatch.setattr(e.time,'sleep',lambda *a:None)
    calls=[]
    def post(*a,**kw):
        calls.append(1)
        return SimpleNamespace(status_code=503,text='unavailable')
    monkeypatch.setattr(e.requests,'post',post)
    with pytest.raises(ValueError,match='budget exhausted'):
        e.gemini_json('review',max_requests=2)
    assert len(calls)==2


def stock_row(role='illustration'):
    return dict(strategy='STOCK_IMAGE',intent='ILLUSTRATE',rationale='Creator researching',visual_role=role,
                semantic_context=dict(transcript='videos on this topic',entities=['laptop']),
                asset=dict(retrieval_query='creator editing videos on laptop',alternate_queries=['content creator workflow desk','youtube creator researching'],required_entities=['desk']))


def test_specific_queries_lead_and_generic_entity_words_are_not_searched(monkeypatch):
    from app.services.media_search_service import media_search_service as media
    calls=[]
    monkeypatch.setattr(media,'search_media',lambda query,**kw:calls.append((kw['provider'],query)) or [])
    e.retrieve_asset(stock_row(),'test',set())
    pexels=[q for provider,q in calls if provider=='pexels']
    assert pexels==['creator editing videos on laptop','content creator workflow desk','youtube creator researching']
    calls.clear()
    e.retrieve_asset(stock_row('evidence'),'test',set())
    assert [q for provider,q in calls if provider=='pexels'][:2]==['laptop','desk'] # Named evidence still searches its entity first.


def test_rejected_video_search_is_not_retried_as_a_looser_image_search(monkeypatch,tmp_path):
    searches=[]
    monkeypatch.setattr(e,'retrieve_asset',lambda row,*a:searches.append(row['strategy']) or (None,[]))
    row=dict(stock_row(),strategy='BROLL_VIDEO',status='planned',segment_id='segment-1',composition={'layout':'fullscreen'},anchor_phrase='videos',
             timing_method='exact word timestamps',start_sec=5,end_sec=7,display_text='videos')
    graphics,_=e.execute_plan(SimpleNamespace(id='noretry',captions=[],graphics=[]),[row],tmp_path)
    assert searches==['BROLL_VIDEO'] and not graphics and row['status']=='rejected_assets'


def test_reviewer_rejects_a_pick_whose_required_subject_is_not_visible(monkeypatch):
    from io import BytesIO
    from PIL import Image
    from app.services.media_search_service import MediaSearchService
    service=MediaSearchService()
    buffer=BytesIO();Image.new('RGB',(32,32),'white').save(buffer,format='JPEG')
    monkeypatch.setattr('requests.get',lambda *a,**kw:SimpleNamespace(status_code=200,content=buffer.getvalue()+b'0'*100))
    monkeypatch.setattr(service.google_ai,'get_api_key',lambda:'fixture-credential')
    pool=[dict(id='rig',title='Camera on a tripod',thumb_url='https://example.test/a.jpg'),dict(id='desk',title='Desk',thumb_url='https://example.test/b.jpg')]
    answers=iter([dict(selected_index=0,confidence=.95,justification='Looks like a creator setup',required_subject_visible=False,missing=['earnings dashboard']),
                  dict(selected_index=0,confidence=.95,justification='Dashboard clearly visible',required_subject_visible=True,missing=[])])
    monkeypatch.setattr(e,'gemini_json',lambda *a,**kw:next(answers))
    rejected,reason=service.rerank_candidates_with_vision(pool,'YouTube earnings dashboard','youtube analytics',strict=True)
    assert rejected=={} and 'earnings dashboard' in reason
    accepted,_=service.rerank_candidates_with_vision(pool,'YouTube earnings dashboard','youtube analytics',strict=True)
    assert accepted['id']=='rig'


def test_pixabay_video_uses_the_thumbnail_the_api_returns(monkeypatch):
    from app.services.media_providers.pixabay import PixabayProvider
    provider=PixabayProvider(api_key='fixture-credential')
    hit=dict(id=7,duration=9,tags='youtube, creator',user='someone',user_id=1,
             videos=dict(large=dict(url='https://cdn.test/large.mp4',width=1920,height=1080,thumbnail='https://cdn.test/large.jpg'),
                         medium=dict(url='https://cdn.test/medium.mp4',width=1280,height=720,thumbnail='https://cdn.test/medium.jpg')))
    monkeypatch.setattr('requests.get',lambda *a,**kw:SimpleNamespace(status_code=200,json=lambda:{'hits':[hit]},raise_for_status=lambda:None,text='',headers={}))
    results=provider.search_videos('youtube creator',limit=3)
    assert results and results[0].thumb_url=='https://cdn.test/medium.jpg'
