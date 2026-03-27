"""Camera alignment helper based on ArUco markers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from dataset_tools.opencv_utils import require_opencv_gui

YELLOW = (0, 255, 255)
GREEN = (0, 255, 0)
RED = (0, 0, 255)

cv2 = None


def get_status_color(error_value: float | None) -> tuple[int, int, int]:
    """Map alignment error to a UI color."""
    if error_value is None:
        return YELLOW
    if error_value < 3.0:
        return GREEN
    return RED


def compute_alignment_error(
    reference_data: dict[int, np.ndarray] | None,
    detected_markers: dict[int, np.ndarray],
) -> tuple[float | None, str]:
    """Compute average marker corner error against saved reference data."""
    if reference_data is None:
        return None, "No Reference (Press 's')"
    if not detected_markers:
        return None, "All Markers Lost"

    errors: list[float] = []
    matched_ids: list[int] = []

    for marker_id, reference_corners in reference_data.items():
        detected_corners = detected_markers.get(marker_id)
        if detected_corners is None:
            continue
        error = np.mean(np.linalg.norm(detected_corners - reference_corners, axis=1))
        errors.append(float(error))
        matched_ids.append(marker_id)

    if not errors:
        return None, f"Target IDs {sorted(reference_data.keys())} not found"

    average_error = float(np.mean(errors))
    return average_error, f"Error: {average_error:.2f}px (IDs:{matched_ids})"


def _require_opencv():
    global cv2
    if cv2 is None:
        cv2 = require_opencv_gui()
    return cv2


def _safe_destroy_window(window_name: str) -> None:
    if cv2 is None:
        return

    try:
        cv2.destroyWindow(window_name)
    except Exception:  # pragma: no cover - cleanup should not hide the real failure
        pass


def _safe_destroy_all_windows() -> None:
    if cv2 is None:
        return

    try:
        cv2.destroyAllWindows()
    except Exception:  # pragma: no cover - cleanup should not hide the real failure
        pass


def normalize_camera_source(camera_source: str) -> str | int:
    """Normalize the original camera source CLI option."""
    return int(camera_source) if camera_source.isdigit() else camera_source


class OpenCVFrameSource:
    """Frame source backed by cv2.VideoCapture."""

    def __init__(self, camera_source: str | int):
        opencv = _require_opencv()
        self.capture = opencv.VideoCapture(camera_source)
        if not self.capture.isOpened():
            raise RuntimeError(f"无法打开摄像头 {camera_source}")

    def read(self) -> tuple[bool, np.ndarray | None]:
        return self.capture.read()

    def release(self) -> None:
        self.capture.release()


def create_aruco_detector():
    """Create a detector that works across OpenCV ArUco API versions."""
    opencv = _require_opencv()
    if hasattr(opencv.aruco, "DetectorParameters"):
        parameters = opencv.aruco.DetectorParameters()
    else:
        parameters = opencv.aruco.DetectorParameters_create()

    if hasattr(opencv.aruco, "ArucoDetector"):
        detector = opencv.aruco.ArucoDetector(
            opencv.aruco.getPredefinedDictionary(opencv.aruco.DICT_4X4_50),
            parameters,
        )
        return detector, parameters

    return None, parameters


class MultiCameraAligner:
    """Interactive marker-based camera alignment helper."""

    def __init__(
        self,
        reference_path: str | Path = "camera_reference_multi.json",
        reference_image_path: str | Path = "reference_img.png",
    ):
        opencv = _require_opencv()
        self.reference_path = Path(reference_path)
        self.reference_image_path = Path(reference_image_path)
        self.dictionary = opencv.aruco.getPredefinedDictionary(opencv.aruco.DICT_4X4_50)
        self.detector, self.parameters = create_aruco_detector()
        self.reference_data = self.load_reference()

    def load_reference(self) -> dict[int, np.ndarray] | None:
        if not self.reference_path.exists():
            return None

        with open(self.reference_path, encoding="utf-8") as file:
            data = json.load(file)

        reference_data: dict[int, np.ndarray] = {}
        for marker_id, corners in data.items():
            reference_data[int(marker_id)] = np.array(corners, dtype=np.float32)
        return reference_data

    def detect_markers(self, frame) -> tuple[dict[int, np.ndarray], np.ndarray | None, list]:
        opencv = _require_opencv()
        if self.detector is not None:
            corners, ids, rejected = self.detector.detectMarkers(frame)
        else:
            corners, ids, rejected = opencv.aruco.detectMarkers(
                frame,
                self.dictionary,
                parameters=self.parameters,
            )
        if ids is None:
            return {}, None, rejected
        marker_ids = ids.flatten()
        detected = {int(marker_ids[index]): corners[index][0] for index in range(len(marker_ids))}
        return detected, ids, rejected

    def save_reference(self, frame) -> bool:
        opencv = _require_opencv()
        detected, _, _ = self.detect_markers(frame)
        if not detected:
            print("❌ 错误：当前画面没看到任何 ArUco 码，无法保存！")
            return False

        serialized = {marker_id: corners.tolist() for marker_id, corners in detected.items()}
        with open(self.reference_path, "w", encoding="utf-8") as file:
            json.dump(serialized, file, indent=2, ensure_ascii=False)
        opencv.imwrite(str(self.reference_image_path), frame)
        self.reference_data = self.load_reference()
        print(f"✅ 基准已更新，保存了 {len(serialized)} 个 marker。")
        return True

    def get_alignment_error(self, frame) -> tuple[float | None, str]:
        detected, _, _ = self.detect_markers(frame)
        return compute_alignment_error(self.reference_data, detected)

    def run_ghosting_ui(self, capture) -> None:
        opencv = _require_opencv()
        reference_image = opencv.imread(str(self.reference_image_path))
        if reference_image is None:
            print("❌ 找不到参考图，请先按 's' 保存")
            return

        print(">>> 虚影模式开启，按 'q' 退出")
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            error_value, status = self.get_alignment_error(frame)
            color = get_status_color(error_value)
            reference_resized = opencv.resize(reference_image, (frame.shape[1], frame.shape[0]))
            ghost = opencv.addWeighted(frame, 0.5, reference_resized, 0.5, 0)
            opencv.putText(
                ghost,
                f"GHOST MODE: {status}",
                (20, 50),
                opencv.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )
            opencv.imshow("Ghosting_Mode", ghost)

            if opencv.waitKey(1) & 0xFF == ord("q"):
                break

        _safe_destroy_window("Ghosting_Mode")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Marker-based camera alignment helper",
    )
    parser.add_argument(
        "--cameras_index_or_path",
        required=True,
        help="Camera index or video device path",
    )
    parser.add_argument(
        "--reference-path",
        default="camera_reference_multi.json",
        help="Path to the saved reference marker JSON",
    )
    parser.add_argument(
        "--reference-image-path",
        default="reference_img.png",
        help="Path to the saved reference image",
    )
    return parser


def main(args: list[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args=args)
    opencv = _require_opencv()

    capture = OpenCVFrameSource(normalize_camera_source(parsed.cameras_index_or_path))

    aligner = MultiCameraAligner(
        reference_path=parsed.reference_path,
        reference_image_path=parsed.reference_image_path,
    )

    print("s: 保存当前 marker 作为基准")
    print("v: 进入虚影对齐模式")
    print("q: 退出")

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            detected, ids, _ = aligner.detect_markers(frame)
            error_value, status = compute_alignment_error(aligner.reference_data, detected)
            color = get_status_color(error_value)

            display_frame = frame.copy()
            if ids is not None:
                marker_corners = [
                    corners.reshape(1, 4, 2)
                    for corners in detected.values()
                ]
                opencv.aruco.drawDetectedMarkers(
                    display_frame,
                    marker_corners,
                    ids,
                )

            opencv.putText(
                display_frame,
                status,
                (10, 30),
                opencv.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )
            opencv.imshow("Calibration_Monitor", display_frame)

            key = opencv.waitKey(1) & 0xFF
            if key == ord("s"):
                aligner.save_reference(frame)
            elif key == ord("v"):
                aligner.run_ghosting_ui(capture)
            elif key == ord("q"):
                break
    finally:
        capture.release()
        _safe_destroy_all_windows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
