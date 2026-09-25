"""Unit tests for detection geometry validation."""

from backend.app.detection.detector import is_plausible_detection


FRAME_SHAPE = (480, 640, 3)


def test_vertical_phone_is_allowed() -> None:
    assert is_plausible_detection("cell phone", (200, 100, 300, 390), FRAME_SHAPE)


def test_horizontal_phone_is_allowed() -> None:
    assert is_plausible_detection("cell phone", (100, 180, 430, 330), FRAME_SHAPE)


def test_narrow_edge_box_is_rejected_as_laptop() -> None:
    assert not is_plausible_detection("laptop", (0, 150, 35, 430), FRAME_SHAPE)


def test_open_laptop_shape_is_allowed() -> None:
    assert is_plausible_detection("laptop", (110, 120, 530, 390), FRAME_SHAPE)


def test_vertical_box_is_rejected_as_tv() -> None:
    assert not is_plausible_detection("tv", (20, 50, 120, 410), FRAME_SHAPE)


def test_widescreen_tv_shape_is_allowed() -> None:
    assert is_plausible_detection("tv", (80, 80, 560, 350), FRAME_SHAPE)
