"""Scatter flat clutter (paper, paint, stains, grass) ahead of the moving car
in the Webots sim, for training-data collection. Textures are generated with
different seeds and colours from the test scene's, so the test stays held out.

  python3 tools/sim_clutter_spawner.py   # with the sim and a driver running

Keeps at most 40 items alive, removing the oldest. Textures go to
~/traversability_data/clutter_textures (the Webots snap can't read hidden
directories)."""
import math
import os

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
from webots_ros2_msgs.srv import SpawnNodeFromString

TEX = os.path.expanduser('~/traversability_data/clutter_textures')
rng = np.random.default_rng(1234)
os.makedirs(TEX, exist_ok=True)
for k in range(6):   # grass variants
    base = np.array([rng.uniform(25, 70), rng.uniform(90, 150), rng.uniform(40, 90)], np.float32)
    n = cv2.GaussianBlur(rng.normal(0, 1, (256, 256)).astype(np.float32), (0, 0), rng.uniform(1, 4))
    img = (base * (1 + 0.3 * n / n.std() + 0.15 * rng.normal(0, 1, (256, 256)))[..., None]).clip(0, 255)
    cv2.imwrite(f'{TEX}/grass{k}.jpg', img.astype(np.uint8))
for k in range(6):   # paper variants
    img = np.full((256, 256, 3), int(rng.integers(180, 245)), np.uint8)
    for y in range(int(rng.integers(5, 15)), 256, int(rng.integers(6, 12))):
        cv2.line(img, (10, y), (int(rng.integers(100, 246)), y), (60, 60, 60), 2)
    cv2.imwrite(f'{TEX}/paper{k}.jpg', img)


class Spawner(Node):
    def __init__(self):
        super().__init__('clutter_spawner')
        self.pos, self.prev, self.heading, self.last_spawn, self.n, self.live = None, None, None, None, 0, []
        self.create_subscription(PointStamped, '/vehicle/gps', self.on_gps, 1)
        self.cli = self.create_client(SpawnNodeFromString, '/Ros2Supervisor/spawn_node_from_string')
        self.rm = self.create_publisher(String, '/Ros2Supervisor/remove_node', 10)

    def on_gps(self, m):
        p = (m.point.x, m.point.y)
        if self.prev is not None and math.dist(p, self.prev) > 1.0:
            self.heading = math.atan2(p[1] - self.prev[1], p[0] - self.prev[0])
            self.prev = p
        elif self.prev is None:
            self.prev = p
        self.pos = p

    def item(self, wx, wy, yaw):
        self.n += 1
        name = f'clutter_{self.n}'
        kind = rng.choice(['grass', 'paper', 'paint', 'stain'], p=[0.35, 0.25, 0.2, 0.2])
        lx, ly = rng.uniform(0.3, 2.0), rng.uniform(0.3, 2.0)
        tex, color = '', (1, 1, 1)
        if kind == 'grass':
            lx, ly = rng.uniform(1.0, 3.0), rng.uniform(1.0, 3.0)
            tex = f'{TEX}/grass{rng.integers(6)}.jpg'
        elif kind == 'paper':
            lx, ly = rng.uniform(0.3, 0.8), rng.uniform(0.3, 0.8)
            tex = f'{TEX}/paper{rng.integers(6)}.jpg'
        elif kind == 'paint':
            color = tuple(rng.choice([(0.9, 0.9, 0.9), (0.9, 0.8, 0.1), (0.8, 0.2, 0.2), (0.2, 0.4, 0.8)]))
            lx, ly = rng.uniform(0.15, 0.5), rng.uniform(1.0, 3.0)
        else:
            color = tuple([rng.uniform(0.02, 0.12)] * 3)
        tex_s = f'baseColorMap ImageTexture {{ url [ "{tex}" ] }}' if tex else ''
        box = f'Box {{ size {lx:.2f} {ly:.2f} 0.004 }}'
        rot = yaw + rng.uniform(-0.6, 0.6)
        s = (f'Solid {{ name "{name}" translation {wx:.3f} {wy:.3f} 0.022 rotation 0 0 1 {rot:.3f} '
             f'children [ Shape {{ appearance PBRAppearance {{ baseColor {color[0]} {color[1]} {color[2]} {tex_s} '
             f'roughness 1 metalness 0 }} geometry {box} }} ] }}')
        self.cli.call_async(SpawnNodeFromString.Request(data=s))
        self.live.append(name)
        while len(self.live) > 40:
            self.rm.publish(String(data=self.live.pop(0)))

    def tick(self):
        if self.pos is None or self.heading is None:
            return
        if self.last_spawn is not None and math.dist(self.pos, self.last_spawn) < 12:
            return
        self.last_spawn = self.pos
        c, s = math.cos(self.heading), math.sin(self.heading)
        for _ in range(int(rng.integers(1, 4))):
            fwd, lat = rng.uniform(15, 30), rng.uniform(-5, 5)
            self.item(self.pos[0] + c * fwd - s * lat, self.pos[1] + s * fwd + c * lat, self.heading)


rclpy.init()
node = Spawner()
node.cli.wait_for_service()
node.create_timer(0.2, node.tick)
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
