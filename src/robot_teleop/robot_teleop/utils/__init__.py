"""
Utility functions for robot teleoperation.
"""

import time
import numpy as np


def precise_sleep(duration: float) -> None:
    """
    Sleep for a precise duration using a hybrid approach.

    Uses time.sleep for coarse sleeping and busy-wait for precision.

    Args:
        duration: Sleep duration in seconds
    """
    if duration <= 0:
        return

    end_time = time.perf_counter() + duration

    if duration > 0.002:
        time.sleep(duration - 0.001)

    while time.perf_counter() < end_time:
        pass


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value to a range."""
    return max(min_val, min(max_val, value))


def normalize_angle(angle: float) -> float:
    """Normalize angle to [-pi, pi] range."""
    while angle > np.pi:
        angle -= 2 * np.pi
    while angle < -np.pi:
        angle += 2 * np.pi
    return angle
