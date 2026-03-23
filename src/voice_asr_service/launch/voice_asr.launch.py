#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone launch entry for debugging the voice ASR node."""

from launch import LaunchDescription
from launch.actions import LogInfo
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        LogInfo(
            msg=(
                "[voice_asr_service] Standalone launch is for debugging only. "
                "Use robot_config/robot.launch.py with the robot.voice_asr YAML section "
                "as the primary configuration entry."
            )
        ),
        Node(
            package="voice_asr_service",
            executable="voice_asr_node",
            name="voice_asr_node",
            output="screen",
        ),
    ])
