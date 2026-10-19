"""Brand film: brand-kit extraction rules, script composition and job safety, without a browser or network."""
import pytest
from app.services.brand_video import site_reader as reader, script, jobs


def raw(**overrides):
    base = dict(body_background='rgb(11, 11, 14)', html_background='rgba(0, 0, 0, 0)', text_color='rgb(237, 234, 226)', theme_color='',
                actions=[dict(text='BOOK A STRATEGY CALL', background='rgb(212, 175, 55)', color='rgb(11,11,14)', area=9000),
                         dict(text='☀️ LIGHT', background='rgb(40,40,40)', color='rgb(252,246,186)', area=20000),
                         dict(text='Home', background='rgba(0,0,0,0)', color='rgb(237,234,226)', area=800)])
    return base | overrides


def test_palette_takes_background_text_and_the_saturated_accent():
    colors = reader.palette(raw())
    assert colors['background'] == '#0b0b0e' and colors['text'] == '#edeae2' and colors['accent'] == '#d4af37' and colors['dark']


def test_call_to_action_is_the_action_verb_button_not_a_theme_toggle():
    assert reader.pick_cta(raw()['actions']) == 'BOOK A STRATEGY CALL'
    assert reader.pick_cta([dict(text='Pricing', background='rgb(1,2,3)', color='', area=50)]) == 'Pricing'


def test_card_groups_are_sorted_by_what_they_are():
    groups = [[card('★★★★★', '"Great work."'), card('★★★★★', '"Fast team."'), card('★★★★★', '"Loved it."')],
              [card('30+', 'CLIPS'), card('5 days', 'TURNAROUND'), card('5M+', 'VIEWS')],
              [card('Strategy call', 'We map your goals.', 'FRAME 01'), card('Footage intake', 'You drop files.', 'FRAME 02'), card('Edit & review', 'We cut.', 'FRAME 03')],
              [card('ABOUT', 'SERVICES CONTACT'), card('CONSULTING', 'TECHNOLOGY PLATFORMS'), card('Contact', 'HEAD OFFICE DUBAI')],
              [card('Driven by Human Insights', 'Committed to elevating the lifestyle at large, we enrich aspirations.'),
               card('Enabled with latest Technology', 'Making the most of advancements we are engineering solutions.'),
               card('Personalized to local feel', 'Evolving with the diverse communities across the globe today.')]]
    out = reader.classify_groups(groups)
    assert [c['title'] for c in out['features']] == ['Driven by Human Insights', 'Enabled with latest Technology', 'Personalized to local feel']
    assert out['steps'][0]['title'] == 'Strategy call' and out['stats'][0]['title'] == '30+' and len(out['testimonials']) == 3


def test_industry_is_read_from_the_copy():
    assert reader.industry('Redefining the way financial transactions are performed for banks and lenders') == 'finance'
    assert reader.industry('Hello and welcome') == 'general'


def test_figures_keep_the_number_and_a_short_label():
    found = reader.figures(['Dedicated clip channels that turn one episode into 30+ assets, built to dominate feeds.', 'Founded in 2019 by two editors.'])
    assert [(f['value'], f['label']) for f in found] == [('30+', 'assets')]


def kit(**copy):
    base = {'hero': 'Great video editing. Limitless creativity. Powered by AI.', 'hero_body': '', 'cta': 'BOOK A STRATEGY CALL',
            'paragraphs': [], 'sections': [], 'features': [], 'steps': [], 'stats': [], 'testimonials': [], 'faq': []}
    return {'name': 'OONEX', 'domain': 'oonex.in', 'description': '', 'logo': None, 'images': [], 'figures': [], 'hero_image': None,
            'industry': 'agency', 'colors': {'background': '#0b0b0e', 'text': '#edeae2', 'accent': '#d4af37', 'dark': True},
            'fonts': {'heading': 'Instrument Serif', 'body': 'Inter'}, 'copy': base | copy}


def card(title, body, eyebrow=''):
    return {'eyebrow': eyebrow, 'title': title, 'body': body}


def test_script_tells_what_the_company_does_from_site_copy():
    plan = script.compose(kit(
        hero_body='OONEX is a creative operating system combining premium editing and proprietary tools.',
        features=[card('Podcasts & Hooks', 'We structure the hooks inside your long-form content.', 'STORYTELLING'),
                  card('Viral Clipping', 'Dedicated clip channels that turn one episode into 30+ assets.'),
                  card('SaaS Explainers', 'Crystal-clear product demos that convert cold leads.')],
        stats=[card('30+', 'CLIPS PER EPISODE'), card('5 days', 'AVG. TURNAROUND')],
        testimonials=[card('★★★★★', '"OONEX turned one hour of raw podcast footage into a month of content."')],
        paragraphs=['Everything runs through one system, built for a single outcome: authority that compounds.']))
    scenes = {s['type']: s for s in plan['scenes']}
    assert [s['type'] for s in plan['scenes']] == ['statement', 'statement', 'grid', 'counters', 'quote', 'sweep', 'end']
    assert plan['scenes'][1]['lines'][0]['text'].startswith('OONEX is a creative operating system')
    assert [i['title'] for i in scenes['grid']['items']] == ['Podcasts & Hooks', 'Viral Clipping', 'SaaS Explainers']
    assert [(i['value'], i['label']) for i in scenes['counters']['items']] == [('30+', 'clips per episode'), ('5 days', 'avg. turnaround')]
    assert scenes['quote']['lines'][0]['text'].startswith('OONEX turned one hour')
    assert scenes['sweep']['lines'][0]['text'] == 'Authority that compounds.'
    assert plan['direction'] == 'editorial' and plan['total'] <= script.MAX_SECONDS


def test_a_light_finance_site_gets_its_offer_over_its_photo_and_a_clean_look():
    k = kit(hero='Envisioning the Future', cta='CONTACT',
            hero_body='We are developing pioneer solutions that will enable the next level growth and financial inclusion of local businesses.',
            sections=[{'heading': 'Redefining The Way Financial Transactions Are Performed', 'body': '', 'level': 1, 'group': 5}],
            features=[card('Driven by Human Insights', 'Committed to elevating the lifestyle at large.'),
                      card('Enabled with latest Technology', 'Engineering sustainable solutions.'),
                      card('Personalized to local feel', 'Evolving with diverse communities.')],
            paragraphs=['Axieva Inc. All rights to everything we do.'])
    k.update(name='Axieva', domain='axieva.com', industry='finance', hero_image='hero.jpg',
             colors={'background': '#ffffff', 'text': '#000000', 'accent': '#a2896c', 'dark': False}, fonts={'heading': 'Open Sans', 'body': 'Open Sans'})
    plan = script.compose(k)
    assert [s['type'] for s in plan['scenes']][:3] == ['statement', 'photo', 'grid']
    assert plan['scenes'][1]['lines'][0]['text'] == 'Redefining The Way Financial Transactions Are Performed'
    assert plan['direction'] == 'clean' and plan['scenes'][-1]['cta'] == 'CONTACT'


def test_directions_follow_the_brand():
    assert script.direction(kit()) == 'editorial'
    dark_sans = kit(); dark_sans['fonts'] = {'heading': 'Inter'}
    assert script.direction(dark_sans) == 'tech'
    shop = kit(); shop.update(industry='commerce', colors={'background': '#ffffff', 'text': '#111111', 'accent': '#ff3b30', 'dark': False}); shop['fonts'] = {'heading': 'Poppins'}
    assert script.direction(shop) == 'bold'


def test_missing_sections_are_skipped_not_invented():
    plan = script.compose(kit())
    assert [s['type'] for s in plan['scenes']] == ['statement', 'end']


def test_accent_falls_on_the_turn_of_the_line():
    assert script.line('Raw to ready in 5 business days.')['accent_from'] == 5
    assert script.line('Hello')['accent_from'] == 1


def test_jobs_accept_only_public_sites_and_safe_ids():
    for bad in ('localhost:8003', 'http://127.0.0.1/admin', 'ftp://oonex.in', 'not a site'):
        with pytest.raises(ValueError):
            jobs.start(bad)
    with pytest.raises(ValueError):
        jobs.start('oonex.in', aspect='4:3')
    with pytest.raises(ValueError):
        jobs.folder('../../etc')


def test_studio_check_accepts_a_pure_film_and_rejects_hidden_time(monkeypatch, tmp_path):
    from app.services.brand_video import studio
    monkeypatch.setattr(jobs, 'ROOT', tmp_path)
    state = jobs.create('example.com', '16:9', status='designing')
    folder = jobs.folder(state['id'])
    good = '''<html><body style="margin:0;background:#fff"><div id="box" style="position:absolute;width:200px;height:200px;background:#123"></div>
<script>window.TOTAL = 3; window.seek = t => { document.getElementById('box').style.left = (t * 300) + 'px'; }; window.seek(0);</script></body></html>'''
    (folder / 'film.html').write_text(good)
    problems, sheet = studio.check(state['id'], [0.5, 2.0])
    assert problems == [] and sheet and sheet.exists()
    (folder / 'film.html').write_text(good.replace("(t * 300) + 'px'", "(Math.random() * 1500) + 'px'"))
    problems, _ = studio.check(state['id'], [1.0])
    assert any('Math.random' in p for p in problems) and any('different when revisited' in p for p in problems)
    (folder / 'film.html').write_text('<html><body><script>window.seek = t => {};</script></body></html>')
    assert any('TOTAL' in p for p in studio.check(state['id'], [0])[0])
