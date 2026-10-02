"""Pack and unpack the organised x/y/z/label PointCloud2 passed between nodes."""

import array

import numpy as np
from sensor_msgs.msg import PointCloud2, PointField

FIELDS = ('x', 'y', 'z', 'label')
DTYPE = np.dtype([(name, np.float32) for name in FIELDS])


def pack(points, labels, header):
    """(H, W, 3) points + (H, W) labels -> organised PointCloud2."""
    height, width = labels.shape
    data = np.empty((height, width), dtype=DTYPE)
    data['x'], data['y'], data['z'] = points[..., 0], points[..., 1], points[..., 2]
    data['label'] = labels

    msg = PointCloud2()
    msg.header = header
    msg.height, msg.width = height, width
    msg.fields = [PointField(name=name, offset=4 * i, datatype=PointField.FLOAT32, count=1)
                  for i, name in enumerate(FIELDS)]
    msg.is_bigendian = False
    msg.point_step = DTYPE.itemsize
    msg.row_step = DTYPE.itemsize * width
    msg.is_dense = False
    # array('B') rather than bytes: rclpy validates a plain sequence element
    # by element, which is very slow for a cloud this size.
    buffer = array.array('B')
    buffer.frombytes(data.tobytes())
    msg.data = buffer
    return msg


def unpack(msg):
    """Organised PointCloud2 -> ((H, W, 3) points, (H, W) uint8 labels)."""
    data = np.frombuffer(msg.data, dtype=DTYPE).reshape(msg.height, msg.width)
    points = np.stack((data['x'], data['y'], data['z']), axis=-1)
    return points, data['label'].astype(np.uint8)
