# geolife_viewer/state.py
from typing import Callable, Dict, Optional, List, Any

class AppState:
    """
    Observable state with change notifications.
    Observers receive (event_name, payload_dict).
    """
    def __init__(self):
        self._selected_user: Optional[str] = None
        self._selected_trajectory: str = "All"  # "All" or a file name
        self._selected_algorithm: Optional[str] = None  # "Douglas-Peucker" | "SQUISH" | None
        self._algorithm_params: Dict[str, Any] = {"epsilon": 0.0005, "k": 200}

        self._observers: List[Callable[[str, dict], None]] = []

    # ---- observer management ----
    def subscribe(self, fn: Callable[[str, dict], None]):
        if fn not in self._observers:
            self._observers.append(fn)

    def _notify(self, event: str, payload: dict):
        for fn in list(self._observers):
            fn(event, payload)

    # ---- setters with diff detection ----
    def set_user(self, user_id: Optional[str]):
        if user_id != self._selected_user:
            self._selected_user = user_id
            self._notify("user_changed", {"user": user_id})

    def set_trajectory(self, traj_name: str):
        if traj_name != self._selected_trajectory:
            self._selected_trajectory = traj_name
            self._notify("trajectory_changed", {"trajectory": traj_name})

    def set_algorithm(self, algorithm: Optional[str]):
        if algorithm != self._selected_algorithm:
            self._selected_algorithm = algorithm
            self._notify("algorithm_changed", {"algorithm": algorithm})

    def set_algorithm_param(self, key: str, value):
        if self._algorithm_params.get(key) != value:
            self._algorithm_params[key] = value
            self._notify("algorithm_param_changed", {"key": key, "value": value})

    # ---- getters ----
    @property
    def selected_user(self): return self._selected_user
    @property
    def selected_trajectory(self): return self._selected_trajectory
    @property
    def selected_algorithm(self): return self._selected_algorithm
    @property
    def algorithm_params(self): return dict(self._algorithm_params)