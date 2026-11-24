import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.project_manager import project_manager


def test_saved_export_can_be_downloaded_without_rendering(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    monkeypatch.setattr(project_manager, "projects_dir", tmp_path)
    pid = "export_existing_fixture"
    folder = tmp_path / pid
    (folder / "exports").mkdir(parents=True)
    (folder / "project.json").write_text(json.dumps({
        "id": pid, "name": "Demo", "created_at": "t", "updated_at": "t",
    }))
    (folder / "settings.json").write_text("{}")
    (folder / "captions.json").write_text("[]")
    (folder / "graphics.json").write_text("[]")
    video = folder / "exports" / "Demo_burned.mp4"
    video.write_bytes(b"fake-mp4")

    client = TestClient(app)
    status = client.get(f"/api/media/{pid}/export-status")
    assert status.status_code == 200
    body = status.json()
    assert body["ready"] is True
    assert body["full"]["file_name"] == "Demo_burned.mp4"
    assert body["full"]["download_url"].endswith("existing=true")

    saved = client.get(body["full"]["download_url"])
    assert saved.status_code == 200
    assert saved.content == b"fake-mp4"
    assert "Demo_burned.mp4" in saved.headers["content-disposition"]

    missing = client.get(f"/api/media/{pid}/download-mp4?subtitles_only=true&existing=true")
    assert missing.status_code == 404
