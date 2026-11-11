"""Resolve Whisper runtime device / compute type for CPU and CUDA hosts."""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional, Tuple

# Optional structured logger — keep import soft so unit tests need no FastAPI stack.
try:
    from app.core.logging_setup import format_exception_detail, get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover
    logger = None

    def format_exception_detail(exc, *, limit=1500):  # type: ignore
        return {"type": type(exc).__name__, "message": str(exc)}


def cuda_device_count(probe: Optional[Callable[[], int]] = None) -> int:
    """Return CTranslate2 CUDA device count (0 when unavailable)."""
    if probe is not None:
        try:
            return max(0, int(probe()))
        except Exception:
            return 0
    try:
        import ctranslate2

        return max(0, int(ctranslate2.get_cuda_device_count()))
    except Exception:
        return 0


def default_compute_type(device: str) -> str:
    """float16 on CUDA, int8 on CPU — overridable via WHISPER_COMPUTE_TYPE."""
    override = (os.getenv("WHISPER_COMPUTE_TYPE") or "").strip()
    if override:
        return override
    return "float16" if device == "cuda" else "int8"


def resolve_whisper_device(
    preference: Optional[str] = None,
    *,
    cuda_count: Optional[int] = None,
    cuda_probe: Optional[Callable[[], int]] = None,
) -> Tuple[str, str, Optional[str]]:
    """Pick Whisper device and compute type.

    Returns ``(device, compute_type, fallback_reason)``.
    ``fallback_reason`` is set when CUDA was desired but CPU is used instead.

    Env:
      WHISPER_DEVICE=auto|cuda|cpu (default auto)
      WHISPER_COMPUTE_TYPE — optional explicit compute type
    """
    requested = (preference or os.getenv("WHISPER_DEVICE") or "auto").strip().lower()
    if requested not in ("auto", "cuda", "cpu"):
        requested = "auto"

    available = cuda_count if cuda_count is not None else cuda_device_count(cuda_probe)

    if requested == "cpu":
        device = "cpu"
        reason = None
    elif requested == "cuda":
        if available > 0:
            device = "cuda"
            reason = None
        else:
            device = "cpu"
            reason = "cuda_requested_but_unavailable"
    else:  # auto
        if available > 0:
            device = "cuda"
            reason = None
        else:
            device = "cpu"
            reason = "no_cuda_devices"

    return device, default_compute_type(device), reason


def whisper_cache_key(model_size: str, device: str, compute_type: str) -> str:
    return f"{model_size}:{device}:{compute_type}"


def describe_selection(device: str, compute_type: str, reason: Optional[str] = None) -> Dict[str, Any]:
    return {
        "device": device,
        "compute_type": compute_type,
        "fallback_reason": reason,
        "whisper_device_env": (os.getenv("WHISPER_DEVICE") or "auto").strip().lower() or "auto",
    }


def load_whisper_model(
    model_size: str,
    *,
    preference: Optional[str] = None,
    cuda_count: Optional[int] = None,
    model_factory: Optional[Callable[..., Any]] = None,
    cpu_threads: Optional[int] = None,
) -> Tuple[Any, str, str, Optional[str]]:
    """Construct a WhisperModel with CUDA→CPU fallback.

    Returns ``(model, device, compute_type, fallback_reason)``.
    ``model_factory`` defaults to ``faster_whisper.WhisperModel`` (injectable for tests).
    """
    device, compute_type, reason = resolve_whisper_device(preference, cuda_count=cuda_count)
    factory = model_factory
    if factory is None:
        from faster_whisper import WhisperModel as factory  # type: ignore

    threads = cpu_threads if cpu_threads is not None else min(8, max(4, os.cpu_count() or 4))

    def _construct(dev: str, ctype: str) -> Any:
        kwargs: Dict[str, Any] = {"device": dev, "compute_type": ctype, "num_workers": 1}
        if dev == "cpu":
            kwargs["cpu_threads"] = threads
        return factory(model_size, **kwargs)

    try:
        model = _construct(device, compute_type)
        if logger:
            logger.info(
                "whisper_device_selected",
                event="whisper_device_selected",
                model_size=model_size,
                device=device,
                compute_type=compute_type,
                fallback_reason=reason,
                whisper_device_env=(os.getenv("WHISPER_DEVICE") or "auto"),
            )
        return model, device, compute_type, reason
    except Exception as exc:
        if device != "cuda":
            raise
        cpu_device, cpu_compute, _ = resolve_whisper_device("cpu")
        if logger:
            logger.warning(
                "whisper_cuda_fallback",
                event="whisper_cuda_fallback",
                model_size=model_size,
                device=cpu_device,
                compute_type=cpu_compute,
                fallback_reason="cuda_init_failed",
                error_detail=format_exception_detail(exc),
            )
        model = _construct(cpu_device, cpu_compute)
        if logger:
            logger.info(
                "whisper_device_selected",
                event="whisper_device_selected",
                model_size=model_size,
                device=cpu_device,
                compute_type=cpu_compute,
                fallback_reason="cuda_init_failed",
                whisper_device_env=(os.getenv("WHISPER_DEVICE") or "auto"),
            )
        return model, cpu_device, cpu_compute, "cuda_init_failed"
