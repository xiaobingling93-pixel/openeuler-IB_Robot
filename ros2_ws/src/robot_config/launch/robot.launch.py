"""Main robot launch file for robot_config.

This launch file loads robot configuration from YAML and dynamically generates:
- ros2_control hardware interface and controllers
- Robot state publisher
- Camera drivers (usb_cam, realsense2_camera)
- Static TF publishers for camera frames

Usage:
    ros2 launch robot_config robot.launch.py robot_config:=test_cam use_sim:=false
    ros2 launch robot_config robot.launch.py robot_config:=so101_single_arm use_sim:=false
"""

import os
import re
import yaml
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
)
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, FindExecutable
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue


def load_robot_config(robot_config_name, config_path_override=None):
    """Load robot configuration from YAML file.

    Args:
        robot_config_name: Robot configuration name
        config_path_override: Optional full path to config file

    Returns:
        Robot configuration dict
    """
    # Get package share directory
    try:
        robot_config_share = get_package_share_directory("robot_config")
    except:
        robot_config_share = str(Path(__file__).parent.parent)

    # Determine config file path
    if config_path_override:
        config_path = Path(config_path_override)
    else:
        config_path = Path(robot_config_share) / "config" / "robots" / f"{robot_config_name}.yaml"

    print(f"[robot_config] Loading config from: {config_path}")
    print(f"[robot_config] Config exists: {config_path.exists()}")

    # Load YAML
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    robot_config = data.get("robot", {})
    print(f"[robot_config] Loaded robot: {robot_config.get('name', 'UNKNOWN')}")
    print(f"[robot_config] Peripherals: {len(robot_config.get('peripherals', []))}")

    return robot_config


def generate_ros2_control_nodes(robot_config, use_sim):
    """Generate ros2_control nodes from configuration.

    Args:
        robot_config: Robot configuration dict
        use_sim: Simulation mode flag

    Returns:
        List of Node actions for ros2_control
    """
    nodes = []
    ros2_control_config = robot_config.get("ros2_control")

    if not ros2_control_config:
        print("[robot_config] No ros2_control configuration found, skipping ros2_control nodes")
        return nodes

    print("[robot_config] Creating ros2_control nodes")

    # Get URDF path
    urdf_path = ros2_control_config.get("urdf_path")
    if not urdf_path:
        print("[robot_config] WARNING: No urdf_path specified in ros2_control config")
        return nodes

    # Resolve $(find package) and $(env VAR) substitutions
    if "$(find " in urdf_path:
        # Extract package name from $(find package_name)/path
        match = re.search(r'\$\(find\s+(\w+)\)', urdf_path)
        if match:
            package_name = match.group(1)
            try:
                pkg_share = get_package_share_directory(package_name)
                urdf_path = urdf_path.replace(f"$(find {package_name})", pkg_share)
            except:
                print(f"[robot_config] ERROR: Could not find package {package_name}")
                return nodes

    if "$(env " in urdf_path:
        # Replace $(env VAR) with environment variable
        match = re.search(r'\$\(env\s+(\w+)\)', urdf_path)
        if match:
            var_name = match.group(1)
            var_value = os.environ.get(var_name, "")
            urdf_path = urdf_path.replace(f"$(env {var_name})", var_value)

    print(f"[robot_config] URDF path: {urdf_path}")

    # Check if URDF file exists
    if not Path(urdf_path).exists():
        print(f"[robot_config] WARNING: URDF file not found at {urdf_path}")
        return nodes

    # Check if cameras should be enabled
    enable_cameras = False
    for periph in robot_config.get("peripherals", []):
        if periph.get("type") == "camera":
            enable_cameras = True
            break

    # Generate robot_description using xacro
    xacro_args = [
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        urdf_path,
        " ",
        "use_sim:=",
        "true" if use_sim == 'true' else "false",
    ]

    # Add use_cameras argument if cameras are configured
    if enable_cameras:
        xacro_args.extend([
            " ",
            "use_cameras:=true",
        ])

    robot_description_content = ParameterValue(
        Command(xacro_args),
        value_type=str
    )
    robot_description = {"robot_description": robot_description_content}

    # Add use_sim_time for simulation
    if use_sim == 'true':
        robot_description["use_sim_time"] = True

    # Robot State Publisher
    nodes.append(Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    ))

    # In simulation mode: Gazebo's gz_ros2_control plugin handles hardware and controllers
    # In real hardware mode: Start ros2_control_node and spawners
    if use_sim != 'true':
        print("[robot_config] Real hardware mode: starting ros2_control_node and controller spawners")

        hardware_plugin = ros2_control_config.get("hardware_plugin", "")
        controllers_config = ros2_control_config.get("controllers_config")

        if not controllers_config:
            # Try to find default controllers config based on robot type
            if "so101" in hardware_plugin.lower():
                try:
                    so101_hw_share = get_package_share_directory("so101_hw_interface")
                    controllers_config = os.path.join(so101_hw_share, "config", "so101_controllers.yaml")
                except:
                    print("[robot_config] WARNING: Could not find so101_hw_interface package for controllers config")

        if controllers_config and Path(controllers_config).exists():
            print(f"[robot_config] Controllers config: {controllers_config}")

            nodes.append(Node(
                package="controller_manager",
                executable="ros2_control_node",
                parameters=[
                    robot_description,
                    controllers_config,
                ],
                output="screen",
            ))

            # Spawn joint_state_broadcaster
            nodes.append(Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "joint_state_broadcaster",
                    "--controller-manager",
                    "/controller_manager",
                ],
            ))

            # Spawn arm_controller
            nodes.append(Node(
                package="controller_manager",
                executable="spawner",
                arguments=["arm_controller", "--controller-manager", "/controller_manager"],
            ))

            # Spawn gripper_controller
            nodes.append(Node(
                package="controller_manager",
                executable="spawner",
                arguments=["gripper_controller", "--controller-manager", "/controller_manager"],
            ))
        else:
            print(f"[robot_config] WARNING: Controllers config not found at {controllers_config}")
    else:
        print("[robot_config] Simulation mode: Gazebo's gz_ros2_control will handle controllers")

    print(f"[robot_config] Created {len(nodes)} ros2_control nodes")
    return nodes


def launch_setup(context, *args, **kwargs):
    """Launch setup function that generates all nodes.

    Args:
        context: Launch context

    Returns:
        List of launch actions
    """
    actions = []

    # Get launch parameters
    robot_config_name = context.launch_configurations.get('robot_config', 'test_cam')
    config_path_override = context.launch_configurations.get('config_path', '')
    use_sim = context.launch_configurations.get('use_sim', 'false')

    print(f"[robot_config] Launch setup with:")
    print(f"[robot_config]   robot_config: {robot_config_name}")
    print(f"[robot_config]   config_path: {config_path_override if config_path_override else '(none)'}")
    print(f"[robot_config]   use_sim: {use_sim}")

    # Load robot configuration
    try:
        robot_config = load_robot_config(robot_config_name, config_path_override if config_path_override else None)
    except Exception as e:
        print(f"[robot_config] ERROR loading config: {e}")
        raise

    # ========== ros2_control Nodes ==========
    try:
        ros2_control_nodes = generate_ros2_control_nodes(robot_config, use_sim)
        actions.extend(ros2_control_nodes)
    except Exception as e:
        print(f"[robot_config] ERROR generating ros2_control nodes: {e}")
        raise

    # TODO: Add more node generation functions in subsequent commits
    # - generate_camera_nodes()
    # - generate_tf_nodes()
    # - generate_gazebo_nodes()

    print(f"[robot_config] Total nodes to launch: {len(actions)}")

    return actions


def generate_launch_description():
    """Generate launch description for robot system."""
    return LaunchDescription([
        DeclareLaunchArgument(
            "robot_config",
            default_value="test_cam",
            description="Robot configuration name (without .yaml extension)",
        ),
        DeclareLaunchArgument(
            "config_path",
            default_value="",
            description="Optional: Full path to robot config file (overrides robot_config)",
        ),
        DeclareLaunchArgument(
            "use_sim",
            default_value="false",
            description="Use simulation mode (skip camera nodes)",
        ),
        OpaqueFunction(function=launch_setup),
    ])
