# geolife_viewer/graph/graph_page.py
import os
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk

from  state import AppState
from  config import DATA_PATH, FIGSIZE, LINE_WIDTH, FONT_TITLE, FONT_LABEL, BG_FACE
from  data_loader import list_trajectories, read_plt
from  simplification.dispatcher import simplify_trajectory

class GraphPage(tk.Frame):
    """
    Owns the Matplotlib figure. Subscribes to AppState and re-renders
    ONLY on user / trajectory / algorithm changes (and param changes).
    """
    def __init__(self, master, state: AppState):
        super().__init__(master)
        self.state = state

        # Matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=FIGSIZE)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Optional toolbar
        tb = NavigationToolbar2Tk(self.canvas, self)
        tb.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # runtime cache for raw file -> dataframe (avoid re-reading)
        self._df_cache = {}   # file_path -> DataFrame
        # last render state (for diffing)
        self._last = {"user": None, "traj": None, "alg": None, "params": None}

        # subscribe to state changes
        self.state.subscribe(self._on_state_event)

        # initial draw (if user already set by ControlsPage)
        self._render_if_needed()

    def _on_state_event(self, event: str, payload: dict):
        if event in {"user_changed", "trajectory_changed", "algorithm_changed", "algorithm_param_changed"}:
            self._render_if_needed()

    def _render_if_needed(self):
        u = self.state.selected_user
        t = self.state.selected_trajectory
        a = self.state.selected_algorithm
        p = tuple(sorted(self.state.algorithm_params.items()))

        if (u, t, a, p) == (self._last["user"], self._last["traj"], self._last["alg"], self._last["params"]):
            return  # no change -> no re-render

        self._last.update({"user": u, "traj": t, "alg": a, "params": p})
        self._render(u, t, a)

    def _read_df(self, file_path: str):
        if file_path not in self._df_cache:
            self._df_cache[file_path] = read_plt(file_path)
        return self._df_cache[file_path]

    def _render(self, user_id, trajectory_name, algorithm):
        ax = self.ax
        ax.clear()

        if not user_id:
            ax.set_title("No user selected", **FONT_TITLE)
            self.canvas.draw(); return

        traj_folder = os.path.join(DATA_PATH, user_id, "Trajectory")
        files = list_trajectories(DATA_PATH, user_id)
        if not files:
            ax.set_title(f"No trajectories for user {user_id}", **FONT_TITLE)
            self.canvas.draw(); return

        if trajectory_name not in ["All"] + files:
            trajectory_name = "All"

        colors = matplotlib.colormaps['tab20'].resampled(max(1, len(files)))
        for idx, file in enumerate(files):
            file_path = os.path.join(traj_folder, file)
            df = self._read_df(file_path)

            # Build (lon, lat) tuples
            coords = list(zip(df["lon"].tolist(), df["lat"].tolist()))

            # Apply simplification if algorithm selected
            simplified = simplify_trajectory(file_path, coords, algorithm, self.state.algorithm_params)
            xs = [c[0] for c in simplified]
            ys = [c[1] for c in simplified]

            visible = (trajectory_name == "All") or (trajectory_name == file)
            ax.plot(xs, ys, color=colors(idx), linewidth=LINE_WIDTH, alpha=0.9, visible=visible, label=file)

        ax.set_title(f"Trajectories for User {user_id}" + (f"  [{algorithm}]" if algorithm else ""), **FONT_TITLE)
        ax.set_xlabel("Longitude", **FONT_LABEL)
        ax.set_ylabel("Latitude", **FONT_LABEL)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_facecolor(BG_FACE)
        if len(files) <= 10:
            ax.legend(fontsize=8, loc='upper right')
        self.canvas.draw()