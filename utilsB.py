import pandas as pd


def read_plt(path, include_time=False):
    """
    Read a Geolife .plt trajectory file.

    Parameters
    ----------
    path : str
        Path to the .plt file.
    include_time : bool
        If True, return (lat, lon, timestamp_seconds_from_start).
        Otherwise return (lat, lon).

    Returns
    -------
    list
        List of tuples.
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

    if len(dt) == 0 or dt.isna().all():
        timestamps = [None] * len(df)
    else:
        valid_dt = dt.copy()
        first_valid = valid_dt.dropna().iloc[0] if not valid_dt.dropna().empty else pd.NaT

        if pd.isna(first_valid):
            timestamps = [None] * len(df)
        else:
            # seconds from trajectory start
            timestamps = []
            for t in valid_dt:
                if pd.isna(t):
                    timestamps.append(None)
                else:
                    timestamps.append((t - first_valid).total_seconds())

    return list(zip(df["lat"], df["lon"], timestamps))