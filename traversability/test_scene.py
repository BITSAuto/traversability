"""Webots test scene for the traversability pipeline.

Spawns flat road clutter (paint, a newspaper, an oil stain, a grass patch)
and real obstacles (a box, a curb, a brick, a barrel) in front of the Tesla
at its start pose, then checks the occupancy grid against them:

  ros2 run traversability spawn_test_scene   # place objects (re-run to reset)
  ros2 run traversability check_test_scene   # score /traversability/grid
  ros2 run traversability spawn_test_scene --ros-args -p remove_only:=true

Run it on a plain road segment, not at the car's start pose: the start pose
is inside a RoadIntersection whose visible surface sits ~10 cm above its
collision surface, so objects settle partly buried (thin patches entirely).
Drive straight ahead ~20 m first (onto road(5)), stop, then spawn.

Object positions are in the camera_ground frame published by
ground_geometry (X forward, Y left, origin on the road below the camera),
so the check compares like with like. The spawner converts them to world
coordinates from the GPS (mounted in the car's front sensor slot) and the
car's heading, so the car must still be at -- or driven straight along its
heading from -- the world's start pose, and stationary while checking.

Obstacles carry physics so they settle onto the road; they sink ~2 cm into
it, because road segments' collision surface sits ~2 cm below the visible
one. Flat objects (4 mm) would vanish that way, so they get no physics and
are placed on the visible road surface (``road_surface_z``) instead.
"""

import math
import os
import sys
from dataclasses import dataclass

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PointStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from std_msgs.msg import String
from webots_ros2_msgs.srv import SpawnNodeFromString

from traversability.grid import FREE, LETHAL, NO_INFO

FLAT = 0.004


@dataclass(frozen=True)
class SceneObject:
    name: str
    x: float              # centre, camera_ground frame (forward)
    y: float              # centre, camera_ground frame (left)
    size: tuple           # (along x, along y, height) metres
    expect: str           # 'free' or 'lethal' for the geometry-only grid
    color: tuple = (0.5, 0.5, 0.5)
    texture: str = ''     # file in worlds/textures
    note: str = ''


SCENE = (
    SceneObject('trav_paint_line', 4.5, 0.0, (0.3, 2.4, FLAT), 'free', (0.95, 0.95, 0.95)),
    SceneObject('trav_newspaper', 5.0, -1.3, (0.45, 0.6, FLAT), 'free', (1, 1, 1), 'newspaper.png'),
    SceneObject('trav_oil_stain', 6.5, 0.6, (0.9, 1.0, FLAT), 'free', (0.04, 0.04, 0.05)),
    SceneObject('trav_grass', 4.0, 3.5, (1.2, 1.5, FLAT), 'free', (1, 1, 1), 'grass.jpg',
                'flat, so free on geometry alone; phase 2 semantics must forbid it'),
    SceneObject('trav_brick', 3.5, -2.2, (0.25, 0.3, 0.15), 'lethal', (0.6, 0.25, 0.15)),
    SceneObject('trav_curb', 5.5, -3.0, (3.0, 0.25, 0.15), 'lethal', (0.7, 0.7, 0.7)),
    SceneObject('trav_box', 7.5, -1.0, (0.5, 0.5, 0.5), 'lethal', (0.65, 0.5, 0.3)),
    SceneObject('trav_barrel', 9.0, 1.5, (0.5, 0.5, 1.0), 'lethal', (0.1, 0.3, 0.7)),
)

# Road region (camera_ground frame) that should hold no lethal cells other
# than the obstacles above: x range, y range.
CLEAR_REGION = ((2.5, 9.5), (-6.0, 6.0))
# Lethal cells this close to an obstacle are counted as smear, not as false
# positives: stereo depth noise grows as z^2 (sigma ~0.3 m at 8 m for a
# D435), so an obstacle's points spread along the viewing ray.
SMEAR_MARGIN = 1.0


def _vrml(obj, world_x, world_y, z, yaw, texture_dir):
    lx, ly, lz = obj.size
    texture = ''
    if obj.texture:
        path = os.path.join(texture_dir, obj.texture)
        texture = f'baseColorMap ImageTexture {{ url [ "{path}" ] }}'
    box = f'Box {{ size {lx} {ly} {lz} }}'
    physics = ''
    if lz > FLAT:
        mass = max(0.2, 300.0 * lx * ly * lz)   # light cardboard-ish density
        physics = f'physics Physics {{ density -1 mass {mass:.3f} }}'
    return (
        f'Solid {{ name "{obj.name}" '
        f'translation {world_x:.4f} {world_y:.4f} {z:.4f} rotation 0 0 1 {yaw:.6f} '
        f'children [ Shape {{ appearance PBRAppearance {{ baseColor {obj.color[0]} {obj.color[1]} '
        f'{obj.color[2]} {texture} roughness 1 metalness 0 }} geometry {box} }} ] '
        f'boundingObject {box} {physics} }}'
    )


class SpawnTestScene(Node):
    def __init__(self):
        super().__init__('spawn_test_scene')
        p = self.declare_parameter
        # TeslaModel3 rotation in tesla_city.wbt.
        self.yaw = p('vehicle_yaw', 3.1415).value
        # Camera position relative to the GPS, which sits at the front sensor
        # slot's origin (camera translation in tesla_city.wbt).
        self.camera_offset_x = p('camera_offset_x', -2.12).value
        # Spawn height: above the road everywhere near the start pose; objects
        # then fall the last few centimetres under physics.
        self.spawn_z = p('spawn_z', 0.30).value
        # Visible surface of the straight road segments (their translation z).
        self.road_surface_z = p('road_surface_z', 0.02).value
        self.remove_only = p('remove_only', False).value
        self.gps = None
        self.create_subscription(PointStamped, '/vehicle/gps', self.on_gps, 1)
        self.remove_pub = self.create_publisher(String, '/Ros2Supervisor/remove_node', 10)
        self.client = self.create_client(SpawnNodeFromString, '/Ros2Supervisor/spawn_node_from_string')

    def on_gps(self, msg):
        self.gps = (msg.point.x, msg.point.y)

    def remove_scene(self):
        while self.remove_pub.get_subscription_count() == 0 and rclpy.ok():
            self.get_logger().info('Waiting for the Ros2Supervisor...', throttle_duration_sec=5.0)
            rclpy.spin_once(self, timeout_sec=0.5)
        for obj in SCENE:
            self.remove_pub.publish(String(data=obj.name))
            rclpy.spin_once(self, timeout_sec=0.05)
        rclpy.spin_once(self, timeout_sec=1.0)

    def run(self):
        # Remove any previous copy so the scene can be reset by re-running.
        self.remove_scene()
        if self.remove_only:
            return True
        while self.gps is None and rclpy.ok():
            self.get_logger().info('Waiting for /vehicle/gps...', throttle_duration_sec=5.0)
            rclpy.spin_once(self, timeout_sec=0.5)
        if not self.client.wait_for_service(timeout_sec=30.0):
            self.get_logger().error('/Ros2Supervisor/spawn_node_from_string not available.')
            return False

        c, s = math.cos(self.yaw), math.sin(self.yaw)
        cam_x = self.gps[0] + c * self.camera_offset_x
        cam_y = self.gps[1] + s * self.camera_offset_x
        textures = os.path.join(get_package_share_directory('traversability'), 'worlds', 'textures')

        ok = True
        for obj in SCENE:
            wx = cam_x + c * obj.x - s * obj.y
            wy = cam_y + s * obj.x + c * obj.y
            z = (self.road_surface_z if obj.size[2] <= FLAT else self.spawn_z) + obj.size[2] / 2
            request = SpawnNodeFromString.Request(data=_vrml(obj, wx, wy, z, self.yaw, textures))
            future = self.client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)
            success = future.result() is not None and future.result().success
            ok &= success
            self.get_logger().info(f'{obj.name}: {"spawned" if success else "FAILED"} '
                                   f'at world ({wx:.2f}, {wy:.2f})')
        return ok


def spawn_main(args=None):
    rclpy.init(args=args)
    node = SpawnTestScene()
    ok = node.run()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if ok else 1)


def footprint(grid_info, obj, margin_cells):
    """Boolean mask of grid cells under an object's footprint (+/- margin)."""
    res = grid_info.resolution
    ox, oy = grid_info.origin.position.x, grid_info.origin.position.y
    cols = ox + (np.arange(grid_info.width) + 0.5) * res
    rows = oy + (np.arange(grid_info.height) + 0.5) * res
    gx, gy = np.meshgrid(cols, rows)
    hx = obj.size[0] / 2 + margin_cells * res
    hy = obj.size[1] / 2 + margin_cells * res
    return (np.abs(gx - obj.x) <= hx) & (np.abs(gy - obj.y) <= hy)


def score(msg):
    """Per-object and clear-region results for one OccupancyGrid."""
    grid = np.asarray(msg.data, dtype=np.int8).reshape(msg.info.height, msg.info.width)
    results = []
    obstacle_zone = np.zeros(grid.shape, bool)
    for obj in SCENE:
        if obj.expect == 'free':
            # Shrink by a cell so edge cells shared with the road don't count.
            cells = grid[footprint(msg.info, obj, -1)]
            seen = np.count_nonzero(cells != NO_INFO)
            lethal = np.count_nonzero(cells == LETHAL)
            passed = seen > 0.5 * cells.size and lethal <= 0.02 * cells.size
            detail = f'{seen}/{cells.size} cells seen, {lethal} lethal'
        else:
            # Only the near face is visible; one lethal cell around it counts.
            mask = footprint(msg.info, obj, 1)
            obstacle_zone |= footprint(msg.info, obj, round(SMEAR_MARGIN / msg.info.resolution))
            lethal = np.count_nonzero(grid[mask] == LETHAL)
            passed = lethal > 0
            detail = f'{lethal} lethal cells'
        results.append((obj, passed, detail))

    (x0, x1), (y0, y1) = CLEAR_REGION
    res = msg.info.resolution
    ox, oy = msg.info.origin.position.x, msg.info.origin.position.y
    gx, gy = np.meshgrid(ox + (np.arange(msg.info.width) + 0.5) * res,
                         oy + (np.arange(msg.info.height) + 0.5) * res)
    region = (gx >= x0) & (gx <= x1) & (gy >= y0) & (gy <= y1) & ~obstacle_zone
    in_region = (gx >= x0) & (gx <= x1) & (gy >= y0) & (gy <= y1)
    false_lethal = np.count_nonzero(grid[region] == LETHAL)
    free = np.count_nonzero(grid[region] == FREE)
    lethal_objects = np.zeros(grid.shape, bool)
    for obj in SCENE:
        if obj.expect == 'lethal':
            lethal_objects |= footprint(msg.info, obj, 1)
    smear = np.count_nonzero((grid == LETHAL) & in_region & obstacle_zone & ~lethal_objects)
    return results, false_lethal, smear, free, np.count_nonzero(region)


class CheckTestScene(Node):
    def __init__(self):
        super().__init__('check_test_scene')
        self.frames = self.declare_parameter('frames', 5).value
        self.grids = []
        self.create_subscription(OccupancyGrid, '/traversability/grid', self.grids.append, 5)


def check_main(args=None):
    rclpy.init(args=args)
    node = CheckTestScene()
    while len(node.grids) < node.frames and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=1.0)
    all_passed = True
    for i, msg in enumerate(node.grids[-node.frames:]):
        results, false_lethal, smear, free, region = score(msg)
        frame_passed = all(p for _, p, _ in results) and false_lethal == 0
        all_passed &= frame_passed
        if i == node.frames - 1 or not frame_passed:
            print(f'--- frame {i + 1}/{node.frames}: {"PASS" if frame_passed else "FAIL"}')
            for obj, passed, detail in results:
                note = f'  ({obj.note})' if obj.note else ''
                print(f'  {"ok  " if passed else "FAIL"} {obj.name:16s} expect {obj.expect:6s} {detail}{note}')
            print(f'  {"ok  " if false_lethal == 0 else "FAIL"} clear road region: '
                  f'{false_lethal} false lethal cells, {free}/{region} cells free '
                  f'(+{smear} lethal cells of obstacle smear within {SMEAR_MARGIN} m)')
    print('RESULT:', 'PASS' if all_passed else 'FAIL')
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if all_passed else 1)
