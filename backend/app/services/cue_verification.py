"""Conservative cross-language/independent-ASR consensus gate.
Agreement is not ground-truth acoustic accuracy; retain that distinction in reports.
"""
import math

FUNCTION_WORDS={'अगर','और','या','तो','कि','के','की','का','में','से','है','हैं','यह','वह','आप','हम','if','and','or','the','a','an','is','are','of','in','to'}

def assess_match(cue, word, semantic_match, semantic_confidence, tolerance=.25):
    result={'cue':cue,'local_word':word,'tolerance_seconds':tolerance,'ground_truth_verified':False}
    if not semantic_match or semantic_confidence < .9:
        return dict(result,status='needs_review',reason='Cross-language meaning was not confidently matched')
    if word['word'].strip('.,!?।').casefold() in FUNCTION_WORDS:
        return dict(result,status='needs_review',reason='Grammatical word cannot anchor this noun/action')
    a,b=float(cue['start']),float(word['start'])
    if not all(math.isfinite(x) for x in (a,b,float(word['end']))) or word['end']<=b:
        return dict(result,status='needs_review',reason='Invalid acoustic word interval')
    if float(cue.get('confidence',0))<.9 or float(word.get('probability',0))<.5:
        return dict(result,status='needs_review',reason='One recognizer has low confidence')
    delta=round(abs(a-b),4)
    result['onset_disagreement_seconds']=delta
    if delta>tolerance:
        return dict(result,status='needs_review',reason='Independent onsets disagree beyond tolerance')
    return dict(result,status='crosschecked',start=b,reason='Meaning matches; independent onset estimates agree within tolerance')
