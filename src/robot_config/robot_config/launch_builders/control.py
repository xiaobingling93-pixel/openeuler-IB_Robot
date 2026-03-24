"""Control system launch builders.

This module handles:
- ros2_control node generation
- Controller spawner creation
- Joint configuration validation (delegates to utils.py)

URDF building (xacro processing + camera injection) is in description.py.
"""

from pathlib import Path
from launch_ros.actions import Node

from robot_config.utils import resolve_ros_path, parse_bool, validate_joint_config
from robot_config.launch_builders.description import generate_robot_description


def generate_controller_spawners(controller_names, use_sim=True, controller_manager_name="controller_manager"):
    """Generate controller spawner nodes.

    Args:
        controller_names: List of controller names to spawn
        use_sim: Simulation mode (affects timeout and use_sim_time)
        controller_manager_name: Name of controller manager service

    Returns:
        List of Node actions for controller spawners
    """
    is_sim = parse_bool(use_sim, default=True)

    nodes = []
    timeout = 30 if is_sim else 10

    for controller_name in controller_names:
        nodes.append(Node(
            package="controller_manager",
            executable="spawner",
            name=f"spawner_{controller_name}",
            parameters=[
                {"use_sim_time": is_sim}
            ],
            arguments=[
                controller_name,
                "--controller-manager",
                f"/{controller_manager_name}",
                "--controller-manager-timeout",
                str(timeout),
            ],
            output="screen",
        ))

    return nodes


def generate_ros2_control_nodes(robot_config, use_sim, auto_start_controllers='true'):
    """Generate ros2_control nodes from configuration.

    Args:
        robot_config: Robot configuration dict
        use_sim: Simulation mode flag (string or bool)
        auto_start_controllers: Whether to automatically start controllers (string or bool)

    Returns:
        Tuple: (nodes, spawners_dict, deferred_sim_spawners)
        In Gazebo simulation, controller spawners are returned in
        ``deferred_sim_spawners`` (not included in ``nodes``) so launch can
        start them after ``ros_gz_sim create`` exits.
    """
    is_sim = parse_bool(use_sim, default=False)
    is_auto_start = parse_bool(auto_start_controllers, default=True)

    nodes = []
    spawners_dict = {}
    deferred_sim_spawners = []
    ros2_control_config = robot_config.get("ros2_control")

    if not ros2_control_config:
        print("[robot_config] No ros2_control configuration found")
        return nodes, spawners_dict, deferred_sim_spawners

    print("[robot_config] Creating ros2_control nodes")

    # Validate joint configuration
    validate_joint_config(robot_config)

    # Build URDF (xacro processing + camera injection) via description layer
    _desc_result = generate_robot_description(robot_config, use_sim)
    if _desc_result is None:
        return nodes, spawners_dict, deferred_sim_spawners
    _, robot_description = _desc_result

    # Robot State Publisher
    nodes.append(Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    ))

    # Get control mode configuration
    control_mode_name = robot_config.get("default_control_mode", "model_inference")
    control_modes = robot_config.get("control_modes", {})

    if control_modes:
        if control_mode_name not in control_modes:
            available_modes = list(control_modes.keys())
            print(f"[robot_config] ERROR: Control mode '{control_mode_name}' not found")
            print(f"[robot_config] Available modes: {available_modes}")
            if available_modes:
                control_mode_name = available_modes[0]

        if control_mode_name:
            mode_config = control_modes[control_mode_name]
            controller_names = mode_config.get("controllers", [])
            mode_description = mode_config.get("description", "No description")
            print(f"[robot_config] Using control mode: {control_mode_name}")
            print(f"[robot_config]   Description: {mode_description}")
            print(f"[robot_config]   Controllers: {controller_names}")
        else:
            controller_names = []
    else:
        controller_names = ros2_control_config.get("controllers", [])

    controllers_config = resolve_ros_path(ros2_control_config.get("controllers_config"))

    if not is_sim:
        # Real hardware mode
        print("[robot_config] Real hardware mode")

        if controllers_config and Path(controllers_config).exists():
            print(f"[robot_config] Controllers config: {controllers_config}")

            nodes.append(Node(
                package="controller_manager",
                executable="ros2_control_node",
                parameters=[controllers_config],
                remappings=[
                    ("~/robot_description", "/robot_description"),
                ],
                output="screen",
            ))

            if is_auto_start and controller_names:
                spawners = generate_controller_spawners(controller_names, use_sim=False)
                nodes.extend(spawners)
                # Store spawners in dict
                for i, name in enumerate(controller_names):
                    if i < len(spawners):
                        spawners_dict[name] = spawners[i]
    else:
        # Simulation mode — spawners run after Gazebo model insert (robot.launch.py)
        print("[robot_config] Simulation mode: Gazebo provides controller_manager")
        print(f"[robot_config] Controllers to spawn (deferred until after gz spawn): {controller_names}")

        if is_auto_start and controller_names:
            deferred_sim_spawners = generate_controller_spawners(controller_names, use_sim=True)
            print(f"[robot_config] Deferred {len(deferred_sim_spawners)} controller spawners")
            for i, name in enumerate(controller_names):
                if i < len(deferred_sim_spawners):
                    spawners_dict[name] = deferred_sim_spawners[i]

    return nodes, spawners_dict, deferred_sim_spawners
