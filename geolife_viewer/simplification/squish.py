# geolife_viewer/simplification/squish.py
from typing import List, Tuple
import heapq
from math import sqrt

Point = Tuple[float, float]

def _dist(a: Point, b: Point) -> float:
    return sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def _seg_perp_dist(p: Point, a: Point, b: Point) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    c1 = vx * wx + vy * wy
    if c1 <= 0:
        return _dist(p, a)
    c2 = vx * vx + vy * vy
    if c2 <= c1:
        return _dist(p, b)
    t = c1 / c2
    projx, projy = ax + t * vx, ay + t * vy
    return sqrt((px - projx) ** 2 + (py - projy) ** 2)

def _priority(prev_pt: Point, pt: Point, next_pt: Point) -> float:
    # local error (lower = more removable)
    return _seg_perp_dist(pt, prev_pt, next_pt)

def squish(points: List[Point], k: int, epsilon: float) -> List[Point]:
    """
    Streaming, memory-bounded simplification:
    - Keep endpoints.
    - Maintain a heap of interior points by priority (error).
    - If len(buffer) > k => remove lowest-priority point.
    - Also remove points with priority <= epsilon.
    """
    n = len(points)
    if n <= 2:
        return points[:]

    # Linked-list structure via index maps
    prev = {i: i-1 for i in range(n)}
    next_ = {i: i+1 for i in range(n)}
    alive = {i: True for i in range(n)}

    # heap of (priority, index)
    heap = []
    for i in range(1, n-1):
        pr = _priority(points[i-1], points[i], points[i+1])
        heapq.heappush(heap, (pr, i))

    kept = {0, n-1}
    kept_count = 2
    max_allowed = max(2, min(k, n))

    def _requeue(i: int):
        if 0 < i < n-1 and alive.get(i, False):
            li = prev[i]
            ri = next_[i]
            if 0 <= li < n and 0 <= ri < n and alive.get(li, False) and alive.get(ri, False):
                pr = _priority(points[li], points[i], points[ri])
                heapq.heappush(heap, (pr, i))

    while heap:
        pr, i = heapq.heappop(heap)
        if not alive.get(i, False) or i in (0, n-1):
            continue

        if kept_count >= max_allowed or pr <= epsilon:
            # remove i
            alive[i] = False
            li, ri = prev[i], next_[i]
            # stitch neighbors
            if 0 <= li < n:
                next_[li] = ri
            if 0 <= ri < n:
                prev[ri] = li
            # update neighbors
            if 0 < li < n-1 and alive.get(li, False):
                _requeue(li)
            if 0 < ri < n-1 and alive.get(ri, False):
                _requeue(ri)
        else:
            kept.add(i)
            kept_count += 1
            _requeue(i)

        if kept_count >= max_allowed and pr > epsilon:
            # we already kept enough points and current best error is above epsilon
            break

    # Reconstruct ordered points
    out = []
    idx = 0
    while True:
        if alive.get(idx, False) or idx in (0, n-1):
            out.append(points[idx])
        if idx == n-1:
            break
        idx = next_.get(idx, idx+1)

    # ensure endpoints present
    if out[0] != points[0]:
        out.insert(0, points[0])
    if out[-1] != points[-1]:
        out.append(points[-1])

    return out