"""Gazebo simulation backend adapter.

Migrated from robot_config.launch_builders.simulation (generate_gazebo_nodes).
Logic is unchanged from T1; this file is a pure structural reorganization.

Camera bridge topic naming contains a known path mismatch — the bridge
publishes on the raw Gazebo sensor topic, not on /camera/{name}/image_raw.
This will be fixed in T3.
"""

import os
from pathlib import Path

from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from robot_config.utils import resolve_ros_path
from .base_adapter import SimBackendAdapter


class GazeboAdapter(SimBackendAdapter):
    """Gazebo Ignition simulation backend.

    Handles:
    - GZ_SIM_RESOURCE_PATH / IGN_GAZEBO_RESOURCE_PATH environment variables
    - Gazebo server and GUI launch via ros_gz_sim
    - Robot entity creation (spawn from /robot_description topic)
    - Clock bridge (/clock)
    - Joint state bridge (/world/demo/model/.../joint_state)
    - Camera image and camera_info bridges per peripheral
    """

    def start_backend(self, robot_config: dict) -> list:
        """Launch Gazebo and core infrastructure.

        Sets environment variables, spawns the robot entity, and starts
        clock + joint state bridges. Camera bridges are handled separately
        by spawn_peripheral_bridges().
        """
        actions = []
        ros2_control_config = robot_config.get("ros2_control")

        # ---- Environment variable setup ----
        gazebo_resource_paths = []
        gazebo_model_paths = []

        try:
            install_share = os.path.dirname(
                FindPackageShare('robot_description').find('robot_description')
            )
            gazebo_resource_paths.append(install_share)
            gazebo_model_paths.append(install_share)
            print(f"[robot_config] Added install share path for Gazebo: {install_share}")

            robot_desc_share = FindPackageShare('robot_description').find('robot_description')
            mesh_path = os.path.join(robot_desc_share, 'meshes', 'lerobot', 'so101')
            if Path(mesh_path).exists():
                mesh_files = list(Path(mesh_path).glob('*.stl'))
                print(f"[robot_config] Verified {len(mesh_files)} mesh files at {mesh_path}")
            else:
                print(f"[robot_config] WARNING: Mesh directory not found at {mesh_path}")
        except Exception as e:
            print(f"[robot_config] WARNING: Could not find robot_description package: {e}")

        if gazebo_resource_paths:
            combined_resource = ':'.join(gazebo_resource_paths)
            actions.append(SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', combined_resource))
            actions.append(SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', combined_resource))

        if gazebo_model_paths:
            combined_model = ':'.join(gazebo_model_paths)
            actions.append(SetEnvironmentVariable('GAZEBO_MODEL_PATH', combined_model))
            actions.append(SetEnvironmentVariable('GZ_SIM_MODEL_PATH', combined_model))

        # ---- World file resolution ----
        world_file = robot_config.get("world_file", "")
        if not world_file:
            world_file = "$(find robot_config)/config/worlds/simulation.world"
        elif not world_file.startswith("$("):
            world_file = f"$(find robot_config)/config/worlds/{world_file}"

        world_path = resolve_ros_path(world_file)
        if not Path(world_path).exists():
            print(f"[robot_config] WARNING: World file not found at {world_path}")

        # ---- Entity creation (spawn robot from /robot_description) ----
        create_entity = Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', robot_config.get("name", "so101"),
                '-allow-renaming',
                '-topic', '/robot_description',
                '-x', str(robot_config.get("initial_pose_x", 0.0)),
                '-y', str(robot_config.get("initial_pose_y", 0.0)),
                '-z', str(robot_config.get("initial_pose_z", 0.0)),
            ],
            output='screen',
        )

        # ---- Clock bridge ----
        clock_bridge = Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
            output='screen',
        )

        # ---- Joint state bridge ----
        joint_state_bridge = Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                f'/world/demo/model/{robot_config.get("name", "so101")}'
                f'/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model'
            ],
            output='screen',
        )

        actions.extend([create_entity, clock_bridge, joint_state_bridge])

        # ---- Gazebo server + GUI ----
        gz_args = ""
        if Path(world_path).exists():
            gz_args = f"-r {world_path}"
        else:
            print("[robot_config] Using empty Gazebo world (world file not found)")

        gazebo_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([
                    FindPackageShare('ros_gz_sim'),
                    'launch',
                    'gz_sim.launch.py',
                ])
            ),
            launch_arguments={'gz_args': gz_args}.items(),
        )
        actions.append(gazebo_launch)

        return actions

    def load_scene(self, scene_file_path: str) -> list:
        """Stub: scene loading for Gazebo (T5 implementation)."""
        print(f"[robot_config] GazeboAdapter.load_scene: not implemented yet (T5)")
        return []

    def ensure_controller_manager(self, robot_config: dict) -> list:
        """Gazebo provides controller_manager via gz_ros2_control plugin."""
        return []

    def spawn_peripheral_bridges(self, peripherals: list) -> list:
        """Create ros_gz_bridge nodes for camera topics.

        Builds one image bridge and one camera_info bridge per camera
        peripheral. Bridge topic path is the raw Gazebo sensor path;
        remapping to /camera/{name}/image_raw is a T3 task.
        """
        actions = []
        camera_bridges = []

        for periph in peripherals:
            if periph.get("type") == "camera":
                name = periph["name"]
                camera_bridges.append({
                    "name": name,
                    "sensor_name": f"{name}_camera",
                })

        if camera_bridges:
            print(f"[robot_config] Gazebo: Creating {len(camera_bridges)} camera bridge(s)")

        for bridge in camera_bridges:
            sensor_name = bridge['sensor_name']
            # NOTE: model_name is not available here; using sensor_name as link proxy.
            # This path format matches what _build_cameras_urdf_from_yaml injects.
            # T3 will add proper remapping to /camera/{name}/image_raw.
            print(f"[robot_config]   Camera bridge: {bridge['name']} -> sensor: {sensor_name}")

            actions.append(Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                arguments=[
                    f'/world/demo/model/so101/link/{sensor_name}_link'
                    f'/sensor/{sensor_name}/{sensor_name}/image'
                    f'@sensor_msgs/msg/Image[gz.msgs.Image'
                ],
                output='screen',
            ))

            actions.append(Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                arguments=[
                    f'/world/demo/model/so101/link/{sensor_name}_link'
                    f'/sensor/{sensor_name}/{sensor_name}/camera_info'
                    f'@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'
                ],
                output='screen',
            ))

        return actions

    def update_object_pose(self, object_name: str, pose) -> None:
        """[Reserved for v1] Runtime object pose update via Gazebo service."""
        pass
