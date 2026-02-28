# geolife_viewer/simplification/rdp.py
from math import sqrt
from typing import List, Tuple

Point = Tuple[float, float]

def _point_segment_dist(p: Point, a: Point, b: Point) -> float:
    # perpendicular distance from p to segment ab
    (px, py), (ax, ay), (bx, by) = p, a, b
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    c1 = vx * wx + vy * wy
    if c1 <= 0:  # before a
        return sqrt((px - ax) ** 2 + (py - ay) ** 2)
    c2 = vx * vx + vy * vy
    if c2 <= c1:  # after b
        return sqrt((px - bx) ** 2 + (py - by) ** 2)
    t = c1 / c2
    projx, projy = ax + t * vx, ay + t * vy
    return sqrt((px - projx) ** 2 + (py - projy) ** 2)

def douglas_peucker(points: List[Point], epsilon: float) -> List[Point]:
    if len(points) <= 2:
        return points
    a, b = points[0], points[-1]
    max_d, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = _point_segment_dist(points[i], a, b)
        if d > max_d:
            max_d, idx = d, i
    if max_d > epsilon:
        left = douglas_peucker(points[: idx + 1], epsilon)
        right = douglas_peucker(points[idx:], epsilon)
        return left[:-1] + right
    else:
        return [a, b]
