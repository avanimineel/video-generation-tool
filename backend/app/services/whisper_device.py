"""Resolve Whisper runtime device / compute type for CPU and CUDA hosts."""
from __future__ import annotations

import ctypes
import ctypes.util
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def format_exception_detail(exc: BaseException, *, limit: int = 1500) -> Dict[str, Any]:
    return {"type": type(exc).__name__, "message": str(exc)[:limit]}


def is_cublas_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "cublas" in text or "libcublas" in text


def classify_cuda_fallback(exc: BaseException) -> str:
    return "missing_libcublas" if is_cublas_error(exc) else "cuda_init_failed"


def libcublas_available(
    *,
    loader: Optional[Callable[[str], Any]] = None,
    find_library: Optional[Callable[[str], Optional[str]]] = None,
) -> bool:
    """True when CUDA 12 cuBLAS (or a discoverable libcublas) can be loaded.

    CTranslate2 reports CUDA devices from the driver even when the CUDA *toolkit*
    libs (libcublas.so.12) are missing — common on Amazon Linux GPU AMIs. VAD may
    still run via ONNX; decode then fails with RuntimeError about libcublas.
    """
    load = loader or ctypes.CDLL
    find = find_library or ctypes.util.find_library
    for name in ("libcublas.so.12", "libcublas.so"):
        try:
            load(name)
            return True
        except OSError:
            continue
    if find("cublas") or find("cublasLt"):
        return True
    search_dirs = [
        Path("/usr/local/cuda/lib64"),
        Path("/usr/lib64"),
        Path("/usr/local/cuda/targets/x86_64-linux/lib"),
    ]
    search_dirs.extend(sorted(Path("/usr/local").glob("cuda-12*/lib64")))
    for directory in search_dirs:
        try:
            if any(directory.glob("libcublas.so*")):
                return True
        except OSError:
            continue
    return False


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
    cublas_ok: Optional[bool] = None,
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
    has_cublas = libcublas_available() if cublas_ok is None else cublas_ok

    if requested == "cpu":
        return "cpu", default_compute_type("cpu"), None

    if available <= 0:
        reason = "cuda_requested_but_unavailable" if requested == "cuda" else "no_cuda_devices"
        return "cpu", default_compute_type("cpu"), reason

    if not has_cublas:
        # Driver/device present but toolkit libs missing — do not select CUDA.
        return "cpu", default_compute_type("cpu"), "missing_libcublas"

    return "cuda", default_compute_type("cuda"), None


def whisper_cache_key(model_size: str, device: str, compute_type: str) -> str:
    return f"{model_size}:{device}:{compute_type}"


def describe_selection(device: str, compute_type: str, reason: Optional[str] = None) -> Dict[str, Any]:
    return {
        "device": device,
        "compute_type": compute_type,
        "fallback_reason": reason,
        "whisper_device_env": (os.getenv("WHISPER_DEVICE") or "auto").strip().lower() or "auto",
    }


def log_cuda_fallback(
    model_size: str,
    device: str,
    compute_type: str,
    reason: str,
    exc: Optional[BaseException] = None,
):
    """Emit structured whisper_cuda_fallback (reason e.g. missing_libcublas)."""
    extra = {
        "event": "whisper_cuda_fallback",
        "model_size": model_size,
        "device": device,
        "compute_type": compute_type,
        "fallback_reason": reason,
    }
    if exc is not None:
        extra["error_detail"] = format_exception_detail(exc)
    logger.warning(
        "whisper_cuda_fallback reason=%s device=%s compute_type=%s model_size=%s",
        reason,
        device,
        compute_type,
        model_size,
        extra=extra,
    )


def load_whisper_model(
    model_size: str,
    *,
    preference: Optional[str] = None,
    cuda_count: Optional[int] = None,
    cublas_ok: Optional[bool] = None,
    model_factory: Optional[Callable[..., Any]] = None,
    cpu_threads: Optional[int] = None,
) -> Tuple[Any, str, str, Optional[str]]:
    """Construct a WhisperModel with CUDA→CPU fallback.

    Returns ``(model, device, compute_type, fallback_reason)``.
    """
    device, compute_type, reason = resolve_whisper_device(
        preference, cuda_count=cuda_count, cublas_ok=cublas_ok
    )
    factory = model_factory
    if factory is None:
        from faster_whisper import WhisperModel as factory  # type: ignore

    threads = cpu_threads if cpu_threads is not None else min(8, max(4, os.cpu_count() or 4))

    def _construct(dev: str, ctype: str) -> Any:
        kwargs: Dict[str, Any] = {"device": dev, "compute_type": ctype, "num_workers": 1}
        if dev == "cpu":
            kwargs["cpu_threads"] = threads
        return factory(model_size, **kwargs)

    if reason == "missing_libcublas":
        log_cuda_fallback(model_size, "cpu", compute_type, "missing_libcublas")

    try:
        model = _construct(device, compute_type)
        logger.info(
            "whisper_device_selected device=%s compute_type=%s model_size=%s fallback_reason=%s",
            device,
            compute_type,
            model_size,
            reason,
            extra={
                "event": "whisper_device_selected",
                "model_size": model_size,
                "device": device,
                "compute_type": compute_type,
                "fallback_reason": reason,
                "whisper_device_env": (os.getenv("WHISPER_DEVICE") or "auto"),
            },
        )
        return model, device, compute_type, reason
    except Exception as exc:
        if device != "cuda":
            raise
        fallback_reason = classify_cuda_fallback(exc)
        cpu_device, cpu_compute, _ = resolve_whisper_device("cpu")
        log_cuda_fallback(model_size, cpu_device, cpu_compute, fallback_reason, exc)
        model = _construct(cpu_device, cpu_compute)
        logger.info(
            "whisper_device_selected device=%s compute_type=%s model_size=%s fallback_reason=%s",
            cpu_device,
            cpu_compute,
            model_size,
            fallback_reason,
            extra={
                "event": "whisper_device_selected",
                "model_size": model_size,
                "device": cpu_device,
                "compute_type": cpu_compute,
                "fallback_reason": fallback_reason,
                "whisper_device_env": (os.getenv("WHISPER_DEVICE") or "auto"),
            },
        )
        return model, cpu_device, cpu_compute, fallback_reason
