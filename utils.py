import pandas as pd


def read_plt(path, include_time=False):
    """
    Read a GeoLife .plt trajectory file.

    When include_time=True, return tuples in the form
    (lat, lon, timestamp_seconds_from_start).
    Otherwise return (lat, lon).
    """
    df = pd.read_csv(
        path,
        skiprows=6,
        header=None,
        names=["lat", "lon", "unused", "alt", "date_days", "date", "time"],
    )

    df = df[["lat", "lon", "date", "time"]].dropna(subset=["lat", "lon"])
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)

    if not include_time:
        return list(zip(df["lat"], df["lon"]))

    dt = pd.to_datetime(
        df["date"].astype(str) + " " + df["time"].astype(str),
        errors="coerce",
    )

    timestamps = [None] * len(df)
    valid = dt.dropna()
    if not valid.empty:
        start = valid.iloc[0]
        timestamps = [
            None if pd.isna(t) else float((t - start).total_seconds())
            for t in dt
        ]

    return list(zip(df["lat"], df["lon"], timestamps))
