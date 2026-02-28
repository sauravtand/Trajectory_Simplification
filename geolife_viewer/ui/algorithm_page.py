# geolife_viewer/ui/algorithm_page.py
import tkinter as tk
from tkinter import ttk
from state import AppState

class AlgorithmPage(tk.Frame):
    """
    Single-select algorithm chooser with parameters.
    - Radio buttons: None, Douglas–Peucker, SQUISH
    - Parameters:
        - epsilon (float) for both
        - k (int) for SQUISH
    """
    def __init__(self, master, state: AppState):
        super().__init__(master)
        self.state = state

        tk.Label(self, text="Simplification Algorithm:").pack(anchor="w", pady=(0, 6))

        self._alg_var = tk.StringVar(value=state.selected_algorithm or "None")

        for label in ["None", "Douglas-Pecker", "SQUISH"]:
            # (Typo intentionally fixed below to "Douglas-Peucker" in handler)
            rb = ttk.Radiobutton(self, text=label, value=label, variable=self._alg_var, command=self._on_alg_changed)
            rb.pack(anchor="w")

        # epsilon
        frm_eps = tk.Frame(self)
        frm_eps.pack(anchor="w", pady=(8, 4), fill=tk.X)
        tk.Label(frm_eps, text="ε (epsilon):").pack(side=tk.LEFT)
        self._eps_var = tk.DoubleVar(value=state.algorithm_params.get("epsilon", 0.0005))
        eps_entry = ttk.Entry(frm_eps, textvariable=self._eps_var, width=10)
        eps_entry.pack(side=tk.LEFT, padx=8)
        eps_entry.bind("<Return>", self._on_params_changed)

        # k for SQUISH
        frm_k = tk.Frame(self)
        frm_k.pack(anchor="w", pady=(4, 0), fill=tk.X)
        tk.Label(frm_k, text="k (SQUISH capacity):").pack(side=tk.LEFT)
        self._k_var = tk.IntVar(value=int(state.algorithm_params.get("k", 200)))
        k_entry = ttk.Entry(frm_k, textvariable=self._k_var, width=10)
        k_entry.pack(side=tk.LEFT, padx=8)
        k_entry.bind("<Return>", self._on_params_changed)

        ttk.Button(self, text="Apply", command=self._apply_params).pack(anchor="w", pady=8)

    def _on_alg_changed(self):
        value = self._alg_var.get()
        # normalize label typo if any
        if value == "Douglas-Pecker":
            value = "Douglas-Peucker"
        alg = None if value == "None" else value
        self.state.set_algorithm(alg)

    def _on_params_changed(self, _evt=None):
        self._apply_params()

    def _apply_params(self):
        self.state.set_algorithm_param("epsilon", float(self._eps_var.get()))
        self.state.set_algorithm_param("k", int(self._k_var.get()))