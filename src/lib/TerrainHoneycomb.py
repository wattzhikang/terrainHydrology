import sqlite3

from typing import Tuple, List, Dict

from .Math import Point, polygonArea, pointInPolygon

class Q:
    """Represents a ridge point

    Ridge points are created with a ``position``. The elevation is computed
    later, and bordering nodes are added as discovered.

    :cvar position: Location
    :vartype position: tuple[float,float]
    :cvar nodes: A list of the IDs of each cell that this vertex borders
    :vartype nodes: list[int]
    :cvar elevation: The elevation of this point
    :vartype elevation: float
    """
    def __init__(self, position: Point) -> None:
        self.position = position
        self.nodes = [ ]
        self.elevation = 0
    def addBorderedNode(self, nodeID: int) -> None:
        """When this Q is discovered to border another node, add it here
        
        This is done during the initialization of the
        :py:obj:`TerrainHoneycomb`.
        """
        self.nodes.append(nodeID)

class Edge:
    """An edge of a cell in :py:obj:`TerrainHoneycomb`

    This is a line segment between 2 :py:obj:`Q` s.

    :cvar Q0: One end of the edge
    :vartype Q0: :py:obj:`Q`
    :cvar Q1: The other end of the edge
    :vartype Q1: :py:obj:`Q`
    :cvar hasRiver: True if this edge is transected by a river
    :vartype hasRiver: bool
    :cvar isShore: True if this edge
    :vartype isShore: bool
    :cvar shoreSegment: If this edge is a shore segment, then this is a pair of indices of shore points for the shore segment that this edge intersects or line on. They correspond to :py:meth:`ShoreModel.__getitem__`
    :vartype shoreSegment: Tuple[int,int]
    """
    def __init__(self, Q0: Q, Q1: Q, hasRiver: bool, isShore: bool, shoreSegment: Tuple[int, int]=None) -> None:
        self.Q0 = Q0
        self.Q1 = Q1
        self.hasRiver = hasRiver
        self.isShore = isShore
        self.shoreSegment = shoreSegment
    def __getitem__(self, index: int):
        if index == 0:
            return self.Q0
        elif index == 1:
            return self.Q1
        else:
            raise ValueError('There are only 2 Qs in an Edge')

class TerrainHoneycomb:
    """This class partitions the land into cells around the river nodes

    There is a cell around each river node. Every cell is a polygon. Each
    edge of any polygon is either transected by the flow of a river, forms part
    of the shoreline, or forms a mountainous ridge between two rivers.

    The ID of a cell is the same as the ID of the :py:obj:`HydroPrimitive` that
    it is based around.

    Note that constructor does not construct a terrain honeycomb. That is done
    by :py:func:`TerrainHoneycombFunctions.initializeTerrainHoneycomb`.

    :param resolution: The resolution of the underlying rasters in meters per pixel
    :type resolution: float
    :param edgeLength: The edge length in the simulation
    :type edgeLength: float
    :param binaryFile: A binary file
    :type binaryFile: IO

    .. note::
        If passing in a binary file, you must seek to the appropriate location.

    .. note::
       ``resolution`` should be the same that was passed to the ShoreModel.

    """
    def loadFromDB(self, edgeLength, db: sqlite3.Connection):
        """Loads the terrain honeycomb from a database

        :param resolution: The resolution of the underlying rasters in meters per pixel
        :type resolution: float
        :param edgeLength: The edge length in the simulation
        :type edgeLength: float
        :param db: The database connection
        :type db: sqlite3.Connection
        """
        db.row_factory = sqlite3.Row

        qs = { }
        for qRow in db.execute('SELECT id, elevation, X(loc) AS locX, Y(loc) AS locY FROM Qs'):
            id = qRow['id']
            elevation = qRow['elevation']
            locX = qRow['locX']
            locY = qRow['locY']

            borderNodes = [ ]
            for borderNodeRow in db.execute('SELECT rivernode FROM Cells WHERE q = ?', (id,)):
                borderNodes.append(borderNodeRow['rivernode'])
            
            q = Q((locX, locY))
            q.elevation = elevation
            q.nodes = borderNodes

            qs[id] = q
        self.qs = list(qs.values())
        
        edges = { }
        for edgeRow in db.execute('SELECT id, Q0, Q1, hasRiver, isShore, shore0, shore1 FROM Edges'):
            id = edgeRow['id']
            Q0 = qs[edgeRow['Q0']]
            Q1 = qs[edgeRow['Q1']]
            hasRiver = edgeRow['hasRiver']
            isShore = edgeRow['isShore']
            shore0 = edgeRow['shore0']
            shore1 = edgeRow['shore1']

            edge = Edge(Q0, Q1, hasRiver, isShore, (shore0, shore1))
            edges[id] = edge

        self.cellsEdges: Dict[int, List[Edge]] = { } # cellID -> list of edges
        # get all the edges that border each cell
        for row in db.execute('SELECT edge, node0, node1 FROM EdgeCells'):
            node0 = row['node0']
            node1 = row['node1']
            edgeID = row['edge']

            if node0 not in self.cellsEdges:
                self.cellsEdges[node0] = [ ]
            self.cellsEdges[node0].append(edges[edgeID])
            if node1 not in self.cellsEdges:
                self.cellsEdges[node1] = [ ]
            self.cellsEdges[node1].append(edges[edgeID])
        # since EdgeCells excludes shore segments, we need to add them in
        for row in db.execute('SELECT Edges.id, q1s.rivernode FROM Edges JOIN Cells AS q0s ON q0s.q = Edges.q0 JOIN Cells AS q1s ON q1s.q = Edges.q1 AND q1s.rivernode = q0s.rivernode WHERE isShore = 1'):
            edgeID = row['id']
            nodeID = row['rivernode']

            if nodeID not in self.cellsEdges:
                self.cellsEdges[nodeID] = [ ]
            self.cellsEdges[nodeID].append(edges[edgeID])

        self.cellsDownstreamRidges: Dict[int, Edge] = { }
        # get all the pairs of children and their parents, and get the edges between them
        for row in db.execute('SELECT rivernode, downstreamEdge FROM DownstreamEdges'):
            nodeID = row['rivernode']
            downstreamEdgeID = row['downstreamEdge']

            self.cellsDownstreamRidges[nodeID] = edges[downstreamEdgeID]
    def saveToDB(self, db: sqlite3.Connection):
        """Saves the terrain honeycomb to a database

        :param db: The database connection
        :type db: sqlite3.Connection
        """
        #compile list of all primitives
        createdEdges: Dict[int, Edge] = { }
        for cellID in range(self.numCells()):
            for edge in self.cellEdges(cellID):
                if id(edge) not in createdEdges:
                    createdEdges[id(edge)] = edge

        with db:
            db.execute("DELETE FROM Qs")
            db.execute("DELETE FROM Cells")
            db.execute("DELETE FROM Edges")

            # write Qs
            db.executemany("INSERT INTO Qs (id, elevation, loc) VALUES (?, ?, MakePoint(?, ?, 347895))", [(id(q), q.elevation, float(q.position[0]), float(q.position[1])) for q in self.qs])

            # write cells using the edges, that way we can save the order of the Qs for a good polygon
            for cellID, edges in self.cellsEdges.items():
                # we have to put the Qs in order, so we can make a good polygon
                # the edges are in order, and they are all chained together, so we can just use the order of the edges
                # but the Qs of the edges are not in order, so we will have to figure out which Q is first for each edge
                # the first Q of an edge is the Q that is not in the next edge, but _is_ in the previous edge
                qs = [ edges[0].Q0 if edges[0].Q1 == edges[1].Q0 or edges[0].Q1 == edges[1].Q1 else edges[0].Q1 ]
                for edgeIdx, edge in enumerate(edges[1:], start=1):
                    # the first Q of this edge is the Q that is in the previous edge
                    if edge.Q0 == edges[edgeIdx-1].Q0 or edge.Q0 == edges[edgeIdx-1].Q1:
                        qs.append(edge.Q0)
                    else:
                        qs.append(edge.Q1)

                # now we have the Qs in order, so we can make a polygon
                db.executemany("INSERT INTO Cells (rivernode, polygonOrder, q) VALUES (?, ?, ?)", [(cellID, idx, id(q)) for idx, q in enumerate(qs)])

            # write edges
            db.executemany("INSERT INTO Edges (id, q0, q1, hasRiver, isShore, shore0, shore1) VALUES (?, ?, ?, ?, ?, ?, ?)", [(saveID, id(edge.Q0), id(edge.Q1), edge.hasRiver, edge.isShore, edge.shoreSegment[0] if edge.isShore else None, edge.shoreSegment[1] if edge.isShore else None) for saveID, edge in createdEdges.items()])
    def numCells(self) -> int:
        """Gets the number of cells in the terrain

        :return: The number of cells
        :rtype: int
        """
        # the number of cells is the number of entries in self.cellsEdges
        return len(self.cellsEdges)
    def cellVertices(self, nodeID: int) -> List[Point]:
        """Gets the coordinates of the Qs that define the shape of the node's cell

        .. todo:: This method does not consistently give vertices in
            counterclockwise order. It ought to.

        :param nodeID: The ID of the node whose shape you wish to query
        :type nodeID: int
        :return: The coordinates of the cell's shape
        :rtype: Math.Point
        """

        # we have to put the Qs in order, so we can make a good polygon
        # the edges are in order, and they are all chained together, so we can just use the order of the edges
        # but the Qs of the edges are not in order, so we will have to figure out which Q is first for each edge
        # the first Q of an edge is the Q that is not in the next edge, but _is_ in the previous edge
        edges = self.cellsEdges[nodeID]
        qs = [ edges[0].Q0 if edges[0].Q1 == edges[1].Q0 or edges[0].Q1 == edges[1].Q1 else edges[0].Q1 ]
        for edgeIdx, edge in enumerate(edges[1:], start=1):
            # the first Q of this edge is the Q that is in the previous edge
            if edge.Q0 == edges[edgeIdx-1].Q0 or edge.Q0 == edges[edgeIdx-1].Q1:
                qs.append(edge.Q0)
            else:
                qs.append(edge.Q1)

        # now get the positions of the Qs with a list comprehension
        return [q.position for q in qs]
    def cellArea(self, cellID: int) -> float:
        """Calculates the area of a cell

        This method derives the area based on the cell's shape. It is accurate.

        :param node: The node that you wish to query
        :type node: HydroPrimitive
        """
        return polygonArea(
            self.cellVertices(cellID)
        )
    def cellQs(self, node: int) -> List[Q]:
        """Returns all the Qs binding the cell that corresponds to the given node

        :param node: The node you wish to query
        :type node: int
        :return: List of Q instances
        :rtype: list[Q]
        """
        ridges = self.cellsEdges[node]
        return [ridge.Q0 for ridge in ridges]
    def allQs(self) -> List[Q]:
        """Simply returns all Qs of the land

        Note: the index of a Q in this list does not correspond to anything significant

        :return: All Qs of the land
        :rtype: list[Q]
        """
        return self.qs.copy()
    def boundingBox(self, n: int) -> Tuple[float,float,float,float]:
        """Returns the measurements for a bounding box that could contain a cell

        This method had a rather specific application. You'll probably never use it.

        :param n: The ID of the cell you wish to get a bounding box for
        :type n: int
        :return: A tuple indicating the lower X, upper X, lower Y, and upper Y, respectively, in meters
        :rtype: tuple[float,float,float,float]
        """
        vertices = self.cellVertices(n) # vertices binding the region
        if len(vertices) < 1:
            # If this cell has a malformed shape, don't
            return (None, None, None, None)
        xllim = min([v[0] for v in vertices])
        xulim = max([v[0] for v in vertices])
        yllim = min([v[1] for v in vertices])
        yulim = max([v[1] for v in vertices])
        return (xllim, xulim, yllim, yulim)
    def isInCell(self, p: Point, n: int) -> bool:
        """Determines if a point is within a given cell

        :param p: The point you wish to test
        :type p: Math.Point
        :param n: The ID of the cell you wish to test
        :type n: int
        :return: True of point ``p`` is in the cell that corresponds to ``n``
        :rtype: bool
        """
        return pointInPolygon(p, self.cellVertices(n))
    def cellRidges(self, n: int) -> List[Edge]:
        """Returns cell edges that are not transected by a river, and are not part of the shoreline

        :param n: The ID of the cell that you wish to query
        :type n: int
        :return: A list of tuples, each contain exactly 1 or 2 Qs.
        :rtype: list[tuple]
        """
        return [edge for edge in self.cellsEdges[n] if not (edge.hasRiver or edge.isShore)]
    def cellEdges(self, cellID: int) -> List[Edge]:
        """Gets all the edges of a cell
        
        This includes edges that are transected by rivers or form part of the
        shoreline.
        
        :param cellID: The ID of the cell that you wish to query
        :type param: int
        :return: A list of all the edges that bound the cell
        :rtype: list[Edge]
        """
        return self.cellsEdges[cellID]
    def cellOutflowRidge(self, n: int) -> Edge:
        """Returns the ridge through which the river flows out of the cell

        .. note::
           A ridge will only be returned if the Hydrology node that this cell
           is based around has a parent. Otherwise, ``None`` will be returned.

        :return: The IDs of the vertices that define the outflow ridge, unless this cell is the mouth of a river
        :rtype: Edge | None
        """
        return self.cellsDownstreamRidges[n] if n in self.cellsDownstreamRidges else None