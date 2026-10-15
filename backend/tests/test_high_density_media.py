import pytest
from app.services.high_density_media_service import (
    calculate_media_coverage,
    maximize_media_density,
    merge_intervals,
    split_gap_by_speech
)
from app.core.models import CaptionItem, MotionGraphicItem, ProjectState
from fastapi.testclient import TestClient
from app.main import app
from app.api import projects as api_projects

def test_merge_intervals():
    intervals = [(0.0, 3.5), (3.4, 5.0), (7.0, 10.0), (9.8, 12.0)]
    merged = merge_intervals(intervals)
    assert len(merged) == 2
    assert merged[0] == (0.0, 5.0)
    assert merged[1] == (7.0, 12.0)

def test_split_gap_by_speech():
    captions = [
        CaptionItem(id='1', start=1.0, end=2.5, text='First short phrase'),
        CaptionItem(id='2', start=2.5, end=4.5, text='Second sentence spoken'),
        CaptionItem(id='3', start=4.5, end=7.0, text='Third sentence continues')
    ]
    splits = split_gap_by_speech(0.0, 7.0, captions)
    assert len(splits) >= 1
    assert splits[0][0] == 0.0
    assert splits[-1][1] == 7.0

def test_media_coverage_and_maximize_api(monkeypatch):
    state = ProjectState(
        id='test_density_proj',
        name='Test Density',
        created_at='now',
        updated_at='now',
        duration_seconds=20.0,
        graphics=[
            MotionGraphicItem(
                id='g1', start=0.0, end=18.0, template_id='youtube_insert', title='Test Clip',
                track='V2', media_url='/api/media/test/asset/vid.mp4'
            )
        ]
    )
    monkeypatch.setattr(api_projects.project_manager, 'get_project', lambda pid: state if pid == 'test_density_proj' else None)
    
    client = TestClient(app)
    res = client.get('/api/projects/test_density_proj/media-coverage')
    assert res.status_code == 200
    data = res.json()
    assert 'coverage_percentage' in data
    assert 'total_duration' in data
    assert data['coverage_percentage'] == 90.0


def test_generate_hook_title_graphics():
    from app.services.high_density_media_service import generate_hook_title_graphics
    state = ProjectState(
        id='test_titles_proj',
        name='Test Titles',
        created_at='now',
        updated_at='now',
        duration_seconds=70.0,
        captions=[
            CaptionItem(id='c1', start=0.5, end=3.5, text='foods for cancer prevention'),
            CaptionItem(id='c2', start=4.0, end=6.0, text='first item is haldi'),
            CaptionItem(id='c3', start=9.0, end=12.0, text='haldi does not cure cancer')
        ]
    )
    titles = generate_hook_title_graphics(state)
    assert titles == []  # Legacy keyword-fragment titles must never return.


def test_density_never_resurrects_cached_rejected_media(monkeypatch):
    from app.services import high_density_media_service as svc
    state = ProjectState(id='preserved', name='Preserved', created_at='now', updated_at='now',
                         duration_seconds=10, graphics=[MotionGraphicItem(id='hook_title_manual', start=0,
                         end=3, template_id='kinetic_typography', title='My approved title')])
    before = state.model_dump()
    monkeypatch.setattr(svc.project_manager, 'get_project', lambda _: state)
    monkeypatch.setattr(svc.project_manager, 'save_project', lambda *a: pytest.fail('Legacy pass must not write'))
    monkeypatch.setattr(svc, 'get_available_assets', lambda *a: pytest.fail('Do not reuse unreviewed cached media'))
    result = svc.maximize_media_density(state.id)
    assert result['added_count'] == 0 and result['status'] == 'requires_reviewed_edit'
    assert state.model_dump() == before
