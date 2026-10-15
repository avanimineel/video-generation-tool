from app.services.media_search_service import MediaSearchService

def test_named_people_still_try_primary_providers_and_never_generate(monkeypatch):
    s=MediaSearchService();calls=[]
    for name in ('pexels','pixabay','wikimedia'):
        def empty(*args, provider=name, **kwargs):calls.append(provider);return []
        monkeypatch.setattr(getattr(s,name),'search_images',empty)
    monkeypatch.setattr(s,'generate_ai_media',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('Recursive generation forbidden')))
    assert s.search_media('Lisa Ray')==[]
    assert calls==['pexels','pixabay','wikimedia']

def test_unreviewed_single_image_is_not_auto_inserted(monkeypatch):
    s=MediaSearchService()
    monkeypatch.setattr(s,'generate_search_queries',lambda _:['polio camp India'])
    monkeypatch.setattr(s,'search_media',lambda *a,**kw:[{'id':'wrong','url':'https://example.org/foreign.jpg'}])
    def reject(*a,**kw):
        assert kw['strict'] is True
        return {}, 'No documented Indian context'
    monkeypatch.setattr(s,'rerank_candidates_with_vision',reject)
    result=s.auto_match_for_caption('An Indian polio camp')
    assert result['media'] is None and result['status']=='needs_review'
    assert not result['source_citation']
