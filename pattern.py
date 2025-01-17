import networkx as nx
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D, art3d
from topology import _format_axes, set_axes_equal
import numpy as np
import math
import random

class Pattern:
    def __init__(self, name):
        self.name = name
        self.graph = nx.Graph()
        self.graph = None
        self.stitchRepr = None
        self.textRepr = None

    def __str__(self):
        return self.textRepr
    
    # sc: single crochet, inc: increase, dec: decrease
    def convertTextToStitch(self, text):
        stitchRepr = []
        rows = text.split("\n")
        for row in rows:
            if row:
                stitches = row.split(":")[1].strip().split(",")
                stichesUnpacked = []
                for stitch in stitches:
                    # stitch = stitch.replace(" ", "")
                    stitch = stitch.strip()

                    numStitches = 1
                    stitchType = None

                    if stitch.isnumeric():
                        numStitches = int(stitch)
                        stitchType = "sc"

                    elif " " in stitch:
                        stitch = stitch.split(" ")
                        if stitch[0].isnumeric():
                            numStitches = int(stitch[0])
                            stitchType = stitch[1]
                        elif stitch[1].isnumeric():
                            numStitches = int(stitch[1])
                            stitchType = stitch[0]
                        else:
                            raise ValueError(f"Invalid stitch representation: {stitch}")

                    else:
                        stitchType = stitch

                    for i in range(numStitches):
                        stichesUnpacked.append(stitchType)

                stitchRepr.append(stichesUnpacked)
        return stitchRepr
    
    def rowStitchCount(self, row):
        count = 0
        for stitch in row:
            if stitch == "sc" or stitch.startswith("dec"):
                count += 1
            elif stitch == "inc":
                count += 2
            elif stitch.startswith("inc"):
                count += int(stitch[3:]) + 1
            else:
                raise NotImplementedError(f"Stitch type {stitch} not implemented")
        return count

    def packStichesRow(self, row):
        packedRow = []
        stitchType = row[0]
        count = 1
        for i in range(1, len(row)):
            if row[i] == stitchType:
                count += 1
            else:
                packedRow.append(f"{count} {stitchType}")
                stitchType = row[i]
                count = 1
        packedRow.append(f"{count} {stitchType}")
        packedRow = [stitch.strip() for stitch in packedRow]
        packedRow = ", ".join(packedRow)
        return packedRow

    def convertStitchToText(self, stitchRepr):
        textRepr = ""
        for i, row in enumerate(stitchRepr):
            packedRow = self.packStichesRow(row)
            rowStitchCount = self.rowStitchCount(row)
            textRepr += f"Row {i+1} [{rowStitchCount} st]:  {packedRow}\n"
        return textRepr

    def loadFromText(self, text):
        self.stitchRepr = self.convertTextToStitch(text)
        self.textRepr = text

    def loadFromStitch(self, stitchRepr):
        self.stitchRepr = stitchRepr
        self.textRepr = self.convertStitchToText(stitchRepr)

    def StitchToGraph(self, magicCircle=True):
        self.graph = nx.Graph()
        # startRow = ["sc"] * 10
        # stitchList = [startRow] + self.stitchRepr
        stitchNum = 0
        # if magicCircle:    
        #     self.graph.add_node(0, pos=[0, 0, 0], weight=1)
        #     stitchNum = 1

        for rowNum, row in enumerate(self.stitchRepr):
            rowStitchCount = self.rowStitchCount(row)
            for i in range(rowStitchCount):
                self.graph.add_node(stitchNum, pos=[i-(rowStitchCount-1)/2, rowNum+1, random.random()*10], weight=1)

                # Horizontal edges
                if i == 0:
                    if rowStitchCount > 1:
                        self.graph.add_edge(stitchNum, stitchNum+rowStitchCount-1, weight=1/(2**rowNum))
                else:
                    self.graph.add_edge(stitchNum, stitchNum-1, weight=1/(2**rowNum))
                stitchNum += 1

        closedStitches = 0
        currentStitch = 0
        for i, row in enumerate(self.stitchRepr):
            if i == 0:
                currentStitch = self.rowStitchCount(row)
                continue

            weighting = 1/(2**i)

            for stitchNum, stitch in enumerate(row):

                # Vertical edges
                if stitch == "sc":
                    self.graph.add_edge(currentStitch, closedStitches, weight=weighting)
                    currentStitch += 1
                    closedStitches += 1

                elif stitch == "inc":
                    self.graph.add_edge(currentStitch, closedStitches, weight=weighting)
                    self.graph.add_edge(currentStitch+1, closedStitches, weight=weighting)
                    currentStitch += 2
                    closedStitches += 1

                elif stitch == "dec":
                    self.graph.add_edge(currentStitch, closedStitches, weight=weighting)
                    self.graph.add_edge(currentStitch, closedStitches+1, weight=weighting)
                    currentStitch += 1
                    closedStitches += 2

                elif stitch.startswith("dec"):
                    numDec = int(stitch[3:])
                    for i in range(numDec+1):
                        self.graph.add_edge(currentStitch, closedStitches+i, weight=weighting)
                    currentStitch += 1
                    closedStitches += numDec+1

                elif stitch.startswith("inc"):
                    numInc = int(stitch[3:])
                    for i in range(numInc+1):
                        self.graph.add_edge(currentStitch+i, closedStitches, weight=weighting)
                    currentStitch += numInc+1
                    closedStitches += 1

                else:
                    raise NotImplementedError(f"Stitch type {stitch} not implemented")
        return self.graph
    

    def spiralPos(self):
        pos = {}
        rowLengths = [self.rowStitchCount(row) for row in self.stitchRepr]
        stitchNum = 0
        for i, length in enumerate(rowLengths):
            theta = 0
            r = length / (2*math.pi)
            for j in range(length):
                x = r * math.cos(theta)
                y = r * math.sin(theta)
                pos[stitchNum] = [i, x, y]
                theta += 2*math.pi/length
                stitchNum += 1
        return pos

    def displayGraph(self):
        pos = nx.get_node_attributes(self.graph, 'pos')
        pos = {k: np.array([v[0], v[1]]) for k, v in pos.items()}
        # pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, with_labels=False, node_size=10)
        plt.show()

    def display3DGraph(self):
        pos = nx.get_node_attributes(self.graph, "pos")
        # pos = {k: np.array([v[0], v[1], 0]) for k, v in original_pos.items()}

        # rowLengths = [self.rowStitchCount(row) for row in self.stitchRepr]
        # pos = self.spiralPos(rowLengths)
        # pos = nx.spring_layout(self.graph, dim=3, k=1, iterations=500, pos=pos, weight=None, scale=None, threshold=0.05)
        # pos = nx.drawing.layout.spring_layout(self.graph, dim=3, pos=original_pos, k=1/math.sqrt(2), iterations=50, weight="weight")
        node_xyz = np.array([pos[v] for v in sorted(self.graph)])
        edge_xyz = np.array([[pos[u], pos[v]] for u, v in self.graph.edges()])

        # Create the 3D figure
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")

        # Plot the nodes - alpha is scaled by "depth" automatically
        # ax.scatter(*node_xyz.T, s=5, ec="w")

        # Plot the edges
        for vizedge in edge_xyz:
            ax.plot(*vizedge.T, color="tab:gray")

        _format_axes(ax)
        set_axes_equal(ax)
        plt.show()

    def displayFaces(self):
        v = nx.get_node_attributes(self.graph, 'pos')
        v = np.array([v[node] for node in sorted(v.keys())])
        f = nx.minimum_cycle_basis(self.graph)
        f = [np.array([v[node] for node in face]) for face in f]
        # f_norm = [(x/np.max(x)) for x in f]

        C = np.array([np.mean(sum(vertex)/len(vertex)) for vertex in f])

        fig = plt.figure()
        ax = fig.add_subplot(projection="3d")

        norm = plt.Normalize(C.min(), C.max())
        colors = plt.cm.viridis(norm(C))

        pc = art3d.Poly3DCollection(f, facecolors=colors, edgecolor="black")
        ax.add_collection(pc)
        

        plt.show()



strPattern = """
Row   0 [ 10 st]:  10 sc
Row   1 [ 15 st]:  inc, 1, inc, 1, inc, 1, inc, 1, inc, 1
Row   2 [ 19 st]:  2, inc, 3, inc, 3, inc, 3, inc
Row   3 [ 23 st]:  1, inc, 3, inc, 4, inc, 4, inc, 3
Row   4 [ 28 st]:  3, inc, 3, inc, 4, inc, 4, inc, 3, inc, 1
Row   5 [ 32 st]:  3, inc, 6, inc, 6, inc, 6, inc, 3
Row   6 [ 37 st]:  2, inc, 5, inc, 5, inc, 6, inc, 5, inc, 4
Row   7 [ 41 st]:  inc, 8, inc, 8, inc, 9, inc, 8
Row   8 [ 45 st]:  3, inc, 9, inc, 9, inc, 10, inc, 6
Row   9 [ 50 st]:  1, inc, 8, inc, 8, inc, 8, inc, 8, inc, 7
Row  10 [ 54 st]:  9, inc, 12, inc, 11, inc, 12, inc, 2
Row  11 [ 59 st]:  7, inc, 10, inc, 10, inc, 9, inc, 10, inc, 3
Row  12 [ 63 st]:  3, inc, 14, inc, 14, inc, 13, inc, 11
Row  13 [ 67 st]:  8, inc, 15, inc, 15, inc, 14, inc, 7
Row  14 [ 72 st]:  8, inc, 12, inc, 13, inc, 12, inc, 12, inc, 5
Row  15 [ 69 st]:  4, dec, 22, dec, 22, dec, 18
Row  16 [ 66 st]:  15, dec, 21, dec, 21, dec, 6
Row  17 [ 63 st]:  4, dec, 20, dec, 20, dec, 16
Row  18 [ 60 st]:  15, dec, 19, dec, 19, dec, 4
Row  19 [ 57 st]:  7, dec, 18, dec, 18, dec, 11
Row  20 [ 54 st]:  dec, 17, dec, 17, dec, 17
Row  21 [ 51 st]:  8, dec, 16, dec, 16, dec, 8
Row  22 [ 48 st]:  dec, 15, dec, 15, dec, 15
Row  23 [ 45 st]:  9, dec, 14, dec, 14, dec, 5
Row  24 [ 42 st]:  3, dec, 13, dec, 13, dec, 10
Row  25 [ 39 st]:  11, dec, 12, dec, 12, dec, 1
Row  26 [ 36 st]:  7, dec, 11, dec, 11, dec, 4
Row  27 [ 33 st]:  2, dec, 10, dec, 10, dec, 8
Row  28 [ 30 st]:  8, dec, 9, dec, 9, dec, 1
Row  29 [ 27 st]:  4, dec, 8, dec, 8, dec, 4
Row  30 [ 20 st]:  2, dec, 1, dec, 2, dec, 2, dec, 2, dec, 2, dec, 2, dec
Row  31 [ 15 st]:  2, dec, 2, dec, 2, dec, 2, dec, 2, dec
Row  32 [ 11 st]:  2, dec, 2, dec, 1, dec, 2, dec
Row  33 [ 10 st]:  2, dec, 7
Row  34 [  9 st]:  6, dec, 2
Row  35 [  9 st]:  9
Row  36 [  8 st]:  2, dec, 5
Row  37 [  8 st]:  8
Row  38 [  7 st]:  6, dec
Row  39 [  7 st]:  7
Row  40 [  6 st]:  2, dec, 3
Row  41 [  6 st]:  6
Row  42 [  5 st]:  4, dec
Row  43 [  5 st]:  5
Row  44 [  4 st]:  1, dec, 2
Row  45 [  4 st]:  4
Row  46 [  3 st]:  dec, 2
Row  47 [  3 st]:  3
Row  48 [  2 st]:  1, dec
Row  49 [  2 st]:  2
Row  50 [  1 st]:  dec
Row  51 [  1 st]:  1
"""

lathe2 = """
Row   0 [  7 st]: 7 sc
Row   1 [ 14 st]: inc, inc, inc, inc, inc, inc, inc
Row   2 [ 20 st]:  1, inc, 2, inc, 1, inc, 1, inc, 2, inc, 1, inc
Row   3 [ 23 st]:  4, inc, 6, inc, 6, inc, 1
Row   4 [ 27 st]:  2, inc, 4, inc, 5, inc, 5, inc, 3
Row   5 [ 29 st]:  1, inc, 12, inc, 12
Row   6 [ 32 st]:  9, inc, 8, inc, 9, inc
Row   7 [ 33 st]:  2, inc, 29
Row   8 [ 34 st]:  19, inc, 13
Row   9 [ 35 st]:  2, inc, 31
Row  10 [ 36 st]:  19, inc, 15
Row  11 [ 35 st]:  2, dec, 32
Row  12 [ 36 st]:  19, inc, 15
Row  13 [ 38 st]:  10, inc, 17, inc, 7
Row  14 [ 39 st]:  9, inc, 28
Row  15 [ 41 st]:  inc, 18, inc, 19
Row  16 [ 43 st]:  9, inc, 19, inc, 11
Row  17 [ 45 st]:  19, inc, 20, inc, 2
Row  18 [ 46 st]:  18, inc, 26
Row  19 [ 46 st]:  46
Row  20 [ 46 st]:  46
Row  21 [ 42 st]:  2, dec, 10, dec, 9, dec, 10, dec, 7
Row  22 [ 36 st]:  2, dec, 5, dec, 5, dec, 5, dec, 5, dec, 5, dec, 3
Row  23 [ 30 st]:  3, dec, 4, dec, 4, dec, 4, dec, 4, dec, 4, dec, 1
Row  24 [ 24 st]:  2, dec, 3, dec, 3, dec, 3, dec, 3, dec, 3, dec, 1
Row  25 [ 19 st]:  1, dec, 3, dec, 2, dec, 3, dec, 3, dec, 2
Row  26 [ 16 st]:  1, dec, 4, dec, 4, dec, 4
Row  27 [ 12 st]:  1, dec, 2, dec, 2, dec, 2, dec, 1
Row  28 [ 10 st]:  3, dec, 4, dec, 1
Row  29 [ 12 st]:  1, inc, 4, inc, 3
Row  30 [ 14 st]:  3, inc, 5, inc, 2
Row  31 [ 15 st]:  2, inc, 11
Row  32 [ 15 st]:  15
Row  33 [ 14 st]:  9, dec, 4
Row  34 [  9 st]:  dec, 1, dec, 1, dec, 1, dec, 1, dec
Row  35 [  3 st]:  dec2, dec2, dec2
Row  36 [  1 st]:  dec2
"""


spherePattern = """
Row   0 [  5 st]:  5 sc
Row   1 [ 11 st]:  2 inc, inc2, 2 inc
Row   2 [ 16 st]:  inc, 2 sc, inc, 1 sc, inc, 1 sc, inc, 1 sc, inc, 1 sc
Row   3 [ 16 st]:  2 sc, inc, 3 sc, inc, 2 sc, inc, 2 sc, inc, 2 sc, inc
Row   4 [ 21 st]:  4 sc, inc, 5 sc, inc, 4 sc, inc, 4 sc, inc
Row   5 [ 25 st]:  inc, 7 sc, inc, 8 sc, inc, 7 sc
Row   6 [ 28 st]:  22 sc, inc, 5 sc
Row   7 [ 29 st]:  8 sc, inc, 20 sc
Row   8 [ 29 st]:  22 sc, dec, 6 sc
Row   9 [ 28 st]:  8 sc, dec, 19 sc
Row  10 [ 25 st]:  5 sc, dec, 7 sc, dec, 8 sc, dec, 2 sc
Row  11 [ 21 st]:  dec, 4 sc, dec, 4 sc, dec, 4 sc, dec, 5 sc
Row  12 [ 16 st]:  1 sc, dec, 3 sc, dec, 2 sc, dec, 2 sc, dec, 2 sc, dec, 1 sc
Row  13 [ 11 st]:  dec, 1 sc, dec, 2 sc, dec, 1 sc, dec, 1 sc, dec, 1 sc
Row  14 [  5 st]:  dec, dec, dec2, dec, dec
"""

smallSphere = """
Row   0 [  5 st]:  5 sc
Row   1 [ 10 st]:  5 inc
Row   2 [ 14 st]:  inc, 2 sc, inc, 1 sc, inc, 2 sc, inc, 1 sc
Row   3 [ 15 st]:  7 sc, inc, 6 sc
Row   4 [ 14 st]:  dec, 13 sc
Row   5 [ 10 st]:  dec, 1 sc, dec, 2 sc, dec, 1 sc, dec, 2 sc
Row   6 [  5 st]:  dec, dec, dec, dec, dec
"""

testPattern = """
Row   0 [  5 st]:  5 sc
Row   1 [ 10 st]:  5 inc
Row   2 [ 16 st]:  10 inc
Row   3 [ 16 st]:  20 inc
Row   4 [ 21 st]:  40 inc
Row   4 [ 21 st]:  80 inc
Row   4 [ 21 st]:  160 inc

"""

hyperbolicPattern = """
Row  -1 [  1 st]: sc
Row   0 [  6 st]: inc5
Row   1 [  18 st]: 6 inc2
"""
# Row   1 [ 25 st]:  3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc
# Row   2 [ 31 st]:  3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, sc
# Row   3 [ 38 st]:  3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc
# Row   4 [ 47 st]:  3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 2 sc
# Row   5 [ 58 st]:  3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc
# Row   6 [ 72 st]:  3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 2 sc
# Row   7 [ 90 st]:  3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc
# Row   8 [ 112 st]: 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 2 sc
# Row   9 [ 140 st]: 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc
# Row  10 [ 175 st]: 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc, 3 sc, inc


if __name__ == "__main__":
    import simulation
    import animation

    pattern = Pattern("test")
    pattern.loadFromText(smallSphere)
    print(pattern.textRepr)
    print(pattern.stitchRepr)
    pattern.StitchToGraph()
    # Remove attributes
    # for node in pattern.graph.nodes:
    #     pattern.graph.nodes[node].pop("pos", None)
    # nx.write_gexf(pattern.graph, "hyperbolic.gexf")
    # print(pattern.graph.edges)
    # pattern.displayGraph()

    # rowLengths = [pattern.rowStitchCount(row) for row in pattern.stitchRepr]
    pos = pattern.spiralPos()
    pos = {k: np.array([v[0] + random.random(), v[1] + random.random(), v[2] + random.random()]) for k, v in pos.items()}
    nx.set_node_attributes(pattern.graph, pos, "pos")
    # pattern.display3DGraph()

    print("Minimising positions")
    # res = simulation.minimisePositions(pattern.graph)
    # boundsX = (0, len(pattern.stitchRepr)+1)
    # r = max([abs(pos[i][1]) for i in pos])+1
    # boundsY = (-r, r)
    # boundsZ = (-r, r)
    # bounds = [boundsX, boundsY, boundsZ] * (len(pos)-1)
    # res = simulation.minimisePositions(pattern.graph, bounds=bounds)


    # print(res.x)
    # print(res.fun)

    # animation.animateGraph(pattern.graph, simulation.springSimulationNumba, iterations=100, deltaT=0.02, interval=200)
    # print(simulation.springSimulationNP(pattern.graph, 10000, 0.001, analysis=True))
    # print(simulation.springSimulationNP(pattern.graph, 1000, 0.01, analysis=True))
    # for i in range(50):
    #     print(simulation.springSimulationNP(pattern.graph, 1000, 0.01, analysis=False))
    pattern.display3DGraph()

    