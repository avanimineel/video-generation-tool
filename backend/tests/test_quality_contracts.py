from app.services.media_constraints import evidence_rejection
from app.services.title_styles import choose_title_style
from app.core.models import MotionGraphicItem

def test_a_search_query_does_not_impose_a_country():
    row={'visual_role':'illustration','semantic_context':{'transcript':'in India lung cancer is not detected'},'asset':{'retrieval_query':'India polio camp','semantic_target':'chest x-ray'}}
    assert evidence_rejection({'title':'Nurse in an American hospital'}, row) is None
    assert evidence_rejection({'title':'Chest x-ray of lungs'}, row) is None


def test_evidence_requires_the_subject_named_by_this_video():
    row={'visual_role':'evidence','asset':{'required_entities':['Delhi']}}
    assert evidence_rejection({'title':'Nurse in an American hospital'}, row)
    assert evidence_rejection({'title':'Clinic in Delhi'}, row) is None

def test_named_person_not_replaced_with_generic_portrait():
    row={'intent':'IDENTIFY','asset':{'required_entities':['Lisa Ray']}}
    assert evidence_rejection({'title':'Woman with dark hair'},row)
    assert evidence_rejection({'title':'Lisa Ray at event'},row) is None

def test_title_style_is_stable_and_manual_style_survives():
    g=MotionGraphicItem(id='t',start=0,end=3,template_id='kinetic_typography',title='The exact spoken words')
    assert choose_title_style(g)=='editorial' # House style; other looks are opt-in.
    g.parameters['title_style']='paper'
    assert choose_title_style(g)=='paper'


def test_named_identity_can_reach_search_but_generic_candidate_cannot():
    from app.services.finished_reel_understanding import source_requirement
    row={'visual_role':'identity','strategy':'STOCK_IMAGE','asset':{'required_entities':['Nargis Dutt']}}
    assert source_requirement(row) is None
    assert evidence_rejection({'title':'Generic actress portrait'},row)
    assert evidence_rejection({'title':'Nargis Dutt photographed at event'},row) is None


def test_referential_fragments_are_not_highlights():
    from app.services.editorial_planner import weak_title
    assert weak_title('This actor')
    assert weak_title('later he himself')
    assert not weak_title('advanced stage lung cancer')
    assert not weak_title('Sanjay Dutt')
