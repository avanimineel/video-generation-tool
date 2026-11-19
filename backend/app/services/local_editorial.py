"""Local editorial path used when Gemini or Twelve Labs reject a key.

Order is Gemini, then in-process Qwen, then LOCAL_PLANNER_URL,
then a deterministic planner that needs no GPU. Shot cuts come from ffmpeg.
YOLO11n, Florence-2, and SigLIP live in local_models and stay empty when a weight fails to load.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import requests

from app.core.config import settings
from app.services.editorial_planner import Decision, Scores, verbatim_text, weak_title

_AUTH = {401, 403}


def note_provider_failure(provider: str, status: int) -> None:
    if status not in _AUTH:
        return
    health = _load()
    health[provider] = {"status": status, "degraded": True}
    _save(health)


def provider_degraded(provider: str) -> bool:
    return bool(_load().get(provider, {}).get("degraded"))


def clear_provider(provider: str) -> None:
    health = _load()
    health.pop(provider, None)
    _save(health)


def local_planner_configured() -> bool:
    return bool(os.getenv("LOCAL_PLANNER_URL", "").strip())


def local_llm_json(prompt: str, schema: Optional[dict] = None) -> Optional[dict]:
    """OpenAI-compatible JSON call. A missing server returns None."""
    url = os.getenv("LOCAL_PLANNER_URL", "").strip()
    if not url:
        return None
    body = {
        "model": os.getenv("LOCAL_PLANNER_MODEL", "qwen2.5"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "editorial_plan", "schema": schema}}
    try:
        response = requests.post(url, json=body, timeout=(5, 90))
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or payload.get("content")
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return None
    return None


def deterministic_decisions(segments, feedback=None) -> list:
    """A stock image for a visible subject, otherwise a spoken title or a number."""
    decisions = []
    seen = set()
    domain = str(((feedback or {}).get("domain") or {}).get("domain") or "")
    for segment in segments:
        choices = _cues(segment, domain)
        if not choices:
            decisions.append(_quiet(segment, "No number or substantive spoken phrase in this stretch."))
            continue
        for cue in choices:
            search_text = cue["text"]
            fixed = _saved_transcript(domain, cue["text"])
            if fixed and fixed.get("correction"):
                search_text = str(fixed["correction"])
            query, alternates = visual_query(search_text, domain)
            if fixed and fixed.get("note") and str(fixed["note"]) not in alternates:
                alternates = [str(fixed["note"]), *alternates][:2]
            saved = _saved_example(domain, search_text)
            if saved and saved.get("query"):
                query = str(saved["query"])
                note = str(saved.get("note") or "")
                if note and note not in alternates:
                    alternates = [note, *alternates][:2]
            if query in seen and alternates:
                query = next((item for item in alternates if item not in seen), query)
            if query:
                seen.add(query)
            if query and cue["cue_kind"] != "number":
                decisions.append(_picture(segment, cue, query, alternates))
            else:
                decisions.append(_title(segment, cue))
    return decisions


def _saved_example(domain: str, text: str):
    if not domain:
        return None
    from app.services.domain_knowledge import match_example
    return match_example(domain, text)


def _saved_transcript(domain: str, text: str):
    if not domain:
        return None
    from app.services.domain_knowledge import match_transcript
    return match_transcript(domain, text)


def auth_failure(message: str) -> bool:
    text = message or ""
    return "401" in text or "403" in text or "degraded" in text.lower() or "API key not valid" in text or "api_key_invalid" in text


def _cues(segment, domain: str = "") -> list[dict]:
    beats = list(getattr(segment, "dialogue_beats", None) or [])
    if not beats and getattr(segment, "transcript", ""):
        beats = [{"start_sec": segment.start_sec, "end_sec": segment.end_sec, "text": segment.transcript}]
    spoken = getattr(segment, "transcript", "") or ""
    chosen = []
    last_end = segment.start_sec
    for clause in _clauses(beats):
        text = focus_phrase(clause["text"], domain)
        if not text or weak_title(text) or not verbatim_text(text, spoken):
            continue
        start = max(_phrase_start(clause, text), last_end)
        end = min(float(clause["end_sec"]), segment.end_sec)
        if end < start + 1.0:
            end = min(segment.end_sec, start + 1.6)
        if end <= start or start >= segment.end_sec:
            continue
        number = bool(re.search(r"\d", text))
        if chosen and start - chosen[-1]["start_sec"] < 1.5 and not number:
            continue
        anchor_id, anchor_word = _anchor(segment, start)
        chosen.append({
            "text": text,
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "strategy": "STAT_COUNTER" if number else "KINETIC_TYPOGRAPHY",
            "cue_kind": "number" if number else "phrase",
            "intent": "QUANTIFY" if number else "EMPHASIZE",
            "audio_anchor_id": anchor_id,
            "audio_anchor_word": anchor_word,
        })
        last_end = end
        if len(chosen) >= 2:
            break
    return chosen


def _clauses(beats) -> list[dict]:
    """Join adjacent three-word captions into the spoken sentence they came from."""
    clauses = []
    current = None
    for beat in beats:
        text = str(beat.get("text") or "").strip()
        if not text:
            continue
        start = float(beat.get("start_sec") or 0)
        end = float(beat.get("end_sec") or start)
        if current is None:
            current = {"text": text, "start_sec": start, "end_sec": end}
            continue
        ended = current["text"].rstrip().endswith((".", "?", "!", "।"))
        gap = start - current["end_sec"]
        if ended or gap > 0.75 or len(current["text"].split()) + len(text.split()) > 18:
            clauses.append(current)
            current = {"text": text, "start_sec": start, "end_sec": end}
            continue
        current["text"] = f"{current['text']} {text}"
        current["end_sec"] = end
    if current:
        clauses.append(current)
    return clauses


def focus_phrase(text: str, domain: str = "") -> str:
    """A 4 to 8 word spoken clause. A field term keeps a greeting from becoming the title."""
    words = [word for word in str(text or "").split() if word]
    if not words:
        return ""
    terms = _domain_terms(domain)
    best = ""
    best_score = -1
    shortest = min(8, len(words))
    for size in range(shortest, 2, -1):
        for index in range(0, len(words) - size + 1):
            window = words[index:index + size]
            score = _window_score(window, terms)
            if score > best_score:
                best_score = score
                best = " ".join(window)
    if best_score < 0:
        return ""
    return _trim_leading_filler(best)


def _window_score(window, terms: set[str]) -> int:
    tokens = [_norm(word) for word in window]
    content = [token for token in tokens if token not in _ABSTRACT and len(token) > 2]
    hits = [token for token in tokens if token in terms]
    if terms and (_norm(window[0]) in _ABSTRACT or not hits):
        return -1
    if not terms and len(content) < 2 and not any(char.isdigit() for char in " ".join(window)):
        return -1
    return 12 * len(hits) + 2 * len(content) + len(window)


def _trim_leading_filler(text: str) -> str:
    words = text.split()
    while len(words) > 4 and _norm(words[0]) in _ABSTRACT:
        words = words[1:]
    return " ".join(words)


def _phrase_start(clause: dict, phrase: str) -> float:
    words = clause["text"].split()
    wanted = [_norm(word) for word in phrase.split()]
    span = max(0.0, float(clause["end_sec"]) - float(clause["start_sec"]))
    for index in range(0, len(words) - len(wanted) + 1):
        if [_norm(word) for word in words[index:index + len(wanted)]] == wanted:
            return float(clause["start_sec"]) + span * (index / max(1, len(words)))
    return float(clause["start_sec"])


def useful_title(text: str, domain: str = "") -> bool:
    words = str(text or "").split()
    if any(char.isdigit() for char in text or ""):
        return True
    tokens = [_norm(word) for word in words]
    if any(token in _domain_terms(domain) for token in tokens):
        return len(words) >= 3
    return len(words) >= 4 and any(token not in _ABSTRACT and len(token) > 2 for token in tokens)


def lengthen_spoken_titles(decisions, segments, domain: str = ""):
    """Replace a three-word fragment with the medical or concrete clause around it."""
    by_id = {segment.id: segment for segment in segments}
    for decision in decisions:
        segment = by_id.get(decision.segment_id)
        if segment is None or not decision.intervene:
            continue
        transcript = getattr(segment, "transcript", "") or ""
        if decision.strategy in ("KINETIC_TYPOGRAPHY", "MIXED_TYPOGRAPHY_TITLE"):
            if useful_title(decision.display_text, domain):
                continue
            phrase = focus_phrase(transcript, domain)
            if phrase and verbatim_text(phrase, transcript):
                decision.display_text = phrase
                decision.anchor_phrase = phrase
            else:
                decision.intervene = False
                decision.strategy = "NO_INTERVENTION"
                decision.rationale = "This stretch has no concrete spoken phrase to put on screen."
        elif decision.strategy == "STOCK_IMAGE":
            query = (decision.asset.retrieval_query if decision.asset else "") or ""
            if _query_names_subject(query, domain):
                continue
            phrase = focus_phrase(transcript, domain) or transcript
            replacement, alternates = visual_query(phrase, domain)
            if replacement and decision.asset is not None:
                decision.asset.retrieval_query = replacement
                decision.asset.semantic_target = replacement
                decision.asset.alternate_queries = alternates
                if phrase and verbatim_text(phrase, transcript):
                    decision.display_text = phrase
                    decision.anchor_phrase = phrase
    return decisions


def spoken_sentences(captions) -> list[dict]:
    """Join caption boxes into the sentences that were spoken."""
    words = []
    for caption in captions or []:
        items = caption.get("words") if isinstance(caption, dict) else getattr(caption, "words", None)
        if not items:
            text = caption.get("text") if isinstance(caption, dict) else getattr(caption, "text", "")
            start = caption.get("start") if isinstance(caption, dict) else getattr(caption, "start", 0)
            end = caption.get("end") if isinstance(caption, dict) else getattr(caption, "end", start)
            if text:
                words.append({"word": str(text), "start": float(start or 0), "end": float(end or start or 0)})
            continue
        for item in items:
            token = item.get("word") if isinstance(item, dict) else getattr(item, "word", "")
            if not token:
                continue
            start = item.get("start") if isinstance(item, dict) else getattr(item, "start", 0)
            end = item.get("end") if isinstance(item, dict) else getattr(item, "end", start)
            words.append({"word": str(token), "start": float(start or 0), "end": float(end or start or 0)})
    sentences = []
    current = []
    for word in words:
        current.append(word)
        if word["word"].rstrip().endswith((".", "?", "!", "।")):
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return [{
        "text": " ".join(word["word"] for word in group),
        "start": group[0]["start"],
        "end": group[-1]["end"],
    } for group in sentences if group]


def claim_phrase(text: str, domain: str = "") -> str:
    """Use the whole sentence when it opens on the subject. A greeting stays off the title."""
    words = [word for word in str(text or "").split() if word]
    terms = _domain_terms(domain)
    if 4 <= len(words) <= 12:
        first = next((index for index, word in enumerate(words) if _norm(word) in terms), None)
        if terms and first is not None and first <= 2:
            return " ".join(words)
        if not terms and _norm(words[0]) not in _ABSTRACT:
            return " ".join(words)
    return focus_phrase(text, domain)


def promote_sentence_titles(decisions, segments, captions, domain: str = ""):
    """Put a full spoken sentence on screen. A one-second window cannot hold it."""
    titles = []
    for sentence in spoken_sentences(captions):
        phrase = claim_phrase(sentence["text"], domain)
        if len(phrase.split()) < 4 or not verbatim_text(phrase, sentence["text"]):
            continue
        if _domain_terms(domain) and not any(_norm(word) in _domain_terms(domain) for word in phrase.split()):
            continue
        segment = next((item for item in segments if item.start_sec <= sentence["start"] < item.end_sec), None)
        if segment is None:
            continue
        anchor_id, anchor_word = None, ""
        cues = [word for word in (getattr(segment, "audio_cues", None) or []) if word.get("usable") and word.get("word")]
        if cues:
            nearest = min(cues, key=lambda word: abs(float(word.get("start") or 0) - sentence["start"]))
            if abs(float(nearest.get("start") or 0) - sentence["start"]) <= 0.8:
                anchor_id, anchor_word = nearest.get("id"), str(nearest.get("word") or "")
        end = min(sentence["end"], sentence["start"] + 4.0)
        if end < sentence["start"] + 1.5:
            end = sentence["start"] + 1.6
        titles.append(Decision(
            segment_id=segment.id,
            intervene=True,
            rationale="The spoken sentence is placed in full. A short caption box was not used as the title.",
            intent="EMPHASIZE",
            strategy="KINETIC_TYPOGRAPHY",
            anchor_phrase=phrase,
            audio_anchor_id=anchor_id,
            audio_anchor_word=anchor_word,
            display_text=phrase,
            cue_kind="phrase",
            start_sec=round(sentence["start"], 3),
            end_sec=round(end, 3),
            visual_role="emphasis",
            scores=_scores(),
            composition={"layout": "text_overlay", "position": [0.5, 0.32]},
        ))
    if not titles:
        return decisions
    for decision in decisions:
        if not decision.intervene:
            continue
        for title in titles:
            if decision.display_text.strip() == title.display_text.strip():
                continue
            if decision.start_sec < title.start_sec < decision.end_sec and title.start_sec - decision.start_sec >= 1.5:
                decision.end_sec = round(title.start_sec, 3)
            elif title.start_sec <= decision.start_sec < title.end_sec and decision.strategy in ("STOCK_IMAGE", "KINETIC_TYPOGRAPHY", "MIXED_TYPOGRAPHY_TITLE"):
                decision.intervene = False
                decision.strategy = "NO_INTERVENTION"
                decision.rationale = "This fragment is part of a sentence that is already placed as a title."
    return list(decisions) + titles


def _query_names_subject(query: str, domain: str) -> bool:
    tokens = [_norm(word) for word in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", query or "")]
    content = [token for token in tokens if token not in _ABSTRACT]
    if any(token in _domain_terms(domain) for token in content):
        return True
    return len(content) >= 2


def _anchor(segment, start: float):
    cues = [word for word in (getattr(segment, "audio_cues", None) or []) if word.get("usable") and word.get("word")]
    if not cues:
        return None, ""
    nearest = min(cues, key=lambda word: abs(float(word.get("start") or 0) - start))
    return nearest.get("id"), str(nearest.get("word") or "")


def _scores() -> Scores:
    return Scores(**{name: (0.2 if name in ("redundancy", "visual_fatigue") else 0.55) for name in Scores.model_fields})


def _quiet(segment, reason: str) -> Decision:
    return Decision(
        segment_id=segment.id,
        intervene=False,
        rationale=reason,
        strategy="NO_INTERVENTION",
        start_sec=segment.start_sec,
        end_sec=segment.end_sec,
        scores=_scores(),
    )


_ABSTRACT = {
    "this", "that", "these", "those", "there", "here", "with", "from", "into", "about",
    "after", "before", "today", "where", "when", "what", "which", "while", "because",
    "would", "could", "should", "their", "them", "they", "your", "our", "are", "was",
    "were", "been", "being", "have", "has", "had", "the", "and", "for", "not", "but",
    "very", "just", "also", "than", "then", "over", "under", "starting", "start",
    "discuss", "discussion", "talking", "video", "people", "something", "anything",
    "really", "most", "more", "such", "will", "can", "may", "into",
    "about", "talk", "one", "series", "going", "know", "particular", "new",
    "surprised", "here", "you", "are", "the", "for", "maximum",
    "we", "to", "of", "in", "is", "on", "at", "by", "or",
}


_DOMAIN_WORDS = {
    "medical": {
        "cancer", "tumour", "tumor", "lung", "biopsy", "chemotherapy", "patient",
        "scan", "x-ray", "xray", "tb", "surgery", "blood", "cough", "symptom",
        "diagnosis", "treatment", "smoker", "death", "deaths",
    },
    "sports": {"goal", "ball", "coach", "tournament", "injury", "team", "match", "score"},
}


def _norm(word: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", word.lower())


def _domain_terms(domain: str) -> set[str]:
    return set(_DOMAIN_WORDS.get((domain or "").strip().lower(), ()))


def visual_query(text: str, domain: str = "") -> tuple[str, list[str]]:
    """Stock search words taken from the spoken line, in the order they were said."""
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text or "")
    content: list[str] = []
    for word in words:
        token = word.lower().strip("'")
        if token in _ABSTRACT or token in content:
            continue
        content.append(token)
    terms = [token for token in content if token in _domain_terms(domain)]
    if terms:
        content = terms + [token for token in content if token not in terms]
    elif len(content) < 2:
        return "", []
    query = " ".join(content[:5])
    alternates = []
    pair = " ".join(content[:2])
    tail = " ".join(content[-2:])
    for item in (pair, tail):
        if item and item != query and item not in alternates:
            alternates.append(item)
    return query, alternates[:2]


def _picture(segment, cue: dict, query: str, alternates: list[str]) -> Decision:
    from app.services.editorial_planner import AssetPlan, Composition
    return Decision(
        segment_id=segment.id,
        intervene=True,
        rationale="Local planner. The spoken line names a visible subject, so a fresh stock image is searched.",
        intent="ILLUSTRATE",
        strategy="STOCK_IMAGE",
        anchor_phrase=cue["text"],
        audio_anchor_id=cue.get("audio_anchor_id"),
        audio_anchor_word=cue.get("audio_anchor_word") or "",
        cue_kind="object",
        start_sec=cue["start_sec"],
        end_sec=cue["end_sec"],
        display_text=cue["text"],
        visual_role="illustration",
        scores=_scores(),
        asset=AssetPlan(
            asset_type="image",
            semantic_target=query,
            retrieval_query=query,
            alternate_queries=alternates,
            required_entities=query.split()[:2],
            desired_visual_description=query,
            negative_constraints=["watermark", "logo", "slide with only text"],
        ),
        composition=Composition(layout="split_screen", position=[0.5, 0.5]),
    )


def _title(segment, cue: dict) -> Decision:
    return Decision(
        segment_id=segment.id,
        intervene=True,
        rationale="Local planner. Spoken text placed because the cloud planner is unavailable.",
        intent=cue["intent"],
        strategy=cue["strategy"],
        anchor_phrase=cue["text"],
        audio_anchor_id=cue.get("audio_anchor_id"),
        audio_anchor_word=cue.get("audio_anchor_word") or "",
        cue_kind=cue["cue_kind"],
        start_sec=cue["start_sec"],
        end_sec=cue["end_sec"],
        display_text=cue["text"],
        visual_role="emphasis",
        scores=_scores(),
        composition={"layout": "text_overlay", "position": [0.5, 0.32]},
    )


def _path():
    return settings.projects_dir / "provider_health.json"


def _load() -> dict:
    path = _path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(health: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(health, indent=2), encoding="utf-8")
    temporary.replace(path)
