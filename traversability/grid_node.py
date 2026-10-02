"""Traversability grid node.

Turns the labelled ground points from ground_geometry into a local
nav_msgs/OccupancyGrid in the ground frame (X forward, Y left):
obstacle/drop -> 100, ground -> 0, unseen -> -1. Road between vertically
adjacent ground pixels is filled in as free (see grid.fill_ground_gaps).

Phase 1 is geometry only. Phase 2 adds a semantic input (road / sidewalk /
vegetation / other) and the fusion rules from the plan; this node is where
they go.

Subscribes:  /traversability/ground_points  sensor_msgs/PointCloud2
Publishes:   /traversability/grid           nav_msgs/OccupancyGrid
"""

import numpy as np
import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2

from traversability import cloud
from traversability.geometry import GROUND
from traversability.grid import GridSpec, fill_ground_gaps, rasterize


class GridNode(Node):
    def __init__(self):
        super().__init__('traversability_grid')
        p = self.declare_parameter
        self.spec = GridSpec(
            x_min=p('x_min', 0.0).value, x_max=p('x_max', 12.0).value,
            y_min=p('y_min', -8.0).value, y_max=p('y_max', 8.0).value,
            resolution=p('resolution', 0.1).value)
        self.min_obstacle_points = p('min_obstacle_points', 3).value
        self.min_ground_points = p('min_ground_points', 1).value
        # Free space between vertically adjacent ground pixels up to this far
        # apart (m) counts as seen; 0 disables. See grid.fill_ground_gaps.
        self.fill_max_gap = p('fill_max_gap', 1.0).value

        self.pub = self.create_publisher(OccupancyGrid, '/traversability/grid', 2)
        self.create_subscription(PointCloud2, '/traversability/ground_points', self.on_points, 2)

    def on_points(self, msg):
        points, labels = cloud.unpack(msg)
        filled = fill_ground_gaps(points, labels, self.spec.resolution, self.fill_max_gap)
        points = np.concatenate((points.reshape(-1, 3), filled))
        labels = np.concatenate((labels.ravel(), np.full(len(filled), GROUND, np.uint8)))
        grid = rasterize(points, labels, self.spec,
                         min_obstacle_points=self.min_obstacle_points,
                         min_ground_points=self.min_ground_points)

        out = OccupancyGrid()
        out.header = msg.header
        out.info.map_load_time = msg.header.stamp
        out.info.resolution = float(self.spec.resolution)
        out.info.width = self.spec.width
        out.info.height = self.spec.height
        out.info.origin.position.x = float(self.spec.x_min)
        out.info.origin.position.y = float(self.spec.y_min)
        out.info.origin.orientation.w = 1.0
        out.data = grid.ravel().tolist()
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = GridNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass  # Ctrl-C / launch shutdown
    finally:
        # On SIGINT, newer rclpy (Jazzy) has already shut the context down.
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
