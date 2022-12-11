import typing

import numpy as np
from scipy.spatial import Voronoi
import Math

from DataModel import Point, ShoreModel, TerrainHoneycomb, Q, Edge, HydroPrimitive, HydrologyNetwork, RasterData

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
    :return: The elevation of the ridge
    :rtype: float
    """
    if len(q.nodes) < 2:
        # if this Q only borders 1 node, then it's directly on the shore, and should be 0
        return 0
    nodes = [hydrology.node(n) for n in q.nodes]
    maxElevation = max([node.elevation for node in nodes])
    d = np.linalg.norm(np.array(q.position) - np.array(nodes[0].position))
    slope = terrainSlopeRate * terrainSlope[q.position[0],q.position[1]] / 255
    return maxElevation + d * slope

def initializeTerrainHoneycomb(shore: ShoreModel, hydrology: HydrologyNetwork) -> TerrainHoneycomb:
    """Based on a hydrology network and a shoreline, determines the correct TerrainHoneycomb
    
    :param shore: The shoreline
    :type shore: DataModel.ShoreModel
    :param hydrology: The hydrology network
    :type hydrology: DataModel.HydrologyNetwork
    :return: A correctly-configured Terrain Honeycomb
    :rtype: DataModel.TerrainHoneycomb
    """
    cells = TerrainHoneycomb()

    points = [node.position for node in hydrology.allNodes()]

    # Add corners so that the entire area is covered
    points.append((-shore.realShape[0],-shore.realShape[1]))
    points.append((-shore.realShape[0],shore.realShape[1]))
    points.append((shore.realShape[0],shore.realShape[1]))
    points.append((shore.realShape[0],-shore.realShape[1]))

    vor = Voronoi(points,qhull_options='Qbb Qc Qz Qx')
    vor.vertices = [(vertex[0],vertex[1]) for vertex in vor.vertices] # convert to list for easy comprehension

    # This is for reverse lookup of ridge_points. Given a point (node ID),
    # it retrieves the ridges that border it
    point_ridges: typing.Dict[int, typing.List[int]] = ridgesToPoints(vor)

    createdQs: typing.Dict[int, Q] = { }
    shoreQs: typing.List[Q] = [ ]
    createdEdges: typing.Dict[int, Edge] = { }

    cellsEdges: typing.Dict[int, typing.List[Edge]] = { }
    cellsDownstreamEdges: typing.Dict[int, Edge] = { }
    for node in hydrology.allNodes():
        # order the cell edges in counterclockwise order
        point_ridges[node.id] = orderEdges(point_ridges[node.id], node.position, vor, shore)
        orderCreatedEdges(point_ridges[node.id], vor, createdEdges)

        # then we have to organize and set up all the edges of the cell
        cellsEdges[node.id] = processRidge(point_ridges[node.id], [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

        # find the downstream edge
        for ridgeID in point_ridges[node.id]:
            otherNodeID = vor.ridge_points[ridgeID][vor.ridge_points[ridgeID] != node.id][0]
            if otherNodeID >= len(hydrology):
                # This is one of the corners, and not a real node
                continue
            otherNode = hydrology.node(otherNodeID)
            if node.parent is not None and otherNode.id == node.parent.id:
                # This node is the other node's parent. Therefore this ridge is the downstream ridge of this node
                cellsDownstreamEdges[node.id] = createdEdges[ridgeID]
                break

        # Since these edges are chained in a loop, all of the Qs will be covered
        for edge in cellsEdges[node.id]:
            edge.Q0.addBorderedNode(node.id)

    cells.vertices = vor.vertices
    cells.regions = vor.regions
    cells.point_region = vor.point_region
    cells.region_point = {vor.point_region[i]: i for i in range(len(vor.point_region))}

    cells.shore = shore
    cells.hydrology = hydrology

    cells.qs = list(createdQs.values()) + shoreQs
    cells.cellsEdges = cellsEdges
    cells.cellsDownstreamRidges = cellsDownstreamEdges

    return cells

# This is for reverse lookup of ridge_points. Given a point (node ID),
# it retrieves the ridges that border it
def ridgesToPoints(vor: Voronoi) -> typing.Dict[int, typing.List[int]]:
    """This creates a dictionary that is simply the reverse lookup of Voronoi.ridge_points
    
    Given a point (node ID), it retrieves indices of the ridges that border it.

    This is for internal use.

    :param vor: The Voronoi partition of the hydrology network
    :type vor: scipy.spatial.Voronoi
    :return: A dictionary that can be used to retrieve the indices of ridges that border a point
    :rtype: dict[int, list[int]]
    """
    point_ridges = { }
    for ridgeID, points in enumerate(vor.ridge_points):
        for point in points: # there should only be 2 of these
            if point in point_ridges:
                point_ridges[point].append(ridgeID)
            else:
                point_ridges[point] = [ ridgeID ]
    return point_ridges

def processRidge(edgesLeft: typing.List[int], cellEdges: typing.List[Edge], createdEdges: typing.Dict[int, Edge], createdQs: typing.Dict[int, Q], shoreQs: typing.List[Q], vor: Voronoi, shore: ShoreModel, hydrology: HydrologyNetwork) -> typing.List[Edge]:
    """This function will process a normal ridge that is entirely located on land and may or may not be transected by a river.
    
    If this ridge intersects the shore at all, it immediately hands over
    control to :py:func:`terminateRidgeAndStartShore()`. This function does not
    assume that there is a previously-processed ridge.

    :param edgesLeft: The (Voronoi) indices of edges that haven't been processed yet
    :type edgesLeft: list[int]
    :param cellEdges: The edges that have been processed into true DataModel.Edge objects
    :type cellEdges: list[DataModel.Edge]
    :param createdEdges: A dict of all the edges that have been created so far. This is necessary because many, if not most, edges are shared between cells. The index will correspond to the Voronoi index of the ridge it corresponds to.
    :type createdEdges: dict[int, Edge]
    :param createdQs: A dict of all the Qs that have been created so far. This is necessary because many, if not most, Qs are shared between cells. The index will correspond to the Voronoi index of the ridge point it corresponds to.
    :type createdQs: dict[int, Q]
    :param shoreQs: A list of all Qs that are not shared between cells, that is, Qs that are on the shore.
    :type shoreQs: list[Q]
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :param shore: The shoreline
    :type shore: DataModel.ShoreModel
    :param hydrology: The hydrology network created from the shoreline
    :type hydrology: DataModel.HydrologyNetwork
    :return: The list of the cell's edges
    :rtype: list[Edge]
    """
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

            newRidge: Edge = Edge(Q0, Q1, hasRiver=hasRiver(ridgeID, vor, hydrology), isShore=False, shoreSegment=shoreSegment)
            createdEdges[edgesLeft[0]] = newRidge
        cellEdges.append(newRidge)
        edgesLeft = edgesLeft[1:]
        return processRidge(edgesLeft, cellEdges, createdEdges, createdQs, shoreQs, vor, shore, hydrology)
    else:
        # we know that the first vertex is on land, so if the second vertex
        # isn't, then we know that this edge must intersect the shore somewhere
        return terminateRidgeAndStartShore(edgesLeft, cellEdges, createdEdges, createdQs, shoreQs, vor, shore, hydrology)

def terminateRidgeAndStartShore(edgesLeft: typing.List[int], cellEdges: typing.List[Edge], createdEdges: typing.Dict[int, Edge], createdQs: typing.Dict[int, Q], shoreQs: typing.List[Q], vor: Voronoi, shore: ShoreModel, hydrology: HydrologyNetwork) -> typing.List[Edge]:
    """The current ridge intersects the shoreline. Terminate it at the shore, and then start processing the shoreline
    
    This function does not assume that there is a previously-processed edge

    :param edgesLeft: The (Voronoi) indices of edges that haven't been processed yet
    :type edgesLeft: list[int]
    :param cellEdges: The edges that have been processed into true DataModel.Edge objects
    :type cellEdges: list[DataModel.Edge]
    :param createdEdges: A dict of all the edges that have been created so far. This is necessary because many, if not most, edges are shared between cells. The index will correspond to the Voronoi index of the ridge it corresponds to.
    :type createdEdges: dict[int, Edge]
    :param createdQs: A dict of all the Qs that have been created so far. This is necessary because many, if not most, Qs are shared between cells. The index will correspond to the Voronoi index of the ridge point it corresponds to.
    :type createdQs: dict[int, Q]
    :param shoreQs: A list of all Qs that are not shared between cells, that is, Qs that are on the shore.
    :type shoreQs: list[Q]
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :param shore: The shoreline
    :type shore: DataModel.ShoreModel
    :param hydrology: The hydrology network created from the shoreline
    :type hydrology: DataModel.HydrologyNetwork
    :return: The list of the cell's edges
    :rtype: list[Edge]
    """
    terminatedEdge: Edge = None
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
        intersection: Point = Math.edgeIntersection(getVertex0(edgesLeft[0], vor), getVertex1(edgesLeft[0], vor), shore[shoreSegment[0]], shore[shoreSegment[1]])

        Q1: Q = Q(intersection)
        shoreQs.append(Q1)

        terminatedEdge = Edge(Q0, Q1, hasRiver=hasRiver(edgesLeft[0], vor, hydrology), isShore=False, shoreSegment=shoreSegment)
        createdEdges[edgesLeft[0]] = terminatedEdge

    cellEdges.append(terminatedEdge)
    edgesLeft = edgesLeft[1:]
    return processShoreSegment(terminatedEdge.shoreSegment, edgesLeft, cellEdges, createdEdges, createdQs, shoreQs, vor, shore, hydrology)

def processShoreSegment(currentSegment: typing.Tuple[int, int], edgesLeft: typing.List[int], cellEdges: typing.List[Edge], createdEdges: typing.Dict[int, Edge], createdQs: typing.Dict[int, Q], shoreQs: typing.List[Q], vor: Voronoi, shore: ShoreModel, hydrology: HydrologyNetwork) -> typing.List[Edge]:
    """After a ridge has been terminated at the coast, this function can process the coastline until it finds an intersection with one of the other ridges in the cell
    
    This function assumes that at least one ridge has been processed so far.

    :param currentSegment: The shore segment that this function must process. This is a segment in :py:obj:`DataModel.ShoreModel`
    :type currentSegment: tuple[int, int]
    :param edgesLeft: The (Voronoi) indices of edges that haven't been processed yet
    :type edgesLeft: list[int]
    :param cellEdges: The edges that have been processed into true DataModel.Edge objects
    :type cellEdges: list[DataModel.Edge]
    :param createdEdges: A dict of all the edges that have been created so far. This is necessary because many, if not most, edges are shared between cells. The index will correspond to the Voronoi index of the ridge it corresponds to.
    :type createdEdges: dict[int, Edge]
    :param createdQs: A dict of all the Qs that have been created so far. This is necessary because many, if not most, Qs are shared between cells. The index will correspond to the Voronoi index of the ridge point it corresponds to.
    :type createdQs: dict[int, Q]
    :param shoreQs: A list of all Qs that are not shared between cells, that is, Qs that are on the shore.
    :type shoreQs: list[Q]
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :param shore: The shoreline
    :type shore: DataModel.ShoreModel
    :param hydrology: The hydrology network created from the shoreline
    :type hydrology: DataModel.HydrologyNetwork
    :return: The list of the cell's edges
    :rtype: list[Edge]
    """
    Q0: Q = cellEdges[-1][1]

    # does the current shore segment intersect with any of the edges that haven't been processed yet?
    for otherRidgeID in edgesLeft:
        if Math.edgeIntersection(getVertex0(otherRidgeID, vor), getVertex1(otherRidgeID, vor), shore[currentSegment[0]], shore[currentSegment[1]]) is not None:
            return terminateShoreAndStartRidge(otherRidgeID, currentSegment, edgesLeft, cellEdges, createdEdges, createdQs, shoreQs, vor, shore, hydrology)
    
    # This Q does not exist anywhere but in this cell, so it cannot have been created previously
    Q1: Q = Q(shore[currentSegment[1]])
    shoreQs.append(Q1)

    newEdge: Edge = Edge(Q0, Q1, hasRiver=False, isShore=True, shoreSegment=currentSegment)
    cellEdges.append(newEdge)

    nextIdx = currentSegment[1]+1 if currentSegment[1]+1 < len(shore) else 0
    currentSegment = (currentSegment[1], nextIdx)

    return processShoreSegment(currentSegment, edgesLeft, cellEdges, createdEdges, createdQs, shoreQs, vor, shore, hydrology)

def terminateShoreAndStartRidge(intersectingRidgeID: int, currentSegment: typing.Tuple[int, int], edgesLeft: typing.List[int], cellEdges: typing.List[Edge], createdEdges: typing.Dict[int, Edge], createdQs: typing.Dict[int, Q], shoreQs: typing.List[Q], vor: Voronoi, shore: ShoreModel, hydrology: HydrologyNetwork) -> typing.List[Edge]:
    """This function terminates the shore segment.
    
    It does _not_ process the following ridge segment, as
    :py:func:`processRidge()` can simply observe that this ridge has been
    processed, and so it can just use the second Q of this edge to start the
    next one.

    :param intersectingRidgeID: The voronoi edge that the current shore segment intersects
    :type intersectingRidgeID: int
    :param currentSegment: The shore segment that this function must process. This is a segment in :py:obj:`DataModel.ShoreModel`
    :type currentSegment: tuple[int, int]
    :param edgesLeft: The (Voronoi) indices of edges that haven't been processed yet
    :type edgesLeft: list[int]
    :param cellEdges: The edges that have been processed into true DataModel.Edge objects
    :type cellEdges: list[DataModel.Edge]
    :param createdEdges: A dict of all the edges that have been created so far. This is necessary because many, if not most, edges are shared between cells. The index will correspond to the Voronoi index of the ridge it corresponds to.
    :type createdEdges: dict[int, Edge]
    :param createdQs: A dict of all the Qs that have been created so far. This is necessary because many, if not most, Qs are shared between cells. The index will correspond to the Voronoi index of the ridge point it corresponds to.
    :type createdQs: dict[int, Q]
    :param shoreQs: A list of all Qs that are not shared between cells, that is, Qs that are on the shore.
    :type shoreQs: list[Q]
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :param shore: The shoreline
    :type shore: DataModel.ShoreModel
    :param hydrology: The hydrology network created from the shoreline
    :type hydrology: DataModel.HydrologyNetwork
    :return: The list of the cell's edges
    :rtype: list[Edge]
    """
    Q0: Q = cellEdges[-1][1]
    Q1: Q = None
    # if the intersecting ridge has already been created, then all we need to do is meet it
    if intersectingRidgeID in createdEdges:
        Q1 = createdEdges[intersectingRidgeID].Q0
    else:
        intersection: typing.Tuple[float, float] = Math.edgeIntersection(getVertex0(intersectingRidgeID, vor), getVertex1(intersectingRidgeID, vor), shore[currentSegment[0]], shore[currentSegment[1]])
        Q1: Q = Q(intersection)
        shoreQs.append(Q1)

    newEdge: Edge = Edge(Q0, Q1, hasRiver=False, isShore=True, shoreSegment=currentSegment)
    cellEdges.append(newEdge)

    intersectingRidgeIdx = edgesLeft.index(intersectingRidgeID)
    edgesLeft = edgesLeft[intersectingRidgeIdx:] # eliminate ridges that are not on shore at all

    return processRidge(edgesLeft, cellEdges, createdEdges, createdQs, shoreQs, vor, shore, hydrology)

def hasRiver(ridgeID: int, vor: Voronoi, hydrology: HydrologyNetwork) -> bool:
    """Determines whether or not a river transects this edge
    
    :param ridgeID: The (Voronoi) ridge ID
    :type ridgeID: int
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :param hydrology: The hydrology network created from the shoreline
    :type hydrology: DataModel.HydrologyNetwork
    :return: True if a river transects this edge
    :rtype: bool
    """
    node0: HydroPrimitive = hydrology.node(vor.ridge_points[ridgeID][0])
    node1: HydroPrimitive = hydrology.node(vor.ridge_points[ridgeID][1])
    # a river runs through this ridge if the other node is this node's parent, or this node is the other node's parent
    return node0.parent == node1 or node1.parent == node0

def findIntersectingShoreSegment(p0: Point, p1: Point, shore: ShoreModel) -> typing.Tuple[int, int]:
    """Tries to find a shore segment that intersects with a line segment
    
    :param p0: The first point of the input line segment
    :type p0: Math.Point
    :param p1: The second point of the input line segment
    :type p1: Math.Point
    :return: A shore segment if there is one that intersects with the input line segment, or None
    :rtype: tuple[int, int] | None
    """
    power: int = 1
    while True:
        indexes: typing.List[int] = shore.closestNPoints(p0, 4**power)
        for index in indexes:
            if index >= len(shore):
                return None
            otherIndex = index+1 if index+1 < len(shore) else 0
            if Math.edgeIntersection(shore[index], shore[otherIndex], p0, p1) is not None:
                return (index, otherIndex)
        power = power + 1

def orderEdges(edgesLeft: typing.List[int], nodeLoc: typing.Tuple[float,float], vor: Voronoi, shore: ShoreModel) -> typing.List[int]:
    """Orders edges of a cell in clockwise order, and so that the first edge is on land.
    
    This function will arrange the edges, and their internal vertices, so that they are all in counterclockwise order.

    It also shifts the list so that the first edge in the list has its first vertex on land.

    :param edgesLeft: The edges to order. This should be a complete list of all the edges of a single cell.
    :type edgesLeft: list[int]
    :param nodeLoc: The location of the node, but theoretically could be any point inside the cell. The edges will be counterclockwise around this point.
    :type nodeLoc: tuple[float, float]
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :param shore: The shoreline
    :type shore: DataModel.ShoreModel
    :return: The list of edge IDs, in counterclockwise order
    :rtype: list[int]
    """
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
    """Order edges that have already been created.
    
    This has to be done before :py:func:`processRidge()` is called.

    :param edgesLeft: The edges to order. This should be a complete list of all the edges of a single cell.
    :type edgesLeft: list[int]
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :param createdEdges: A dict of all the edges that have been created so far. The index will correspond to the Voronoi index of the ridge it corresponds to.
    :type createdEdges: dict[int, Edge]
    """
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
    """This function ensures that ridge vertices are always in counterclockwise order relative to the node's location
    
    This is typically supposed to be called by :py:func:`orderEdges()`.

    :param ridgeID: The (Voronoi) ID of the ridge that must be sorted.
    :type ridgeID: int
    :param node: The location of the node. This can really be any location in the cell, but the node's location is conveniently accessible
    :type node: tuple[float, float]
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    """
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

def swapVertices(ridgeID: int, vor: Voronoi) -> None:
    """Swaps 2 vertex IDs for a ridge in the Voronoi dictionaries.
    
    This is mostly just shorthand. I got tired of writing these lines over and over.

    Note that this does mutate the Voronoi's dictionaries.
    
    :param ridgeID: The ID of the ridge. Its vertices will be swapped.
    :type ridgeID: int
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    """
    tmpVertex: int = vor.ridge_vertices[ridgeID][0]
    vor.ridge_vertices[ridgeID][0] = vor.ridge_vertices[ridgeID][1]
    vor.ridge_vertices[ridgeID][1] = tmpVertex

def getVertexID0(ridgeID: int, vor: Voronoi) -> int:
    """Gets the first vertex ID of a ridge. This is just shorthand. I got tired of writing this line over and over.
    
    :param ridgeID: The ID of the ridge to query
    :type ridgeID: int
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :return: the first vertex ID of a ridge
    :rtype: int
    """
    return vor.ridge_vertices[ridgeID][0]

def getVertexID1(ridgeID: int, vor: Voronoi) -> int:
    """Gets the second vertex ID of a ridge. This is just shorthand. I got tired of writing this line over and over.
    
    :param ridgeID: The ID of the ridge to query
    :type ridgeID: int
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :return: the second vertex ID of a ridge
    :rtype: int
    """
    return vor.ridge_vertices[ridgeID][1]

def getVertex0(ridgeID: int, vor: Voronoi) -> Point:
    """Gets the first vertex location of a ridge. This is just shorthand. I got tired of writing this line over and over.
    
    :param ridgeID: The ID of the ridge to query
    :type ridgeID: int
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :return: the first vertex location of a ridge
    :rtype: Math.Point
    """
    return vor.vertices[vor.ridge_vertices[ridgeID][0]]

def getVertex1(ridgeID: int, vor: Voronoi) -> Point:
    """Gets the second vertex location of a ridge. This is just shorthand. I got tired of writing this line over and over.
    
    :param ridgeID: The ID of the ridge to query
    :type ridgeID: int
    :param vor: The Voronoi partition for the hydrology network
    :type vor: Scipy.Voronoi
    :return: the second vertex location of a ridge
    :rtype: Math.Point
    """
    return vor.vertices[vor.ridge_vertices[ridgeID][1]]