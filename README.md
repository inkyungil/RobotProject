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

## 설치

```bash
# ROS2 Jazzy 환경 소싱
source /opt/ros/jazzy/setup.bash

# Python 의존성 설치
pip install fastapi uvicorn

# 서버 실행
uvicorn main:app --reload
```

## 구현 로드맵

- [ ] Phase 1 — ROS2 workspace + Gazebo 가상 카메라 구성
- [ ] Phase 2 — FastAPI 브릿지 서버 (PointCloud2 구독 → WebSocket 전송)
- [ ] Phase 3 — Unity Robotics Hub 연동 및 3D 렌더링
- [ ] Phase 4 — 실물 카메라(RealSense) 연동

## 프로젝트 구조

```
RobotProject/
├── README.md
├── PROJECT.md          # 상세 작업 로그
├── main.py             # FastAPI 브릿지 서버
├── ros2_ws/            # ROS2 워크스페이스 (예정)
│   └── src/
│       └── digital_twin/
└── unity_scripts/      # Unity C# 스크립트 (예정)
```
