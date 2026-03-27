"""Tests for camera alignment helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset_tools.camera_alignment import (  # noqa: E402
    compute_alignment_error,
    get_status_color,
    normalize_camera_source,
)
from dataset_tools.opencv_utils import (  # noqa: E402
    opencv_has_gui_support,
    path_has_cv2_module,
)


def test_compute_alignment_error_averages_marker_corner_distance():
    reference = {
        1: np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float32),
    }
    detected = {
        1: np.array([[1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0]], dtype=np.float32),
    }

    error, status = compute_alignment_error(reference, detected)

    assert error == 1.0
    assert status == "Error: 1.00px (IDs:[1])"


def test_compute_alignment_error_handles_missing_reference_and_missing_targets():
    error, status = compute_alignment_error(None, {})
    assert error is None
    assert status == "No Reference (Press 's')"

    reference = {
        7: np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float32),
    }
    error, status = compute_alignment_error(reference, {})
    assert error is None
    assert status == "All Markers Lost"

    error, status = compute_alignment_error(reference, {1: reference[7]})
    assert error is None
    assert status == "Target IDs [7] not found"


def test_get_status_color_uses_expected_thresholds():
    assert get_status_color(None) == (0, 255, 255)
    assert get_status_color(2.99) == (0, 255, 0)
    assert get_status_color(3.0) == (0, 0, 255)


def test_normalize_camera_source_supports_video_device():
    assert normalize_camera_source("0") == 0
    assert normalize_camera_source("/dev/video2") == "/dev/video2"


def test_path_has_cv2_module_handles_binary_extension_layout(tmp_path):
    assert path_has_cv2_module(tmp_path) is False

    (tmp_path / "cv2.cpython-310-x86_64-linux-gnu.so").write_text("")

    assert path_has_cv2_module(tmp_path) is True


def test_opencv_has_gui_support_parses_build_information():
    class DummyOpenCV:
        def __init__(self, build_information: str):
            self.build_information = build_information

        def getBuildInformation(self) -> str:
            return self.build_information

    assert opencv_has_gui_support(DummyOpenCV("GUI: GTK3")) is True
    assert opencv_has_gui_support(DummyOpenCV("GUI: NONE")) is False
