"""Save a PNG of what the pipeline currently sees, for headless checking.

  ros2 run traversability snapshot                      # -> ./traversability_snapshot.png
  ros2 run traversability snapshot --ros-args -p output:=/tmp/snap.png -p image_topic:=''

Left: the colour image (if ``image_topic`` is set and publishing). Middle:
per-pixel labels in the depth image (green ground, red obstacle, blue drop,
purple overhead, dark unknown). Right: the occupancy grid seen from above,
forward up, 1 m ticks (white free, red lethal, grey unknown).
"""

import sys

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, PointCloud2

from traversability import cloud

LABEL_BGR = np.array([(58, 58, 58), (127, 191, 127), (40, 39, 214), (180, 119, 31), (189, 103, 148)], np.uint8)
PANEL_H = 480


def _fit(img, height=PANEL_H):
    return cv2.resize(img, (round(img.shape[1] * height / img.shape[0]), height), interpolation=cv2.INTER_NEAREST)


def _title(img, text):
    cv2.putText(img, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def render_grid(msg):
    grid = np.asarray(msg.data, np.int8).reshape(msg.info.height, msg.info.width)
    img = np.full(grid.shape + (3,), 150, np.uint8)
    img[grid == 0] = 245
    img[grid == 100] = (40, 39, 214)
    # rows = Y (left +), cols = X (forward): show forward up, left on the left.
    img = np.ascontiguousarray(img.transpose(1, 0, 2)[::-1, ::-1])
    scale = max(1, round(PANEL_H / img.shape[0]))
    img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    res = msg.info.resolution / scale
    x0, y0 = msg.info.origin.position.x, msg.info.origin.position.y
    h, w = img.shape[:2]
    for metres in range(int(np.ceil(x0)), int(x0 + h * res) + 1):
        row = h - 1 - int((metres - x0) / res)
        cv2.line(img, (0, row), (6, row), (0, 0, 0), 1)
        cv2.putText(img, f'{metres}m', (8, row + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
    camera_col = w - 1 - int((0.0 - y0) / res)
    cv2.drawMarker(img, (camera_col, h - 3), (255, 0, 0), cv2.MARKER_TRIANGLE_UP, 12, 2)
    return img


class Snapshot(Node):
    def __init__(self):
        super().__init__('traversability_snapshot')
        self.output = self.declare_parameter('output', 'traversability_snapshot.png').value
        image_topic = self.declare_parameter('image_topic', '/camera/camera/color/image_raw').value
        self.bridge = CvBridge()
        self.got = {}
        self.create_subscription(PointCloud2, '/traversability/ground_points',
                                 lambda m: self.got.setdefault('points', m), 2)
        self.create_subscription(OccupancyGrid, '/traversability/grid', lambda m: self.got.setdefault('grid', m), 2)
        self.need = {'points', 'grid'}
        if image_topic:
            self.need.add('image')
            self.create_subscription(Image, image_topic, lambda m: self.got.setdefault('image', m),
                                     qos_profile_sensor_data)

    def save(self):
        panels = []
        if 'image' in self.got:
            panels.append(_title(_fit(self.bridge.imgmsg_to_cv2(self.got['image'], 'bgr8')), 'colour'))
        points, labels = cloud.unpack(self.got['points'])
        panels.append(_title(_fit(LABEL_BGR[np.clip(labels, 0, 4)]), 'labels: ground / obstacle / drop'))
        grid = render_grid(self.got['grid'])
        panels.append(_title(_fit(grid) if grid.shape[0] != PANEL_H else grid, 'grid (forward up)'))
        cv2.imwrite(self.output, np.hstack(panels))

        valid = labels > 0
        counts = np.bincount(labels[valid], minlength=5)
        heights = points[..., 2][labels == 1]
        self.get_logger().info(
            f'saved {self.output}: {valid.sum()} valid pixels, ground {counts[1]}, obstacle {counts[2]}, '
            f'drop {counts[3]}, overhead {counts[4]}; ground height spread (p5..p95) '
            f'{np.percentile(heights, 5) if heights.size else float("nan"):+.3f}..'
            f'{np.percentile(heights, 95) if heights.size else float("nan"):+.3f} m')


def main(args=None):
    rclpy.init(args=args)
    node = Snapshot()
    deadline = node.get_clock().now().nanoseconds + 15e9
    while rclpy.ok() and not node.need <= node.got.keys():
        rclpy.spin_once(node, timeout_sec=0.5)
        if node.get_clock().now().nanoseconds > deadline:
            if {'points', 'grid'} <= node.got.keys():
                node.get_logger().warn('No colour image; saving without it.')
                break
            node.get_logger().error(f'Timed out; got {sorted(node.got)}. Is the pipeline running?')
            node.destroy_node()
            rclpy.shutdown()
            sys.exit(1)
    node.save()
    node.destroy_node()
    rclpy.shutdown()
