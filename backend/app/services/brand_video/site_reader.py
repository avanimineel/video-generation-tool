"""Read a website in Chrome and keep what makes the brand recognisable: a reusable brand kit.

The kit holds the name, palette, type, logo, pitch copy, figures and imagery. It is saved per
brand so later videos (and reel titles) reuse it without reading the site again.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

EXTRACT_JS = r"""
() => {
  const legal = /©|all rights reserved|privacy policy|cookie|terms of (use|service)/i;
  // Footers, legal lines and cookie banners never describe the business.
  const visible = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && Number(s.opacity) > 0.05
      && !el.closest('footer,[class*="footer"],[class*="cookie"],[id*="cookie"]') && !legal.test(el.innerText || ''); };
  const text = el => (el.innerText || '').replace(/\s+/g, ' ').trim();
  const family = el => el ? getComputedStyle(el).fontFamily.split(',')[0].replace(/["']/g, '').trim() : '';
  const meta = name => (document.querySelector(`meta[property="${name}"],meta[name="${name}"]`) || {}).content || '';
  // Each heading keeps the first short paragraph that follows it, so steps and services carry their own line.
  const after = h => { let el = h; for (let i = 0; i < 6 && el; i++) { el = el.nextElementSibling || (el.parentElement && el.parentElement.nextElementSibling);
      if (el && /^(P|DIV|SPAN)$/.test(el.tagName) && text(el).length >= 20 && text(el).length <= 200 && !el.querySelector('h1,h2,h3')) return text(el); } return ''; };
  const headings = [...document.querySelectorAll('h1,h2,h3')].filter(visible)
    .map(h => { const block = h.closest('section,[id]'); return {level: Number(h.tagName[1]), text: text(h), body: after(h), top: h.getBoundingClientRect().top + scrollY,
      group: block ? [...document.querySelectorAll('section,[id]')].indexOf(block) : -1}; }).filter(h => h.text.length > 1 && h.text.length < 160);
  const paragraphs = [...document.querySelectorAll('p,li')].filter(visible).map(text).filter(t => t.length >= 25 && t.length <= 240);
  const actions = [...document.querySelectorAll('a,button')].filter(visible).map(el => {
    const s = getComputedStyle(el); return {text: text(el), background: s.backgroundColor, color: s.color, area: el.offsetWidth * el.offsetHeight};
  }).filter(a => a.text && a.text.length <= 40);
  const images = [...document.querySelectorAll('img')].filter(visible).map(img => ({
    src: img.currentSrc || img.src, alt: img.alt || '', width: img.naturalWidth, height: img.naturalHeight,
    logo: /logo|brand/i.test(img.src + ' ' + img.alt + ' ' + img.className + ' ' + (img.closest('header,nav') ? 'header' : ''))
  })).filter(i => i.src && !i.src.startsWith('data:'));
  const headerSvg = document.querySelector('header svg, nav svg, a[href="/"] svg');
  const icons = [...document.querySelectorAll('link[rel~="icon"],link[rel="apple-touch-icon"]')].map(l => ({href: l.href, sizes: l.sizes ? String(l.sizes) : ''}));
  const fontLinks = [...document.querySelectorAll('link[href*="fonts.googleapis.com"]')].map(l => l.href);
  const loaded = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, ''));
  const h1 = document.querySelector('h1');
  // Repeated sibling blocks that each hold a short title and a sentence: features, pillars, services, plans.
  const lines = el => (el.innerText || '').split('\n').map(t => t.replace(/\s+/g, ' ').trim()).filter(Boolean);
  // A small label above the title ("STORYTELLING", "FRAME 01", "Step 2") is kept apart as the eyebrow.
  const eyebrowLike = t => t.length <= 24 && (t === t.toUpperCase() && /[A-Z]/.test(t) || /^(step|frame|phase|stage|0?\d+)\b/i.test(t));
  const cardOf = el => { let parts = lines(el); if (parts.length < 2) return null;
    let eyebrow = '';
    if (parts.length >= 3 && eyebrowLike(parts[0]) && !eyebrowLike(parts[1])) { eyebrow = parts[0]; parts = parts.slice(1); }
    const title = parts[0], body = parts.slice(1).join(' ');
    return title.split(' ').length <= 8 && title.length <= 60 && body.length >= 3 && body.length <= 320 ? {eyebrow, title, body} : null; };
  const groups = []; const seen = new Set();
  for (const parent of document.querySelectorAll('body *')) {
    const kids = [...parent.children].filter(visible);
    if (kids.length < 3 || kids.length > 12) continue;
    const cards = kids.map(cardOf).filter(Boolean);
    if (cards.length < 3 || cards.length < kids.length * .6) continue;
    const key = cards.map(c => c.title).join('|'); if (seen.has(key)) continue; seen.add(key);
    groups.push({top: parent.getBoundingClientRect().top + scrollY, cards: cards.slice(0, 8)});
    if (groups.length >= 8) break;
  }
  const heroImage = [...document.querySelectorAll('img')].filter(visible)
    .map(img => ({src: img.currentSrc || img.src, area: img.getBoundingClientRect().width * img.getBoundingClientRect().height, top: img.getBoundingClientRect().top + scrollY}))
    .filter(i => i.src && !i.src.startsWith('data:') && i.top < innerHeight * 1.2 && i.area > 60000).sort((a, b) => b.area - a.area)[0];
  const bg = [...document.querySelectorAll('section,header,div')].slice(0, 400).map(el => getComputedStyle(el).backgroundImage)
    .map(b => (b.match(/url\(["']?([^"')]+)["']?\)/) || [])[1]).filter(Boolean)[0] || '';
  return {
    hero_body: h1 ? after(h1) : '', card_groups: groups, hero_image: heroImage ? heroImage.src : bg,
    title: document.title, description: meta('description') || meta('og:description'), site_name: meta('og:site_name'),
    og_image: meta('og:image'), theme_color: meta('theme-color'),
    body_background: getComputedStyle(document.body).backgroundColor, html_background: getComputedStyle(document.documentElement).backgroundColor,
    text_color: getComputedStyle(h1 || document.body).color, body_color: getComputedStyle(document.body).color,
    heading_font: family(h1 || document.querySelector('h2')), body_font: family(document.querySelector('p') || document.body),
    headings, paragraphs: [...new Set(paragraphs)].slice(0, 40), actions, images, icons, font_links: fontLinks, loaded_fonts: [...new Set(loaded)],
    header_svg: headerSvg ? headerSvg.outerHTML.slice(0, 60000) : '', page_height: document.body.scrollHeight
  };
}
"""

GENERIC_ACTIONS = {'home', 'about', 'menu', 'close', 'login', 'log in', 'sign in', 'blog', 'faq', 'privacy', 'terms', 'careers', 'next', 'previous'}


def rgb(value):
    """'rgb(1, 2, 3)' or 'rgba(...)' or '#abc' to (r, g, b, alpha), or None."""
    value = (value or '').strip()
    if value.startswith('#'):
        h = value[1:]
        if len(h) == 3: h = ''.join(c * 2 for c in h)
        if len(h) >= 6: return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0
        return None
    nums = re.findall(r'[\d.]+', value)
    if len(nums) >= 3:
        return int(float(nums[0])), int(float(nums[1])), int(float(nums[2])), float(nums[3]) if len(nums) > 3 else 1.0
    return None


def hex_color(c):
    return '#%02x%02x%02x' % c[:3]


def saturation(c):
    hi, lo = max(c[:3]), min(c[:3])
    return 0 if hi == 0 else (hi - lo) / hi


def luminance(c):
    return (.2126 * c[0] + .7152 * c[1] + .0722 * c[2]) / 255


def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])) ** .5


def palette(raw):
    """Background, text and one accent: the most saturated colour the site gives real visual weight to."""
    background = next((c for c in (rgb(raw['body_background']), rgb(raw['html_background'])) if c and c[3] > .5), (255, 255, 255, 1))
    text = rgb(raw['text_color']) or ((20, 20, 20, 1) if luminance(background) > .5 else (245, 245, 245, 1))
    weights = {}
    for action in raw['actions']:
        for key in ('background', 'color'):
            c = rgb(action[key])
            if c and c[3] > .5 and distance(c, background) > 60 and saturation(c) > .25:
                weights[c[:3]] = weights.get(c[:3], 0) + max(1, action['area']) * (2 if key == 'background' else 1)
    theme = rgb(raw.get('theme_color'))
    if theme and saturation(theme) > .25 and distance(theme, background) > 60:
        weights[theme[:3]] = weights.get(theme[:3], 0) + 10 ** 9
    # Of the three most prominent colours, the most saturated reads as the accent (gold over pale cream).
    accent = max(sorted(weights, key=weights.get, reverse=True)[:3], key=saturation) if weights else None
    if accent is None:
        accent = (214, 170, 72) if luminance(background) < .5 else (196, 120, 48)  # Warm gold default, as in the reference taste.
    ranked = sorted(weights, key=weights.get, reverse=True)
    return {'background': hex_color(background), 'text': hex_color(text), 'accent': hex_color(accent),
            'palette': [hex_color(c) for c in ranked[:5]], 'dark': luminance(background) < .5,
            'accent_source': 'theme-color or most prominent buttons' if weights else 'default (site has no strong accent)'}


def google_family(name, font_links, loaded):
    """The family name if Google Fonts can serve it (the site links it, or it is a known Google family)."""
    if not name: return None
    slug = name.replace(' ', '+')
    if any(slug.lower() in link.lower() or name.lower() in link.lower() for link in font_links):
        return name
    return name if name in loaded and not name.lower().startswith(('-apple', 'system', 'helvetica', 'arial', 'times', 'georgia')) else None


FIGURE = re.compile(r'(\d[\d,.]*\s*(?:\+|%|x|k|m|days?|hours?|weeks?|months?|years?|clips?|videos?|clients?|brands?|creators?)?)\s+([A-Za-z][\w\s-]{2,40})', re.I)


def figures(lines):
    """Short claims that carry a number ("30+ assets"), the material for counter scenes. The label is the
    one to three words after the figure, cut at the first function word."""
    found = []
    for line in lines:
        if len(line) > 200: continue
        match = FIGURE.search(line)
        if not match or not re.search(r'\d', match.group(1)) or re.search(r'\b(19|20)\d\d\b', match.group(1)): continue
        words = []
        for word in match.group(2).split():
            if word.lower() in ('a', 'an', 'the', 'and', 'or', 'to', 'in', 'on', 'at', 'for', 'of', 'with', 'that', 'built', 'by') or len(words) == 3: break
            words.append(word.strip('.,'))
        if words:
            found.append({'value': match.group(1).strip(), 'label': ' '.join(words), 'line': line})
    return found[:6]


CTA_VERBS = re.compile(r'\b(book|get|start|try|contact|schedule|call|demo|join|sign up|buy|shop|hire|talk|request|apply|claim|download)\b', re.I)


def pick_cta(actions):
    """The call to action the site pushes hardest: a styled button with an action verb, else its biggest real button."""
    candidates = [a for a in actions if a['text'].lower() not in GENERIC_ACTIONS and len(a['text'].split()) <= 6
                  and re.search(r'[A-Za-z]{3}', a['text']) and not re.search(r'[\u2600-\u27bf\U0001F300-\U0001FAFF]', a['text'])]
    verbs = [a for a in candidates if CTA_VERBS.search(a['text'])]
    if verbs: return max(verbs, key=lambda a: a['area'])['text']
    styled = [a for a in candidates if (rgb(a['background']) or (0, 0, 0, 0))[3] > .5]
    best = max(styled or candidates, key=lambda a: a['area'], default=None)
    return best['text'] if best else 'Get in touch'


def brand_name(raw, domain):
    for source in (raw.get('site_name'), re.split(r'\s+[|\-–—:·]\s+', raw.get('title') or '')[0]):
        if source and 1 < len(source) <= 30: return source.strip()
    return domain.split('.')[0].capitalize()


INDUSTRIES = {
    'finance': r'financ|payment|bank|lend|loan|invest|wealth|insur|fintech|transaction|credit|wallet',
    'software': r'saas|software|platform|api|cloud|dashboard|automat|integrat|app\b|developer',
    'agency': r'agency|studio|editing|design|branding|marketing|creative|content|video|campaign',
    'health': r'health|clinic|patient|doctor|medical|care\b|wellness|therapy|hospital',
    'commerce': r'shop|store|product|cart|order|shipping|collection|buy|sale',
    'education': r'course|learn|student|teach|school|academy|training|class',
    'property': r'real estate|property|apartment|home|rent|villa|construction',
    'food': r'restaurant|food|menu|cafe|coffee|kitchen|recipe|dining'}


def industry(text):
    """The field the site talks about most, by keyword frequency; 'general' when nothing stands out."""
    text = text.casefold()
    scores = {name: len(re.findall(pattern, text)) for name, pattern in INDUSTRIES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else 'general'


STEP_LABEL = re.compile(r'^(step|frame|phase|stage)\s*0?\d|^0?\d+$', re.I)
STEP_WORD = re.compile(r'\b(call|intake|drop|review|publish|deliver|launch|onboard|plan|map|build|ship|edit|repeat|kickoff|brief|sign up|install|connect|discover|design|develop|test)\b', re.I)


def classify_groups(groups):
    """Sort repeated card groups by what they are: steps, stats, testimonials, questions or features."""
    out = {'features': [], 'steps': [], 'stats': [], 'testimonials': [], 'faq': []}; features = []
    for cards in groups:
        titles = [c['title'] for c in cards]; bodies = [c['body'] for c in cards]
        if all(re.search(r'★|☆', t) or b.lstrip().startswith(('"', '“')) for t, b in zip(titles, bodies)):
            kind = 'testimonials'
        elif sum(t.rstrip().endswith('?') for t in titles) >= len(titles) * .6:
            kind = 'faq'
        elif sum(bool(re.match(r'^[+\-~]?\d[\d,.]*\s*[%+xkmb]*\s*$', t, re.I)) for t in titles) >= len(titles) * .6:
            kind = 'stats'
        elif sum(bool(STEP_LABEL.search(c.get('eyebrow', ''))) or bool(STEP_WORD.search(c['title'])) for c in cards) >= len(cards) * .6:
            kind = 'steps'
        else:
            kind = 'features'
        if kind == 'features':
            features.append(cards)
        elif not out[kind]:
            out[kind] = cards
    # Real feature cards: a readable title over a full sentence. Page-wide wrappers and nav strips score low.
    def readable(card):
        return card['title'] != card['title'].upper() and len(re.findall(r'\b[a-z]{3,}\b', card['body'])) >= 4 and len(card['body']) <= 260
    scored = [(sum(map(readable, cards)) / len(cards), len(cards), cards) for cards in features]
    best = max((s for s in scored if s[0] >= .75), default=None, key=lambda s: (s[0], s[1]))
    out['features'] = best[2] if best else []
    return out


def copy_text(raw):
    return ' '.join([h['text'] for h in raw['headings']] + raw['paragraphs'] + [c['title'] + ' ' + c['body'] for g in raw.get('card_groups', []) for c in g['cards']])


def download(url, folder, name):
    try:
        response = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0 brand-kit-reader'})
        response.raise_for_status()
        kind = response.headers.get('content-type', '')
        if not kind.startswith('image/'): return None
        suffix = {'image/svg+xml': '.svg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif'}.get(kind.split(';')[0], '.jpg')
        path = folder / (name + suffix)
        path.write_bytes(response.content)
        return path
    except requests.RequestException:
        return None


def read_site(url, out_dir, browser=None):
    """Render the page in Chrome, extract the brand kit, download logo and key images, save brand_kit.json."""
    from playwright.sync_api import sync_playwright
    if not urlparse(url).scheme: url = 'https://' + url
    domain = urlparse(url).netloc.removeprefix('www.')
    folder = Path(out_dir); assets = folder / 'assets'; assets.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        chrome = browser or p.chromium.launch(channel='chrome', headless=True)
        page = chrome.new_page(viewport={'width': 1440, 'height': 900})
        # Many sites never go network-idle (analytics, video); load plus a short settle is enough.
        page.goto(url, wait_until='load', timeout=45000)
        page.wait_for_timeout(1500)
        # Scroll once so lazy-loaded sections and images exist before reading.
        for y in range(0, 6000, 900):
            page.evaluate(f'window.scrollTo(0, {y})'); page.wait_for_timeout(120)
        page.evaluate('window.scrollTo(0, 0)'); page.wait_for_timeout(300)
        raw = page.evaluate(EXTRACT_JS)
        page.screenshot(path=str(folder / 'site.png'))
        if not browser: chrome.close()

    colors = palette(raw)
    headings = sorted(raw['headings'], key=lambda h: (h['top'], h['level']))
    hero = next((h['text'] for h in headings if h['level'] == 1), headings[0]['text'] if headings else raw['title'])
    sub = [h['text'] for h in headings if h['text'] != hero]
    lines = [h['text'] for h in headings] + raw['paragraphs']

    logo_path = None
    logo_images = [i for i in raw['images'] if i['logo']]
    if raw['header_svg'] and ('logo' in raw['header_svg'].lower() or not logo_images):
        logo_path = assets / 'logo.svg'; logo_path.write_text(raw['header_svg'])
    elif logo_images:
        logo_path = download(urljoin(url, logo_images[0]['src']), assets, 'logo')
    images = [i for i in raw['images'] if not i['logo'] and i['width'] >= 360 and i['height'] >= 200]
    images = sorted(images, key=lambda i: i['width'] * i['height'], reverse=True)[:12]
    if raw['og_image']: images.insert(0, {'src': urljoin(url, raw['og_image']), 'alt': 'social preview', 'width': 1200, 'height': 630})
    saved = []
    for index, image in enumerate(images[:12]):
        path = download(urljoin(url, image['src']), assets, f'image_{index:02d}_' + hashlib.sha1(image['src'].encode()).hexdigest()[:8])
        if path: saved.append({'path': str(path), 'alt': image['alt'], 'source': urljoin(url, image['src'])})

    kit = {
        'url': url, 'domain': domain, 'name': brand_name(raw, domain), 'title': raw['title'], 'description': raw['description'],
        'colors': colors,
        'fonts': {'heading': raw['heading_font'], 'body': raw['body_font'],
                  'heading_google': google_family(raw['heading_font'], raw['font_links'], raw['loaded_fonts']),
                  'body_google': google_family(raw['body_font'], raw['font_links'], raw['loaded_fonts'])},
        'logo': str(logo_path) if logo_path else None,
        'industry': industry(' '.join([raw['title'], raw['description'], copy_text(raw)])),
    'hero_image': None,
    'copy': {'hero': hero, 'hero_body': raw.get('hero_body', ''), 'subheadings': sub[:12], 'paragraphs': raw['paragraphs'][:20], 'cta': pick_cta(raw['actions']),
             **classify_groups([g['cards'] for g in sorted(raw.get('card_groups', []), key=lambda g: g['top'])]),
                 'sections': [{'heading': h['text'], 'body': h['body'], 'level': h['level'], 'group': h['group']} for h in headings if h['text'] != hero][:30]},
        'figures': figures(lines),
        'images': saved,
        'screenshot': str(folder / 'site.png'),
        'source_note': 'Extracted from the public website; images remain the brand owner\'s.'}
    if raw.get('hero_image'):
        hero_path = download(urljoin(url, raw['hero_image']), assets, 'hero')
        if hero_path: kit['hero_image'] = str(hero_path)
    (folder / 'brand_kit.json').write_text(json.dumps(kit, indent=2, ensure_ascii=False))
    return kit
