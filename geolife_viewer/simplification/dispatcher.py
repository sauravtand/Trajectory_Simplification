# geolife_viewer/simplification/dispatcher.py
from functools import lru_cache
from typing import List, Tuple, Optional, Dict
import os
from simplification.rdp import douglas_peucker
from simplification.squish import squish

Point = Tuple[float, float]

def _file_sig(file_path: str) -> Tuple[str, float]:
    """Return a cache-safe signature of a data file (path, mtime)."""
    try:
        return (os.path.abspath(file_path), os.path.getmtime(file_path))
    except OSError:
        return (os.path.abspath(file_path), 0.0)

@lru_cache(maxsize=256)
def _simplify_cached(file_sig: Tuple[str, float],
                     algorithm: Optional[str],
                     epsilon: float,
                     k: int,
                     coords: Tuple[Point, ...]) -> Tuple[Point, ...]:
    if algorithm is None:
        return coords
    if algorithm == "Douglas-Peucker":
        return tuple(douglas_peucker(list(coords), epsilon))
    if algorithm == "SQUISH":
        return tuple(squish(list(coords), k=k, epsilon=epsilon))
    # Fallback: no simplification
    return coords

def simplify_trajectory(file_path: str,
                        coords: List[Point],
                        algorithm: Optional[str],
                        params: Dict[str, float | int]) -> List[Point]:
    """
    Public dispatcher: stable signature for the rest of the app.
    - `file_path` helps cache invalidation on file change (mtime).
    - `coords` is a list[(lon, lat)].
    - `algorithm` is one of: None | "Douglas-Peucker" | "SQUISH".
    - `params` includes: epsilon (float), k (int for SQUISH).
    """
    eps = float(params.get("epsilon", 0.0005))
    k = int(params.get("k", 200))
    sig = _file_sig(file_path)
    return list(_simplify_cached(sig, algorithm, eps, k, tuple(coords)))