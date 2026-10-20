"""Unit tests for Whisper CUDA/CPU device selection (mocked CUDA availability)."""
import pytest

from app.services.whisper_device import (
    default_compute_type,
    resolve_whisper_device,
    whisper_cache_key,
)


@pytest.mark.parametrize(
    "preference,cuda_count,expected_device,expect_reason",
    [
        ("auto", 1, "cuda", None),
        ("auto", 0, "cpu", "no_cuda_devices"),
        ("cuda", 2, "cuda", None),
        ("cuda", 0, "cpu", "cuda_requested_but_unavailable"),
        ("cpu", 4, "cpu", None),
        ("cpu", 0, "cpu", None),
        ("bogus", 1, "cuda", None),  # invalid → auto
        ("bogus", 0, "cpu", "no_cuda_devices"),
    ],
)
def test_resolve_whisper_device_matrix(preference, cuda_count, expected_device, expect_reason, monkeypatch):
    monkeypatch.delenv("WHISPER_COMPUTE_TYPE", raising=False)
    monkeypatch.delenv("WHISPER_DEVICE", raising=False)
    device, compute, reason = resolve_whisper_device(preference, cuda_count=cuda_count)
    assert device == expected_device
    assert reason == expect_reason
    assert compute == ("float16" if expected_device == "cuda" else "int8")


def test_whisper_compute_type_env_override(monkeypatch):
    monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "int8_float16")
    assert default_compute_type("cuda") == "int8_float16"
    assert default_compute_type("cpu") == "int8_float16"


def test_resolve_reads_whisper_device_env(monkeypatch):
    monkeypatch.setenv("WHISPER_DEVICE", "cpu")
    monkeypatch.delenv("WHISPER_COMPUTE_TYPE", raising=False)
    device, compute, reason = resolve_whisper_device(cuda_count=8)
    assert device == "cpu"
    assert compute == "int8"
    assert reason is None


def test_cuda_probe_callable_used(monkeypatch):
    monkeypatch.delenv("WHISPER_DEVICE", raising=False)
    monkeypatch.delenv("WHISPER_COMPUTE_TYPE", raising=False)
    calls = []

    def probe():
        calls.append(1)
        return 1

    device, _, reason = resolve_whisper_device("auto", cuda_probe=probe)
    assert device == "cuda"
    assert reason is None
    assert calls == [1]


def test_whisper_cache_key_includes_device_and_compute():
    assert whisper_cache_key("small", "cuda", "float16") == "small:cuda:float16"
    assert whisper_cache_key("small", "cpu", "int8") != whisper_cache_key("small", "cuda", "float16")


def test_load_whisper_model_falls_back_when_cuda_init_fails(monkeypatch):
    """If CUDA WhisperModel construction fails, load CPU and report fallback reason."""
    from app.services.whisper_device import load_whisper_model

    monkeypatch.setenv("WHISPER_DEVICE", "cuda")
    monkeypatch.delenv("WHISPER_COMPUTE_TYPE", raising=False)

    loads = []

    class FakeModel:
        def __init__(self, size, **kwargs):
            loads.append(dict(kwargs))
            if kwargs.get("device") == "cuda":
                raise RuntimeError("CUDA driver mismatch")
            self.size = size

    model, device, compute, reason = load_whisper_model(
        "base",
        preference="cuda",
        cuda_count=1,
        model_factory=FakeModel,
    )
    assert model is not None
    assert device == "cpu"
    assert compute == "int8"
    assert reason == "cuda_init_failed"
    assert any(c.get("device") == "cuda" for c in loads)
    assert any(c.get("device") == "cpu" for c in loads)
