"""Turning a coordinate system by dragging a ring around one of its axes.

The geometry and the angle arithmetic live here, apart from Qt and VTK, so
the fiddly part — which way a drag turns the frame, and by how much — can be
tested without a window.

A coordinate system is stored as four rows: three orthonormal basis vectors
and an origin. Rotation only ever touches the basis; the origin stays put.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike

RING_STEPS = 96          # points around a ring: enough that picking is smooth


def rotation_about(axis: ArrayLike, angle: float) -> np.ndarray:
    """The 3x3 rotation of `angle` radians about a unit `axis`.

    Rodrigues' formula, written out rather than pulled from a library:
    scipy is not a dependency and this is four lines.
    """
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    cross = np.array([[0.0, -axis[2], axis[1]],
                      [axis[2], 0.0, -axis[0]],
                      [-axis[1], axis[0], 0.0]])
    return (np.eye(3) + np.sin(angle) * cross
            + (1.0 - np.cos(angle)) * (cross @ cross))


def ring_points(matrix: ArrayLike, axis: int, radius: float,
                steps: int = RING_STEPS) -> np.ndarray:
    """A closed ring of points around one principal axis of a frame.

    The ring for the X axis lies in the frame's own Y-Z plane, so it is the
    circle you would sweep by turning about X.
    """
    matrix = np.asarray(matrix, dtype=np.float64)
    origin = matrix[3]
    first, second = ((axis + 1) % 3, (axis + 2) % 3)
    angle = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)[:, np.newaxis]
    return origin + radius * (np.cos(angle) * matrix[first]
                              + np.sin(angle) * matrix[second])


def rotate_frame(matrix: ArrayLike, axis: int, angle: float) -> np.ndarray:
    """A copy of `matrix` with its basis turned about one of its own axes.

    The axis travels with the frame — turning about X twice by 45 degrees
    is turning about that same X by 90, not about the world's X.
    """
    matrix = np.array(matrix, dtype=np.float64)
    turned = np.array(matrix)
    turned[:3] = matrix[:3] @ rotation_about(matrix[axis], angle).T
    return turned


def angle_in_plane(matrix: ArrayLike, axis: int,
                   point: ArrayLike) -> float:
    """Where a world point sits around one principal axis, in radians.

    Measured in the ring's own plane from the first of the two axes it
    spans, so it pairs with `ring_points`.
    """
    matrix = np.asarray(matrix, dtype=np.float64)
    offset = np.asarray(point, dtype=np.float64) - matrix[3]
    first, second = ((axis + 1) % 3, (axis + 2) % 3)
    return float(np.arctan2(offset @ matrix[second], offset @ matrix[first]))


def wrapped(angle: float) -> float:
    """An angle folded into [-pi, pi), so a drag past the seam stays small.

    A drag from 179 to -179 degrees is two degrees, not 358.
    """
    return float((angle + np.pi) % (2.0 * np.pi) - np.pi)


def ring_under_cursor(rings: Sequence[tuple[int, np.ndarray]],
                      cursor: ArrayLike,
                      tolerance: float = 14.0) -> int | None:
    """Which ring a pixel is over, or None.

    `rings` is a list of (axis, screen points). The nearest ring within the
    tolerance wins; the rings cross each other, so ties go to whichever is
    genuinely closer rather than to whichever was drawn first.
    """
    cursor = np.asarray(cursor, dtype=np.float64)
    best, best_distance = None, tolerance
    for axis, points in rings:
        if not len(points):
            continue
        distance = float(np.linalg.norm(points - cursor, axis=1).min())
        if distance < best_distance:
            best, best_distance = axis, distance
    return best


def plane_hit(origin: ArrayLike, normal: ArrayLike, eye: ArrayLike,
              direction: ArrayLike) -> np.ndarray | None:
    """Where a ray meets the plane through `origin`, or None if parallel.

    Dragging a ring means following the cursor around the plane the ring
    lies in, which is what this finds.
    """
    normal = np.asarray(normal, dtype=np.float64)
    direction = np.asarray(direction, dtype=np.float64)
    along = float(normal @ direction)
    if abs(along) < 1e-9:
        return None
    distance = float(normal @ (np.asarray(origin, dtype=np.float64)
                               - np.asarray(eye, dtype=np.float64))) / along
    return np.asarray(eye, dtype=np.float64) + distance * direction


def identity_frame(matrix: ArrayLike) -> np.ndarray:
    """The frame with its rotation undone, keeping where it sits."""
    matrix = np.asarray(matrix, dtype=np.float64)
    reset = np.zeros_like(matrix)
    reset[:3] = np.eye(3)
    reset[3] = matrix[3]
    return reset
