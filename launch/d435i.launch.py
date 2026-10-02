"""Traversability on a real RealSense D435i.

Starts realsense2_camera (depth 848x480, colour, accelerometer) and the
traversability pipeline with config/d435i.yaml.

Launch arguments:
  params  parameter file (default: config/d435i.yaml)
  camera  also start realsense2_camera (default: true); set false if the
          driver is already running elsewhere with the same topics
  rviz    open RViz with config/traversability.rviz (default: false)
  fps     depth/colour frame rate (default: 30; use 15 on USB 2)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('traversability')
    params = LaunchConfiguration('params')
    fps = LaunchConfiguration('fps')
    profile = PythonExpression(["'848x480x' + '", fps, "'"])

    # Scoped without forwarding, so this file's own arguments (params, camera,
    # ...) don't leak into rs_launch.py, which warns about unknown ones. The
    # driver's settings are handed in as the group's only configurations
    # (evaluated before the reset, so `profile` can still read `fps`).
    realsense = GroupAction(
        scoped=True, forwarding=False, condition=IfCondition(LaunchConfiguration('camera')),
        launch_configurations={
            'depth_module.depth_profile': profile,
            'rgb_camera.color_profile': profile,
            'enable_accel': 'true',
            'enable_gyro': 'false',
            'pointcloud.enable': 'false',
            'align_depth.enable': 'false',
        },
        actions=[IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('realsense2_camera'), 'launch', 'rs_launch.py')))])

    return LaunchDescription([
        DeclareLaunchArgument('params', default_value=os.path.join(share, 'config', 'd435i.yaml')),
        DeclareLaunchArgument('camera', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('fps', default_value='30'),
        realsense,
        Node(package='traversability', executable='ground_geometry', name='ground_geometry',
             parameters=[params], output='screen'),
        Node(package='traversability', executable='traversability_grid', name='traversability_grid',
             parameters=[params], output='screen'),
        Node(package='rviz2', executable='rviz2', name='rviz2',
             arguments=['-d', os.path.join(share, 'config', 'traversability.rviz')],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
