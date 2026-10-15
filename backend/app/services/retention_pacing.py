"""One-second camera beats supplement reviewed media; never invent stock or text."""
import math
from app.core.models import MotionGraphicItem


def add_camera_beats(state, graphics, protected=()):
    # Existing authored treatments win. Repeated runs replace only this layer.
    retained = [g for g in graphics if not g.parameters.get('retention_camera')]
    occupied = sorted((max(0., g.start), min(state.duration_seconds, g.end))
                      for g in retained + list(protected) if g.end > g.start)
    merged = []
    for start, end in occupied:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    gaps = []; cursor = 0.
    for start, end in merged:
        if start > cursor: gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < state.duration_seconds: gaps.append((cursor, state.duration_seconds))
    added = []
    for start, end in gaps:
        if end - start < .5: continue
        count = max(1, math.ceil(end-start))
        step = (end-start)/count
        scale = 1.
        for i in range(count):
            # Shared endpoints prevent snaps when seeking or crossing beat cuts.
            next_scale = 1. if i == count-1 else (1.10 if i % 2 == 0 else 1.02)
            # A short isolated gap is one gentle push/pull with a smooth envelope.
            pulse = count == 1
            a = start+i*step; b = start+(i+1)*step
            added.append(MotionGraphicItem(
                id=f'retention_camera_{a:.3f}', start=a, end=b, track='V1',
                template_id='source_reframe', title='Camera beat',
                parameters={'editorial_generated':True,'retention_camera':True,
                            'start_scale':scale,'end_scale':next_scale,
                            'motion_curve':'pulse' if pulse else 'smoothstep',
                            'sfx_muted':True,'timing_method':'one-second editorial rhythm, not a speech cue'}))
            scale = next_scale
    return sorted(retained+added,key=lambda g:g.start), {
        'target_beat_seconds':1.0,'camera_beats':len(added),
        'reviewed_treatments':len(retained),
        'camera_seconds':round(sum(g.end-g.start for g in added),2),
        'note':'Camera motion fills uncovered intervals. Reviewed media and protected treatments retain their authored duration; no claim of a new asset every second.'}


PUNCH_SCALE = 1.14
MIN_HOLD_SECONDS = 1.2
MAX_HOLD_SECONDS = 4.0


def sentence_beats(captions, duration):
    """Spans between sentence ends (or clear pauses), merged and split to a watchable hold length."""
    caps = sorted((c for c in captions if c.end > c.start), key=lambda c: c.start)
    cuts = [0.0]
    for cap, following in zip(caps, caps[1:]):
        text = (cap.translated_text or cap.text or '').strip()
        if text.endswith(('.', '?', '!', '।')) or following.start - cap.end > .45:
            cuts.append(following.start)
    cuts.append(float(duration))
    beats = []
    for start, end in zip(cuts, cuts[1:]):
        if beats and (end - start < MIN_HOLD_SECONDS or beats[-1][1] - beats[-1][0] < MIN_HOLD_SECONDS):
            beats[-1] = (beats[-1][0], end)
        elif end > start:
            beats.append((start, end))
    result = []
    for start, end in beats:
        parts = max(1, math.ceil((end - start) / MAX_HOLD_SECONDS))
        result += [(start + (end - start) * i / parts, start + (end - start) * (i + 1) / parts) for i in range(parts)]
    return result


def add_punch_ins(state, graphics, head_band=None):
    """Alternate the wide shot with a hard punch-in on sentence beats, anchored on the speaker's face.
    The picture changes with the speech, without adding stock or text."""
    if head_band is None:
        from app.services.subject_layers import speaker_head_band as head_band
    retained = [g for g in graphics if not g.parameters.get('retention_camera')]
    covered = [(g.start, g.end) for g in retained
               if getattr(g, 'placement_mode', 'overlay') == 'insert' or g.parameters.get('subject_mask')
               or g.parameters.get('title_style') in ('behind_subject', 'cards_broll', 'staircase', 'flame_subject')]
    added = []
    beats = sentence_beats(getattr(state, 'captions', []), getattr(state, 'duration_seconds', 0) or 0)
    for index, (start, end) in enumerate(beats):
        if index % 2 == 0:
            continue  # Open wide, then alternate.
        hidden = sum(max(0, min(end, b) - max(start, a)) for a, b in covered)
        if hidden > (end - start) * .4:
            continue  # A zoom under a cutaway or a speaker matte would be invisible or misaligned.
        band = head_band(state, (start + end) / 2)
        added.append(MotionGraphicItem(
            id=f'punch_in_{start:.3f}', start=round(start, 3), end=round(end, 3), track='V1',
            template_id='source_reframe', title='Punch-in',
            parameters={'editorial_generated': True, 'retention_camera': True,
                        'start_scale': PUNCH_SCALE, 'end_scale': PUNCH_SCALE, 'motion_curve': 'hold',
                        # A face sits in the upper half; a measurement outside that range is a bad matte.
                        'focus_x': .5, 'focus_y': round((band[0] + band[1]) / 2, 3) if band and .15 <= (band[0] + band[1]) / 2 <= .55 else .36,
                        'timing_method': 'sentence boundary from captions'}))
    return sorted(retained + added, key=lambda g: g.start), {
        'punch_ins': len(added), 'beats': len(beats),
        'cut_times': sorted({t for g in added for t in (g.start, g.end)})}
