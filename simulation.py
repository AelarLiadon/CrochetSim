import networkx as nx
import numpy as np
import scipy as sp
import math
from numba import jit
import matplotlib.pyplot as plt

def springSimulation(G, iterations=100, deltaT=0.1):
    # connections dict
    connections = {node: list(G[node]) for node in G.nodes}
    positions = nx.get_node_attributes(G, 'pos')
    positions = {node: np.array(position) for node, position in positions.items()}
    velocities = {node: np.array([0, 0, 0], dtype="float64") for node in G.nodes}

    for _ in range(iterations):
        
        for node in G.nodes:
            updatePosition(node, connections, positions, velocities, deltaT)
    nx.set_node_attributes(G, positions, 'pos')

    # print(np.linalg.norm(sum([abs(vel) for vel in velocities.values()])))
    return np.linalg.norm(sum([abs(vel) for vel in velocities.values()]))

def fastExp(x):
    # return min(x*(1+np.abs(x)), 1e3)
    return x#math.sin(x)

def resultantForce(node, connections, positions):
    # Calculate the resultant force on a node
    force = np.array([0, 0, 0], dtype="float64")
    for connection in connections[node]:
        # Calculate the force between the node and its connection
        # F = k * (d - l) * u
        # k = spring constant
        # d = distance between nodes
        # l = rest length of spring
        # u = unit vector from node to connection
        connectionPosition = positions[connection]
        nodePosition = positions[node]
        d = np.linalg.norm(connectionPosition - nodePosition)
        if d < 1e-3:
            continue
        u = (connectionPosition - nodePosition) / d
        l = 1
        force += (d - l) * u
    return force

def updatePosition(node, connections, positions, velocities, deltaT):
    m = 1
    a = resultantForce(node, connections, positions) / m
    velocities[node] += a * deltaT
    positions[node] += velocities[node] * deltaT


def springSimulationNP(G, iterations=100, deltaT=0.1, analysis=False):
    connections = [list(G[node]) for node in sorted(G.nodes.keys())]
    
    positions = nx.get_node_attributes(G, 'pos')
    positions = np.array([np.array(positions[node]) for node in sorted(positions.keys())], dtype="float64")
    velocities = np.array([[0, 0, 0] for _ in range(len(G.nodes))], dtype="float64")
    forces = np.array([[0, 0, 0] for _ in range(len(G.nodes))], dtype="float64")

    if analysis:
        distanceErrors = []
        sForces = []
        sVelocities = []

    for _ in range(iterations):
        for i in range(len(G.nodes)):
            forces[i] = resultantForce(i, connections, positions)

        # sumF = sumForces(forces)
        distErr = distanceError(G, positions)
        # maxF = np.linalg.norm(np.max(np.abs(forces)))
        if distErr == 0:
            return 0
        # dT = deltaT * len(G.nodes) / sumF
        updateAllPositions(positions, velocities, forces, deltaT)

        if analysis:
            distanceErrors.append(distErr)
            sForces.append(sumForces(forces))
            sVelocities.append(sumVelocities(velocities))
        
    nx.set_node_attributes(G, {node: positions[i] for i, node in enumerate(sorted(G.nodes.keys()))}, 'pos')

    if analysis:
        plt.plot(distanceErrors, label="Distance Error")
        plt.plot(sForces, label="Sum Forces")
        plt.plot(sVelocities, label="Sum Velocities")
        plt.legend()
        plt.show()

    # print(np.linalg.norm(sum([abs(vel) for vel in velocities.values()])))
    return distErr

def springSimulationNumba(G, iterations=100, deltaT=0.1, analysis=False):
    pos = nx.get_node_attributes(G, 'pos')
    positions = np.array(np.array([pos[node] for node in G.nodes]), dtype="float64")
    velocities = np.random.rand(len(G.nodes), 3)*0.1
    adjacency = nx.adjacency_matrix(G, weight=None).toarray()

    if analysis:
        distanceErrors = []
        sForces = []
        sVelocities = []


    for _ in range(iterations):
        forces = np.array([[0, 0, 0] for _ in range(len(G.nodes))], dtype="float64")
        computeForcesNumba(positions, forces, adjacency)
        updateAllPositions(positions, velocities, forces, deltaT)

        if analysis:
            distanceErrors.append(distanceError(G, positions))
            sForces.append(sumForces(forces))
            sVelocities.append(sumVelocities(velocities))
    
    nx.set_node_attributes(G, {node: positions[i] for i, node in enumerate(G.nodes)}, 'pos')

    if analysis:
        plt.plot(distanceErrors, label="Distance Error")
        plt.plot(sForces, label="Sum Forces")
        plt.plot(sVelocities, label="Sum Velocities")
        plt.legend()
        plt.show()


    return distanceError(G, positions)

@jit(nopython=True)
def computeForcesNumba(positions, forces, adjacency):
    for i in range(len(positions)):
        for j in range(len(positions)):
            if adjacency[i, j] == 1:
                d = np.linalg.norm(positions[i] - positions[j])
                u = (positions[j] - positions[i]) / d
                l = 1
                forces[i] += (d - l) * u

# @jit(nopython=True)
def sumVelocities(velocities):
    return np.linalg.norm(np.sum(np.abs(velocities)))

# @jit(nopython=True)
def sumForces(forces):
    return np.linalg.norm(np.sum(np.abs(forces)))

def distanceError(G, positions):
    pairs = list(G.edges)
    vertexCoords = np.array([positions[node] for node in G.nodes])
    pairCoords = np.array([vertexCoords[pair[0]] - vertexCoords[pair[1]] for pair in pairs])
    dist = np.linalg.norm(pairCoords, axis=1)
    return np.sum(np.abs(dist - 1))

@jit(nopython=True)
def updateAllPositions(positions, velocities, forces, deltaT):
    m = 1
    accelerations = forces / m
    velocities += accelerations * deltaT
    positions += velocities * deltaT

import random
def objectiveFuncConstructor(G):
    def objectiveFunc(vertexCoordsFlattened):
        vertexCoords = vertexCoordsFlattened.reshape(-1, 3)
        pairs = list(G.edges)
        
        fixedNodeCoord = G.nodes[0]["pos"]
        vertexCoords = np.insert(vertexCoords, 0, fixedNodeCoord, axis=0)
        
        pairCoords = np.array([vertexCoords[pair[0]] - vertexCoords[pair[1]] for pair in pairs])
        dist = np.linalg.norm(pairCoords, axis=1)
        sumDistances = np.sum(np.abs(dist - 1))
        # print(sumDistances)
        if random.random() < 0.001:
            print(sumDistances)

        # if sumDistances < 50:
        #     return 0
        return sumDistances

    return objectiveFunc



def minimisePositions(G, bounds=None):
    # Minimise the objective function
    # Using BFGS
    initialVertexCoords = np.array([G.nodes[node]["pos"] for node in G.nodes if node != 0])
    initialVertexCoordsFlattened = initialVertexCoords.flatten()
    res = sp.optimize.minimize(objectiveFuncConstructor(G), initialVertexCoordsFlattened, method="L-BFGS-B", options={"disp": True, "maxfun": 1e7}, bounds=bounds, tol=1e-6)
    
    pos = res.x.reshape(-1, 3)
    pos = np.insert(pos, 0, G.nodes[0]["pos"], axis=0)
    nx.set_node_attributes(G, {node: pos[i] for i, node in enumerate(G.nodes)}, 'pos')
    return res

def DualAnnealing(G, bounds):
    initialVertexCoords = np.array([G.nodes[node]["pos"] for node in G.nodes if node != 0])
    initialVertexCoordsFlattened = initialVertexCoords.flatten()
    res = sp.optimize.dual_annealing(objectiveFuncConstructor(G), bounds=bounds, x0=initialVertexCoordsFlattened)
    pos = res.x.reshape(-1, 3)
    pos = np.insert(pos, 0, G.nodes[0]["pos"], axis=0)
    nx.set_node_attributes(G, {node: pos[i] for i, node in enumerate(G.nodes)}, 'pos')
    return res