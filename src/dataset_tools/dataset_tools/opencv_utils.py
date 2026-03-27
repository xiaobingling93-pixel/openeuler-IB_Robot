"""Helpers for resolving a GUI-capable OpenCV build."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys


def path_has_cv2_module(search_path: Path) -> bool:
    """Return whether a Python search path contains a cv2 module."""
    if (search_path / "cv2").exists():
        return True

    for pattern in ("cv2*.so", "cv2*.pyd", "cv2*.dylib"):
        if next(search_path.glob(pattern), None) is not None:
            return True

    return False


def system_cv2_search_paths() -> list[Path]:
    """Collect likely system site-packages paths that may provide cv2."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    candidates = [
        Path(f"/usr/lib/python{version}/dist-packages"),
        Path(f"/usr/lib64/python{version}/site-packages"),
        Path("/usr/lib/python3/dist-packages"),
        Path("/usr/lib64/python3/site-packages"),
        Path(f"/usr/local/lib/python{version}/dist-packages"),
        Path(f"/usr/local/lib/python{version}/site-packages"),
    ]

    search_paths: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.exists() or not path_has_cv2_module(candidate):
            continue
        seen.add(candidate)
        search_paths.append(candidate)

    return search_paths


def opencv_has_gui_support(opencv_module) -> bool:
    """Check whether an OpenCV module provides HighGUI support."""
    get_build_information = getattr(opencv_module, "getBuildInformation", None)
    if get_build_information is None:
        return False

    try:
        build_information = get_build_information()
    except Exception:  # pragma: no cover - depends on OpenCV runtime
        return False

    for line in build_information.splitlines():
        stripped = line.strip()
        if stripped.startswith("GUI:"):
            return "NONE" not in stripped.upper()

    return False


def import_cv2_from_path(search_path: Path):
    """Import cv2 from a specific search path without polluting sys.path."""
    original_path = list(sys.path)
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "cv2" or name.startswith("cv2.")
    }

    try:
        for name in original_modules:
            sys.modules.pop(name, None)

        sys.path.insert(0, str(search_path))
        importlib.invalidate_caches()
        return importlib.import_module("cv2")
    except Exception:  # pragma: no cover - depends on local Python/OpenCV install
        for name in list(sys.modules):
            if name == "cv2" or name.startswith("cv2."):
                sys.modules.pop(name, None)
        sys.modules.update(original_modules)
        return None
    finally:
        sys.path[:] = original_path


def load_opencv():
    """Prefer a GUI-capable system OpenCV, then fall back to the default import."""
    for search_path in system_cv2_search_paths():
        opencv_module = import_cv2_from_path(search_path)
        if opencv_module is not None and opencv_has_gui_support(opencv_module):
            return opencv_module

    try:
        return importlib.import_module("cv2")
    except ImportError:  # pragma: no cover - depends on runtime environment
        return None


def require_opencv_gui():
    """Load OpenCV and raise a clear error unless HighGUI and ArUco are available."""
    opencv_module = load_opencv()
    if opencv_module is None:
        raise RuntimeError(
            "OpenCV is not available. Install a build with cv2.aruco support first.",
        )
    if not hasattr(opencv_module, "aruco"):
        raise RuntimeError("The installed OpenCV build does not provide cv2.aruco.")
    if not opencv_has_gui_support(opencv_module):
        raise RuntimeError(
            "camera_alignment requires an OpenCV build with HighGUI window support, "
            f"but resolved {getattr(opencv_module, '__file__', 'cv2')} without GTK/QT/Cocoa support.",
        )
    return opencv_module
