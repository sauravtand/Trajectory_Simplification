# main.py
import os
import tkinter as tk
from tkinter import ttk
import folium
from algorithms import rdp, squish
from utils import read_plt
import webbrowser

DATA_PATH = "data/geolife/Data"

# -----------------------------
# Load users
# -----------------------------
users = sorted([u for u in os.listdir(DATA_PATH) if u.isdigit()])

# -----------------------------
# Create window
# -----------------------------
root = tk.Tk()
root.title("Simple Trajectory Viewer")

# -----------------------------
# Dropdowns
# -----------------------------
user_var = tk.StringVar()
traj_var = tk.StringVar()
algo_var = tk.StringVar(value="None")

def load_trajectories(event=None):
    user = user_var.get()
    folder = os.path.join(DATA_PATH, user, "Trajectory")
    files = [f for f in os.listdir(folder) if f.endswith(".plt")]
    traj_dropdown["values"] = ["All"] + files
    traj_var.set("All")
def plot():
    import os
    import webbrowser
    import math
    import folium
    from branca.element import MacroElement, Template

    user = user_var.get()
    traj = traj_var.get()
    algo = algo_var.get()

    folder = os.path.join(DATA_PATH, user, "Trajectory")
    files = [f for f in os.listdir(folder) if f.endswith(".plt")]

    # --- 1) Base map: CartoDB Positron (clean, English-like labels) ---
    m = folium.Map(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap contributors © CARTO",
        zoom_start=12
    )
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    folium.TileLayer(
        tiles="https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png",
        name="Stamen Toner",
        attr="Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap",
        overlay=False,
        control=True
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        name="Esri WorldGrayCanvas",
        attr="Tiles © Esri — Esri, DeLorme, NAVTEQ",
        overlay=False,
        control=True
    ).add_to(m)

    # --- 2) Prepare bounds for auto-zoom ---
    global_min_lat, global_min_lon = +90.0, +180.0
    global_max_lat, global_max_lon = -90.0, -180.0
    any_drawn = False

    # High-contrast color cycle for simplified trajectories
    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf"
    ]

    # Helper: add many points efficiently by sampling if needed
    def add_points(points, group, color, radius=3, max_points=3000):
        """
        Add small circle markers for 'points' to 'group'.
        If too many points, subsample to ~max_points for performance.
        """
        if not points:
            return
        n = len(points)
        step = 1 if n <= max_points else math.ceil(n / max_points)
        for i in range(0, n, step):
            lat, lon = points[i]
            folium.CircleMarker(
                [lat, lon], radius=radius, color=color,
                fill=True, fill_opacity=1
            ).add_to(group)

    # Feature groups to toggle layers on/off
    fg_original_lines = folium.FeatureGroup(name="Original Trajectory (line)", show=True).add_to(m)
    fg_simplified_lines = folium.FeatureGroup(name="Simplified Trajectory (line)", show=True).add_to(m)
    fg_removed_points = folium.FeatureGroup(name="Removed Points (red)", show=True).add_to(m)
    fg_kept_points = folium.FeatureGroup(name="Kept Points (simplified vertices)", show=True).add_to(m)

    for idx, f in enumerate(files):
        if traj != "All" and f != traj:
            continue

        pts = read_plt(os.path.join(folder, f))  # [(lat, lon), ...]  NOTE: (lat, lon) order for Folium
        if not pts:
            continue

        any_drawn = True

        # Update bounds from ORIGINAL points
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        global_min_lat = min(global_min_lat, min(lats))
        global_max_lat = max(global_max_lat, max(lats))
        global_min_lon = min(global_min_lon, min(lons))
        global_max_lon = max(global_max_lon, max(lons))

        color = colors[idx % len(colors)]

        # ----- ORIGINAL (thin, light gray line) -----
        folium.PolyLine(
            pts, color="#bbbbbb", weight=2, opacity=0.7,
            tooltip=f"{f} (Original: {len(pts)} pts)"
        ).add_to(fg_original_lines)

        # ----- SIMPLIFY -----
        simplified = pts
        if algo == "Douglas-Peucker":
            simplified = rdp(pts, epsilon=0.0008)
        elif algo == "SQUISH":
            simplified = squish(pts, k=300)

        # ----- SPLIT POINTS: kept vs removed -----
        # RDP and this SQUISH keep a subset of original vertices -> exact coordinate match works.
        simplified_set = set((round(p[0], 10), round(p[1], 10)) for p in simplified)

        kept_points = []
        removed_points = []
        for p in pts:
            key = (round(p[0], 10), round(p[1], 10))
            if key in simplified_set:
                kept_points.append(p)
            else:
                removed_points.append(p)

        # ----- SIMPLIFIED (bold, colored line) -----
        reduction_pct = (1 - len(kept_points) / len(pts)) * 100 if len(pts) else 0.0
        folium.PolyLine(
            simplified,
            color=color,
            weight=5,
            opacity=0.95,
            tooltip=(f"{f} (Simplified: {len(kept_points)} pts — "
                     f"Reduced {reduction_pct:.1f}%)")
        ).add_to(fg_simplified_lines)

        # ----- POINTS -----
        # Removed: red
        add_points(removed_points, fg_removed_points, color="#d62728", radius=3)
        # Kept: same color as simplified line
        add_points(kept_points, fg_kept_points, color=color, radius=4)

    # --- 3) Fit map to data or fallback view ---
    if any_drawn and (global_min_lat < global_max_lat) and (global_min_lon < global_max_lon):
        m.fit_bounds([[global_min_lat, global_min_lon], [global_max_lat, global_max_lon]])
    else:
        # Fallback: world view if nothing drawn
        m.location = [20.0, 0.0]
        m.zoom_start = 2

    # --- 4) Legend (top-left) – FIXED macro signature ---
    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed; 
        top: 10px; left: 10px; z-index: 1000;
        background: rgba(255,255,255,0.92); 
        padding: 10px 12px; 
        border: 1px solid #ccc; 
        border-radius: 6px; 
        font-size: 12px;">
      <div style="font-weight: 600; margin-bottom: 4px;">Legend</div>
      <div><span style="display:inline-block;width:14px;height:3px;background:#bbbbbb;margin-right:6px;"></span> Original line</div>
      <div><span style="display:inline-block;width:14px;height:3px;background:#1f77b4;margin-right:6px;"></span> Simplified line (color varies)</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#d62728;border-radius:50%;display:inline-block;margin-right:6px;"></span> Removed points</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#1f77b4;border-radius:50%;display:inline-block;margin-right:6px;"></span> Kept points (simplified vertices)</div>
    </div>
    {% endmacro %}
    """
    macro = MacroElement()
    macro._template = Template(legend_html)
    m.get_root().add_child(macro)

    # --- 5) Layer control (toggle lines/points) ---
    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    # --- 6) Save & open ---
    m.save("map.html")
    webbrowser.open("map.html")
# -----------------------------
# UI Layout
# -----------------------------
tk.Label(root, text="User:").grid(row=0, column=0)
user_dropdown = ttk.Combobox(root, textvariable=user_var, values=users)
user_dropdown.grid(row=0, column=1)
user_dropdown.bind("<<ComboboxSelected>>", load_trajectories)

tk.Label(root, text="Trajectory:").grid(row=1, column=0)
traj_dropdown = ttk.Combobox(root, textvariable=traj_var, values=["All"])
traj_dropdown.grid(row=1, column=1)

tk.Label(root, text="Algorithm:").grid(row=2, column=0)
algo_dropdown = ttk.Combobox(root, textvariable=algo_var,
                             values=["None", "Douglas-Peucker", "SQUISH"])
algo_dropdown.grid(row=2, column=1)

plot_button = tk.Button(root, text="Plot on Map", command=plot)
plot_button.grid(row=3, column=0, columnspan=2, pady=10)

root.mainloop()