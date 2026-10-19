"""Camera moves, speed and hand-overs for full-screen cutaways (B-roll only; the speaker shot stays still).

Rules, so the choices read as edited rather than random:
- A still always moves (a still that sits is dead air); stills rotate through moves and pan toward the subject.
- Video already moves: a gentle push-in at most, and a speed ramp when the cue is an action.
- Back-to-back cutaways hand over with a whip pan; a cutaway after a stretch of speaker eases in with a
  dissolve when it is long enough to afford one, otherwise it cuts. Short cutaways always cut.
"""
STILL_MOVES = ('push_in', 'pan', 'tilt_up', 'slow_zoom_out', 'crane_up', 'push_in', 'dutch')
BACK_TO_BACK_SECONDS = .6


def is_cutaway(graphic):
    return getattr(graphic, 'placement_mode', 'overlay') == 'insert' or graphic.template_id == 'youtube_insert'


def choose_motion(graphics):
    """Set animation, speed and transitions on generated full-screen cutaways that have none chosen yet."""
    cutaways = sorted((g for g in graphics if is_cutaway(g) and g.parameters.get('editorial_generated')), key=lambda g: g.start)
    stills = 0
    for index, graphic in enumerate(cutaways):
        p = graphic.parameters
        if p.get('motion_chosen'): continue
        length = graphic.end - graphic.start
        before = cutaways[index - 1] if index else None
        after = cutaways[index + 1] if index + 1 < len(cutaways) else None
        if graphic.media_type == 'video':
            move = 'slow_zoom_in' if length >= 1.2 else 'none'
            p['speed'] = 'speed_ramp' if p.get('cue_kind') == 'action' and length >= 1.5 else 'normal'
        else:
            move = STILL_MOVES[stills % len(STILL_MOVES)]; stills += 1
            if move == 'pan':
                focus = float(p.get('media_pos_x', .5))
                move = 'pan_right' if focus > .55 else 'pan_left' if focus < .45 else 'tilt_up'
            p['speed'] = 'normal'
        p['animation'] = move; graphic.animation = move
        joined_before = before is not None and graphic.start - before.end <= BACK_TO_BACK_SECONDS
        joined_after = after is not None and after.start - graphic.end <= BACK_TO_BACK_SECONDS
        p['transition_in'] = 'whip' if joined_before else ('dissolve' if length >= 2.0 else 'cut')
        p['transition_out'] = 'whip' if joined_after else 'cut'
        p['motion_chosen'] = True
    return graphics
