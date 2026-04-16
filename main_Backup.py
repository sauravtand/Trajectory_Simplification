import math
import os
import webbrowser
import tkinter as tk
from tkinter import ttk

import folium
from branca.element import Element, MacroElement, Template

from algorithms import simplify_all_algorithms, xy_to_latlon
from utils import read_plt

DATA_PATH = "data/geolife/Data"

ALGO_COLORS = {
    "DP": "#1f77b4",
    "SQUISH": "#ff7f0e",
    "VW": "#2ca02c",
    "SW": "#2ca",
    "RW": "#9467bd",
}

ALGO_DISPLAY = {
    "None": None,
    "Douglas-Peucker": "DP",
    "Visvalingam-Whyatt": "VW",
    "Sliding-Window": "SW",
    "Reumann-Witkam": "RW",
    "SQUISH": "SQUISH",
}

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


def fmt(value, digits=2):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _metric_row(label, value):
    return (
        "<div style='display:flex;justify-content:space-between;gap:12px;padding:4px 0;'>"
        f"<span style='color:#555'>{label}</span>"
        f"<span style='font-weight:600'>{value}</span>"
        "</div>"
    )


def build_single_metrics_card(algo_label, algo_key, metric, source_name):
    color = ALGO_COLORS.get(algo_key, "#333333")
    rows = [
        _metric_row("Trajectory", source_name),
        _metric_row("Algorithm", algo_label),
        _metric_row("Outliers Removed", metric.get("outliers_removed", 0)),
        _metric_row("Kept Points", metric.get("kept_points", 0)),
        _metric_row("Removed Points", metric.get("removed_points", 0)),
        _metric_row("PED max / mean / rmse", f"{fmt(metric.get('PED_max'))} / {fmt(metric.get('PED_mean'))} / {fmt(metric.get('PED_rmse'))}"),
        _metric_row("SED max / mean / rmse", f"{fmt(metric.get('SED_max'))} / {fmt(metric.get('SED_mean'))} / {fmt(metric.get('SED_rmse'))}"),
        _metric_row("DAD max / mean", f"{fmt(metric.get('DAD_max_deg'))}° / {fmt(metric.get('DAD_mean_deg'))}°"),
        _metric_row("SAD max / mean", f"{fmt(metric.get('SAD_max'))} / {fmt(metric.get('SAD_mean'))}"),
        _metric_row("ISSD", fmt(metric.get("ISSD"))),
        _metric_row("Length Ratio", fmt(metric.get("length_ratio"), 3)),
        _metric_row("Runtime", f"{fmt(metric.get('runtime_ms'))} ms"),
    ]

    return f"""
    <div style="
        background:white;
        border:1px solid #d9d9d9;
        border-left:6px solid {color};
        border-radius:14px;
        padding:14px 16px;
        box-shadow:0 4px 14px rgba(0,0,0,0.10);
        margin-bottom:12px;
        font-size:13px;
        line-height:1.35;
    ">
        <div style="font-size:15px;font-weight:700;margin-bottom:8px;color:#222;">Metrics Summary</div>
        {''.join(rows)}
    </div>
    """


def build_comparison_cards(metrics, source_name):
    cards = []
    algo_order = ["DP", "SQUISH", "VW", "SW", "RW"]

    for name in algo_order:
        if name not in metrics:
            continue
        m = metrics[name]
        cards.append(f"""
        <div style="
            background:white;
            border:1px solid #d9d9d9;
            border-left:6px solid {ALGO_COLORS.get(name, '#333333')};
            border-radius:14px;
            padding:12px 14px;
            box-shadow:0 4px 14px rgba(0,0,0,0.08);
            margin-bottom:10px;
            font-size:12.5px;
            line-height:1.3;
        ">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:14px;font-weight:700;color:#222;">{name}</div>
                <div style="font-size:11px;color:#666;">{source_name}</div>
            </div>
            {_metric_row('Outliers', m.get('outliers_removed', 0))}
            {_metric_row('Kept', m.get('kept_points', 0))}
            {_metric_row('PED max', fmt(m.get('PED_max')))}
            {_metric_row('SED max', fmt(m.get('SED_max')))}
            {_metric_row('DAD max', f"{fmt(m.get('DAD_max_deg'))}°")}
            {_metric_row('SAD max', fmt(m.get('SAD_max')))}
            {_metric_row('ISSD', fmt(m.get('ISSD')))}
            {_metric_row('Length Ratio', fmt(m.get('length_ratio'), 3))}
            {_metric_row('Runtime', f"{fmt(m.get('runtime_ms'))} ms")}
        </div>
        """)

    return f"""
    <div style="
        background:#f8f9fb;
        border:1px solid #d9d9d9;
        border-radius:16px;
        padding:14px;
        box-shadow:0 4px 16px rgba(0,0,0,0.10);
    ">
        <div style="font-size:15px;font-weight:700;margin-bottom:10px;color:#222;">Comparison Summary</div>
        {''.join(cards) if cards else '<div style="color:#666">No metrics available.</div>'}
    </div>
    """


def add_sidebar_panel(m, html_content):
    sidebar_html = f"""
    <div style="
        position: fixed;
        bottom: 12px;
        left: 12px;
        width: 260px;
        max-height: 40vh;
        overflow-y: auto;
        z-index: 9998;
        padding-right: 4px;
    ">
        {html_content}
    </div>
    """
    m.get_root().html.add_child(Element(sidebar_html))


def get_removed_kept_points(original_latlon, simplified_latlon):
    simplified_set = {(round(a, 7), round(b, 7)) for a, b in simplified_latlon}
    removed = []
    kept = []
    for la, lo in original_latlon:
        if (round(la, 7), round(lo, 7)) in simplified_set:
            kept.append((la, lo))
        else:
            removed.append((la, lo))
    return removed, kept


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
    sidebar_sections = []

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

        folium.PolyLine(
            pts_latlon,
            color="#bbbbbb",
            weight=2,
            opacity=0.6,
            tooltip=f"{f} (Original: {len(pts_latlon)} pts)",
        ).add_to(fg_original)

        cleaned_xy, results, metrics, _ = simplify_all_algorithms(pts_with_time, removal_rate=0.50)
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

                if selected_algo == name:
                    removed, kept = get_removed_kept_points(pts_latlon, simplified_latlon)
                    add_points(removed, fg_removed, "#d62728", radius=3)
                    add_points(kept, fg_kept, ALGO_COLORS[name], radius=4)

            sidebar_sections.append(build_comparison_cards(metrics, f))

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
            sidebar_sections.append(build_single_metrics_card(algo_choice, algo_key, metrics[algo_key], f))

    if sidebar_sections:
        add_sidebar_panel(m, ''.join(sidebar_sections))

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
        <span style="display:inline-block;width:14px;height:3px;background:#bbbbbb"></span> Original<br>
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
