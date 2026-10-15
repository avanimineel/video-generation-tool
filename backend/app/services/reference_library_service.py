"""
Shared Reference & Taste Library
Unified repository for visual style standards, motion graphics archetypes,
and editorial examples. Acts as the single source of truth across both
the storyboard generator and DaVinci companion auto-production.
"""

from typing import List, Dict, Any, Optional

class ReferenceLibraryService:
    def __init__(self):
        # 8 Canonical Visual Archetypes combining Storyboard Studio & Companion
        self._reference_archetypes: List[Dict[str, Any]] = [
            {
                "id": "creator_red_ribbon",
                "name": "Creator Signature: Red Ribbon & Serif Emphasis",
                "category": "High-Impact Kinetic Text",
                "graphic_type": "split_screen_vertical",
                "description": (
                    "Translucent crimson ribbon (#991B1B) across the lower-third with bold white Serif typography "
                    "and emotional cursive italics. Host is punched in 1.2x on medium close-up."
                ),
                "visual_guidance": "Use when the speaker delivers an emotional hook, contrarian insight, or core thesis statement.",
                "wireframe": "host_right_red_ribbon",
                "sample_query": "Crimson geometric ribbon banner, minimalist dark background, high contrast editorial"
            },
            {
                "id": "doodle_underline",
                "name": "Depth-of-Field Defocus + Hand-Drawn Marker Doodle",
                "category": "Organic Annotations",
                "graphic_type": "dimension_callout",
                "description": (
                    "Camera holds subject framing while background softly defuses. A vibrant red or neon hand-drawn marker "
                    "scribble animates dynamically beneath the key operational phrase."
                ),
                "visual_guidance": "Use when the speaker stresses a critical noun, mechanism, or mistake that needs immediate visual anchor.",
                "wireframe": "host_left_red_doodle",
                "sample_query": "Red felt-tip marker scribble underline, sketch doodle on textured surface"
            },
            {
                "id": "cutout_radar",
                "name": "2.5D Collage Cutout & Concentric Radar Waves",
                "category": "Documentary Collage",
                "graphic_type": "split_screen_vertical",
                "description": (
                    "Vintage illustrative cutout elements isolated with gentle parallax float. Concentric white and cyan "
                    "radar pulse rings radiate outward with hand-drawn oval highlights."
                ),
                "visual_guidance": "Use when explaining an abstract concept, economic system, or geographic entity that benefits from tactile collage.",
                "wireframe": "cutout_house_radar_oval",
                "sample_query": "Vintage architectural cutout with subtle radar pulse graphics, clean paper texture"
            },
            {
                "id": "cutout_landscape",
                "name": "2.5D Cutout Subject in Landscape + Tracking Ribbon",
                "category": "Visual Metaphors",
                "graphic_type": "youtube_insert",
                "description": (
                    "Full-frame wide visual metaphor: Cutout figure positioned in a wide meadow or horizon. A dark red or cyan "
                    "ribbon tracks across the skyline connecting the subject to the destination."
                ),
                "visual_guidance": "Use for broad philosophical transitions, perspective shifts, or chapter chapter intros.",
                "wireframe": "cutout_man_field_ribbon",
                "sample_query": "Figure standing in open horizon landscape with tracking motion ribbon, cinematic documentary"
            },
            {
                "id": "article_reconstruction",
                "name": "Full-Screen White Research Paper Reconstruction",
                "category": "Investigative Evidence",
                "graphic_type": "article_reconstruction",
                "description": (
                    "100% full-screen pure white backdrop with official publisher masthead, bold black serif headline, "
                    "publication date/metadata, and a clean yellow or cyan highlighter wipe animating across the smoking-gun quote."
                ),
                "visual_guidance": "Use whenever citing published medical literature, investigative journalism, legal filings, or statistics. Must cover entire screen.",
                "wireframe": "fullscreen_white_paper_article",
                "sample_query": "Scientific medical journal publication masthead, clean typography, document archive"
            },
            {
                "id": "split_screen_vertical",
                "name": "50/50 Broadcast Split Screen Evidence",
                "category": "Side-by-Side Proof",
                "graphic_type": "split_screen_vertical",
                "description": (
                    "Precision 50/50 vertical division: Speaker framed on bottom half, high-resolution clinical or documentary evidence "
                    "on top half. Minimalist 2px solid white divider. Zero badges, pills, or watermarks."
                ),
                "visual_guidance": "Use when the speaker explains visual evidence that the audience must observe simultaneously with speaker delivery.",
                "wireframe": "broadcast_vertical_split_50_50",
                "sample_query": "Close-up radiology CT scan cross section, sterile lighting, diagnostic evidence"
            },
            {
                "id": "dimension_callout",
                "name": "Technical Dimension Callout HUD",
                "category": "Precision Metrics",
                "graphic_type": "dimension_callout",
                "description": (
                    "Ultra-clean vector measurement tick marks, connecting extension lines, and cyan numerical readout "
                    "(e.g., '7 CM', '10 MM', 'STAGE 3') displaying exact physical or anatomical dimensions."
                ),
                "visual_guidance": "Use immediately when physical sizes, anatomical dimensions, timeframes, or metric units are spoken.",
                "wireframe": "cyan_vector_dimension_callout",
                "sample_query": "Architectural dimension schematic, cyan technical readout on clean background"
            },
            {
                "id": "youtube_insert",
                "name": "Contextual B-Roll Cutaway",
                "category": "Contextual Cutaways",
                "graphic_type": "youtube_insert",
                "description": (
                    "Tight, high-impact cutaway B-roll footage illustrating the spoken topic. Timed to the spoken action and visual reading demand "
                    "to maintain aggressive documentary velocity without fatiguing the viewer. Zero topic pills or badges."
                ),
                "visual_guidance": "Use for punchy real-world illustration of tools, environments, or actions. Hold long enough to understand the action.",
                "wireframe": "clean_cinematic_cutaway_1s",
                "sample_query": "Clinician reviewing scan on illuminated light box, focused gaze, documentary framing"
            }
        ]

    def get_all_archetypes(self) -> List[Dict[str, Any]]:
        return self._reference_archetypes

    def get_archetype_by_id(self, archetype_id: str) -> Optional[Dict[str, Any]]:
        for a in self._reference_archetypes:
            if a["id"] == archetype_id:
                return a
        return None

    def get_taste_summary_for_prompt(self) -> str:
        """
        Formats reference taste archetypes into a concise prompt guideline for Pegasus 1.5.
        """
        from app.services.finished_reel_understanding import profile_prompt
        return profile_prompt()


reference_library_service = ReferenceLibraryService()
