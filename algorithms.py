import heapq
import math
import statistics
import time
from typing import Dict, Iterable, List, Sequence, Tuple

EARTH_RADIUS = 6_371_000

PointXY = Tuple[float, float]
PointLL = Tuple[float, float]
PointLLT = Tuple[float, float, float]


# ============================================================
# 1. LAT/LON <-> XY
# ============================================================

def latlon_to_xy(lat: float, lon: float, lat0: float = None) -> PointXY:
    """
    Convert latitude/longitude to planar XY meters using
    equirectangular approximation.
    """
    if lat0 is None:
        lat0 = lat

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lat0_rad = math.radians(lat0)

    x = EARTH_RADIUS * lon_rad * math.cos(lat0_rad)
    y = EARTH_RADIUS * lat_rad
    return x, y


def xy_to_latlon(x: float, y: float, lat0: float) -> PointLL:
    """
    Convert planar XY meters back to latitude/longitude.
    """
    lat = math.degrees(y / EARTH_RADIUS)
    lon = math.degrees(x / (EARTH_RADIUS * math.cos(math.radians(lat0))))
    return lat, lon


# ============================================================
# 2. BASIC HELPERS
# ============================================================

def point_distance(a: PointXY, b: PointXY) -> float:
    return math.dist(a, b)


def point_to_segment_distance(p: PointXY, a: PointXY, b: PointXY) -> float:
    """
    Minimum distance from point p to segment a-b.
    """
    if a == b:
        return point_distance(p, a)

    ax, ay = a
    bx, by = b
    px, py = p

    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay

    ab2 = abx * abx + aby * aby
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / max(ab2, 1e-12)))

    proj = (ax + t * abx, ay + t * aby)
    return point_distance(p, proj)


def perpendicular_distance(p: PointXY, a: PointXY, b: PointXY) -> float:
    """
    Perpendicular distance from point p to infinite line through a-b.
    """
    if a == b:
        return point_distance(p, a)

    x, y = p
    x1, y1 = a
    x2, y2 = b

    num = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1)
    den = point_distance(a, b)
    return num / max(den, 1e-12)


def triangle_area(a: PointXY, b: PointXY, c: PointXY) -> float:
    return abs(
        a[0] * (b[1] - c[1]) +
        b[0] * (c[1] - a[1]) +
        c[0] * (a[1] - b[1])
    ) / 2.0


def path_length(points: Sequence[PointXY]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(point_distance(points[i - 1], points[i]) for i in range(1, len(points)))


def median_absolute_deviation(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    med = statistics.median(values)
    return statistics.median(abs(v - med) for v in values)


def local_turn_angle(points: Sequence[PointXY], i: int) -> float:
    """
    Higher angle = more important turning point.
    """
    if i <= 0 or i >= len(points) - 1:
        return math.pi

    ax, ay = points[i - 1]
    bx, by = points[i]
    cx, cy = points[i + 1]

    v1 = (ax - bx, ay - by)
    v2 = (cx - bx, cy - by)

    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return 0.0

    cosang = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.acos(cosang)


def ensure_exact_target(
    indices: Iterable[int],
    n: int,
    target_k: int,
    points: Sequence[PointXY],
) -> List[int]:
    """
    Force the final simplified result to contain exactly target_k points.
    """
    idx = set(int(i) for i in indices)
    idx.add(0)
    idx.add(n - 1)

    if target_k >= n:
        return list(range(n))

    if len(idx) > target_k:
        removable = [i for i in idx if i not in {0, n - 1}]
        removable.sort(key=lambda i: (local_turn_angle(points, i), i))
        idx -= set(removable[: len(idx) - target_k])

    elif len(idx) < target_k:
        candidates = [i for i in range(1, n - 1) if i not in idx]
        candidates.sort(key=lambda i: (-local_turn_angle(points, i), i))
        idx.update(candidates[: target_k - len(idx)])

    return sorted(idx)


# ============================================================
# 3. OUTLIER REMOVAL (TIME + DISTANCE BASED)
# ============================================================

def remove_outliers_time_distance(
    points_xy: Sequence[PointXY],
    times: Sequence[float],
    max_speed_mps: float = 50.0,
    spike_ratio: float = 4.0,
    bridge_ratio: float = 0.25,
    z_thresh: float = 3.5,
):
    """
    Remove implausible spikes using both distance and time.

    A middle point is treated as an outlier when:
    - prev->curr speed is too high, and
    - curr->next speed is too high, and
    - prev and next are relatively close (spike / return behavior)

    Also applies a robust jump-distance test as backup.
    """
    n = len(points_xy)
    if n < 3:
        safe_times = list(times) if times is not None else [None] * n
        return list(points_xy), safe_times, {
            "removed": 0,
            "input": n,
            "output": n,
        }

    if times is None:
        times = [None] * n
    else:
        times = list(times)

    jumps = [point_distance(points_xy[i - 1], points_xy[i]) for i in range(1, n)]
    med_jump = statistics.median(jumps) if jumps else 0.0
    mad_jump = median_absolute_deviation(jumps)
    robust_scale = max(1.4826 * mad_jump, 1e-9)

    keep = [True] * n
    keep[0] = True
    keep[-1] = True

    for i in range(1, n - 1):
        prev_p = points_xy[i - 1]
        curr_p = points_xy[i]
        next_p = points_xy[i + 1]

        d1 = point_distance(prev_p, curr_p)
        d2 = point_distance(curr_p, next_p)
        d_bridge = point_distance(prev_p, next_p)

        t_prev = times[i - 1]
        t_curr = times[i]
        t_next = times[i + 1]

        has_time = (
            t_prev is not None and
            t_curr is not None and
            t_next is not None
        )

        is_outlier = False

        if has_time:
            dt1 = t_curr - t_prev
            dt2 = t_next - t_curr

            if dt1 <= 0 or dt2 <= 0:
                # invalid time ordering -> suspicious middle point
                is_outlier = True
            else:
                v1 = d1 / dt1
                v2 = d2 / dt2

                fast_spike = (
                    v1 > max_speed_mps and
                    v2 > max_speed_mps and
                    d_bridge < bridge_ratio * max(d1 + d2, 1e-9)
                )

                sharp_return = (
                    d1 > spike_ratio * max(d_bridge, 1.0) and
                    d2 > spike_ratio * max(d_bridge, 1.0)
                )

                is_outlier = fast_spike or sharp_return

        # Robust backup based on jump statistics
        z1 = abs(d1 - med_jump) / robust_scale
        z2 = abs(d2 - med_jump) / robust_scale
        robust_spike = (
            z1 > z_thresh and
            z2 > z_thresh and
            d_bridge < bridge_ratio * max(d1 + d2, 1e-9)
        )

        if is_outlier or robust_spike:
            keep[i] = False

    cleaned_points = [p for p, ok in zip(points_xy, keep) if ok]
    cleaned_times = [t for t, ok in zip(times, keep) if ok]

    return cleaned_points, cleaned_times, {
        "removed": n - len(cleaned_points),
        "input": n,
        "output": len(cleaned_points),
    }


# ============================================================
# 4. CLASSICAL SIMPLIFICATION ALGORITHMS
# ============================================================

# ------------------------------------------------------------
# 4.1 Douglas-Peucker
# ------------------------------------------------------------

def _dp_indices(points: Sequence[PointXY], start: int, end: int, eps: float, kept: set):
    if end <= start + 1:
        return

    max_dist = -1.0
    split_idx = None
    a = points[start]
    b = points[end]

    for i in range(start + 1, end):
        d = perpendicular_distance(points[i], a, b)
        if d > max_dist:
            max_dist = d
            split_idx = i

    if split_idx is not None and max_dist > eps:
        kept.add(split_idx)
        _dp_indices(points, start, split_idx, eps, kept)
        _dp_indices(points, split_idx, end, eps, kept)


def simpl_dp(points: Sequence[PointXY], target_k: int) -> List[PointXY]:
    if len(points) <= target_k:
        return list(points)

    def run(eps: float) -> List[int]:
        kept = {0, len(points) - 1}
        _dp_indices(points, 0, len(points) - 1, eps, kept)
        return sorted(kept)

    lo = 0.0
    hi = max(path_length(points), 1.0)
    best_idx = list(range(len(points)))

    for _ in range(32):
        mid = (lo + hi) / 2.0
        idx = run(mid)
        if len(idx) > target_k:
            lo = mid
        else:
            best_idx = idx
            hi = mid

    best_idx = ensure_exact_target(best_idx, len(points), target_k, points)
    return [points[i] for i in best_idx]


# ------------------------------------------------------------
# 4.2 Visvalingam-Whyatt
# ------------------------------------------------------------

def simpl_vw(points: Sequence[PointXY], target_k: int) -> List[PointXY]:
    n = len(points)
    if n <= target_k:
        return list(points)

    prev_idx = [i - 1 for i in range(n)]
    next_idx = [i + 1 for i in range(n)]
    next_idx[-1] = -1
    removed = [False] * n
    heap = []

    def push(i: int):
        if i <= 0 or i >= n - 1 or removed[i]:
            return
        a = prev_idx[i]
        c = next_idx[i]
        if a == -1 or c == -1:
            return
        area = triangle_area(points[a], points[i], points[c])
        heapq.heappush(heap, (area, i, a, c))

    for i in range(1, n - 1):
        push(i)

    alive = n
    while alive > target_k and heap:
        _, i, old_prev, old_next = heapq.heappop(heap)

        if removed[i] or prev_idx[i] != old_prev or next_idx[i] != old_next:
            continue

        removed[i] = True
        alive -= 1

        a = prev_idx[i]
        c = next_idx[i]

        if a != -1:
            next_idx[a] = c
        if c != -1:
            prev_idx[c] = a

        push(a)
        push(c)

    idx = [i for i in range(n) if not removed[i]]
    idx = ensure_exact_target(idx, n, target_k, points)
    return [points[i] for i in idx]


# ------------------------------------------------------------
# 4.3 Sliding Window
# ------------------------------------------------------------

def simpl_sw(points: Sequence[PointXY], target_k: int) -> List[PointXY]:
    n = len(points)
    if n <= target_k:
        return list(points)

    def run(eps: float) -> List[int]:
        kept = [0]
        start = 0
        i = 1

        while i < n - 1:
            valid = True
            for j in range(start + 1, i + 1):
                if perpendicular_distance(points[j], points[start], points[i + 1]) > eps:
                    valid = False
                    break

            if not valid:
                kept.append(i)
                start = i

            i += 1

        if kept[-1] != n - 1:
            kept.append(n - 1)

        return kept

    lo = 0.0
    hi = max(path_length(points), 1.0)
    best_idx = list(range(n))

    for _ in range(32):
        mid = (lo + hi) / 2.0
        idx = run(mid)
        if len(idx) > target_k:
            lo = mid
        else:
            best_idx = idx
            hi = mid

    best_idx = ensure_exact_target(best_idx, n, target_k, points)
    return [points[i] for i in best_idx]


# ------------------------------------------------------------
# 4.4 Reumann-Witkam
# ------------------------------------------------------------

def simpl_rw(points: Sequence[PointXY], target_k: int) -> List[PointXY]:
    n = len(points)
    if n <= target_k:
        return list(points)

    def run(strip: float) -> List[int]:
        kept = [0]
        anchor = 0
        ref = 1

        for i in range(2, n):
            if perpendicular_distance(points[i], points[anchor], points[ref]) > strip:
                kept.append(i - 1)
                anchor = i - 1
                ref = i

        if kept[-1] != n - 1:
            kept.append(n - 1)

        return kept

    lo = 0.0
    hi = max(path_length(points), 1.0)
    best_idx = list(range(n))

    for _ in range(32):
        mid = (lo + hi) / 2.0
        idx = run(mid)
        if len(idx) > target_k:
            lo = mid
        else:
            best_idx = idx
            hi = mid

    best_idx = ensure_exact_target(best_idx, n, target_k, points)
    return [points[i] for i in best_idx]


# ------------------------------------------------------------
# 4.5 SQUISH
# ------------------------------------------------------------

def simpl_squish(points: Sequence[PointXY], target_k: int) -> List[PointXY]:
    """
    Priority-based SQUISH-style simplification.
    Removes points with the smallest local importance first.
    """
    n = len(points)
    if n <= target_k:
        return list(points)

    prev_idx = [i - 1 for i in range(n)]
    next_idx = [i + 1 for i in range(n)]
    next_idx[-1] = -1
    removed = [False] * n
    heap = []

    def local_priority(i: int) -> float:
        if i <= 0 or i >= n - 1 or removed[i]:
            return float("inf")

        a = prev_idx[i]
        c = next_idx[i]
        if a == -1 or c == -1:
            return float("inf")

        return point_to_segment_distance(points[i], points[a], points[c])

    def push(i: int):
        if i <= 0 or i >= n - 1 or removed[i]:
            return
        p = local_priority(i)
        heapq.heappush(heap, (p, i, prev_idx[i], next_idx[i]))

    for i in range(1, n - 1):
        push(i)

    alive = n
    while alive > target_k and heap:
        priority, i, old_prev, old_next = heapq.heappop(heap)

        if removed[i]:
            continue
        if prev_idx[i] != old_prev or next_idx[i] != old_next:
            continue

        removed[i] = True
        alive -= 1

        a = prev_idx[i]
        c = next_idx[i]

        if a != -1:
            next_idx[a] = c
        if c != -1:
            prev_idx[c] = a

        push(a)
        push(c)

    idx = [i for i in range(n) if not removed[i]]
    idx = ensure_exact_target(idx, n, target_k, points)
    return [points[i] for i in idx]


# ============================================================
# 5. ERROR METRICS
# ============================================================

def compute_error_metrics(original: Sequence[PointXY], simplified: Sequence[PointXY]) -> Dict[str, float]:
    """
    Compare original polyline to simplified polyline using point-to-segment distances.
    """
    if not original or not simplified:
        return {
            "sum": 0.0,
            "mean": 0.0,
            "rmse": 0.0,
            "max": 0.0,
            "length_ratio": 0.0,
        }

    if len(simplified) == 1:
        errs = [point_distance(p, simplified[0]) for p in original]
    else:
        errs = []
        for p in original:
            best = float("inf")
            for i in range(len(simplified) - 1):
                d = point_to_segment_distance(p, simplified[i], simplified[i + 1])
                if d < best:
                    best = d
            errs.append(best)

    sum_err = sum(errs)
    mean_err = sum_err / len(errs) if errs else 0.0
    rmse = math.sqrt(sum(e * e for e in errs) / len(errs)) if errs else 0.0
    max_err = max(errs) if errs else 0.0

    orig_len = path_length(original)
    simpl_len = path_length(simplified)
    length_ratio = (simpl_len / orig_len) if orig_len > 0 else 1.0

    return {
        "sum": sum_err,
        "mean": mean_err,
        "rmse": rmse,
        "max": max_err,
        "length_ratio": length_ratio,
    }


# ============================================================
# 6. MAIN WRAPPER
# ============================================================

def simplify_all_algorithms(latlon_points, removal_rate=0.50):
    """
    Full pipeline:
    1) lat/lon -> XY
    2) remove outliers using time + distance
    3) simplify with same target point count for all algorithms
    4) compute comparable metrics
    """
    if not latlon_points:
        return [], {}, {}

    # Input may be [(lat, lon), ...] or [(lat, lon, t), ...]
    has_time = len(latlon_points[0]) >= 3
    lat0 = float(latlon_points[0][0])

    coords_xy = []
    times = []

    for p in latlon_points:
        lat = float(p[0])
        lon = float(p[1])
        coords_xy.append(latlon_to_xy(lat, lon, lat0))
        times.append(float(p[2]) if has_time and p[2] is not None else None)

    cleaned_xy, cleaned_times, outlier_info = remove_outliers_time_distance(
        coords_xy,
        times,
        max_speed_mps=50.0,
        spike_ratio=4.0,
        bridge_ratio=0.25,
        z_thresh=3.5,
    )

    if len(cleaned_xy) < 2:
        return cleaned_xy, {}, {}

    target_k = max(2, int(round(len(cleaned_xy) * (1.0 - removal_rate))))
    target_k = min(target_k, len(cleaned_xy))

    algorithms = {
        "DP": simpl_dp,
        "SQUISH": simpl_squish,
        "VW": simpl_vw,
        "SW": simpl_sw,
        "RW": simpl_rw,
    }

    results = {}
    metrics = {}

    for name, func in algorithms.items():
        start = time.perf_counter()
        simplified = func(cleaned_xy, target_k)
        runtime_ms = (time.perf_counter() - start) * 1000.0

        results[name] = simplified

        err = compute_error_metrics(cleaned_xy, simplified)
        err["runtime_ms"] = runtime_ms
        err["kept_points"] = len(simplified)
        err["removed_points"] = len(cleaned_xy) - len(simplified)
        err["outliers_removed"] = outlier_info["removed"]
        metrics[name] = err

    return cleaned_xy, results, metrics