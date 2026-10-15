import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db
from app.services.fusion_templates import fusion_generator

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'healthy'

def test_project_lifecycle_and_persistence():
    # 1. Create project
    create_res = client.post('/api/projects', json={'name': 'Podcast_James_01', 'aspect_ratio': '9:16'})
    assert create_res.status_code == 200
    data = create_res.json()
    proj_id = data['id']
    assert 'Podcast_James_01' in proj_id

    # 2. Get project
    get_res = client.get(f'/api/projects/{proj_id}')
    assert get_res.status_code == 200
    assert get_res.json()['name'] == 'Podcast_James_01'

    # 3. Transcribe speech
    trans_res = client.post('/api/subtitles/transcribe', json={
        'project_id': proj_id,
        'raw_text': 'Back then I had no idea what to do. It felt like the ground was moving under my feet.',
        'words_per_caption': 4
    })
    assert trans_res.status_code == 200
    captions = trans_res.json()['captions']
    assert len(captions) >= 2
    assert 'words' in captions[0]
    assert len(captions[0]['words']) > 0

    # 4. Split caption
    first_cap = captions[0]
    split_time = round((first_cap['start'] + first_cap['end']) / 2, 2)
    split_res = client.post('/api/subtitles/split', json={
        'project_id': proj_id,
        'caption_id': first_cap['id'],
        'split_time': split_time
    })
    assert split_res.status_code == 200
    new_caps = split_res.json()['captions']
    assert len(new_caps) == len(captions) + 1

    # 5. Rename project
    rename_res = client.post(f'/api/projects/{proj_id}/rename', json={'new_name': 'Podcast_James_01_Edited'})
    assert rename_res.status_code == 200
    assert rename_res.json()['name'] == 'Podcast_James_01_Edited'

    # 6. Verify persistence across list
    list_res = client.get('/api/projects')
    assert list_res.status_code == 200
    projects = list_res.json()['projects']
    matching = [p for p in projects if p['id'] == proj_id]
    assert len(matching) == 1
    assert matching[0]['name'] == 'Podcast_James_01_Edited'

def test_translation_and_word_alignment(monkeypatch):
    from app.services.translation_service import translation_service
    def translated(captions, **kwargs):
        for c in captions: c.translated_text = "Faithful fixture translation"
        return captions
    monkeypatch.setattr(translation_service,"translate_captions_list",translated)
    create_res = client.post('/api/projects', json={'name': 'Hindi_Podcast_EP02', 'aspect_ratio': '9:16'})
    proj_id = create_res.json()['id']

    # Transcribe Hindi / Hinglish
    client.post('/api/subtitles/transcribe', json={
        'project_id': proj_id,
        'raw_text': 'agar aap AI tools banana chahte hain toh aapko backend aur frontend dono ko tezi se jodna hoga.',
        'words_per_caption': 5
    })

    # Translate
    trans_res = client.post('/api/subtitles/translate', json={'project_id': proj_id})
    assert trans_res.status_code == 200
    caps = trans_res.json()['captions']
    assert len(caps) > 0
    assert caps[0]['translated_text'] is not None
    assert len(caps[0]['words']) > 0

def test_fusion_generator_and_davinci_status():
    catalog = fusion_generator.get_template_catalog()
    assert len(catalog) >= 5
    template_ids = [t['id'] for t in catalog]
    assert 'kinetic_typography' in template_ids
    assert 'silhouette_curve' in template_ids
    assert 'stat_counter' in template_ids

    # Test comp generation
    comp_code = fusion_generator.generate_motion_graphic_comp('kinetic_typography', {
        'headline': 'Back then',
        'accent_word': 'I had',
        'punchline': 'no idea.'
    })
    assert 'TextPlus' in comp_code
    assert 'Merge' in comp_code

    # Test DaVinci status endpoint
    status_res = client.get('/api/davinci/status')
    assert status_res.status_code == 200
    assert 'is_running' in status_res.json()
    assert 'script_api_available' in status_res.json()

def test_media_search_and_auto_match(monkeypatch):
    from app.services.media_search_service import media_search_service as media
    from app.services.media_providers.base import MediaAsset
    asset=MediaAsset(id='fixture',provider='pexels',title='Cellular pathology',media_type='image',thumb_url='https://example.org/thumb.jpg',preview_url='https://example.org/image.jpg',download_url='https://example.org/image.jpg')
    monkeypatch.setattr(media.pexels,'search_images',lambda *a,**k:[asset])
    monkeypatch.setattr(media,'rerank_candidates_with_vision',lambda assets,*a,**k:(assets[0],'Fixture reviewed'))
    # 1. Search endpoint
    search_res = client.get('/api/media/search?query=cancer&type=image')
    assert search_res.status_code == 200
    data = search_res.json()
    assert data['count'] > 0
    assert len(data['results']) > 0
    assert 'url' in data['results'][0]
    assert 'source_credit' in data['results'][0]

    # 2. Auto-match endpoint for cancer dialogue
    match_res = client.post('/api/media/auto-match', json={
        'caption_text': 'the cancer cells grew rapidly inside the lungs'
    })
    assert match_res.status_code == 200
    match = match_res.json()
    assert 'cancer' in match['search_term'] or 'cell' in match['search_term']
    assert any(term.lower() in match['broll_title'].lower() for term in ['medical', 'oncology', 'cellular', 'pathology'])
    assert match['media']['url'].startswith('http')

