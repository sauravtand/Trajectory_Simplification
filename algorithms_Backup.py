import heapq
import math
import statistics
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

EARTH_RADIUS = 6_371_000

PointXY = Tuple[float, float]
PointXYT = Tuple[float, float, Optional[float]]


# ============================================================
# 1. LAT/LON <-> XY
# ============================================================

def latlon_to_xy(lat: float, lon: float, lat0: Optional[float] = None) -> PointXY:
    if lat0 is None:
        lat0 = lat
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lat0_rad = math.radians(lat0)
    x = EARTH_RADIUS * lon_rad * math.cos(lat0_rad)
    y = EARTH_RADIUS * lat_rad
    return x, y


def xy_to_latlon(x: float, y: float, lat0: float) -> Tuple[float, float]:
    lat = math.degrees(y / EARTH_RADIUS)
    lon = math.degrees(x / (EARTH_RADIUS * math.cos(math.radians(lat0))))
    return lat, lon


# ============================================================
# 2. BASIC HELPERS
# ============================================================

def point_distance(a: PointXY, b: PointXY) -> float:
    return math.dist(a, b)


def segment_length(a: PointXY, b: PointXY) -> float:
    return point_distance(a, b)


def path_length(points: Sequence[PointXY]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(point_distance(points[i - 1], points[i]) for i in range(1, len(points)))


def point_to_segment_distance(p: PointXY, a: PointXY, b: PointXY) -> float:
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


def median_absolute_deviation(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    med = statistics.median(values)
    return statistics.median(abs(v - med) for v in values)


def angle_of_segment(a: PointXY, b: PointXY) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def angle_diff_rad(a1: float, a2: float) -> float:
    d = abs(a1 - a2)
    return min(d, 2.0 * math.pi - d)


def local_turn_angle(points: Sequence[PointXY], i: int) -> float:
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


def exact_target_indices(indices: Iterable[int], n: int, target_k: int, points: Sequence[PointXY]) -> List[int]:
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
# 3. 9IER REMOVAL (TIME + DISTANCE)
# ============================================================

def remove_outliers_time_distance(
    points_xy: Sequence[PointXY],
    times: Sequence[Optional[float]],
    max_speed_mps: float = 50.0,
    spike_ratio: float = 4.0,
    bridge_ratio: float = 0.25,
    z_thresh: float = 3.5,
):
    n = len(points_xy)
    if n < 3:
        return list(points_xy), list(times), {"removed": 0, "input": n, "output": n}

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
        has_time = t_prev is not None and t_curr is not None and t_next is not None

        temporal_spike = False
        if has_time:
            dt1 = t_curr - t_prev
            dt2 = t_next - t_curr
            if dt1 <= 0 or dt2 <= 0:
                temporal_spike = True
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
                temporal_spike = fast_spike or sharp_return

        z1 = abs(d1 - med_jump) / robust_scale
        z2 = abs(d2 - med_jump) / robust_scale
        robust_spike = (
            z1 > z_thresh and
            z2 > z_thresh and
            d_bridge < bridge_ratio * max(d1 + d2, 1e-9)
        )

        if temporal_spike or robust_spike:
            keep[i] = False

    cleaned_points = [p for p, ok in zip(points_xy, keep) if ok]
    cleaned_times = [t for t, ok in zip(times, keep) if ok]
    return cleaned_points, cleaned_times, {
        "removed": n - len(cleaned_points),
        "input": n,
        "output": len(cleaned_points),
    }


# ============================================================
# 4. CLASSICAL SIMPLIFICATION METHODS
# ============================================================

def _dp_keep(points: Sequence[PointXY], start: int, end: int, eps: float, kept: set):
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
        _dp_keep(points, start, split_idx, eps, kept)
        _dp_keep(points, split_idx, end, eps, kept)


def simpl_dp_indices(points: Sequence[PointXY], target_k: int) -> List[int]:
    if len(points) <= target_k:
        return list(range(len(points)))

    def run(eps: float) -> List[int]:
        kept = {0, len(points) - 1}
        _dp_keep(points, 0, len(points) - 1, eps, kept)
        return sorted(kept)

    lo, hi = 0.0, max(path_length(points), 1.0)
    best = list(range(len(points)))
    for _ in range(32):
        mid = (lo + hi) / 2.0
        idx = run(mid)
        if len(idx) > target_k:
            lo = mid
        else:
            best = idx
            hi = mid
    return exact_target_indices(best, len(points), target_k, points)


def simpl_vw_indices(points: Sequence[PointXY], target_k: int) -> List[int]:
    n = len(points)
    if n <= target_k:
        return list(range(n))

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
    return exact_target_indices(idx, n, target_k, points)


def simpl_sliding_indices(points: Sequence[PointXY], target_k: int) -> List[int]:
    n = len(points)
    if n <= target_k:
        return list(range(n))

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

    lo, hi = 0.0, max(path_length(points), 1.0)
    best = list(range(n))
    for _ in range(32):
        mid = (lo + hi) / 2.0
        idx = run(mid)
        if len(idx) > target_k:
            lo = mid
        else:
            best = idx
            hi = mid
    return exact_target_indices(best, n, target_k, points)


def simpl_rw_indices(points: Sequence[PointXY], target_k: int) -> List[int]:
    n = len(points)
    if n <= target_k:
        return list(range(n))

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

    lo, hi = 0.0, max(path_length(points), 1.0)
    best = list(range(n))
    for _ in range(32):
        mid = (lo + hi) / 2.0
        idx = run(mid)
        if len(idx) > target_k:
            lo = mid
        else:
            best = idx
            hi = mid
    return exact_target_indices(best, n, target_k, points)


def simpl_squish_indices(points: Sequence[PointXY], target_k: int) -> List[int]:
    n = len(points)
    if n <= target_k:
        return list(range(n))

    prev_idx = [i - 1 for i in range(n)]
    next_idx = [i + 1 for i in range(n)]
    next_idx[-1] = -1
    removed = [False] * n
    heap = []

    def priority(i: int) -> float:
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
        heapq.heappush(heap, (priority(i), i, prev_idx[i], next_idx[i]))

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
    return exact_target_indices(idx, n, target_k, points)


# ============================================================
# 5. ERROR METRICS FROM THE PAPERS
# ============================================================

def aggregate(values: Sequence[float]) -> Dict[str, float]:
    if not values:
        return {"max": 0.0, "mean": 0.0, "rmse": 0.0, "sum": 0.0}
    total = sum(values)
    return {
        "max": max(values),
        "mean": total / len(values),
        "rmse": math.sqrt(sum(v * v for v in values) / len(values)),
        "sum": total,
    }


def synchronized_point(a: PointXY, ta: Optional[float], b: PointXY, tb: Optional[float], t: Optional[float]) -> Optional[PointXY]:
    if ta is None or tb is None or t is None:
        return None
    dt = tb - ta
    if dt <= 0:
        return None
    alpha = (t - ta) / dt
    x = a[0] + alpha * (b[0] - a[0])
    y = a[1] + alpha * (b[1] - a[1])
    return x, y


def safe_speed(a: PointXY, ta: Optional[float], b: PointXY, tb: Optional[float]) -> Optional[float]:
    if ta is None or tb is None:
        return None
    dt = tb - ta
    if dt <= 0:
        return None
    return point_distance(a, b) / dt


def compute_anchor_error_metrics(
    original_points: Sequence[PointXY],
    original_times: Sequence[Optional[float]],
    kept_indices: Sequence[int],
) -> Dict[str, float]:
    ped_vals: List[float] = []
    sed_vals: List[float] = []
    dad_vals_rad: List[float] = []
    sad_vals: List[float] = []
    issd_sum = 0.0

    for left, right in zip(kept_indices[:-1], kept_indices[1:]):
        a = original_points[left]
        b = original_points[right]
        ta = original_times[left]
        tb = original_times[right]
        anchor_angle = angle_of_segment(a, b)
        anchor_speed = safe_speed(a, ta, b, tb)

        for i in range(left, right):
            p = original_points[i]
            ped = perpendicular_distance(p, a, b)
            ped_vals.append(ped)

            sp = synchronized_point(a, ta, b, tb, original_times[i])
            if sp is not None:
                sed = point_distance(p, sp)
                sed_vals.append(sed)
                issd_sum += sed * sed

            if i + 1 <= right:
                local_angle = angle_of_segment(original_points[i], original_points[i + 1])
                dad_vals_rad.append(angle_diff_rad(anchor_angle, local_angle))
                local_speed = safe_speed(original_points[i], original_times[i], original_points[i + 1], original_times[i + 1])
                if anchor_speed is not None and local_speed is not None:
                    sad_vals.append(abs(anchor_speed - local_speed))

    ped_agg = aggregate(ped_vals)
    sed_agg = aggregate(sed_vals)
    dad_agg = aggregate(dad_vals_rad)
    sad_agg = aggregate(sad_vals)

    return {
        "PED_max": ped_agg["max"],
        "PED_mean": ped_agg["mean"],
        "PED_rmse": ped_agg["rmse"],
        "SED_max": sed_agg["max"],
        "SED_mean": sed_agg["mean"],
        "SED_rmse": sed_agg["rmse"],
        "DAD_max_deg": math.degrees(dad_agg["max"]),
        "DAD_mean_deg": math.degrees(dad_agg["mean"]),
        "SAD_max": sad_agg["max"],
        "SAD_mean": sad_agg["mean"],
        "ISSD": issd_sum,
    }


# ============================================================
# 6. MAIN WRAPPER
# ============================================================

def simplify_all_algorithms(latlon_points, removal_rate: float = 0.50):
    if not latlon_points:
        return [], {}, {}, {}

    has_time = len(latlon_points[0]) >= 3
    lat0 = float(latlon_points[0][0])

    coords_xy: List[PointXY] = []
    times: List[Optional[float]] = []
    for p in latlon_points:
        lat = float(p[0])
        lon = float(p[1])
        coords_xy.append(latlon_to_xy(lat, lon, lat0))
        times.append(float(p[2]) if has_time and p[2] is not None else None)

    cleaned_xy, cleaned_times, outlier_info = remove_outliers_time_distance(coords_xy, times)
    if len(cleaned_xy) < 2:
        return cleaned_xy, {}, {}, outlier_info

    target_k = max(2, int(round(len(cleaned_xy) * (1.0 - removal_rate))))
    target_k = min(target_k, len(cleaned_xy))

    algorithms = {
        "DP": simpl_dp_indices,
        "SQUISH": simpl_squish_indices,
        "VW": simpl_vw_indices,
        "SW": simpl_sliding_indices,
        "RW": simpl_rw_indices,
    }

    results: Dict[str, List[PointXY]] = {}
    metrics: Dict[str, Dict[str, float]] = {}

    for name, func in algorithms.items():
        start = time.perf_counter()
        kept_idx = func(cleaned_xy, target_k)
        runtime_ms = (time.perf_counter() - start) * 1000.0
        simplified = [cleaned_xy[i] for i in kept_idx]
        results[name] = simplified

        m = compute_anchor_error_metrics(cleaned_xy, cleaned_times, kept_idx)
        m["runtime_ms"] = runtime_ms
        m["kept_points"] = len(kept_idx)
        m["removed_points"] = len(cleaned_xy) - len(kept_idx)
        m["outliers_removed"] = outlier_info["removed"]
        m["compression_ratio"] = len(kept_idx) / len(cleaned_xy)
        orig_len = path_length(cleaned_xy)
        simp_len = path_length(simplified)
        m["length_ratio"] = (simp_len / orig_len) if orig_len > 0 else 1.0
        metrics[name] = m

    return cleaned_xy, results, metrics, outlier_info
