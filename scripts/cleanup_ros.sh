#!/bin/bash
# Clean up ROS 2 controller_manager shared memory and residual processes

echo "Cleaning up ROS 2 controller_manager state..."

# Kill ROS 2 processes gracefully
echo "1. Stopping ROS 2 processes..."
pkill -SIGINT -f "ros2 launch" 2>/dev/null || true
pkill -SIGINT -f "move_group" 2>/dev/null || true
# Gazebo
pkill -SIGINT -f "ign gazebo" 2>/dev/null || true
pkill -SIGINT -f "gz sim" 2>/dev/null || true
# MuJoCo simulation
pkill -SIGINT -f "mujoco_ros2_control/ros2_control_node" 2>/dev/null || true
# Real hardware controller
pkill -SIGINT -f "controller_manager/ros2_control_node" 2>/dev/null || true
sleep 2

# Force kill if still running
echo "2. Force killing remaining processes..."
pkill -9 -f "ros2 launch" 2>/dev/null || true
pkill -9 -f "move_group" 2>/dev/null || true
# Gazebo
pkill -9 -f "ign gazebo" 2>/dev/null || true
pkill -9 -f "gz sim" 2>/dev/null || true
# MuJoCo simulation
pkill -9 -f "mujoco_ros2_control/ros2_control_node" 2>/dev/null || true
# Real hardware controller
pkill -9 -f "controller_manager/ros2_control_node" 2>/dev/null || true
sleep 1

# Reap any zombie ros2_control processes
echo "3. Reaping zombie processes..."
wait $(pgrep -f "ros2_control_no" 2>/dev/null) 2>/dev/null || true

# Clean shared memory (ROS 2 Humble uses /dev/shm)
echo "4. Cleaning shared memory..."
rm -f /dev/shm/ros2_humble_* 2>/dev/null || true
rm -f /dev/shm/ros_humble_* 2>/dev/null || true

# Clean ROS logs (optional)
echo "5. Cleaning ROS logs (optional)..."
# rm -rf ~/.ros/log/* 2>/dev/null || true

echo "✓ Cleanup complete!"
echo ""
echo "You can now run:"
echo "  source .shrc_local && export ROS_DOMAIN_ID=<您的唯一ID> && source install/setup.zsh && ros2 launch robot_config robot.launch.py ..."
