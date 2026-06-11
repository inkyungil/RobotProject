#!/usr/bin/env python3
"""
Frontier-based autonomous exploration node.

Subscribes to /map (OccupancyGrid from SLAM Toolbox), finds unexplored frontier
cells, and sends NavigateToPose goals to Nav2 one at a time until the map is
fully explored.

Topics:
  sub /map              nav_msgs/OccupancyGrid
  sub /explore/cmd      std_msgs/String  ("start" | "stop")
  pub /explore/status   std_msgs/String  ("idle" | "exploring" | "complete")
"""

import collections
import math
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

MAP_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    depth=1,
)

FRONTIER_MIN_CELLS = 8       # ignore tiny frontier clusters
GOAL_TIMEOUT_SEC   = 30.0    # cancel goal after this many seconds
EXPLORE_TICK_SEC   = 1.5     # how often to look for new frontiers


class FrontierExplorer(Node):
    def __init__(self):
        super().__init__('frontier_explorer')

        self._map:         OccupancyGrid | None = None
        self._exploring:   bool                 = False
        self._nav_active:  bool                 = False
        self._goal_sent_at: float               = 0.0
        self._goal_handle                       = None

        self.create_subscription(OccupancyGrid, '/map',         self._on_map,     MAP_QOS)
        self.create_subscription(String,        '/explore/cmd', self._on_cmd,     10)
        self._status_pub = self.create_publisher(String, '/explore/status', 10)
        self._nav        = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        self._current_status = 'idle'
        self.create_timer(EXPLORE_TICK_SEC, self._tick)
        self.create_timer(2.0, self._pub_status_periodic)
        self.get_logger().info('FrontierExplorer ready — send "start" to /explore/cmd')

    # ── callbacks ──────────────────────────────────────────────────────────────

    def _on_map(self, msg: OccupancyGrid):
        self._map = msg

    def _on_cmd(self, msg: String):
        cmd = msg.data.strip().lower()
        if cmd == 'start' and not self._exploring:
            self._exploring  = True
            self._nav_active = False
            self._pub_status('exploring')
            self.get_logger().info('Exploration started')
        elif cmd == 'stop':
            self._exploring  = False
            self._nav_active = False
            self._pub_status('idle')
            self.get_logger().info('Exploration stopped')
            if self._goal_handle is not None:
                self._goal_handle.cancel_goal_async()
                self._goal_handle = None

    # ── main loop ──────────────────────────────────────────────────────────────

    def _tick(self):
        if not self._exploring:
            return
        if self._map is None:
            return

        # Watchdog: cancel stuck goals
        if self._nav_active:
            elapsed = time.monotonic() - self._goal_sent_at
            if elapsed < GOAL_TIMEOUT_SEC:
                return
            self.get_logger().warn(f'Goal timed out after {elapsed:.0f}s, picking new frontier')
            self._nav_active = False

        info   = self._map.info
        grid   = np.array(self._map.data, dtype=np.int8).reshape(info.height, info.width)
        fronts = self._find_frontiers(grid)

        if not fronts:
            self.get_logger().info('No more frontiers — exploration complete!')
            self._exploring = False
            self._pub_status('complete')
            return

        # Navigate to centroid of the largest frontier
        fronts.sort(key=lambda f: -f[2])
        gx, gy, _ = fronts[0]
        wx = info.origin.position.x + (gx + 0.5) * info.resolution
        wy = info.origin.position.y + (gy + 0.5) * info.resolution
        self.get_logger().info(f'→ frontier ({wx:.2f}, {wy:.2f}), {len(fronts)} clusters remaining')
        self._send_goal(wx, wy)

    # ── frontier detection ─────────────────────────────────────────────────────

    def _find_frontiers(self, grid: np.ndarray) -> list[tuple[float, float, int]]:
        """
        Return list of (cx, cy, size) in grid coordinates.
        A frontier cell is unknown (-1) adjacent to a free (0) cell.
        """
        free    = (grid == 0).view(np.uint8)
        unknown = (grid == -1)

        # dilate free mask by 1 step (4-connectivity)
        adj = np.zeros_like(free)
        adj[1:,  :]  |= free[:-1, :]
        adj[:-1, :]  |= free[1:,  :]
        adj[:,  1:]  |= free[:,  :-1]
        adj[:, :-1]  |= free[:,   1:]

        frontier_mask = unknown & adj.view(bool)
        return self._label_components(frontier_mask)

    def _label_components(self, mask: np.ndarray) -> list[tuple[float, float, int]]:
        """BFS connected-component labelling on a boolean 2-D mask."""
        h, w       = mask.shape
        visited    = np.zeros((h, w), dtype=bool)
        results    = []
        ys, xs     = np.where(mask)

        for start_y, start_x in zip(ys, xs):
            if visited[start_y, start_x]:
                continue
            queue    = collections.deque()
            queue.append((int(start_y), int(start_x)))
            visited[start_y, start_x] = True
            cells    = []

            while queue:
                r, c = queue.popleft()
                cells.append((c, r))          # (x, y) in grid coords
                for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and mask[nr, nc]:
                        visited[nr, nc] = True
                        queue.append((nr, nc))

            if len(cells) >= FRONTIER_MIN_CELLS:
                cx = sum(p[0] for p in cells) / len(cells)
                cy = sum(p[1] for p in cells) / len(cells)
                results.append((cx, cy, len(cells)))

        return results

    # ── Nav2 helpers ───────────────────────────────────────────────────────────

    def _send_goal(self, wx: float, wy: float):
        if not self._nav.wait_for_server(timeout_sec=2.0):
            self.get_logger().warn('Nav2 not available, retrying next tick')
            return

        goal           = NavigateToPose.Goal()
        goal.pose      = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp    = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = wx
        goal.pose.pose.position.y = wy
        goal.pose.pose.orientation.w = 1.0

        self._nav_active   = True
        self._goal_sent_at = time.monotonic()
        future = self._nav.send_goal_async(goal)
        future.add_done_callback(self._on_goal_accepted)

    def _on_goal_accepted(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn('Goal rejected by Nav2')
            self._nav_active = False
            return
        self._goal_handle = handle
        handle.get_result_async().add_done_callback(self._on_nav_done)

    def _on_nav_done(self, future):
        self._nav_active  = False
        self._goal_handle = None
        status = future.result().status
        self.get_logger().info(f'Navigation finished (status={status})')

    # ── helpers ────────────────────────────────────────────────────────────────

    def _pub_status_periodic(self):
        self._pub_status(self._current_status)

    def _pub_status(self, status: str):
        self._current_status = status
        msg      = String()
        msg.data = status
        self._status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FrontierExplorer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
