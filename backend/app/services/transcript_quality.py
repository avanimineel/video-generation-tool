"""Detect structural ASR corruption without guessing the speaker's words."""

# After dropping punctuation-only / replacement-char captions, require at least
# this fraction of the original list to remain readable before continuing.
MIN_USABLE_SPEECH_RATIO = 0.1


def _speech_chars(text: str):
    return [ch for ch in text if ch.isalpha() or ch.isdigit()]


def is_readable_speech(text: str) -> bool:
    """True when caption text has at least one letter/digit and no U+FFFD."""
    cleaned = (text or '').strip()
    return bool(_speech_chars(cleaned)) and '\ufffd' not in cleaned


def transcript_issues(captions):
    issues = []
    for i, c in enumerate(captions, 1):
        text = c.text.strip()
        letters = _speech_chars(text)
        # Combining vowel/intonation marks alone are not a spoken subtitle.
        if not letters or '\ufffd' in text:
            issues.append(f'line {i}: unreadable speech text')
        if c.end <= c.start:
            issues.append(f'line {i}: invalid time interval')
        if i > 1 and c.start < captions[i - 2].start:
            issues.append(f'line {i}: timestamps run backwards')
    return issues


def drop_unreadable_captions(captions):
    """Drop structurally unreadable captions; never invent replacement words.

    Returns (kept, dropped) where dropped entries are
    ``{'line': 1-based index, 'text': str, 'reason': str}``.
    Timing issues are left for ``transcript_issues`` on the kept list.
    """
    kept = []
    dropped = []
    for i, c in enumerate(captions, 1):
        text = (c.text or '').strip()
        letters = _speech_chars(text)
        if not letters:
            dropped.append({
                'line': i,
                'text': text,
                'reason': 'no letters or digits (punctuation-only or empty)',
            })
        elif '\ufffd' in text:
            dropped.append({
                'line': i,
                'text': text,
                'reason': 'contains replacement character U+FFFD',
            })
        else:
            kept.append(c)
    return kept, dropped


def has_enough_usable_speech(kept_count: int, original_count: int,
                             min_ratio: float = MIN_USABLE_SPEECH_RATIO) -> bool:
    """Fail closed when almost no readable speech remains after filtering."""
    if kept_count <= 0 or original_count <= 0:
        return False
    return (kept_count / original_count) >= min_ratio
