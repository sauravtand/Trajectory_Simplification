# utils.py
import pandas as pd

def read_plt(path):
    df = pd.read_csv(
        path, skiprows=6, header=None,
        names=["lat","lon","unused","alt","date_days","date","time"]
    )
    return list(zip(df["lat"], df["lon"]))