# geolife_viewer/data_loader.py
import os
import pandas as pd

def list_users(data_path: str):
    return sorted([u for u in os.listdir(data_path) if u.isdigit()])

def list_trajectories(data_path: str, user_id: str):
    traj_folder = os.path.join(data_path, user_id, "Trajectory")
    if not os.path.exists(traj_folder):
        return []
    return sorted([f for f in os.listdir(traj_folder) if f.endswith(".plt")])

def read_plt(file_path: str) -> pd.DataFrame:
    return pd.read_csv(
        file_path,
        skiprows=6,
        header=None,
        names=["lat", "lon", "unused", "alt", "date_days", "date", "time"]
    )
