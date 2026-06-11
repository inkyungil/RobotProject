import asyncio
import base64
import gzip
import json
import math
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ── ROS2 optional integration ─────────────────────────────────────────────────
ROS2_AVAILABLE = False
_ros2_node = None

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import OccupancyGrid, Odometry
    from std_msgs.msg import String as RosString

    ROS2_AVAILABLE = True
except ImportError:
    pass

# ── Shared state ──────────────────────────────────────────────────────────────
state: dict = {"x": 0.0, "y": 0.0, "theta": 0.0, "linear": 0.0, "angular": 0.0}
_path: list[dict] = [{"x": 0.0, "y": 0.0}]
_clients: Set[WebSocket] = set()

_map_data:    dict | None = None   # latest serialised OccupancyGrid
_map_updated: bool        = False
_explore_status: str      = "idle"

_MAX_PATH = 3000
_PATH_RESOLUTION = 0.02


def _append_path():
    last = _path[-1]
    if math.hypot(state["x"] - last["x"], state["y"] - last["y"]) >= _PATH_RESOLUTION:
        _path.append({"x": round(state["x"], 4), "y": round(state["y"], 4)})
        if len(_path) > _MAX_PATH:
            _path.pop(0)


# ── ROS2 node ─────────────────────────────────────────────────────────────────
if ROS2_AVAILABLE:
    MAP_QOS = QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        depth=1,
    )

    class _ControlNode(Node):
        def __init__(self):
            super().__init__("robot_dashboard")
            self._pub     = self.create_publisher(Twist,     "/cmd_vel",       10)
            self._exp_pub = self.create_publisher(RosString, "/explore/cmd",   10)

            self.create_subscription(Odometry,      "/odom",           self._odom_cb,   10)
            self.create_subscription(OccupancyGrid, "/map",            self._map_cb,    MAP_QOS)
            self.create_subscription(RosString,     "/explore/status", self._status_cb, 10)

        def publish_velocity(self, linear: float, angular: float):
            msg = Twist()
            msg.linear.x  = float(linear)
            msg.angular.z = float(angular)
            self._pub.publish(msg)

        def publish_explore_cmd(self, cmd: str):
            msg      = RosString()
            msg.data = cmd
            self._exp_pub.publish(msg)

        def _odom_cb(self, msg: "Odometry"):
            state["x"]     = msg.pose.pose.position.x
            state["y"]     = msg.pose.pose.position.y
            q              = msg.pose.pose.orientation
            siny           = 2.0 * (q.w * q.z + q.x * q.y)
            cosy           = 1.0 - 2.0 * (q.y ** 2 + q.z ** 2)
            state["theta"] = math.atan2(siny, cosy)
            _append_path()

        def _map_cb(self, msg: "OccupancyGrid"):
            global _map_data, _map_updated
            # int8 → uint8: -1 (unknown) becomes 205, 0 (free) stays 0, 100 (occupied) stays 100
            raw = bytes([v & 0xFF for v in msg.data])
            compressed = gzip.compress(raw, compresslevel=1)
            _map_data = {
                "type":       "map",
                "width":      msg.info.width,
                "height":     msg.info.height,
                "resolution": round(msg.info.resolution, 4),
                "origin_x":   round(msg.info.origin.position.x, 4),
                "origin_y":   round(msg.info.origin.position.y, 4),
                "data":       base64.b64encode(compressed).decode("ascii"),
                "compressed": True,
            }
            _map_updated = True

        def _status_cb(self, msg: "RosString"):
            global _explore_status
            _explore_status = msg.data

    def _spin():
        rclpy.init()
        global _ros2_node
        _ros2_node = _ControlNode()
        rclpy.spin(_ros2_node)

    threading.Thread(target=_spin, daemon=True).start()


# ── WebSocket broadcast ───────────────────────────────────────────────────────
async def _broadcast(payload: str):
    dead: Set[WebSocket] = set()
    for ws in _clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


# ── Simulation loop (20 Hz) — also pushes map when updated ───────────────────
async def _simulation_loop():
    global _map_updated
    dt   = 0.05
    loop = asyncio.get_event_loop()
    last = loop.time()

    while True:
        await asyncio.sleep(dt)

        # Sim physics (only when ROS2 is absent)
        if not ROS2_AVAILABLE:
            now     = loop.time()
            elapsed = now - last
            last    = now
            lin, ang = state["linear"], state["angular"]
            if lin != 0.0 or ang != 0.0:
                state["theta"] += ang * elapsed
                state["x"]     += lin * math.cos(state["theta"]) * elapsed
                state["y"]     += lin * math.sin(state["theta"]) * elapsed
                _append_path()

        if not _clients:
            continue

        # State message (every tick)
        await _broadcast(json.dumps({
            "type":    "state",
            "x":       round(state["x"], 4),
            "y":       round(state["y"], 4),
            "theta":   round(state["theta"], 4),
            "linear":  round(state["linear"], 3),
            "angular": round(state["angular"], 3),
            "ros2":    ROS2_AVAILABLE,
            "explore": _explore_status,
        }))

        # Map message (only when new data arrives)
        if _map_updated and _map_data:
            _map_updated = False
            await _broadcast(json.dumps(_map_data))


# ── FastAPI ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(_simulation_loop())
    yield
    task.cancel()


app = FastAPI(title="Robot Control Dashboard", lifespan=lifespan)


class Velocity(BaseModel):
    linear:  float = 0.0
    angular: float = 0.0


@app.post("/cmd_vel")
async def cmd_vel(vel: Velocity):
    state["linear"]  = max(-2.0, min(2.0, vel.linear))
    state["angular"] = max(-3.0, min(3.0, vel.angular))
    if _ros2_node:
        _ros2_node.publish_velocity(state["linear"], state["angular"])
    return {"ok": True}


@app.post("/reset")
async def reset():
    state.update(x=0.0, y=0.0, theta=0.0, linear=0.0, angular=0.0)
    _path.clear()
    _path.append({"x": 0.0, "y": 0.0})
    if _ros2_node:
        _ros2_node.publish_velocity(0.0, 0.0)
    return {"ok": True}


@app.post("/explore/start")
async def explore_start():
    global _explore_status
    if _ros2_node:
        _ros2_node.publish_explore_cmd("start")
        _explore_status = "exploring"
    else:
        _explore_status = "exploring"   # sim mode: just update status
    return {"ok": True, "status": _explore_status}


@app.post("/explore/stop")
async def explore_stop():
    global _explore_status
    if _ros2_node:
        _ros2_node.publish_explore_cmd("stop")
    _explore_status = "idle"
    if _ros2_node:
        _ros2_node.publish_velocity(0.0, 0.0)
    return {"ok": True, "status": _explore_status}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Send initial map before joining _clients to avoid concurrent send with simulation loop
    if _map_data:
        try:
            await websocket.send_text(json.dumps(_map_data))
        except Exception:
            pass
    _clients.add(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _clients.discard(websocket)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return Path("static/index.html").read_text()
