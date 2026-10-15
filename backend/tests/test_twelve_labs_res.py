import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.services.twelve_labs_service import twelve_labs_service
from app.core.config import settings

def test_twelve_labs_cache_eviction(tmp_path, monkeypatch):
    test_cache = tmp_path / "twelve_labs_assets.json"
    initial_data = {
        "hash123": {"asset_id": "asset_abc", "filename": "test1.mp4"},
        "hash456": {"asset_id": "asset_bad", "filename": "test2.mov"}
    }
    test_cache.write_text(json.dumps(initial_data))
    monkeypatch.setattr(settings, "projects_dir", tmp_path)

    # Evict by asset_id
    twelve_labs_service._evict_cached_asset(asset_id="asset_bad")
    updated = json.loads(test_cache.read_text())
    assert "hash456" not in updated
    assert "hash123" in updated

    # Evict by file_hash
    twelve_labs_service._evict_cached_asset(file_hash="hash123")
    updated2 = json.loads(test_cache.read_text())
    assert "hash123" not in updated2
    assert len(updated2) == 0

def test_twelve_labs_index_asset_evicts_on_failure(tmp_path, monkeypatch):
    test_cache = tmp_path / "twelve_labs_assets.json"
    initial_data = {
        "hash999": {"asset_id": "bad_res_asset", "filename": "bad.mov"}
    }
    test_cache.write_text(json.dumps(initial_data))
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    monkeypatch.setattr(twelve_labs_service, "_get_api_key", lambda: "fake_key")
    monkeypatch.setattr(twelve_labs_service, "get_or_create_default_index", lambda: "fake_idx")

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"code":"video_resolution_too_low","message":"The resolution of the video is too low."}'

    with patch("requests.post", return_value=mock_resp):
        res = twelve_labs_service.index_asset("bad_res_asset")
        assert res["success"] is False
        assert "Indexing asset failed (400)" in res["error"]
        
        # Cache should have been evicted
        updated = json.loads(test_cache.read_text())
        assert "hash999" not in updated
