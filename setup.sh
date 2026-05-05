#!/bin/bash

# Define the Project Root
PROJ_ROOT="$HOME/project_tubitak"

# ArduPilot
export PATH="$PATH:$PROJ_ROOT/ardupilot/Tools/autotest"
if [ -f "$PROJ_ROOT/ardupilot/Tools/completion/completion.bash" ]; then
  source "$PROJ_ROOT/ardupilot/Tools/completion/completion.bash"
fi

# ArduPilot-Gazebo Plugin (Removed duplicate path injections)
export GZ_SIM_RESOURCE_PATH="$PROJ_ROOT/ardupilot_gazebo/models:$PROJ_ROOT/ardupilot_gazebo/worlds"
export GZ_SIM_SYSTEM_PLUGIN_PATH="$PROJ_ROOT/ardupilot_gazebo/build"

# MAVProxy
export PATH="$PATH:$HOME/.local/bin"
export DISPLAY=:0

# Source standard ROS 2 BEFORE doing anything ROS-related
if [ -f "/opt/ros/humble/setup.bash" ]; then
  source /opt/ros/humble/setup.bash
else
  echo "[WARNING] ROS 2 Humble is not sourced or not installed at /opt/ros/humble."
fi

# Navigate to ROS workspace
cd "$PROJ_ROOT/ros2_ws" || exit

# Conditionally clone the bridge (ignores if already cloned)
if [ ! -d "src/ros_gz" ]; then
  echo "Cloning ros_gz bridge..."
  git clone -b humble https://github.com/gazebosim/ros_gz.git src/ros_gz
else
  echo "ros_gz already exists. Skipping clone."
fi

# Force Gazebo Harmonic bridging
export GZ_VERSION=harmonic

# Update and install dependencies
if command -v rosdep &>/dev/null; then
  rosdep update
  rosdep install -r --from-paths src -i -y --rosdistro humble
else
  echo "[ERROR] rosdep command not found. Please run: sudo apt install python3-rosdep"
fi

# Build ONLY the bridge packages (Placeholder removed)
# Limit make to 2 cores and force sequential building to save RAM
export MAKEFLAGS="-j2"
colcon build \
  --executor sequential \
  --symlink-install \
  --packages-up-to ros_gz_image ros_gz_bridge \
  --allow-overriding ros_gz_bridge ros_gz_image ros_gz_interfaces

# Source the custom workspace you just built
if [ -f "install/setup.bash" ]; then
  source install/setup.bash
fi

# Return to project root
cd "$PROJ_ROOT" || exit

echo "--- Project Environment Active ---"
