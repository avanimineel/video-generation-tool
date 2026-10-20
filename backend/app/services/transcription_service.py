import re
import os
from typing import List, Dict, Any, Tuple, Optional
from app.core.models import CaptionItem, WordTiming, CaptionStyle, MotionGraphicItem
from app.core.logging_setup import get_logger, format_exception_detail
from app.services.media_search_service import media_search_service
from app.services.whisper_device import (
    load_whisper_model,
    resolve_whisper_device,
    whisper_cache_key,
)

logger = get_logger(__name__)

def join_number_fragments(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Whisper times "3,000" as two words ("3" and ",000"). Rejoin them so a
    # number is never split across subtitle boxes; no spoken text is changed.
    joined: List[Dict[str, Any]] = []
    for word in words:
        if joined and re.match(r'[,.]\d', word['word']) and joined[-1]['word'][-1:].isdigit():
            joined[-1] = {**joined[-1], 'word': joined[-1]['word'] + word['word'], 'end': word['end']}
        else:
            joined.append(dict(word))
    return joined

STOCK_HALLUCINATIONS = ('thank you for watching', 'thanks for watching', 'please subscribe', 'like and subscribe',
                        'subtitles by', 'amara.org', 'transcribed by', 'see you in the next video')


def hallucinated(segment):
    """Reason to drop a Whisper segment that is not real speech, or None.
    Uses Whisper's own confidence signals; ordinary low-volume speech is kept."""
    text = ' '.join(re.findall(r"[\w']+", (getattr(segment, 'text', '') or '').casefold()))
    no_speech = float(getattr(segment, 'no_speech_prob', 0) or 0)
    logprob = float(getattr(segment, 'avg_logprob', 0) or 0)
    if float(getattr(segment, 'compression_ratio', 0) or 0) > 2.4:
        return 'repetition loop'
    if no_speech > .6 and logprob < -1.0:
        return 'silence decoded as speech'
    if any(phrase in text for phrase in STOCK_HALLUCINATIONS) and (no_speech > .3 or logprob < -.7):
        return 'stock closing phrase on low-confidence audio'
    return None


class TranscriptionService:
    CONDITIONS = {
        'cancer', 'diabetes', 'hypertension', 'stroke', 'tumor', 'inflammation',
        'alzheimer', "alzheimer's", 'arrhythmia', 'sepsis', 'infection', 'dementia',
        'cholesterol', 'sclerosis', 'syndrome', 'disease', 'chronic', 'acute',
        'myocardial', 'infarction', 'cardiovascular', 'osteoporosis', 'arthritis',
        'asthma', 'depression', 'anxiety', 'obesity', 'cirrhosis', 'pancreatitis'
    }
    ORGANS = {
        'heart', 'brain', 'gut', 'liver', 'kidney', 'kidneys', 'lungs', 'lung',
        'pancreas', 'artery', 'arteries', 'neurons', 'neuron', 'mitochondria',
        'spine', 'vessels', 'vessel', 'blood', 'cells', 'cell', 'microbiome',
        'stomach', 'colon', 'thyroid', 'muscle', 'bone', 'joints', 'veins'
    }
    EMOTIONS = {
        'fatal', 'lethal', 'danger', 'breakthrough', 'miracle', 'critical',
        'emergency', 'toxic', 'cure', 'alert', 'warning', 'deadly', 'shocking',
        'kill', 'life-saving', 'secret', 'destroy', 'boost', 'protect'
    }

    def analyze_word_emphasis(self, word: str) -> Dict[str, Any]:
        clean = re.sub(r'[^a-zA-Z0-9%]', '', word.lower())
        # 1. Metrics & Numbers
        if re.search(r'\d+[%xXmgkK]?', word) or clean in {'double', 'triple', 'half', 'million', 'billion', 'percent', 'zero'}:
            return {'is_keyword': True, 'keyword_category': 'metric', 'keyword_color': '#00F0FF', 'keyword_font': 'Montserrat'}
        
        # 2. Medical Conditions (Vivid Red / Coral)
        if clean in self.CONDITIONS or any(c in clean for c in ['cancer', 'diabet', 'inflam', 'hyperten', 'stroke', 'tumor']):
            return {'is_keyword': True, 'keyword_category': 'condition', 'keyword_color': '#FF4D4D', 'keyword_font': 'Playfair Display'}
        
        # 3. Organs & Anatomy (Electric Lime)
        if clean in self.ORGANS or any(o in clean for o in ['cardio', 'neuro', 'mitochondr']):
            return {'is_keyword': True, 'keyword_category': 'organ', 'keyword_color': '#CCFF00', 'keyword_font': 'Playfair Display'}
        
        # 4. Emotional Triggers & Warnings (Gold / Amber)
        if clean in self.EMOTIONS:
            return {'is_keyword': True, 'keyword_category': 'impact', 'keyword_color': '#FFB800', 'keyword_font': 'Montserrat'}
        
        return {'is_keyword': False, 'keyword_category': None, 'keyword_color': None, 'keyword_font': None}

    def detect_language(self, text: str) -> str:
        if re.search(r'[ऀ-ॿ]', text):
            return 'hi'
        hinglish_words = {'kya', 'hai', 'aap', 'hum', 'toh', 'bhi', 'nahi', 'karna', 'hoga', 'yeh', 'woh', 'achha', 'matlab', 'kaise', 'bhai', 'yaar'}
        words = set(re.findall(r'[a-zA-Z]+', text.lower()))
        if len(words.intersection(hinglish_words)) >= 2:
            return 'hinglish'
        return 'en'

    def generate_timeline_placeholders(self, duration_seconds: float) -> Tuple[str, List[CaptionItem]]:
        captions: List[CaptionItem] = []
        cap_dur = 3.0
        gap = 0.5
        t = 0.5
        idx = 1
        while t < duration_seconds - 0.5:
            end_t = min(round(duration_seconds - 0.2, 2), round(t + cap_dur, 2))
            chunk_words = [f"Clip", f"{idx}:", "Click", "to", "edit"]
            words = []
            dur_per_word = (end_t - t) / max(1, len(chunk_words))
            for w_idx, w in enumerate(chunk_words):
                w_start = round(t + w_idx * dur_per_word, 2)
                w_end = round(w_start + dur_per_word, 2)
                words.append(WordTiming(word=w, start=w_start, end=w_end, highlight=False))

            captions.append(CaptionItem(
                id=f"cap_clip_{idx}_{int(t * 100)}",
                start=round(t, 2),
                end=end_t,
                text=f"Clip {idx}: Click to edit dialogue",
                pos_x=0.5,
                pos_y=0.78,
                words=words,
                style=CaptionStyle(
                    font_family='Montserrat',
                    font_weight='bold',
                    font_size=42,
                    text_color='#FFFFFF',
                    has_background=True,
                    background_color='#000000',
                    background_opacity=0.75,
                    corner_radius=16,
                    padding_x=20,
                    padding_y=10,
                    animation_type='none',
                    highlight_active_color='#CCFF00',
                    highlight_past_color='#B0B0B0',
                    highlight_future_color='#FFFFFF',
                    highlight_scale=1.0
                ),
                source_language='en'
            ))
            t = end_t + gap
            idx += 1
            if idx > 15:
                break
        return 'en', captions

    def transcribe_audio_or_text(
        self,
        raw_text: str,
        start_offset: float = 0.0,
        words_per_caption: int = 3
    ) -> Tuple[str, List[CaptionItem]]:
        lang = self.detect_language(raw_text)
        
        # Split into sentences or phrases cleanly
        clean_text = raw_text.replace(chr(10), ' ').replace('।', '.')
        raw_sentences = [s.strip() for s in re.split(r'[.!?]+', clean_text) if s.strip()]
        if not raw_sentences:
            return self.generate_timeline_placeholders(15.0)

        captions: List[CaptionItem] = []
        current_time = start_offset

        for idx, sentence in enumerate(raw_sentences):
            words = sentence.split()
            for c_idx in range(0, len(words), words_per_caption):
                chunk_words = words[c_idx:c_idx + words_per_caption]
                chunk_text = ' '.join(chunk_words)
                
                word_timings: List[WordTiming] = []
                chunk_start = current_time
                for w in chunk_words:
                    w_dur = max(0.25, round(len(w) * 0.05 + 0.15, 2))
                    w_end = round(current_time + w_dur, 2)
                    kw_info = self.analyze_word_emphasis(w)
                    word_timings.append(WordTiming(
                        word=w,
                        start=current_time,
                        end=w_end,
                        highlight=False,
                        is_keyword=kw_info['is_keyword'],
                        keyword_category=kw_info.get('keyword_category'),
                        keyword_color=kw_info.get('keyword_color'),
                        keyword_font=kw_info.get('keyword_font')
                    ))
                    current_time = w_end

                chunk_end = current_time
                current_time = round(current_time + 0.15, 2)

                caption_id = f'cap_{idx}_{c_idx}_{int(chunk_start * 100)}'
                
                style = CaptionStyle(
                    font_family='Montserrat',
                    font_weight='bold',
                    font_size=42,
                    text_color='#FFFFFF',
                    has_background=True,
                    background_color='#000000',
                    background_opacity=0.75,
                    corner_radius=16,
                    padding_x=20,
                    padding_y=10,
                    animation_type='none',
                    highlight_active_color='#CCFF00',
                    highlight_past_color='#B0B0B0',
                    highlight_future_color='#FFFFFF',
                    highlight_scale=1.0
                )

                captions.append(CaptionItem(
                    id=caption_id,
                    start=chunk_start,
                    end=chunk_end,
                    text=chunk_text,
                    pos_x=0.5,
                    pos_y=0.78,
                    words=word_timings,
                    style=style,
                    source_language=lang
                ))

        return lang, captions

    _whisper_models: Dict[str, Any] = {}

    @classmethod
    def clear_whisper_model_cache(cls):
        """Test helper: drop cached WhisperModel instances."""
        cls._whisper_models.clear()

    @classmethod
    def get_whisper_model(cls, model_size: Optional[str] = None):
        target_size = model_size or os.getenv('WHISPER_MODEL_SIZE', 'base')
        # Probe intended device for cache key; load_whisper_model may fall back to CPU.
        intended_device, intended_compute, _ = resolve_whisper_device()
        cache_key = whisper_cache_key(target_size, intended_device, intended_compute)
        if cache_key in cls._whisper_models:
            return cls._whisper_models[cache_key]
        # Also hit CPU cache if a prior CUDA attempt already fell back.
        cpu_key = whisper_cache_key(target_size, 'cpu', resolve_whisper_device('cpu')[1])
        if intended_device == 'cuda' and cpu_key in cls._whisper_models:
            return cls._whisper_models[cpu_key]

        os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        try:
            model, device, compute_type, reason = load_whisper_model(target_size)
            key = whisper_cache_key(target_size, device, compute_type)
            cls._whisper_models[key] = model
            return model
        except Exception as e:
            logger.exception(
                "whisper_model_init_failed",
                event="whisper_model_init_failed",
                model_size=target_size,
                error_detail=format_exception_detail(e),
            )
            if target_size != 'base':
                return cls.get_whisper_model('base')
            return None

    def chunk_segment_words(self, words: List[Dict[str, Any]], words_per_caption: int = 3) -> List[List[Dict[str, Any]]]:
        if not words:
            return []

        # Never merge an orphan into a four-word box. Preserve the final
        # remainder rather than inventing or dropping spoken words.
        size = max(1, min(20, words_per_caption))
        return [words[i:i + size] for i in range(0, len(words), size)]

    def transcribe_with_whisper(
        self,
        media_path: str,
        words_per_caption: int = 3,
        task: str = 'translate',
        model_size: Optional[str] = None
    ) -> Tuple[str, List[CaptionItem]]:
        target_model = model_size or os.getenv('WHISPER_MODEL_SIZE', 'base')
        model = self.get_whisper_model(target_model)
        if not model:
            raise RuntimeError('Speech model could not load. Check the local Whisper installation.')

        # Default to 'translate' for high-accuracy English subtitles from Hindi/Hinglish speech
        whisper_task = task if task in ['transcribe', 'translate'] else 'translate'
        prompt = "Transcribe the spoken dialogue faithfully, preserving names, numbers and technical terms."

        # Fast 16kHz mono audio extraction: avoids slow video container demuxing in Python
        audio_target = media_path
        ext = os.path.splitext(media_path)[1].lower()
        if ext in ['.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi']:
            try:
                from app.core.config import settings
                wav_cand = os.path.splitext(media_path)[0] + "_16k.wav"
                if not os.path.exists(wav_cand) or os.path.getmtime(media_path) > os.path.getmtime(wav_cand):
                    import subprocess
                    subprocess.run(
                        [settings.ffmpeg_bin, "-y", "-i", media_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_cand],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True
                    )
                if os.path.exists(wav_cand):
                    audio_target = wav_cand
            except Exception as e:
                print(f"[Whisper] 16kHz audio extraction notice: {e}")
                audio_target = media_path

        # Use beam search for coherent multilingual speech rather than greedy decoding.
        beam_sz = 5
        segments, info = model.transcribe(
            audio_target,
            beam_size=beam_sz,
            best_of=1,
            task=whisper_task,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=200),
            initial_prompt=prompt,
            condition_on_previous_text=False,
            word_timestamps=True
        )
        detected_lang = 'en' if whisper_task == 'translate' else (info.language or 'en')

        captions: List[CaptionItem] = []
        cap_counter = 0

        for seg in segments:
            reason = hallucinated(seg)
            if reason:
                print(f"[Transcription] Dropped {seg.start:.2f}-{seg.end:.2f}s ({reason}): {seg.text.strip()[:60]!r}")
                continue
            # Extract acoustic words from this specific segment
            seg_words = []
            if seg.words:
                for w in seg.words:
                    clean_w = w.word.strip()
                    # Medical phonetic normalization
                    if clean_w.lower() in ['cuff', 'cuff,']:
                        clean_w = 'cough,' if clean_w.endswith(',') else 'cough'
                    elif clean_w.lower() in ['jeep', 'jeep,'] and any(k in prompt.lower() for k in ('tongue', 'mouth', 'teeth', 'cancer')):
                        clean_w = 'tongue,' if clean_w.endswith(',') else 'tongue'
                    if clean_w:
                        seg_words.append({
                            'word': clean_w,
                            'start': round(float(w.start), 2),
                            'end': round(float(w.end), 2)
                        })
            else:
                raw_words = seg.text.strip().split()
                if raw_words:
                    seg_dur = max(0.2, float(seg.end - seg.start))
                    w_dur = seg_dur / len(raw_words)
                    for i, rw in enumerate(raw_words):
                        seg_words.append({
                            'word': rw,
                            'start': round(float(seg.start) + i * w_dur, 2),
                            'end': round(float(seg.start) + (i + 1) * w_dur, 2)
                        })

            seg_words = join_number_fragments(seg_words)
            if not seg_words:
                continue

            # Break segment into sentence-aware 3-5 word subtitle chunks
            chunks = self.chunk_segment_words(seg_words, words_per_caption)

            for chunk in chunks:
                if not chunk:
                    continue
                c_start = chunk[0]['start']
                c_end = max(chunk[-1]['end'], round(c_start + 0.5, 2))
                c_text = " ".join(w['word'] for w in chunk)

                word_objs = []
                for w in chunk:
                    kw_info = self.analyze_word_emphasis(w['word'])
                    word_objs.append(WordTiming(
                        word=w['word'],
                        start=w['start'],
                        end=w['end'],
                        highlight=False,
                        is_keyword=kw_info['is_keyword'],
                        keyword_category=kw_info.get('keyword_category'),
                        keyword_color=kw_info.get('keyword_color'),
                        keyword_font=kw_info.get('keyword_font')
                    ))

                cap_counter += 1
                cap_item = CaptionItem(
                    id=f"cap_wh_{cap_counter}_{int(c_start * 100)}",
                    start=c_start,
                    end=c_end,
                    text=c_text,
                    translated_text=c_text,
                    pos_x=0.5,
                    pos_y=0.82,
                    words=word_objs,
                    style=CaptionStyle(
                        font_family='Montserrat',
                        font_weight='bold',
                        font_size=42,
                        text_color='#FFFFFF',
                        has_background=True,
                        background_color='#000000',
                        background_opacity=0.75,
                        corner_radius=16,
                        padding_x=20,
                        padding_y=10,
                        animation_type='none',
                        highlight_active_color='#CCFF00',
                        highlight_past_color='#B0B0B0',
                        highlight_future_color='#FFFFFF',
                        highlight_scale=1.0
                    ),
                    source_language=detected_lang
                )
                captions.append(cap_item)

        # Bridge silence gaps between consecutive captions so subtitles persist across speech pauses
        for i in range(len(captions) - 1):
            curr = captions[i]
            nxt = captions[i + 1]
            gap = nxt.start - curr.end
            if gap < 0 or 0 < gap <= .35:
                curr.end = nxt.start

        return detected_lang, captions

    def transcribe_with_gemini(
        self,
        audio_path: str,
        api_key: str,
        words_per_caption: int = 3
    ) -> Tuple[str, List[CaptionItem]]:
        try:
            from google import genai
            from google.genai import types
            import json

            client = genai.Client(api_key=api_key)
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()

            prompt = (
                "You are an expert video subtitle transcriber. "
                "Transcribe the spoken words from this audio into timed captions. "
                "Detect language as 'en', 'hi', or 'hinglish'. "
                "Return valid JSON strictly matching: "
                "{\"detected_language\": \"en\", \"captions\": [{\"start\": 0.0, \"end\": 2.5, \"text\": \"spoken line\", "
                "\"words\": [{\"word\": \"spoken\", \"start\": 0.0, \"end\": 1.2}, {\"word\": \"line\", \"start\": 1.2, \"end\": 2.5}]}]}"
            )

            res = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type='audio/mp3'),
                    prompt
                ]
            )
            raw = res.text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n", "", raw)
                raw = re.sub(r"\n```$", "", raw)
            data = json.loads(raw)
            lang = data.get("detected_language", "en")
            caps: List[CaptionItem] = []
            for idx, c in enumerate(data.get("captions", [])):
                wt = [WordTiming(**w) for w in c.get("words", [])]
                caps.append(CaptionItem(
                    id=f"cap_gemini_{idx}",
                    start=float(c.get("start", 0)),
                    end=float(c.get("end", 2)),
                    text=c.get("text", ""),
                    pos_x=0.5,
                    pos_y=0.82,
                    words=wt,
                    style=CaptionStyle(
                        font_family='Montserrat',
                        font_weight='bold',
                        font_size=42,
                        text_color='#FFFFFF',
                        has_background=True,
                        background_color='#000000',
                        background_opacity=0.75,
                        corner_radius=16,
                        padding_x=20,
                        padding_y=10,
                        animation_type='none',
                        highlight_active_color='#CCFF00',
                        highlight_past_color='#B0B0B0',
                        highlight_future_color='#FFFFFF',
                        highlight_scale=1.0
                    ),
                    source_language=lang
                ))
            if caps:
                return lang, caps
        except Exception as e:
            print("Gemini transcription error:", e)
        return self.generate_timeline_placeholders(30.0)

    def enrich_captions_with_keywords(self, captions: List[CaptionItem]) -> List[CaptionItem]:
        enriched = []
        for cap in captions:
            new_words = []
            for w in cap.words:
                kw = self.analyze_word_emphasis(w.word)
                new_words.append(WordTiming(
                    word=w.word,
                    start=w.start,
                    end=w.end,
                    highlight=w.highlight,
                    is_keyword=kw['is_keyword'],
                    keyword_category=kw.get('keyword_category'),
                    keyword_color=kw.get('keyword_color'),
                    keyword_font=kw.get('keyword_font')
                ))
            new_cap = cap.model_copy()
            new_cap.words = new_words
            enriched.append(new_cap)
        return enriched

    def detect_dimensions_and_cues(
        self,
        captions: List[CaptionItem],
        project_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[MotionGraphicItem], List[Dict[str, Any]]]:
        if not captions:
            return [], [], []

        MEASUREMENT_REGEX = re.compile(
            r'\b(\d+(?:\.\d+)?)\s*(feet|foot|ft|meters|meter|m|inches|inch|in|miles|mile|km|mph|km/h|knots|lbs|kg|tons|ton|volts|watts|deg|degrees|percent|%|cm|mm)\b'
            r'|\b(mach\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*mm|stage\s*[1-4]|stage\s*one|stage\s*two|stage\s*three|stage\s*four)\b',
            re.IGNORECASE
        )

        SEMANTIC_PHRASE_PATTERNS = [
            {
                "id": "mortality_burden",
                "category": "Epidemiology & Global Mortality Burden",
                "pattern": re.compile(r'\b(maximum\s+cancer[\s-]related\s+deaths?|highest\s+cancer\s+deaths?|highest\s+mortality|leading\s+cause\s+of\s+cancer\s+deaths?|causes?\s+the\s+most\s+deaths?)\b', re.IGNORECASE),
                "template_name": "50/50 Vertical Split (Mortality Statistics)",
                "topic_title": "Mortality Statistics & Global Disease Burden",
                "topic_explanation": "global oncological mortality data, fatality rates, and epidemiologic disease burden",
                "default_query": "medical chart doctor hospital data"
            },
            {
                "id": "global_incidence",
                "category": "Global Cancer Incidence & Epidemiology",
                "pattern": re.compile(r'\b(commonest\s+cancer\s+in\s+the\s+world|most\s+common\s+cancer\s+in\s+the\s+world|lung\s+cancer\s+is\s+the\s+commonest|commonest\s+cancer|most\s+common\s+cancer)\b', re.IGNORECASE),
                "template_name": "50/50 Vertical Split (Global Incidence)",
                "topic_title": "Global Cancer Incidence & Epidemiology",
                "topic_explanation": "global prevalence, anatomical pulmonary structure, and epidemiological incidence",
                "default_query": "pulmonary lungs anatomy medical"
            },
            {
                "id": "diagnostic_screening",
                "category": "Radiological Screening & Early Detection",
                "pattern": re.compile(r'\b(not\s+detected\s+(?:here|early|in\s+time)|diagnostic\s+screening|chest\s+ct\s+scan|low[\s-]dose\s+ct|early\s+detection\s+scan|diagnosed\s+with\s+lung\s+cancer)\b', re.IGNORECASE),
                "template_name": "50/50 Vertical Split (Diagnostic Screening)",
                "topic_title": "Diagnostic Screening & CT Imaging",
                "topic_explanation": "radiographic chest CT screening, axial tomography slices, and diagnostic scans",
                "default_query": "chest ct scan radiology lung screening"
            },
            {
                "id": "differential_diagnosis",
                "category": "Differential Diagnostics & Misdiagnosis",
                "pattern": re.compile(r'\b(tb\s+medicines?|tuberculosis\s+treatment|lung\s+infection|misdiagnosed\s+as\s+tb|confused\s+with\s+tuberculosis|bacterial\s+infection)\b', re.IGNORECASE),
                "template_name": "50/50 Vertical Split (Differential Diagnostics)",
                "topic_title": "Differential Diagnosis: TB vs Neoplasm",
                "topic_explanation": "radiographic differential diagnosis between infectious tuberculosis infiltration and malignant nodules",
                "default_query": "pulmonary tuberculosis radiology infection"
            },
            {
                "id": "clinical_symptoms",
                "category": "Clinical Symptoms & Hemoptysis",
                "pattern": re.compile(r'\b(patient\s+is\s+bloodied|coughing\s+blood|blood\s+in\s+sputum|persistent\s+cough|shortness\s+of\s+breath|respiratory\s+distress)\b', re.IGNORECASE),
                "template_name": "50/50 Vertical Split (Clinical Symptoms)",
                "topic_title": "Clinical Symptoms: Hemoptysis & Cough",
                "topic_explanation": "clinical manifestation of respiratory symptoms including hemoptysis and bronchial distress",
                "default_query": "patient coughing respiratory clinic consultation"
            },
            {
                "id": "surgical_resection",
                "category": "Surgical Oncology & Lymphadenectomy",
                "pattern": re.compile(r'\b(along\s+with\s+lymph\s+nodes?|part\s+of\s+lung\s+also\s+comes\s+out|lymph\s+nodes?|surgical\s+resection|lobectomy|thoracic\s+surgery)\b', re.IGNORECASE),
                "template_name": "50/50 Vertical Split (Surgical Resection)",
                "topic_title": "Surgical Resection & Lymphadenectomy",
                "topic_explanation": "thoracic oncology surgical procedure including anatomical lobectomy and regional lymph node clearance",
                "default_query": "thoracic surgery operating room oncology"
            },
            {
                "id": "cellular_pathology",
                "category": "Cellular Pathology & Oncogenesis",
                "pattern": re.compile(r'\b(malignant\s+tumor\s+growth|cancer\s+cells?\s+dividing|cellular\s+mutation|tumor\s+microenvironment|histological\s+biopsy)\b', re.IGNORECASE),
                "template_name": "50/50 Vertical Split (Cellular Pathology)",
                "topic_title": "Cellular Pathology & Histology",
                "topic_explanation": "microscopic histopathological evaluation of aberrant neoplastic cellular growth",
                "default_query": "cancer cell histology microscopy oncology"
            },
            {
                "id": "kinetic_action",
                "category": "Cinematic Kinetic Action Beat",
                "pattern": re.compile(r'\b(rocket\s+launch|spacecraft\s+liftoff|eject\s+from\s+cockpit|supersonic\s+flight|mach\s*\d+)\b', re.IGNORECASE),
                "template_name": "50/50 Vertical Split (Kinetic Action)",
                "topic_title": "Aerospace Kinetic Transition",
                "topic_explanation": "high-velocity aerospace propulsion and kinetic dynamics",
                "default_query": "rocket launch aerospace flight"
            }
        ]

        CONVERSATIONAL_INTRO_REGEX = re.compile(
            r'^(today\s*,?\s*)?(we\s+are\s+starting|welcome\s+to|in\s+this\s+video|let[\'s\s]+talk\s+about|we\s+are\s+going\s+to\s+talk\s+about|i\s+want\s+to\s+talk\s+about|hello\s+everyone|welcome\s+back|starting\s+a\s+new\s+series)\b',
            re.IGNORECASE
        )

        sentence_contexts: List[Dict[str, Any]] = []
        curr_caps: List[CaptionItem] = []
        for i, cap in enumerate(captions):
            curr_caps.append(cap)
            is_terminal = bool(re.search(r'[.?!]\s*$', cap.text.strip()))
            gap_to_next = False
            if i < len(captions) - 1:
                next_cap = captions[i + 1]
                if next_cap.start - cap.end > 0.6:
                    gap_to_next = True

            if is_terminal or gap_to_next:
                s_text = " ".join(c.text.strip() for c in curr_caps)
                s_words = []
                for c in curr_caps:
                    s_words.extend(c.words)
                sentence_contexts.append({
                    "text": s_text,
                    "start": curr_caps[0].start,
                    "end": curr_caps[-1].end,
                    "caption_ids": [c.id for c in curr_caps],
                    "captions": list(curr_caps),
                    "words": s_words
                })
                curr_caps = []
        if curr_caps:
            s_text = " ".join(c.text.strip() for c in curr_caps)
            s_words = []
            for c in curr_caps:
                s_words.extend(c.words)
            sentence_contexts.append({
                "text": s_text,
                "start": curr_caps[0].start,
                "end": curr_caps[-1].end,
                "caption_ids": [c.id for c in curr_caps],
                "captions": list(curr_caps),
                "words": s_words
            })

        detected_cues: List[Dict[str, Any]] = []
        generated_graphics: List[MotionGraphicItem] = []
        reasoning_log: List[Dict[str, Any]] = []
        used_media_urls: List[str] = []
        last_cue_end = -10.0

        for sent in sentence_contexts:
            sent_text = sent["text"]

            # 1. Quantitative Dimensions
            dim_matches = list(MEASUREMENT_REGEX.finditer(sent_text))
            for m in dim_matches:
                match_text = m.group(0).strip()
                c_start = sent["start"]
                for w in sent["words"]:
                    if any(part.lower() in w.word.lower() for part in match_text.split()):
                        c_start = w.start
                        break

                if c_start < last_cue_end + 1.2:
                    continue

                g_item = MotionGraphicItem(
                    id=f"dim_{int(c_start * 100)}_{len(generated_graphics)}",
                    start=round(c_start, 2),
                    end=round(min(c_start + 2.8, sent["end"] + 0.5), 2),
                    template_id="dimension_callout",
                    title=f"Dimension: {match_text.upper()}",
                    parameters={
                        "measurement_text": match_text.upper(),
                        "subtext": "Technical Specification",
                        "line_orientation": "horizontal",
                        "line_length_pct": 65,
                        "color": "#00F0FF"
                    },
                    pos_x=0.5,
                    pos_y=0.45,
                    scale=1.0
                )
                generated_graphics.append(g_item)
                last_cue_end = g_item.end

                ts_reason = (
                    f"Placed at {g_item.start:.2f}s coinciding with vocal articulation of metric '{match_text}'. "
                    f"Synchronizing dimension callout to acoustic onset reinforces retention of numerical data."
                )
                img_reason = (
                    f"Generated architectural HUD dimension callout for '{match_text.upper()}' "
                    f"with high-contrast cyan (#00F0FF) bounding pill and precision ticks."
                )
                layout_reason = "Centered in upper-mid quadrant (Y=0.45), safely above bottom subtitles."
                pacing_reason = "Focused 2.8s display window calibrated to alphanumeric reading speed."

                cue_entry = {
                    "type": "dimension_callout",
                    "term": match_text,
                    "caption_id": sent["caption_ids"][0],
                    "start": g_item.start,
                    "end": g_item.end,
                    "graphic_id": g_item.id,
                    "category": "Quantitative Dimension & Metric",
                    "reasoning": {
                        "cue_index": len(generated_graphics),
                        "graphic_id": g_item.id,
                        "template_id": "dimension_callout",
                        "template_name": "Architectural Dimension Callout",
                        "timestamp_start": g_item.start,
                        "timestamp_end": g_item.end,
                        "timestamp_formatted": f"{int(g_item.start // 60):02d}:{g_item.start % 60:05.2f}",
                        "duration_sec": round(g_item.end - g_item.start, 2),
                        "spoken_trigger_phrase": sent_text,
                        "trigger_term": match_text,
                        "cue_category": "Quantitative Dimension & Metric",
                        "timestamp_logic": ts_reason,
                        "image_logic": img_reason,
                        "layout_logic": layout_reason,
                        "pacing_logic": pacing_reason,
                        "search_query": f"dimension measurement {match_text}",
                        "source_provider": "Procedural HUD Engine",
                        "media_url": None,
                        "media_type": "vector_graphic"
                    }
                }
                detected_cues.append(cue_entry)
                reasoning_log.append(cue_entry["reasoning"])

            # 2. Contextual Sentence & Semantic Phrase Evaluation
            eval_text = sent_text
            is_intro = bool(CONVERSATIONAL_INTRO_REGEX.search(sent_text))
            if is_intro:
                cleaned_sub = re.sub(
                    r'^(today\s*,?\s*)?(we\s+are\s+starting|welcome\s+to|in\s+this\s+video|let[\'s\s]+talk\s+about|we\s+are\s+going\s+to\s+talk\s+about|i\s+want\s+to\s+talk\s+about|hello\s+everyone|welcome\s+back|starting\s+a\s+new\s+series)[^,.:;]*[,.:;]?\s*',
                    '',
                    sent_text,
                    flags=re.IGNORECASE
                ).strip()
                if cleaned_sub and len(cleaned_sub) > 10:
                    eval_text = cleaned_sub
                else:
                    continue

            matched_pattern = None
            matched_phrase = None
            for p in SEMANTIC_PHRASE_PATTERNS:
                m = p["pattern"].search(eval_text)
                if m:
                    matched_pattern = p
                    matched_phrase = m.group(0).strip()
                    break

            if not matched_pattern:
                CLINICAL_ENTITIES_REGEX = re.compile(
                    r'\b(cancer|tumor|lungs?|disease|infection|tuberculosis|biopsy|surgery|chemotherapy|radiation|metastasis|pulmonary|nodule|pathology)\b',
                    re.IGNORECASE
                )
                m_ent = CLINICAL_ENTITIES_REGEX.search(eval_text)
                if m_ent and len(eval_text.split()) >= 4:
                    ent = m_ent.group(0).lower()
                    words_in_eval = eval_text.split()
                    idx_ent = -1
                    for wi, w in enumerate(words_in_eval):
                        if ent in w.lower():
                            idx_ent = wi
                            break
                    if idx_ent != -1:
                        w_start = max(0, idx_ent - 1)
                        w_end = min(len(words_in_eval), idx_ent + 3)
                        extracted_phrase = " ".join(words_in_eval[w_start:w_end])
                    else:
                        extracted_phrase = eval_text[:40]

                    matched_pattern = {
                        "id": "clinical_evidence",
                        "category": "Clinical Evidence & Medical Context",
                        "template_name": f"50/50 Vertical Split ({ent.title()})",
                        "topic_title": f"Clinical Focus: {extracted_phrase.title()}",
                        "topic_explanation": f"clinical documentary evidence corroborating {extracted_phrase}",
                        "default_query": f"{ent} clinical oncology healthcare"
                    }
                    matched_phrase = extracted_phrase

            if matched_pattern and matched_phrase:
                phrase_tokens = matched_phrase.lower().split()
                c_start = sent["start"]
                if phrase_tokens:
                    first_tok = re.sub(r'[^a-zA-Z0-9]', '', phrase_tokens[0])
                    for w in sent["words"]:
                        w_clean = re.sub(r'[^a-zA-Z0-9]', '', w.word.lower())
                        if first_tok and first_tok in w_clean:
                            c_start = max(sent["start"], round(w.start - 0.15, 2))
                            break

                # B-roll clamping rule: no B-roll other than white report can extend more than 1.0 second
                c_end = round(min(c_start + 1.0, sent["end"]), 2)

                if c_start >= last_cue_end + 1.5:
                    match_info = media_search_service.auto_match_for_caption(
                        sent_text,
                        exclude_urls=used_media_urls,
                        project_id=project_id
                    )
                    broll_title = match_info.get("broll_title", matched_pattern["topic_title"])
                    citation = match_info.get("source_citation", "Source: Clinical Research Archives")
                    media_asset = match_info.get("media", {})
                    media_url = media_asset.get("url", "")
                    media_thumb = media_asset.get("thumb_url", media_url)
                    media_type = media_asset.get("media_type", "image")
                    primary_query = match_info.get("search_term", matched_pattern.get("default_query", matched_phrase))

                    if media_url:
                        used_media_urls.append(media_url)

                    g_item = MotionGraphicItem(
                        id=f"split_{int(c_start * 100)}_{len(generated_graphics)}",
                        start=round(c_start, 2),
                        end=c_end,
                        template_id="split_screen_vertical",
                        title=f"50/50 Split ({matched_phrase[:25].title()})",
                        parameters={
                            "broll_title": broll_title,
                            "speaker_label": "Speaker",
                            "source_citation": citation,
                            "split_ratio": 0.5,
                            "divider_color": "#FFFFFF",
                            "media_url": media_url,
                            "media_type": media_type
                        },
                        pos_x=0.5,
                        pos_y=0.5,
                        scale=1.0,
                        media_url=media_url,
                        media_type=media_type
                    )
                    generated_graphics.append(g_item)
                    last_cue_end = g_item.end

                    ts_reason = (
                        f"Placed at {g_item.start:.2f}s anchored to vocal onset of semantic phrase '{matched_phrase}'. "
                        f"Evaluating full sentence context ('{sent_text[:60]}...') filtered conversational filler and revealed visual at thesis assertion."
                    )
                    img_reason = (
                        f"Sentence context identified '{matched_pattern['category']}'. "
                        f"Queried '{primary_query}' and retrieved distinct licensed imagery depicting {matched_pattern['topic_explanation']}."
                    )
                    layout_reason = (
                        "50/50 Vertical Split dedicates top 50% to high-authority visual proof with citation, "
                        "preserving speaker in bottom 50% for human engagement."
                    )
                    pacing_reason = (
                        f"Maintains > 1.5s separation after prior visual event. "
                        f"Allocated a {g_item.end - g_item.start:.1f}s display window for dual-task processing of visual proof and subtitles."
                    )

                    cue_entry = {
                        "type": "split_screen_vertical",
                        "term": matched_phrase,
                        "caption_id": sent["caption_ids"][0],
                        "start": g_item.start,
                        "end": g_item.end,
                        "graphic_id": g_item.id,
                        "category": matched_pattern["category"],
                        "reasoning": {
                            "cue_index": len(generated_graphics),
                            "graphic_id": g_item.id,
                            "template_id": "split_screen_vertical",
                            "template_name": matched_pattern["template_name"],
                            "timestamp_start": g_item.start,
                            "timestamp_end": g_item.end,
                            "timestamp_formatted": f"{int(g_item.start // 60):02d}:{g_item.start % 60:05.2f}",
                            "duration_sec": round(g_item.end - g_item.start, 2),
                            "spoken_trigger_phrase": sent_text,
                            "trigger_term": matched_phrase,
                            "cue_category": matched_pattern["category"],
                            "timestamp_logic": ts_reason,
                            "image_logic": img_reason,
                            "layout_logic": layout_reason,
                            "pacing_logic": pacing_reason,
                            "search_query": primary_query,
                            "source_provider": citation,
                            "media_url": media_url,
                            "media_thumb": media_thumb,
                            "media_type": media_type
                        }
                    }
                    detected_cues.append(cue_entry)
                    reasoning_log.append(cue_entry["reasoning"])

        return detected_cues, generated_graphics, reasoning_log

transcription_service = TranscriptionService()
