import re
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Sequence
from app.core.models import CaptionItem, WordTiming
from app.core.config import settings

try:
    from app.core.logging_setup import get_logger
    logger = get_logger(__name__)
except Exception:  # pragma: no cover
    logger = logging.getLogger(__name__)


def _log(level: int, event: str, **fields: Any) -> None:
    """Structured-friendly log; falls back to plain message if kwargs unsupported."""
    try:
        logger.log(level, event, event=event, **fields)
    except TypeError:
        logger.log(level, "%s %s", event, fields)


def _log_info(event: str, **fields: Any) -> None:
    _log(logging.INFO, event, **fields)


def _log_debug(event: str, **fields: Any) -> None:
    _log(logging.DEBUG, event, **fields)


def _log_exception(event: str, **fields: Any) -> None:
    import sys
    exc_info = sys.exc_info()
    try:
        logger.exception(event, event=event, **fields)
    except TypeError:
        # Stdlib logging rejects structured kwargs; keep the *original* exc_info.
        logger.error("%s %s", event, fields, exc_info=exc_info)


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
        _log_info(
            'translation_gemini_path_start',
            backend='gemini',
            line_count=len(text_list),
            checkpoint=str(checkpoint) if checkpoint else None,
        )
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
                    _log_debug(
                        'translation_gemini_checkpoint_resume',
                        accepted_count=len(accepted),
                        total=len(source),
                    )
            except (ValueError, OSError, TypeError) as exc:
                _log_debug(
                    'translation_gemini_checkpoint_unusable',
                    error=str(exc)[:200],
                )
        try:
            for attempt in range(3):
                pending = [row for row in source if row['id'] not in accepted]
                if not pending:
                    break
                _log_debug(
                    'translation_gemini_attempt',
                    attempt=attempt + 1,
                    pending_count=len(pending),
                    accepted_count=len(accepted),
                )
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
            _log_info(
                'translation_gemini_path_end',
                backend='gemini',
                line_count=len(text_list),
                accepted_count=len(accepted),
            )
            return [accepted[i] for i in range(len(text_list))]
        except Exception:
            _log_exception(
                'translation_gemini_path_failed',
                backend='gemini',
                line_count=len(text_list),
                accepted_count=len(accepted),
            )
            raise

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
        model_name = None
        try:
            from app.services.local_translation import default_model_name
            model_name = default_model_name()
        except Exception:
            model_name = os.getenv('LOCAL_TRANSLATION_MODEL') or 'facebook/nllb-200-distilled-600M'
        _log_info(
            'translation_local_path_start',
            backend='local',
            model=model_name,
            line_count=len(text_list),
            checkpoint=str(checkpoint) if checkpoint else None,
            injected_fn=translate_fn is not None,
        )
        source = [{"id": i, "text": text} for i, text in enumerate(text_list)]
        accepted: Dict[int, str] = {}
        try:
            if checkpoint and Path(checkpoint).exists():
                try:
                    cached = json.loads(Path(checkpoint).read_text())
                    if cached.get('source') == source and cached.get('backend') in (None, 'local'):
                        accepted = {int(i): t for i, t in cached.get('accepted', {}).items()
                                    if str(i).isdigit() and 0 <= int(i) < len(source)
                                    and isinstance(t, str) and any(c.isalnum() for c in t)
                                    and not self.is_devanagari(t)}
                        _log_debug(
                            'translation_local_checkpoint_resume',
                            accepted_count=len(accepted),
                            total=len(source),
                        )
                except (ValueError, OSError, TypeError) as exc:
                    _log_debug(
                        'translation_local_checkpoint_unusable',
                        error=str(exc)[:200],
                    )

            pending_ids = [i for i in range(len(text_list)) if i not in accepted]
            if pending_ids:
                pending_texts = [text_list[i] for i in pending_ids]
                _log_debug(
                    'translation_local_pending',
                    pending_count=len(pending_ids),
                    accepted_count=len(accepted),
                )
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
            _log_info(
                'translation_local_path_end',
                backend='local',
                model=model_name,
                line_count=len(text_list),
                accepted_count=len(accepted),
            )
            return [accepted[i] for i in range(len(text_list))]
        except Exception:
            _log_exception(
                'translation_local_path_failed',
                backend='local',
                model=model_name,
                line_count=len(text_list),
                accepted_count=len(accepted),
            )
            raise

    def _translate_chunk(
        self,
        chunk: List[str],
        checkpoint_path: Optional[Path] = None,
        *,
        local_fn: Optional[Callable[[Sequence[str]], List[str]]] = None,
        chunk_index: int = 0,
        chunk_count: int = 1,
    ) -> List[str]:
        """Translate one batch honoring TRANSLATION_BACKEND=auto|local|gemini."""
        from app.core.config import get_provider_key

        preference = self.translation_backend_preference()
        has_gemini = bool(get_provider_key("GEMINI_API_KEY"))
        model_name = os.getenv('LOCAL_TRANSLATION_MODEL') or 'facebook/nllb-200-distilled-600M'
        _log_info(
            'translation_chunk_start',
            preference=preference,
            gemini_key_present=has_gemini,
            model=model_name,
            chunk_index=chunk_index,
            chunk_count=chunk_count,
            lines=len(chunk),
            checkpoint=str(checkpoint_path) if checkpoint_path else None,
        )

        def try_local():
            _log_debug(
                'translation_trying_local',
                preference=preference,
                chunk_index=chunk_index,
                chunk_count=chunk_count,
                lines=len(chunk),
                model=model_name,
            )
            result = self.translate_with_local(chunk, checkpoint_path, translate_fn=local_fn)
            _log_info(
                'translation_backend_selected',
                backend='local',
                preference=preference,
                model=model_name,
                gemini_key_present=has_gemini,
                chunk_index=chunk_index,
                chunk_count=chunk_count,
                lines=len(chunk),
            )
            return result

        def try_gemini():
            _log_debug(
                'translation_trying_gemini',
                preference=preference,
                chunk_index=chunk_index,
                chunk_count=chunk_count,
                lines=len(chunk),
                gemini_key_present=has_gemini,
            )
            result = self.translate_with_gemini(chunk, checkpoint_path)
            _log_info(
                'translation_backend_selected',
                backend='gemini',
                preference=preference,
                model=model_name,
                gemini_key_present=has_gemini,
                chunk_index=chunk_index,
                chunk_count=chunk_count,
                lines=len(chunk),
            )
            return result

        try:
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
                _log_exception(
                    'translation_local_failed_in_auto',
                    preference='auto',
                    gemini_key_present=has_gemini,
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    local_error=str(local_exc)[:300],
                )
                if not has_gemini:
                    raise ValueError(
                        'Local translation failed and no Gemini key is configured; '
                        'original-language captions retained. No guessed translation was inserted. '
                        f'({local_exc})'
                    ) from local_exc
                _log_info(
                    'translation_backend_fallback',
                    backend='gemini',
                    preference='auto',
                    fallback_reason='local_failed',
                    gemini_key_present=True,
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    local_error=str(local_exc)[:300],
                )
                try:
                    return try_gemini()
                except Exception as gemini_exc:
                    _log_exception(
                        'translation_gemini_fallback_failed',
                        preference='auto',
                        chunk_index=chunk_index,
                        chunk_count=chunk_count,
                        gemini_error=str(gemini_exc)[:300],
                    )
                    raise ValueError(
                        'Local translation failed and Gemini fallback also failed; '
                        'original-language captions retained. '
                        f'local=({local_exc}); gemini=({gemini_exc})'
                    ) from gemini_exc
        finally:
            _log_debug(
                'translation_chunk_end',
                preference=preference,
                chunk_index=chunk_index,
                chunk_count=chunk_count,
                lines=len(chunk),
            )

    def translate_captions_list(
        self,
        captions: List[CaptionItem],
        checkpoint_dir=None,
        *,
        local_fn: Optional[Callable[[Sequence[str]], List[str]]] = None,
    ) -> List[CaptionItem]:
        if not captions:
            return captions

        from app.core.config import get_provider_key
        preference = self.translation_backend_preference()
        has_gemini = bool(get_provider_key("GEMINI_API_KEY"))
        model_name = os.getenv('LOCAL_TRANSLATION_MODEL') or 'facebook/nllb-200-distilled-600M'
        _log_info(
            'translation_captions_start',
            preference=preference,
            gemini_key_present=has_gemini,
            model=model_name,
            caption_count=len(captions),
        )

        from app.services.transcript_quality import transcript_issues
        issues = transcript_issues(captions)
        if issues:
            _log_info(
                'translation_captions_blocked_quality',
                preference=preference,
                issue_count=len(issues),
                issues=issues[:5],
            )
            raise ValueError('Source speech needs retranscription before translation: ' + '; '.join(issues[:5]))

        # 1. Clean legacy prefixes
        for cap in captions:
            cap.text = re.sub(r'^\[EN\]\s*', '', cap.text, flags=re.IGNORECASE).strip()

        # 2. Check if translation is needed
        texts_to_translate = [c.text for c in captions]
        chunk_size = 20
        chunk_count = (len(texts_to_translate) + chunk_size - 1) // chunk_size
        _log_info(
            'translation_captions_chunking',
            caption_count=len(texts_to_translate),
            chunk_size=chunk_size,
            chunk_count=chunk_count,
            preference=preference,
            gemini_key_present=has_gemini,
            model=model_name,
        )

        translated_texts: List[str] = []
        try:
            for chunk_index, i in enumerate(range(0, len(texts_to_translate), chunk_size)):
                chunk = texts_to_translate[i:i + chunk_size]
                checkpoint_path = None
                if checkpoint_dir:
                    import hashlib, json
                    digest = hashlib.sha256(
                        json.dumps({'version': 2, 'source': chunk}, ensure_ascii=False).encode()
                    ).hexdigest()
                    checkpoint_path = Path(checkpoint_dir) / (digest + '.json')
                _log_debug(
                    'translation_captions_chunk',
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    lines=len(chunk),
                    offset=i,
                )
                translated_chunk = self._translate_chunk(
                    chunk,
                    checkpoint_path,
                    local_fn=local_fn,
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                )
                if len(translated_chunk) != len(chunk):
                    raise ValueError('Translation returned mismatched IDs; no partial dictionary translation was inserted.')
                translated_texts.extend(translated_chunk)
        except Exception:
            _log_exception(
                'translation_captions_failed',
                preference=preference,
                gemini_key_present=has_gemini,
                model=model_name,
                caption_count=len(captions),
                translated_so_far=len(translated_texts),
            )
            raise

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

        _log_info(
            'translation_captions_end',
            preference=preference,
            gemini_key_present=has_gemini,
            model=model_name,
            caption_count=len(captions),
            chunk_count=chunk_count,
        )
        return captions

translation_service = TranslationService()
