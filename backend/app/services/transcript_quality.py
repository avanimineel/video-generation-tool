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
