"""Local Hindi→English NMT (NLLB-200 distilled) for offline / EC2 captions.

Model download (once per host)::

    # Default model (~1.2GB). First translate call also auto-downloads via Hugging Face.
    python3 -c "from transformers import AutoModelForSeq2SeqLM, AutoTokenizer; \\
        AutoTokenizer.from_pretrained('facebook/nllb-200-distilled-600M'); \\
        AutoModelForSeq2SeqLM.from_pretrained('facebook/nllb-200-distilled-600M')"

Env:
  LOCAL_TRANSLATION_MODEL  (default facebook/nllb-200-distilled-600M)
  LOCAL_TRANSLATION_DEVICE auto|cuda|cpu  (default auto)
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable, List, Optional, Sequence

try:
    from app.core.logging_setup import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover — Phase A logging helper may not be merged yet
    import logging

    logger = logging.getLogger(__name__)

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")

# Lazy singleton
_MODEL = None
_TOKENIZER = None
_LOADED_KEY: Optional[str] = None


def is_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI.search(text or ""))


def resolve_local_device(preference: Optional[str] = None) -> str:
    requested = (preference or os.getenv("LOCAL_TRANSLATION_DEVICE") or "auto").strip().lower()
    if requested in ("cpu", "cuda"):
        if requested == "cuda":
            try:
                import torch

                return "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                return "cpu"
        return "cpu"
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def default_model_name() -> str:
    return (os.getenv("LOCAL_TRANSLATION_MODEL") or "facebook/nllb-200-distilled-600M").strip()


def _log(event: str, **fields: Any) -> None:
    try:
        logger.info(event, event=event, **fields)
    except TypeError:
        logger.info("%s %s", event, fields)


def get_nllb(model_name: Optional[str] = None, device: Optional[str] = None):
    """Load (or return cached) NLLB tokenizer + model."""
    global _MODEL, _TOKENIZER, _LOADED_KEY
    name = model_name or default_model_name()
    dev = device or resolve_local_device()
    key = f"{name}:{dev}"
    if _MODEL is not None and _TOKENIZER is not None and _LOADED_KEY == key:
        return _TOKENIZER, _MODEL, dev

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    _log("local_translation_model_loading", model=name, device=dev)
    tokenizer = AutoTokenizer.from_pretrained(name)
    model = AutoModelForSeq2SeqLM.from_pretrained(name)
    if dev == "cuda":
        model = model.to("cuda")
    model.eval()
    _TOKENIZER, _MODEL, _LOADED_KEY = tokenizer, model, key
    _log("local_translation_model_ready", model=name, device=dev)
    return tokenizer, model, dev


def clear_local_translation_cache() -> None:
    global _MODEL, _TOKENIZER, _LOADED_KEY
    _MODEL = _TOKENIZER = None
    _LOADED_KEY = None


def _translate_one(
    text: str,
    tokenizer,
    model,
    device: str,
    *,
    src_lang: str = "hin_Deva",
    tgt_lang: str = "eng_Latn",
    max_new_tokens: int = 128,
) -> str:
    import torch

    # transformers NLLB: set src_lang on tokenizer when available
    if hasattr(tokenizer, "src_lang"):
        tokenizer.src_lang = src_lang
    encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
    if device == "cuda":
        encoded = {k: v.to("cuda") for k, v in encoded.items()}
    forced = None
    if hasattr(tokenizer, "lang_code_to_id") and tgt_lang in tokenizer.lang_code_to_id:
        forced = tokenizer.lang_code_to_id[tgt_lang]
    elif hasattr(tokenizer, "convert_tokens_to_ids"):
        # Newer tokenizers expose language codes as tokens.
        tok_id = tokenizer.convert_tokens_to_ids(tgt_lang)
        if tok_id is not None and tok_id != getattr(tokenizer, "unk_token_id", None):
            forced = tok_id
    gen_kwargs = {"max_new_tokens": max_new_tokens}
    if forced is not None:
        gen_kwargs["forced_bos_token_id"] = forced
    with torch.no_grad():
        generated = model.generate(**encoded, **gen_kwargs)
    out = tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()
    return out


def translate_lines_local(
    texts: Sequence[str],
    *,
    model_name: Optional[str] = None,
    device: Optional[str] = None,
    translate_fn: Optional[Callable[[str], str]] = None,
) -> List[str]:
    """Translate subtitle fragments to English. Never invents empty placeholders.

    Lines without Devanagari are returned unchanged (already Latin / English / Hinglish
    left for optional Gemini upgrade). Devanagari lines go through NLLB hin_Deva→eng_Latn.
    """
    if not texts:
        return []

    if translate_fn is None:
        tokenizer, model, dev = get_nllb(model_name, device)

        def translate_fn(line: str) -> str:  # type: ignore
            return _translate_one(line, tokenizer, model, dev)

    results: List[str] = []
    for raw in texts:
        text = (raw or "").strip()
        if not text:
            raise ValueError("Local translation refused an empty subtitle line; original speech is saved.")
        if not is_devanagari(text):
            results.append(text)
            continue
        out = (translate_fn(text) or "").strip()
        if not out or not any(c.isalnum() for c in out) or is_devanagari(out):
            raise ValueError(
                "Local translation produced unusable English for a Devanagari line; "
                "original speech is saved."
            )
        results.append(out)
    return results
