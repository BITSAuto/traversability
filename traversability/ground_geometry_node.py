"""Ground-plane geometry node.

Fits the ground plane to each depth frame (RANSAC, constrained by the IMU's
gravity direction), then labels every depth pixel as ground / obstacle / drop
/ overhead by its height above that plane. Flat things on the road -- paint,
a newspaper, a manhole cover -- come out as ground no matter what they look
like.

Subscribes:
  depth_topic        sensor_msgs/Image       32FC1 metres or 16UC1 millimetres
  camera_info_topic  sensor_msgs/CameraInfo  intrinsics of the depth image
  imu_topic          sensor_msgs/Imu         accelerometer, for the gravity prior

Publishes:
  /traversability/ground_points  sensor_msgs/PointCloud2
      Organised (depth image layout, subsampled by `decimation`), fields
      x/y/z/label, in the ground frame. Labels: see traversability.geometry.
  TF  <depth frame> -> ground_frame
      On the plane directly below the camera; X forward, Y left, Z up.
"""

import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image, Imu
from tf2_ros import Buffer, TransformBroadcaster, TransformException, TransformListener

from traversability import cloud, geometry
from traversability.transforms import matrix_to_quaternion, quaternion_to_matrix


class GroundGeometryNode(Node):
    def __init__(self):
        super().__init__('ground_geometry')
        p = self.declare_parameter
        self.depth_topic = p('depth_topic', '/vehicle/range_finder/image').value
        self.info_topic = p('camera_info_topic', '/vehicle/range_finder/camera_info').value
        self.imu_topic = p('imu_topic', '/vehicle/imu').value
        self.ground_frame = p('ground_frame', 'camera_ground').value
        self.depth_scale = p('depth_scale', 0.001).value          # 16UC1 units -> m
        self.decimation = p('decimation', 2).value
        self.min_range = p('min_range', 0.3).value
        self.max_range = p('max_range', 10.0).value
        # Plane fitting: only trust points in this range band.
        self.fit_min_range = p('fit_min_range', 1.0).value
        self.fit_max_range = p('fit_max_range', 8.0).value
        self.ransac_iterations = p('ransac_iterations', 100).value
        self.inlier_threshold = p('inlier_threshold', 0.05).value
        self.max_tilt_deg = p('max_tilt_deg', 20.0).value
        self.height_range = (p('camera_height_min', 0.5).value,
                             p('camera_height_max', 3.0).value)
        # Classification.
        self.obstacle_height = p('obstacle_height', 0.08).value
        self.drop_depth = p('drop_depth', 0.10).value
        self.clearance_height = p('clearance_height', 2.5).value
        self.depth_noise_coeff = p('depth_noise_coeff', 0.005).value
        self.noise_sigmas = p('noise_sigmas', 2.0).value
        # Ground-frame box [x_min, x_max, y_min, y_max] hiding the vehicle's
        # own body. Fewer than four values disables it (ROS 2 can't declare
        # an empty array parameter without a type, hence the [0.0] default).
        self.self_mask = list(p('self_mask', [0.0]).value)
        self.imu_filter_tau = p('imu_filter_tau', 1.0).value      # s

        self.bridge = CvBridge()
        self.rng = np.random.default_rng(0)
        self.tracker = geometry.GroundPlaneTracker()
        self.intrinsics = None
        self.up = None                 # low-pass filtered, IMU frame
        self.last_imu_time = None
        self.imu_to_camera = {}        # cached static rotations, by frame pair

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.pub_points = self.create_publisher(
            cloud.PointCloud2, '/traversability/ground_points', 2)

        self.create_subscription(CameraInfo, self.info_topic, self.on_info, 1)
        self.create_subscription(Imu, self.imu_topic, self.on_imu, qos_profile_sensor_data)
        self.create_subscription(Image, self.depth_topic, self.on_depth, qos_profile_sensor_data)
        self.get_logger().info(f'Waiting for {self.depth_topic}, {self.info_topic}, {self.imu_topic}')

    def on_info(self, msg):
        self.intrinsics = (msg.k[0], msg.k[4], msg.k[2], msg.k[5])

    def on_imu(self, msg):
        a = msg.linear_acceleration
        accel = np.array([a.x, a.y, a.z])
        now = Time.from_msg(msg.header.stamp).nanoseconds * 1e-9
        if self.up is None or self.last_imu_time is None:
            self.up = accel
        else:
            # First-order low-pass: vehicle acceleration and braking briefly
            # tilt the measured "up"; gravity is what stays.
            dt = max(0.0, now - self.last_imu_time)
            k = dt / (self.imu_filter_tau + dt) if self.imu_filter_tau > 0 else 1.0
            self.up = (1 - k) * self.up + k * accel
        self.last_imu_time = now
        self.imu_frame = msg.header.frame_id

    def gravity_up(self, camera_frame):
        """Filtered "up" in the camera frame; camera -Y (level camera) if unknown."""
        level = np.array([0.0, -1.0, 0.0])
        if self.up is None:
            self.get_logger().warn('No IMU yet; assuming a level camera.', throttle_duration_sec=5.0)
            return level
        key = (self.imu_frame, camera_frame)
        if key not in self.imu_to_camera:
            try:
                q = self.tf_buffer.lookup_transform(camera_frame, self.imu_frame, Time()).transform.rotation
            except TransformException as e:
                self.get_logger().warn(f'No TF {self.imu_frame} -> {camera_frame} yet ({e}); '
                                       'assuming a level camera.', throttle_duration_sec=5.0)
                return level
            self.imu_to_camera[key] = quaternion_to_matrix(q.x, q.y, q.z, q.w)
        up = geometry.up_from_accelerometer(self.up, self.imu_to_camera[key])
        return level if up is None else up

    def depth_metres(self, msg):
        depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        if msg.encoding == '16UC1':
            return depth.astype(np.float32) * self.depth_scale
        if msg.encoding == '32FC1':
            return depth
        raise ValueError(f'unsupported depth encoding {msg.encoding}')

    def on_depth(self, msg):
        if self.intrinsics is None:
            self.get_logger().warn('No camera_info yet.', throttle_duration_sec=5.0)
            return
        try:
            depth = self.depth_metres(msg)
        except ValueError as e:
            self.get_logger().error(str(e), throttle_duration_sec=5.0)
            return

        points = geometry.deproject(depth, *self.intrinsics, step=self.decimation,
                                    min_range=self.min_range, max_range=self.max_range)
        z = points[..., 2]
        fit_mask = (z > self.fit_min_range) & (z < self.fit_max_range)
        fit = geometry.fit_ground_plane(
            points[fit_mask], self.gravity_up(msg.header.frame_id), self.rng,
            iterations=self.ransac_iterations, inlier_threshold=self.inlier_threshold,
            max_tilt_deg=self.max_tilt_deg, height_range=self.height_range)
        plane = self.tracker.update(fit)
        if plane is None:
            self.get_logger().warn('No ground plane found.', throttle_duration_sec=2.0)
            return
        if fit is None:
            self.get_logger().warn('Plane fit failed; holding the previous plane.',
                                   throttle_duration_sec=2.0)

        rotation, origin = geometry.ground_frame(plane)
        ground_points = geometry.to_ground(points, rotation, origin).astype(np.float32)
        labels = geometry.classify(
            ground_points, z, plane.offset, obstacle_height=self.obstacle_height,
            drop_depth=self.drop_depth, clearance_height=self.clearance_height,
            depth_noise_coeff=self.depth_noise_coeff, noise_sigmas=self.noise_sigmas)
        if len(self.self_mask) == 4:
            geometry.mask_box(ground_points, labels, self.self_mask)

        self.publish_tf(msg.header, rotation, origin)
        header = msg.header
        header.frame_id = self.ground_frame
        self.pub_points.publish(cloud.pack(ground_points, labels, header))
        self.get_logger().info(
            f'camera height {plane.offset:.3f} m, tilt '
            f'{np.degrees(np.arccos(np.clip(-plane.normal[1], -1, 1))):.2f} deg',
            throttle_duration_sec=5.0)

    def publish_tf(self, header, rotation, origin):
        t = TransformStamped()
        t.header.stamp = header.stamp
        t.header.frame_id = header.frame_id
        t.child_frame_id = self.ground_frame
        t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = map(float, origin)
        q = matrix_to_quaternion(rotation)
        t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w = map(float, q)
        self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = GroundGeometryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
