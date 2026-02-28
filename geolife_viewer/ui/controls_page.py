# geolife_viewer/ui/controls_page.py
import tkinter as tk
from tkinter import ttk
from state import AppState
from config import DATA_PATH
from data_loader import list_users, list_trajectories

class ControlsPage(tk.Frame):
    """
    User & Trajectory selection (keeps your original behavior/UX).
    Writes selections into AppState; no plotting here.
    """
    def __init__(self, master, state: AppState):
        super().__init__(master)
        self.state = state

        # Populate users
        self.all_users = list_users(DATA_PATH)
        self.current_user_index = 0 if self.all_users else -1

        # UI
        tk.Label(self, text="Select User:").pack(side=tk.LEFT, padx=5)
        self.user_dropdown = ttk.Combobox(self, values=self.all_users, width=10)
        if self.all_users:
            self.user_dropdown.current(self.current_user_index)
            self.state.set_user(self.all_users[self.current_user_index])
        self.user_dropdown.bind("<<ComboboxSelected>>", self._on_user)
        self.user_dropdown.pack(side=tk.LEFT, padx=5)

        tk.Label(self, text="Select Trajectory:").pack(side=tk.LEFT, padx=5)
        self.traj_dropdown = ttk.Combobox(self, values=["All"], width=25)
        self.traj_dropdown.bind("<<ComboboxSelected>>", self._on_traj)
        self.traj_dropdown.pack(side=tk.LEFT, padx=5)

        prev_button = tk.Button(self, text="Previous User", command=self._prev_user)
        prev_button.pack(side=tk.LEFT, padx=10)
        next_button = tk.Button(self, text="Next User", command=self._next_user)
        next_button.pack(side=tk.LEFT, padx=10)

        # initialize trajectory list for current user
        self._update_trajectory_dropdown()

    def _update_trajectory_dropdown(self):
        user = self.state.selected_user
        if not user:
            self.traj_dropdown['values'] = ["All"]
            self.traj_dropdown.set("All")
            self.state.set_trajectory("All")
            return

        files = list_trajectories(DATA_PATH, user)
        values = ["All"] + files
        self.traj_dropdown['values'] = values
        current = self.traj_dropdown.get()
        if current not in values:
            self.traj_dropdown.set("All")
            self.state.set_trajectory("All")

    def _on_user(self, _evt=None):
        user_id = self.user_dropdown.get()
        if user_id in self.all_users:
            self.current_user_index = self.all_users.index(user_id)
            self.state.set_user(user_id)
            self._update_trajectory_dropdown()

    def _on_traj(self, _evt=None):
        traj_name = self.traj_dropdown.get() or "All"
        self.state.set_trajectory(traj_name)

    def _prev_user(self):
        if not self.all_users: return
        self.current_user_index = (self.current_user_index - 1) % len(self.all_users)
        uid = self.all_users[self.current_user_index]
        self.user_dropdown.set(uid)
        self.state.set_user(uid)
        self._update_trajectory_dropdown()

    def _next_user(self):
        if not self.all_users: return
        self.current_user_index = (self.current_user_index + 1) % len(self.all_users)
        uid = self.all_users[self.current_user_index]
        self.user_dropdown.set(uid)
        self.state.set_user(uid)
        self._update_trajectory_dropdown()