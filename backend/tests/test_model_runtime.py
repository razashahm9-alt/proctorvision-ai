"""Tests for accelerated-model selection and prediction arguments."""

from pathlib import Path

import numpy as np

from backend.app.core.config import Settings
from backend.app.detection import detector as detector_module
from backend.app.detection.detector import DeviceDetector


class FakeResult:
    boxes = []


class FakeModel:
    names = {
        62: "tv",
        63: "laptop",
        67: "cell phone",
    }

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def predict(self, **arguments):
        self.calls.append(arguments)
        return [FakeResult()]


def make_settings(
    pytorch_path: Path,
    openvino_path: Path,
    *,
    prefer_openvino: bool = True,
) -> Settings:
    return Settings(
        _env_file=None,
        model_path=pytorch_path,
        openvino_model_path=openvino_path,
        prefer_openvino=prefer_openvino,
        preload_model=False,
        warmup_model=True,
    )


def test_model_selection_prefers_openvino_and_falls_back_safely(
    tmp_path: Path,
) -> None:
    pytorch_path = tmp_path / "yolo11s.pt"
    pytorch_path.touch()
    openvino_path = tmp_path / "yolo11s_openvino_model"
    settings = make_settings(pytorch_path, openvino_path)

    assert settings.selected_model_path == pytorch_path
    assert settings.selected_model_runtime == "PyTorch CPU"

    openvino_path.mkdir()
    (openvino_path / "yolo11s.xml").touch()
    (openvino_path / "yolo11s.bin").touch()

    assert settings.selected_model_path == openvino_path
    assert settings.selected_model_runtime == "OpenVINO CPU"


def test_openvino_warmup_and_detection_omit_pytorch_device_argument(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pytorch_path = tmp_path / "yolo11s.pt"
    pytorch_path.touch()
    openvino_path = tmp_path / "yolo11s_openvino_model"
    openvino_path.mkdir()
    (openvino_path / "yolo11s.xml").touch()
    (openvino_path / "yolo11s.bin").touch()
    settings = make_settings(pytorch_path, openvino_path)
    fake_model = FakeModel()
    monkeypatch.setattr(detector_module, "YOLO", lambda _path: fake_model)
    detector = DeviceDetector(settings)

    detector.load()
    response = detector.detect(np.zeros((240, 416, 3), dtype=np.uint8))

    assert len(fake_model.calls) == 2
    assert "device" not in fake_model.calls[0]
    assert "device" not in fake_model.calls[1]
    assert detector.status()["using_fallback"] is False
    assert detector.status()["warmup_ms"] is not None
    assert response.runtime == "OpenVINO CPU"
    assert response.model_name == "yolo11s"


def test_pytorch_fallback_keeps_explicit_cpu_device(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pytorch_path = tmp_path / "yolo11s.pt"
    pytorch_path.touch()
    settings = make_settings(
        pytorch_path,
        tmp_path / "missing_openvino_model",
    )
    fake_model = FakeModel()
    monkeypatch.setattr(detector_module, "YOLO", lambda _path: fake_model)
    detector = DeviceDetector(settings)

    detector.load()

    assert fake_model.calls[0]["device"] == "cpu"
    assert detector.status()["using_fallback"] is True
    assert detector.runtime == "PyTorch CPU"


def test_failed_openvino_initialization_falls_back_to_pytorch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pytorch_path = tmp_path / "yolo11s.pt"
    pytorch_path.touch()
    openvino_path = tmp_path / "yolo11s_openvino_model"
    openvino_path.mkdir()
    (openvino_path / "yolo11s.xml").touch()
    (openvino_path / "yolo11s.bin").touch()
    settings = make_settings(pytorch_path, openvino_path)
    fake_model = FakeModel()

    def fake_yolo(path: str):
        if path == str(openvino_path):
            raise RuntimeError("OpenVINO runtime unavailable")
        return fake_model

    monkeypatch.setattr(detector_module, "YOLO", fake_yolo)
    detector = DeviceDetector(settings)

    detector.load()

    assert detector.model_path == pytorch_path
    assert detector.runtime == "PyTorch CPU"
    assert detector.status()["using_fallback"] is True
    assert fake_model.calls[0]["device"] == "cpu"
