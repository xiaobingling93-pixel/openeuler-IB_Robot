"""MuJoCo simulation backend adapter stub.

Full implementation is deferred to T6. This stub registers MuJoCo in the
backend registry so that:
  - robot.launch.py prints a clear "not implemented" warning instead of
    silently falling back to Gazebo when simulation.platform: mujoco
  - Unit tests can verify the adapter skeleton and registry dispatch

T6 implementation notes (from mujoco_ros2_control_test_copy analysis):
  - start_backend: launch mujoco_ros2_control node with robot_description
    and mujoco_model_path; set MUJOCO_PLUGIN_PATH env var
  - ensure_controller_manager: mujoco_ros2_control IS the controller_manager,
    so spawn joint_state_broadcaster and position controllers here
  - spawn_peripheral_bridges: return [] — mujoco_ros2_control publishes
    ROS 2 camera topics directly (/{name}_camera/color, /camera_info)
  - Topic remapping /{name}_camera/color -> /camera/{name}/image_raw needed
  - URDF ros2_control plugin must use MujocoSystem (not GazeboSimSystem)
  - Controllers config: JTC-based (joint_trajectory_controller) vs
    position_controllers used in Gazebo/hardware modes
"""

from .base_adapter import SimBackendAdapter


class MujocoAdapter(SimBackendAdapter):
    """MuJoCo simulation backend (T6 implementation pending)."""

    def start_backend(self, robot_config: dict) -> list:
        raise NotImplementedError(
            "MuJoCo adapter not implemented yet (T6). "
            "Set simulation.platform: gazebo in your robot YAML to use Gazebo."
        )

    def load_scene(self, scene_file_path: str) -> list:
        raise NotImplementedError("MuJoCo adapter not implemented yet (T6)")

    def ensure_controller_manager(self, robot_config: dict) -> list:
        raise NotImplementedError("MuJoCo adapter not implemented yet (T6)")

    def spawn_peripheral_bridges(self, peripherals: list) -> list:
        raise NotImplementedError("MuJoCo adapter not implemented yet (T6)")

    def update_object_pose(self, object_name: str, pose) -> None:
        raise NotImplementedError("MuJoCo adapter not implemented yet (T6)")
