"""Robot description layer: URDF building from YAML configuration.

Handles xacro processing and dynamic camera URDF injection.
Separated from control.py so both Gazebo and MuJoCo adapters can reuse
the same URDF generation without controller logic.

Public API:
    generate_robot_description(robot_config, use_sim) -> (full_urdf, params) | None
"""

import json
from pathlib import Path
import xacro as _xacro_lib

from robot_config.utils import resolve_ros_path, parse_bool


def _build_cameras_urdf_from_yaml(peripherals: list) -> str:
    """从 YAML peripherals 动态生成相机 link/joint/gazebo XML。

    命名约定（与 sim_peripheral_bridge.py 的 bridge 路径对齐）：
    - URDF link 名     = YAML frame_id（如 camera_top_frame）
      → robot_state_publisher TF 帧名与图像消息 header.frame_id 一致
    - Gazebo sensor 名 = {name}_camera（如 top_camera）
      → 与 sim_peripheral_bridge.py sensor_name 约定一致
    - Gazebo topic     = {name}_camera/image
      → Ignition Gazebo 发布于 /{name}_camera/image，由 bridge 桥接

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


def generate_robot_description(robot_config: dict, use_sim):
    """Build the full robot URDF from YAML config (xacro + camera injection).

    Processes the base xacro URDF and dynamically injects camera links/joints
    from YAML ``peripherals`` entries. This is the single source of truth for
    robot_description used by both robot_state_publisher and simulation adapters.

    Args:
        robot_config: Robot configuration dict (from YAML).
        use_sim:      Simulation mode flag (string or bool).

    Returns:
        ``(full_urdf_str, robot_description_params)`` on success, where
        ``robot_description_params`` is a dict ready to pass to
        ``robot_state_publisher`` parameters (includes ``use_sim_time`` when
        use_sim is True).

        ``None`` on any failure (missing path, xacro error). Caller should
        treat None as a non-recoverable config error and abort.
    """
    is_sim = parse_bool(use_sim, default=False)
    ros2_control_config = robot_config.get("ros2_control", {})

    # Resolve and validate URDF path
    urdf_path = ros2_control_config.get("urdf_path")
    if not urdf_path:
        print("[robot_config] WARNING: No urdf_path specified")
        return None
    urdf_path = resolve_ros_path(urdf_path)
    print(f"[robot_config] URDF path: {urdf_path}")
    if not Path(urdf_path).exists():
        print(f"[robot_config] WARNING: URDF file not found at {urdf_path}")
        return None

    # Build xacro parameter mappings from YAML
    port = ros2_control_config.get("port", "/dev/ttyACM0")
    calib_file = resolve_ros_path(ros2_control_config.get("calib_file", ""))
    reset_positions_json = json.dumps(ros2_control_config.get("reset_positions", {}))

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
        return None

    # Dynamically inject camera URDF blocks from YAML peripherals
    peripherals = robot_config.get("peripherals", [])
    cameras_xml = _build_cameras_urdf_from_yaml(peripherals)
    if cameras_xml:
        full_urdf = base_urdf.replace("</robot>", cameras_xml + "\n</robot>", 1)
        print(f"[robot_config] Injected {sum(1 for p in peripherals if p.get('type') == 'camera')} camera(s) into URDF from YAML")
    else:
        full_urdf = base_urdf

    robot_description_params = {"robot_description": full_urdf}
    if is_sim:
        robot_description_params["use_sim_time"] = True

    return full_urdf, robot_description_params
