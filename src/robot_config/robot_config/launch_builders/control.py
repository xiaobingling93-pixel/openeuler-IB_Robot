"""Control system launch builders.

This module handles:
- ros2_control node generation
- Controller spawner creation
- Joint configuration validation (delegates to utils.py)
"""

import json
from pathlib import Path
from launch_ros.actions import Node
import xacro as _xacro_lib

from robot_config.utils import resolve_ros_path, parse_bool, validate_joint_config


def _build_cameras_urdf_from_yaml(peripherals: list) -> str:
    """从 YAML peripherals 动态生成相机 link/joint/gazebo XML。

    命名约定（与 simulation.py 的 ros_gz_bridge 路径对齐）：
    - URDF link 名     = YAML frame_id（如 camera_top_frame）
      → robot_state_publisher TF 帧名与图像消息 header.frame_id 一致
    - Gazebo sensor 名 = {name}_camera（如 top_camera）
      → 与 simulation.py 第 94 行 sensor_name 约定一致
    - Gazebo topic     = {name}_camera/image
      → 拼出 bridge 路径 .../sensor/{name}_camera/{name}_camera/image

    固定相机（parent_frame=world/base）和随臂相机（parent_frame=gripper）
    生成逻辑完全相同，区别仅在于 parent link 的值。
    MuJoCo 使用的 <gazebo reference> 块会被忽略（不影响 MJCF 解析）。
    """
    parts = []
    for periph in peripherals:
        if periph.get("type") != "camera":
            continue
        name        = periph["name"]
        frame_id    = periph.get("frame_id", f"camera_{name}_frame")
        t           = periph.get("transform", {})
        parent      = t.get("parent_frame", "world")
        x           = t.get("x",     0.0)
        y           = t.get("y",     0.0)
        z           = t.get("z",     0.0)
        roll        = t.get("roll",  0.0)
        pitch       = t.get("pitch", 0.0)
        yaw         = t.get("yaw",   0.0)
        width       = periph.get("width",  640)
        height      = periph.get("height", 480)
        fps         = periph.get("fps",     30)
        sensor_name = f"{name}_camera"

        parts.append(f"""
    <!-- {name} camera (generated from YAML peripherals) -->
    <link name="{frame_id}">
        <inertial>
            <origin xyz="0 0 0" rpy="0 0 0"/>
            <mass value="0.01"/>
            <inertia ixx="0.001" ixy="0" ixz="0" iyy="0.001" iyz="0" izz="0.001"/>
        </inertial>
    </link>
    <joint name="{name}_camera_joint" type="fixed">
        <parent link="{parent}"/>
        <child  link="{frame_id}"/>
        <origin xyz="{x} {y} {z}" rpy="{roll} {pitch} {yaw}"/>
    </joint>
    <gazebo reference="{frame_id}">
        <sensor type="camera" name="{sensor_name}">
            <update_rate>{fps}</update_rate>
            <camera>
                <horizontal_fov>1.047</horizontal_fov>
                <image>
                    <width>{width}</width>
                    <height>{height}</height>
                    <format>R8G8B8</format>
                </image>
                <clip><near>0.1</near><far>100</far></clip>
            </camera>
            <always_on>true</always_on>
            <visualize>true</visualize>
            <topic>{sensor_name}/image</topic>
        </sensor>
    </gazebo>""")
    return "\n".join(parts)


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

    # Get URDF path
    urdf_path = ros2_control_config.get("urdf_path")
    if not urdf_path:
        print("[robot_config] WARNING: No urdf_path specified")
        return nodes, spawners_dict, deferred_sim_spawners

    urdf_path = resolve_ros_path(urdf_path)
    print(f"[robot_config] URDF path: {urdf_path}")

    if not Path(urdf_path).exists():
        print(f"[robot_config] WARNING: URDF file not found at {urdf_path}")
        return nodes, spawners_dict, deferred_sim_spawners

    # Get hardware parameters
    port = ros2_control_config.get("port", "/dev/ttyACM0")
    calib_file = resolve_ros_path(ros2_control_config.get("calib_file", ""))

    # Handle reset_positions
    reset_positions_dict = ros2_control_config.get("reset_positions", {})
    reset_positions_json = json.dumps(reset_positions_dict)

    # Process base URDF via Python xacro library (cameras excluded from xacro)
    xacro_mappings = {
        'use_sim': 'true' if is_sim else 'false',
        'port': port,
        'calib_file': calib_file,
        'reset_positions': f"'{reset_positions_json}'",
    }
    if is_sim:
        _gz_ctrl_yaml = resolve_ros_path("$(find so101_hardware)/config/so101_controllers.yaml")
        if Path(_gz_ctrl_yaml).exists():
            xacro_mappings["gz_ros2_control_parameters_file"] = str(Path(_gz_ctrl_yaml).resolve())
    try:
        doc = _xacro_lib.process_file(urdf_path, mappings=xacro_mappings)
        base_urdf = doc.toxml()
    except Exception as e:
        print(f"[robot_config] ERROR: xacro processing failed: {e}")
        return nodes, spawners_dict, deferred_sim_spawners

    # Dynamically generate camera URDF from YAML peripherals and inject
    peripherals = robot_config.get("peripherals", [])
    cameras_xml = _build_cameras_urdf_from_yaml(peripherals)
    if cameras_xml:
        full_urdf = base_urdf.replace("</robot>", cameras_xml + "\n</robot>", 1)
        print(f"[robot_config] Injected {sum(1 for p in peripherals if p.get('type') == 'camera')} camera(s) into URDF from YAML")
    else:
        full_urdf = base_urdf

    robot_description = {"robot_description": full_urdf}
    if is_sim:
        robot_description["use_sim_time"] = True

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
