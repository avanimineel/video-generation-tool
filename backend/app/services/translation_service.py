import re
import os
from typing import List, Dict, Any
from app.core.models import CaptionItem, WordTiming
from app.core.config import settings

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

    def translate_captions_list(self, captions: List[CaptionItem], checkpoint_dir=None) -> List[CaptionItem]:
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
        has_devanagari = any(self.is_devanagari(t) for t in texts_to_translate)

        translated_texts = []
        from app.core.config import get_provider_key
        if get_provider_key("GEMINI_API_KEY"):
            # Batch translate in chunks of 20 for speed and context
            for i in range(0, len(texts_to_translate), 20):
                chunk = texts_to_translate[i:i+20]
                if checkpoint_dir:
                    import hashlib, json
                    from pathlib import Path
                    digest = hashlib.sha256(json.dumps({'version': 1, 'source': chunk}, ensure_ascii=False).encode()).hexdigest()
                    translated_chunk = self.translate_with_gemini(chunk, Path(checkpoint_dir) / (digest + '.json'))
                else:
                    translated_chunk = self.translate_with_gemini(chunk)
                if len(translated_chunk) == len(chunk):
                    translated_texts.extend(translated_chunk)
                else:
                    raise ValueError('Translation returned mismatched IDs; no partial dictionary translation was inserted.')
        else:
            raise ValueError("Translation provider is unavailable; original-language captions retained. No guessed translation was inserted.")

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
