# algorithms.py
import math
import statistics

# ============================================================
# 1. LAT/LON → METERS (Equirectangular Approximation)
# ============================================================

EARTH_RADIUS = 6371000  # meters

def latlon_to_xy(lat, lon, lat0=None):
    """
    Converts lat/lon (degrees) to (x, y) in meters.
    lat0 is reference latitude for scale (use first point).
    """
    if lat0 is None:
        lat0 = lat
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lat0_rad = math.radians(lat0)

    x = EARTH_RADIUS * (lon_rad) * math.cos(lat0_rad)
    y = EARTH_RADIUS * (lat_rad)
    return x, y


# ============================================================
# 2. OUTLIER REMOVAL
# ============================================================

def remove_outliers_speed(points, speed_threshold=300_000 / 3600):
    """
    Remove outliers based on unrealistic speed jumps.
    speed_threshold default = 300 km/h in m/s.
    """
    if len(points) < 3:
        return points

    cleaned = [points[0]]
    for i in range(1, len(points) - 1):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]
        x3, y3 = points[i + 1]
        d1 = math.dist((x1, y1), (x2, y2))
        d2 = math.dist((x2, y2), (x3, y3))

        if d1 > speed_threshold or d2 > speed_threshold:
            continue

        cleaned.append(points[i])

    cleaned.append(points[-1])
    return cleaned


def remove_outliers_zscore(points, z_thresh=3.0):
    """
    Remove points where distance jumps are statistical outliers.
    """
    if len(points) < 3:
        return points

    dists = []
    for i in range(1, len(points)):
        d = math.dist(points[i - 1], points[i])
        dists.append(d)

    if len(dists) < 2:
        return points

    mean = statistics.mean(dists)
    stdev = statistics.stdev(dists)

    cleaned = [points[0]]
    for i in range(1, len(points) - 1):
        d = math.dist(points[i - 1], points[i])
        if abs(d - mean) / stdev < z_thresh:
            cleaned.append(points[i])

    cleaned.append(points[-1])
    return cleaned


def remove_outliers(points):
    """
    Combined outlier filter: speed + zscore.
    """
    pts = remove_outliers_speed(points)
    pts = remove_outliers_zscore(pts)
    return pts


# ============================================================
# 3. CORE GEOMETRY HELPERS
# ============================================================

def perpendicular_distance(p, a, b):
    if a == b:
        return math.dist(p, a)
    x, y = p
    x1, y1 = a
    x2, y2 = b
    num = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1)
    den = math.dist(a, b)
    return num / den


# ============================================================
# 4. ALGORITHMS
# ============================================================

# -------------------
# Douglas–Peucker
# -------------------
def dp_recursive(points, eps):
    if len(points) < 3:
        return points
    max_dist = 0
    index = 0
    for i in range(1, len(points) - 1):
        d = perpendicular_distance(points[i], points[0], points[-1])
        if d > max_dist:
            max_dist = d
            index = i
    if max_dist > eps:
        left = dp_recursive(points[:index + 1], eps)
        right = dp_recursive(points[index:], eps)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


def simpl_dp(points, target_k):
    # binary search on epsilon
    lo, hi = 0, 5000  # reasonable eps range in meters
    best = points

    for _ in range(20):
        mid = (lo + hi) / 2
        s = dp_recursive(points, mid)
        if len(s) > target_k:
            lo = mid
        else:
            best = s
            hi = mid
    return best


# -------------------
# SQUISH
# -------------------
def simpl_squish(points, target_k):
    lo, hi = 2, len(points)
    best = points

    for _ in range(20):
        mid = (lo + hi) // 2
        step = max(1, len(points) // mid)
        s = points[::step]

        if len(s) > target_k:
            lo = mid + 1
        else:
            best = s
            hi = mid - 1
    return best


# -------------------
# Visvalingam–Whyatt
# -------------------
def triangle_area(a, b, c):
    return abs(
        a[0] * (b[1] - c[1]) +
        b[0] * (c[1] - a[1]) +
        c[0] * (a[1] - b[1])
    ) / 2


def simpl_vw(points, target_k):
    if len(points) <= target_k:
        return points

    # compute areas
    areas = []
    for i in range(1, len(points) - 1):
        area = triangle_area(points[i - 1], points[i], points[i + 1])
        areas.append((area, i))

    # sort by area (smallest gets removed first)
    areas.sort(key=lambda x: x[0])

    # determine cutoff
    remove_count = len(points) - target_k
    remove_idx = set([idx for area, idx in areas[:remove_count]])

    result = []
    for i, p in enumerate(points):
        if i not in remove_idx:
            result.append(p)
    return result


# -------------------
# Sliding Window
# -------------------
def simpl_sliding(points, target_k):
    lo, hi = 2, len(points)
    best = points
    for _ in range(20):
        mid = (lo + hi) // 2
        window = max(2, len(points) // mid)

        kept = []
        i = 0
        while i < len(points):
            kept.append(points[i])
            i += window

        if len(kept) > target_k:
            lo = mid + 1
        else:
            best = kept
            hi = mid - 1
    return best


# -------------------
# Reumann–Witkam
# -------------------
def simpl_rw(points, target_k):
    lo, hi = 1, 2000  # strip width in meters
    best = points

    for _ in range(20):
        strip = (lo + hi) / 2

        kept = [points[0]]
        a = points[0]
        b = points[1]

        vx = b[0] - a[0]
        vy = b[1] - a[1]
        norm = math.hypot(vx, vy)
        if norm == 0:
            vx = 1
            vy = 0
        else:
            vx /= norm
            vy /= norm

        for p in points[2:]:
            # perpendicular distance to line a->b
            d = abs((p[0] - a[0]) * vy - (p[1] - a[1]) * vx)
            if d > strip:
                kept.append(p)
                a = kept[-2]
                b = kept[-1]
                vx = b[0] - a[0]
                vy = b[1] - a[1]
                norm = math.hypot(vx, vy)
                if norm != 0:
                    vx /= norm
                    vy /= norm

        kept.append(points[-1])

        if len(kept) > target_k:
            lo = strip
        else:
            best = kept
            hi = strip

    return best


# ============================================================
# 5. ERROR METRICS
# ============================================================

def compute_sed(original, simplified):
    """
    Compute SED-like errors by pairing each original point with its nearest
    segment in simplified curve.
    """
    def point_segment_dist(p, a, b):
        if a == b:
            return math.dist(p, a)
        ax, ay = a
        bx, by = b
        px, py = p
        t = max(0, min(1, ((px - ax)*(bx - ax) + (py - ay)*(by - ay)) /
                        ((bx - ax)**2 + (by - ay)**2)))
        proj = (ax + t*(bx - ax), ay + t*(by - ay))
        return math.dist(p, proj)

    errs = []
    for p in original:
        best = float("inf")
        for i in range(len(simplified) - 1):
            d = point_segment_dist(p, simplified[i], simplified[i+1])
            best = min(best, d)
        errs.append(best)

    return {
        "sum": sum(errs),
        "mean": sum(errs) / len(errs),
        "max": max(errs)
    }


# ============================================================
# 6. MAIN SIMPLIFICATION WRAPPER
# ============================================================

def simplify_all_algorithms(latlon_points, removal_rate=0.50):
    """
    Converts input lat/lon -> xy meters,
    removes outliers,
    runs all algorithms with same keep-count,
    returns dictionary of results.
    """

    # 1) convert
    lat0 = latlon_points[0][0]
    pts_xy = [latlon_to_xy(lat, lon, lat0) for lat, lon in latlon_points]

    # 2) remove outliers
    pts_xy = remove_outliers(pts_xy)

    # 3) compute target K
    target_k = max(2, int(len(pts_xy) * (1 - removal_rate)))

    # 4) run algorithms
    results = {}
    results["DP"] = simpl_dp(pts_xy, target_k)
    results["SQUISH"] = simpl_squish(pts_xy, target_k)
    results["VW"] = simpl_vw(pts_xy, target_k)
    results["SW"] = simpl_sliding(pts_xy, target_k)
    results["RW"] = simpl_rw(pts_xy, target_k)

    # 5) compute errors
    errors = {}
    for name, pts in results.items():
        errors[name] = compute_sed(pts_xy, pts)

    return pts_xy, results, errors