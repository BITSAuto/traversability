"""Traversability pipeline: ground_geometry -> traversability_grid.

Launch arguments:
  params  parameter file (default: config/tesla_sim.yaml)
  noise   insert depth_noise between the depth topic and ground_geometry to
          emulate D435 stereo noise on perfect sim depth (default: false)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# D435-like stereo depth noise, sigma_z = c * z^2 (see depth_noise_node).
NOISE_COEFF = 0.005


def generate_launch_description():
    params = LaunchConfiguration('params')
    noise = LaunchConfiguration('noise')
    default_params = os.path.join(get_package_share_directory('traversability'), 'config', 'tesla_sim.yaml')

    def geometry(condition, extra):
        return Node(package='traversability', executable='ground_geometry', name='ground_geometry',
                    parameters=[params, extra], condition=condition, output='screen')

    return LaunchDescription([
        DeclareLaunchArgument('params', default_value=default_params),
        DeclareLaunchArgument('noise', default_value='false'),
        geometry(UnlessCondition(noise), {}),
        geometry(IfCondition(noise), {'depth_topic': '/vehicle/range_finder/image_noisy',
                                      'depth_noise_coeff': NOISE_COEFF}),
        Node(package='traversability', executable='depth_noise', name='depth_noise',
             parameters=[{'depth_noise_coeff': NOISE_COEFF}],
             condition=IfCondition(noise), output='screen'),
        Node(package='traversability', executable='traversability_grid', name='traversability_grid',
             parameters=[params], output='screen'),
    ])
