"""Local story beats and source-frame checks.

Qwen2.5-3B-Instruct only chooses which neighboring captions continue one claim.
The words on screen stay the spoken lines. Florence-2 looks at one frame per
caption and keeps the speaker when that frame already shows the subject.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)

QWEN_ID = "Qwen/Qwen2.5-3B-Instruct"
FLORENCE_ID = "microsoft/Florence-2-large"
PERSON_WORDS = {
    "person", "people", "man", "woman", "speaker", "face", "doctor", "patient",
    "human", "nurse", "guy", "lady",
}

_beat_cache: dict = {}
_last_source = "separate"
_qwen = None
_florence = None


def models_enabled() -> bool:
    flag = os.getenv("LOCAL_STORY_MODELS", "auto").strip().lower()
    if flag in {"0", "off", "false", "no"}:
        return False
    if os.getenv("PYTEST_CURRENT_TEST") and flag != "1":
        return False
    return True


def beat_source() -> str:
    return _last_source


def _line(caption):
    if isinstance(caption, dict):
        text = str(caption.get("text") or caption.get("translated_text") or "").strip()
        start = float(caption.get("start", caption.get("start_sec", 0)) or 0)
        end = float(caption.get("end", caption.get("end_sec", start)) or start)
        return text, start, end
    translated = str(getattr(caption, "translated_text", "") or "").strip()
    spoken = str(getattr(caption, "text", "") or "").strip()
    start = float(getattr(caption, "start", 0) or 0)
    end = float(getattr(caption, "end", start) or start)
    return translated or spoken, start, end


def normalize_groups(count: int, groups) -> list:
    """Neighboring indexes that share a beat. A gap or a bad id stays separate."""
    beat_of = list(range(count))
    for group in groups or []:
        ids = sorted({i for i in group if isinstance(i, int) and 0 <= i < count})
        if len(ids) < 2:
            continue
        lead = ids[0]
        previous = lead
        for index in ids[1:]:
            if index == previous + 1:
                beat_of[index] = beat_of[lead]
            else:
                lead = index
            previous = index
    result = []
    for index, beat in enumerate(beat_of):
        if result and beat_of[index - 1] == beat and beat != index:
            result[-1].append(index)
        else:
            result.append([index])
    return result


def parse_beat_ids(text: str, count: int):
    """Beat ids from the model. None when the reply is not a neighbor grouping."""
    if count < 1:
        return []
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    ids = data.get("beat") if isinstance(data, dict) else None
    if not isinstance(ids, list) or len(ids) != count:
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) for item in ids):
        return None
    if ids[0] != 0:
        return None
    for previous, nxt in zip(ids, ids[1:]):
        if nxt not in (previous, previous + 1):
            return None
    return ids


def groups_from_ids(ids) -> list:
    groups = []
    for index, beat in enumerate(ids):
        if groups and beat == ids[index - 1]:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


def _singletons(count: int) -> list:
    return [[index] for index in range(count)]


def qwen_dir() -> Path | None:
    raw = os.getenv("QWEN_MODEL_PATH") or "/data/developer/oonex/models/Qwen2.5-3B-Instruct"
    path = Path(raw)
    if not (path / "config.json").is_file():
        return None
    total = sum(item.stat().st_size for item in path.glob("*.safetensors"))
    if total < 4_000_000_000:
        return None
    return path


def florence_dir() -> Path | None:
    raw = os.getenv("FLORENCE_MODEL_PATH")
    candidates = []
    if raw:
        candidates.append(Path(raw))
    cache = Path(os.getenv("HF_HUB_CACHE") or "/data/developer/oonex/hf-cache")
    candidates.append(cache / "models--microsoft--Florence-2-large" / "snapshots")
    for candidate in candidates:
        if candidate.is_file() or (candidate / "config.json").is_file():
            weights = candidate / "model.safetensors"
            if weights.is_file() and weights.stat().st_size > 1_000_000_000:
                return candidate
        if candidate.is_dir():
            for config in candidate.glob("*/config.json"):
                folder = config.parent
                weights = folder / "model.safetensors"
                if weights.is_file() and weights.stat().st_size > 1_000_000_000:
                    return folder
    return None


def _expand(count: int, usable: list, groups: list) -> list:
    raw = []
    for group in groups:
        raw.append([usable[index] for index in group if 0 <= index < len(usable)])
    return normalize_groups(count, raw)


def caption_beat_groups(captions) -> list:
    """Group neighboring captions. The model is asked only for beat ids."""
    global _last_source
    captions = list(captions or [])
    count = len(captions)
    if count < 2 or not models_enabled():
        _last_source = "separate"
        return _singletons(count)
    usable = []
    lines = []
    for index, caption in enumerate(captions):
        text, start, end = _line(caption)
        if not text:
            continue
        usable.append(index)
        lines.append((text, start, end))
    if len(usable) < 2:
        _last_source = "separate"
        return _singletons(count)
    key = tuple((round(start, 2), round(end, 2), text) for text, start, end in lines)
    cached = _beat_cache.get(key)
    if cached is not None:
        groups, _last_source = cached
        return _expand(count, usable, groups)
    groups, source = _qwen_groups(lines)
    _beat_cache[key] = (groups, source)
    _last_source = source
    return _expand(count, usable, groups)


def _qwen_groups(lines):
    path = qwen_dir()
    if path is None:
        logger.warning("Qwen2.5-3B-Instruct weights are incomplete. Each caption stays its own beat.")
        return _singletons(len(lines)), "separate"
    numbered = "\n".join(f"{index}. {text}" for index, (text, _start, _end) in enumerate(lines))
    prompt = (
        "You group neighboring spoken captions into beats. "
        "You never rewrite, translate, or add words. "
        "Join a caption to the previous one only when it continues the same claim: "
        "a consequence, an example, or the same subject. "
        "A greeting, a new topic, or a call to action starts a new beat. "
        'Reply with JSON only: {"beat":[0,0,1]} with one integer per caption, in order. '
        "The first caption is beat 0. A beat id never goes backward and never skips a caption.\n\n"
        f"Captions:\n{numbered}"
    )
    try:
        text = _generate_qwen(path, prompt, max(48, 8 * len(lines)))
    except Exception as exc:
        logger.warning("Qwen beat grouping failed: %s", exc)
        return _singletons(len(lines)), "separate"
    finally:
        release_qwen()
    ids = parse_beat_ids(text, len(lines))
    if ids is None:
        logger.warning("Qwen beat reply was not a neighbor grouping. Each caption stays its own beat.")
        return _singletons(len(lines)), "separate"
    return groups_from_ids(ids), "qwen2.5-3b"


def _generate_qwen(path: Path, prompt: str, max_new_tokens: int) -> str:
    global _qwen
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if _qwen is None:
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model = AutoModelForCausalLM.from_pretrained(path, local_files_only=True, dtype=dtype)
        if torch.cuda.is_available():
            model = model.to("cuda")
        model.eval()
        _qwen = (model, tokenizer)
    model, tokenizer = _qwen
    messages = [{"role": "user", "content": prompt}]
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(rendered, return_tensors="pt")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = output[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


def release_qwen():
    global _qwen
    _qwen = None
    _empty_cuda()


def _empty_cuda():
    import gc
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        return


def content_stems(text: str) -> set:
    from app.services.title_styles import PLAIN_WORDS
    words = re.findall(r"[a-z]{4,}", (text or "").casefold())
    return {word[:5] for word in words if word not in PLAIN_WORDS}


def frame_shows_subject(located: str, description: str, subject: str) -> bool:
    """True when Florence placed the subject, or the caption names it and not only a person."""
    subject_stems = content_stems(subject)
    if not subject_stems:
        return False
    located_text = re.sub(r"<loc_\d+>", " ", located or "")
    if "<loc_" in (located or "") and subject_stems & content_stems(located_text):
        return True
    overlap = subject_stems & content_stems(description)
    person = {word[:5] for word in PERSON_WORDS}
    if subject_stems - person:
        overlap -= person
    return bool(overlap)


def subject_phrase(row) -> str:
    asset = (row or {}).get("asset") or {}
    entities = [str(item).strip() for item in asset.get("required_entities") or [] if str(item).strip()]
    if entities:
        return entities[0][:80]
    query = str(asset.get("retrieval_query") or asset.get("semantic_target") or "").strip()
    return " ".join(query.split()[:8])[:80]


def collapse_beats(items, keys) -> list:
    """Merge neighboring dialogue beats that share a key. The text stays verbatim."""
    merged = []
    for item, key in zip(items, keys):
        if merged and key is not None and key == merged[-1].get("_beat"):
            merged[-1]["end_sec"] = item["end_sec"]
            merged[-1]["text"] = (str(merged[-1]["text"]) + " " + str(item["text"])).strip()
            continue
        merged.append({**item, "_beat": key})
    for item in merged:
        item.pop("_beat", None)
    return merged


def video_path(state):
    from app.core.config import settings
    project_id = getattr(state, "id", None)
    candidates = []
    for attr in ("proxy_media_path", "source_media_path"):
        raw = getattr(state, attr, None)
        if not raw:
            continue
        candidates.append(Path(str(raw)))
        if project_id:
            candidates.append(settings.projects_dir / str(project_id) / str(raw))
    for path in candidates:
        if path.is_file():
            return path
    return None


def caption_moments(state, row) -> list:
    start = float((row or {}).get("start_sec") or 0)
    end = float((row or {}).get("end_sec") or start)
    moments = []
    for caption in getattr(state, "captions", None) or []:
        text, c_start, c_end = _line(caption)
        if not text or c_start >= end or c_end <= start:
            continue
        moments.append(max(0.0, (max(c_start, start) + min(c_end, end)) / 2))
    if not moments:
        moments.append(max(0.0, (start + end) / 2))
    unique = []
    for moment in moments:
        if not unique or abs(unique[-1] - moment) > 0.2:
            unique.append(round(moment, 3))
    return unique


def grab_frame(path: Path, moment: float):
    from PIL import Image
    from app.core.config import settings
    process = subprocess.run(
        [
            settings.ffmpeg_bin, "-v", "error", "-ss", f"{max(0.0, float(moment)):.3f}",
            "-i", str(path), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
        ],
        capture_output=True,
        timeout=25,
    )
    if process.returncode != 0 or not process.stdout:
        return None
    return Image.open(BytesIO(process.stdout)).convert("RGB")


def _load_florence():
    global _florence
    if _florence is not None:
        return _florence
    path = florence_dir()
    if path is None:
        raise FileNotFoundError("Florence-2 weights are not on this machine.")
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        path, trust_remote_code=True, local_files_only=True, dtype=dtype, attn_implementation="eager",
    )
    processor = AutoProcessor.from_pretrained(path, trust_remote_code=True, local_files_only=True)
    if torch.cuda.is_available():
        model = model.to("cuda")
    _tie_florence_embeddings(model)
    _patch_florence_cache(model)
    model.eval()
    _florence = (model, processor)
    return _florence


def _patch_florence_cache(model):
    """The bundled Florence code indexes a tuple cache. Current transformers passes a cache object."""
    language = getattr(model, "language_model", None)
    if language is None or not hasattr(language, "prepare_inputs_for_generation"):
        return
    base = language.prepare_inputs_for_generation

    def prepare_inputs_for_generation(decoder_input_ids, past_key_values=None, **kwargs):
        if past_key_values is None or isinstance(past_key_values, (tuple, list)):
            return base(decoder_input_ids, past_key_values=past_key_values, **kwargs)
        length = 0
        getter = getattr(past_key_values, "get_seq_length", None)
        if getter is not None:
            length = int(getter() or 0)
        if length:
            if decoder_input_ids.shape[1] > length:
                decoder_input_ids = decoder_input_ids[:, length:]
            else:
                decoder_input_ids = decoder_input_ids[:, -1:]
        prepared = base(decoder_input_ids, past_key_values=None, **kwargs)
        prepared["past_key_values"] = past_key_values
        prepared["decoder_input_ids"] = decoder_input_ids
        return prepared

    language.prepare_inputs_for_generation = prepare_inputs_for_generation


def _tie_florence_embeddings(model):
    """The checkpoint stores one shared matrix. Point the new embedding copies at it."""
    language = getattr(model, "language_model", None)
    inner = getattr(language, "model", None)
    shared = getattr(inner, "shared", None)
    if shared is None:
        return
    for tower in (getattr(inner, "encoder", None), getattr(inner, "decoder", None)):
        tokens = getattr(tower, "embed_tokens", None)
        if tokens is not None:
            tokens.weight = shared.weight
    head = getattr(language, "lm_head", None)
    if head is not None:
        head.weight = shared.weight


def release_vision():
    global _florence
    _florence = None
    _empty_cuda()


def _florence_text(image, prompt: str, max_new_tokens: int) -> str:
    import torch
    model, processor = _load_florence()
    inputs = processor(text=prompt, images=image, return_tensors="pt")
    weight_dtype = next(model.parameters()).dtype
    tensors = {}
    for key, value in inputs.items():
        if not hasattr(value, "to"):
            tensors[key] = value
            continue
        if getattr(value, "is_floating_point", lambda: False)():
            tensors[key] = value.to(device=model.device, dtype=weight_dtype)
        else:
            tensors[key] = value.to(model.device)
    with torch.inference_mode():
        generated = model.generate(
            **tensors, max_new_tokens=max_new_tokens, num_beams=1, do_sample=False, use_cache=False,
        )
    return processor.batch_decode(generated, skip_special_tokens=False)[0]


def describe_frame(image, subject: str) -> tuple:
    """Open-vocabulary location plus a detailed caption for one frame."""
    located = _florence_text(image, "<OPEN_VOCABULARY_DETECTION>" + subject, 64)
    description = _florence_text(image, "<DETAILED_CAPTION>", 80)
    labels = ""
    try:
        _model, processor = _florence
        parsed = processor.post_process_generation(
            located,
            task="<OPEN_VOCABULARY_DETECTION>",
            image_size=(image.width, image.height),
        )
        answer = parsed.get("<OPEN_VOCABULARY_DETECTION>") or {}
        names = list(answer.get("bboxes_labels") or []) + list(answer.get("polygons_labels") or []) + list(answer.get("labels") or [])
        boxes = list(answer.get("bboxes") or []) + list(answer.get("polygons") or [])
        if boxes and names:
            labels = " ".join(str(name) for name in names)
            located = labels + " <loc_0>"
    except Exception:
        labels = ""
    clean = re.sub(r"<[^>]+>", " ", description or "")
    return located, " ".join(clean.split()), labels


def source_already_shows(state, row) -> str | None:
    """A short reason when one source frame already shows the stock subject."""
    if not models_enabled():
        return None
    try:
        return _source_already_shows(state, row)
    except Exception as exc:
        logger.warning("Florence frame check skipped: %s", exc)
        return None


def _source_already_shows(state, row) -> str | None:
    subject = subject_phrase(row)
    path = video_path(state)
    if not subject or path is None:
        return None
    for moment in caption_moments(state, row):
        image = grab_frame(path, moment)
        if image is None:
            continue
        located, description, _labels = describe_frame(image, subject)
        if frame_shows_subject(located, description, subject):
            detail = description[:140] or subject
            return f"The source frame already shows this subject ({detail}). The speaker stays on screen."
    return None
