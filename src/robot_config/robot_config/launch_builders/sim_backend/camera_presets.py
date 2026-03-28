"""Platform-specific default camera poses for simulation.

When a camera peripheral in the robot YAML has ``use_default_transform: true``,
the launch system looks up default transform and fovy values from this module
instead of using the (zeroed-out) values in the YAML.

Two mount categories:
  "wrist" — gripper-mounted palm-plate camera, follows the end-effector.
  "base"  — generic workspace camera fixed on the robot base body.
             Used by any camera whose name is NOT "wrist" (top, front, etc.).

Convention:
  Values are stored in each platform's native coordinate convention:
    - Gazebo (gz-sim): camera forward = +X, up = +Z
    - MuJoCo:          camera forward = -Z, up = +Y
  No cross-platform conversion is needed at runtime — each adapter reads its
  own column directly.
"""

PRESETS = {
    "gazebo": {
        "wrist": {
            "parent_frame": "gripper",
            "x": 0.002,
            "y": 0.061,
            "z": -0.025,
            "roll": -1.5708,
            "pitch": 1.1708,
            "yaw": -1.5708,
            "fovy": 65,
        },
        "base": {
            "parent_frame": "base",
            "x": 0.0,
            "y": -0.28,
            "z": 0.5,
            "roll": 0.0,
            "pitch": 1.5708,
            "yaw": -1.5708,
            "fovy": 70,
        },
    },
    "mujoco": {
        "wrist": {
            "parent_frame": "gripper",
            "x": 0.002,
            "y": 0.061,
            "z": -0.025,
            "roll": 0.0,
            "pitch": -0.4,
            "yaw": -1.5708,
            "fovy": 65,
        },
        "base": {
            "parent_frame": "base",
            "x": 0.0,
            "y": -0.28,
            "z": 0.55,
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 3.1415,
            "fovy": 70,
        },
    },
}


def get_preset(platform: str, camera_name: str) -> dict | None:
    """Look up default camera transform for a given platform and camera name.

    Args:
        platform: "gazebo" or "mujoco".
        camera_name: The ``name`` field from the YAML peripheral entry.
                     "wrist" → wrist preset; anything else → base preset.

    Returns:
        A dict with keys (parent_frame, x, y, z, roll, pitch, yaw, fovy),
        or None if the platform is unknown.
    """
    platform_presets = PRESETS.get(platform)
    if not platform_presets:
        return None
    if camera_name == "wrist":
        return platform_presets.get("wrist")
    return platform_presets.get("base")
