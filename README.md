
# Trajectory Simplification – What Changes, How It Works, and What It Optimizes

This README explains—in practical, plain terms—**what** the simplification does to your GPS/trajectory data, **how** each algorithm makes its decisions, and **what each method optimizes** (point reduction vs. accuracy vs. memory/latency). It’s written to match the simple Folium + Tkinter app you’re using.

---

## Quick Summary

- **Goal of simplification**: Replace a long, noisy polyline with a shorter one that keeps the important shape.
- **Why**: Faster rendering, smaller files, clearer visuals, and quicker exploration.
- **Two algorithms included**:
  - **Douglas–Peucker (RDP)** → Optimizes **shape accuracy** subject to a tolerance **ε** (epsilon). Fewer points as ε grows.
  - **SQUISH (streaming, memory-bounded)** → Optimizes **point count / memory** via a capacity **k** (and optionally an error threshold ε). Faster and scalable on long traces.

---

## Key Terms

- **Point**: A coordinate `(lat, lon)`.
- **Segment**: Straight line between two points.
- **Perpendicular distance**: Shortest Euclidean distance from a point to a segment.
- **ε (epsilon)**: Tolerance (how much deviation from the original you allow). Larger ε ⇒ more simplification (fewer points).
- **k (capacity)**: Upper bound on retained points (besides endpoints) for SQUISH. Smaller k ⇒ fewer points.

> **Units note**: In the simple app, distances are computed in **degrees** (lon/lat). For strict metric tolerances (meters), project to a metric CRS or replace the distance with a geodesic version.

---

## What Does Simplification Change?

### Visual Changes

- **Small wiggles and micro-zigzags** are removed.
- Long straight sections become **clean, straight segments**.
- Curves are retained with fewer key vertices, keeping the **overall shape**.

### Quantitative Changes (shown in tooltips)

- **Point count reduction**: e.g., `Original: 3241 pts → Simplified: 143 pts (–95.6%)`.
- **Start/end** stay the same (we always keep endpoints).

### What Stays the Same

- The **ordering** of points along the path.
- The **connectivity** (no jumps between unrelated parts; still a single polyline per trajectory).

---

## Algorithm 1 – Douglas–Peucker (RDP)

**What it focuses on:**

- Preserving **shape accuracy** with a **global error guarantee**: the simplified line never deviates more than **ε** (epsilon) from the original, measured by maximum perpendicular distance.

**How it works (conceptual):**

1. Connect the **first and last** point with a straight segment.
2. Find the interior point **farthest** from this segment.
3. If that maximum distance **> ε**, the point is important → **keep** it and **split** the polyline at this point; recurse on both halves.
4. If the maximum distance **≤ ε**, **discard** all interior points of the current segment (keep only endpoints).

**What ε controls:**

- **Smaller ε** → stricter tolerance → **keep more points** → higher accuracy, less compression.
- **Larger ε** → looser tolerance → **fewer points** → more compression, potentially more shape loss.

**When to use RDP:**

- When you care about **faithfulness to the original shape** and want a **single, intuitive knob** (ε) controlling a hard error bound.

**Trade-offs:**

- Not streaming; considers the polyline as a whole (but fine for typical trajectory sizes).
- Runtime can grow with very long traces (still practical for interactive use).

---

## Algorithm 2 – SQUISH (Streaming, Memory‑Bounded)

**What it focuses on:**

- **Reducing point count / memory** efficiently—great for **very long trajectories**.
- Provides a capacity **k** (and optional ε) for **bounded memory** and responsive simplification.

**How it works (conceptual):**

1. For each interior point `p_i`, compute a **local importance** (priority) ≈ perpendicular distance from `p_i` to the segment `(p_{i-1} → p_{i+1})`.
2. Keep points with **higher** importance; consider removing **lowest** importance first.
3. Use a **min‑heap** to repeatedly remove the **least significant** point when:
   - the kept set **exceeds k**, or
   - the point’s local error **≤ ε** (safe to drop).
4. After removal, update neighbor priorities and continue until constraints are satisfied.

**What k and ε control:**

- **k**: Maximum complexity. Smaller k ⇒ fewer points regardless of global error.
- **ε**: Local error threshold—higher ε ⇒ drop more low‑impact points.

**When to use SQUISH:**

- When you need **speed**, **streaming behavior**, or a **hard cap** on the number of points (e.g., mapping many long files at once).

**Trade-offs:**

- No global error guarantee like RDP; focuses on local significance.
- The final visual may differ slightly from RDP for the same ε.

---

## What Each Algorithm Optimizes

| Algorithm        | Primary Objective                         | Secondary Effects                       |
|------------------|--------------------------------------------|------------------------------------------|
| Douglas–Peucker  | **Accuracy** (global max error ≤ ε)        | Reduces points as a consequence          |
| SQUISH           | **Point count / memory** (cap via **k**)   | Tries to keep locally important shape; uses ε to drop negligible points |

---

## How to Choose Parameters (Practical)

- **City‑scale lon/lat plots**:
  - RDP: start with **ε ≈ 0.0005–0.002** degrees. Increase until clutter is gone but shape looks right.
  - SQUISH: **k ≈ 200–1000** depending on how much detail you want. You can add **ε** (similar to RDP) to drop small wiggles sooner.

- **Performance tips**:
  - Prefer **SQUISH** + moderate **k** when plotting **many** long trajectories or when interactivity matters most.
  - Prefer **RDP** when you want a **clear error bound** and very faithful simplification.

---

## Interpreting the Map in This App

- Each trajectory shows:
  - **Original** (thin, gray) under the **Simplified** (bold, colored) line.
  - Tooltips with **point counts** and **reduction %** quantify changes.
  - **Start/End markers** for both versions (original = black; simplified start = green; simplified end = red).
- Use the **layer control** (top‑right) to switch among clean, English‑centric basemaps (Positron, Toner, Esri Gray) to maximize readability.

---

## Extending This

- Add a **slider/entry** in the UI for `epsilon` (RDP) and `k` (SQUISH).
- Export the **simplified trajectories** to GeoJSON/CSV.
- Swap in a **metric distance** (e.g., haversine or a projected CRS) if you need ε in **meters**.
- Visualize **removed points** as red dots or an error heatmap (areas with the largest deviations).

---

## FAQ

**Q: Does simplification change the order of points?**  
A: No. It removes vertices but preserves order and connectivity.

**Q: Why do some curves look straighter after simplification?**  
A: That’s expected—non-essential intermediate points are removed; remaining vertices approximate the curve with fewer segments.

**Q: Which algorithm should I start with?**  
A: Try **Douglas–Peucker** with ε around `0.001`. If performance is slow on many long traces, switch to **SQUISH** with `k≈300`.

---

## One‑Line Intuitions

- **Douglas–Peucker**: “Keep the line within ε of the original everywhere.”
- **SQUISH**: “Keep at most k important points and drop the least important ones first.”
