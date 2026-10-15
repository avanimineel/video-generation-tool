import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import init_db
from app.services.project_manager import project_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_single_project_deletion_and_disk_purge():
    create_res = client.post('/api/projects', json={'name': 'DelUnitTest_01', 'aspect_ratio': '9:16'})
    assert create_res.status_code == 200
    pid = create_res.json()['id']
    pdir = settings.projects_dir / pid
    assert pdir.exists()

    del_res = client.delete(f'/api/projects/{pid}')
    assert del_res.status_code == 200
    assert del_res.json()['success'] is True
    assert not pdir.exists()

    list_res = client.get('/api/projects')
    assert list_res.status_code == 200
    project_ids = [p['id'] for p in list_res.json()['projects']]
    assert pid not in project_ids

def test_autosave_rejected_for_deleted_project():
    create_res = client.post('/api/projects', json={'name': 'DelUnitTest_Autosave', 'aspect_ratio': '9:16'})
    pid = create_res.json()['id']
    pdir = settings.projects_dir / pid
    assert pdir.exists()

    del_res = client.delete(f'/api/projects/{pid}')
    assert del_res.status_code == 200
    assert not pdir.exists()

    autosave_res = client.post(f'/api/projects/{pid}/autosave', json={
        'id': pid,
        'name': 'DelUnitTest_Autosave',
        'created_at': '2026-10-06T00:00:00',
        'updated_at': '2026-10-06T00:00:00',
        'settings': {'aspect_ratio': '9:16'},
        'captions': [],
        'graphics': []
    })
    assert autosave_res.status_code == 404
    assert not pdir.exists()

def test_bulk_project_deletion():
    p1 = client.post('/api/projects', json={'name': 'Bulk_A', 'aspect_ratio': '9:16'}).json()['id']
    p2 = client.post('/api/projects', json={'name': 'Bulk_B', 'aspect_ratio': '9:16'}).json()['id']
    p3 = client.post('/api/projects', json={'name': 'Bulk_C', 'aspect_ratio': '9:16'}).json()['id']

    assert (settings.projects_dir / p1).exists()
    assert (settings.projects_dir / p2).exists()
    assert (settings.projects_dir / p3).exists()

    bulk_res = client.post('/api/projects/bulk-delete', json={'project_ids': [p1, p2]})
    assert bulk_res.status_code == 200
    data = bulk_res.json()
    assert data['success'] is True
    assert data['deleted_count'] == 2

    assert not (settings.projects_dir / p1).exists()
    assert not (settings.projects_dir / p2).exists()
    assert (settings.projects_dir / p3).exists()

    client.delete(f'/api/projects/{p3}')
    assert not (settings.projects_dir / p3).exists()
