import pytest
from PIL import Image
from app.core.models import MotionGraphicItem, CaptionItem, WordTiming
from app.services.title_styles import STYLES, split_mixed_typography, arrange_title, choose_title_style
from app.services.burnin_renderer import render_bounding_box_svg, render_editorial_text, FontManager
from app.services.subject_layers import prepare_subject_layers, FACE_SAFE_STYLES


def test_styles_includes_mixed_typography():
    assert 'mixed_typography' in STYLES
    assert 'mixed_typography' in FACE_SAFE_STYLES


def test_split_mixed_typography():
    # Single word
    setup, accent = split_mixed_typography(['REVELATION'])
    assert setup == ""
    assert accent == "REVELATION"

    # Two words
    setup, accent = split_mixed_typography(['HIDDEN', 'COST'])
    assert setup == "HIDDEN"
    assert accent == "COST"

    # Multi-word with punchword at end
    setup, accent = split_mixed_typography(['THE', 'BIGGEST', 'MISTAKE'])
    assert "THE" in setup
    assert "MISTAKE" in accent

    # Number word as accent
    setup, accent = split_mixed_typography(['THREE', 'FATAL', 'FLAWS'])
    assert "THREE" in accent
    assert "FATAL FLAWS" in setup or "FLAWS" in setup


def test_arrange_title_mixed_typography():
    graphic = MotionGraphicItem(
        id='test_mg_1',
        start=1.0,
        end=4.0,
        template_id='kinetic_typography',
        title='THE SECRET OF LONGEVITY',
        pos_x=0.5,
        pos_y=0.5,
        scale=1.0,
        parameters={}
    )
    arrange_title(graphic, 'mixed_typography')
    
    assert graphic.parameters['title_style'] == 'mixed_typography'
    assert 'setup_text' in graphic.parameters
    assert 'accent_text' in graphic.parameters
    assert graphic.parameters['accent_color'] == '#E04F26'
    assert graphic.parameters['setup_color'] == '#FFFFFF'
    assert graphic.parameters['bounding_box_highlight'] is True
    assert graphic.parameters['box_rotation'] == -3.0
    assert len(graphic.parameters['title_lines']) == 2
    assert graphic.parameters['title_lines'][0]['text'] == graphic.parameters['setup_text']
    assert graphic.parameters['title_lines'][1]['text'] == graphic.parameters['accent_text']


def test_choose_title_style_mixed_typography():
    g1 = MotionGraphicItem(
        id='g1', start=0, end=2, template_id='mixed_typography_title',
        title='Title', pos_x=0.5, pos_y=0.5, scale=1.0, parameters={}
    )
    assert choose_title_style(g1) == 'mixed_typography'

    g2 = MotionGraphicItem(
        id='g2', start=0, end=2, template_id='kinetic_typography',
        title='Title', pos_x=0.5, pos_y=0.5, scale=1.0, parameters={'title_style': 'mixed_typography'}
    )
    assert choose_title_style(g2) == 'mixed_typography'


def test_render_bounding_box_svg_geometry():
    box_w, box_h = 240, 70
    stroke_color = '#E04F26'
    img = render_bounding_box_svg(box_w, box_h, stroke_color=stroke_color, stroke_width=2, handle_size=8, padding=4)
    
    assert isinstance(img, Image.Image)
    assert img.mode == 'RGBA'
    assert img.width >= box_w + 16
    assert img.height >= box_h + 16

    pixels = img.load()
    found_orange = False
    for x in range(img.width):
        for y in range(img.height):
            r, g, b, a = pixels[x, y]
            if a > 200 and r > 200 and g < 100 and b < 60:
                found_orange = True
                break
        if found_orange:
            break
    assert found_orange, "Expected #E04F26 color in rendered bounding box"


def test_render_editorial_text_mixed_typography():
    canvas = Image.new('RGBA', (720, 1280), (10, 10, 10, 255))
    fonts = FontManager()
    
    graphic = MotionGraphicItem(
        id='test_render_mg',
        start=0.0,
        end=3.0,
        template_id='kinetic_typography',
        title='DON’T MAKE THIS MISTAKE',
        pos_x=0.5,
        pos_y=0.5,
        scale=1.0,
        parameters={
            'title_style': 'mixed_typography',
            'setup_text': 'DON’T MAKE THIS',
            'accent_text': 'MISTAKE',
            'setup_color': '#FFFFFF',
            'accent_color': '#E04F26',
            'bounding_box_highlight': True,
            'box_rotation': -3.0
        }
    )
    
    render_editorial_text(canvas, graphic, width=720, height=1280, fonts=fonts, t=1.0)
    
    pixels = canvas.load()
    non_bg_pixels = 0
    for x in range(100, 620, 10):
        for y in range(400, 800, 10):
            r, g, b, a = pixels[x, y]
            if (r, g, b) != (10, 10, 10):
                non_bg_pixels += 1
    assert non_bg_pixels > 0, "Mixed typography should draw onto canvas"


def test_subject_layers_recognition():
    class DummyState:
        id = "dummy_proj"
    
    g_mixed = MotionGraphicItem(
        id='g_m', start=0, end=2, template_id='kinetic_typography',
        title='Test', pos_x=0.5, pos_y=0.5, scale=1.0,
        parameters={'title_style': 'mixed_typography', 'behind_subject': True}
    )
    g_plain = MotionGraphicItem(
        id='g_p', start=0, end=2, template_id='kinetic_typography',
        title='Test', pos_x=0.5, pos_y=0.5, scale=1.0,
        parameters={'title_style': 'rise'}
    )
    
    prepare_subject_layers(DummyState(), [g_plain, g_mixed])
    assert 'subject_mask_error' not in g_plain.parameters
    assert 'subject_mask_error' in g_mixed.parameters
