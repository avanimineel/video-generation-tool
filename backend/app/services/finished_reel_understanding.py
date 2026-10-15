"""Reference-grounded finished-reel requirements; does not modify a timeline."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

PROFILE = Path(__file__).resolve().parents[1] / 'reference_profiles' / 'medical_reel_113.json'


def load_profile():
    return json.loads(PROFILE.read_text())


def source_role(path=None, digest=None):
    if digest is None and path and Path(path).is_file():
        h = hashlib.sha256()
        with Path(path).open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        digest = h.hexdigest()
    for role, source in load_profile()['sources'].items():
        if digest == source['sha256']:
            return 'finished_reference' if role == 'after' else 'before_source'
    return 'unclassified_source'


EDITOR_REFERENCE = PROFILE.parent / 'editor_breakdown_108.json'


@lru_cache(maxsize=16)
def _source_digest(path, size, modified_ns):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def editor_reference(source_path=None):
    """General style transfers; identity, medical claims and timestamps do not."""
    p = json.loads(EDITOR_REFERENCE.read_text())
    result = {'id': p['id'], 'provenance': p['provenance'], 'rules': p['rules']}
    if source_path and Path(source_path).is_file():
        path = Path(source_path).resolve()
        stat = path.stat()
        digest = _source_digest(str(path), stat.st_size, stat.st_mtime_ns)
        if digest == p['source_sha256']:
            result['scenes'] = p['scenes']
    return result


def profile_prompt():
    p = load_profile()
    return ('FINISHED-REEL REFERENCE: ' + p['name'] + '\n' + p['alignment'] + '\n' +
            '\n'.join('- ' + r for r in p['rules']) + '\nObserved examples (style, not reusable claims):\n' +
            json.dumps(p['examples'], ensure_ascii=False) + '\nCURRENT EDITOR STYLE (overrides earlier pacing guidance):\n' + json.dumps(editor_reference(), ensure_ascii=False))


def build_brief(segments, role='unclassified_source', source_path=None):
    """Expose questions the semantic planner must resolve, rather than keyword rules."""
    beats = []
    for s in segments:
        questions = ['What must the viewer understand here?', 'Does the existing picture already communicate it?',
                     'Is the needed visual identity, evidence, illustration, demonstration, emphasis, or presenter?',
                     'What exact asset/source is required, and what would be a misleading substitute?']
        if s.narrative_role == 'HOOK':
            questions.append('What is the opening promise and which identity or image makes it immediately clear?')
        if s.claims:
            questions.append('Is this a reported claim needing a source, or an explanation needing illustration? Preserve attribution and uncertainty.')
        if s.narrative_role == 'LIST_ITEM':
            questions.append('Should these steps accumulate in a numbered checklist across successive beats?')
        if s.narrative_role in ('CTA', 'PAYOFF'):
            questions.append('What is the exact takeaway or action, and does the closing need supplied branding?')
        beats.append({'segment_id':s.id,'start_sec':s.start_sec,'end_sec':s.end_sec,
                      'meaning':s.semantic_summary,'narrative_role':s.narrative_role,
                      'existing_picture':s.current_visual_context,
                      'existing_treatments':getattr(s,'existing_treatments',[]),
                      'claims':s.claims,'uncertainties':s.uncertainties,'questions':questions})
    return {'profile_id':load_profile()['id'],'source_role':role,'beats':beats,'editor_reference':editor_reference(source_path),
            'scope':'Finished-reel requirements and gaps, not proof that all treatments can be rendered.',
            'unassessed':['Music and sound-effect design','Frame-accurate before/after alignment']}


def source_requirement(row):
    if row.get('strategy') == 'SOURCE_VIDEO_REFRAME':
        return 'Automatic camera reframes are disabled: use a meaningful source-backed scene or retain the speaker.'
    role = row.get('visual_role', 'illustration')
    if role in ('identity','evidence') and row.get('strategy') in ('BROLL_VIDEO','STOCK_IMAGE','GENERATED_VISUAL','ICONOGRAPHY','MOTION_GRAPHIC'):
        entities = row.get('asset', {}).get('required_entities', []) or []
        if entities and row.get('strategy') in ('BROLL_VIDEO','STOCK_IMAGE'):
            return None  # Retrieval must verify named source metadata and visual relevance.
        return 'Needs a verified specific source for ' + role + '; generic stock cannot fulfill this requirement.'
    if row.get('existing_treatment_action') == 'preserve' and row.get('intervene'):
        return 'Existing treatment is marked preserve; do not cover it with a duplicate overlay.'
    return None


UNRESOLVED_STATUSES = ('rejected_assets', 'needs_source_or_renderer', 'needs_review')
# Retention pacing: longer than this with no on-screen change is reported as a gap.
LONG_STATIC_SECONDS = 6.0


def scorecard(rows, duration=0, changes=()):
    """Measured facts about the realized timeline; the run outcome is derived from these, not assumed."""
    inserted = sorted((r for r in rows if r['status'] == 'inserted'), key=lambda r: r['start_sec'])
    duration = max(float(duration or 0), max((r['end_sec'] for r in rows), default=0))
    covered, fullscreen, longest_static, cursor = 0.0, 0.0, 0.0, 0.0
    for r in inserted:
        start, end = max(cursor, r['start_sec']), max(cursor, r['end_sec'])
        covered += end - start
        if (r.get('realized_composition') or {}).get('layout') == 'fullscreen':
            fullscreen += end - start
        cursor = end
    # A camera cut is an on-screen change too, though it covers nothing.
    events = sorted([(r['start_sec'], r['end_sec']) for r in inserted] + [(t, t) for t in changes])
    cursor = 0.0
    for start, end in events:
        longest_static = max(longest_static, start - cursor)
        cursor = max(cursor, end)
    longest_static = max(longest_static, duration - cursor)
    unresolved = [r for r in rows if r['status'] in UNRESOLVED_STATUSES]
    reasons = []
    preserved = [r for r in rows if r.get('preserved_existing')]
    captioned = [r for r in rows if 'burned_in_captions' in [str(t).lower() for t in (r.get('semantic_context') or {}).get('existing_treatments', [])]]
    if not inserted and any(r.get('intervene') for r in rows) and not preserved:
        outcome = 'needs_attention'; reasons.append('No planned visual reached the timeline.')
    else:
        outcome = 'complete'
        if preserved:
            outcome = 'complete_with_gaps'; reasons.append(f'Source looks already edited: {len(preserved)} visual(s) skipped to keep its existing captions and visuals.')
        if rows and len(captioned) > len(rows) / 2:
            outcome = 'complete_with_gaps'; reasons.append('Source already has burned-in captions; the automatic subtitles duplicate them.')
        if unresolved:
            outcome = 'complete_with_gaps'; reasons.append(f'{len(unresolved)} planned visual(s) could not be realized.')
        # A substituted title is a recorded gap, never a silent replacement.
        fallbacks = [r for r in inserted if r.get('requested_strategy')]
        if fallbacks:
            outcome = 'complete_with_gaps'; reasons.append(f'{len(fallbacks)} request(s) shown as a spoken title because {", ".join(sorted({r["requested_strategy"] for r in fallbacks}))} has no renderer.')
        if duration and longest_static > LONG_STATIC_SECONDS:
            outcome = 'complete_with_gaps'; reasons.append(f'{longest_static:.1f}s stretch with no on-screen change.')
    return {'outcome': outcome, 'reasons': reasons, 'duration_sec': round(duration, 2), 'inserted': len(inserted),
            'unresolved': len(unresolved), 'preserved_existing': len(preserved), 'camera_cuts': len(changes),
            'rejected_assets': sum(r['status'] == 'rejected_assets' for r in rows),
            'visual_coverage': round(covered / duration, 3) if duration else 0,
            'speaker_visible_ratio': round(1 - fullscreen / duration, 3) if duration else 1,
            'longest_static_sec': round(longest_static, 2)}


def audit_plan(rows, duration=0, changes=()):
    fulfilled, gaps = [], []
    for row in rows:
        item = {'segment_id':row['segment_id'],'start_sec':row['start_sec'],'end_sec':row['end_sec'],
                'role':row.get('visual_role','illustration'),'viewer_need':row.get('viewer_need') or row.get('editorial_need',''),
                'strategy':row['strategy'],'status':row['status'],'reason':row.get('decision_reason','')}
        if row['status'] == 'inserted':
            fulfilled.append(item)
        elif row['status'] != 'no_intervention' or row.get('intervene'):
            gaps.append(item)
    card = scorecard(rows, duration, changes)
    return {'inserted_treatments':fulfilled,'unresolved_requirements':gaps,'scorecard':card,
            'complete_finished_reel':card['outcome']=='complete',
            'note':'Inserted visuals are not a finished-reel quality guarantee. Review unresolved requirements, captions, source fidelity and closing design.'}
