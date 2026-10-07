from glob import glob

from setuptools import setup

package_name = 'traversability'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name, package_name + '.learning'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml') + glob('config/*.rviz')),
        ('share/' + package_name + '/worlds/textures', glob('worlds/textures/*.png') + glob('worlds/textures/*.jpg')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='neel',
    maintainer_email='neelnaik2005@gmail.com',
    description='Depth-based road traversability: ground-plane geometry and a local occupancy grid.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ground_geometry = traversability.ground_geometry_node:main',
            'traversability_grid = traversability.grid_node:main',
            'depth_noise = traversability.depth_noise_node:main',
            'spawn_test_scene = traversability.test_scene:spawn_main',
            'check_test_scene = traversability.test_scene:check_main',
            'snapshot = traversability.snapshot:main',
            'semantic_seg = traversability.semantic_seg_node:main',
            'record_frames = traversability.record_frames_node:main',
            'autolabel = traversability.learning.autolabel:main',
            'train_student = traversability.learning.train:main',
            'export_model = traversability.learning.export:main',
            'benchmark_models = traversability.learning.benchmark:main',
        ],
    },
)
