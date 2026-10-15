import json
import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from app.services.project_manager import project_manager as pm, ProjectConflict
from app.core.database import init_db
from app.core.models import CaptionItem

def project():
    init_db()
    return pm.create_project('transaction')

def test_same_second_projects_have_distinct_ids():
    a=project();b=project();assert a.id!=b.id

def test_two_concurrent_writers_cannot_silently_overwrite():
    p=project();barrier=Barrier(2)
    def save(text):
        state=pm.get_project(p.id);state.captions=[CaptionItem(id='c',start=0,end=1,text=text)]
        barrier.wait()
        try:pm.save_project(state);return 'saved'
        except ProjectConflict:return 'conflict'
    with ThreadPoolExecutor(2) as pool:
        futures=[pool.submit(save,t) for t in ('first','second')]
        assert sorted(f.result() for f in futures)==['conflict','saved']
    assert len(pm.get_project(p.id).captions)==1

def test_failed_save_keeps_complete_previous_revision(monkeypatch):
    p=project();before=pm.get_project(p.id).model_dump()
    from app.services import project_manager as module
    original=module.atomic_text
    def fail(path,text):
        if path.name=='graphics.json':raise OSError('simulated full disk')
        return original(path,text)
    monkeypatch.setattr(module,'atomic_text',fail)
    p.captions=[CaptionItem(id='c',start=0,end=1,text='Uncommitted')]
    with pytest.raises(OSError):pm.save_project(p)
    assert pm.get_project(p.id).model_dump()==before

def test_stale_normal_save_and_future_revision_rejected():
    from fastapi.testclient import TestClient
    from app.main import app
    p=project();old=p.model_dump();p.name='New name';pm.save_project(p)
    client=TestClient(app)
    assert client.put('/api/projects/'+p.id,json=old).status_code==409
    old['updated_at']='9999-01-01'
    assert client.post('/api/projects/'+p.id+'/autosave',json=old).status_code==409
    assert pm.get_project(p.id).name=='New name'


def test_repeated_identical_saves_keep_revision_and_skip_mask_work(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import subject_layers
    p=project();revision=p.updated_at
    def unexpected(*args):raise AssertionError('Unchanged project should not rebuild masks')
    monkeypatch.setattr(subject_layers,'prepare_subject_layers',unexpected)
    client=TestClient(app)
    for _ in range(2):
        result=client.post('/api/projects/'+p.id+'/autosave',json=p.model_dump())
        assert result.status_code==200
        assert result.json()['autosaved_at']==revision
    pm.save_project(p)
    assert p.updated_at==revision


def test_identical_stale_retry_is_safe_but_different_stale_edit_is_not():
    p=project();old_revision=p.updated_at
    p.name='New edit';pm.save_project(p);new_revision=p.updated_at
    retry=p.model_copy(deep=True);retry.updated_at=old_revision
    pm.save_project(retry)
    assert retry.updated_at==new_revision
    retry.updated_at=old_revision;retry.name='Conflicting edit'
    with pytest.raises(ProjectConflict):pm.save_project(retry)
    assert pm.get_project(p.id).name=='New edit'
