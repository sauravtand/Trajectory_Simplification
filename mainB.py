import math
import os
import webbrowser
import tkinter as tk
from tkinter import ttk

import folium
from branca.element import MacroElement, Template

from algorithms import simplify_all_algorithms, xy_to_latlon
from utils import read_plt

DATA_PATH = "data/geolife/Data"

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


# ============================================================
# GUI SETUP
# ============================================================

root = tk.Tk()
root.title("Trajectory Simplification Viewer")

user_var = tk.StringVar()
traj_var = tk.StringVar()
algo_var = tk.StringVar(value="None")
compare_var = tk.BooleanVar(value=False)

try:
    users = sorted([u for u in os.listdir(DATA_PATH) if u.isdigit()])
except FileNotFoundError:
    users = []


# ============================================================
# HELPERS
# ============================================================

def load_trajectories(event=None):
    user = user_var.get()
    folder = os.path.join(DATA_PATH, user, "Trajectory")

    try:
        files = sorted([f for f in os.listdir(folder) if f.endswith(".plt")])
    except FileNotFoundError:
        files = []

    traj_dropdown["values"] = ["All"] + files
    traj_var.set("All")


def add_points(points, group, color, radius=3, max_points=3000):
    """
    Draw point markers with downsampling for large trajectories.
    """
    if not points:
        return

    step = 1 if len(points) <= max_points else math.ceil(len(points) / max_points)

    for i in range(0, len(points), step):
        lat, lon = points[i]
        folium.CircleMarker(
            [lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=1.0,
        ).add_to(group)


def build_metrics_table(metrics):
    rows = ""
    for name, m in metrics.items():
        rows += (
            f"<tr>"
            f"<td>{name}</td>"
            f"<td>{m['outliers_removed']}</td>"
            f"<td>{m['kept_points']}</td>"
            f"<td>{m['removed_points']}</td>"
            f"<td>{m['sum']:.2f}</td>"
            f"<td>{m['mean']:.2f}</td>"
            f"<td>{m['rmse']:.2f}</td>"
            f"<td>{m['max']:.2f}</td>"
            f"<td>{m['length_ratio']:.3f}</td>"
            f"<td>{m['runtime_ms']:.2f}</td>"
            f"</tr>"
        )

    return f"""
    <div style="font-size:13px; max-width:1000px; overflow:auto;">
        <b>Comparison of Error Metrics</b><br>
        <table border="1" style="border-collapse:collapse;">
            <tr>
                <th>Algorithm</th>
                <th>Outliers Removed</th>
                <th>Kept</th>
                <th>Removed</th>
                <th>Sum</th>
                <th>Mean</th>
                <th>RMSE</th>
                <th>Max</th>
                <th>Length Ratio</th>
                <th>Runtime (ms)</th>
            </tr>
            {rows}
        </table>
    </div>
    """


def get_removed_kept_points(original_latlon, simplified_latlon):
    """
    Compare original and simplified points by rounded coordinate matching.
    """
    simplified_set = {(round(a, 7), round(b, 7)) for a, b in simplified_latlon}

    removed = []
    kept = []

    for la, lo in original_latlon:
        if (round(la, 7), round(lo, 7)) in simplified_set:
            kept.append((la, lo))
        else:
            removed.append((la, lo))

    return removed, kept


# ============================================================
# MAIN PLOT FUNCTION
# ============================================================

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
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
        ),
        name="Esri WorldGrayCanvas",
        attr="Tiles © Esri",
    ).add_to(m)

    fg_original = folium.FeatureGroup(name="Original", show=True).add_to(m)
    fg_simpl_all = folium.FeatureGroup(name="Simplified Lines", show=True).add_to(m)
    fg_removed = folium.FeatureGroup(name="Removed Points", show=True).add_to(m)
    fg_kept = folium.FeatureGroup(name="Kept Points", show=True).add_to(m)

    min_lat, min_lon = 90, 180
    max_lat, max_lon = -90, -180
    any_drawn = False

    for f in files:
        if traj != "All" and f != traj:
            continue

        pts_with_time = read_plt(os.path.join(folder, f), include_time=True)
        pts_latlon = [(lat, lon) for lat, lon, _ in pts_with_time]

        if not pts_latlon:
            continue

        any_drawn = True

        lats = [p[0] for p in pts_latlon]
        lons = [p[1] for p in pts_latlon]

        min_lat = min(min_lat, min(lats))
        max_lat = max(max_lat, max(lats))
        min_lon = min(min_lon, min(lons))
        max_lon = max(max_lon, max(lons))

        # Draw original trajectory
        folium.PolyLine(
            pts_latlon,
            color="#bbbbbb",
            weight=2,
            opacity=0.6,
            tooltip=f"{f} (Original: {len(pts_latlon)} pts)",
        ).add_to(fg_original)

        # Run backend pipeline
        cleaned_xy, results, metrics = simplify_all_algorithms(
            pts_with_time,
            removal_rate=0.50,
        )

        if not cleaned_xy or not results:
            continue

        lat0 = pts_latlon[0][0]

        if comparison_mode:
            selected_algo = ALGO_DISPLAY[algo_choice]

            for name, pts_xy_simpl in results.items():
                simplified_latlon = [xy_to_latlon(x, y, lat0) for x, y in pts_xy_simpl]

                folium.PolyLine(
                    simplified_latlon,
                    color=ALGO_COLORS[name],
                    weight=4,
                    opacity=0.9,
                    tooltip=f"{name}: {len(simplified_latlon)} pts",
                ).add_to(fg_simpl_all)

                # Only show removed/kept markers for selected algorithm
                if selected_algo == name:
                    removed, kept = get_removed_kept_points(pts_latlon, simplified_latlon)
                    add_points(removed, fg_removed, "#d62728", radius=3)
                    add_points(kept, fg_kept, ALGO_COLORS[name], radius=4)

            mid = len(pts_latlon) // 2
            folium.Marker(
                pts_latlon[mid],
                popup=build_metrics_table(metrics),
            ).add_to(m)

        else:
            algo_key = ALGO_DISPLAY[algo_choice]

            if algo_key is None or algo_key not in results:
                continue

            simplified_latlon = [xy_to_latlon(x, y, lat0) for x, y in results[algo_key]]

            folium.PolyLine(
                simplified_latlon,
                color=ALGO_COLORS[algo_key],
                weight=5,
                opacity=0.95,
                tooltip=f"{algo_choice}: {len(simplified_latlon)} pts",
            ).add_to(fg_simpl_all)

            removed, kept = get_removed_kept_points(pts_latlon, simplified_latlon)
            add_points(removed, fg_removed, "#d62728", radius=3)
            add_points(kept, fg_kept, ALGO_COLORS[algo_key], radius=4)

            err = metrics[algo_key]
            html = f"""
            <div style="font-size:13px;">
                <b>Error Metrics ({algo_choice})</b><br>
                Outliers Removed: {err['outliers_removed']}<br>
                Kept Points: {err['kept_points']}<br>
                Removed Points: {err['removed_points']}<br>
                Sum Error: {err['sum']:.2f} m<br>
                Mean Error: {err['mean']:.2f} m<br>
                RMSE: {err['rmse']:.2f} m<br>
                Max Error: {err['max']:.2f} m<br>
                Length Ratio: {err['length_ratio']:.3f}<br>
                Runtime: {err['runtime_ms']:.2f} ms<br>
            </div>
            """

            mid = len(simplified_latlon) // 2
            folium.Marker(simplified_latlon[mid], popup=html).add_to(m)

    if any_drawn:
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
    else:
        m.location = [20, 0]
        m.zoom_start = 2

    legend = f"""
    {{% macro html(this, kwargs) %}}
    <div style="
        position:fixed;
        top:10px;
        left:10px;
        z-index:9999;
        background:white;
        padding:10px;
        border:1px solid #ccc;
        border-radius:5px;
        font-size:13px">
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


# ============================================================
# UI CONTROLS
# ============================================================

tk.Label(root, text="User:").grid(row=0, column=0)
user_dropdown = ttk.Combobox(root, textvariable=user_var, values=users)
user_dropdown.grid(row=0, column=1)
user_dropdown.bind("<<ComboboxSelected>>", load_trajectories)

tk.Label(root, text="Trajectory:").grid(row=1, column=0)
traj_dropdown = ttk.Combobox(root, textvariable=traj_var, values=["All"])
traj_dropdown.grid(row=1, column=1)

tk.Label(root, text="Algorithm:").grid(row=2, column=0)
algo_dropdown = ttk.Combobox(
    root,
    textvariable=algo_var,
    values=[
        "None",
        "Douglas-Peucker",
        "SQUISH",
        "Visvalingam-Whyatt",
        "Sliding-Window",
        "Reumann-Witkam",
    ],
)
algo_dropdown.grid(row=2, column=1)

compare_box = tk.Checkbutton(
    root,
    text="Compare all algorithms (show error metrics)",
    variable=compare_var,
)
compare_box.grid(row=3, column=0, columnspan=2)

plot_btn = tk.Button(root, text="Plot", command=plot)
plot_btn.grid(row=4, column=0, columnspan=2, pady=10)

root.mainloop()