import re
import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# ============================================================================
# Schemas & Models Matching User Specifications
# ============================================================================

class BeatItem(BaseModel):
    beat_id: str
    text: str
    start_time: float
    end_time: float
    has_document: bool = False
    priority_score: float = 0.0

class BeatEnhancementDecision(BaseModel):
    beat_id: str
    enhance: bool
    mode: str  # "background_only" | "full_sequence" | "none"
    reason: str

class BeatEnhancementSelectorOutput(BaseModel):
    beats: List[BeatEnhancementDecision]
    total_enhanced_frames: int
    total_enhanced_seconds: float

class CategoryPattern(BaseModel):
    pattern: str
    support_count: int
    confidence: str  # "low" | "medium" | "high"

class CategoryReferencePatternOutput(BaseModel):
    category: str
    sample_size: int = Field(..., alias="sample_size")
    patterns: List[CategoryPattern]
    insufficient_data: bool

    class Config:
        populate_by_name = True

class ExplainerRequest(BaseModel):
    mode: str  # "background_only" | "full_sequence"
    duration_seconds: float
    aspect_ratios: List[str] = ["9:16", "16:9"]
    style_preset: str
    prompt: str
    narration_text: Optional[str] = None
    camera_motion: Optional[str] = "push_in"

class DynamicGraphicSample(BaseModel):
    sample_id: str
    beat_id: str
    start_time: float
    end_time: float
    duration_seconds: float
    beat_type: str  # "hook" | "payoff" | "evidence" | "narrative"
    mode: str  # "background_only" | "full_sequence"
    style_preset: str
    prompt: str
    reason: str
    category_pattern: str
    pattern_confidence: str
    camera_motion: str
    overlay_headline: str
    template_id: str
    parameters: Dict[str, Any]

# ============================================================================
# Reference Database of High-Performing Category Patterns (Agent 2 Knowledge)
# ============================================================================

CATEGORY_REFERENCE_VIDEOS: Dict[str, List[Dict[str, Any]]] = {
    "healthcare": [
        {
            "video_id": "ref_health_01",
            "view_count": 2840000,
            "engagement_rate": 0.092,
            "patterns": [
                "Clinical document/paper scan with yellow highlighter on trial statistic",
                "Macro cellular animation with glowing fluorophores on pathology mention",
                "Split-screen comparison: Healthy organ vs afflicted pathology"
            ]
        },
        {
            "video_id": "ref_health_02",
            "view_count": 1950000,
            "engagement_rate": 0.088,
            "patterns": [
                "Clinical document/paper scan with yellow highlighter on trial statistic",
                "Macro cellular animation with glowing fluorophores on pathology mention",
                "Authentic patient clinical assessment with subtle handheld camera breath"
            ]
        },
        {
            "video_id": "ref_health_03",
            "view_count": 3400000,
            "engagement_rate": 0.104,
            "patterns": [
                "Authentic patient clinical assessment with subtle handheld camera breath",
                "Split-screen comparison: Healthy organ vs afflicted pathology",
                "Diagnostic CT radiography scan rotation on anatomy revelation"
            ]
        }
    ],
    "finance": [
        {
            "video_id": "ref_fin_01",
            "view_count": 1420000,
            "engagement_rate": 0.079,
            "patterns": [
                "Financial statement PDF zoom with green/red callout box",
                "Kinetic stock candlestick trajectory with volumetric glow",
                "Stat count-up metric with bold sans typography"
            ]
        },
        {
            "video_id": "ref_fin_02",
            "view_count": 2100000,
            "engagement_rate": 0.084,
            "patterns": [
                "Financial statement PDF zoom with green/red callout box",
                "Kinetic stock candlestick trajectory with volumetric glow",
                "Currency exchange / federal reserve archival macro"
            ]
        }
    ],
    "technology": [
        {
            "video_id": "ref_tech_01",
            "view_count": 3100000,
            "engagement_rate": 0.095,
            "patterns": [
                "3D architectural blueprint wireframe with neon pulse trace",
                "Macro silicon wafer circuit dive with shallow focal plane",
                "Terminal shell log readout with cyan typewriter effect"
            ]
        },
        {
            "video_id": "ref_tech_02",
            "view_count": 1850000,
            "engagement_rate": 0.091,
            "patterns": [
                "3D architectural blueprint wireframe with neon pulse trace",
                "Macro silicon wafer circuit dive with shallow focal plane",
                "Patent schematic document scan with technical dimension callouts"
            ]
        }
    ],
    "documentary": [
        {
            "video_id": "ref_doc_01",
            "view_count": 4200000,
            "engagement_rate": 0.112,
            "patterns": [
                "Archival classified document declassification reveal",
                "High-contrast monochrome historical archival footage with slow push-in",
                "Geographic satellite terrain dive to key incident coordinates"
            ]
        },
        {
            "video_id": "ref_doc_02",
            "view_count": 2900000,
            "engagement_rate": 0.098,
            "patterns": [
                "Archival classified document declassification reveal",
                "High-contrast monochrome historical archival footage with slow push-in",
                "Timeline milestone card with year badge and paper texture"
            ]
        }
    ]
}

# ============================================================================
# AGENT 2: Category Reference Pattern Extractor
# ============================================================================

class CategoryReferencePatternExtractor:
    """
    SYSTEM: You study a set of reference videos from one content category —
    already known to be strong performers — and extract recurring visual-
    treatment patterns another agent can apply going forward. Do not invent a
    pattern unsupported by at least {min_support} of the reference videos. If
    the reference set is too small or too inconsistent to support a pattern
    confidently, say so explicitly instead of guessing.
    """
    def extract_patterns(
        self,
        category: str,
        reference_videos: Optional[List[Dict[str, Any]]] = None,
        min_support: int = 2
    ) -> CategoryReferencePatternOutput:
        cat_key = category.lower().strip()
        ref_set = reference_videos or CATEGORY_REFERENCE_VIDEOS.get(cat_key)

        if not ref_set or len(ref_set) < min_support:
            # Check fallback categories or report insufficient data
            for known_cat, videos in CATEGORY_REFERENCE_VIDEOS.items():
                if known_cat in cat_key or any(w in cat_key for w in known_cat.split()):
                    ref_set = videos
                    cat_key = known_cat
                    break

        if not ref_set or len(ref_set) < min_support:
            return CategoryReferencePatternOutput(
                category=category,
                sample_size=len(ref_set) if ref_set else 0,
                patterns=[],
                insufficient_data=True
            )

        sample_size = len(ref_set)
        # Count frequency of each visual treatment pattern across reference videos
        pattern_counts: Dict[str, int] = {}
        for vid in ref_set:
            seen_in_video = set(vid.get("patterns", []))
            for pat in seen_in_video:
                pattern_counts[pat] = pattern_counts.get(pat, 0) + 1

        extracted_patterns: List[CategoryPattern] = []
        for pat, count in pattern_counts.items():
            if count >= min_support:
                support_ratio = count / sample_size
                confidence = "high" if support_ratio >= 0.75 else "medium" if support_ratio >= 0.5 else "low"
                extracted_patterns.append(CategoryPattern(
                    pattern=pat,
                    support_count=count,
                    confidence=confidence
                ))

        extracted_patterns.sort(key=lambda p: (p.support_count, p.confidence == "high"), reverse=True)

        return CategoryReferencePatternOutput(
            category=cat_key,
            sample_size=sample_size,
            patterns=extracted_patterns,
            insufficient_data=len(extracted_patterns) == 0
        )

# ============================================================================
# AGENT 1: Frame/Beat Enhancement Selector
# ============================================================================

class FrameBeatEnhancementSelector:
    """
    SYSTEM: You decide which beats in a video's beat list qualify for premium
    AI-generated visual treatment. You receive a category, the full beat list
    (text, start_time, end_time, has_document), and a rule profile (general +
    category-specific). Apply general rules first, then category rules. Always
    flag the first beat if it falls within the opening 3 seconds — hooks
    qualify regardless of other rules. Never enhance more than {max_pct}% of
    total runtime; if more beats qualify than the budget allows, keep the
    highest-priority ones (hook and payoff first) and drop the rest.
    """
    def select_enhancements(
        self,
        category: str,
        fps: float,
        beats: List[BeatItem],
        rule_profile: Optional[Dict[str, Any]] = None
    ) -> BeatEnhancementSelectorOutput:
        rules = rule_profile or {}
        max_pct = float(rules.get("max_pct", 25.0))  # Default 25% max runtime budget
        
        if not beats:
            return BeatEnhancementSelectorOutput(
                beats=[],
                total_enhanced_frames=0,
                total_enhanced_seconds=0.0
            )

        total_runtime = max(beats[-1].end_time, max(b.end_time for b in beats))
        max_budget_seconds = (max_pct / 100.0) * total_runtime

        scored_beats: List[Dict[str, Any]] = []

        for idx, beat in enumerate(beats):
            dur = max(1.0, beat.end_time - beat.start_time)
            is_hook = (idx == 0 and beat.start_time <= 3.0)
            
            # Priority Scoring:
            # 100+ for Hook (mandatory qualify)
            # 80+ for Climax / High-Impact Payoff
            # 70+ for Document Evidence
            # 40-60 for Standard Narrative
            score = 0.0
            beat_role = "narrative"
            
            text_lower = beat.text.lower()
            
            if is_hook:
                score += 150.0
                beat_role = "hook"
            elif any(w in text_lower for w in ["fatal", "result", "died", "cured", "revealed", "discovered", "concluded", "ultimately", "finally", "truth", "shocking"]):
                score += 85.0
                beat_role = "payoff"
            elif beat.has_document or any(w in text_lower for w in ["study", "report", "paper", "data", "fda", "lancet", "clinical trial", "contract", "filing"]):
                score += 75.0
                beat.has_document = True
                beat_role = "evidence"
            elif any(w in text_lower for w in ["cancer", "cough", "couph", "lungs", "tumor", "cells", "infection", "symptoms", "attack"]):
                score += 65.0
                beat_role = "clinical_concept"
            else:
                score += 30.0

            # Determine prospective mode
            mode = "background_only" if beat.has_document else "full_sequence"

            scored_beats.append({
                "beat": beat,
                "duration": dur,
                "is_hook": is_hook,
                "beat_role": beat_role,
                "score": score,
                "mode": mode,
                "reason": (
                    "Opening Hook (guaranteed qualification within 0-3s)" if is_hook
                    else f"High-Impact Narrative {beat_role.replace('_', ' ').title()}"
                )
            })

        # Sort candidate beats by score descending (Hook & Payoff first)
        candidate_beats = sorted(scored_beats, key=lambda x: x["score"], reverse=True)

        selected_beat_ids = set()
        accumulated_seconds = 0.0

        for cand in candidate_beats:
            b = cand["beat"]
            dur = cand["duration"]

            # Hook ALWAYS qualifies regardless of budget
            if cand["is_hook"]:
                selected_beat_ids.add(b.beat_id)
                accumulated_seconds += dur
                continue

            # Check if adding fits within max runtime budget
            if (accumulated_seconds + dur) <= max_budget_seconds:
                selected_beat_ids.add(b.beat_id)
                accumulated_seconds += dur

        decisions: List[BeatEnhancementDecision] = []
        for item in scored_beats:
            b = item["beat"]
            will_enhance = b.beat_id in selected_beat_ids
            mode = item["mode"] if will_enhance else "none"
            reason = (
                item["reason"] if will_enhance
                else "Dropped to respect runtime budget cap ({:.0f}s max)".format(max_budget_seconds)
            )

            decisions.append(BeatEnhancementDecision(
                beat_id=b.beat_id,
                enhance=will_enhance,
                mode=mode,
                reason=reason
            ))

        total_frames = int(round(accumulated_seconds * fps))

        return BeatEnhancementSelectorOutput(
            beats=decisions,
            total_enhanced_frames=total_frames,
            total_enhanced_seconds=round(accumulated_seconds, 2)
        )

# ============================================================================
# AGENT 3: Explainer Request Builder
# ============================================================================

class ExplainerRequestBuilder:
    """
    SYSTEM:
    If mode is "background_only", build a looping ambient background request
    (no narration, no characters), sized to the beat's duration, meant to sit
    behind a document + highlighter overlay.
    If mode is "full_sequence", build request that generates the complete
    illustrative visual for this beat's narration — no document exists for
    this beat, so the generated visual has to carry the whole idea on its own.
    """
    def build_request(
        self,
        mode: str,
        beat: BeatItem,
        style_config: Optional[Dict[str, Any]] = None,
        category_patterns: Optional[List[CategoryPattern]] = None
    ) -> ExplainerRequest:
        config = style_config or {}
        duration = max(3.0, min(10.0, round(beat.end_time - beat.start_time, 1)))
        
        # Pull best pattern if confidence is medium or higher
        top_pattern = None
        if category_patterns:
            top_pattern = next(
                (p.pattern for p in category_patterns if p.confidence in ("high", "medium")),
                None
            )

        if mode == "background_only":
            # Looping ambient background (no narration, no characters) for document + highlighter overlay
            bg_prompt = (
                f"Minimalist cinematic atmospheric background loop. Subtle dark slate bokeh lighting, "
                f"gentle ambient film grain, soft drifting dust particles, low focal depth, seamless loop. "
                f"Clean corporate documentary aesthetic. No characters, no text, no narration."
            )
            if top_pattern and "document" in top_pattern.lower():
                bg_prompt = (
                    f"Subtle dark laboratory desk wood and muted archival parchment texture. "
                    f"Soft angled rim lighting from upper left, shallow depth of field, gentle atmospheric loop. "
                    f"No people, no dialogue, no overlaid typography."
                )

            return ExplainerRequest(
                mode="background_only",
                duration_seconds=duration,
                aspect_ratios=["9:16", "16:9"],
                style_preset="ambient_document_backdrop",
                prompt=bg_prompt,
                narration_text=None,
                camera_motion="subtle_drift"
            )

        else:
            # Full sequence: Complete illustrative visual carrying the narrative idea
            camera_move = config.get("camera_motion", "push_in")
            if any(w in beat.text.lower() for w in ["cough", "couph", "pain", "patient", "urgent", "breath"]):
                camera_move = "handheld"
            elif any(w in beat.text.lower() for w in ["cell", "microscopic", "dna", "molecule", "virus"]):
                camera_move = "macro"
            elif any(w in beat.text.lower() for w in ["world", "system", "scale", "hospital", "body"]):
                camera_move = "orbit"

            # Formulate Higgsfield-grade storytelling prompt
            clean_beat_text = beat.text.strip().rstrip(".,")
            full_prompt = (
                f"Authentic cinematic visual sequence illustrating: '{clean_beat_text}'. "
                f"Camera movement: {camera_move}. Naturalistic documentary lighting, shallow depth of field, "
                f"photorealistic broadcast quality, vivid textures. Unbroken continuous shot."
            )

            if top_pattern:
                full_prompt += f" Styled according to high-performing reference convention: {top_pattern}."

            return ExplainerRequest(
                mode="full_sequence",
                duration_seconds=duration,
                aspect_ratios=["9:16", "16:9"],
                style_preset="cinematic_illustrative_sequence",
                prompt=full_prompt,
                narration_text=clean_beat_text,
                camera_motion=camera_move
            )

# ============================================================================
# Dynamic Graphics Pipeline Coordinator (Service Layer)
# ============================================================================

class DynamicGraphicsService:
    def __init__(self):
        self.pattern_extractor = CategoryReferencePatternExtractor()
        self.enhancement_selector = FrameBeatEnhancementSelector()
        self.request_builder = ExplainerRequestBuilder()

    def segment_captions_into_beats(self, captions: List[Any]) -> List[BeatItem]:
        """Groups raw caption lines into coherent narrative beats (2.5s to 6.5s each)."""
        beats: List[BeatItem] = []
        if not captions:
            return beats

        current_words: List[str] = []
        beat_start = float(captions[0].start if hasattr(captions[0], "start") else captions[0].get("start", 0))
        beat_end = float(captions[0].end if hasattr(captions[0], "end") else captions[0].get("end", 2))
        beat_id_idx = 1

        DOCUMENT_KEYWORDS = {
            "study", "studies", "paper", "report", "lancet", "nejm", "fda", "patent",
            "clinical", "trial", "statistic", "data", "filing", "contract", "chart",
            "document", "evidence", "proven", "documented", "record", "archive"
        }

        for cap in captions:
            text = cap.text if hasattr(cap, "text") else cap.get("text", "")
            start = float(cap.start if hasattr(cap, "start") else cap.get("start", 0))
            end = float(cap.end if hasattr(cap, "end") else cap.get("end", start + 2))
            
            current_words.append(text)
            beat_end = end

            # Break beat on punctuation or when duration reaches ~3-5 seconds
            dur = beat_end - beat_start
            ends_sentence = bool(re.search(r'[.?!]\s*$', text))

            if dur >= 3.0 and (ends_sentence or dur >= 5.0):
                beat_text = " ".join(current_words)
                has_doc = any(w in beat_text.lower() for w in DOCUMENT_KEYWORDS)
                
                beats.append(BeatItem(
                    beat_id=f"beat_{beat_id_idx}_{int(beat_start * 100)}",
                    text=beat_text,
                    start_time=round(beat_start, 2),
                    end_time=round(beat_end, 2),
                    has_document=has_doc
                ))
                beat_id_idx += 1
                current_words = []
                beat_start = beat_end

        # Flush any remaining words into final beat
        if current_words:
            beat_text = " ".join(current_words)
            has_doc = any(w in beat_text.lower() for w in DOCUMENT_KEYWORDS)
            beats.append(BeatItem(
                beat_id=f"beat_{beat_id_idx}_{int(beat_start * 100)}",
                text=beat_text,
                start_time=round(beat_start, 2),
                end_time=round(beat_end, 2),
                has_document=has_doc
            ))

        return beats

    def detect_category(self, text: str) -> str:
        """Detects high-level content category from overall video transcript."""
        t_low = text.lower()
        if any(w in t_low for w in ["cough", "couph", "lung", "cancer", "doctor", "hospital", "patient", "disease", "infection", "medicine", "medical", "treatment", "symptom"]):
            return "healthcare"
        if any(w in t_low for w in ["stock", "dollar", "revenue", "money", "profit", "crypto", "bitcoin", "invest", "finance", "bank"]):
            return "finance"
        if any(w in t_low for w in ["ai", "model", "software", "code", "chip", "robot", "cloud", "server", "algorithm", "data"]):
            return "technology"
        if any(w in t_low for w in ["history", "war", "century", "president", "nasa", "flight", "mission", "archive", "historical"]):
            return "documentary"
        return "healthcare"  # Default clinical / documentary

    def generate_dynamic_samples_for_project(
        self,
        captions: List[Any],
        fps: float = 30.0,
        category_override: Optional[str] = None,
        max_pct: float = 25.0,
        min_support: int = 2
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end 3-Agent pipeline and returns dynamic graphic proposals
        tailored to the active video.
        """
        beats = self.segment_captions_into_beats(captions)
        full_transcript = " ".join([b.text for b in beats])
        category = category_override or self.detect_category(full_transcript)

        # Agent 2: Extract Category Reference Patterns
        pattern_output = self.pattern_extractor.extract_patterns(
            category=category,
            min_support=min_support
        )

        # Agent 1: Select Qualified Beats with Runtime Budget
        rule_profile = {
            "max_pct": max_pct,
            "category": category
        }
        enhancement_output = self.enhancement_selector.select_enhancements(
            category=category,
            fps=fps,
            beats=beats,
            rule_profile=rule_profile
        )

        decisions_by_id = {d.beat_id: d for d in enhancement_output.beats}

        # Agent 3: Build Explainer Requests & Formulate UI Graphic Proposals
        samples: List[DynamicGraphicSample] = []
        sample_idx = 1

        for beat in beats:
            dec = decisions_by_id.get(beat.beat_id)
            if not dec or not dec.enhance:
                continue

            explainer_req = self.request_builder.build_request(
                mode=dec.mode,
                beat=beat,
                style_config={"camera_motion": "handheld" if "cough" in beat.text.lower() else "push_in"},
                category_patterns=pattern_output.patterns
            )

            # Determine beat type badge
            is_hook = (beat.start_time <= 3.0)
            beat_type = "hook" if is_hook else "evidence" if dec.mode == "background_only" else "payoff"

            # Assign matching category pattern
            matched_pat = pattern_output.patterns[0].pattern if pattern_output.patterns else "Authentic Documentary Realism"
            conf = pattern_output.patterns[0].confidence if pattern_output.patterns else "medium"

            # Headline overlay extracted from narration
            words = beat.text.strip().split()
            overlay_hl = " ".join(words[:4]).title() if words else "Key Evidence"

            # Build timeline graphic parameters compatible with Track V2
            template_id = "split_screen_vertical" if dec.mode == "full_sequence" else "dimension_callout"
            params = {
                "broll_title": overlay_hl,
                "broll_subtitle": explainer_req.prompt[:60] + "...",
                "source_citation": f"Dynamic Visual ({matched_pat[:32]})",
                "split_ratio": 0.5,
                "camera_motion": explainer_req.camera_motion,
                "ai_prompt": explainer_req.prompt,
                "mode": dec.mode
            }

            samples.append(DynamicGraphicSample(
                sample_id=f"sample_{sample_idx}_{int(beat.start_time * 100)}",
                beat_id=beat.beat_id,
                start_time=beat.start_time,
                end_time=beat.end_time,
                duration_seconds=explainer_req.duration_seconds,
                beat_type=beat_type,
                mode=dec.mode,
                style_preset=explainer_req.style_preset,
                prompt=explainer_req.prompt,
                reason=dec.reason,
                category_pattern=matched_pat,
                pattern_confidence=conf,
                camera_motion=explainer_req.camera_motion or "push_in",
                overlay_headline=overlay_hl,
                template_id=template_id,
                parameters=params
            ))
            sample_idx += 1

        total_runtime = beats[-1].end_time if beats else 0.0

        return {
            "category": category,
            "total_runtime_seconds": round(total_runtime, 2),
            "total_beats_count": len(beats),
            "enhanced_beats_count": len(samples),
            "total_enhanced_seconds": enhancement_output.total_enhanced_seconds,
            "budget_pct_used": round((enhancement_output.total_enhanced_seconds / max(1.0, total_runtime)) * 100, 1),
            "max_budget_pct": max_pct,
            "patterns": [p.model_dump() for p in pattern_output.patterns],
            "samples": [s.model_dump() for s in samples]
        }

dynamic_graphics_service = DynamicGraphicsService()
