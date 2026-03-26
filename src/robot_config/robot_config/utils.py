"""Utility functions for robot_config package.

This module contains common utility functions used across the robot_config package:
- Path resolution (ROS-style substitutions)
- Boolean parsing
- Type conversion helpers
- Joint configuration validation
"""

import os
import re
import yaml
from pathlib import Path
from ament_index_python.packages import get_package_share_directory


def resolve_ros_path(path):
    """Resolve ROS-style path substitutions like $(find pkg) and $(env VAR).

    Handles ROS path substitution syntax:
    - $(find package_name): Resolves to package share directory
    - $(env VAR_NAME): Resolves to environment variable value

    Args:
        path: Path string that may contain $(find package) or $(env VAR)

    Returns:
        Resolved path string. Returns original path if it's None or empty.

    Example:
        >>> resolve_ros_path("$(find so101_hardware)/config/controllers.yaml")
        "/home/user/workspace/install/share/so101_hardware/config/controllers.yaml"

        >>> resolve_ros_path("$(env HOME)/.config/robot.yaml")
        "/home/user/.config/robot.yaml"
    """
    if not path:
        return path

    # Resolve $(find package)
    find_pattern = re.compile(r'\$\(find\s+(\w+)\)')
    for match in find_pattern.finditer(path):
        pkg_name = match.group(1)
        try:
            pkg_path = get_package_share_directory(pkg_name)
            path = path.replace(f"$(find {pkg_name})", pkg_path)
        except Exception as e:
            print(f"[robot_config] WARNING: Could not find package '{pkg_name}': {e}")

    # Resolve $(env VAR)
    env_pattern = re.compile(r'\$\(env\s+(\w+)\)')
    for match in env_pattern.finditer(path):
        var_name = match.group(1)
        var_value = os.environ.get(var_name, "")
        path = path.replace(f"$(env {var_name})", var_value)
        if not var_value:
            print(f"[robot_config] WARNING: Environment variable '{var_name}' is not set or empty")

    return path


def parse_bool(value, default=False):
    """Parse various value types to boolean with robust handling.

    Handles multiple input formats:
    - Strings: "true", "TRUE", "True", "1", "yes", "on" -> True
    - Strings: "false", "FALSE", "False", "0", "no", "off" -> False
    - Booleans: True/False -> as-is
    - Numbers: 1/0 -> True/False
    - None: -> default value

    Args:
        value: Input value to parse (string, bool, int, or None)
        default: Default value if input is None or unparseable

    Returns:
        Boolean value

    Example:
        >>> parse_bool("true")
        True
        >>> parse_bool("FALSE")
        False
        >>> parse_bool(True)
        True
        >>> parse_bool(None, default=False)
        False
    """
    if value is None:
        return default

    # Handle boolean types directly
    if isinstance(value, bool):
        return value

    # Convert to string and normalize
    str_value = str(value).strip().lower()

    # Check for true-like values
    if str_value in ('true', '1', 'yes', 'on'):
        return True

    # Check for false-like values
    if str_value in ('false', '0', 'no', 'off', ''):
        return False

    # Unknown value, return default
    return default


def validate_joint_config(robot_config):
    """Validate joint configuration across controllers and robot config.

    Implements DRY principle by checking that joint definitions are consistent
    between robot_config and controller configuration files.

    Args:
        robot_config: Robot configuration dict with joints and ros2_control sections

    Returns:
        True if validation passes, False otherwise

    Raises:
        Prints warnings/errors but does not raise exceptions to avoid blocking startup
    """
    print("[robot_config] ========== Joint Configuration Validation ==========")

    joints_config = robot_config.get("joints", {})
    if not joints_config:
        print("[robot_config] WARNING: No 'joints' configuration found")
        return True

    expected_arm_joints = set(joints_config.get("arm", []))
    expected_gripper_joints = set(joints_config.get("gripper", []))
    expected_all_joints = set(joints_config.get("all", []))

    print(f"[robot_config] Canonical joints from robot_config:")
    print(f"[robot_config]   arm: {sorted(expected_arm_joints)}")
    print(f"[robot_config]   gripper: {sorted(expected_gripper_joints)}")
    print(f"[robot_config]   all: {sorted(expected_all_joints)}")

    # Load controllers configuration
    ros2_control_config = robot_config.get("ros2_control", {})
    controllers_config_path = ros2_control_config.get("controllers_config", "")

    if not controllers_config_path:
        print("[robot_config] WARNING: No controllers_config path specified")
        return True

    controllers_config_path = resolve_ros_path(controllers_config_path)

    if not Path(controllers_config_path).exists():
        print(f"[robot_config] WARNING: Controllers config not found at {controllers_config_path}")
        return True

    # Load controllers YAML
    try:
        with open(controllers_config_path, 'r') as f:
            controllers_yaml = yaml.safe_load(f)
    except Exception as e:
        print(f"[robot_config] ERROR: Failed to load controllers config: {e}")
        return False

    validation_passed = True
    controllers_checked = 0

    # Check arm_position_controller
    arm_pos_ctrl = controllers_yaml.get("arm_position_controller", {}).get("ros__parameters", {})
    if arm_pos_ctrl:
        ctrl_joints = set(arm_pos_ctrl.get("joints", []))
        if ctrl_joints != expected_arm_joints:
            print(f"[robot_config] ERROR: arm_position_controller joints mismatch!")
            validation_passed = False
        else:
            print(f"[robot_config] ✓ arm_position_controller joints match")
        controllers_checked += 1

    # Check gripper_position_controller
    grip_pos_ctrl = controllers_yaml.get("gripper_position_controller", {}).get("ros__parameters", {})
    if grip_pos_ctrl:
        ctrl_joints = set(grip_pos_ctrl.get("joints", []))
        if ctrl_joints != expected_gripper_joints:
            print(f"[robot_config] ERROR: gripper_position_controller joints mismatch!")
            validation_passed = False
        else:
            print(f"[robot_config] ✓ gripper_position_controller joints match")
        controllers_checked += 1

    # Check joint_state_broadcaster
    jsb_ctrl = controllers_yaml.get("joint_state_broadcaster", {}).get("ros__parameters", {})
    if jsb_ctrl:
        ctrl_joints = set(jsb_ctrl.get("joints", []))
        if ctrl_joints != expected_all_joints:
            print(f"[robot_config] ERROR: joint_state_broadcaster joints mismatch!")
            validation_passed = False
        else:
            print(f"[robot_config] ✓ joint_state_broadcaster joints match")
        controllers_checked += 1

    print(f"[robot_config] Validated {controllers_checked} controller configurations")

    if validation_passed:
        print("[robot_config] ✓ All joint configurations are consistent")
    else:
        print("[robot_config] ✗ Joint configuration validation FAILED")

    print("[robot_config] =========================================================")

    return validation_passed


def prepare_lerobot_env():
    """Prepare environment with lerobot PYTHONPATH."""
    env = os.environ.copy()
    workspace_path = os.environ.get("WORKSPACE", os.getcwd())
    lerobot_src = os.path.join(workspace_path, "libs/lerobot/src")

    if os.path.exists(lerobot_src):
        current_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{lerobot_src}:{current_pp}" if current_pp else lerobot_src

    return env


# ---------------------------------------------------------------------------
# Joint unit-conversion helpers  (LeRobot percentage  ↔  ros2_control radians)
# ---------------------------------------------------------------------------
import json
import math
from typing import List, Optional, Tuple

# Each entry: (rad_min, rad_max, pct_span, pct_offset)
JointConversionEntry = Tuple[float, float, float, float]

_TICKS_PER_RAD = 4096.0 / (2.0 * math.pi)


def build_joint_conversion_table(
    calib_file: str,
    joint_names: List[str],
    gripper_joints: Optional[List[str]] = None,
) -> List[JointConversionEntry]:
    """Build per-joint (rad_min, rad_max, pct_span, pct_offset) from calibration.

    The C++ hardware layer converts  ticks ↔ radians  using a fixed formula::

        rad  = (ticks - 2048) / (4096 / 2π)
        ticks = rad * (4096 / 2π) + 2048

    LeRobot normalises ticks to percentage-of-range values:

    * Arm joints   – ``RANGE_M100_100``::

          pct = (ticks - range_min) / (range_max - range_min) * 200 - 100

    * Gripper       – ``RANGE_0_100``::

          pct = (ticks - range_min) / (range_max - range_min) * 100

    Combining the two gives a direct  rad ↔ pct  linear mapping whose
    coefficients depend on each motor's calibrated ``range_min / range_max``.

    Parameters
    ----------
    calib_file : str
        Path to the calibration JSON produced by ``calibrate_arm``.
    joint_names : list[str]
        Ordered joint identifiers that match keys in the JSON (e.g. ["1","2",…,"6"]).
    gripper_joints : list[str] | None
        Joint names that use RANGE_0_100 (span=100, offset=0).
        All other joints are assumed RANGE_M100_100 (span=200, offset=-100).

    Returns
    -------
    list[JointConversionEntry]
        One ``(rad_min, rad_max, pct_span, pct_offset)`` per joint.
    """
    if gripper_joints is None:
        gripper_joints = []

    with open(calib_file, "r") as fh:
        calib = json.load(fh)

    table: List[JointConversionEntry] = []
    for jname in joint_names:
        entry = calib[jname]
        tick_min = entry["range_min"]
        tick_max = entry["range_max"]

        rad_min = (tick_min - 2048.0) / _TICKS_PER_RAD
        rad_max = (tick_max - 2048.0) / _TICKS_PER_RAD

        if jname in gripper_joints:
            pct_span = 100.0
            pct_offset = 0.0
        else:
            pct_span = 200.0
            pct_offset = -100.0

        table.append((rad_min, rad_max, pct_span, pct_offset))

    return table
