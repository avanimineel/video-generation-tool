"""Local picture index and editorial model.

Weights live outside the repo, under the Hugging Face cache and
`/data/developer/oonex/models`. One GPU model is loaded at a time.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

YOLO_NAMES = {
    "person": "face",
    "sports ball": "ball",
    "knife": "instrument",
    "scissors": "instrument",
}
GROUND_PHRASES = {
    "general": "face. hand.",
    "medical": "face. hand. surgical instrument.",
    "sports": "face. hand. ball.",
}


def weights_dir() -> Path:
    return Path(os.getenv("LOCAL_MODELS_DIR", "/data/developer/oonex/models"))


def yolo_weights() -> Path:
    return Path(os.getenv("EDITORIAL_YOLO_WEIGHTS", str(weights_dir() / "yolo11n.pt")))


def xyxy_to_center(box, width: float, height: float) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = [float(value) for value in box]
    width = max(width, 1.0)
    height = max(height, 1.0)
    return ((x1 + x2) / 2 / width, (y1 + y2) / 2 / height, max(0.0, x2 - x1) / width, max(0.0, y2 - y1) / height)


def head_box(box):
    """Upper portion of a person box, used as the face region."""
    x1, y1, x2, y2 = [float(value) for value in box]
    return (x1, y1, x2, y1 + (y2 - y1) * 0.42)


def map_yolo_label(name: str) -> Optional[str]:
    return YOLO_NAMES.get((name or "").lower())


def sample_times(cuts: list[float], duration: float, limit: int = 8) -> list[float]:
    times = [0.0]
    times.extend(float(cut) for cut in cuts)
    if duration > 1 and len(times) < 2:
        step = max(1.0, duration / limit)
        marker = 0.0
        while marker < duration and len(times) < limit:
            times.append(round(marker, 3))
            marker += step
    unique = []
    for value in times:
        if 0 <= value < duration and all(abs(value - seen) > 0.2 for seen in unique):
            unique.append(round(value, 3))
        if len(unique) >= limit:
            break
    return unique or [0.0]


def extract_frame(video: str, time_sec: float, dest: Path) -> bool:
    from app.core.config import settings
    ffmpeg = settings.ffmpeg_bin if settings.ffmpeg_bin and Path(settings.ffmpeg_bin).is_file() else "ffmpeg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{time_sec:.3f}", "-i", video, "-frames:v", "1", "-q:v", "3", str(dest), "-y"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0 and dest.is_file()


def index_picture(video: str, cuts: list[float], duration: float, domain: str, out_dir: Path) -> dict:
    """Shot keyframes, YOLO avoid boxes, Florence captions, and SigLIP vectors."""
    from PIL import Image
    frames = []
    captions = []
    embeddings = []
    times = sample_times(cuts, duration)
    for index, time_sec in enumerate(times):
        image_path = out_dir / f"frame_{index:02d}.jpg"
        if not extract_frame(video, time_sec, image_path):
            continue
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        detections = detect_frame(image, width, height, domain)
        try:
            caption = florence_caption(image)
        except Exception:
            caption = ""
        try:
            vector = siglip_embed(image)
        except Exception:
            vector = []
        frames.append({"time_sec": time_sec, "detections": detections, "caption": caption})
        captions.append({"time_sec": time_sec, "caption": caption})
        embeddings.append({"time_sec": time_sec, "vector": vector})
        release_vision()
    if embeddings:
        (out_dir / "siglip_index.json").write_text(json.dumps(embeddings), encoding="utf-8")
    return {"frames": frames, "captions": captions}


def detect_frame(image, width: int, height: int, domain: str) -> list[dict]:
    found = []
    for label, box in yolo_boxes(image):
        mapped = map_yolo_label(label)
        if mapped == "face":
            box = head_box(box)
        if not mapped:
            continue
        if mapped not in {"face", "hand", "instrument", "ball"}:
            continue
        found.append({"label": mapped, "preview_rect": [round(value, 4) for value in xyxy_to_center(box, width, height)]})
    try:
        grounded = florence_ground(image, domain)
    except Exception:
        grounded = []
    for label, box in grounded:
        found.append({"label": label, "preview_rect": [round(value, 4) for value in xyxy_to_center(box, width, height)]})
    return found


def yolo_boxes(image) -> list[tuple[str, tuple]]:
    weights = yolo_weights()
    if not weights.is_file():
        return []
    model = _yolo()
    if model is None:
        return []
    result = model.predict(image, verbose=False, device=_device())[0]
    boxes = []
    names = result.names or {}
    for box in result.boxes or []:
        name = names.get(int(box.cls), "")
        xyxy = tuple(float(value) for value in box.xyxy[0].tolist())
        boxes.append((str(name), xyxy))
    return boxes


def florence_caption(image) -> str:
    parsed = _florence(image, "<DETAILED_CAPTION>", "<DETAILED_CAPTION>")
    if isinstance(parsed, dict):
        return str(parsed.get("<DETAILED_CAPTION>") or "")
    return ""


def florence_ground(image, domain: str) -> list[tuple[str, tuple]]:
    task = "<CAPTION_TO_PHRASE_GROUNDING>"
    phrase = GROUND_PHRASES.get(domain, GROUND_PHRASES["general"])
    width, height = image.size
    parsed = _florence(image, task, task + phrase)
    data = parsed.get(task, parsed) if isinstance(parsed, dict) else {}
    labels = data.get("labels") or []
    boxes = data.get("bboxes") or []
    mapped = []
    scale_x = width / 768
    scale_y = height / 768
    for label, box in zip(labels, boxes):
        token = str(label).lower()
        if "instrument" in token or "forceps" in token or "scalpel" in token:
            name = "instrument"
        elif "hand" in token:
            name = "hand"
        elif "ball" in token:
            name = "ball"
        elif "face" in token:
            name = "face"
        else:
            continue
        x1, y1, x2, y2 = [float(value) for value in box]
        mapped.append((name, (x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y)))
    return mapped


def _tie_florence(model) -> None:
    """The safetensors file stores one shared matrix. The token tables point at it."""
    shared = model.language_model.model.shared.weight
    model.language_model.model.encoder.embed_tokens.weight = shared
    model.language_model.model.decoder.embed_tokens.weight = shared
    model.language_model.lm_head.weight = shared


def siglip_embed(image) -> list[float]:
    model, processor = _siglip()
    import torch
    inputs = processor(images=image, return_tensors="pt")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        if hasattr(features, "pooler_output"):
            features = features.pooler_output
        elif isinstance(features, tuple):
            features = features[0]
        features = features / features.norm(dim=-1, keepdim=True)
    return [round(float(value), 6) for value in features[0].detach().cpu().tolist()]


def qwen_plan(segments) -> Optional[dict]:
    """Compact JSON plan. The full director prompt is too long for one local pass."""
    brief = [{
        "id": segment.id,
        "start_sec": segment.start_sec,
        "end_sec": segment.end_sec,
        "transcript": (segment.transcript or "")[:400],
    } for segment in segments]
    prompt = (
        "Return JSON {\"decisions\": [...]} for these spoken segments. "
        "Each decision needs segment_id, intervene, rationale, strategy, start_sec, end_sec, display_text, "
        "intent, cue_kind, and scores with semantic_relevance, visual_value, information_gain, evidence_value, "
        "attention_value, redundancy, visual_fatigue, confidence. "
        "strategy is KINETIC_TYPOGRAPHY, STAT_COUNTER, or NO_INTERVENTION. "
        "display_text must be an exact contiguous phrase from transcript. No extra prose.\n"
        + json.dumps(brief, ensure_ascii=False)
    )
    return qwen_json(prompt)


def qwen_json(prompt: str) -> Optional[dict]:
    release_vision()
    global _YOLO
    _YOLO = None
    _empty_cache()
    model, tokenizer = _qwen()
    import torch
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=900, do_sample=False)
    reply = tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    start = reply.find("{")
    end = reply.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(reply[start:end + 1])
    except ValueError:
        return None


def release_vision() -> None:
    global _FLORENCE, _SIGLIP
    _FLORENCE = None
    _SIGLIP = None
    _empty_cache()


def release_planner() -> None:
    global _QWEN
    _QWEN = None
    _empty_cache()


def _device() -> str:
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _empty_cache() -> None:
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        return


_YOLO = None
_FLORENCE = None
_SIGLIP = None
_QWEN = None


def _yolo():
    global _YOLO
    if _YOLO is None:
        from ultralytics import YOLO
        _YOLO = YOLO(str(yolo_weights()))
    return _YOLO


def _patch_florence_config() -> None:
    """Transformers 5 raises on a missing forced_bos_token_id that Florence-2 reads."""
    root = Path(os.getenv("HF_HOME", "/data/developer/oonex/hf-cache"))
    needle = 'if self.forced_bos_token_id is None and kwargs.get("force_bos_token_to_be_generated", False):'
    guard = 'if not hasattr(self, "forced_bos_token_id"):\n            self.forced_bos_token_id = None\n        ' + needle
    processor_needle = "tokenizer.additional_special_tokens +"
    processor_guard = 'list(getattr(tokenizer, "extra_special_tokens", None) or getattr(tokenizer, "additional_special_tokens", [])) +'
    if not root.is_dir():
        return
    for path in list(root.rglob("configuration_florence2.py")) + list(root.rglob("processing_florence2.py")):
        text = path.read_text(encoding="utf-8")
        updated = text
        if path.name.startswith("configuration") and needle in updated and 'not hasattr(self, "forced_bos_token_id")' not in updated:
            updated = updated.replace(needle, guard, 1)
        if path.name.startswith("processing") and processor_needle in updated:
            updated = updated.replace(processor_needle, processor_guard)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def _florence(image, task: str, prompt: str):
    global _FLORENCE
    import torch
    if _FLORENCE is None:
        from transformers import AutoModelForCausalLM, AutoProcessor
        _patch_florence_config()
        name = os.getenv("FLORENCE_MODEL", "microsoft/Florence-2-large")
        dtype = torch.float16 if _device() == "cuda" else torch.float32
        model = AutoModelForCausalLM.from_pretrained(name, trust_remote_code=True, torch_dtype=dtype, attn_implementation="eager")
        processor = AutoProcessor.from_pretrained(name, trust_remote_code=True)
        model.to(_device())
        _tie_florence(model)
        model.eval()
        _FLORENCE = (model, processor, dtype)
    model, processor, dtype = _FLORENCE
    from PIL import Image
    if image.size != (768, 768):
        image = image.resize((768, 768), Image.Resampling.BICUBIC)
    inputs = processor(text=prompt, images=image, return_tensors="pt")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    if "pixel_values" in inputs:
        inputs["pixel_values"] = inputs["pixel_values"].to(dtype)
    with torch.no_grad():
        generated = model.generate(**inputs, max_new_tokens=128, num_beams=1, do_sample=False, use_cache=False)
    text = processor.batch_decode(generated, skip_special_tokens=False)[0]
    return processor.post_process_generation(text, task=task, image_size=image.size)


def _siglip():
    global _SIGLIP
    if _SIGLIP is None:
        import torch
        from transformers import AutoModel, AutoProcessor
        name = os.getenv("SIGLIP_MODEL", "google/siglip-so400m-patch14-384")
        dtype = torch.float16 if _device() == "cuda" else torch.float32
        model = AutoModel.from_pretrained(name, torch_dtype=dtype).to(_device())
        model.eval()
        processor = AutoProcessor.from_pretrained(name)
        _SIGLIP = (model, processor)
    return _SIGLIP


def _qwen():
    global _QWEN
    if _QWEN is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        name = os.getenv("QWEN_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
        tokenizer = AutoTokenizer.from_pretrained(name)
        model = AutoModelForCausalLM.from_pretrained(name, quantization_config=quant, device_map="auto")
        model.eval()
        _QWEN = (model, tokenizer)
    return _QWEN
