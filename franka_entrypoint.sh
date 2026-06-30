#!/bin/bash
set -e

if [ -f /ros2_ws/src/dependency.repos ]; then
  vcs import /ros2_ws/src < /ros2_ws/src/dependency.repos --recursive --skip-existing
fi

if [ -f /ros2_ws/install/setup.bash ]; then
  source /ros2_ws/install/setup.bash
elif [ -n "${ROS_DISTRO:-}" ] && [ -f "/opt/ros/$ROS_DISTRO/setup.bash" ]; then
  source "/opt/ros/$ROS_DISTRO/setup.bash"
fi

exec "$@"
