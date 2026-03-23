---
name: ibrobot-launch
description: "Launches IB-Robot nodes with proper environment setup. Use when user wants to 'launch', 'run robot', 'start simulation', 'start system', '启动机器人', '运行仿真', '测试推理', 'test inference', '遥操作调试', 'teleop', 'start so101', or needs to run any robot configuration. Triggers for 'launch robot', 'bringup', '启动节点', or running hardware interfaces."
---

# IB-Robot Launch Skill

This skill provides the complete workflow for launching IB-Robot nodes: build first, then run with proper environment setup.

## Core Workflow: Build → Launch

### Two-Step Process (Required)

**Step 1**: Build the project using the `ibrobot-build` skill
**Step 2**: Launch with environment setup in a single Bash call

**Why this order?** Building must complete before launching, but each step needs its own Bash call because we need to verify the build succeeded before attempting to launch.

**CRITICAL**: This workspace uses `ROS_DOMAIN_ID=42`. **ALWAYS** set this before launching or nodes will fail to communicate.

## Standard Launch Pattern

### 1. Build First

Use the `ibrobot-build` skill to compile (no ROS_DOMAIN_ID needed for build):

```bash
source .shrc_local && colcon build --symlink-install --merge-install --packages-select robot_config
```

Wait for build to complete successfully.

### 2. Then Launch

In a new Bash call, use the complete environment setup **with ROS_DOMAIN_ID**:

```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py <args>
```

**Why these components?**
- `source .shrc_local`: Sets up PYTHONPATH, venv, lerobot paths
- `export ROS_DOMAIN_ID=42`: **CRITICAL** - Enables DDS discovery on correct domain
- `source install/setup.zsh`: Sets up ROS 2 workspace overlay
- All are needed in the **same shell** for the launch to work

## Common Launch Commands

### Launch Simulation (Gazebo)

```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py robot_config:=so101_single_arm use_sim:=true
```

### Launch with Specific Control Mode

```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py robot_config:=so101_single_arm control_mode:=moveit_planning use_sim:=true
```

### Launch MoveIt (Separate Terminal)

```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_moveit so101_moveit.launch.py is_sim:=True
```

### Launch Real Hardware

```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py robot_config:=so101_single_arm use_sim:=false
```

## Launch Parameters

### robot_config
- Description: Which robot configuration to use
- Default: `so101_single_arm`
- Options: Any YAML file in `config/robots/`

### control_mode
- Description: Which control mode to activate
- Default: From YAML's `default_control_mode`
- Options:
  - `teleop_act`: Position control with ACT inference
  - `moveit_planning`: Trajectory control for MoveIt

### use_sim
- Description: Use Gazebo simulation or real hardware
- Default: `false`
- Options: `true`, `false`

## Environment Details

### What .shrc_local Provides
1. ROS 2 Humble environment
2. Python venv activation
3. PYTHONPATH with lerobot
4. Workspace overlay (install/setup.zsh)
5. Convenient aliases (cb, cbp, src)

### What install/setup.zsh Provides
1. ROS 2 package paths
2. AMENT_PREFIX_PATH
3. Library paths
4. Python package paths

### What ROS_DOMAIN_ID=42 Provides
**CRITICAL for runtime operations**:
1. Enables DDS discovery on domain 42
2. Allows nodes to find each other
3. Enables topic/service communication
4. Prevents conflicts with other ROS 2 systems

**All three are required** for complete environment setup.

## Typical Workflows

### Workflow 1: Test After Code Changes

```bash
# Step 1: Build (no ROS_DOMAIN_ID)
source .shrc_local && colcon build --symlink-install --merge-install --packages-select robot_config

# Step 2: Launch (with ROS_DOMAIN_ID)
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py use_sim:=true
```

### Workflow 2: Full System Test

```bash
# Step 1: Full build (no ROS_DOMAIN_ID)
source .shrc_local && colcon build --symlink-install --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Step 2: Launch simulation (with ROS_DOMAIN_ID)
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py use_sim:=true

# Step 3 (in separate terminal): Launch MoveIt (with ROS_DOMAIN_ID)
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_moveit so101_moveit.launch.py is_sim:=True
```

### Workflow 3: Hardware Testing

```bash
# Step 1: Build (no ROS_DOMAIN_ID)
source .shrc_local && colcon build --symlink-install --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Step 2: Launch real hardware (with ROS_DOMAIN_ID)
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py use_sim:=false
```

## Troubleshooting

### Issue: Controllers fail to spawn / Nodes cannot discover each other

**Cause**: Missing `ROS_DOMAIN_ID` environment variable

**Solution**: Always export ROS_DOMAIN_ID in the launch command:
```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch ...
```

**Symptoms**:
- `[ERROR] [spawner]: process has died`
- `waiting for service /controller_manager/list_controllers to become available...`
- Nodes start but cannot communicate

### Issue: "ModuleNotFoundError: No module named 'lerobot'"

**Cause**: Missing `source .shrc_local`

**Solution**: Use the complete pattern:
```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch ...
```

### Issue: "Package 'robot_config' not found"

**Cause**: Missing `source install/setup.zsh`

**Solution**: Always include both sources:
```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch ...
```

### Issue: "Controller not found"

**Cause**: Wrong control mode for the task

**Example**: MoveIt needs `moveit_planning` mode, but system launched with `teleop_act`

**Solution**: Use correct control_mode:
```bash
# For MoveIt
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py control_mode:=moveit_planning use_sim:=true
```

### Issue: Launch file not found after build

**Cause**: Environment not refreshed after build

**Solution**: The `source install/setup.zsh` should pick up changes, but if not:
```bash
source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 pkg list | grep robot_config
```

### Issue: colcon build error - "install directory was created with the layout 'merged'"

**Cause**: Workspace uses merged install layout, but command doesn't include `--merge-install`

**Solution**: Add `--merge-install` flag:
```bash
source .shrc_local && colcon build --symlink-install --merge-install --packages-select robot_config
```

## Important Notes

### 1. Always Build First
- Launch will fail if packages aren't built
- Use `ibrobot-build` skill before this skill

### 2. Single Bash Call per Launch
- Each launch command must be in its own Bash call
- Use `&&` to chain all setup and launch in one shell

### 3. Separate Launches = Separate Calls
- Each terminal needs its own Bash call
- Can't share environment between terminals

### 4. ROS_DOMAIN_ID is Critical
- Without it, controllers will fail to spawn
- Nodes cannot discover each other
- System will appear to hang or fail silently

### 5. Check Logs
Launch logs are saved to:
```
~/.ros/log/YYYY-MM-DD-HH-MM-SS-*/
```

## Quick Reference

**For Interactive Terminals (User's shell)**:
| Task | Command |
|------|---------|
| Build first | `source .shrc_local && cb` |
| Sim launch | `source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py use_sim:=true` |
| Hardware launch | `source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py use_sim:=false` |
| MoveIt launch | `source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_moveit so101_moveit.launch.py is_sim:=True` |
| Specific mode | `source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py control_mode:=moveit_planning` |

**For Non-Interactive Shells (Bash tool)**:
| Task | Command |
|------|---------|
| Build first | `source .shrc_local && colcon build --symlink-install --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release` |
| Sim launch | `source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py use_sim:=true` |
| Hardware launch | `source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py use_sim:=false` |
| MoveIt launch | `source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_moveit so101_moveit.launch.py is_sim:=True` |
| Specific mode | `source .shrc_local && export ROS_DOMAIN_ID=42 && source install/setup.zsh && ros2 launch robot_config robot.launch.py control_mode:=moveit_planning` |

## Architecture Context

After the Feb 2026 refactoring:
- Single command launches entire system (Gazebo + Inference + Action Dispatcher)
- Contracts auto-generated at launch time
- Environment injection handled by launch system
- Control mode determines which controllers and services start

**Key Point**: The unified launch system means one command does everything, but proper environment setup (including ROS_DOMAIN_ID) is more critical than ever.
