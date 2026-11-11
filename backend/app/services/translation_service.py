import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Sequence
from app.core.models import CaptionItem, WordTiming
from app.core.config import settings

try:
    from app.core.logging_setup import get_logger
    logger = get_logger(__name__)
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger(__name__)


def _log(event: str, **fields: Any) -> None:
    try:
        logger.info(event, event=event, **fields)
    except TypeError:
        logger.info("%s %s", event, fields)


class TranslationService:
    # Context-aware medical and conversational phrase dictionary
    EXPANDED_DICTIONARY = {
        "फेफड़े का कैंसर": "lung cancer",
        "लंग कैंसर": "lung cancer",
        "कैंसर": "cancer",
        "टीबी": "TB",
        "इन्फेक्शन": "infection",
        "इन्फेक्शन की दवाई": "antibiotics for infection",
        "कीमोथेरेपी": "chemotherapy",
        "रेडिएशन": "radiation therapy",
        "सर्जरी": "surgery",
        "ऑपरेशन": "operation",
        "स्टेज 1": "Stage 1",
        "स्टेज 2": "Stage 2",
        "स्टेज 3": "Stage 3",
        "स्टेज 4": "Stage 4",
        "खांसी": "cough",
        "बलगम": "sputum",
        "खून": "blood",
        "सांस लेने में दिक्कत": "difficulty breathing",
        "सीने में दर्द": "chest pain",
        "कमजोरी": "fatigue",
        "वजन कम होना": "weight loss",
        "ट्यूमर": "tumor",
        "गांठ": "lump",
        "बायोप्सी": "biopsy",
        "सीटी स्कैन": "CT scan",
        "एक्स रे": "X-ray",
        "आधे लोग": "half of the patients",
        "दवाई चालू": "started medication",
        "खत्म हो जाते हैं": "pass away",
        "इलाज": "treatment",
        "बचाव": "prevention",
        "मरीज़": "patient",
        "डॉक्टर": "doctor",
        "अस्पताल": "hospital",
        "जांच": "tests",
        "रिपोर्ट": "report",
        "दवा": "medicine",
        "दर्द": "pain"
    }

    def is_devanagari(self, text: str) -> bool:
        return bool(re.search(r'[\u0900-\u097F]', text))

    def translate_with_gemini(self, text_list: List[str], checkpoint=None) -> List[str]:
        from app.services.editorial_planner import gemini_json
        import json
        if not text_list:
            return []
        schema = {"type": "object", "properties": {"lines": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "integer"}, "text": {"type": "string"}},
            "required": ["id", "text"]}}}, "required": ["lines"]}
        source = [{"id": i, "text": text} for i, text in enumerate(text_list)]
        accepted = {}
        if checkpoint and checkpoint.exists():
            try:
                cached = json.loads(checkpoint.read_text())
                if cached.get('source') == source:
                    accepted = {int(i): t for i, t in cached.get('accepted', {}).items()
                                if str(i).isdigit() and 0 <= int(i) < len(source)
                                and isinstance(t, str) and any(c.isalnum() for c in t)
                                and not self.is_devanagari(t)}
            except (ValueError, OSError, TypeError):
                pass
        for attempt in range(3):
            pending = [row for row in source if row['id'] not in accepted]
            if not pending:
                break
            prompt = ("Translate Hindi, Hinglish and English into faithful English subtitles. "
                      "Keep all facts, names, numbers and negation. Do not invent or summarize. "
                      "Each ID is a separate subtitle fragment: return exactly one nonempty English text per requested ID, "
                      "even when adjacent fragments form a sentence. Never merge, renumber or omit IDs. "
                      "Use the full context for meaning, but return only REQUESTED IDs. "
                      "Return {lines:[{id:integer,text:string}]}. FULL CONTEXT: " + json.dumps(source,ensure_ascii=False)
                      + " REQUESTED: " + json.dumps(pending,ensure_ascii=False))
            data = gemini_json(prompt, schema, max_requests=2)
            requested = {row['id'] for row in pending}
            candidates = {}
            duplicates = set()
            for row in data.get('lines', []):
                if not isinstance(row, dict):
                    continue
                ident, text = row.get('id'), row.get('text')
                if type(ident) is not int or ident not in requested:
                    continue
                if ident in candidates:
                    duplicates.add(ident)
                if isinstance(text, str) and any(c.isalnum() for c in text) and not self.is_devanagari(text):
                    candidates[ident] = text.strip()
            accepted.update({i:t for i,t in candidates.items() if i not in duplicates})
            if checkpoint:
                from app.services.editorial_planner import write_json
                write_json(checkpoint, {'source': source, 'accepted': accepted})
        missing = [i+1 for i in range(len(text_list)) if i not in accepted]
        if missing:
            raise ValueError('Translation incomplete after retries; subtitle lines ' + ', '.join(map(str,missing)) + ' need review. Original speech is saved.')
        return [accepted[i] for i in range(len(text_list))]

    def sanitize_english_subtitles(self, text: str) -> str:
        # A phonetic guess is not a correction. Content changes need source audio
        # or an explicit edit; global substitutions corrupt unrelated videos.
        return text

    def translate_caption_rule_based(self, raw_text: str) -> str:
        clean = re.sub(r'^\[EN\]\s*', '', raw_text, flags=re.IGNORECASE).strip()
        
        # If already predominantly Latin/English, return sanitized text
        if not self.is_devanagari(clean):
            return self.sanitize_english_subtitles(clean)

        # Replace known phrases in sentence context
        translated = clean
        for hi, en in self.EXPANDED_DICTIONARY.items():
            translated = translated.replace(hi, en)

        return self.sanitize_english_subtitles(translated)

    def translation_backend_preference(self) -> str:
        value = (os.getenv('TRANSLATION_BACKEND') or 'auto').strip().lower()
        return value if value in ('auto', 'local', 'gemini') else 'auto'

    def translate_with_local(
        self,
        text_list: List[str],
        checkpoint=None,
        *,
        translate_fn: Optional[Callable[[Sequence[str]], List[str]]] = None,
    ) -> List[str]:
        """Local NLLB path with the same checkpoint resume semantics as Gemini."""
        import json
        if not text_list:
            return []
        source = [{"id": i, "text": text} for i, text in enumerate(text_list)]
        accepted: Dict[int, str] = {}
        if checkpoint and Path(checkpoint).exists():
            try:
                cached = json.loads(Path(checkpoint).read_text())
                if cached.get('source') == source and cached.get('backend') in (None, 'local'):
                    accepted = {int(i): t for i, t in cached.get('accepted', {}).items()
                                if str(i).isdigit() and 0 <= int(i) < len(source)
                                and isinstance(t, str) and any(c.isalnum() for c in t)
                                and not self.is_devanagari(t)}
            except (ValueError, OSError, TypeError):
                pass

        pending_ids = [i for i in range(len(text_list)) if i not in accepted]
        if pending_ids:
            pending_texts = [text_list[i] for i in pending_ids]
            if translate_fn is None:
                from app.services.local_translation import translate_lines_local
                translated = translate_lines_local(pending_texts)
            else:
                translated = list(translate_fn(pending_texts))
            if len(translated) != len(pending_texts):
                raise ValueError('Local translation returned mismatched line count; original speech is saved.')
            for idx, text in zip(pending_ids, translated):
                if not isinstance(text, str) or not any(c.isalnum() for c in text) or self.is_devanagari(text):
                    raise ValueError(
                        f'Local translation produced unusable English for subtitle line {idx + 1}; '
                        'original speech is saved.'
                    )
                accepted[idx] = text.strip()
            if checkpoint:
                from app.services.editorial_planner import write_json
                write_json(Path(checkpoint), {'source': source, 'accepted': accepted, 'backend': 'local'})

        missing = [i + 1 for i in range(len(text_list)) if i not in accepted]
        if missing:
            raise ValueError(
                'Local translation incomplete; subtitle lines '
                + ', '.join(map(str, missing))
                + ' need review. Original speech is saved.'
            )
        return [accepted[i] for i in range(len(text_list))]

    def _translate_chunk(
        self,
        chunk: List[str],
        checkpoint_path: Optional[Path] = None,
        *,
        local_fn: Optional[Callable[[Sequence[str]], List[str]]] = None,
    ) -> List[str]:
        """Translate one batch honoring TRANSLATION_BACKEND=auto|local|gemini."""
        from app.core.config import get_provider_key

        preference = self.translation_backend_preference()
        has_gemini = bool(get_provider_key("GEMINI_API_KEY"))
        errors: List[str] = []

        def try_local():
            result = self.translate_with_local(chunk, checkpoint_path, translate_fn=local_fn)
            _log('translation_backend_selected', backend='local', preference=preference, lines=len(chunk))
            return result

        def try_gemini():
            result = self.translate_with_gemini(chunk, checkpoint_path)
            _log('translation_backend_selected', backend='gemini', preference=preference, lines=len(chunk))
            return result

        if preference == 'local':
            return try_local()
        if preference == 'gemini':
            if not has_gemini:
                raise ValueError(
                    'TRANSLATION_BACKEND=gemini but no usable GEMINI_API_KEY is configured; '
                    'original-language captions retained.'
                )
            return try_gemini()

        # auto: local first, Gemini fallback when key present
        try:
            return try_local()
        except Exception as local_exc:
            errors.append(f'local:{type(local_exc).__name__}:{local_exc}')
            if not has_gemini:
                raise ValueError(
                    'Local translation failed and no Gemini key is configured; '
                    'original-language captions retained. No guessed translation was inserted. '
                    f'({local_exc})'
                ) from local_exc
            _log(
                'translation_backend_fallback',
                backend='gemini',
                preference='auto',
                fallback_reason='local_failed',
                local_error=str(local_exc)[:300],
            )
            try:
                return try_gemini()
            except Exception as gemini_exc:
                raise ValueError(
                    'Local translation failed and Gemini fallback also failed; '
                    'original-language captions retained. '
                    f'local=({local_exc}); gemini=({gemini_exc})'
                ) from gemini_exc

    def translate_captions_list(
        self,
        captions: List[CaptionItem],
        checkpoint_dir=None,
        *,
        local_fn: Optional[Callable[[Sequence[str]], List[str]]] = None,
    ) -> List[CaptionItem]:
        if not captions:
            return captions

        from app.services.transcript_quality import transcript_issues
        issues = transcript_issues(captions)
        if issues:
            raise ValueError('Source speech needs retranscription before translation: ' + '; '.join(issues[:5]))

        # 1. Clean legacy prefixes
        for cap in captions:
            cap.text = re.sub(r'^\[EN\]\s*', '', cap.text, flags=re.IGNORECASE).strip()

        # 2. Check if translation is needed
        texts_to_translate = [c.text for c in captions]

        translated_texts: List[str] = []
        for i in range(0, len(texts_to_translate), 20):
            chunk = texts_to_translate[i:i + 20]
            checkpoint_path = None
            if checkpoint_dir:
                import hashlib, json
                digest = hashlib.sha256(
                    json.dumps({'version': 2, 'source': chunk}, ensure_ascii=False).encode()
                ).hexdigest()
                checkpoint_path = Path(checkpoint_dir) / (digest + '.json')
            translated_chunk = self._translate_chunk(chunk, checkpoint_path, local_fn=local_fn)
            if len(translated_chunk) != len(chunk):
                raise ValueError('Translation returned mismatched IDs; no partial dictionary translation was inserted.')
            translated_texts.extend(translated_chunk)

        for idx, cap in enumerate(captions):
            t_text = translated_texts[idx] if idx < len(translated_texts) else cap.text
            cap.translated_text = t_text

            if t_text == cap.text:
                continue

            # Proportional word timing allocation based on character lengths
            words = t_text.split()
            if words:
                dur = max(0.4, cap.end - cap.start)
                total_chars = sum(len(w) for w in words)
                total_weight = max(1, total_chars + len(words) * 2)

                new_words = []
                cur_t = cap.start
                for w in words:
                    w_weight = len(w) + 2
                    w_dur = round((w_weight / total_weight) * dur, 2)
                    w_start = round(cur_t, 2)
                    w_end = round(min(cap.end, cur_t + w_dur), 2)
                    try:
                        from app.services.transcription_service import transcription_service
                        kw_info = transcription_service.analyze_word_emphasis(w)
                    except Exception:
                        kw_info = {'is_keyword': False}
                    new_words.append(WordTiming(
                        word=w,
                        start=w_start,
                        end=w_end,
                        highlight=False,
                        is_keyword=kw_info.get('is_keyword', False),
                        keyword_category=kw_info.get('keyword_category'),
                        keyword_color=kw_info.get('keyword_color'),
                        keyword_font=kw_info.get('keyword_font')
                    ))
                    cur_t = w_end
                cap.words = new_words

        return captions

translation_service = TranslationService()
