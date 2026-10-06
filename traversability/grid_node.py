"""Traversability grid node.

Turns the labelled ground points from ground_geometry into a local
nav_msgs/OccupancyGrid in the ground frame (X forward, Y left). Road between
vertically adjacent ground pixels is filled in (see grid.fill_ground_gaps).

Geometry only (``semantic_topic`` empty): obstacle/drop -> 100,
ground -> 0, unseen -> -1.

With semantics (phase 2): each point is projected into the colour camera
and takes the class semantic_seg assigned to that pixel, then
traversability.fusion decides each cell -- geometry obstacles stay lethal,
road is free, sidewalk/terrain is lethal, and small "other" patches
surrounded by road (paint, a newspaper) are free. Ground outside the colour
camera's view is unknown by default (``unlabelled_ground``).

Subscribes:  /traversability/ground_points  sensor_msgs/PointCloud2
             semantic_topic                 sensor_msgs/Image mono8 (optional)
             semantic_camera_info_topic     sensor_msgs/CameraInfo (optional)
Publishes:   /traversability/grid           nav_msgs/OccupancyGrid
"""

from collections import deque

import numpy as np
import rclpy
from cv_bridge import CvBridge
from nav_msgs.msg import OccupancyGrid
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image, PointCloud2
from tf2_ros import Buffer, TransformException, TransformListener

from traversability import cloud, fusion
from traversability.geometry import GROUND
from traversability.grid import GridSpec, fill_ground_gaps, rasterize
from traversability.semantics import NONE
from traversability.transforms import quaternion_to_matrix


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

        semantic_topic = p('semantic_topic', '').value
        info_topic = p('semantic_camera_info_topic', '/vehicle/camera/camera_info').value
        # Pair a semantic frame with a cloud only if their stamps are this close.
        self.semantic_max_age = p('semantic_max_age', 0.1).value
        # With no semantic frame for this long, publish from clouds alone
        # (obstacles still lethal, ground unknown) so the grid never stalls.
        self.semantic_timeout = p('semantic_timeout', 1.0).value
        self.fusion = fusion.FusionParams(
            min_obstacle_points=self.min_obstacle_points,
            max_patch_area=p('max_patch_area', 2.0).value,
            enclosure_fraction=p('enclosure_fraction', 0.75).value,
            enclosure_margin=p('enclosure_margin', 2).value,
            unlabelled_ground=p('unlabelled_ground', 'unknown').value)

        self.pub = self.create_publisher(OccupancyGrid, '/traversability/grid', 2)
        self.create_subscription(PointCloud2, '/traversability/ground_points', self.on_points, 2)

        self.semantic = bool(semantic_topic)
        if self.semantic:
            self.bridge = CvBridge()
            self.clouds = deque(maxlen=30)      # ~2 s of depth: semantics lag behind
            self.last_semantics = None
            self.last_fused_stamp = None
            self.intrinsics = None
            self.tf_buffer = Buffer()
            self.tf_listener = TransformListener(self.tf_buffer, self)
            self.create_subscription(Image, semantic_topic, self.on_semantics, 5)
            self.create_subscription(CameraInfo, info_topic, self.on_info, 1)
            self.get_logger().info(f'Fusing semantics from {semantic_topic}')

    def on_info(self, msg):
        self.intrinsics = (msg.k[0], msg.k[4], msg.k[2], msg.k[5])

    def on_semantics(self, sem):
        """Semantics lag the cameras by the model's latency, so the grid is
        driven from here: pair each semantic frame with the buffered cloud
        closest to it in time."""
        self.last_semantics = self.get_clock().now()
        t = Time.from_msg(sem.header.stamp).nanoseconds
        cloud_msg = min(self.clouds, default=None,
                        key=lambda m: abs(Time.from_msg(m.header.stamp).nanoseconds - t))
        gap = None if cloud_msg is None else abs(Time.from_msg(cloud_msg.header.stamp).nanoseconds - t)
        if gap is None or gap > self.semantic_max_age * 1e9:
            self.get_logger().warn('No depth cloud close in time to the semantic frame; skipping it.',
                                   throttle_duration_sec=5.0)
            return
        if cloud_msg.header.stamp == self.last_fused_stamp:
            return      # already fused this cloud with a near-identical frame
        self.last_fused_stamp = cloud_msg.header.stamp
        self.publish_grid(cloud_msg, sem)

    def point_semantics(self, msg, points, sem):
        """Per-point classes, or None if camera info / TF isn't available yet."""
        if self.intrinsics is None:
            self.get_logger().warn('No semantic camera_info yet.', throttle_duration_sec=5.0)
            return None
        try:
            # Latest rather than at the cloud's stamp: the plane is smoothed
            # and changes slowly, and its TF can trail the cloud slightly.
            t = self.tf_buffer.lookup_transform(sem.header.frame_id, msg.header.frame_id, Time())
        except TransformException as e:
            self.get_logger().warn(f'No TF {msg.header.frame_id} -> {sem.header.frame_id} ({e})',
                                   throttle_duration_sec=5.0)
            return None
        q, tr = t.transform.rotation, t.transform.translation
        classes = self.bridge.imgmsg_to_cv2(sem, desired_encoding='mono8')
        return fusion.sample_semantics(points, quaternion_to_matrix(q.x, q.y, q.z, q.w),
                                       np.array([tr.x, tr.y, tr.z]), *self.intrinsics, classes)

    def on_points(self, msg):
        if not self.semantic:
            self.publish_grid(msg)
            return
        self.clouds.append(msg)
        stale = (self.last_semantics is None or
                 (self.get_clock().now() - self.last_semantics).nanoseconds > self.semantic_timeout * 1e9)
        if stale:
            self.get_logger().warn('No semantics; publishing obstacles only, ground unknown.',
                                   throttle_duration_sec=5.0)
            self.publish_grid(msg, None)

    def publish_grid(self, msg, sem=None):
        points, labels = cloud.unpack(msg)
        classes = None
        if self.semantic:
            # Without usable semantics, ground counts as unlabelled (unknown
            # by default) rather than falling back to geometry-only, which
            # would show grass and sidewalks as free.
            if sem is not None:
                classes = self.point_semantics(msg, points, sem)
            if classes is None:
                classes = np.full(labels.shape, NONE, np.uint8)

        if classes is None:
            filled = fill_ground_gaps(points, labels, self.spec.resolution, self.fill_max_gap)
            points = np.concatenate((points.reshape(-1, 3), filled))
            labels = np.concatenate((labels.ravel(), np.full(len(filled), GROUND, np.uint8)))
            grid = rasterize(points, labels, self.spec,
                             min_obstacle_points=self.min_obstacle_points,
                             min_ground_points=self.min_ground_points)
        else:
            filled, filled_classes = fill_ground_gaps(points, labels, self.spec.resolution,
                                                      self.fill_max_gap, classes)
            points = np.concatenate((points.reshape(-1, 3), filled))
            labels = np.concatenate((labels.ravel(), np.full(len(filled), GROUND, np.uint8)))
            classes = np.concatenate((classes.ravel(), filled_classes))
            grid, _ = fusion.fuse(points, labels, classes, self.spec, self.fusion)

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
