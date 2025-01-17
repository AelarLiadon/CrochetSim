import matplotlib.pyplot as plt
import numpy as np
import math
import random as rand
from matplotlib import animation
import networkx as nx
from topology import _format_axes, set_axes_equal

iters = None
error = None

def animateGraph(G, simulationFunc, iterations=100, deltaT=0.1, interval=200):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    pos = nx.get_node_attributes(G, 'pos')
    pos = {node: np.array(position) for node, position in pos.items()}


    def update(frame):
        cumulative_error = simulationFunc(G, 500, deltaT)
        pos = nx.get_node_attributes(G, 'pos')
        pos = {node: np.array(position) for node, position in pos.items()}

        node_xyz = np.array([pos[v] for v in sorted(G)])
        edge_xyz = np.array([[pos[u], pos[v]] for u, v in G.edges()])

        # Create the 3D figure

        # Plot the nodes - alpha is scaled by "depth" automatically
        # ax.scatter(*node_xyz.T, s=5, ec="w")

        ax.clear()
        # Plot the edges
        for vizedge in edge_xyz:
            ax.plot(*vizedge.T, color="tab:gray")

        _format_axes(ax)
        set_axes_equal(ax)

        global iters
        global error

        if iters is not None:
            iters.remove()
        if error is not None:
            error.remove()

        iters = ax.text(0.5, 1.05, 7, "", bbox={'facecolor':'w', 'alpha':0.5, 'pad':5}, transform=ax.transAxes, ha='center')
        iters.set_text("Iter: " + str(frame))

        error = ax.text(0.5, 1.1, 0, "", bbox={'facecolor':'w', 'alpha':0.5, 'pad':5}, transform=ax.transAxes, ha='center')
        error.set_text("Error: " + str(round(cumulative_error, 4)))
                                            




    ani = animation.FuncAnimation(fig, update, frames=iterations, repeat=False, interval=interval)
    plt.show()