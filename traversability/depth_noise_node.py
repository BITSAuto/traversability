"""Adds D435-like depth noise to a perfect simulated depth image.

Stereo depth error grows with the square of distance: sigma_z = c * z^2,
where c ~ subpixel / (focal_px * baseline). For a D435 at 848x480
(focal ~425 px, baseline 50 mm, ~0.08 px subpixel) c is about 0.004; the
default 0.005 is slightly pessimistic. Pixels beyond range stay invalid.

Webots depth is noise-free, so tuning thresholds on it alone would be
optimistic -- run this between the sim and ground_geometry to test against
realistic noise.
"""

import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class DepthNoiseNode(Node):
    def __init__(self):
        super().__init__('depth_noise')
        p = self.declare_parameter
        self.coeff = p('depth_noise_coeff', 0.005).value
        self.rng = np.random.default_rng(p('seed', 0).value)
        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, p('output_topic', '/vehicle/range_finder/image_noisy').value,
                                         qos_profile_sensor_data)
        self.create_subscription(Image, p('input_topic', '/vehicle/range_finder/image').value,
                                 self.on_depth, qos_profile_sensor_data)

    def on_depth(self, msg):
        if msg.encoding != '32FC1':
            self.get_logger().error(f'expected 32FC1 depth, got {msg.encoding}', throttle_duration_sec=5.0)
            return
        depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        noise = self.rng.standard_normal(depth.shape, dtype=np.float32) * self.coeff
        finite = np.isfinite(depth)
        noisy = depth.copy()
        noisy[finite] += noise[finite] * depth[finite] ** 2
        out = self.bridge.cv2_to_imgmsg(noisy.astype(np.float32), encoding='32FC1')
        out.header = msg.header
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = DepthNoiseNode()
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
