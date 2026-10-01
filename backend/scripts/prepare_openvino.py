"""Export YOLO11s to an FP32 OpenVINO model for faster Intel CPU inference."""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def is_complete_openvino_export(path: Path) -> bool:
    return (
        path.is_dir()
        and any(path.glob("*.xml"))
        and any(path.glob("*.bin"))
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a YOLO .pt model to OpenVINO FP32. ProctorVision will "
            "select the exported directory automatically on its next start."
        )
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "yolo11s.pt",
        help="Source YOLO .pt path (default: project-root/yolo11s.pt).",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=416,
        help="Square inference size used by the app (default: 416).",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    model_path = arguments.model.resolve()
    if not model_path.is_file():
        raise SystemExit(f"Source model not found: {model_path}")

    expected_output = model_path.with_name(
        f"{model_path.stem}_openvino_model"
    )
    if is_complete_openvino_export(expected_output):
        print(f"OpenVINO model already exists: {expected_output}")
        print("No export was needed.")
        return 0
    if expected_output.exists():
        raise SystemExit(
            "An incomplete OpenVINO export already exists at "
            f"{expected_output}. Rename that folder, then run this command again."
        )

    print(f"Exporting {model_path.name} to OpenVINO FP32...")
    exported = YOLO(str(model_path)).export(
        format="openvino",
        imgsz=arguments.image_size,
        dynamic=False,
        batch=1,
    )
    exported_path = Path(str(exported)).resolve()
    if not exported_path.exists():
        raise SystemExit(
            f"Ultralytics reported an export, but no output exists at {exported_path}"
        )

    print(f"OpenVINO model ready: {exported_path}")
    print("Restart the backend; ProctorVision will select it automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
