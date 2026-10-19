"""Turn a brand kit into a short launch-film script built around what the company does.

Story: hook, the plain offer, what you get (features), how it works (steps), proof (stats or a client
quote), positioning line, call to action. Copy rules, adapted from short-form copywriting and
design-taste practice:
- Every line comes from the brand's own site. Lines are trimmed, never invented.
- One idea per scene, short lines, the turn of each line set in the accent style.
- A missing section is skipped, not filled with filler.
- The art direction follows the brand's own type, colours and field, so two brands never share a look.
"""
import hashlib
import re

from app.services.brand_video.site_reader import INDUSTRIES

SECONDS_PER_WORD = .34
MAX_SECONDS = 32
FILLER = ('and', 'or', 'the', 'a', 'an', 'to', 'of', 'for', 'with', 'that', 'your', 'in', 'on', 'into', 'at', 'by', 'from', 'will', 'are', 'is', 'we')


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text or '') if s.strip()]


def trim(text, words=9):
    """The first clause of a line, at most `words` words, ending on a content word."""
    first = sentences(text)[0] if sentences(text) else (text or '')
    first = re.split(r'[;:—–]|\s-\s', first)[0].strip()
    parts = first.split()
    if len(parts) > words:
        parts = parts[:words]
    while parts and parts[-1].lower().strip(',') in FILLER:
        parts.pop()
    return ' '.join(parts).rstrip(',').strip('“”"')


def accent_tail(text):
    """Set the turn of the line in the accent style: the last third of its words (at least one)."""
    words = text.split()
    return max(1, len(words) // 3) if len(words) > 1 else 0


def line(text):
    return {'text': text, 'accent_from': len(text.split()) - accent_tail(text)}


def duration(*texts, base=1.4):
    return round(base + SECONDS_PER_WORD * sum(len(t.split()) for t in texts), 2)


def field_words(text, field):
    pattern = INDUSTRIES.get(field)
    return len(re.findall(pattern, text.casefold())) if pattern else 0


def offer_line(kit):
    """The plainest statement of what the company does. Prefers a sentence-like heading that names the
    field ("Redefining the way financial transactions are performed"), then the line under the hero,
    then the meta description; the clause that carries the field's words wins."""
    copy, field = kit['copy'], kit.get('industry', 'general')
    candidates = [s['heading'] for s in copy.get('sections', []) if len(s['heading'].split()) >= 4 and s['heading'] != copy['hero']]
    candidates += [copy.get('hero_body', ''), kit.get('description', '')]
    clauses = []
    for text in candidates:
        for sentence in sentences(text) or [text]:
            for clause in re.split(r'\b(?:that will|which will|so that|that)\b|[;:—–]', sentence):
                clause = re.sub(r'^\W*(we are|we\'re|we|our mission is to|is)\s+(developing|building|making|creating)?\s*', '', clause.strip(), flags=re.I)
                if len(clause.split()) >= 4: clauses.append(clause)
    if not clauses: return None
    best = max(clauses, key=lambda c: (field_words(c, field), -candidates.index(next(t for t in candidates if c[:20] in t)) if any(c[:20] in t for t in candidates) else 0))
    text = trim(best, 10)
    return text[0].upper() + text[1:] if text else None


def brand_line(kit):
    """A positioning line, not a process step: the payoff after a colon ("...: authority that compounds."),
    else a short sentence from the description or a paragraph that is not a card description."""
    copy = kit['copy']
    used = {sentence for group in ('features', 'steps', 'faq', 'testimonials') for card in copy.get(group, []) for sentence in sentences(card['body'])}
    used |= {sentence for section in copy.get('sections', []) for sentence in sentences(section.get('body', ''))}
    pool = [s for text in [kit.get('description', '')] + copy.get('paragraphs', []) for s in sentences(text) if s not in used and not any(s in u or u in s for u in used)]
    for sentence in pool:
        if ':' in sentence:
            tail = sentence.rsplit(':', 1)[1].strip()
            if 2 <= len(tail.split()) <= 6: return tail[0].upper() + tail[1:]
    return next((s for s in pool if 4 <= len(s.split()) <= 9), None)


def direction(kit):
    """Art direction from the brand itself: its heading type, background and field.
    Serif brands get an editorial film, light sites a clean one, dark sans sites a tech one, and
    consumer brands with a strong colour a bold one."""
    heading = (kit['fonts'].get('heading') or '').lower()
    serif = any(name in heading for name in ('serif', 'garamond', 'playfair', 'bodoni', 'didot', 'baskerville', 'georgia', 'times', 'lora', 'merriweather', 'caslon', 'canela', 'tiempos', 'fraunces')) and 'sans' not in heading
    accent = kit['colors']['accent'].lstrip('#'); r, g, b = (int(accent[i:i + 2], 16) for i in (0, 2, 4))
    vivid = (max(r, g, b) - min(r, g, b)) / max(1, max(r, g, b)) > .55
    if kit.get('industry') in ('commerce', 'food', 'education') and vivid: return 'bold'
    if serif: return 'editorial'
    return 'tech' if kit['colors']['dark'] else 'clean'


def compose(kit, aspect='16:9'):
    """Scenes for the renderer. Each scene has a type, its copy and a duration in seconds."""
    copy = kit['copy']; scenes = []
    hero = [trim(s, 7) for s in sentences(copy['hero'])][:3] or [trim(copy['hero'], 8)]
    offer = offer_line(kit)
    if offer and offer.casefold() in ' '.join(hero).casefold(): offer = None
    scenes.append({'type': 'statement', 'lines': [line(s) for s in hero], 'camera': 'dolly_in', 'duration': duration(*hero)})
    if offer and kit.get('hero_image'):
        scenes.append({'type': 'photo', 'image': kit['hero_image'], 'lines': [line(offer)], 'camera': 'dolly_in', 'duration': duration(offer, base=2.0)})
    elif offer:
        scenes.append({'type': 'statement', 'lines': [line(offer)], 'camera': 'drift', 'duration': duration(offer)})

    features = copy.get('features', [])[:4]
    if len(features) >= 3:
        items = [{'eyebrow': c.get('eyebrow', ''), 'title': c['title'], 'body': trim(c['body'], 11)} for c in features]
        scenes.append({'type': 'grid', 'title': 'What you get', 'items': items, 'camera': 'none', 'duration': round(1.6 + .9 * len(items), 2)})

    steps = copy.get('steps', [])[:4]
    if len(steps) >= 3:
        days = next((f for f in kit.get('figures', []) if re.search(r'day|week|hour', f['label'], re.I)), None)
        lead = f"Ready in {days['value']} {days['label']}." if days and re.search(r'\d', days['value']) else 'How it works.'
        scenes.append({'type': 'cards', 'lead': line(lead), 'items': [{'title': c['title'], 'body': trim(c['body'], 14)} for c in steps],
                       'camera': 'none', 'duration': round(1.0 + 1.7 * len(steps), 2)})

    # Stat labels keep their abbreviations ('avg. turnaround'), so they are cut by words, not sentences.
    stats = [{'value': c['title'].strip(), 'label': ' '.join(c['body'].split()[:4]).lower(), 'source': 'site'} for c in copy.get('stats', [])][:3]
    if not stats:
        stats = [{'value': f['value'], 'label': f['label'].lower(), 'source': f['line']} for f in kit.get('figures', []) if re.search(r'\d{2,}|\+|%', f['value'])][:3]
    if stats:
        scenes.append({'type': 'counters', 'items': stats, 'camera': 'dolly_in', 'duration': round(1.6 + 1.3 * len(stats), 2)})

    quote = next((c for c in copy.get('testimonials', []) if len(c['body'].split()) >= 6), None)
    if quote:
        said = trim(quote['body'].strip(' "“”'), 16)
        scenes.append({'type': 'quote', 'lines': [line(said)], 'camera': 'drift', 'duration': duration(said, base=1.8)})

    tagline = brand_line(kit)
    if tagline:
        scenes.append({'type': 'sweep', 'lines': [line(trim(tagline, 9))], 'camera': 'none', 'duration': duration(tagline, base=1.8)})
    scenes.append({'type': 'end', 'name': kit['name'], 'cta': copy.get('cta') or 'Get in touch', 'domain': kit['domain'],
                   'logo': kit.get('logo'), 'camera': 'none', 'duration': 3.0})

    # Keep the film short: drop the least important optional scenes first until it fits.
    for kind in ('sweep', 'cards', 'quote', 'grid', 'counters'):
        if sum(s['duration'] for s in scenes) <= MAX_SECONDS: break
        scenes = [s for s in scenes if s['type'] != kind]
    look = direction(kit)
    # Hand-overs vary by direction and brand, so cuts never feel identical across films.
    seed = int(hashlib.sha1(kit['domain'].encode()).hexdigest(), 16)
    styles = {'editorial': ('dissolve', 'whip'), 'clean': ('slide', 'dissolve'), 'tech': ('whip', 'slide'), 'bold': ('wipe', 'slide')}[look]
    for index, scene in enumerate(scenes):
        scene['transition_in'] = 'none' if index == 0 else styles[(index + seed) % 2]
    return {'aspect': aspect, 'direction': look, 'industry': kit.get('industry', 'general'),
            'brief': {'offer': offer, 'field': kit.get('industry', 'general')}, 'scenes': scenes,
            'total': round(sum(s['duration'] for s in scenes), 2)}
