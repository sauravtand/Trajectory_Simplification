# geolife_viewer/app.py
import tkinter as tk
from state import AppState
from ui.controls_page import ControlsPage
from ui.algorithm_page import AlgorithmPage
from graph.graph_page import GraphPage

def main():
    root = tk.Tk()
    root.title("Interactive GeoLife Trajectory Viewer")

    state = AppState()

    # Layout: Graph on top, controls bottom-left, algorithm bottom-right
    graph = GraphPage(root, state)
    graph.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    bottom = tk.Frame(root)
    bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=6)

    controls = ControlsPage(bottom, state)
    controls.pack(side=tk.LEFT, padx=8)

    algo = AlgorithmPage(bottom, state)
    algo.pack(side=tk.LEFT, padx=24)

    root.mainloop()

if __name__ == "__main__":
    main()