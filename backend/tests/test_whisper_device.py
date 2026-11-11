"""Unit tests for Whisper CUDA/CPU device selection and cuBLAS probing."""
import pytest

from app.services.whisper_device import (
    classify_cuda_fallback,
    default_compute_type,
    is_cublas_error,
    libcublas_available,
    resolve_whisper_device,
    whisper_cache_key,
)


@pytest.mark.parametrize(
    "preference,cuda_count,cublas_ok,expected_device,expect_reason",
    [
        ("auto", 1, True, "cuda", None),
        ("auto", 0, True, "cpu", "no_cuda_devices"),
        ("auto", 1, False, "cpu", "missing_libcublas"),
        ("cuda", 2, True, "cuda", None),
        ("cuda", 0, True, "cpu", "cuda_requested_but_unavailable"),
        ("cuda", 1, False, "cpu", "missing_libcublas"),
        ("cpu", 4, True, "cpu", None),
        ("cpu", 0, False, "cpu", None),
        ("bogus", 1, True, "cuda", None),
        ("bogus", 0, True, "cpu", "no_cuda_devices"),
    ],
)
def test_resolve_whisper_device_matrix(
    preference, cuda_count, cublas_ok, expected_device, expect_reason, monkeypatch
):
    monkeypatch.delenv("WHISPER_COMPUTE_TYPE", raising=False)
    monkeypatch.delenv("WHISPER_DEVICE", raising=False)
    device, compute, reason = resolve_whisper_device(
        preference, cuda_count=cuda_count, cublas_ok=cublas_ok
    )
    assert device == expected_device
    assert reason == expect_reason
    assert compute == ("float16" if expected_device == "cuda" else "int8")


def test_whisper_compute_type_env_override(monkeypatch):
    monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "int8_float16")
    assert default_compute_type("cuda") == "int8_float16"
    assert default_compute_type("cpu") == "int8_float16"


def test_libcublas_probe_uses_loader(monkeypatch):
    calls = []

    def loader(name):
        calls.append(name)
        if name == "libcublas.so.12":
            raise OSError("not found")
        raise OSError("not found")

    assert libcublas_available(loader=loader, find_library=lambda _n: None) is False
    assert "libcublas.so.12" in calls


def test_libcublas_probe_succeeds_on_so12():
    def loader(name):
        if name != "libcublas.so.12":
            raise OSError("no")
        return object()

    assert libcublas_available(loader=loader, find_library=lambda _n: None) is True


def test_cublas_error_classification():
    err = RuntimeError("Library libcublas.so.12 is not found or cannot be loaded")
    assert is_cublas_error(err)
    assert classify_cuda_fallback(err) == "missing_libcublas"
    assert classify_cuda_fallback(RuntimeError("CUDA driver mismatch")) == "cuda_init_failed"


def test_load_whisper_model_falls_back_on_cublas_init_failure(monkeypatch):
    from app.services.whisper_device import load_whisper_model

    monkeypatch.setenv("WHISPER_DEVICE", "cuda")
    monkeypatch.delenv("WHISPER_COMPUTE_TYPE", raising=False)
    loads = []

    class FakeModel:
        def __init__(self, size, **kwargs):
            loads.append(dict(kwargs))
            if kwargs.get("device") == "cuda":
                raise RuntimeError("Library libcublas.so.12 is not found or cannot be loaded")
            self.size = size

    model, device, compute, reason = load_whisper_model(
        "base",
        preference="cuda",
        cuda_count=1,
        cublas_ok=True,  # probe said ok; construction still fails → runtime fallback
        model_factory=FakeModel,
    )
    assert model is not None
    assert device == "cpu"
    assert compute == "int8"
    assert reason == "missing_libcublas"
    assert any(c.get("device") == "cuda" for c in loads)
    assert any(c.get("device") == "cpu" for c in loads)


def test_resolve_skips_cuda_when_cublas_missing_before_construct(monkeypatch):
    from app.services.whisper_device import load_whisper_model

    monkeypatch.delenv("WHISPER_DEVICE", raising=False)
    monkeypatch.delenv("WHISPER_COMPUTE_TYPE", raising=False)
    loads = []

    class FakeModel:
        def __init__(self, size, **kwargs):
            loads.append(dict(kwargs))
            self.size = size

    model, device, compute, reason = load_whisper_model(
        "base",
        preference="auto",
        cuda_count=1,
        cublas_ok=False,
        model_factory=FakeModel,
    )
    assert device == "cpu"
    assert reason == "missing_libcublas"
    assert all(c.get("device") == "cpu" for c in loads)
    assert model is not None
    assert compute == "int8"


def test_whisper_cache_key_includes_device_and_compute():
    assert whisper_cache_key("small", "cuda", "float16") == "small:cuda:float16"
    assert whisper_cache_key("small", "cpu", "int8") != whisper_cache_key("small", "cuda", "float16")


def test_decode_time_cublas_fallback_retries_cpu(monkeypatch, tmp_path):
    """VAD/info can succeed on CUDA; decode then raises libcublas — retry on CPU."""
    from app.services.transcription_service import TranscriptionService

    TranscriptionService.clear_whisper_model_cache()
    media = tmp_path / "clip.wav"
    media.write_bytes(b"RIFF")

    class Seg:
        def __init__(self):
            self.start = 0.0
            self.end = 1.0
            self.text = "hello world"
            self.words = None
            self.no_speech_prob = 0.0
            self.avg_logprob = -0.1
            self.compression_ratio = 1.0

    class Info:
        language = "en"

    class CudaModel:
        def transcribe(self, *a, **kw):
            raise RuntimeError("Library libcublas.so.12 is not found or cannot be loaded")

    class CpuModel:
        def transcribe(self, *a, **kw):
            return [Seg()], Info()

    calls = {"n": 0}

    def fake_get(cls, model_size=None, *, force_device=None):
        calls["n"] += 1
        if force_device == "cpu" or calls["n"] > 1:
            model = CpuModel()
            key = f"{model_size or 'base'}:cpu:int8"
            cls._whisper_models[key] = model
            cls._whisper_model_devices[key] = "cpu"
            return model
        model = CudaModel()
        key = f"{model_size or 'base'}:cuda:float16"
        cls._whisper_models[key] = model
        cls._whisper_model_devices[key] = "cuda"
        return model

    monkeypatch.setattr(TranscriptionService, "get_whisper_model", classmethod(fake_get))
    svc = TranscriptionService()
    lang, captions = svc.transcribe_with_whisper(str(media), task="transcribe", model_size="base")
    assert lang == "en"
    assert len(captions) >= 1
    assert "hello" in captions[0].text.lower()
