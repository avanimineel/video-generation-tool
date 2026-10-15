import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services.asset_downloader import asset_downloader
from app.services.media_search_service import media_search_service
from app.services.media_providers.base import MediaAsset
from app.services.media_providers.pexels import PexelsProvider
from app.services.media_providers.pixabay import PixabayProvider
from app.services.media_providers.wikimedia import WikimediaProvider
from app.services.media_providers.google_ai import GoogleAIProvider

client = TestClient(app)

def test_providers_status_endpoint():
    res = client.get("/api/media/providers/status")
    assert res.status_code == 200
    data = res.json()
    assert "pexels" in data
    assert "pixabay" in data
    assert "wikimedia" in data
    assert "google_ai" in data
    assert "connected" in data["wikimedia"]
    assert "status" in data["wikimedia"]
    assert "masked_key" in data["wikimedia"]

def test_query_generator():
    dialogue = "The patient had severe coughing and fever in the hospital ward"
    queries = media_search_service.generate_search_queries(dialogue)
    assert len(queries) >= 1
    assert any("cough" in q or "hospital" in q or "patient" in q for q in queries)

def test_media_search_endpoint_with_filters(monkeypatch):
    asset=MediaAsset(id='fixture',provider='pexels',title='Doctor at hospital',media_type='image',thumb_url='https://example.org/thumb.jpg',preview_url='https://example.org/image.jpg',download_url='https://example.org/image.jpg')
    monkeypatch.setattr(media_search_service.pexels,'search_images',lambda *a,**k:[asset])
    res = client.get("/api/media/search?query=doctor&type=image&provider=all&limit=4")
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert data["count"] > 0
    assert "url" in data["results"][0]
    assert "source_credit" in data["results"][0]

def test_asset_downloader_deduplication_and_metadata(tmp_path):
    test_project_id = "proj_test_downloader"
    
    sample_asset = {
        "id": "test_asset_999",
        "provider": "pexels",
        "media_type": "image",
        "url": "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=400",
        "download_url": "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=400",
        "title": "Test Clinical Asset",
        "source_credit": "Source: Test Archive",
        "author": "Dr. Test",
        "width": 800,
        "height": 600
    }

    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"FAKE_JPEG_IMAGE_DATA_CONTENT_BYTES_1234567890" * 50]
    mock_resp.raise_for_status = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("requests.get", return_value=mock_resp):
        # First download
        res1 = asset_downloader.download_asset(test_project_id, sample_asset)
        assert res1["success"] is True
        assert "local_path" in res1
        assert Path(res1["local_path"]).exists()
        assert Path(res1["local_path"]).stat().st_size > 0
        assert res1["filename"].startswith("pexels_test_asset_999")
        
        # Sidecar JSON check
        sidecar = Path(res1["local_path"]).with_suffix(".json")
        assert sidecar.exists()

        # Second download (deduplication hit - should not trigger network)
        res2 = asset_downloader.download_asset(test_project_id, sample_asset)
        assert res2["success"] is True
        assert res2["is_new"] is False
        assert res2["filename"] == res1["filename"]

        # Verify download endpoint via FastAPI TestClient
        api_res = client.post(f"/api/media/{test_project_id}/download-asset", json=sample_asset)
        assert api_res.status_code == 200
        assert api_res.json()["success"] is True

        # Verify asset file serving endpoint
        serve_res = client.get(f"/api/media/{test_project_id}/asset/downloaded/{res1['filename']}")
        assert serve_res.status_code == 200
        assert len(serve_res.content) > 0

def test_generate_ai_image_unconfigured():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
        res = client.post("/api/media/generate-ai-image", json={
            "project_id": "test_proj",
            "prompt": "Hospital room",
            "aspect_ratio": "9:16"
        })
        assert res.status_code == 400
        assert "not configured" in res.json()["detail"].lower()

@pytest.mark.parametrize('endpoint', ['generate-ai-video', 'omni-motion-generate'])
def test_mock_generation_key_is_rejected_without_persisting(endpoint):
    from app.core import config
    before = config.CREDENTIAL_FILE.read_bytes() if config.CREDENTIAL_FILE.exists() else None
    res = client.post('/api/media/' + endpoint, json={
        'project_id': 'isolated_mock_key', 'prompt': 'Indian doctor in clinic',
        'aspect_ratio': '9:16', 'duration': 4, 'motion_instructions': 'Cinematic zoom',
        'gemini_api_key': 'AIzaSyTestMockKeyForTestingPurposes12345'
    })
    assert res.status_code == 400
    assert 'placeholder' in res.json()['detail'].lower()
    after = config.CREDENTIAL_FILE.read_bytes() if config.CREDENTIAL_FILE.exists() else None
    assert before == after
