# main.py
import os
import math
import webbrowser
import tkinter as tk
from tkinter import ttk
import folium
from branca.element import Template, MacroElement

from utils import read_plt
from algorithms import simplify_all_algorithms

DATA_PATH = "data/geolife/Data"

# ---------------------------------------------------------
# Algorithm Colors
# ---------------------------------------------------------
ALGO_COLORS = {
    "DP": "#1f77b4",
    "SQUISH": "#ff7f0e",
    "VW": "#2ca02c",
    "SW": "#d62728",
    "RW": "#9467bd",
}

ALGO_DISPLAY = {
    "None": None,
    "Douglas-Peucker": "DP",
    "SQUISH": "SQUISH",
    "Visvalingam-Whyatt": "VW",
    "Sliding-Window": "SW",
    "Reumann-Witkam": "RW",
}

# ---------------------------------------------------------
# GUI Setup
# ---------------------------------------------------------
root = tk.Tk()
root.title("Trajectory Simplification Viewer")

user_var = tk.StringVar()
traj_var = tk.StringVar()
algo_var = tk.StringVar(value="None")
compare_var = tk.BooleanVar(value=False)   # << CHECKBOX FOR COMPARISON MODE


# ---------------------------------------------------------
# Load Users
# ---------------------------------------------------------
try:
    users = sorted([u for u in os.listdir(DATA_PATH) if u.isdigit()])
except FileNotFoundError:
    users = []


# ---------------------------------------------------------
# Load Trajectory Files for a User
# ---------------------------------------------------------
def load_trajectories(event=None):
    user = user_var.get()
    folder = os.path.join(DATA_PATH, user, "Trajectory")
    try:
        files = sorted([f for f in os.listdir(folder) if f.endswith(".plt")])
    except FileNotFoundError:
        files = []

    traj_dropdown["values"] = ["All"] + files
    traj_var.set("All")


# ---------------------------------------------------------
# Helper for plotting points
# ---------------------------------------------------------
def add_points(points, group, color, radius=3, max_points=3000):
    if not points:
        return
    step = 1 if len(points) <= max_points else math.ceil(len(points) / max_points)
    for i in range(0, len(points), step):
        lat, lon = points[i]
        folium.CircleMarker(
            [lat, lon], radius=radius, color=color, fill=True, fill_opacity=1
        ).add_to(group)


# ---------------------------------------------------------
# MAIN PLOT FUNCTION
# ---------------------------------------------------------
def plot():
    user = user_var.get()
    traj = traj_var.get()
    algo_choice = algo_var.get()
    comparison_mode = compare_var.get()

    folder = os.path.join(DATA_PATH, user, "Trajectory")
    try:
        files = sorted([f for f in os.listdir(folder) if f.endswith(".plt")])
    except FileNotFoundError:
        files = []

    # ---------------------------------------------------------
    # Base Map with All Tile Options
    # ---------------------------------------------------------
    m = folium.Map(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap © CARTO",
        zoom_start=12,
    )

    folium.TileLayer("OpenStreetMap").add_to(m)

    folium.TileLayer(
        tiles="https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png",
        name="Stamen Toner",
        attr="Map tiles © Stamen, Data © OSM",
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
              "Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        name="Esri WorldGrayCanvas",
        attr="Tiles © Esri",
    ).add_to(m)

    fg_original = folium.FeatureGroup(name="Original", show=True).add_to(m)
    fg_simpl_all = folium.FeatureGroup(name="Simplified Lines", show=True).add_to(m)
    fg_removed = folium.FeatureGroup(name="Removed Points", show=True).add_to(m)
    fg_kept = folium.FeatureGroup(name="Kept Points", show=True).add_to(m)

    # Bounds
    min_lat, min_lon = +90, +180
    max_lat, max_lon = -90, -180
    any_drawn = False

    # ---------------------------------------------------------
    # Process Trajectories
    # ---------------------------------------------------------
    for f in files:
        if traj != "All" and f != traj:
            continue

        pts_latlon = read_plt(os.path.join(folder, f))
        if not pts_latlon:
            continue

        any_drawn = True
        lats = [p[0] for p in pts_latlon]
        lons = [p[1] for p in pts_latlon]

        min_lat = min(min_lat, min(lats))
        max_lat = max(max_lat, max(lats))
        min_lon = min(min_lon, min(lons))
        max_lon = max(max_lon, max(lons))

        # Original line
        folium.PolyLine(
            pts_latlon,
            color="#bbbbbb",
            weight=2,
            opacity=0.6,
            tooltip=f"{f} (Original: {len(pts_latlon)} pts)"
        ).add_to(fg_original)

        # =====================================================
        # RUN ALL ALGORITHMS (Comparison OR Single)
        # =====================================================
        pts_xy, results, errors = simplify_all_algorithms(pts_latlon, removal_rate=0.50)

        if comparison_mode:
            # ================================================
            # SHOW ALL ALGORITHMS
            # ================================================
            for k, pts_xy_simpl in results.items():

                # Convert XY → LatLon
                lat0 = pts_latlon[0][0]
                simplified_latlon = []
                for x, y in pts_xy_simpl:
                    lat = math.degrees(y / 6371000)
                    lon = math.degrees(x / (6371000 * math.cos(math.radians(lat0))))
                    simplified_latlon.append((lat, lon))

                # Draw simplified line
                folium.PolyLine(
                    simplified_latlon,
                    color=ALGO_COLORS[k],
                    weight=4,
                    opacity=0.9,
                    tooltip=f"{k}: {len(simplified_latlon)} pts"
                ).add_to(fg_simpl_all)

                # Removed/kept points ONLY for selected algorithm
                if ALGO_DISPLAY[algo_choice] == k:
                    simplified_set = set((round(a, 7), round(b, 7))
                                         for a, b in simplified_latlon)
                    removed = []
                    kept = []

                    for (la, lo) in pts_latlon:
                        if (round(la, 7), round(lo, 7)) in simplified_set:
                            kept.append((la, lo))
                        else:
                            removed.append((la, lo))

                    add_points(removed, fg_removed, "#d62728", radius=3)
                    add_points(kept, fg_kept, ALGO_COLORS[k], radius=4)

            # ---------------------------------------------------------
            # ERROR TABLE POPUP
            # ---------------------------------------------------------
            table_rows = ""
            for k, err in errors.items():
                table_rows += (
                    f"<tr>"
                    f"<td>{k}</td>"
                    f"<td>{err['sum']:.2f}</td>"
                    f"<td>{err['mean']:.2f}</td>"
                    f"<td>{err['max']:.2f}</td>"
                    f"</tr>"
                )

            table_html = f"""
            <div style="font-size:14px">
            <b>Comparison of Error Metrics</b><br>
            <table border="1" style="border-collapse:collapse;">
            <tr><th>Algorithm</th><th>Sum</th><th>Mean</th><th>Max</th></tr>
            {table_rows}
            </table>
            </div>
            """

            mid = len(pts_latlon) // 2
            folium.Marker(
                pts_latlon[mid],
                popup=table_html
            ).add_to(m)

        else:
            # =================================================
            # SINGLE ALGORITHM MODE
            # =================================================
            algo_key = ALGO_DISPLAY[algo_choice]

            if algo_key is None:
                continue  # show original only

            pts_xy_simpl = results[algo_key]

            # Convert XY → latlon
            lat0 = pts_latlon[0][0]
            simplified_latlon = []
            for x, y in pts_xy_simpl:
                lat = math.degrees(y / 6371000)
                lon = math.degrees(x / (6371000 * math.cos(math.radians(lat0))))
                simplified_latlon.append((lat, lon))

            # Simplified line
            folium.PolyLine(
                simplified_latlon,
                color=ALGO_COLORS[algo_key],
                weight=5,
                opacity=0.95,
                tooltip=f"{algo_choice}: {len(simplified_latlon)} pts"
            ).add_to(fg_simpl_all)

            # Removed & Kept points
            simplified_set = set((round(a, 7), round(b, 7))
                                 for a, b in simplified_latlon)
            removed = []
            kept = []

            for (la, lo) in pts_latlon:
                if (round(la, 7), round(lo, 7)) in simplified_set:
                    kept.append((la, lo))
                else:
                    removed.append((la, lo))

            add_points(removed, fg_removed, "#d62728", radius=3)
            add_points(kept, fg_kept, ALGO_COLORS[algo_key], radius=4)

            # Error metrics popup
            err = errors[algo_key]
            html = f"""
            <div>
            <b>Error Metrics ({algo_choice})</b><br>
            Sum Error: {err['sum']:.2f} m<br>
            Mean Error: {err['mean']:.2f} m<br>
            Max Error: {err['max']:.2f} m<br>
            </div>
            """
            mid = len(simplified_latlon) // 2
            folium.Marker(
                simplified_latlon[mid],
                popup=html
            ).add_to(m)

    # ---------------------------------------------------------
    # Auto-zoom
    # ---------------------------------------------------------
    if any_drawn:
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
    else:
        m.location = [20, 0]
        m.zoom_start = 2

    # ---------------------------------------------------------
    # Map Legend
    # ---------------------------------------------------------
    legend = f"""
    {{% macro html(this, kwargs) %}}
    <div style="
        position:fixed;top:10px;left:10px;z-index:9999;
        background:white;padding:10px;border:1px solid #ccc;
        border-radius:5px;font-size:13px">
        <b>Legend</b><br>
        <span style="display:inline-block;width:14px;height:3px;background:#bbbbbb"></span>
        Original<br>
        <span style="display:inline-block;width:14px;height:3px;background:{ALGO_COLORS['DP']}"></span> DP<br>
        <span style="display:inline-block;width:14px;height:3px;background:{ALGO_COLORS['SQUISH']}"></span> SQUISH<br>
        <span style="display:inline-block;width:14px;height:3px;background:{ALGO_COLORS['VW']}"></span> VW<br>
        <span style="display:inline-block;width:14px;height:3px;background:{ALGO_COLORS['SW']}"></span> SW<br>
        <span style="display:inline-block;width:14px;height:3px;background:{ALGO_COLORS['RW']}"></span> RW<br>
        <hr>
        <span style="display:inline-block;width:10px;height:10px;background:#d62728;border-radius:50%"></span>
        Removed Points<br>
        Kept Points = same color as algorithm
    </div>
    {{% endmacro %}}
    """

    macro = MacroElement()
    macro._template = Template(legend)
    m.get_root().add_child(macro)

    folium.LayerControl().add_to(m)

    m.save("map.html")
    webbrowser.open("map.html")


# ---------------------------------------------------------
# UI Controls
# ---------------------------------------------------------
tk.Label(root, text="User:").grid(row=0, column=0)
user_dropdown = ttk.Combobox(root, textvariable=user_var, values=users)
user_dropdown.grid(row=0, column=1)
user_dropdown.bind("<<ComboboxSelected>>", load_trajectories)

tk.Label(root, text="Trajectory:").grid(row=1, column=0)
traj_dropdown = ttk.Combobox(root, textvariable=traj_var, values=["All"])
traj_dropdown.grid(row=1, column=1)

tk.Label(root, text="Algorithm:").grid(row=2, column=0)
algo_dropdown = ttk.Combobox(
    root, textvariable=algo_var,
    values=[
        "None",
        "Douglas-Peucker",
        "SQUISH",
        "Visvalingam-Whyatt",
        "Sliding-Window",
        "Reumann-Witkam"
    ]
)
algo_dropdown.grid(row=2, column=1)

# Comparison checkbox
compare_box = tk.Checkbutton(
    root, text="Compare all algorithms (show error metrics)",
    variable=compare_var
)
compare_box.grid(row=3, column=0, columnspan=2)

plot_btn = tk.Button(root, text="Plot", command=plot)
plot_btn.grid(row=4, column=0, columnspan=2, pady=10)

root.mainloop()