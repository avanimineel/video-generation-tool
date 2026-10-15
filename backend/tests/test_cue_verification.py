from app.services.cue_verification import assess_match

def test_matching_word_within_quarter_second_passes_without_ground_truth_claim():
    r=assess_match({'start':46.94,'confidence':.99},{'start':46.8,'end':47.1,'word':'फ्रूट्स','probability':.8},True,.99)
    assert r['status']=='crosschecked' and r['onset_disagreement_seconds']==.14
    assert not r['ground_truth_verified']

def test_if_cannot_mean_fruits_even_at_identical_time():
    r=assess_match({'start':52.56,'confidence':1},{'start':52.56,'end':53,'word':'अगर','probability':1},True,1)
    assert r['status']=='needs_review'

def test_disagreement_and_uncertain_translation_are_not_accepted():
    c={'start':5.405,'confidence':1};w={'start':5.74,'end':6,'word':'हल्दी','probability':.9}
    assert assess_match(c,w,True,1)['status']=='needs_review'
    w['start']=5.4
    assert assess_match(c,w,False,.99)['status']=='needs_review'
