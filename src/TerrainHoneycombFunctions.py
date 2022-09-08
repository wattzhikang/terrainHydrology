from concurrent.futures import process
import typing

import numpy as np
from scipy.spatial import Voronoi
import Math

from tqdm import trange

from DataModel import Point, ShoreModel, ShoreModelShapefile, TerrainHoneycomb, Q, Edge, HydroPrimitive, HydrologyNetwork, RasterData

def getRidgeElevation(q: Q, hydrology: HydrologyNetwork, terrainSlope: RasterData, terrainSlopeRate: float) -> float:
    """Computes the elevation of a ridge/crest

    :param q: The ridge primitive to compute an elevation for
    :type q: Q
    :param hydrology: The hydrology network for the terrain
    :type hydrology: HydrologyNetwork
    :param terrainSlope: A raster that indicates how steep the terrain should climb in different areas
    :type terrainSlope: RasterData
    :param terrainSlopeRate: This is documented in hydrology.py under "Terrain Parameters"
    :type terrainSlopeRate: float
    """
    nodes = [hydrology.node(n) for n in q.nodes]
    maxElevation = max([node.elevation for node in nodes])
    d = np.linalg.norm(q.position - nodes[0].position)
    slope = terrainSlopeRate * terrainSlope[q.position[0],q.position[1]] / 255
    return maxElevation + d * slope

def initializeTerrainHoneycomb(shore: ShoreModel, hydrology: HydrologyNetwork) -> TerrainHoneycomb:
    points = [node.position for node in hydrology.allNodes()]

    # Add corners so that the entire area is covered
    points.append((-shore.realShape[0],-shore.realShape[1]))
    points.append((-shore.realShape[0],shore.realShape[1]))
    points.append((shore.realShape[0],shore.realShape[1]))
    points.append((shore.realShape[0],-shore.realShape[1]))

    vor = Voronoi(points,qhull_options='Qbb Qc Qz Qx')

    # This is for reverse lookup of ridge_points. Given a point (node ID),
    # it retrieves the ridges that border it
    point_ridges: typing.Dict[int, typing.List[int]] = ridgesToPoints(vor)

    createdQs: typing.Dict[int, Q] = { }
    createdEdges: typing.Dict[int, Edge] = { }

    cells = { }
    for node in hydrology.allNodes():
        # order the cell edges in counterclockwise order
        point_ridges[node.id] = orderEdges(point_ridges[node.id], node.position, vor, shore)
        orderCreatedEdges(point_ridges[node.id], vor, createdEdges)

        # then we have to organize and set up all the edges of the cell
        cells[node.id] = processRidge(point_ridges[node.id], [ ], createdEdges, createdQs, vor, shore, hydrology)

    return cells

# This is for reverse lookup of ridge_points. Given a point (node ID),
# it retrieves the ridges that border it
def ridgesToPoints(vor: Voronoi) -> typing.Dict[int, typing.List[int]]:
    point_ridges = { }
    for ridgeID, points in enumerate(vor.ridge_points):
        for point in points: # there should only be 2 of these
            if point in point_ridges:
                point_ridges[point].append(ridgeID)
            else:
                point_ridges[point] = [ ridgeID ]
    return point_ridges

# This function will process a normal ridge that is entirely located on land and may or may not be transected by a river.
# If this ridge intersects the shore at all, it immediately hands over control to terminateRidgeAndStartShore()
# Processes: a perfectly normal ridge (including a ridge that is the first in a chain)
# This function does not assume that there is a previously-processed ridge
def processRidge(edgesLeft: typing.List[int], cellEdges: typing.List[Edge], createdEdges: typing.Dict[int, Edge], createdQs: typing.Dict[int, Q], vor: Voronoi, shore: ShoreModel, hydrology: HydrologyNetwork) -> typing.List[Edge]:
    if len(edgesLeft) < 1:
        # if there are no more edges left to process, then we're done here
        return cellEdges

    ridgeID: int = edgesLeft[0]
    if shore.isOnLand(getVertex1(ridgeID, vor)):
        newRidge: Edge = None
        # both land Edges and the Qs that they are made of are shared between cells. So we have to
        # check both kinds of objects to see if they have already been created before creating them
        if edgesLeft[0] in createdEdges:
            newRidge = createdEdges[edgesLeft[0]]
        else:
            Q0: Q = None
            if len(cellEdges) > 0:
                # just get the vertex of the previous edge if we can
                Q0 = cellEdges[-1][1]
            elif getVertexID0(ridgeID, vor) in createdQs:
                # the previous edge hasn't been created, but maybe this Q has been
                Q0 = createdQs[getVertexID0(ridgeID, vor)]
            else:
                Q0 = Q(getVertex0(ridgeID, vor))
                createdQs[getVertexID0(ridgeID, vor)] = Q0

            Q1: Q = None
            if getVertexID1(ridgeID, vor) in createdQs:
                Q1 = createdQs[getVertexID1(ridgeID, vor)]
            else:
                Q1 = Q(getVertex1(ridgeID, vor))
                createdQs[getVertexID1(ridgeID, vor)] = Q1

            shoreSegment: typing.Tuple[int,int] = None
            if len(cellEdges) > 1 and cellEdges[-1].isShore:
                shoreSegment = cellEdges[-1].shoreSegment

            # if ridgeID == 35:
            #     breakpoint()
            newRidge: Edge = Edge(Q0, Q1, hasRiver=hasRiver(ridgeID, vor, hydrology), isShore=False, shoreSegment=shoreSegment)
            createdEdges[edgesLeft[0]] = newRidge
        cellEdges.append(newRidge)
        edgesLeft = edgesLeft[1:]
        return processRidge(edgesLeft, cellEdges, createdEdges, createdQs, vor, shore, hydrology)
    else:
        # we know that the first vertex is on land, so if the second vertex
        # isn't, then we know that this edge must intersect the shore somewhere
        return terminateRidgeAndStartShore(edgesLeft, cellEdges, createdEdges, createdQs, vor, shore, hydrology)

# The current ridge intersects the shoreline. Terminate it at the shore, and then start processing the shoreline
# Processes: a ridge that intersects the shore
# This function does not assume that there is a previously-processed edge
def terminateRidgeAndStartShore(edgesLeft: typing.List[int], cellEdges: typing.List[Edge], createdEdges: typing.Dict[int, Edge], createdQs: typing.Dict[int, Q], vor: Voronoi, shore: ShoreModel, hydrology: HydrologyNetwork) -> typing.List[Edge]:
    terminatedEdge: Edge = None
    shoreSegment = None # TMP DEBUG
    if edgesLeft[0] in createdEdges:
        terminatedEdge = createdEdges[edgesLeft[0]]
    else:
        # we can't assume that the previous ridge has been processed
        Q0: Q = None
        if len(cellEdges) > 0:
            # just get the vertex of the previous edge if we can
            Q0 = cellEdges[-1][1]
        elif getVertexID0(edgesLeft[0], vor) in createdQs:
            # the previous edge hasn't been created, but maybe this Q has been
            Q0 = createdQs[getVertexID0(edgesLeft[0], vor)]
        else:
            Q0 = Q(getVertex0(edgesLeft[0], vor))
            createdQs[getVertexID0(edgesLeft[0], vor)] = Q0

        # We can assume that this Q has not been created. This Q will
        # only belong to this edge, since it comes out of the sea, and
        # because this edge has not been created, therefore this Q
        # cannot have been, either.
        Q1: Q = None

        shoreSegment: typing.Tuple[int, int] = findIntersectingShoreSegment(getVertex0(edgesLeft[0], vor), getVertex1(edgesLeft[0], vor), shore)
        if shoreSegment[0] >= len(shore) or shoreSegment[1] >= len(shore):
            breakpoint()
        intersection: Point = Math.edgeIntersection(getVertex0(edgesLeft[0], vor), getVertex1(edgesLeft[0], vor), shore[shoreSegment[0]], shore[shoreSegment[1]])

        Q1: Q = Q(intersection)

        # if edgesLeft[0] == 35:
        #     breakpoint()
        terminatedEdge = Edge(Q0, Q1, hasRiver=hasRiver(edgesLeft[0], vor, hydrology), isShore=False, shoreSegment=shoreSegment)
        createdEdges[edgesLeft[0]] = terminatedEdge

    cellEdges.append(terminatedEdge)
    edgesLeft = edgesLeft[1:]
    return processShoreSegment(terminatedEdge.shoreSegment, edgesLeft, cellEdges, createdEdges, createdQs, vor, shore, hydrology)
# After a ridge has been terminated at the coast, this function can process the coastline until it finds an intersection
# with one of the other ridges in the cell
# This function assumes that at least one ridge has been processed so far.
def processShoreSegment(currentSegment: typing.Tuple[int, int], edgesLeft: typing.List[int], cellEdges: typing.List[Edge], createdEdges: typing.Dict[int, Edge], createdQs: typing.Dict[int, Q], vor: Voronoi, shore: ShoreModel, hydrology: HydrologyNetwork) -> typing.List[Edge]:
    Q0: Q = cellEdges[-1][1]

    # does the current shore segment intersect with any of the edges that haven't been processed yet?
    for otherRidgeID in edgesLeft:
        # if currentSegment is None:
        #     breakpoint()
        if Math.edgeIntersection(getVertex0(otherRidgeID, vor), getVertex1(otherRidgeID, vor), shore[currentSegment[0]], shore[currentSegment[1]]) is not None:
            return terminateShoreAndStartRidge(otherRidgeID, currentSegment, edgesLeft, cellEdges, createdEdges, createdQs, vor, shore, hydrology)
    
    # This Q does not exist anywhere but in this cell, so it cannot have been created previously
    Q1: Q = Q(shore[currentSegment[1]])

    # if edgesLeft[0] == 35:
    #     breakpoint()
    newEdge: Edge = Edge(Q0, Q1, hasRiver=False, isShore=True, shoreSegment=currentSegment)
    # createdEdges[edgesLeft[0]] = newEdge
    cellEdges.append(newEdge)

    nextIdx = currentSegment[1]+1 if currentSegment[1]+1 < len(shore) else 0
    currentSegment = (currentSegment[1], nextIdx)

    return processShoreSegment(currentSegment, edgesLeft, cellEdges, createdEdges, createdQs, vor, shore, hydrology)

# This function terminates the shore segment. It does _not_ process the following ridge segment, as processRidge()
# can simply observe that this ridge has been processed, and so it can just use the second Q of this edge to
# start the next one.
# Processes: the terminated shore segment
def terminateShoreAndStartRidge(intersectingRidgeID: int, currentSegment: typing.Tuple[int, int], edgesLeft: typing.List[int], cellEdges: typing.List[Edge], createdEdges: typing.Dict[int, Edge], createdQs: typing.Dict[int, Q], vor: Voronoi, shore: ShoreModel, hydrology: HydrologyNetwork) -> typing.List[Edge]:
    Q0: Q = cellEdges[-1][1]
    Q1: Q = None
    # if the intersecting ridge has already been created, then all we need to do is meet it
    if intersectingRidgeID in createdEdges:
        Q1 = createdEdges[intersectingRidgeID].Q0
    else:
        intersection: typing.Tuple[float, float] = Math.edgeIntersection(getVertex0(intersectingRidgeID, vor), getVertex1(intersectingRidgeID, vor), shore[currentSegment[0]], shore[currentSegment[1]])
        Q1: Q = Q(intersection)

    # if edgesLeft[0] == 35:
    #     breakpoint()
    newEdge: Edge = Edge(Q0, Q1, hasRiver=False, isShore=True, shoreSegment=currentSegment)
    # createdEdges[edgesLeft[0]] = newEdge
    cellEdges.append(newEdge)

    intersectingRidgeIdx = edgesLeft.index(intersectingRidgeID)
    edgesLeft = edgesLeft[intersectingRidgeIdx:] # eliminate ridges that are not on shore at all

    return processRidge(edgesLeft, cellEdges, createdEdges, createdQs, vor, shore, hydrology)

def hasRiver(ridgeID: int, vor: Voronoi, hydrology: HydrologyNetwork) -> bool:
    node0: HydroPrimitive = hydrology.node(vor.ridge_points[ridgeID][0])
    node1: HydroPrimitive = hydrology.node(vor.ridge_points[ridgeID][1])
    # a river runs through this ridge if the other node is this node's parent, or this node is the other node's parent
    return node0.parent == node1 or node1.parent == node0

def findIntersectingShoreSegment(p0: Point, p1: Point, shore: ShoreModel) -> typing.Tuple[int, int]:
    power: int = 1
    while True:
        indexes: typing.List[int] = shore.closestNPoints(p0, 4**power)
        for index in indexes:
            if index >= len(shore):
                breakpoint()
                return None
            otherIndex = index+1 if index+1 < len(shore) else 0
            if Math.edgeIntersection(shore[index], shore[otherIndex], p0, p1) is not None:
                return (index, otherIndex)
        power = power + 1

def orderEdges(edgesLeft: typing.List[int], nodeLoc: typing.Tuple[float,float], vor: Voronoi, shore: ShoreModel) -> typing.List[int]:
    # only the first ridge needs to be re-ordered. The others will be
    # chained along, so they will be in the right order
    orderVertices(edgesLeft[0], nodeLoc, vor)
    # set the edges in order by chaining them together
    orderedEdges: typing.List[int] = [ edgesLeft[0] ]
    edgesLeft = edgesLeft[1:]
    while len(edgesLeft) > 0:
        # find the other ridge that has this ridge's second vertex
        nextEdgeIdx = None
        for idx in range(len(edgesLeft)):
            ridgeID: int = edgesLeft[idx]
            # breakpoint()
            if getVertexID1(orderedEdges[-1], vor) == getVertexID0(ridgeID, vor):
                nextEdgeIdx = idx
                break
            elif getVertexID1(orderedEdges[-1], vor) == getVertexID1(ridgeID, vor):
                swapVertices(ridgeID, vor)
                nextEdgeIdx = idx
                break
        if nextEdgeIdx is not None:
            orderedEdges.append(edgesLeft[nextEdgeIdx])
            edgesLeft = edgesLeft[:idx] + edgesLeft[idx+1:]
        else:
            # if there is no edge that links up with this one, then it is impossible to form a chain
            # out of these edges
            return None
    # shift the edges so that the list starts with an edge whose
    # counterclockwise-most vertex is on land
    for idx, ridgeID in enumerate(orderedEdges):
        if shore.isOnLand(getVertex0(ridgeID, vor)):
            orderedEdges = orderedEdges[idx:] + orderedEdges[:idx]
            break
    return orderedEdges

def orderCreatedEdges(edgesLeft: typing.List[int], vor: Voronoi, createdEdges: typing.Dict[int, Edge]) -> None:
    for edgeID in edgesLeft:
        if edgeID not in createdEdges:
            continue
        edge = createdEdges[edgeID]
        # we want the first Q to match the first vertex
        # one of these situations must be true
        # 1) first vertex matches first Q
        # 2) first vertex matches second Q
        #    (first vertex must not be on land)
        # 3) second vertex matches first Q
        # 4) second vertex matches second Q
        try:
            if edge[0].position == getVertex0(edgeID, vor):
                continue
            elif edge[0].position == getVertex1(edgeID, vor):
                swap: Q = edge.Q0
                edge.Q0 = edge.Q1
                edge.Q1 = swap
            elif edge[1].position == getVertex0(edgeID, vor):
                swap: Q = edge.Q0
                edge.Q0 = edge.Q1
                edge.Q1 = swap
            else: # edge[1].position == getVertex1(edgeID, vor):
                continue
        except:
            breakpoint()

# this function ensures that ridge vertices are always in counterclockwise order relative to the node's location
def orderVertices(ridgeID: int, node: typing.Tuple[float, float], vor: Voronoi) -> None:
    vector0:    typing.List[float, float, float] = [getVertex0(ridgeID, vor)[0], getVertex0(ridgeID, vor)[1], 0.0]
    vector1:    typing.List[float, float, float] = [getVertex1(ridgeID, vor)[0], getVertex1(ridgeID, vor)[1], 0.0]
    nodeVector: typing.List[float, float, float] = [node[0], node[1], 0.0]

    vector0 = np.subtract(vector0, nodeVector)
    vector1 = np.subtract(vector1, nodeVector)

    # if the cross product of the two vectors is pointing downward, then the
    # second vector is clockwise to the first one, relative to the node's
    # position
    if np.cross(vector0, vector1)[2] < 0:
        swapVertices(ridgeID, vor)
    return

def swapVertices(ridgeID, vor) -> None:
    tmpVertex: int = vor.ridge_vertices[ridgeID][0]
    vor.ridge_vertices[ridgeID][0] = vor.ridge_vertices[ridgeID][1]
    vor.ridge_vertices[ridgeID][1] = tmpVertex

def getVertexID0(ridgeID: int, vor: Voronoi) -> int:
    return vor.ridge_vertices[ridgeID][0]

def getVertexID1(ridgeID: int, vor: Voronoi) -> int:
    return vor.ridge_vertices[ridgeID][1]

def getVertex0(ridgeID: int, vor: Voronoi) -> Point:
    return vor.vertices[vor.ridge_vertices[ridgeID][0]]

def getVertex1(ridgeID: int, vor: Voronoi) -> Point:
    return vor.vertices[vor.ridge_vertices[ridgeID][1]]