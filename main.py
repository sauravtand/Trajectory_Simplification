import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib
import tkinter as tk
from tkinter import ttk

# ===== CONFIG =====
DATA_PATH = "data/geolife/Data"
LINE_WIDTH = 2
FIGSIZE = (8, 6)
FONT_TITLE = {'fontsize': 16, 'fontweight': 'bold'}
FONT_LABEL = {'fontsize': 12}

# ===== LOAD USERS =====
all_users = sorted([u for u in os.listdir(DATA_PATH) if u.isdigit()])
current_user_index = 0

# ===== GLOBALS =====
lines = []
current_files = []

# ===== FUNCTIONS =====
def read_plt(file_path):
    return pd.read_csv(
        file_path,
        skiprows=6,
        header=None,
        names=["lat", "lon", "unused", "alt", "date_days", "date", "time"]
    )

def plot_user(user_id, trajectory_name="All"):
    """Plot user trajectories. If trajectory_name != 'All', show only that trajectory."""
    global lines, current_files
    ax.clear()
    lines = []
    traj_folder = os.path.join(DATA_PATH, user_id, "Trajectory")
    if not os.path.exists(traj_folder):
        ax.set_title(f"No trajectories for user {user_id}", **FONT_TITLE)
        canvas.draw()
        return

    files = [f for f in os.listdir(traj_folder) if f.endswith(".plt")]
    current_files = files
    colors = matplotlib.colormaps['tab20'].resampled(len(files))

    # Update trajectory dropdown
    traj_dropdown['values'] = ["All"] + files
    if trajectory_name not in ["All"] + files:
        trajectory_name = "All"
    traj_dropdown.set(trajectory_name)

    for idx, file in enumerate(files):
        df = read_plt(os.path.join(traj_folder, file))
        visible = (trajectory_name == "All") or (trajectory_name == file)
        line, = ax.plot(df["lon"], df["lat"], color=colors(idx),
                        linewidth=LINE_WIDTH, alpha=0.9, visible=visible)
        lines.append(line)

    ax.set_title(f"Trajectories for User {user_id}", **FONT_TITLE)
    ax.set_xlabel("Longitude", **FONT_LABEL)
    ax.set_ylabel("Latitude", **FONT_LABEL)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_facecolor("#f0f0f0")
    ax.legend(fontsize=8, loc='upper right')
    canvas.draw()

def next_user():
    global current_user_index
    current_user_index = (current_user_index + 1) % len(all_users)
    user_dropdown.set(all_users[current_user_index])
    plot_user(all_users[current_user_index])

def prev_user():
    global current_user_index
    current_user_index = (current_user_index - 1) % len(all_users)
    user_dropdown.set(all_users[current_user_index])
    plot_user(all_users[current_user_index])

def select_user(event):
    global current_user_index
    user_id = user_dropdown.get()
    if user_id in all_users:
        current_user_index = all_users.index(user_id)
        plot_user(user_id)

def select_trajectory(event):
    trajectory_name = traj_dropdown.get()
    plot_user(all_users[current_user_index], trajectory_name)

# ===== TKINTER SETUP =====
root = tk.Tk()
root.title("Interactive GeoLife Trajectory Viewer")

# Create matplotlib figure
fig, ax = plt.subplots(figsize=FIGSIZE)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Add toolbar
toolbar = NavigationToolbar2Tk(canvas, root)
toolbar.update()
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Controls frame
frame_controls = tk.Frame(root)
frame_controls.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

# User dropdown
tk.Label(frame_controls, text="Select User:").pack(side=tk.LEFT, padx=5)
user_dropdown = ttk.Combobox(frame_controls, values=all_users, width=10)
user_dropdown.current(current_user_index)
user_dropdown.bind("<<ComboboxSelected>>", select_user)
user_dropdown.pack(side=tk.LEFT, padx=5)

# Trajectory dropdown
tk.Label(frame_controls, text="Select Trajectory:").pack(side=tk.LEFT, padx=5)
traj_dropdown = ttk.Combobox(frame_controls, values=["All"], width=25)
traj_dropdown.bind("<<ComboboxSelected>>", select_trajectory)
traj_dropdown.pack(side=tk.LEFT, padx=5)

# Previous / Next buttons
prev_button = tk.Button(frame_controls, text="Previous User", bg="#1f77b4", fg="white",
                        activebackground="#ff7f0e", command=prev_user)
prev_button.pack(side=tk.LEFT, padx=10)
next_button = tk.Button(frame_controls, text="Next User", bg="#1f77b4", fg="white",
                        activebackground="#ff7f0e", command=next_user)
next_button.pack(side=tk.LEFT, padx=10)

# ===== INITIAL PLOT =====
plot_user(all_users[current_user_index])

root.mainloop()
