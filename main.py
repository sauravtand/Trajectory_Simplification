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
    import folium

    user = user_var.get()
    traj = traj_var.get()
    algo = algo_var.get()

    folder = os.path.join(DATA_PATH, user, "Trajectory")
    files = [f for f in os.listdir(folder) if f.endswith(".plt")]

    # --- 1) Base map: CartoDB Positron (clean, English-like labels) ---
    # Use explicit URLs + attribution for compatibility across Folium versions
    m = folium.Map(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap contributors © CARTO",
        zoom_start=12
    )

    # Add additional English-friendly basemaps
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

    # Optional: also show the original under the simplified line (we do this here)
    show_original_alongside = True

    for idx, f in enumerate(files):
        if traj != "All" and f != traj:
            continue

        pts = read_plt(os.path.join(folder, f))  # [(lat, lon), ...]  NOTE: (lat, lon) order for Folium
        if not pts:
            continue

        any_drawn = True

        # Update bounds from original points
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        global_min_lat = min(global_min_lat, min(lats))
        global_max_lat = max(global_max_lat, max(lats))
        global_min_lon = min(global_min_lon, min(lons))
        global_max_lon = max(global_max_lon, max(lons))

        color = colors[idx % len(colors)]

        # ------------- ORIGINAL (thin, light gray) -------------
        if show_original_alongside:
            folium.PolyLine(
                pts,
                color="#bbbbbb",
                weight=2,
                opacity=0.7,
                tooltip=f"{f} (Original: {len(pts)} pts)"
            ).add_to(m)

            # small black markers for original start/end
            folium.CircleMarker(
                pts[0], radius=4, color="black", fill=True, fill_opacity=1,
                tooltip="Original Start"
            ).add_to(m)
            folium.CircleMarker(
                pts[-1], radius=4, color="black", fill=True, fill_opacity=1,
                tooltip="Original End"
            ).add_to(m)

        # ------------- SIMPLIFIED (bold, colored) -------------
        simplified = pts
        if algo == "Douglas-Peucker":
            # tweak epsilon to your liking; larger = more aggressive
            simplified = rdp(pts, epsilon=0.0008)
        elif algo == "SQUISH":
            # k controls max retained points (besides endpoints)
            simplified = squish(pts, k=300)
        # else: "None" keeps original

        # Display simplified line in color
        reduction_pct = (1 - len(simplified) / len(pts)) * 100 if len(pts) else 0.0
        folium.PolyLine(
            simplified,
            color=color,
            weight=5,          # thicker for clarity
            opacity=0.95,
            tooltip=(f"{f} (Simplified: {len(simplified)} pts — "
                     f"Reduced {reduction_pct:.1f}%)")
        ).add_to(m)

        # Mark simplified start/end (green/red)
        folium.CircleMarker(
            simplified[0], radius=5, color="green", fill=True, fill_opacity=1,
            tooltip="Simplified Start"
        ).add_to(m)
        folium.CircleMarker(
            simplified[-1], radius=5, color="red", fill=True, fill_opacity=1,
            tooltip="Simplified End"
        ).add_to(m)

    # --- 3) Fit map to data or fallback view ---
    if any_drawn and (global_min_lat < global_max_lat) and (global_min_lon < global_max_lon):
        m.fit_bounds([[global_min_lat, global_min_lon], [global_max_lat, global_max_lon]])
    else:
        # Fallback: world view if nothing drawn
        m.location = [20.0, 0.0]
        m.zoom_start = 2

    # --- 4) Basemap layer switcher ---
    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    # --- 5) Save & open ---
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