"""Measure warmed ProctorVision inference without using the webcam."""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings  # noqa: E402
from backend.app.detection.detector import DeviceDetector  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark the model selected by ProctorVision."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of measured frames after warm-up (default: 5).",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if arguments.runs < 1:
        raise SystemExit("--runs must be at least 1")

    detector = DeviceDetector(settings)
    detector.load()
    random = np.random.default_rng(42)
    samples: list[float] = []
    for _ in range(arguments.runs):
        frame = random.integers(
            0,
            256,
            size=(settings.image_size, settings.image_size, 3),
            dtype=np.uint8,
        )
        samples.append(detector.detect(frame).inference_ms)

    status = detector.status()
    print(f"Model: {status['model_name']}")
    print(f"Runtime: {status['runtime']}")
    print(f"Path: {status['model_path']}")
    print(f"Warm-up: {status['warmup_ms']} ms")
    print(f"Samples: {', '.join(f'{value:.0f}' for value in samples)} ms")
    print(f"Median: {statistics.median(samples):.0f} ms")
    print(f"Maximum: {max(samples):.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
