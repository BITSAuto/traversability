"""Slow yellow-line follower for the 1280x720 sim camera (data collection only).

The upstream webots_ros2_tesla lane_follower was tuned for an older, smaller
camera image and drives at 50 km/h, which the relay-modelled steering can't
follow through curves. This one keeps the centre line at a fixed image column
at 15 km/h and publishes /cmd_ackermann.

  python3 tools/sim_slow_follower.py
"""
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from ackermann_msgs.msg import AckermannDrive
from cv_bridge import CvBridge

TARGET_X, ROWS, GAIN, SPEED = 500, (430, 500), 0.0012, 15.0   # px, rows, rad/px, km/h


class Follower(Node):
    def __init__(self):
        super().__init__('slow_follower')
        self.b = CvBridge()
        self.pub = self.create_publisher(AckermannDrive, 'cmd_ackermann', 1)
        self.create_subscription(Image, '/vehicle/camera/image_color', self.on_image, qos_profile_sensor_data)
        self.lost = 0

    def on_image(self, m):
        img = self.b.imgmsg_to_cv2(m, 'bgr8')[ROWS[0]:ROWS[1]]
        mask = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), (15, 90, 110), (40, 255, 255))
        cmd = AckermannDrive()
        xs = np.nonzero(mask)[1]
        if len(xs) > 50:
            self.lost = 0
            cmd.steering_angle = float(np.clip(GAIN * (np.median(xs) - TARGET_X), -0.4, 0.4))
            cmd.speed = SPEED
        else:   # no line (intersection): go straight, slowly, for a while
            self.lost += 1
            cmd.speed = 8.0 if self.lost < 60 else 0.0
        self.pub.publish(cmd)


rclpy.init()
rclpy.spin(Follower())
