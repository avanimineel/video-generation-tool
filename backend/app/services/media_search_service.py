import os
import re
from typing import List, Dict, Any, Optional, Tuple
from .media_providers.base import BaseMediaProvider, MediaAsset
from .media_providers.pexels import PexelsProvider
from .media_providers.pixabay import PixabayProvider
from .media_providers.wikimedia import WikimediaProvider
from .media_providers.google_ai import google_ai_provider

# Curated high-resolution fallback visuals categorized by clinical / documentary topic
CURATED_FALLBACK_MEDIA: Dict[str, List[Dict[str, Any]]] = {
    "mortality": [
        {
            "id": "mort_01",
            "provider": "curated",
            "title": "Global Cancer Mortality Statistics & Epidemiological Trends",
            "url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Global Epidemiology & Health Analytics",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        },
        {
            "id": "mort_02",
            "provider": "curated",
            "title": "Clinical Trial Survival Analytics & Oncology Data Chart",
            "url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Clinical Research Data Repository",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        }
    ],
    "incidence": [
        {
            "id": "inc_01",
            "provider": "curated",
            "title": "Global Disease Incidence & International Healthcare Epidemiology Map",
            "url": "https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: World Health Epidemiological Registry",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        },
        {
            "id": "inc_02",
            "provider": "curated",
            "title": "Epidemiological Prevalence Distribution Chart",
            "url": "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Public Health Analytics",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        }
    ],
    "lung": [
        {
            "id": "lung_01",
            "provider": "curated",
            "title": "Human Pulmonary Anatomy & Bronchial Tree Illustration",
            "url": "https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Thoracic Medical Illustration Archive",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        },
        {
            "id": "lung_02",
            "provider": "curated",
            "title": "Pulmonary Specialist Reviewing Chest Radiograph",
            "url": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Clinical Pulmonology Center",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        }
    ],
    "screening": [
        {
            "id": "screen_01",
            "provider": "curated",
            "title": "Advanced Low-Dose CT Scanner in Sterile Radiology Suite",
            "url": "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Diagnostic Radiology Institute",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        },
        {
            "id": "screen_02",
            "provider": "curated",
            "title": "Radiologist Analyzing Cross-Sectional Axial CT Scans",
            "url": "https://images.unsplash.com/photo-1579684453423-f84349ef60b0?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1579684453423-f84349ef60b0?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Hospital Diagnostic Imaging Department",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        }
    ],
    "treatment": [
        {
            "id": "treat_01",
            "provider": "curated",
            "title": "Targeted Oncology Pharmacology & Precision Medicine Laboratory",
            "url": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Molecular Therapeutics Laboratory",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        },
        {
            "id": "treat_02",
            "provider": "curated",
            "title": "Modern Hospital Surgical Suite & Operating Theater",
            "url": "https://images.unsplash.com/photo-1551076805-e1869033e561?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1551076805-e1869033e561?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Surgical Oncology Center",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        }
    ],
    "pathology": [
        {
            "id": "path_01",
            "provider": "curated",
            "title": "Histopathological Microscopic Assessment of Tumor Tissue",
            "url": "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Pathology Research Archives",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        },
        {
            "id": "path_02",
            "provider": "curated",
            "title": "Cellular Biology Microscope Laboratory Culture",
            "url": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Molecular Oncology Institute",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        }
    ],
    "coughing": [
        {
            "id": "cough_01",
            "provider": "curated",
            "title": "Patient with Respiratory Symptoms & Cough in Clinic",
            "url": "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Pulmonology & Respiratory Health Archive",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        }
    ],
    "doctor": [
        {
            "id": "doc_01",
            "provider": "curated",
            "title": "Medical Specialist Examining Diagnostic Scans with Patient",
            "url": "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=1200&q=80",
            "thumb_url": "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=400&q=80",
            "source_credit": "Source: Outpatient Consultation Archive",
            "media_type": "image",
            "width": 1200, "height": 800, "aspect_ratio": "16:9", "orientation": "landscape"
        }
    ]
}

class MediaSearchService:
    def __init__(self):
        self.pexels = PexelsProvider()
        self.pixabay = PixabayProvider()
        self.wikimedia = WikimediaProvider()
        self.google_ai = google_ai_provider

    def get_providers_status(self) -> Dict[str, Any]:
        return {
            "pexels": self.pexels.check_connection(),
            "pixabay": self.pixabay.check_connection(),
            "wikimedia": self.wikimedia.check_connection(),
            "google_ai": self.google_ai.check_connection()
        }

    def generate_search_queries(self, dialogue_or_caption: str) -> List[str]:
        """
        Converts transcript dialogue or sentence context into 3 to 5 ranked, distinct search queries.
        Analyzes the semantic meaning of the sentence instead of single words.
        """
        text = dialogue_or_caption.strip()
        if not text:
            return ["medical documentary evidence", "clinical healthcare laboratory"]

        clean = re.sub(r"[^\w\s]", " ", text).lower()

        queries: List[str] = []

        # 1. Mortality & Global Burden of Disease
        if any(w in clean for w in ["death", "deaths", "mortality", "fatal", "dying", "survival rate", "killer", "maximum"]):
            queries.extend([
                "medical chart doctor hospital data",
                "doctor analyzing patient charts data",
                "hospital intensive care oncology",
                "physician reviewing medical data clinic",
                "clinical medical research oncology"
            ])

        # 2. Incidence, Global Prevalence & Comparison
        elif any(w in clean for w in ["commonest", "most common", "prevalence", "incidence", "world", "our country"]):
            queries.extend([
                "pulmonary lungs anatomy medical",
                "doctor analyzing patient charts medical",
                "doctor reviewing x-ray lungs",
                "medical research laboratory oncology",
                "clinical oncology healthcare research"
            ])

        # 3. Screening, Radiology, CT Scan & Early Detection
        elif any(w in clean for w in ["detect", "detected", "detection", "screening", "ct scan", "scan", "x-ray", "radiology", "screened", "early stage"]):
            queries.extend([
                "radiologist chest ct scan",
                "doctor examining patient scans",
                "chest x-ray diagnostic examination",
                "physician doctor consultation clinic examination"
            ])

        # 4. Differential Diagnosis & Infection (Tuberculosis vs Cancer)
        elif any(w in clean for w in ["tb", "tuberculosis", "infection", "misdiagnos", "bacteria", "coughing medicine"]):
            queries.extend([
                "pulmonary tuberculosis radiology infection",
                "chest x-ray infection infiltration clinic",
                "microbiology laboratory bacteria diagnosis",
                "pulmonary clinic doctor stethoscope examination"
            ])

        # 5. Clinical Symptoms & Hemoptysis (Coughing blood)
        elif any(w in clean for w in ["blood", "bloodied", "cough", "coughing", "sputum", "breath", "breathing"]):
            queries.extend([
                "patient coughing respiratory clinic consultation",
                "pulmonary clinic patient examination",
                "respiratory care hospital consultation",
                "medical examination stethoscope breathing"
            ])

        # 6. Surgery, Lymph Nodes & Resection
        elif any(w in clean for w in ["surgery", "surgical", "lymph", "node", "resection", "lobectomy", "operation"]):
            queries.extend([
                "thoracic surgery operating room oncology",
                "pulmonary lymph node resection surgical",
                "surgeon operating sterile theater hospital",
                "clinical surgical resection oncology"
            ])

        # 7. Cellular Pathology & Tumor Growth
        elif any(w in clean for w in ["tumor", "tumour", "cell", "cells", "mutation", "growth", "biopsy", "histology", "pathology"]):
            queries.extend([
                "cancer cell histology microscopy oncology",
                "malignant tumor cellular division microscope",
                "oncology pathology laboratory biopsy",
                "medical science microscopy cell research"
            ])

        # 8. Aerospace & Kinetic beats
        elif any(w in clean for w in ["rocket", "launch", "space", "apollo", "eject", "flight", "plane", "mach"]):
            queries.extend([
                "rocket launch aerospace flight",
                "spacecraft launch propulsion sky",
                "aerospace engineering aircraft high speed"
            ])

        # 9. Fallback general clinical/medical queries
        elif any(w in clean for w in ["patient", "doctor", "hospital", "clinic", "treatment", "medicine", "stage"]):
            queries.extend([
                "physician doctor consultation clinic examination",
                "hospital clinical examination patient care",
                "medical oncology clinical treatment research"
            ])

        if not queries:
            words = clean.split()
            stopwords = {"the", "and", "that", "this", "with", "from", "have", "were", "been", "they", "what", "when", "where", "about", "today", "series", "going", "talk", "particular", "starting"}
            kws = [w for w in words if w not in stopwords and len(w) > 3]
            kw_str = " ".join(kws[:3]) if kws else "medical oncology clinical"
            queries = [
                f"{kw_str} healthcare medical clinical",
                f"{kw_str} research documentary archive"
            ]

        # Deduplicate preserving order
        seen = set()
        ranked = []
        for q in queries:
            q_clean = q.strip()
            if q_clean and q_clean not in seen:
                seen.add(q_clean)
                ranked.append(q_clean)

        return ranked[:5]

    def search_media(
        self,
        query: str,
        media_type: str = "image",
        provider: str = "all",
        orientation: Optional[str] = None,
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        clean_q = re.sub(
            r"^(make\s+a\s+video\s+of|generate\s+a\s+video\s+of|add\s+a\s+video\s+of|video\s+of|footage\s+of|clip\s+of|an?\s+)\s+",
            "",
            query.strip(),
            flags=re.IGNORECASE
        ).strip()
        if not clean_q:
            clean_q = "documentary"

        is_medical_search = any(w in clean_q.lower() for w in ["cancer", "tumor", "oncology", "lung", "cough", "doctor", "hospital", "patient", "medical", "mortality", "radiology", "screening"])
        effective_query = clean_q
        if "cancer" in clean_q.lower() and not any(w in clean_q.lower() for w in ["cell", "oncology", "medical", "tumor", "mortality", "statistics", "lung"]):
            effective_query = f"{clean_q} medical oncology cells"

        ASTROLOGY_TERMS = [
            "constellation", "zodiac", "horoscope", "astronomy", "astrological",
            "johann bayer", "uranometria", "celestial atlas", "celestial chart",
            "astrological sign", "crab", "star chart"
        ]
        IRRELEVANT_STOCK_TERMS = [
            "scrabble", "wooden letter", "spelling 'death'", "alphabet blocks",
            "wooden tiles", "tiles spelling", "toy letter", "scrabble tiles", "toy blocks"
        ]
        SMOKING_TOBACCO_TERMS = [
            "cigarette", "cigarettes", "cigar", "ashtray", "smoking", "tobacco",
            "smoke", "burnt cigarette", "holding cigarette", "nicotine", "lighter",
            "vape", "hookah", "weed", "ash", "butts", "unlit cigarette", "pack of cigarettes",
            "smoker", "smoking habit"
        ]
        COVID_PANDEMIC_TERMS = [
            "covid", "covid-19", "coronavirus", "pandemic", "sars-cov-2",
            "quarantine", "lockdown", "vaccine", "confirmed cases",
            "johns hopkins", "sovereignty", "wuhan", "respirator n95"
        ]
        FINANCIAL_IRRELEVANT_TERMS = [
            "forex", "stock market", "crypto", "trading", "financial data",
            "fluctuating financial data", "bitcoin"
        ]

        # Check if the user query explicitly intended to search for smoking/tobacco
        query_intends_smoking = any(w in clean_q.lower() for w in ["smoke", "smoking", "cigarette", "cigar", "tobacco", "nicotine"])
        # Check if the user query explicitly intended to search for COVID-19
        query_intends_covid = any(w in clean_q.lower() for w in ["covid", "coronavirus", "pandemic", "sars-cov-2"])

        def filter_irrelevant(assets: List[MediaAsset]) -> List[MediaAsset]:
            result = []
            for a in assets:
                text_corpus = f"{getattr(a, 'title', '')} {getattr(a, 'description', '')} {getattr(a, 'author', '')} {getattr(a, 'download_url', '')}".lower()
                
                # Exclude astrology / zodiac
                if any(term in text_corpus for term in ASTROLOGY_TERMS):
                    continue
                # Exclude scrabble and wooden toy blocks
                if any(term in text_corpus for term in IRRELEVANT_STOCK_TERMS):
                    continue
                # Exclude financial charts
                if any(term in text_corpus for term in FINANCIAL_IRRELEVANT_TERMS):
                    continue
                # Exclude cigarette / smoking imagery unless the query explicitly asks for it
                if not query_intends_smoking and any(term in text_corpus for term in SMOKING_TOBACCO_TERMS):
                    continue
                # Exclude COVID-19 / pandemic tracker maps unless the query explicitly asks for it
                if not query_intends_covid and any(term in text_corpus for term in COVID_PANDEMIC_TERMS):
                    continue
                
                result.append(a)
            return result

        self.last_search_diagnostics: Dict[str, Any] = {
            "query": clean_q,
            "media_type": media_type,
            "provider_requested": provider,
            "provider_used": None,
            "waterfall_step": None,
            "attempts": []
        }

        # CASE A: Explicit Single Provider
        if provider == "pexels":
            self.last_search_diagnostics["attempts"].append("pexels")
            hits = (self.pexels.search_videos(effective_query, limit=limit, orientation=orientation)
                    if media_type == "video" else
                    self.pexels.search_images(effective_query, limit=limit, orientation=orientation))
            filtered = filter_irrelevant(hits)
            self.last_search_diagnostics["provider_used"] = "pexels"
            self.last_search_diagnostics["waterfall_step"] = "1. Pexels (explicit)"
            return [a.to_dict() for a in filtered[:limit]]

        elif provider == "pixabay":
            self.last_search_diagnostics["attempts"].append("pixabay")
            hits = (self.pixabay.search_videos(effective_query, limit=limit, orientation=orientation)
                    if media_type == "video" else
                    self.pixabay.search_images(effective_query, limit=limit, orientation=orientation))
            filtered = filter_irrelevant(hits)
            self.last_search_diagnostics["provider_used"] = "pixabay"
            self.last_search_diagnostics["waterfall_step"] = "2. Pixabay (explicit)"
            return [a.to_dict() for a in filtered[:limit]]

        elif provider == "google_ai":
            self.last_search_diagnostics["attempts"].append("google_ai")
            ai_item = self.generate_ai_media(effective_query, media_type=media_type)
            if ai_item:
                self.last_search_diagnostics["provider_used"] = "google_ai"
                self.last_search_diagnostics["waterfall_step"] = "Google AI (explicit)"
                return [ai_item]
            return []

        elif provider == "wikimedia":
            self.last_search_diagnostics["attempts"].append("wikimedia")
            hits = (self.wikimedia.search_videos(effective_query, limit=limit, orientation=orientation)
                    if media_type == "video" else
                    self.wikimedia.search_images(effective_query, limit=limit, orientation=orientation))
            filtered = filter_irrelevant(hits)
            self.last_search_diagnostics["provider_used"] = "wikimedia"
            self.last_search_diagnostics["waterfall_step"] = "5. Wikimedia (explicit)"
            return [a.to_dict() for a in filtered[:limit]]

        # CASE B: Waterfall Priority
        # Step 1: Pexels
        self.last_search_diagnostics["attempts"].append("pexels")
        try:
            pexels_hits = (self.pexels.search_videos(effective_query, limit=limit, orientation=orientation)
                           if media_type == "video" else
                           self.pexels.search_images(effective_query, limit=limit, orientation=orientation))
            pexels_filtered = filter_irrelevant(pexels_hits)
            if pexels_filtered:
                self.last_search_diagnostics["provider_used"] = "pexels"
                self.last_search_diagnostics["waterfall_step"] = "1. Pexels"
                return [a.to_dict() for a in pexels_filtered[:limit]]
        except Exception as e:
            print(f"[MediaSearch] Priority 1 (Pexels) failed: {e}")

        # Step 2: Pixabay
        self.last_search_diagnostics["attempts"].append("pixabay")
        try:
            pixabay_hits = (self.pixabay.search_videos(effective_query, limit=limit, orientation=orientation)
                            if media_type == "video" else
                            self.pixabay.search_images(effective_query, limit=limit, orientation=orientation))
            pixabay_filtered = filter_irrelevant(pixabay_hits)
            if pixabay_filtered:
                self.last_search_diagnostics["provider_used"] = "pixabay"
                self.last_search_diagnostics["waterfall_step"] = "2. Pixabay"
                return [a.to_dict() for a in pixabay_filtered[:limit]]
        except Exception as e:
            print(f"[MediaSearch] Priority 2 (Pixabay) failed: {e}")

        # Generated media and unrelated curated placeholders are never stock fallback.
        # Step 5: Wikimedia Fallback
        self.last_search_diagnostics["attempts"].append("wikimedia_fallback")
        try:
            wiki_hits = (self.wikimedia.search_videos(effective_query, limit=limit, orientation=orientation)
                         if media_type == "video" else
                         self.wikimedia.search_images(effective_query, limit=limit, orientation=orientation))
            wiki_filtered = filter_irrelevant(wiki_hits)
            if wiki_filtered:
                self.last_search_diagnostics["provider_used"] = "wikimedia"
                self.last_search_diagnostics["waterfall_step"] = "5. Wikimedia (fallback)"
                return [a.to_dict() for a in wiki_filtered[:limit]]
        except Exception as e:
            print(f"[MediaSearch] Priority 5 (Wikimedia Fallback) failed: {e}")

        self.last_search_diagnostics['provider_used'] = None
        self.last_search_diagnostics['waterfall_step'] = 'No matching stock results'
        return []

    def generate_ai_media(
        self,
        prompt: str,
        media_type: str = "image",
        aspect_ratio: str = "16:9",
        project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Self-generates an image or video using AI when external stock providers do not return relevant media.
        """
        import time
        from pathlib import Path

        clean_p = re.sub(r'^(make\s+a\s+video\s+of|generate\s+a\s+video\s+of|add\s+a\s+video\s+of|video\s+of|footage\s+of|clip\s+of|an?\s+)\s+', '', prompt.strip(), flags=re.IGNORECASE).strip()
        if not clean_p:
            clean_p = "clinical medical oncology research evidence"

        base_dir = Path(__file__).resolve().parent.parent.parent
        proj_slug = project_id or "proj_shared"
        from app.core.config import settings
        out_dir = settings.projects_dir / proj_slug / "media" / "downloaded"
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time() * 1000)

        if media_type == "video":
            out_file = out_dir / f"ai_gen_vid_{timestamp}.mp4"
            try:
                res = self.google_ai.generate_video(
                    prompt=clean_p,
                    aspect_ratio=aspect_ratio,
                    output_path=out_file
                )
                rel_url = f"/api/media/{proj_slug}/asset/downloaded/{out_file.name}"
                return {
                    "id": f"ai_vid_{timestamp}",
                    "provider": "google_ai_video",
                    "title": clean_p[:50].title(),
                    "url": rel_url,
                    "download_url": str(out_file),
                    "thumb_url": rel_url,
                    "source_credit": "Source: Google AI Video",
                    "media_type": "video",
                    "width": 1920, "height": 1080
                }
            except Exception as e:
                print(f"[MediaSearchService] AI video generation error: {e}")

        # Image generation (with resilient procedural fallback)
        out_file = out_dir / f"ai_gen_img_{timestamp}.jpg"
        try:
            res = self.google_ai.generate_image(
                prompt=clean_p,
                aspect_ratio=aspect_ratio,
                output_path=out_file
            )
            rel_url = f"/api/media/{proj_slug}/asset/downloaded/{out_file.name}"
            return {
                "id": f"ai_img_{timestamp}",
                "provider": "google_ai_image",
                "title": clean_p[:50].title(),
                "url": rel_url,
                "download_url": str(out_file),
                "thumb_url": rel_url,
                "source_credit": res.get("engine", "Source: Generated with Google AI"),
                "media_type": "image",
                "width": 1920, "height": 1080
            }
        except Exception as e:
            print(f"[MediaSearchService] Visual generation notice: {e}")
            return None

    def get_unique_fallback(self, topic_hint: str, used_set: set) -> Dict[str, Any]:
        """
        Selects a unique visual from CURATED_FALLBACK_MEDIA that has not yet been used on the timeline.
        """
        lower_hint = topic_hint.lower()
        preferred_cat = "doctor"
        if any(w in lower_hint for w in ["death", "deaths", "mortality", "fatal", "dying", "rate", "killer", "maximum"]):
            preferred_cat = "mortality"
        elif any(w in lower_hint for w in ["commonest", "most common", "prevalence", "incidence", "world"]):
            preferred_cat = "incidence"
        elif any(w in lower_hint for w in ["lung", "respiratory", "pulmonary"]):
            preferred_cat = "lung"
        elif any(w in lower_hint for w in ["detect", "detected", "screening", "scan", "ct", "x-ray"]):
            preferred_cat = "screening"
        elif any(w in lower_hint for w in ["treat", "chemo", "medicine", "drug", "surgery", "lymph"]):
            preferred_cat = "treatment"
        elif any(w in lower_hint for w in ["cell", "tumor", "pathology", "biopsy", "microscop"]):
            preferred_cat = "pathology"
        elif any(w in lower_hint for w in ["cough", "blood", "symptom"]):
            preferred_cat = "coughing"

        # Check preferred category first
        if preferred_cat in CURATED_FALLBACK_MEDIA:
            for item in CURATED_FALLBACK_MEDIA[preferred_cat]:
                if item.get("url") not in used_set and item.get("download_url") not in used_set:
                    return dict(item)

        # Then check any other category for an unused visual
        for cat, items in CURATED_FALLBACK_MEDIA.items():
            for item in items:
                if item.get("url") not in used_set and item.get("download_url") not in used_set:
                    return dict(item)

        # If everything is exhausted, cycle with a unique query param
        default_item = dict(CURATED_FALLBACK_MEDIA["doctor"][0])
        unique_id = f"unique_{len(used_set) + 1}"
        default_item["id"] = unique_id
        default_item["url"] = f"{default_item['url']}&salt={unique_id}"
        default_item["thumb_url"] = f"{default_item['thumb_url']}&salt={unique_id}"
        return default_item

    def rerank_candidates_with_vision(
        self,
        candidates: List[Dict[str, Any]],
        visual_reasoning: str,
        search_query: str,
        strict: bool = False
    ) -> Tuple[Dict[str, Any], str]:
        """
        Batches candidate thumbnails + visual reasoning to Gemini 2.5 Flash to pick the optimal match.
        Falls back to candidate #1 within seconds if the reranker call fails or times out.
        """
        from typing import Tuple
        if not candidates:
            return {}, "No candidates provided"
        if not strict and (len(candidates) == 1 or not visual_reasoning):
            return candidates[0], "Direct single candidate match"

        api_key = self.google_ai.get_api_key()
        if not api_key or (strict and any(t in api_key.lower() for t in ('testmock','placeholder','your_'))):
            if strict:return {}, 'Gemini visual review unavailable: missing or placeholder API key'
            return candidates[0], "Candidate #1 (Gemini API key not configured)"

        pool = candidates[:8]
        import concurrent.futures
        import requests

        def fetch_thumb(c):
            url = c.get("thumb_url") or c.get("url")
            if not url or not url.startswith("http"):
                return None
            try:
                r = requests.get(url, timeout=3.0, headers={"User-Agent": "Resolve-Companion/1.0"})
                if r.status_code == 200 and len(r.content) > 100:
                    from PIL import Image
                    from io import BytesIO
                    image=Image.open(BytesIO(r.content)).convert('RGB');image.thumbnail((768,768))
                    output=BytesIO();image.save(output,format='JPEG');return output.getvalue()
            except Exception:
                pass
            return None

        # Parallel thumbnail prefetch
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(pool)) as executor:
            thumb_bytes_list = list(executor.map(fetch_thumb, pool))

        try:
            import base64
            from app.services.editorial_planner import gemini_json

            contents: List[Any] = [
                f"You are an expert video editor and visual director reviewing stock media options for a talking-head documentary.\n\n"
                f"EDITORIAL CONTEXT & VISUAL REASONING:\n\"{visual_reasoning}\"\n\n"
                f"TARGET SEARCH QUERY:\n\"{search_query}\"\n\n"
                f"Evaluate the following {len(pool)} candidate images. Determine which image best matches the tone, subject accuracy, "
                f"and documentary credibility required. Return strictly JSON with 'selected_index' (0 to {len(pool)-1}) and 'justification'."
            ]

            if strict:
                contents.append("REJECT BY DEFAULT. Approve a candidate only if the required subject, action and setting from the context are plainly visible in its thumbnail. A loosely related scene (a generic office, desk, camera or person for a specific concept) is a rejection, not a best available match. Also return required_subject_visible (true/false) for the selected candidate and missing (list of required things you cannot see in it).")
            contents.append("You may reject ALL candidates: return selected_index=-1 and a reason. Also return confidence (0-1). Obey negative constraints and required entities/actions. Unseen thumbnails cannot be selected. The requested object/action must be clearly visible and in focus. Shared keywords alone are not relevance. Reject an illness/distress scene for a recovery statement, an unrelated person for a specific patient story, and unclear professional roles without contextual evidence. Follow supplied editor corrections and documented geography; do not infer nationality from appearance. Stock is illustration, not verification of a claim.")
            valid_images_count = 0
            for idx, (c, b) in enumerate(zip(pool, thumb_bytes_list)):
                desc = f"\nCandidate [{idx}]: Title='{c.get('title', 'Unknown')}', Provider='{c.get('provider', 'stock')}'"
                contents.append(desc)
                if b:
                    contents.append({"inlineData":{"data":base64.b64encode(b).decode(),"mimeType":"image/jpeg"}})
                    valid_images_count += 1

            if valid_images_count == 0:
                if strict:return {}, 'No decodable thumbnails available for visual review'
                return candidates[0], "Candidate #1 (Thumbnails unavailable for vision rerank)"

            parts=[{'text':c} if isinstance(c,str) else c for c in contents]
            data=gemini_json('Review the numbered candidates below.',timeout=25,image_parts=parts,max_requests=2)
            if data:
                sel_idx = int(data.get("selected_index", -1))
                justification = str(data.get("justification", "Best contextual visual alignment."))
                if strict and (not 0 <= sel_idx < len(pool) or not thumb_bytes_list[sel_idx] or float(data.get('confidence',0)) < .7):
                    return {}, justification
                if strict and (data.get('required_subject_visible') is False or data.get('missing')):
                    return {}, 'Required subject not visible: ' + (', '.join(map(str, data.get('missing') or [])) or justification)
                if 0 <= sel_idx < len(pool):
                    print(f"[MediaSearch] Vision rerank chose Candidate #{sel_idx} ({pool[sel_idx].get('title')}): {justification}")
                    return pool[sel_idx], justification
        except Exception as e:
            from app.services.editorial_planner import safe_error
            if strict:return {}, 'Visual review failed: '+safe_error(e)
            print(f"[MediaSearch] Vision review failed: {safe_error(e)}")
        finally:
            if 'client' in locals() and hasattr(client, '_api_client'):
                if not hasattr(client._api_client, '_async_httpx_client'):
                    client._api_client._async_httpx_client = None
                try:
                    client.close()
                except Exception:
                    pass

        return ({}, "Visual review failed; no unverified asset inserted") if strict else (candidates[0], "Candidate #1 (Default top relevance hit)")

    def auto_match_for_caption(
        self,
        caption_text: str,
        exclude_urls: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        visual_reasoning: Optional[str] = None
    ) -> Dict[str, Any]:
        ranked_queries = self.generate_search_queries(caption_text)
        used_set = set(exclude_urls or [])

        best_media = None
        selected_query = ranked_queries[0] if ranked_queries else "medical evidence"
        all_results: List[Dict[str, Any]] = []
        rerank_justification = ""

        # Iterate through ranked queries to find an asset not yet used on the timeline
        for query in ranked_queries:
            results = self.search_media(query, limit=10)
            if results and not all_results:
                all_results = results
            available = [m for m in results if m.get("url") not in used_set and m.get("download_url") not in used_set]
            if available:
                best_media, rerank_justification = self.rerank_candidates_with_vision(
                    available, visual_reasoning or caption_text, query, strict=True)
                if not best_media:
                    continue
                best_media['rerank_justification'] = rerank_justification
                selected_query = query
                break

        if not best_media:
            return {'status':'needs_review', 'search_term':selected_query, 'ranked_queries':ranked_queries,
                    'broll_title':'', 'source_citation':'', 'media':None, 'all_results':all_results,
                    'rerank_justification':rerank_justification or 'No relevant, reviewed media was found. No substitute inserted.'}
        broll_title=best_media.get('title','')
        source_citation=best_media.get('source_credit','')

        return {
            "search_term": selected_query,
            "ranked_queries": ranked_queries,
            "broll_title": broll_title,
            "source_citation": source_citation,
            "media": best_media,
            "all_results": all_results or [best_media],
            "rerank_justification": rerank_justification
        }

media_search_service = MediaSearchService()

