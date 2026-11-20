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


class RunningInferences:
    """Facts already decided for this video, used the next time a word is ambiguous."""

    def __init__(self, domain: Optional[str] = None):
        self.domain = (domain or "general").strip().lower()
        self.tb = False
        self.lung = False
        self.medicine = False

    def snapshot(self) -> "RunningInferences":
        copied = RunningInferences(self.domain)
        copied.tb = self.tb
        copied.lung = self.lung
        copied.medicine = self.medicine
        return copied

    def note(self, source: str) -> None:
        text = source or ""
        if "टीबी" in text or re.search(r"(?<![A-Za-z])TB(?![A-Za-z])", text):
            self.tb = True
        if "लंग" in text or "फेफड़" in text or "कैंसर" in text:
            self.lung = True
        if re.search(r"दवाई|दवा", text):
            self.medicine = True

    def describe(self) -> str:
        parts = []
        if self.tb:
            parts.append("an earlier line established TB")
        if self.lung:
            parts.append("an earlier line established lung disease")
        if not parts:
            return ""
        if self.domain == "medical":
            parts.append("the project domain is medical")
        return "; ".join(parts)


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

    _ROMAN = {
        "अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ए": "e", "ऐ": "ai",
        "ओ": "o", "औ": "au", "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "च": "ch", "छ": "chh",
        "ज": "j", "झ": "jh", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "त": "t", "थ": "th",
        "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
        "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
        "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai", "ो": "o",
        "ौ": "au", "्": "", "ं": "n", "ँ": "n", "ः": "", "़": "",
    }

    def _romanize(self, word: str) -> str:
        return "".join(self._ROMAN.get(ch, "") for ch in word)

    def _close_spelling(self, hindi_word: str, english_word: str) -> bool:
        spelled = self._romanize(hindi_word)
        heard = re.sub(r"[^a-z]", "", english_word.casefold())
        if len(spelled) < 3 or len(heard) < 3:
            return False
        if spelled in heard or heard in spelled:
            return True
        if abs(len(spelled) - len(heard)) > 1:
            return False
        previous = list(range(len(heard) + 1))
        for i, left in enumerate(spelled, 1):
            current = [i]
            for j, right in enumerate(heard, 1):
                current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (left != right)))
            previous = current
        return previous[-1] <= 1

    def is_transliteration_fragment(self, hindi: str, english: str) -> bool:
        """A spelling of the Hindi, not an English sentence. Do not use it."""
        hindi_words = re.findall(r"[\u0900-\u097F]+", hindi or "")
        english_words = (english or "").split()
        if len(hindi_words) < 4 or not english_words:
            return False
        spelled = [
            word for word in english_words
            if any(self._close_spelling(hindi_word, word) for hindi_word in hindi_words)
        ]
        long_spellings = [
            word for word in english_words
            if any(
                self._close_spelling(hindi_word, word) and len(self._romanize(hindi_word)) >= 4
                for hindi_word in hindi_words
            )
        ]
        opens_with_spelling = self._close_spelling(hindi_words[0], english_words[0])
        mostly_spelled = len(spelled) * 2 >= len(english_words)
        too_short = opens_with_spelling and len(english_words) * 2 < len(hindi_words)
        # "The Adelog considered" still spells a Hindi word. A real sentence does not.
        spelling_led = bool(long_spellings) and len(english_words) <= len(long_spellings) + 2
        return mostly_spelled or too_short or spelling_led

    def tv_means_tb(self, text: str, prior: Optional[RunningInferences] = None) -> bool:
        """Choose TB or television. Same-line words decide first; earlier inferences break a tie."""
        raw = text or ""
        if re.search(r"टीवी\s*पर|टीवी\s*देख|टीवी\s*शो", raw):
            return False
        if re.search(r"\b(on|watch|watching)\s+tv\b|\btv\s+(show|screen)\b", raw, re.IGNORECASE):
            return False
        has_token = bool(re.search(r"टीवी|टीवे|तीवी|तीबी|तीवे", raw)) or bool(
            re.search(r"\btv\b|television", raw, re.IGNORECASE)
        )
        if not has_token:
            return False
        if re.search(r"दवाई|दवा|मान|जैसा|तरह", raw):
            return True
        if prior and prior.tb:
            return True
        if prior and prior.domain == "medical" and prior.lung:
            return True
        return False

    def normalize_medical_asr(
        self,
        text: str,
        prior: Optional[RunningInferences] = None,
        domain: Optional[str] = None,
    ) -> str:
        """Rewrite common mishearings before the line is translated. No person has to mark them."""
        normalized = text or ""
        normalized = re.sub(r"अदेलोग", "आधे लोग", normalized)
        normalized = re.sub(r"(?:अदिलों|आदिय|आदिलो)\s*लोग", "आधे लोग", normalized)
        normalized = re.sub(r"कांसर|कान्सर|कानसर", "कैंसर", normalized)
        normalized = re.sub(r"लंकान्शर", "लंग कैंसर", normalized)
        normalized = re.sub(r"इन्फेक्षन|इन्फेक्शन", "इन्फेक्शन", normalized)
        normalized = re.sub(r"उसको\s*लंग्+", "उसको लंग", normalized)
        if self.tv_means_tb(normalized, prior or RunningInferences(domain)):
            normalized = re.sub(
                r"(?<![\u0900-\u097F])(?:टीवी|टीवे|तीवी|तीबी|तीवे)(?![\u0900-\u097F])",
                "टीबी",
                normalized,
            )
        return normalized

    def _clauses(self, text: str) -> List[str]:
        parts = [part.strip() for part in re.split(r"[,，]", text or "") if part.strip()]
        return parts or [text or ""]

    def _clause_facts(self, clause: str) -> Dict[str, bool]:
        has_tb = "टीबी" in clause
        has_medicine = bool(re.search(r"दवाई|दवा", clause))
        medicine_not_started = bool(re.search(r"(?:कोई\s+)?(?:दवाई|दवा)\s+नहीं", clause))
        has_infection = "इन्फेक्शन" in clause
        infection_denied = bool(re.search(r"इन्फेक्शन\s+नहीं", clause)) and not medicine_not_started
        return {
            "half": "आधे लोग" in clause,
            "tb": has_tb,
            "tb_medicine": has_tb and has_medicine and not medicine_not_started,
            "medicine_not_started": medicine_not_started,
            "lung_cancer": "लंग कैंसर" in clause or "फेफड़े का कैंसर" in clause,
            "cancer": "कैंसर" in clause,
            "cough_in_source": "खांसी" in clause,
            "not_infection": infection_denied,
            "lung_infection": has_infection and "लंग" in clause and "कैंसर" not in clause and not infection_denied,
            "treat_as": bool(re.search(r"मान|जैसा|तरह", clause)),
        }

    def _medical_facts(
        self,
        source: str,
        prior: Optional[RunningInferences] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, bool]:
        text = self.normalize_medical_asr(source, prior=prior, domain=domain)
        merged = {
            "half": False,
            "tb": False,
            "tb_medicine": False,
            "medicine_not_started": False,
            "lung_cancer": False,
            "cancer": False,
            "cough_in_source": False,
            "not_infection": False,
            "lung_infection": False,
            "treat_as": False,
        }
        for clause in self._clauses(text):
            for key, value in self._clause_facts(clause).items():
                merged[key] = merged[key] or value
        return merged

    def medical_english_is_unusable(
        self,
        source: str,
        english: str,
        prior: Optional[RunningInferences] = None,
        domain: Optional[str] = None,
    ) -> bool:
        """Fluent English that missed the medical meaning. Do not show it."""
        if self.is_transliteration_fragment(source, english):
            return True
        facts = self._medical_facts(source, prior=prior, domain=domain)
        if not any(facts.values()) and not self.tv_means_tb(source, prior or RunningInferences(domain)):
            return False
        rendered = (english or "").casefold()
        decided_tb = self.tv_means_tb(source, prior or RunningInferences(domain))
        if decided_tb and not re.search(r"\btb\b", rendered):
            return True
        if (facts["tb"] or facts["tb_medicine"] or decided_tb) and re.search(r"\btv\b|television", rendered):
            return True
        if facts["tb_medicine"] and (
            not re.search(r"\btb\b", rendered)
            or re.search(r"\b(thief|thieves|theft|television)\b", rendered)
        ):
            return True
        if facts["tb"] and re.search(r"\b(thief|thieves|theft)\b", rendered):
            return True
        if (facts["lung_cancer"] or facts["cancer"]) and re.search(r"\bcough", rendered) and "cancer" not in rendered:
            return True
        if facts["lung_cancer"] and "cancer" not in rendered:
            return True
        if facts["half"] and re.search(r"\badelog\b", rendered):
            return True
        if facts["lung_infection"] and facts["medicine_not_started"] and "infection" not in rendered:
            return True
        return False

    def _repair_clause(self, facts: Dict[str, bool], tb_name: str) -> str:
        sentences = []
        if facts["half"] and facts["tb_medicine"]:
            sentences.append(f"For half the people, it is taken as {tb_name} and TB medicine is started.")
        elif facts["tb_medicine"]:
            sentences.append("TB medicine is started.")
        elif facts["tb"] and (facts["treat_as"] or tb_name == "TB-like"):
            lead = "For half the people, " if facts["half"] else ""
            sentences.append(f"{lead}it is taken as {tb_name}." if lead else f"It is taken as {tb_name}.")
        if facts["lung_infection"] and facts["medicine_not_started"]:
            if facts["half"]:
                sentences.append("For half the people, it is taken as a lung infection and no medicine is started.")
            else:
                sentences.append("It is taken as a lung infection and no medicine is started.")
        elif facts["not_infection"]:
            sentences.append(
                "It is not treated as a lung infection." if facts["lung_infection"] else "It is not treated as an infection."
            )
        if facts["lung_cancer"]:
            sentences.append("The disease is lung cancer.")
        elif facts["cancer"] and not facts["tb_medicine"]:
            sentences.append("The disease is cancer.")
        return " ".join(sentences)

    def repair_medical_english(
        self,
        source: str,
        prior: Optional[RunningInferences] = None,
        domain: Optional[str] = None,
    ) -> str:
        """English built from the medical words in the spoken line, for every line that matches."""
        decided = self.tv_means_tb(source, prior or RunningInferences(domain))
        text = self.normalize_medical_asr(source, prior=prior, domain=domain)
        tb_name = "TB-like" if decided else "TB"
        sentences = [
            self._repair_clause(self._clause_facts(clause), tb_name)
            for clause in self._clauses(text)
        ]
        return " ".join(sentence for sentence in sentences if sentence)

    def english_is_display_ready(self, caption: CaptionItem) -> bool:
        """A stored English line can stay only when it still matches the spoken medical meaning."""
        english = caption.translated_text or ""
        if not english.strip() or self.is_devanagari(english):
            return False
        if self.is_transliteration_fragment(caption.text, english):
            return False
        if self.medical_english_is_unusable(caption.text, english):
            return False
        return True

    def correct_stored_captions(self, captions: List[CaptionItem], domain: Optional[str] = None) -> bool:
        before = [caption.translated_text for caption in captions]
        self.correct_medical_lines(captions, domain=domain)
        return [caption.translated_text for caption in captions] != before

    def correct_medical_lines(
        self,
        captions: List[CaptionItem],
        domain: Optional[str] = None,
    ) -> List[CaptionItem]:
        state = RunningInferences(domain)
        for caption in sorted(captions, key=lambda item: (item.start, item.end)):
            prior = state.snapshot()
            english = caption.translated_text or ""
            if self.medical_english_is_unusable(caption.text, english, prior=prior, domain=domain):
                repaired = self.repair_medical_english(caption.text, prior=prior, domain=domain)
                if repaired and not self.medical_english_is_unusable(caption.text, repaired, prior=prior, domain=domain):
                    caption.translated_text = repaired
                    caption.editor_locked = False
            state.note(self.normalize_medical_asr(caption.text, prior=prior, domain=domain))
        return captions

    def join_hindi_clauses(self, captions: List[CaptionItem]) -> List[CaptionItem]:
        """One spoken Hindi line is translated once. Three-word slices are not separate sentences."""
        if not captions:
            return captions
        joined: List[CaptionItem] = []
        for caption in captions:
            text = (caption.text or "").strip()
            previous = joined[-1] if joined else None
            can_join = (
                previous is not None
                and self.is_devanagari(previous.text)
                and self.is_devanagari(text)
                and caption.start - previous.end <= 0.6
                and not previous.text.rstrip().endswith(("।", ".", "?", "!"))
                and len(previous.text.split()) < 18
            )
            if not can_join:
                item = caption.model_copy(deep=True)
                item.source_caption_ids = list(caption.source_caption_ids or [caption.id])
                joined.append(item)
                continue
            previous.text = f"{previous.text.rstrip()} {text}".strip()
            previous.end = max(previous.end, caption.end)
            previous.words = list(previous.words) + list(caption.words)
            previous.translated_text = None
            previous.source_caption_ids = list(previous.source_caption_ids) + [caption.id]
        return joined

    def _display_line(self, caption: CaptionItem) -> str:
        return (caption.translated_text or caption.text or "").strip()

    def _same_spoken_source(self, left: str, right: str) -> bool:
        a = " ".join((left or "").split())
        b = " ".join((right or "").split())
        if not a or not b:
            return False
        if a == b:
            return True
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        return len(shorter) >= 12 and shorter in longer

    def needs_new_translation(self, caption: CaptionItem) -> bool:
        """An edited line, or an English sentence already in hand, is not sent back to the translator."""
        english = (caption.translated_text or "").strip()
        source = (caption.text or "").strip()
        if caption.editor_locked and not self.medical_english_is_unusable(source, english):
            return False
        if english and not self.is_devanagari(english) and not self.is_devanagari(source):
            return False
        if not english or self.is_devanagari(english):
            return bool(self.is_devanagari(source) or not english)
        if self.medical_english_is_unusable(source, english):
            return True
        source_words = re.findall(r"[\u0900-\u097F]+", source)
        return bool(source_words) and len(english.split()) <= 4 and len(source_words) >= 6

    def restore_sentences(self, captions: List[CaptionItem]) -> List[CaptionItem]:
        """Join adjacent short captions into the spoken sentence they came from."""
        ordered = sorted(captions, key=lambda caption: (caption.start, caption.end))
        if len(ordered) < 2:
            return ordered
        groups: List[List[CaptionItem]] = []
        for caption in ordered:
            if not groups:
                groups.append([caption])
                continue
            previous = groups[-1][-1]
            previous_line = self._display_line(previous)
            gap = caption.start - previous.end
            words_so_far = sum(len(self._display_line(item).split()) for item in groups[-1])
            ended = previous_line.rstrip().endswith(("।", ".", "?", "!"))
            short_pair = len(previous_line.split()) <= 4 and len(self._display_line(caption).split()) <= 4
            if (
                gap <= 0.8
                and not ended
                and words_so_far < 22
                and (self._same_spoken_source(previous.text, caption.text) or short_pair)
            ):
                groups[-1].append(caption)
            else:
                groups.append([caption])
        return [self._merge_sentence(group) for group in groups]

    def _merge_sentence(self, group: List[CaptionItem]) -> CaptionItem:
        if len(group) == 1:
            return group[0]
        first = group[0].model_copy(deep=True)
        sources = [caption.text for caption in group]
        cleaned = [" ".join(text.split()) for text in sources if text and text.strip()]
        if cleaned:
            longest = max(cleaned, key=len)
            if all(part == longest or part in longest for part in cleaned):
                first.text = longest
            else:
                merged = cleaned[0]
                for part in cleaned[1:]:
                    if part and part not in merged:
                        merged = f"{merged} {part}".strip()
                first.text = merged
        english = " ".join(line for line in (self._display_line(caption) for caption in group) if line)
        first.translated_text = english or first.text
        first.end = max(caption.end for caption in group)
        first.words = [word for caption in group for word in caption.words]
        first.source_caption_ids = [caption.id for caption in group]
        first.editor_locked = any(caption.editor_locked for caption in group)
        return first

    def apply_saved_edits(self, captions: List[CaptionItem], mappings: List[Dict[str, Any]]) -> List[CaptionItem]:
        """Put the editor's wording back on the time range they corrected."""
        spans: List[Dict[str, Any]] = []
        for row in sorted(mappings or [], key=lambda item: float(item.get("start_sec") or 0)):
            spoken = " ".join(str(row.get("spoken_text") or "").split())
            if not spoken:
                continue
            start = float(row.get("start_sec") or 0)
            end = float(row.get("end_sec") or 0)
            if end <= start:
                continue
            source = " ".join(str(row.get("source_text") or "").split())
            if spans and start - float(spans[-1]["end"]) <= 0.45:
                spans[-1]["end"] = max(float(spans[-1]["end"]), end)
                spans[-1]["spoken"] = f"{spans[-1]['spoken']} {spoken}".strip()
                if len(source) > len(spans[-1]["source"]):
                    spans[-1]["source"] = source
            else:
                spans.append({"start": start, "end": end, "spoken": spoken, "source": source})
        spans = [
            span for span in spans
            if not self.medical_english_is_unusable(span["source"] or span["spoken"], span["spoken"])
        ]
        if not spans:
            return self.correct_medical_lines(captions)
        kept: List[CaptionItem] = []
        for caption in captions:
            duration = max(0.05, caption.end - caption.start)
            covered = False
            for span in spans:
                overlap = min(caption.end, span["end"]) - max(caption.start, span["start"])
                if overlap >= min(0.35, duration * 0.5):
                    covered = True
                    break
            if not covered:
                kept.append(caption)
        style_source = captions[0] if captions else None
        for span in spans:
            item = (style_source.model_copy(deep=True) if style_source else CaptionItem(id="edit", start=0, end=1, text=""))
            item.id = f"edit_{int(span['start'] * 1000)}"
            item.start = span["start"]
            item.end = span["end"]
            item.text = span["source"] or span["spoken"]
            item.translated_text = span["spoken"]
            item.editor_locked = True
            item.words = []
            item.source_caption_ids = [item.id]
            kept.append(item)
        return self.correct_medical_lines(sorted(kept, key=lambda caption: (caption.start, caption.end)))

    def translate_with_gemini(
        self,
        text_list: List[str],
        checkpoint=None,
        domain: Optional[str] = None,
        prior_findings: str = "",
    ) -> List[str]:
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
                if cached.get('source') == source and cached.get('backend') != 'local':
                    accepted = {int(i): t for i, t in cached.get('accepted', {}).items()
                                if str(i).isdigit() and 0 <= int(i) < len(source)
                                and isinstance(t, str) and any(c.isalnum() for c in t)
                                and not self.is_devanagari(t)
                                and not self.medical_english_is_unusable(source[int(i)]['text'], t)}
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
                medical = ""
                if (domain or "").strip().lower() == "medical":
                    medical = (
                        "This is medical speech. Keep cancer, tumour, TB, biopsy, chemotherapy, and scan names as medical terms. "
                        "Do not turn a spoken disease or medicine name into an unrelated English word. "
                    )
                if prior_findings:
                    medical += (
                        "Running inferences already recorded: " + prior_findings + ". "
                        "Use those inferences when a word could be either TB or television. "
                        "Write TB-like, not TV-like. "
                    )
                prompt = (
                    "Translate each Hindi or Hinglish line into one English sentence, then that English is what gets used. "
                    "Do not spell Hindi sounds in Latin letters. "
                    "When the speech is about TB, write TB, never thief or television. "
                    "When the speech is about cancer, write cancer, never cough as the name of the disease. "
                    + medical
                    + "Keep all facts, names, numbers and negation. Do not invent or summarize. "
                    + "Each ID is one spoken sentence: return that full English sentence, not a three-word scrap. "
                    + "Return exactly one nonempty English text per requested ID. Never renumber or omit IDs. "
                    + "Use the full context for meaning, but return only REQUESTED IDs. "
                    + "Return {lines:[{id:integer,text:string}]}. FULL CONTEXT: "
                    + json.dumps(source, ensure_ascii=False)
                    + " REQUESTED: "
                    + json.dumps(pending, ensure_ascii=False)
                )
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
                        source_text = next(row["text"] for row in pending if row["id"] == ident)
                        if self.medical_english_is_unusable(source_text, text):
                            continue
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
                                    and not self.is_devanagari(t)
                                    and not self.medical_english_is_unusable(source[int(i)]['text'], t)}
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
                    if self.medical_english_is_unusable(text_list[idx], text):
                        raise ValueError(
                            f'Local translation missed the medical meaning of subtitle line {idx + 1}; '
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
        domain: Optional[str] = None,
        prior_findings: str = "",
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
            result = self.translate_with_gemini(
                chunk, checkpoint_path, domain=domain, prior_findings=prior_findings
            )
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

        # NLLB-600M spells Hindi ("Adelog", "thief"). Gemini is the Hindi translator
        # whenever a key is configured, including TRANSLATION_BACKEND=local.
        # English lines on the local setting stay on NLLB. NLLB is the fallback.
        hindi = any(self.is_devanagari(line) for line in chunk)
        use_gemini = has_gemini and (
            preference in ('gemini', 'auto') or (preference == 'local' and hindi)
        )
        try:
            if preference == 'gemini' and not has_gemini:
                raise ValueError(
                    'TRANSLATION_BACKEND=gemini but no usable GEMINI_API_KEY is configured; '
                    'original-language captions retained.'
                )
            if use_gemini:
                try:
                    return try_gemini()
                except Exception as gemini_exc:
                    if preference == 'gemini':
                        raise
                    _log_exception(
                        'translation_gemini_failed_falling_back_to_local',
                        preference=preference,
                        chunk_index=chunk_index,
                        chunk_count=chunk_count,
                        gemini_error=str(gemini_exc)[:300],
                    )
                    try:
                        return try_local()
                    except Exception as local_exc:
                        raise ValueError(
                            'Gemini translation failed and the local fallback also failed; '
                            'original-language captions retained. '
                            f'gemini=({gemini_exc}); local=({local_exc})'
                        ) from local_exc
            try:
                return try_local()
            except Exception as local_exc:
                raise ValueError(
                    'Local translation failed and no Gemini key is configured; '
                    'original-language captions retained. No guessed translation was inserted. '
                    f'({local_exc})'
                ) from local_exc
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
        domain: Optional[str] = None,
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

        # 2. Translate only lines that are still Hindi or a short scrap.
        # An edited line and an English sentence already in hand stay as written.
        pending_indexes = [i for i, caption in enumerate(captions) if self.needs_new_translation(caption)]
        if not pending_indexes:
            return self.correct_medical_lines(captions, domain=domain)
        state = RunningInferences(domain)
        normalized: Dict[int, str] = {}
        findings_for_index: Dict[int, str] = {}
        for index in sorted(range(len(captions)), key=lambda item: (captions[item].start, captions[item].end)):
            findings_for_index[index] = state.describe()
            prior = state.snapshot()
            normalized[index] = self.normalize_medical_asr(captions[index].text, prior=prior, domain=domain)
            state.note(normalized[index])
        texts_to_translate = [normalized[i] for i in pending_indexes]
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
        translation_error: Optional[Exception] = None
        try:
            for chunk_index, i in enumerate(range(0, len(texts_to_translate), chunk_size)):
                chunk = texts_to_translate[i:i + chunk_size]
                checkpoint_path = None
                if checkpoint_dir:
                    import hashlib, json
                    digest = hashlib.sha256(
                        json.dumps({'version': 4, 'source': chunk}, ensure_ascii=False).encode()
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
                    domain=domain,
                    prior_findings=findings_for_index.get(pending_indexes[i], ""),
                )
                if len(translated_chunk) != len(chunk):
                    raise ValueError('Translation returned mismatched IDs; no partial dictionary translation was inserted.')
                translated_texts.extend(translated_chunk)
        except Exception as exc:
            translation_error = exc
            _log_exception(
                'translation_captions_failed',
                preference=preference,
                gemini_key_present=has_gemini,
                model=model_name,
                caption_count=len(captions),
                translated_so_far=len(translated_texts),
            )
        for offset, idx in enumerate(pending_indexes):
            if offset >= len(translated_texts):
                break
            cap = captions[idx]
            t_text = translated_texts[offset]
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

        self.correct_medical_lines(captions, domain=domain)
        if translation_error:
            unresolved = [
                index for index in pending_indexes
                if self.medical_english_is_unusable(captions[index].text, captions[index].translated_text or "")
                or (captions[index].translated_text or "") in ("", captions[index].text)
            ]
            if unresolved:
                raise translation_error

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
