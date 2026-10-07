"""Record training frames: colour, registered depth and the ground plane.

Run alongside ground_geometry (it supplies the plane), live or against
``ros2 bag play``. Each saved frame is

  <out>/rgb/<n>.jpg       colour image
  <out>/depth/<n>.png     depth registered to the colour image, uint16 mm
  <out>/meta/<n>.json     colour intrinsics, ground frame pose in the colour
                          camera frame (R, t: p_cam = R p_ground + t), stamp

which is everything traversability.learning needs to compute height above
ground and auto-label the frame (``ros2 run traversability autolabel``).

Parameters: out_dir, min_interval (s between saved frames), image_topic,
depth_topic (registered to colour!), camera_info_topic, max_frames.
"""

import json
import os
import time

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener

from traversability.transforms import quaternion_to_matrix


class RecordFrames(Node):
    def __init__(self):
        super().__init__('record_frames')
        p = self.declare_parameter
        self.out = os.path.expanduser(p('out_dir', 'traversability_frames/' + time.strftime('%Y%m%d_%H%M%S')).value)
        self.min_interval = p('min_interval', 0.5).value
        self.max_frames = p('max_frames', 0).value
        self.ground_frame = p('ground_frame', 'camera_ground').value
        self.depth_scale = p('depth_scale', 0.001).value
        self.max_skew = p('max_skew', 0.05).value          # s between colour and depth stamps
        image_topic = p('image_topic', '/vehicle/camera/image_color').value
        depth_topic = p('depth_topic', '/vehicle/range_finder/image_registered').value
        info_topic = p('camera_info_topic', '/vehicle/camera/camera_info').value
        for sub in ('rgb', 'depth', 'meta'):
            os.makedirs(os.path.join(self.out, sub), exist_ok=True)

        self.bridge = CvBridge()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.info = None
        self.depths = []
        self.last_saved = None
        self.count = len(os.listdir(os.path.join(self.out, 'meta')))
        self.create_subscription(CameraInfo, info_topic, self.on_info, 1)
        self.create_subscription(Image, depth_topic, self.on_depth, qos_profile_sensor_data)
        self.create_subscription(Image, image_topic, self.on_image, qos_profile_sensor_data)
        self.get_logger().info(f'Recording to {self.out} (every {self.min_interval} s)')

    def on_info(self, msg):
        self.info = msg

    def on_depth(self, msg):
        self.depths = (self.depths + [msg])[-10:]

    def on_image(self, msg):
        if self.info is None or not self.depths:
            return
        t = Time.from_msg(msg.header.stamp).nanoseconds * 1e-9
        if self.last_saved is not None and t - self.last_saved < self.min_interval:
            return
        depth_msg = min(self.depths, key=lambda d: abs(Time.from_msg(d.header.stamp).nanoseconds * 1e-9 - t))
        if abs(Time.from_msg(depth_msg.header.stamp).nanoseconds * 1e-9 - t) > self.max_skew:
            return
        try:
            tf = self.tf_buffer.lookup_transform(msg.header.frame_id, self.ground_frame, Time()).transform
        except TransformException as e:
            self.get_logger().warn(f'No ground plane TF ({e}); is ground_geometry running?',
                                   throttle_duration_sec=5.0)
            return

        depth = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='passthrough')
        if depth_msg.encoding == '32FC1':
            depth = np.where(np.isfinite(depth), depth * 1000.0, 0).clip(0, 65535).astype(np.uint16)
        elif depth_msg.encoding == '16UC1' and self.depth_scale != 0.001:
            depth = (depth.astype(np.float32) * self.depth_scale * 1000.0).clip(0, 65535).astype(np.uint16)
        if depth.shape[:2] != (msg.height, msg.width):
            self.get_logger().error('Depth is not registered to the colour image (size differs).',
                                    throttle_duration_sec=5.0)
            return

        q, tr = tf.rotation, tf.translation
        name = f'{self.count:06d}'
        cv2.imwrite(os.path.join(self.out, 'rgb', name + '.jpg'),
                    self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8'), [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(self.out, 'depth', name + '.png'), depth)
        with open(os.path.join(self.out, 'meta', name + '.json'), 'w') as f:
            json.dump({'stamp': t, 'K': list(self.info.k),
                       'R': quaternion_to_matrix(q.x, q.y, q.z, q.w).tolist(),
                       't': [tr.x, tr.y, tr.z]}, f)
        self.count += 1
        self.last_saved = t
        if self.count % 20 == 0:
            self.get_logger().info(f'{self.count} frames in {self.out}')
        if self.max_frames and self.count >= self.max_frames:
            self.get_logger().info('Reached max_frames; stopping.')
            raise SystemExit


def main(args=None):
    rclpy.init(args=args)
    node = RecordFrames()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException, SystemExit):
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
