import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import matplotlib.cm as cm
import matplotlib

# ===== CONFIG =====
DATA_PATH = "data/geolife/Data"
LINE_WIDTH = 1
FIGSIZE = (8, 6)

# Load all users
all_users = sorted([u for u in os.listdir(DATA_PATH) if u.isdigit()])
current_index = 0  # start with first user

def read_plt(file_path):
    """Read a single GeoLife .plt file"""
    return pd.read_csv(
        file_path,
        skiprows=6,
        header=None,
        names=["lat", "lon", "unused", "alt", "date_days", "date", "time"]
    )

def plot_user(ax, user_id):
    """Plot all trajectories of a user on given axes"""
    ax.clear()
    traj_folder = os.path.join(DATA_PATH, user_id, "Trajectory")
    if not os.path.exists(traj_folder):
        ax.set_title(f"No trajectories for user {user_id}")
        return

    files = [f for f in os.listdir(traj_folder) if f.endswith(".plt")]
    colors = matplotlib.colormaps['tab10'].resampled(len(files))

    for idx, file in enumerate(files):
        df = read_plt(os.path.join(traj_folder, file))
        ax.plot(df["lon"], df["lat"], color=colors(idx), alpha=0.8, linewidth=LINE_WIDTH)

    ax.set_title(f"Trajectories for User {user_id}")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True)

def next_user(event):
    global current_index
    current_index = (current_index + 1) % len(all_users)
    plot_user(ax, all_users[current_index])
    plt.draw()

def prev_user(event):
    global current_index
    current_index = (current_index - 1) % len(all_users)
    plot_user(ax, all_users[current_index])
    plt.draw()

# Create figure and axes
fig, ax = plt.subplots(figsize=FIGSIZE)
plt.subplots_adjust(bottom=0.2)

# Initial plot
plot_user(ax, all_users[current_index])

# Add buttons
axprev = plt.axes([0.2, 0.05, 0.1, 0.075])
axnext = plt.axes([0.7, 0.05, 0.1, 0.075])
bnext = Button(axnext, 'Next User')
bnext.on_clicked(next_user)
bprev = Button(axprev, 'Previous User')
bprev.on_clicked(prev_user)

plt.show()
