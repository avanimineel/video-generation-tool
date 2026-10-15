import pytest
from app.services.translation_service import translation_service as service
from app.services import editorial_planner as planner

def test_reordered_and_missing_lines_retry_only_missing(monkeypatch):
    calls=[]
    responses=[{'lines':[{'id':2,'text':'Test negative'},{'id':0,'text':'The doctor said'}]}, {'lines':[{'id':1,'text':'Get a biopsy'}]}]
    def generate(prompt,*a,**kw):
        calls.append(prompt);return responses.pop(0)
    monkeypatch.setattr(planner,'gemini_json',generate)
    assert service.translate_with_gemini(['डॉक्टर ने कहा','बायोप्सी कराओ','जांच नेगेटिव'])==['The doctor said','Get a biopsy','Test negative']
    import json
    assert json.loads(calls[1].split(' REQUESTED: ')[1])==[{'id':1,'text':'बायोप्सी कराओ'}]

def test_duplicate_ids_and_untranslated_rows_not_accepted(monkeypatch):
    outputs=iter([{'lines':[{'id':0,'text':'One'},{'id':0,'text':'Two'},{'id':1,'text':'हिंदी'}]}, {'lines':[{'id':0,'text':'First'},{'id':1,'text':'Second'}]}])
    monkeypatch.setattr(planner,'gemini_json',lambda *a,**k:next(outputs))
    assert service.translate_with_gemini(['पहला','दूसरा'])==['First','Second']

def test_missing_lines_fail_bounded_without_shifting_subtitles(monkeypatch):
    calls=[]
    def generate(*a,**k):calls.append(1);return {'lines':[{'id':99,'text':'Wrong ID'}]}
    monkeypatch.setattr(planner,'gemini_json',generate)
    with pytest.raises(ValueError,match='after retries'):service.translate_with_gemini(['पहला'])
    assert len(calls)==3


def test_translation_resume_reuses_valid_rows_after_provider_failure(monkeypatch, tmp_path):
    checkpoint=tmp_path/'translation.json'
    responses=iter([{'lines':[{'id':0,'text':'First'}]}, RuntimeError('Provider HTTP 503')])
    def fail(*a,**kw):
        item=next(responses)
        if isinstance(item,Exception):raise item
        return item
    monkeypatch.setattr(planner,'gemini_json',fail)
    with pytest.raises(RuntimeError):service.translate_with_gemini(['पहला','दूसरा'],checkpoint)
    calls=[]
    def recover(prompt,*a,**kw):
        calls.append(prompt);return {'lines':[{'id':1,'text':'Second'}]}
    monkeypatch.setattr(planner,'gemini_json',recover)
    assert service.translate_with_gemini(['पहला','दूसरा'],checkpoint)==['First','Second']
    import json
    assert json.loads(calls[0].split(' REQUESTED: ')[1])==[{'id':1,'text':'दूसरा'}]
    monkeypatch.setattr(planner,'gemini_json',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('No repeated requests')))
    assert service.translate_with_gemini(['पहला','दूसरा'],checkpoint)==['First','Second']
