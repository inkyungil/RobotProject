#!/bin/bash
# run_exploration.sh — 자율탐색 전체 스택 실행 (터미널 5개 자동 오픈)
# 사용: bash scripts/run_exploration.sh

WS_DIR="$HOME/PycharmProjects/RobotProject/ros2_ws"
PROJECT_DIR="$HOME/PycharmProjects/RobotProject"

export TURTLEBOT3_MODEL=burger

echo "[1/5] Gazebo + TurtleBot3 World 실행..."
gnome-terminal --title="[1] Gazebo" -- bash -c "
  export TURTLEBOT3_MODEL=burger
  source /opt/ros/jazzy/setup.bash
  ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
  exec bash"

sleep 3

echo "[2/5] SLAM Toolbox 실행..."
gnome-terminal --title="[2] SLAM" -- bash -c "
  source /opt/ros/jazzy/setup.bash
  ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true
  exec bash"

sleep 2

echo "[3/5] Nav2 실행..."
gnome-terminal --title="[3] Nav2" -- bash -c "
  export TURTLEBOT3_MODEL=burger
  source /opt/ros/jazzy/setup.bash
  ros2 launch nav2_bringup navigation_launch.py \
    use_sim_time:=true \
    params_file:=/opt/ros/jazzy/share/turtlebot3_navigation2/param/burger.yaml
  exec bash"

sleep 4

echo "[4/5] Frontier Explorer 실행..."
gnome-terminal --title="[4] Explorer" -- bash -c "
  source /opt/ros/jazzy/setup.bash
  source $WS_DIR/install/setup.bash
  ros2 run digital_twin frontier_explorer
  exec bash"

sleep 1

echo "[5/5] FastAPI 서버 실행..."
gnome-terminal --title="[5] FastAPI" -- bash -c "
  cd $PROJECT_DIR
  source /opt/ros/jazzy/setup.bash
  uvicorn main:app --reload --port 8000
  exec bash"

echo ""
echo "=== 스택 실행 완료 ==="
echo "  브라우저: http://localhost:8000"
echo "  탐색 시작: 대시보드 왼쪽 '탐색 시작' 버튼"
