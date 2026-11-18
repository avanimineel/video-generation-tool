"""Detect structural ASR corruption without guessing the speaker's words."""
import unicodedata


def transcript_issues(captions):
    issues=[]
    for i,c in enumerate(captions,1):
        text=c.text.strip()
        letters=[ch for ch in text if ch.isalpha() or ch.isdigit()]
        # Combining vowel/intonation marks alone are not a spoken subtitle.
        if not letters or '\ufffd' in text:
            issues.append(f'line {i}: unreadable speech text')
        if c.end <= c.start:
            issues.append(f'line {i}: invalid time interval')
        if i>1 and c.start < captions[i-2].start:
            issues.append(f'line {i}: timestamps run backwards')
    return issues


def salvage_captions(captions):
    """Drop lines that cannot be read or timed. Every kept line is unchanged."""
    kept = []
    dropped = []
    for i, caption in enumerate(captions, 1):
        text = (getattr(caption, 'text', None) or '').strip()
        letters = [ch for ch in text if ch.isalpha() or ch.isdigit()]
        if not letters or '\ufffd' in text:
            dropped.append(f'line {i}: unreadable speech text')
            continue
        if caption.end <= caption.start:
            dropped.append(f'line {i}: invalid time interval')
            continue
        if kept and caption.start < kept[-1].start:
            dropped.append(f'line {i}: timestamps run backwards')
            continue
        kept.append(caption)
    return kept, dropped


def caption_skip_message(dropped) -> str:
    shown = '; '.join(dropped[:5])
    extra = '' if len(dropped) <= 5 else f' (+{len(dropped) - 5} more)'
    return (
        f'Skipped {len(dropped)} caption line(s) with unreadable text or invalid timing. '
        f'The rest of the edit continues. {shown}{extra}'
    )


def salvage_is_enough(captions, kept, dropped) -> bool:
    """A few bad lines stay out of the edit. A mostly unreadable transcript does not."""
    if not kept:
        return False
    return len(dropped) <= max(3, len(captions) // 5)
