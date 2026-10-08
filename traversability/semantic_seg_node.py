"""Semantic segmentation node.

Runs a segmentation backend (see traversability.segmentation) on the colour
camera and publishes per-pixel traversability classes for the grid node to
fuse with geometry.

Always works on the newest frame: images arriving while the model is busy
are dropped rather than queued, so output latency stays bounded.

Subscribes:
  image_topic          sensor_msgs/Image (colour)
  depth_topic          sensor_msgs/Image, depth registered to the colour
                       image -- only for RGB-D models (height input)
Publishes:
  /traversability/semantics          sensor_msgs/Image mono8, classes
                                     1 road, 2 sidewalk, 3 terrain, 4 other,
                                     0 below min_confidence; header copied
                                     from the colour image
  /traversability/semantics_overlay  sensor_msgs/Image bgr8, for viewing
                                     (only when someone subscribes)
"""

import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener

from traversability import geometry, segmentation, semantics
from traversability.transforms import quaternion_to_matrix


class SemanticSegNode(Node):
    def __init__(self):
        super().__init__('semantic_seg')
        p = self.declare_parameter
        self.model = p('model', 'hf:nvidia/segformer-b2-finetuned-cityscapes-1024-1024').value
        input_size = (p('input_width', 1024).value, p('input_height', 576).value)
        self.min_confidence = p('min_confidence', 0.0).value
        image_topic = p('image_topic', '/vehicle/camera/image_color').value
        depth_topic = p('depth_topic', '/vehicle/range_finder/image_registered').value
        info_topic = p('camera_info_topic', '/vehicle/camera/camera_info').value
        self.ground_frame = p('ground_frame', 'camera_ground').value
        self.depth_scale = p('depth_scale', 0.001).value
        # The model sees height at its own input size (~1024x576), so compute it
        # at reduced resolution: full-res costs ~100 ms per frame in numpy.
        self.height_decimation = p('height_decimation', 2).value

        self.get_logger().info(f'Loading {self.model} ...')
        self.segmenter = segmentation.load(self.model, input_size=input_size)
        self.get_logger().info(f'Loaded {self.segmenter.name}'
                               + (' (RGB-D: uses height above ground)' if self.segmenter.uses_height else ''))

        self.bridge = CvBridge()
        self.latest_image = None
        self.latest_depth = None
        self.intrinsics = None
        self.pub = self.create_publisher(Image, '/traversability/semantics', 2)
        self.pub_overlay = self.create_publisher(Image, '/traversability/semantics_overlay', 2)
        self.create_subscription(Image, image_topic, self.on_image, qos_profile_sensor_data)
        if self.segmenter.uses_height:
            self.tf_buffer = Buffer()
            self.tf_listener = TransformListener(self.tf_buffer, self)
            self.create_subscription(Image, depth_topic, self.on_depth, qos_profile_sensor_data)
            self.create_subscription(CameraInfo, info_topic, self.on_info, 1)
        self.create_timer(0.005, self.step)
        self.times = []
        self.last_stamp = None

    def on_image(self, msg):
        self.latest_image = msg

    def on_depth(self, msg):
        self.latest_depth = msg

    def on_info(self, msg):
        self.intrinsics = (msg.k[0], msg.k[4], msg.k[2], msg.k[5])

    def height_image(self, image_msg):
        """Height above ground for each colour pixel, from registered depth
        and the ground plane published by ground_geometry."""
        if self.latest_depth is None or self.intrinsics is None:
            return None
        depth_msg = self.latest_depth
        depth = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='passthrough').astype(np.float32)
        if depth_msg.encoding == '16UC1':
            depth *= self.depth_scale
        try:
            t = self.tf_buffer.lookup_transform(image_msg.header.frame_id, self.ground_frame, Time()).transform
        except TransformException as e:
            self.get_logger().warn(f'No ground plane TF yet ({e})', throttle_duration_sec=5.0)
            return None
        q, tr = t.rotation, t.translation
        rotation = quaternion_to_matrix(q.x, q.y, q.z, q.w)
        origin = np.array([tr.x, tr.y, tr.z])
        points = geometry.deproject(depth, *self.intrinsics, step=self.height_decimation, min_range=0.1)
        return geometry.height_above(points, rotation, origin)

    def step(self):
        msg, self.latest_image = self.latest_image, None
        if msg is None or msg.header.stamp == self.last_stamp:
            return      # nothing new (simulators can republish a frame)
        self.last_stamp = msg.header.stamp
        bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        height = None
        if self.segmenter.uses_height:
            height = self.height_image(msg)
            if height is None:
                return
        (classes, confidence), dt = self.segmenter.timed(bgr, height)
        if self.min_confidence > 0:
            classes[confidence < self.min_confidence] = semantics.NONE

        out = self.bridge.cv2_to_imgmsg(classes, encoding='mono8')
        out.header = msg.header
        self.pub.publish(out)
        if self.pub_overlay.get_subscription_count():
            overlay = (0.5 * bgr + 0.5 * semantics.colorize(classes)).astype(np.uint8)
            o = self.bridge.cv2_to_imgmsg(overlay, encoding='bgr8')
            o.header = msg.header
            self.pub_overlay.publish(o)

        self.times.append(dt)
        if len(self.times) >= 30:
            self.get_logger().info(f'{self.segmenter.name}: {1000 * np.median(self.times):.0f} ms/frame (median)')
            self.times.clear()


def main(args=None):
    rclpy.init(args=args)
    node = SemanticSegNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass  # Ctrl-C / launch shutdown
    except Exception:
        if rclpy.ok():
            raise   # a real error; otherwise a publish raced the shutdown
    finally:
        # On SIGINT, newer rclpy (Jazzy) has already shut the context down.
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
