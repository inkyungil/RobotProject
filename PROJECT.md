# Digital Twin Project — ROS2 + Unity

## 아키텍처

```
[1단계: 로봇 센서]        [2단계: ROS2 서버]          [3단계: 가상 공간]
 로봇 카메라 (Depth)  ──>  데이터 수집/정렬   ──(TCP)──>  Unity 실시간 3D 렌더링
  (거리+색상 데이터)       (공간 좌표계 변환)             (디지털 트윈)
```

## 환경

- OS: Ubuntu 24.04
- ROS2: Jazzy
- GPU: NVIDIA GeForce RTX 3060 (VRAM 6GB, CUDA 13.2)
- Unity: 설치 완료
- 카메라: 미정 (Intel RealSense D435i 추천) / 개발 중 Gazebo 가상 카메라 사용

## 구현 로드맵

### Phase 1 — ROS2 환경 + 가상 카메라 [ ]
- [ ] ROS2 workspace 생성 (`~/ros2_ws`)
- [ ] Gazebo 시뮬레이터 설치 및 Depth 카메라 모델 구성
- [ ] PointCloud2 토픽 발행 확인 (`/camera/depth/color/points`)

### Phase 2 — 브릿지 서버 (FastAPI) [ ]
- [ ] ROS2 노드로 PointCloud2 구독
- [ ] 다운샘플링 처리 (VoxelGrid 필터)
- [ ] WebSocket 서버로 Unity에 실시간 전송
- [ ] 좌표계 변환: ROS2(오른손) → Unity(왼손)

### Phase 3 — Unity 수신 및 렌더링 [ ]
- [ ] Unity Robotics Hub TCP Connector 설정
- [ ] PointCloud 수신 파서 작성
- [ ] 실시간 3D 포인트 클라우드 렌더링

### Phase 4 — 실물 카메라 연동 [ ]
- [ ] Intel RealSense ROS2 패키지 (`realsense2_camera`) 설치
- [ ] 가상 카메라 → 실물 카메라 교체
- [ ] 캘리브레이션 및 최적화

## 파일 구조 (목표)

```
RobotProject/
├── PROJECT.md           # 이 파일
├── main.py              # FastAPI 브릿지 서버
├── ros2_ws/             # ROS2 워크스페이스
│   └── src/
│       └── digital_twin/
│           ├── pointcloud_bridge.py   # ROS2 노드
│           └── coordinate_transform.py
└── unity_scripts/       # Unity C# 스크립트
    └── PointCloudReceiver.cs
```

## 진행 로그

- 2026-06-10: 프로젝트 시작, 환경 확인 완료 (ROS2 Jazzy, GPU RTX 3060, Unity)
