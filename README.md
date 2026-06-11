# RobotProject — ROS2 Digital Twin

ROS2 Jazzy + FastAPI + Unity 기반 실시간 디지털 트윈 프로젝트.
Depth 카메라 센서 데이터를 Unity 가상 공간에 실시간으로 렌더링합니다.

## 아키텍처

```
[1단계: 로봇 센서]        [2단계: ROS2 서버]          [3단계: 가상 공간]
 로봇 카메라 (Depth)  ──>  데이터 수집/정렬   ──(TCP)──>  Unity 실시간 3D 렌더링
  (거리+색상 데이터)       (공간 좌표계 변환)             (디지털 트윈)
```

## 환경

| 항목 | 버전 |
|------|------|
| OS | Ubuntu 24.04 |
| ROS2 | Jazzy |
| GPU | NVIDIA RTX 3060 (CUDA 13.2) |
| Unity | 설치 완료 |
| 카메라 | Intel RealSense D435i (예정) |

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install fastapi uvicorn
```

### 2. 서버 실행

**ROS2 없이 (시뮬레이션 모드)**
```bash
uvicorn main:app --reload
```

**ROS2 연동 시**
```bash
source /opt/ros/jazzy/setup.bash
uvicorn main:app --reload
```

> ROS2가 없으면 자동으로 시뮬레이션 모드로 동작합니다.

### 3. 대시보드 접속

브라우저에서 `http://localhost:8000` 열기

### 4. API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/` | 로봇 관제 대시보드 (HTML) |
| `WebSocket` | `/ws` | 실시간 로봇 상태 스트림 (20Hz) |
| `POST` | `/cmd_vel` | 속도 명령 전송 |
| `POST` | `/reset` | 로봇 위치 초기화 |

**`/cmd_vel` 요청 예시**
```json
{ "linear": 0.5, "angular": 0.2 }
```

- `linear`: 전진/후진 속도 (범위: -2.0 ~ 2.0 m/s)
- `angular`: 회전 속도 (범위: -3.0 ~ 3.0 rad/s)

## 구현 로드맵

- [x] Phase 0 — FastAPI 브릿지 서버 + WebSocket 관제 대시보드
- [ ] Phase 1 — TurtleBot3 Gazebo 시뮬레이션 + SLAM Toolbox 맵핑
- [ ] Phase 2 — Nav2 자율탐색 (Frontier Exploration) + 실시간 맵 WebSocket 전송
- [ ] Phase 3 — Unity Robotics Hub 연동 및 3D 렌더링
- [ ] Phase 4 — 실물 카메라(RealSense D435i) 연동

## 프로젝트 구조

```
RobotProject/
├── README.md
├── PROJECT.md              # 상세 작업 로그
├── main.py                 # FastAPI 브릿지 서버
├── ros2_ws/                # ROS2 워크스페이스
│   └── src/
│       └── digital_twin/  # 커스텀 패키지 (예정)
└── unity_scripts/          # Unity C# 스크립트 (예정)
```

## 작업 로그

### 2026-06-11

**자율탐색 + 실시간 맵핑 파이프라인 구성 시작**

- TurtleBot3 패키지 설치 완료
  - `ros-jazzy-turtlebot3`
  - `ros-jazzy-turtlebot3-gazebo`
  - `ros-jazzy-turtlebot3-simulations`
  - `ros-jazzy-turtlebot3-navigation2`
- 기존 환경 확인: Gazebo Sim 8.11, Nav2 (36패키지), SLAM Toolbox 모두 설치됨
- `ros2_ws/` 워크스페이스 디렉터리 생성
- 목표 아키텍처 확정:
  ```
  Gazebo(TurtleBot3) → SLAM Toolbox(/map) → Nav2(자율탐색)
       └──> FastAPI(/map + /odom 구독) → WebSocket → 브라우저 Canvas 실시간 렌더링
       └──> (추후) Unity 디지털 트윈
  ```

**완료 내용 (2026-06-11 이어서)**

- `ros2_ws/src/digital_twin/` ROS2 패키지 생성 및 빌드 완료
- `frontier_explorer.py` — BFS 기반 프론티어 탐색 노드 구현
  - `/map` 구독 → 프론티어 셀 감지 → Nav2 `NavigateToPose` 액션 전송
  - `/explore/cmd` (start/stop), `/explore/status` 토픽으로 제어
- `main.py` 업데이트 — `/map` OccupancyGrid → base64 WebSocket 브릿지
  - `POST /explore/start`, `POST /explore/stop` 엔드포인트 추가
  - WebSocket 메시지 `type` 필드 추가 (`state` / `map`)
- `static/index.html` 전면 업데이트
  - 왼쪽 패널에 **자율탐색** 섹션 (시작/중지 버튼, 상태 표시)
  - 중앙 탭 전환: 경로 맵 | 탐색 맵 (SLAM)
  - 탐색 맵 탭: OccupancyGrid 실시간 렌더링 + 로봇 오버레이 + 줌/패닝
- `scripts/run_exploration.sh` — 전체 스택 원클릭 실행 스크립트

**전체 스택 실행 방법 (재부팅 후)**

> ⚠️ **주의**: 실제 로봇 컴퓨터의 ROS2(`pinky_bringup`, `sllidar_node`)가 **반드시 꺼진 상태**여야 합니다.
> 같은 Domain 74에서 실행 시 TF 충돌로 로봇이 움직이지 않습니다.

```bash
# ROS2 패키지 빌드 (변경 시마다)
cd ~/PycharmProjects/RobotProject/ros2_ws
colcon build --packages-select digital_twin
```

터미널 5개로 순서대로 실행:

```bash
# 터미널 1: Gazebo
export TURTLEBOT3_MODEL=burger && source /opt/ros/jazzy/setup.bash
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py

# 터미널 2: SLAM (Gazebo 완전히 뜬 후)
source /opt/ros/jazzy/setup.bash
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true

# 터미널 3: Nav2 커스텀 런치 (velocity_smoother·collision_monitor 제외)
source /opt/ros/jazzy/setup.bash
source ~/PycharmProjects/RobotProject/ros2_ws/install/setup.bash
ros2 launch digital_twin nav2_sim.launch.py use_sim_time:=true

# 터미널 4: Frontier Explorer
source /opt/ros/jazzy/setup.bash
source ~/PycharmProjects/RobotProject/ros2_ws/install/setup.bash
ros2 run digital_twin frontier_explorer

# 터미널 5: FastAPI
cd ~/PycharmProjects/RobotProject
uvicorn main:app --reload
```

**재부팅 후 확인 사항:**
- `ros2 node list | grep -E "planner|bt_nav|velocity"` 실행 시 아무것도 안 나와야 함 (유령 노드 없어야 함)
- 유령 노드 있으면: `ros2 daemon stop && ros2 daemon start` 후 다시 확인

**디버깅 명령:**
```bash
# Nav2 상태 확인
ros2 node list | grep -E "controller|planner|bt_nav|lifecycle"

# cmd_vel 실제 전달 확인 (로봇이 움직여야 함)
ros2 topic echo /cmd_vel

# Gazebo bridge 확인
gz topic --info --topic /cmd_vel
```

**다음 단계 (미완료)**
- 재부팅 후 유령 노드 없는 깨끗한 환경에서 전체 탐색 파이프라인 테스트
- frontier_explorer → Nav2 → Gazebo 로봇 이동 확인
- SLAM 맵 실시간 브라우저 렌더링 검증
