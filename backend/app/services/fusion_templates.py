from typing import Dict, Any, List
from app.core.models import CaptionStyle

class FusionTemplateGenerator:
    def generate_fusion_caption_setting(self, text: str, style: CaptionStyle, duration_frames: int = 90) -> str:
        corner_rad = min(0.5, style.corner_radius / 64.0)
        size_val = round(style.font_size / 500.0, 3)

        template = """{
    Tools = ordered() {
        SubtitleText = TextPlus {
            Inputs = {
                GlobalOut = Input { Value = %d, },
                Width = Input { Value = 1920, },
                Height = Input { Value = 1080, },
                Font = Input { Value = "%s", },
                Style = Input { Value = "%s", },
                Size = Input { Value = %.3f, },
                StyledText = Input { Value = "%s", },
                HorizontalJustificationNew = Input { Value = 3, },
                VerticalJustificationNew = Input { Value = 3, },
            },
        },
        BackgroundBox = Background {
            Inputs = {
                EffectMask = Input {
                    SourceOp = "BoxMask",
                    Source = "Mask",
                },
                Width = Input { Value = 1920, },
                Height = Input { Value = 1080, },
                TopLeftAlpha = Input { Value = %.2f, },
            },
        },
        BoxMask = RectangleMask {
            Inputs = {
                CornerRadius = Input { Value = %.3f, },
                Width = Input { Value = 0.45, },
                Height = Input { Value = 0.12, },
            },
        },
        MergeCaptions = Merge {
            Inputs = {
                Background = Input {
                    SourceOp = "BackgroundBox",
                    Source = "Output",
                },
                Foreground = Input {
                    SourceOp = "SubtitleText",
                    Source = "Output",
                },
            },
        },
    },
}
"""
        return template % (
            duration_frames,
            style.font_family,
            style.font_weight.capitalize(),
            size_val,
            text,
            style.background_opacity,
            corner_rad
        )

    def get_template_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                'id': 'split_silhouette_walking',
                'name': '50/50 Split Screen: Walking Silhouette & Curved Text',
                'category': 'Higgsfield High-End',
                'description': '50/50 split with talking head on left, electric chartreuse canvas on right with walking vector silhouette and curved text arc.',
                'default_params': {
                    'arc_text_top': 'It felt like',
                    'arc_text_bottom': 'walking away',
                    'bg_color': '#B4F000',
                    'silhouette_style': 'walking',
                    'split_mode': True
                }
            },
            {
                'id': 'split_silhouette_falling',
                'name': '50/50 Split Screen: Falling Silhouette & Inverted Arc',
                'category': 'Higgsfield High-End',
                'description': '50/50 split with athletic falling/jumping silhouette and curved text wrapping beneath.',
                'default_params': {
                    'arc_text_top': 'under',
                    'arc_text_bottom': 'my feet',
                    'bg_color': '#B4F000',
                    'silhouette_style': 'falling',
                    'split_mode': True
                }
            },
            {
                'id': 'kinetic_3d_block',
                'name': 'Giant 3D Block Kinetic Typography (WHAT TO DO)',
                'category': 'Higgsfield High-End',
                'description': 'Screen-filling ultra-compressed impact text with 3D extruded drop shadows and electric lime accents.',
                'default_params': {
                    'line_1': 'WHAT',
                    'line_2_word_1': 'TO',
                    'line_2_word_2': 'DO',
                    'primary_color': '#FFFFFF',
                    'accent_color': '#B4F000',
                    'shadow_depth': 8
                }
            },
            {
                'id': 'editorial_dual_font',
                'name': 'Editorial Dual-Font (Back then / I had no idea)',
                'category': 'Higgsfield High-End',
                'description': 'Bold modern sans-serif paired with luxury cursive serif italic accent.',
                'default_params': {
                    'headline': 'Back then',
                    'accent_word': 'I had',
                    'punchline': 'no idea.',
                    'primary_color': '#FFFFFF',
                    'accent_color': '#CCFF00'
                }
            },
            {
                'id': 'kinetic_typography',
                'name': 'Kinetic Typography Pop',
                'category': 'Text',
                'description': 'Paired white bold sans-serif with lime green accent serif typography and pop entrance.',
                'default_params': {
                    'headline': 'Back then',
                    'accent_word': 'I had',
                    'punchline': 'no idea.',
                    'primary_color': '#FFFFFF',
                    'accent_color': '#CCFF00'
                }
            },
            {
                'id': 'silhouette_curve',
                'name': 'Silhouette & Curved Arc Text',
                'category': 'Social & Metaphor',
                'description': 'Silhouette illustration on lime green background with typography curved in an arc.',
                'default_params': {
                    'arc_text_top': 'It felt like',
                    'arc_text_bottom': 'under my feet',
                    'bg_color': '#CCFF00'
                }
            },
            {
                'id': 'stat_counter',
                'name': 'Big Number & Stat Counter',
                'category': 'Data',
                'description': 'Animated numeric growth counter with percentage badge and smooth count-up spline.',
                'default_params': {
                    'start_value': '$2M',
                    'end_value': '$12M',
                    'sub_badge': '+500% Revenue',
                    'badge_color': '#CCFF00',
                    'duration_sec': 2.5
                }
            },
            {
                'id': 'split_screen_vertical',
                'name': '50/50 Vertical Split (B-Roll Top / Speaker Bottom)',
                'category': 'Spatial & Documentary',
                'description': 'Dynamic canvas split with archival B-roll on top (featuring source credit) and talking head on bottom.',
                'default_params': {
                    'broll_title': 'Archival Flight Footage',
                    'speaker_label': 'Narrator',
                    'source_citation': 'Source: NASA Historical Archives',
                    'split_ratio': 0.5,
                    'divider_color': '#FFFFFF'
                }
            },
            {
                'id': 'dimension_callout',
                'name': 'Architectural Dimension Line & Measurement',
                'category': 'Spatial & Documentary',
                'description': 'Animated blueprint-style dimension line with tick marks, arrows, and measurement tag pill.',
                'default_params': {
                    'measurement_text': '14 FEET LONG',
                    'subtext': 'Fuselage Wingspan Spec',
                    'line_orientation': 'horizontal',
                    'line_length_pct': 65,
                    'color': '#00F0FF'
                }
            },
            {
                'id': 'source_citation',
                'name': 'Automated Source Citation Overlay',
                'category': 'Spatial & Documentary',
                'description': 'Unobtrusive documentary text overlay anchored in the top-left corner establishing archival credibility.',
                'default_params': {
                    'source_name': 'Source: National Archives (1969)',
                    'doc_type': 'Declassified Mission Footage',
                    'position': 'top_left'
                }
            },
            {
                'id': 'archival_filter',
                'name': 'Mixed-Media Archival Treatment (16mm Grain / B&W)',
                'category': 'Spatial & Documentary',
                'description': 'Cohesive mixed-media treatment applying 16mm film grain, vintage vignette, and contrast grade.',
                'default_params': {
                    'filter_style': '16mm_film_grain',
                    'grain_intensity': 0.45,
                    'vignette_depth': 0.55
                }
            },
            {
                'id': 'corner_bug',
                'name': 'Static Top-Right Corner Bug Watermark',
                'category': 'Spatial & Documentary',
                'description': 'Fixed high-contrast brand watermark anchored in the top-right corner across all scenes.',
                'default_params': {
                    'bug_text': 'CHRONICLES',
                    'badge_style': 'minimal_high_contrast',
                    'position': 'top_right'
                }
            },
            {
                'id': 'documentary_outro',
                'name': '3D Rotating Globe Outro & Teaser Carousel',
                'category': 'Spatial & Documentary',
                'description': 'Environmental 3D rotating wireframe globe, episode teaser carousel, and urgent retention CTA.',
                'default_params': {
                    'globe_headline': 'MISSION LOG COMPLETE',
                    'teaser_1': 'Part II: The Stratosphere',
                    'teaser_2': 'Part III: Deep Oceanic Trench',
                    'cta_text': 'SUBSCRIBE FOR NEXT EPISODE'
                }
            }
        ]

    def generate_motion_graphic_comp(self, template_id: str, params: Dict[str, Any], duration_frames: int = 90) -> str:
        if template_id in ['kinetic_typography', 'editorial_dual_font']:
            headline = params.get('headline', 'Back then')
            accent_word = params.get('accent_word', 'I had')
            punchline = params.get('punchline', 'no idea.')
            return f"""{{
    Tools = ordered() {{
        TextHeadline = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.12, }},
                StyledText = Input {{ Value = "{headline} {accent_word} {punchline}", }},
                Center = Input {{ Value = {{ 0.5, 0.5 }}, }},
            }},
        }},
        MergeElements = Merge {{
            Inputs = {{
                Background = Input {{ SourceOp = "TextHeadline", Source = "Output", }},
                Foreground = Input {{ SourceOp = "TextHeadline", Source = "Output", }},
            }},
        }},
    }},
}}"""

        if template_id == 'kinetic_3d_block':
            l1 = params.get('line_1', 'WHAT')
            l2_1 = params.get('line_2_word_1', 'TO')
            l2_2 = params.get('line_2_word_2', 'DO')
            return f"""{{
    Tools = ordered() {{
        TextTop = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Impact", }},
                Style = Input {{ Value = "Regular", }},
                Size = Input {{ Value = 0.18, }},
                StyledText = Input {{ Value = "{l1}", }},
                Center = Input {{ Value = {{ 0.5, 0.65 }}, }},
            }},
        }},
        TextBottom = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Impact", }},
                Style = Input {{ Value = "Regular", }},
                Size = Input {{ Value = 0.18, }},
                StyledText = Input {{ Value = "{l2_1} {l2_2}", }},
                Center = Input {{ Value = {{ 0.5, 0.45 }}, }},
                TopLeftRed = Input {{ Value = 0.706, }},
                TopLeftGreen = Input {{ Value = 0.941, }},
                TopLeftBlue = Input {{ Value = 0.0, }},
            }},
        }},
        Merge3DText = Merge {{
            Inputs = {{
                Background = Input {{ SourceOp = "TextTop", Source = "Output", }},
                Foreground = Input {{ SourceOp = "TextBottom", Source = "Output", }},
            }},
        }},
    }},
}}"""

        if template_id in ['split_silhouette_walking', 'split_silhouette_falling', 'silhouette_curve']:
            top_txt = params.get('arc_text_top', 'It felt like')
            bot_txt = params.get('arc_text_bottom', 'under my feet')
            return f"""{{
    Tools = ordered() {{
        BackgroundChartreuse = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Width = Input {{ Value = 1920, }},
                Height = Input {{ Value = 1080, }},
                TopLeftRed = Input {{ Value = 0.706, }},
                TopLeftGreen = Input {{ Value = 0.941, }},
                TopLeftBlue = Input {{ Value = 0.0, }},
                TopLeftAlpha = Input {{ Value = 1.0, }},
            }},
        }},
        SplitMask = RectangleMask {{
            Inputs = {{
                Center = Input {{ Value = {{ 0.75, 0.5 }}, }},
                Width = Input {{ Value = 0.5, }},
                Height = Input {{ Value = 1.0, }},
            }},
        }},
        ArcTextTop = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Black", }},
                Size = Input {{ Value = 0.09, }},
                StyledText = Input {{ Value = "{top_txt}", }},
                TopLeftRed = Input {{ Value = 0.0, }},
                TopLeftGreen = Input {{ Value = 0.0, }},
                TopLeftBlue = Input {{ Value = 0.0, }},
                Center = Input {{ Value = {{ 0.75, 0.75 }}, }},
            }},
        }},
        ArcTextBottom = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Black", }},
                Size = Input {{ Value = 0.09, }},
                StyledText = Input {{ Value = "{bot_txt}", }},
                TopLeftRed = Input {{ Value = 0.0, }},
                TopLeftGreen = Input {{ Value = 0.0, }},
                TopLeftBlue = Input {{ Value = 0.0, }},
                Center = Input {{ Value = {{ 0.75, 0.25 }}, }},
            }},
        }},
        MergeElements = Merge {{
            Inputs = {{
                Background = Input {{ SourceOp = "BackgroundChartreuse", Source = "Output", }},
                Foreground = Input {{ SourceOp = "ArcTextTop", Source = "Output", }},
            }},
        }},
    }},
}}"""

        if template_id == 'thematic_canvas':
            field_type = params.get('field_type', 'cardiology')
            headline = params.get('headline', 'CLINICAL TRIAL')
            subtext = params.get('subtext', 'Phase III Evidence')
            return f"""{{
    Tools = ordered() {{
        ThematicBg = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Width = Input {{ Value = 1920, }},
                Height = Input {{ Value = 1080, }},
                TopLeftRed = Input {{ Value = 0.04, }},
                TopLeftGreen = Input {{ Value = 0.08, }},
                TopLeftBlue = Input {{ Value = 0.12, }},
            }},
        }},
        PulseNoise = FastNoise {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Detail = Input {{ Value = 4.0, }},
                Contrast = Input {{ Value = 2.5, }},
                Brightness = Input {{ Value = -0.2, }},
                XScale = Input {{ Value = 12.0, }},
            }},
        }},
        CanvasTitle = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Black", }},
                Size = Input {{ Value = 0.07, }},
                StyledText = Input {{ Value = "{headline}", }},
                Center = Input {{ Value = {{ 0.5, 0.85 }}, }},
            }},
        }},
        MergeCanvas = Merge {{
            Inputs = {{
                Background = Input {{ SourceOp = "ThematicBg", Source = "Output", }},
                Foreground = Input {{ SourceOp = "CanvasTitle", Source = "Output", }},
            }},
        }},
    }},
}}"""

        if template_id == 'digital_highlighter':
            journal = params.get('journal_title', 'The New England Journal of Medicine')
            passage = params.get('dense_passage', 'Clinical evidence indicates significant improvement.')
            highlight = params.get('highlight_sentence', 'significant improvement')
            return f"""{{
    Tools = ordered() {{
        PaperSheet = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Width = Input {{ Value = 1200, }},
                Height = Input {{ Value = 800, }},
                TopLeftRed = Input {{ Value = 0.97, }},
                TopLeftGreen = Input {{ Value = 0.96, }},
                TopLeftBlue = Input {{ Value = 0.94, }},
            }},
        }},
        JournalHeader = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Playfair Display", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.04, }},
                StyledText = Input {{ Value = "{journal}", }},
                Center = Input {{ Value = {{ 0.5, 0.9 }}, }},
                TopLeftRed = Input {{ Value = 0.1, }},
                TopLeftGreen = Input {{ Value = 0.1, }},
                TopLeftBlue = Input {{ Value = 0.1, }},
            }},
        }},
        HighlighterBar = RectangleMask {{
            Inputs = {{
                Center = Input {{ Value = {{ 0.5, 0.45 }}, }},
                Width = Input {{ Value = 0.7, }},
                Height = Input {{ Value = 0.06, }},
            }},
        }},
        MarkerColor = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                EffectMask = Input {{ SourceOp = "HighlighterBar", Source = "Mask", }},
                TopLeftRed = Input {{ Value = 1.0, }},
                TopLeftGreen = Input {{ Value = 0.9, }},
                TopLeftBlue = Input {{ Value = 0.0, }},
                TopLeftAlpha = Input {{ Value = 0.45, }},
            }},
        }},
    }},
}}"""

        if template_id == 'article_reconstruction':
            publisher = params.get('publisher', 'Scroll.in')
            headline = params.get('headline', 'Dombivli hospital assault: Doctor resigns')
            para = params.get('paragraph', 'The resident medical officer said he had left the city.')
            return f"""{{
    Tools = ordered() {{
        ArticleCardBg = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Width = Input {{ Value = 1400, }},
                Height = Input {{ Value = 950, }},
                TopLeftRed = Input {{ Value = 0.98, }},
                TopLeftGreen = Input {{ Value = 0.98, }},
                TopLeftBlue = Input {{ Value = 0.96, }},
            }},
        }},
        MastheadText = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Georgia", }},
                Style = Input {{ Value = "Bold Italic", }},
                Size = Input {{ Value = 0.055, }},
                StyledText = Input {{ Value = "{publisher}", }},
                Center = Input {{ Value = {{ 0.5, 0.88 }}, }},
            }},
        }},
        HeadlineText = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.038, }},
                StyledText = Input {{ Value = "{headline}", }},
                Center = Input {{ Value = {{ 0.5, 0.72 }}, }},
            }},
        }},
        HighlighterMask = RectangleMask {{
            Inputs = {{
                Center = Input {{ Value = {{ 0.5, 0.42 }}, }},
                Width = Input {{ Value = 0.75, }},
                Height = Input {{ Value = 0.045, }},
            }},
        }},
        HighlighterColor = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                EffectMask = Input {{ SourceOp = "HighlighterMask", Source = "Mask", }},
                TopLeftRed = Input {{ Value = 0.0, }},
                TopLeftGreen = Input {{ Value = 0.9, }},
                TopLeftBlue = Input {{ Value = 1.0, }},
                TopLeftAlpha = Input {{ Value = 0.55, }},
            }},
        }},
    }},
}}"""

        if template_id == 'jargon_translation':
            study = params.get('clinical_finding', 'Downregulation of inflammatory markers.')
            plain = params.get('plain_english', 'Inflammation dropped dramatically!')
            badge = params.get('takeaway_badge', '↓ 45% Inflammation')
            return f"""{{
    Tools = ordered() {{
        CardBg = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Width = Input {{ Value = 900, }},
                Height = Input {{ Value = 500, }},
                TopLeftAlpha = Input {{ Value = 0.92, }},
            }},
        }},
        StudyText = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Inter", }},
                Size = Input {{ Value = 0.035, }},
                StyledText = Input {{ Value = "{study}", }},
                Center = Input {{ Value = {{ 0.5, 0.65 }}, }},
            }},
        }},
        PlainEnglishText = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Black", }},
                Size = Input {{ Value = 0.045, }},
                StyledText = Input {{ Value = "{plain}", }},
                Center = Input {{ Value = {{ 0.5, 0.35 }}, }},
                TopLeftRed = Input {{ Value = 0.8, }},
                TopLeftGreen = Input {{ Value = 1.0, }},
                TopLeftBlue = Input {{ Value = 0.0, }},
            }},
        }},
    }},
}}"""

        if template_id == 'metaphor_sequence':
            headline = params.get('headline', 'HOW RECEPTORS WORK')
            caption = params.get('caption', 'The key unlocks cellular signaling.')
            return f"""{{
    Tools = ordered() {{
        MetaphorTitle = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Black", }},
                Size = Input {{ Value = 0.06, }},
                StyledText = Input {{ Value = "{headline}", }},
                Center = Input {{ Value = {{ 0.5, 0.85 }}, }},
            }},
        }},
    }},
}}"""

        if template_id == 'authority_watermark':
            doctor = params.get('doctor_name', 'Dr. Priya Sharma, MD')
            creds = params.get('credentials', 'Cardiologist')
            return f"""{{
    Tools = ordered() {{
        Nameplate = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.032, }},
                StyledText = Input {{ Value = "{doctor} • {creds}", }},
                Center = Input {{ Value = {{ 0.25, 0.12 }}, }},
            }},
        }},
    }},
}}"""

        if template_id == 'medical_endcard':
            doctor = params.get('doctor_name', 'Dr. Priya Sharma, MD')
            cta = params.get('cta_text', 'Subscribe for Weekly Insights')
            return f"""{{
    Tools = ordered() {{
        EndCardTitle = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Black", }},
                Size = Input {{ Value = 0.055, }},
                StyledText = Input {{ Value = "{doctor}", }},
                Center = Input {{ Value = {{ 0.5, 0.7 }}, }},
            }},
        }},
        CtaText = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Inter", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.035, }},
                StyledText = Input {{ Value = "{cta}", }},
                Center = Input {{ Value = {{ 0.5, 0.3 }}, }},
            }},
        }},
    }},
}}"""

        if template_id == 'split_screen_vertical':
            citation = params.get('source_citation', 'Source: NASA Historical Archives')
            broll = params.get('broll_title', 'Archival Flight Footage')
            return f"""{{
    Tools = ordered() {{
        TopMask = RectangleMask {{
            Inputs = {{
                Center = Input {{ Value = {{ 0.5, 0.75 }}, }},
                Width = Input {{ Value = 1.0, }},
                Height = Input {{ Value = 0.5, }},
            }},
        }},
        DividerLine = sLine {{
            Inputs = {{
                Point1 = Input {{ Value = {{ 0.0, 0.5 }}, }},
                Point2 = Input {{ Value = {{ 1.0, 0.5 }}, }},
                Thickness = Input {{ Value = 0.003, }},
            }},
        }},
        SourceCitation = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Inter", }},
                Style = Input {{ Value = "Regular", }},
                Size = Input {{ Value = 0.024, }},
                StyledText = Input {{ Value = "{citation}", }},
                Center = Input {{ Value = {{ 0.22, 0.94 }}, }},
            }},
        }},
        BrollTitle = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.022, }},
                StyledText = Input {{ Value = "{broll}", }},
                Center = Input {{ Value = {{ 0.22, 0.54 }}, }},
            }},
        }},
    }},
}}"""

        if template_id == 'dimension_callout':
            measure = params.get('measurement_text', '14 FEET LONG')
            subtext = params.get('subtext', 'Fuselage Wingspan Spec')
            return f"""{{
    Tools = ordered() {{
        DimensionLine = sLine {{
            Inputs = {{
                Point1 = Input {{ Value = {{ 0.2, 0.5 }}, }},
                Point2 = Input {{ Value = {{ 0.8, 0.5 }}, }},
                Thickness = Input {{ Value = 0.002, }},
            }},
        }},
        TickStart = sLine {{
            Inputs = {{
                Point1 = Input {{ Value = {{ 0.2, 0.48 }}, }},
                Point2 = Input {{ Value = {{ 0.2, 0.52 }}, }},
                Thickness = Input {{ Value = 0.002, }},
            }},
        }},
        TickEnd = sLine {{
            Inputs = {{
                Point1 = Input {{ Value = {{ 0.8, 0.48 }}, }},
                Point2 = Input {{ Value = {{ 0.8, 0.52 }}, }},
                Thickness = Input {{ Value = 0.002, }},
            }},
        }},
        MeasureText = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Inter", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.038, }},
                StyledText = Input {{ Value = "{measure}", }},
                Center = Input {{ Value = {{ 0.5, 0.55 }}, }},
            }},
        }},
        SubtextNote = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Inter", }},
                Style = Input {{ Value = "Regular", }},
                Size = Input {{ Value = 0.020, }},
                StyledText = Input {{ Value = "{subtext}", }},
                Center = Input {{ Value = {{ 0.5, 0.44 }}, }},
            }},
        }},
    }},
}}"""

        if template_id == 'source_citation':
            src = params.get('source_name', 'Source: National Archives (1969)')
            dtype = params.get('doc_type', 'Declassified Mission Footage')
            return f"""{{
    Tools = ordered() {{
        CitationMain = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Inter", }},
                Style = Input {{ Value = "Medium", }},
                Size = Input {{ Value = 0.026, }},
                StyledText = Input {{ Value = "{src}", }},
                Center = Input {{ Value = {{ 0.22, 0.94 }}, }},
            }},
        }},
        CitationBadge = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Inter", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.018, }},
                StyledText = Input {{ Value = "{dtype}", }},
                Center = Input {{ Value = {{ 0.22, 0.91 }}, }},
            }},
        }},
    }},
}}"""

        if template_id == 'archival_filter':
            intensity = params.get('grain_intensity', 0.45)
            return f"""{{
    Tools = ordered() {{
        Grain = FilmGrain {{
            Inputs = {{
                GrainSize = Input {{ Value = 1.4, }},
                GrainStrength = Input {{ Value = {intensity}, }},
            }},
        }},
        Vignette = RectangleMask {{
            Inputs = {{
                Width = Input {{ Value = 0.92, }},
                Height = Input {{ Value = 0.92, }},
                CornerRadius = Input {{ Value = 0.45, }},
                Invert = Input {{ Value = 1, }},
                SoftEdge = Input {{ Value = 0.16, }},
            }},
        }},
    }},
}}"""

        if template_id == 'corner_bug':
            bug = params.get('bug_text', 'CHRONICLES')
            return f"""{{
    Tools = ordered() {{
        CornerWatermark = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Black", }},
                Size = Input {{ Value = 0.026, }},
                StyledText = Input {{ Value = "{bug}", }},
                Center = Input {{ Value = {{ 0.86, 0.94 }}, }},
            }},
        }},
    }},
}}"""

        if template_id == 'documentary_outro':
            headline = params.get('globe_headline', 'MISSION LOG COMPLETE')
            cta = params.get('cta_text', 'SUBSCRIBE FOR NEXT EPISODE')
            return f"""{{
    Tools = ordered() {{
        GlobeShape = sShape {{
            Inputs = {{
                Shape = Input {{ Value = 2, }},
                Width = Input {{ Value = 0.35, }},
                Height = Input {{ Value = 0.35, }},
            }},
        }},
        OutroHead = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Black", }},
                Size = Input {{ Value = 0.048, }},
                StyledText = Input {{ Value = "{headline}", }},
                Center = Input {{ Value = {{ 0.5, 0.72 }}, }},
            }},
        }},
        OutroCallToAction = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Inter", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.034, }},
                StyledText = Input {{ Value = "{cta}", }},
                Center = Input {{ Value = {{ 0.5, 0.25 }}, }},
            }},
        }},
    }},
}}"""

        headline = params.get('headline', 'Back then')
        accent = params.get('accent_word', 'I had')
        punchline = params.get('punchline', 'no idea.')

        return f"""{{
    Tools = ordered() {{
        HeadlineText = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Montserrat", }},
                Style = Input {{ Value = "Bold", }},
                Size = Input {{ Value = 0.08, }},
                StyledText = Input {{ Value = "{headline}", }},
            }},
        }},
        AccentText = TextPlus {{
            Inputs = {{
                GlobalOut = Input {{ Value = {duration_frames}, }},
                Font = Input {{ Value = "Playfair Display", }},
                Style = Input {{ Value = "Italic", }},
                Size = Input {{ Value = 0.10, }},
                StyledText = Input {{ Value = "{accent} {punchline}", }},
                TopLeftRed = Input {{ Value = 0.80, }},
                TopLeftGreen = Input {{ Value = 1.0, }},
                TopLeftBlue = Input {{ Value = 0.0, }},
            }},
        }},
        MergeGraphic = Merge {{
            Inputs = {{
                Background = Input {{ SourceOp = "HeadlineText", Source = "Output", }},
                Foreground = Input {{ SourceOp = "AccentText", Source = "Output", }},
            }},
        }},
    }},
}}"""


fusion_generator = FusionTemplateGenerator()
