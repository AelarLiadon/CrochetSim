import math
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import itertools

# Process obj

class Model:
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces

class Vertex:
    def __init__(self, x, y, z, xn, yn, zn):
        self.x = x
        self.y = y
        self.z = z
        self.xn = xn
        self.yn = yn
        self.zn = zn

def processObj(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
        vertices = []
        normals = []
        faces = []
        for line in lines:
            if line.startswith('v '):
                vertex = list(map(float, line[2:].split()))
                vertices.append(vertex)

            if line.startswith('vn '):
                normal = list(map(float, line[3:].split()))
                normals.append(normal)

            if line.startswith('f '):
                points = line[2:].split()
                points = [int(p.split('/')[0]) for p in points]
                faces.append(points)

        vertices = [Vertex(v[0], v[1], v[2], n[0], n[1], n[2]) for v, n in zip(vertices, normals)]

    return Model(vertices, faces)

def createGraph(model):
    G = nx.Graph()
    for face in model.faces:
        for i in range(len(face)):
            G.add_node(face[i], pos=(model.vertices[face[i]-1].x, model.vertices[face[i]-1].y, model.vertices[face[i]-1].z))
            G.add_edge(face[i], face[(i+1)%len(face)])
    return G

def faceGraph(model):
    facesForVertices = defaultdict(list)
    for i, vertex in enumerate(model.vertices):
        for j, face in enumerate(model.faces):
            if i+1 in face:
                facesForVertices[i+1].append(j+1)
    
    G = nx.Graph()
    for faces in facesForVertices.values():
        for face in itertools.combinations(faces, 2):
            G.add_edge(face[0], face[1])

    return G

def displayGraph(G):
    nx.draw(G, with_labels=True)
    plt.show()

def display3DGraph(G):
    pos = nx.get_node_attributes(G, "pos")
    node_xyz = np.array([pos[v] for v in sorted(G)])
    edge_xyz = np.array([(pos[u], pos[v]) for u, v in G.edges()])

    # Create the 3D figure
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    # Plot the nodes - alpha is scaled by "depth" automatically
    ax.scatter(*node_xyz.T, s=100, ec="w")

    # Plot the edges
    for vizedge in edge_xyz:
        ax.plot(*vizedge.T, color="tab:gray")

    _format_axes(ax)
    set_axes_equal(ax)
    plt.show()

def _format_axes(ax):
    """Visualization options for the 3D axes."""
    # Turn gridlines off
    ax.grid(False)
    # Suppress tick labels
    for dim in (ax.xaxis, ax.yaxis, ax.zaxis):
        dim.set_ticks([])
    # Set axes labels
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")

def set_axes_equal(ax):
    """
    Make axes of 3D plot have equal scale so that spheres appear as spheres,
    cubes as cubes, etc.

    Input
      ax: a matplotlib axis, e.g., as output from plt.gca().
    """

    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    x_middle = np.mean(x_limits)
    y_range = abs(y_limits[1] - y_limits[0])
    y_middle = np.mean(y_limits)
    z_range = abs(z_limits[1] - z_limits[0])
    z_middle = np.mean(z_limits)

    # The plot bounding box is a sphere in the sense of the infinity
    # norm, hence I call half the max range the plot radius.
    plot_radius = 0.5*max([x_range, y_range, z_range])

    ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
    ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
    ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])

def __main__():
    model = processObj('seal.obj')
    G = createGraph(model)
    display3DGraph(G)




            
