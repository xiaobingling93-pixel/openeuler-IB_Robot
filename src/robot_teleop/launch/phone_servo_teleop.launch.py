#!/usr/bin/env python3
"""
Launch file for phone teleoperation via MoveIt Servo

Starts:
  1. move_group  - provides planning scene for collision checking
  2. servo_node  - real-time Cartesian→joint velocity control
  3. servo_teleop_node - reads PhoneDevice, publishes TwistStamped to servo_node

Controller requirement:
  The arm_trajectory_controller must be active (not arm_position_controller).
  Ensure the main bringup activates arm_trajectory_controller before launching this.

Usage:
    ros2 launch robot_teleop phone_servo_teleop.launch.py phone_os:=android is_sim:=false
"""

import json
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():

    # ── Launch arguments (same as phone_teleop.launch.py) ──────────────────
    phone_os_arg = DeclareLaunchArgument(
        'phone_os', default_value='ios',
        description='Phone OS: ios or android'
    )
    base_link_name_arg = DeclareLaunchArgument(
        'base_link_name', default_value='base',
        description='Base link frame name (robot_link_command_frame for servo)'
    )
    control_frequency_arg = DeclareLaunchArgument(
        'control_frequency', default_value='30.0',
        description='Control loop frequency in Hz'
    )
    camera_offset_x_arg = DeclareLaunchArgument(
        'camera_offset_x', default_value='0.0'
    )
    camera_offset_y_arg = DeclareLaunchArgument(
        'camera_offset_y', default_value='-0.02'
    )
    camera_offset_z_arg = DeclareLaunchArgument(
        'camera_offset_z', default_value='0.04'
    )
    step_size_x_arg = DeclareLaunchArgument('step_size_x', default_value='0.5')
    step_size_y_arg = DeclareLaunchArgument('step_size_y', default_value='0.5')
    step_size_z_arg = DeclareLaunchArgument('step_size_z', default_value='0.5')
    max_ee_step_arg = DeclareLaunchArgument('max_ee_step_m', default_value='0.05')
    gripper_speed_arg = DeclareLaunchArgument('gripper_speed_factor', default_value='20.0')

    # New args
    is_sim_arg = DeclareLaunchArgument(
        'is_sim', default_value='false',
        description='Use simulation time'
    )
    display_arg = DeclareLaunchArgument(
        'display', default_value='false',
        description='Launch RViz'
    )

    is_sim = LaunchConfiguration('is_sim')
    display = LaunchConfiguration('display')

    # ── MoveIt configuration ────────────────────────────────────────────────
    robot_description_dir = get_package_share_directory('robot_description')
    so101_urdf_path = os.path.join(
        robot_description_dir, 'urdf', 'lerobot', 'so101', 'so101.urdf.xacro'
    )

    moveit_config = (
        MoveItConfigsBuilder('so101', package_name='robot_moveit')
        .robot_description(file_path=so101_urdf_path)
        .robot_description_semantic(file_path='config/lerobot/so101/so101.srdf')
        .robot_description_kinematics(file_path='config/lerobot/so101/kinematics.yaml')
        .joint_limits(file_path='config/lerobot/so101/joint_limits.yaml')
        .planning_pipelines(pipelines=['ompl'])
        .to_moveit_configs()
    )

    # ── move_group node ─────────────────────────────────────────────────────
    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            moveit_config.to_dict(),
            {'use_sim_time': is_sim},
            {'publish_robot_description_semantic': True},
        ],
        arguments=['--ros-args', '--log-level', 'warn'],
    )

    # ── servo_node ──────────────────────────────────────────────────────────
    servo_params_path = os.path.join(
        get_package_share_directory('robot_teleop'), 'config', 'servo_params.yaml'
    )

    servo_node = Node(
        package='moveit_servo',
        executable='servo_node',
        name='servo_node',
        output='screen',
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            servo_params_path,
            {'use_sim_time': is_sim},
        ],
    )

    # ── RViz (optional) ─────────────────────────────────────────────────────
    rviz_config_path = os.path.join(
        get_package_share_directory('robot_moveit'), 'config', 'lerobot', 'so101', 'moveit.rviz'
    )
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
        condition=IfCondition(display),
    )

    # ── Device config (same structure as phone_teleop.launch.py) ────────────
    device_config = {
        'type': 'phone',
        'name': 'phone_teleop',
        'phone_config': {
            'phone_os': 'ios',          # overridden at runtime via parameter
            'camera_offset': [0.0, -0.02, 0.04],
            'end_effector_step_sizes': {'x': 0.5, 'y': 0.5, 'z': 0.5},
            'end_effector_bounds': {
                'min': [-0.5, -0.5, 0.0],
                'max': [0.5, 0.5, 0.5],
            },
            'max_ee_step_m': 0.05,
            'gripper_speed_factor': 20.0,
            'gripper_range': [0.0, 1.0],
        },
    }

    # ── ServoTeleopNode ──────────────────────────────────────────────────────
    servo_teleop_node = Node(
        package='robot_teleop',
        executable='servo_teleop_node',
        name='servo_teleop_node',
        output='screen',
        parameters=[{
            'control_frequency': LaunchConfiguration('control_frequency'),
            'device_config': json.dumps(device_config),
            'base_link_name': LaunchConfiguration('base_link_name'),
            'arm_joint_names': ['1', '2', '3', '4', '5'],
            'gripper_joint_names': ['6'],
            'home_joint_positions': [0.0, 0.0, 0.0, 0.0, 0.0],
            'use_sim_time': is_sim,
        }],
    )

    return LaunchDescription([
        phone_os_arg,
        base_link_name_arg,
        control_frequency_arg,
        camera_offset_x_arg,
        camera_offset_y_arg,
        camera_offset_z_arg,
        step_size_x_arg,
        step_size_y_arg,
        step_size_z_arg,
        max_ee_step_arg,
        gripper_speed_arg,
        is_sim_arg,
        display_arg,

        LogInfo(msg=['Starting phone servo teleop [OS: ', LaunchConfiguration('phone_os'), ']']),

        move_group_node,
        servo_node,
        rviz_node,
        servo_teleop_node,
    ])
