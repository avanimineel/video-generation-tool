"""Scene cards for paper purple.

A beat becomes one card: a place, up to two cut-paper people, and props the
painter already knows. The lexicon maps a spoken word onto those drawings.
A kept card is appended for the next video. Weights are not changed here.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.core.config import settings

STYLES = ("woman", "man", "girl", "boy", "elder")
ACTIONS = ("walk", "sit", "stand", "wave", "offer", "pray")
PROPS = ("pill", "bill", "book", "phone", "house", "heart", "calendar", "cup", "chair", "door")
PLACES = ("house", "table", "doorway")
HEAVY_PROPS = {"pill", "bill", "book", "phone", "heart", "calendar", "cup"}

OBJECT_WORDS = {
    "pill": "pill", "pills": "pill", "medicine": "pill", "medicines": "pill",
    "tablet": "pill", "tablets": "pill", "dose": "pill", "doses": "pill",
    "capsule": "pill", "capsules": "pill",
    "bill": "bill", "bills": "bill", "money": "bill", "rupee": "bill", "rupees": "bill",
    "dollar": "bill", "dollars": "bill", "price": "bill", "prices": "bill",
    "cost": "bill", "costs": "bill", "fee": "bill", "fees": "bill",
    "book": "book", "books": "book", "page": "book", "pages": "book",
    "novel": "book", "novels": "book",
    "phone": "phone", "phones": "phone", "mobile": "phone", "mobiles": "phone",
    "app": "phone", "apps": "phone", "screen": "phone", "screens": "phone",
    "heart": "heart", "hearts": "heart",
    "calendar": "calendar", "calendars": "calendar", "date": "calendar", "dates": "calendar",
    "appointment": "calendar", "appointments": "calendar", "week": "calendar", "weeks": "calendar",
    "month": "calendar", "months": "calendar",
    "cup": "cup", "cups": "cup", "tea": "cup", "coffee": "cup", "water": "cup",
    "glass": "cup", "glasses": "cup",
}

STARTER_ALIASES = {
    "seat": {"prop": "chair"},
    "seats": {"prop": "chair"},
    "seated": {"action": "sit"},
    "goodbye": {"action": "wave"},
    "mentor": {"style": "elder"},
    "family": {"cast": 2, "style": "woman"},
    "greet": {"action": "wave"},
    "elder": {"style": "elder", "action": "walk"},
    "elders": {"style": "elder", "action": "walk"},
    "pray": {"action": "pray"},
    "praying": {"action": "pray"},
    "prayer": {"action": "pray"},
    "prayers": {"action": "pray"},
    "prayed": {"action": "pray"},
    "room": {"place": "house"},
    "rooms": {"place": "house"},
    "home": {"place": "house"},
    "homes": {"place": "house"},
    "house": {"place": "house"},
    "houses": {"place": "house"},
    "door": {"prop": "door"},
    "doors": {"prop": "door"},
    "parent": {"style": "woman"},
    "parents": {"cast": 2, "style": "woman"},
    "parenting": {"style": "woman"},
    "mentors": {"style": "elder"},
    "daughter": {"style": "girl"},
    "daughters": {"style": "girl", "cast": 2},
    "son": {"style": "boy"},
    "sons": {"style": "boy", "cast": 2},
    "child": {"style": "girl"},
    "children": {"style": "girl"},
    "kid": {"style": "boy"},
    "kids": {"style": "boy"},
    "guest": {"style": "man"},
    "guests": {"style": "man", "cast": 2},
    "everyone": {"cast": 2},
    "team": {"cast": 2, "style": "man"},
    "person": {"style": "woman"},
    "people": {"cast": 2},
    "offer": {"action": "offer"},
    "table": {"place": "table"},
}

_WORDS = re.compile(r"[a-z']+")


def lexicon_path():
    return settings.projects_dir / "paper_purple_lexicon.json"


def ledger_path():
    return settings.projects_dir / "accepted_scene_cards.jsonl"


def load_lexicon() -> dict:
    aliases = dict(STARTER_ALIASES)
    pending = []
    path = lexicon_path()
    if path.is_file():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        for word, cue in (saved.get("aliases") or {}).items():
            cleaned = _clean_cue(cue)
            if cleaned:
                aliases[str(word).strip().lower()] = cleaned
        pending = [str(word).strip().lower() for word in (saved.get("pending") or []) if str(word).strip()]
    return {"aliases": aliases, "pending": pending}


def _clean_cue(cue) -> dict:
    if not isinstance(cue, dict):
        return {}
    cleaned = {}
    prop = str(cue.get("prop") or "")
    style = str(cue.get("style") or "")
    action = str(cue.get("action") or "")
    place = str(cue.get("place") or "")
    if prop in PROPS:
        cleaned["prop"] = prop
    if style in STYLES:
        cleaned["style"] = style
    if action in ACTIONS:
        cleaned["action"] = action
    if place in PLACES:
        cleaned["place"] = place
    try:
        count = int(cue.get("cast") or 0)
    except (TypeError, ValueError):
        count = 0
    if count in (1, 2):
        cleaned["cast"] = count
    return cleaned


def _save_lexicon(lexicon: dict) -> None:
    path = lexicon_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    extra = {word: cue for word, cue in lexicon["aliases"].items() if STARTER_ALIASES.get(word) != cue}
    payload = {"aliases": extra, "pending": lexicon.get("pending") or []}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_accepted_cards(limit: int = 8) -> list:
    path = ledger_path()
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows[-limit:]


def read_cues(text: str, lexicon: dict) -> dict:
    aliases = lexicon.get("aliases") or {}
    pending_words = set(lexicon.get("pending") or [])
    place = ""
    props = []
    styles = []
    actions = []
    cast_n = 0
    pending = []
    hit = False
    for word in _WORDS.findall((text or "").lower()):
        if word in pending_words:
            pending.append(word)
            continue
        cue = aliases.get(word)
        if cue is None and word in OBJECT_WORDS:
            cue = {"prop": OBJECT_WORDS[word]}
        if not cue:
            continue
        hit = True
        if cue.get("place") in PLACES and not place:
            place = cue["place"]
        prop = cue.get("prop")
        if prop in PROPS and prop not in props:
            props.append(prop)
        if cue.get("style") in STYLES:
            styles.append(cue["style"])
        if cue.get("action") in ACTIONS:
            actions.append(cue["action"])
        cast_n = max(cast_n, int(cue.get("cast") or 0))
    return {
        "hit": hit,
        "place": place,
        "props": props,
        "styles": styles,
        "actions": actions,
        "cast_n": cast_n,
        "pending": pending,
    }


def build_cast(styles, actions, cast_n) -> list:
    if not styles and not actions and cast_n == 0:
        return []
    count = max(cast_n, len(set(styles)), 1 if actions else 0)
    if "pray" in actions or "offer" in actions:
        count = max(count, 2)
    count = min(2, count)
    if count == 0:
        return []
    primary = styles[0] if styles else "woman"
    if "elder" in styles:
        primary = "elder"
    same_pair = bool(styles) and all(style == primary for style in styles) and cast_n >= 2 and primary in ("girl", "boy")
    secondary = primary if same_pair else ("man" if primary != "man" else "woman")
    action_a = "stand"
    action_b = "stand"
    if "pray" in actions:
        action_a = action_b = "pray"
    elif "offer" in actions:
        action_a = "walk" if primary == "elder" else "stand"
        action_b = "offer"
    elif "wave" in actions:
        action_a = action_b = "wave"
    elif "walk" in actions:
        action_a = "walk"
    elif "sit" in actions:
        action_a = "sit"
    elif actions:
        action_a = actions[-1]
    cast = [{"style": primary, "action": action_a}]
    if count > 1:
        cast.append({"style": secondary, "action": action_b})
    return cast


def card_from_cues(cues: dict) -> dict:
    cast = build_cast(cues["styles"], cues["actions"], cues["cast_n"])
    props = [prop for prop in cues["props"] if prop != cues["place"]]
    subject = next((prop for prop in props if prop in HEAVY_PROPS), "")
    if not subject and props:
        subject = props[0]
    elif not subject and cues["place"] == "house":
        subject = "house"
    elif not subject:
        subject = "object"
    return {
        "place": cues["place"],
        "cast": cast,
        "props": props,
        "subject": subject,
        "pending": cues["pending"],
    }


def card_drawable(card: dict) -> bool:
    return bool(card.get("cast") or card.get("props") or card.get("place"))


def _continues(previous, nxt) -> bool:
    if not previous or not nxt:
        return False
    gap = float(nxt[0]["start"]) - float(previous[-1]["end"])
    if gap > 6:
        return False
    if float(nxt[-1]["end"]) - float(previous[0]["start"]) > 14:
        return False
    return True


def _cue_continues(prev_cues, next_cues) -> bool:
    if not prev_cues["hit"] or not next_cues["hit"]:
        return False
    if next_cues["place"] and next_cues["place"] != prev_cues["place"]:
        return False
    if any(prop in HEAVY_PROPS for prop in next_cues["props"]):
        return False
    prev_people = bool(prev_cues["styles"] or prev_cues["cast_n"] or prev_cues["actions"])
    next_people = bool(next_cues["styles"] or next_cues["cast_n"] or next_cues["actions"])
    if any(prop in HEAVY_PROPS for prop in prev_cues["props"]) and not prev_people and next_people:
        return False
    new_styles = [style for style in next_cues["styles"] if style not in prev_cues["styles"]]
    if new_styles and (next_cues["place"] or "elder" in prev_cues["styles"]):
        return False
    return bool(next_cues["cast_n"] or next_cues["styles"] or next_cues["actions"] or next_cues["props"] or next_cues["place"])


def join_groups(groups, lexicon) -> list:
    merged = []
    merged_cues = []
    for group in groups:
        text = " ".join(row["text"] for row in group)
        cues = read_cues(text, lexicon)
        if merged and _continues(merged[-1], group) and _cue_continues(merged_cues[-1], cues):
            merged[-1].extend(group)
            merged_cues[-1] = read_cues(" ".join(row["text"] for row in merged[-1]), lexicon)
        else:
            merged.append(list(group))
            merged_cues.append(cues)
    return merged


def groups_for(lines, beats, lexicon) -> list:
    if beats:
        groups = []
        for beat in beats:
            wanted = set(beat.get("caption_indexes") or [])
            rows = [row for row in lines if row.get("index") in wanted]
            if rows:
                groups.append(rows)
        covered = {row.get("index") for group in groups for row in group}
        for row in lines:
            if row.get("index") not in covered:
                groups.append([row])
        groups.sort(key=lambda group: float(group[0]["start"]))
    else:
        groups = [[row] for row in lines]
    return join_groups(groups, lexicon)


def scene_prompt(beats, examples) -> str:
    """Ask for cards. The spoken lines are quoted and must not be rewritten."""
    shown = []
    for example in examples[-4:]:
        spoken = " ".join(example.get("lines") or [])
        card = example.get("card") or {}
        shown.append("Spoken: " + spoken + "\n" + json.dumps({
            "id": "example",
            "place": card.get("place") or "",
            "cast": card.get("cast") or [],
            "props": card.get("props") or [],
        }, ensure_ascii=False))
    requests = []
    for beat in beats:
        requests.append(f"{beat['id']}. {beat['text']}")
    return (
        "You choose a paper cutout for each spoken beat. "
        "You never rewrite, translate, or add words. "
        f"Styles: {', '.join(STYLES)}. Actions: {', '.join(ACTIONS)}. "
        f"Props: {', '.join(PROPS)}. Places: {', '.join(PLACES)}. "
        "Use at most two people. Leave a field empty when the line names nothing drawable. "
        'Reply with JSON only: {"cards":[{"id":0,"place":"house","cast":[{"style":"woman","action":"wave"}],"props":["chair"]}]}\n\n'
        + ("\n\n".join(shown) + "\n\n" if shown else "")
        + "Beats:\n"
        + "\n".join(requests)
    )


def parse_scene_reply(text: str) -> list:
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return []
    raw_cards = data.get("cards") if isinstance(data, dict) else None
    if raw_cards is None and isinstance(data, dict) and ("cast" in data or "props" in data or "place" in data):
        raw_cards = [data]
    if not isinstance(raw_cards, list):
        return []
    parsed = []
    for raw in raw_cards:
        if not isinstance(raw, dict):
            continue
        card, rejected = sanitize_card(raw)
        if card is None:
            continue
        parsed.append({"id": raw.get("id"), "card": card, "rejected": rejected})
    return parsed


def sanitize_card(raw) -> tuple:
    if not isinstance(raw, dict):
        return None, []
    rejected = []
    place = str(raw.get("place") or "")
    if place and place not in PLACES:
        rejected.append(place)
        place = ""
    props = []
    for prop in raw.get("props") or []:
        name = str(prop or "")
        if name in PROPS and name not in props:
            props.append(name)
        elif name:
            rejected.append(name)
    cast = []
    for member in raw.get("cast") or []:
        if not isinstance(member, dict) or len(cast) >= 2:
            continue
        style = str(member.get("style") or "")
        action = str(member.get("action") or "stand")
        if style not in STYLES:
            if style:
                rejected.append(style)
            continue
        if action not in ACTIONS:
            if action:
                rejected.append(action)
            action = "stand"
        cast.append({"style": style, "action": action})
    subject = next((prop for prop in props if prop in HEAVY_PROPS), "")
    if not subject and props:
        subject = props[0]
    elif not subject and place == "house":
        subject = "house"
    else:
        subject = subject or "object"
    card = {"place": place, "cast": cast, "props": props, "subject": subject}
    if not card_drawable(card):
        return None, rejected
    return card, rejected


def _remember_pending(words) -> None:
    fresh = []
    for word in words or []:
        token = str(word or "").strip().lower()
        if token and token not in fresh and token not in STARTER_ALIASES and token not in OBJECT_WORDS:
            fresh.append(token)
    if not fresh:
        return
    lexicon = load_lexicon()
    pending = list(lexicon.get("pending") or [])
    changed = False
    for word in fresh:
        if word not in pending and word not in lexicon["aliases"]:
            pending.append(word)
            changed = True
    if changed:
        lexicon["pending"] = pending
        _save_lexicon(lexicon)


def usable_model_cards(parsed, allowed) -> tuple:
    """Keep a model card only for a beat that was actually asked."""
    found = {}
    rejected = []
    allowed = {int(item) for item in allowed}
    for item in parsed or []:
        try:
            beat_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        if beat_id not in allowed:
            continue
        found[beat_id] = item["card"]
        rejected.extend(item.get("rejected") or [])
    return found, rejected


def _qwen_fill(groups, lexicon) -> dict:
    from app.services.local_story_models import _generate_qwen, models_enabled, qwen_dir

    if not models_enabled() or qwen_dir() is None:
        return {}
    beats = []
    for index, group in enumerate(groups):
        text = " ".join(row["text"] for row in group)
        cues = read_cues(text, lexicon)
        if card_drawable(card_from_cues(cues)) or index == 0:
            continue
        if len(text.split()) < 3:
            continue
        beats.append({"id": index, "text": text})
        if len(beats) >= 6:
            break
    if not beats:
        return {}
    try:
        reply = _generate_qwen(qwen_dir(), scene_prompt(beats, load_accepted_cards(4)), 420)
    except Exception:
        return {}
    found, rejected = usable_model_cards(parse_scene_reply(reply), [beat["id"] for beat in beats])
    _remember_pending(rejected)
    return found


def plan_paper_scenes(lines, beats=None, lexicon=None) -> list:
    """One card per beat. A line with no drawing stays off this list."""
    lines = list(lines or [])
    if not lines:
        return []
    lexicon = lexicon if lexicon is not None else load_lexicon()
    groups = groups_for(lines, beats, lexicon)
    guessed = _qwen_fill(groups, lexicon)
    scenes = []
    for index, group in enumerate(groups):
        text = " ".join(row["text"] for row in group)
        cues = read_cues(text, lexicon)
        card = card_from_cues(cues)
        if not card_drawable(card):
            if index in guessed:
                card = guessed[index]
            elif index == 0:
                card = {"place": "", "cast": [], "props": [], "subject": "object", "pending": []}
            else:
                continue
        scenes.append({
            "start": float(group[0]["start"]),
            "end": float(group[-1]["end"]),
            "place": card.get("place") or "",
            "cast": card.get("cast") or [],
            "props": card.get("props") or [],
            "subject": card.get("subject") or "object",
            "lines": [row["text"] for row in group],
            "indexes": [row.get("index") for row in group],
        })
    return scenes


def accept_scene(lines, card, aliases=None, project_id: str = "") -> dict:
    """Keep a card and any new word that already names a drawing."""
    spoken = [" ".join(str(line or "").split()) for line in (lines or []) if str(line or "").strip()]
    if not spoken:
        raise ValueError("A kept scene needs the spoken lines.")
    cleaned, rejected = sanitize_card(card or {})
    if cleaned is None:
        raise ValueError("This scene names nothing the paper painter can draw.")
    lexicon = load_lexicon()
    pending = list(lexicon.get("pending") or [])
    accepted_aliases = {}
    for alias in aliases or []:
        word = str((alias or {}).get("word") or "").strip().lower()
        if not re.fullmatch(r"[a-z][a-z']{1,31}", word):
            continue
        cue = _clean_cue(alias)
        if cue:
            lexicon["aliases"][word] = cue
            accepted_aliases[word] = cue
            if word in pending:
                pending.remove(word)
        else:
            if word not in pending:
                pending.append(word)
            rejected.append(word)
    lexicon["pending"] = pending
    _save_lexicon(lexicon)
    row = {
        "lines": spoken,
        "card": {"place": cleaned["place"], "cast": cleaned["cast"], "props": cleaned["props"]},
        "aliases": accepted_aliases,
        "project_id": project_id,
        "overlay": "paper_purple",
        "at": datetime.now(timezone.utc).isoformat(),
    }
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = (tuple(spoken), json.dumps(row["card"], sort_keys=True))
    seen = set()
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                saved = json.loads(line)
            except ValueError:
                continue
            seen.add((tuple(saved.get("lines") or []), json.dumps(saved.get("card") or {}, sort_keys=True)))
    kept = False
    if key not in seen:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        kept = True
    return {"kept": kept, "pending": pending, "aliases": accepted_aliases, "card": row["card"]}
