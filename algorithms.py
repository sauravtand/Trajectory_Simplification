# algorithms.py
from math import sqrt

def perpendicular_distance(p, a, b):
    if a == b:
        return sqrt((p[0]-a[0])**2 + (p[1]-a[1])**2)
    x, y = p
    x1, y1 = a
    x2, y2 = b
    num = abs((y2 - y1)*x - (x2 - x1)*y + x2*y1 - y2*x1)
    den = sqrt((y2 - y1)**2 + (x2 - x1)**2)
    return num / den

# -----------------------------
# Douglas–Peucker (simple)
# -----------------------------
def rdp(points, epsilon):
    if len(points) < 3:
        return points

    max_dist = 0
    index = 0

    for i in range(1, len(points)-1):
        d = perpendicular_distance(points[i], points[0], points[-1])
        if d > max_dist:
            max_dist = d
            index = i

    if max_dist > epsilon:
        left = rdp(points[:index+1], epsilon)
        right = rdp(points[index:], epsilon)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]

# -----------------------------
# SQUISH (simple version)
# -----------------------------
def squish(points, k):
    if len(points) <= k:
        return points
    step = len(points) // k
    return points[::step]