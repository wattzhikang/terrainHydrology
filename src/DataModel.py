from re import I
import cv2 as cv
from networkx.algorithms.operators import binary
import numpy as np
import networkx as nx
from scipy.spatial import cKDTree
from scipy.spatial import Voronoi
from poisson import PoissonGenerator
from PIL import Image
import shapely.geometry as geom
import struct
import math
from tqdm import trange
import datetime
import shapefile
import abc
import sqlite3

import typing
from typing import List
from typing import Dict

import Math
from Math import Point

def toImageCoordinates(loc: typing.Tuple[float,float], imgSize: typing.Tuple[float,float], resolution: float) -> typing.Tuple[float,float]:
    x = loc[0]
    x /= resolution
    x += imgSize[0] * 0.5

    y = loc[1]
    y /= resolution
    y = imgSize[1] * 0.5 - y

    return (x,y)

def fromImageCoordinates(loc: typing.Tuple[float,float], imgSize: typing.Tuple[float,float], resolution: float) -> typing.Tuple[float,float]:
    x = loc[0]
    x -= imgSize[0] * 0.5
    x *= resolution

    y = loc[1]
    y = imgSize[1] * 0.5 - y
    y *= resolution

    return (x,y)

class RasterData:
    """A simple abstraction of raster data based on an image.

    Simply input a path to an image and a resolution, and this class will
    allow you to access the data for each point on the surface.

    :param inputFileName: This should be a path to the image
    :type inputFileName: str
    :param resolution: The resolution of the input image in meters per pixel
    :type resolution: float
    
    The image should be
    readable by PIL. The image should represent raster data that covers
    the entire area that will be accessed by the algorithm. The values
    are represented by the grayscale value of each pixel. The image's
    actual color model does not model, as it will be converted to
    grayscale in the constructor.
    """
    def __init__(self, inputFileName: str, resolution: float):
        self.raster = Image.open(inputFileName)
        self.xSize = self.raster.size[0]
        self.ySize = self.raster.size[1]
        self.raster = self.raster.convert('L')
        self.raster = self.raster.load()
        self.resolution = resolution
    def __getitem__(self, loc: typing.Tuple[float,float]) -> float:
        """Gets the value for a particular location

        :param loc: The location to interrogate
        :type loc: tuple[float,float]
        :return: The value of the data at loc
        :rtype: float
        """
        loc = toImageCoordinates(loc, (self.xSize,self.ySize), self.resolution)

        return self.raster[int(loc[0]), int(loc[1])]
    def toBinary(self):
        binary = None
        for y in range(self.ySize):
            # print(f'Working on row {y}')
            row = None
            for x in range(self.xSize):
                if row is not None:
                    row = row + struct.pack('!f', self.raster[x,y])
                else:
                    row = struct.pack('!f', self.raster[x,y])
            if binary is not None:
                binary = binary + row
            else:
                binary = row
        return binary

class ShoreModel(metaclass=abc.ABCMeta):
    """This class represents the shoreline of the land area.

    This is an abstract class; some logic is common to all ShoreModel
    implementations, but others must be implemented separately.

    Fundamentally, a shoreline is a list of points that make a polygon. This
    polygon represents the land area.

    :cvar realShape: The spatial dimensions of the area that the gamma image covers, in meters
    :vartype realShape: numpy.ndarray[float,float]

    .. note::
    
       Shape variables are all in order y,x. (I think? This needs to be updated.)
    """
    def closestNPoints(self, loc: Point, n: int) -> typing.List[int]:
        """Gets the closest N shoreline points to a given point

        :param loc: The location to test
        :type loc: `Math.Point`
        :param n: The number of points to retrieve
        :type n: int
        :return: The closest N points to loc
        :rtype: List[Math.Point]
        """
        # ensure that the result is un-squeezed
        n = n if n > 1 else [n]
        distances, indices = self.pointTree.query(loc, k=n)
        return indices
    @abc.abstractmethod
    def distanceToShore(self, loc: Point) -> float:
        """Gets the distance between a point and the shore

        The distance is in meters.

        :param loc: The location to test
        :type loc: `Math.Point`
        :return: The distance between `loc` and the shore in meters
        :rtype: float
        """
        raise NotImplementedError
    def isOnLand(self, loc: Point) -> bool:
        """Determines whether or not a point is on land

        :param loc: The location to test
        :type loc: `Math.Point`
        :return: True if the point is on land, False if otherwise
        :rtype: bool
        """
        return self.distanceToShore(loc) >= 0
    @abc.abstractmethod
    def __getitem__(self, index: int):
        """Gets a point on the shore by index

        :param index: The index
        :type index: int
        :return: The index-th coordinate of the shoreline
        :rtype: `Math.Point`
        """
        raise NotImplementedError
    def __len__(self):
        """The number of points that make up the shore

        :return: The number of points that make up the shore
        :rtype: int
        """
        return len(self.contour)
    def saveToDB(self, db: sqlite3.Connection) -> None:
        """Writes the shoreline to a database

        NOTE: No matter the provenance of a shoreline, whether from an image
        or shapefile, it will be written to the database as a list of points
        in the project coordinate system. So regardless of the source, a
        shoreline should be loaded from the database as a Shapefile shoreline.

        :param db: The database to write to
        :type db: sqlite3.Connection
        """
        with db:
            db.execute('DELETE FROM Shoreline')
            # executemany() opens and closes transactions itself, so we don't need to
            db.executemany("INSERT INTO Shoreline VALUES (?, MakePoint(?, ?, 347895))", [(pointIdx, self[pointIdx][0], self[pointIdx][1]) for pointIdx in range(len(self))])
    def loadFromDB(self, db: sqlite3.Connection) -> None:
        """Loads the shoreline from a database

        :param db: The database to load from
        :type db: sqlite3.Connection
        """
        db.row_factory = sqlite3.Row
        cursor = db.execute('SELECT X(loc) AS locX, Y(loc) AS locY FROM Shoreline ORDER BY id')
        self.contour = [(row['locX'], row['locY']) for row in cursor]
        self.contour = np.array(self.contour, dtype=np.float32)

        self.pointTree = cKDTree(self.contour)

        # This will be a problem if the original object was a ShoreModelImage, but we're going to axe that class anyway
        self.realShape = (max([p[0] for p in self.contour])-min([p[0] for p in self.contour]),max([p[1] for p in self.contour])-min([p[1] for p in self.contour]))

class ShoreModelImage(ShoreModel):
    """This class creates a shoreline based on a black-and-white image

    If you pass in gammaFileName and no binaryFile, this object will be
    initialized based on an image. If you pass in binaryFile with no
    gammaFileImage, this object will be reconstituted from a binary file.

    :param resolution: The resolution of the input image in meters per pixel
    :type resolution: float
    :param gammaFileName: The path to the image that defines the shoreline
    :type gammaFileName: str
    :param binaryFile: A binary file
    :type binaryFile: typing.IO

    .. note::
        If passing in a binary file, you must seek to the appropriate location.
    """
    def __init__(self, resolution: float, gammaFileName: str=None) -> None:
        """Constructor
        """

        self.resolution = resolution

        if gammaFileName is None:
            return

        self.img = cv.imread(gammaFileName)
        
        self.imgray = cv.cvtColor(self.img, cv.COLOR_BGR2GRAY) # a black-and-white version of the input image
        self.rasterShape = self.imgray.shape
        self.realShape = (self.imgray.shape[0] * self.resolution, self.imgray.shape[1] * self.resolution)
        ret, thresh = cv.threshold(self.imgray, 127, 255, 0)
        contours, hierarchy = cv.findContours(thresh, cv.RETR_LIST, cv.CHAIN_APPROX_NONE)
        test = cv.cvtColor(thresh, cv.COLOR_GRAY2BGR) # not sure what this line does or why it exists
        if len(contours) > 1:
            print('WARNING: Multiple contours identified. The program may not have correctly')
            print('identified the land.')
        self.contour = contours[0]
        self.contour=self.contour.reshape(-1,2)
        self.contour=np.flip(self.contour,1)

        realPoints = [fromImageCoordinates((loc[1],loc[0]), self.imgray.shape, resolution) for loc in self.contour]
        self.pointTree = cKDTree(realPoints)
        
        self.imgOutline = self.img.copy()
        cv.drawContours(self.imgOutline, contours, -1, (0,255,0), 2)
        
        # TODO raise exception if dimensions not square
        # TODO raise exception if multiple contours
    def distanceToShore(self, loc: Point) -> float:
        loc = toImageCoordinates(loc, self.imgray.shape, self.resolution)

        #    for some reason this method is      y, x
        return cv.pointPolygonTest(self.contour,(loc[1],loc[0]),True) * self.resolution
    def __getitem__(self, index: int):
        # openCV stores contour points as (y,x), so we need to flip them
        # we also need to convert from image coordinates to project coordinates
        return fromImageCoordinates((self.contour[index][1],self.contour[index][0]), self.imgray.shape, self.resolution)

class ShoreModelShapefile(ShoreModel):
    def __init__(self, inputFileName: str=None) -> None:
        if inputFileName is None:
            return

        with shapefile.Reader(inputFileName, shapeType=5) as shp:
            self.contour = shp.shape(0).points[1:] # the first and last points are identical, so remove them
            self.contour.reverse() # pyshp stores shapes in clockwise order, but we want counterclockwise
            self.contour = np.array(self.contour, dtype=np.dtype(np.float32))

        self.realShape = (max([p[0] for p in self.contour])-min([p[0] for p in self.contour]),max([p[1] for p in self.contour])-min([p[1] for p in self.contour]))
        self.pointTree = cKDTree(self.contour)
    def distanceToShore(self, loc: Point) -> bool:
        # in this class, the contour is stored as x,y, so we put the test points in as x,y
        return cv.pointPolygonTest(self.contour, (loc[0],loc[1]), True)
    def __getitem__(self, index: int):
        # no need to flip the points, since they're stored as x,y
        # no need to convert from a coordinate system, since shapefiles are expected to be in the same coordinate system as the project
        return self.contour[index]

class HydroPrimitive:
    """Represents a certain stretch of river

    A HydroPrimitive is instantiated with the ``id``, ``position``,
    ``elevation``, ``priority``, and ``parent`` attributes, as
    applicable. The other attributes are computed later.

    :cvar id: The ID of this node. See :class:`HydrologyNetwork` for this value's significance
    :vartype id: int
    :cvar position: The location of the node in meters
    :vartype position: tuple[float,float]
    :cvar elevation: The node's elevation in meters
    :vartype elevation: float
    :cvar priority: The priority of the node. See :class:`HydrologyNetwork` for this value's significance
    :vartype priority: int
    :cvar parent: The parent node, or None if this node is a river mouth
    :vartype parent: HydroPrimitive | None
    :cvar contourIndex: If this node is on the coast, this is the index in :class:`Shore` that is closest to this node
    :vartype contourIndex: int
    :cvar rivers: A :class:`LineString` representing the river's actual path. It only flows to a node where it joins with a larger river. This is set in :func:`RiverInterpolationFunctions.computeRivers`
    :vartype rivers: LineString
    :cvar localWatershed: The (rough) area of this cell
    :vartype localWatershed: float
    :cvar inheritedWatershed: The area of this cell, plus all the areas of all the cells that drain into it
    :vartype inheritedWatershed: float
    :cvar flow: The flow rate of water draining out of this cell (including flow from ancestor cells) in cubic meters per second
    :vartype flow: float
    """
    def __init__(self, id: int, loc: typing.Tuple[float,float], elevation: float, priority: int, parent: 'HydroPrimitive'):
        self.id = id
        self.position = loc
        self.elevation = elevation
        self.priority = priority
        self.parent = parent
        self.inheritedWatershed = 0
        self.rivers = [ ]
    def x(self) -> float:
        """Gets the x location of this node

        :return: The x location of this node
        :rtype: float
        """
        return self.position[0]
    def y(self) -> float:
        """Gets the y position of this node

        :return: The y location of this node
        :rtype: float
        """
        return self.position[1]

class HydrologyNetwork:
    """This class represents the network of rivers that flow over the land

    A HydrologyNetwork is basically a forest of trees, with each tree
    representing a river that merges and drains into the ocean through a
    single mouth node.

    A HydrologyNetwork is empty when it is instantiated. The network is
    built incrementally using
    :func:`addNode()<DataModel.HydrologyNetwork.addNode>`. Edges connect
    all nodes.

    It should be noted that each node is associated with an integer ID.
    This ID is strictly the order that each node was added in, starting at
    0. Nodes cannot be removed, thus ``range(len(hydrology))`` will
    iterate over all the nodes in the network.

    .. note::
       Some methods return references to the actual HydroPrimitives that constitute
       the graph. Others return integers that refer to them. Always refer to the
       return type when querying an instance of this class.

    Internally, the data is held in a :class:`networkx DiGraph<networkx.DiGraph>`. A
    :class:`cKDTree<scipy.spatial.cKDTree>` is used for lookup by area.
    """
    def __init__(self, db: sqlite3.Connection = None):
        self.nodeCounter = 0
        self.graph = nx.DiGraph()
        self.mouthNodes = []

        if db is not None:
            self._loadFromDB(db)
    def _loadFromDB(self, db: sqlite3.Connection) -> None:
        db.row_factory = sqlite3.Row

        allpoints_list = [ ]

        for row in db.execute('SELECT id, parent, elevation, localwatershed, inheritedwatershed, flow, X(loc) AS xLoc, Y(loc) AS yLoc FROM RiverNodes ORDER BY id'):
            id = row['id']
            parentID = row['parent']
            elevation = row['elevation']
            localWatershed = row['localWatershed']
            inheritedWatershed = row['inheritedWatershed']
            flow = row['flow']
            x, y = row['xLoc'], row['yLoc']

            # get the node's parent by ID
            parent = None
            if parentID is not None:
                parent = self.graph.nodes[parentID]['primitive']

            # get the rivers of the node
            rivers = [ ]
            for river in db.execute('SELECT AsText(path) FROM RiverPaths WHERE rivernode = ?', (id,)):
                strPoints = river[0].replace('LINESTRING Z(', '').replace(')', '').split(', ')
                riverGeom = [(float(x), float(y), float(z)) for x,y,z in [point.split(' ') for point in strPoints]]
                rivers.append(geom.LineString(riverGeom))

            allpoints_list.append((x,y))

            node = HydroPrimitive(id, (x,y), elevation, 0, parent)
            node.localWatershed = localWatershed
            node.inheritedWatershed = inheritedWatershed
            node.flow = flow
            node.rivers = rivers

            self.graph.add_node(id, primitive=node)

            if parentID is None:
                self.mouthNodes.append(id)
            else:
                self.graph.add_edge(parentID, id)

        self.graphkd = cKDTree(allpoints_list)
    def saveToDB(self, db: sqlite3.Connection) -> None:
        with db:
            db.execute('DELETE FROM RiverNodes')
            # write river nodes
            db.executemany("INSERT INTO RiverNodes (id, parent, elevation, localwatershed, inheritedwatershed, flow, loc) VALUES (?, ?, ?, ?, ?, ?, MakePoint(?, ?, 347895))", [(node.id, node.parent.id if node.parent is not None else None, node.elevation, node.localWatershed, node.inheritedWatershed, node.flow, node.x(), node.y()) for node in self.allNodes()])

            # write river paths
            for node in self.allNodes():
                for river in node.rivers:
                    geom = "LINESTRINGZ(" + ", ".join([f'{p[0]} {p[1]} {p[2]}' for p in river.coords]) + ")"
                    try:
                        db.execute("INSERT INTO RiverPaths (rivernode, path) VALUES (?, GeomFromText(?, 347895))", (node.id, geom))
                    except:
                        print('printing geom')
                        print(geom)
                        raise
                    #TODO: refactor rivers
                    #TODO: this can also be simplified by only storing rivers of leaf nodes
    def addNode(self, loc: typing.Tuple[float,float], elevation: float, priority: int, contourIndex: int=None, parent: HydroPrimitive=None) -> HydroPrimitive:
        """Creates and adds a HydrologyPrimitive to the network

        :param loc: The location of the new node
        :type loc: tuple[float,float]
        :param elevation: The elevation of the node in meters
        :type elevation: float
        :param priority: The priority of the node (for graph expansion)
        :type priority: int
        :param contourIndex: The index of the node's location on the shore (corresponds to :class:`ShoreModel[]<DataModel.ShoreModel>`)
        :type contourIndex: int, optional
        :param parent: The ID of the parent node, if applicable
        :type parent: int, optional

        The priority of the node affects its selection, as described in §4.2.1
        of Genevaux et al, within the graph expansion algorithm.

        The contourIndex should be used when the node represents the mouth of
        a river. In this case, contourIndex should be the index such that,
        when passed to ``ShoreModel[contourIndex]``, yields the position that
        most closely corresponds to the node. (Internally, this is used to
        figure out what the 'direction' of the river should be in the graph
        expansion.)

        :return: The node created
        :rtype: HydroPrimitive
        """
        node = HydroPrimitive(self.nodeCounter, loc, elevation, priority, parent)
        if parent is None or contourIndex is not None:
            node.contourIndex = contourIndex
            self.mouthNodes.append(self.nodeCounter)
        self.graph.add_node(
            self.nodeCounter,
            primitive=node
        )
        if parent is not None:
            self.graph.add_edge(parent.id,self.nodeCounter)
        self.nodeCounter += 1
        allpoints_list = np.array([self.graph.nodes[n]['primitive'].position for n in range(self.nodeCounter)])
        self.graphkd = cKDTree(allpoints_list)
        
        # Classify the new leaf
        node.priority = 1

        # Classify priorities of affected nodes
        classifyNode = node.parent
        while True:
            if classifyNode is None:
                break
            children = self.upstream(classifyNode.id)
            maxNumber = max([child.priority for child in children])
            numMax = len([child.priority for child in children if child.priority == maxNumber])
            if numMax > 1 and classifyNode.priority < maxNumber + 1:
                # if there is more than one child with the maximum number,
                # and the parent isn't already set for it, then change it
                classifyNode.priority = maxNumber + 1
            elif classifyNode.priority < maxNumber:
                # if the parent isn't already set for the maximum number,
                # change it
                classifyNode.priority = maxNumber
            else:
                # if the parent does not need to be changed at all, then
                # none of its ancestors do, and the graph is fully adjsuted
                break
            classifyNode = classifyNode.parent

        return node
    def query_ball_point(self, loc: typing.Tuple[float,float], radius: float) -> typing.List[int]:
        """Gets all nodes that are within a certain distance of a location

        :param loc: The location to test
        :type loc: tuple[float,float]
        :param radius: The radius to search in
        :type radius: float
        :return: The IDs of all nodes that are within ``radius`` of ``loc``
        :rtype: list[int]
        """
        return self.graphkd.query_ball_point(loc,radius)
    def edgesWithinRadius(self, loc: typing.Tuple[float,float], radius: float) -> typing.List[typing.Tuple[HydroPrimitive,HydroPrimitive]]:
        """Gets all *edges* that are within a certain distance of a location

        :param loc: The location to test
        :type loc: tuple[float,float]
        :param radius: The radius to search in
        :type radius: float
        :return: Each tuple represents both ends of the edge
        :rtype: list[tuple[HydroPrimitive,HydroPrimitive]]
        """
        nodesToCheck = self.graphkd.query_ball_point(loc,radius)
        edges = [ self.graph.out_edges(n) for n in nodesToCheck ]
        edges = [item for edge in edges for item in edge]
        return [(self.graph.nodes[e[0]]['primitive'],self.graph.nodes[e[1]]['primitive']) for e in edges]
    def downstream(self, node: int) -> HydroPrimitive:
        """Gets the node that this node flows into

        :param node: The ID of the node whose parent you wish to identify
        :type node: int
        :return: The node that this node flows into
        :rtype: HydroPrimitive
        """
        parent = list(self.graph.predecessors(node))
        if len(parent) > 0:
            return self.graph.nodes[parent[0]]['primitive']
        else:
            return None
    def upstream(self, node: int) -> typing.List[HydroPrimitive]:
        """Gets all the nodes that flow into this node

        :param node: The ID of the node whose ancestors you wish to query
        :type node: int
        :return: A list of nodes that are upstream of this one
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[n]['primitive'] for n in self.graph.successors(node)]
    def adjacentNodes(self, node: int) -> typing.List[HydroPrimitive]:
        """Basically just a concatenation of :func:`downstream()<DataModel.HydrologyNetwork.downstream>` and :func:`upstream()<DataModel.HydrologyNetwork.upstream>`

        :param node: The ID of the node whose adjacent nodes you wish to identify
        :type node: int
        :return: A list of all adjacent nodes, upstream and downstream
        :rtype: list[HydroPrimitive]
        """
        downstream = self.downstream(node)
        upstream   = self.upstream(node)
        if downstream is None:
            downstream = [ ]
        return upstream + downstream
    def allUpstream(self, node: int) -> typing.List[HydroPrimitive]:
        """Gets *all* nodes that are upstream of this one---all the way out to the leaf nodes

        :param node: The node whose upstream nodes you wish to identify
        :type node: int
        :return: All nodes that are upstream of this one
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[n]['primitive'] for n in nx.descendants(self.graph, node)]
    def allNodes(self) -> typing.List[HydroPrimitive]:
        """All nodes in the graph

        This can be used if it is more convenient than ``range(len(hydrology))``

        :return: All nodes in the graph
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[node]['primitive'] for node in list(self.graph.nodes)]
    def allEdges(self) -> typing.List[typing.Tuple[HydroPrimitive,HydroPrimitive]]:
        """Gets all edges in the graph

        :return: Every edge in the graph
        :rtype: list[tuple[HydroPrimitive,Hydroprimitive]]
        """
        return [(self.graph.nodes[u]['primitive'],self.graph.nodes[v]['primitive']) for u,v in self.graph.edges]
    def allMouthNodes(self) -> typing.List[HydroPrimitive]:
        """Gets all the mouth nodes (those that drain to the sea)

        :return: Every mouth node
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[id]['primitive'] for id in self.mouthNodes]
    def allLeaves(self, node) -> typing.List[HydroPrimitive]:
        """Gets all leaf nodes that antecede this node

        :param node: The node whose leaf ancestors you wish to identify
        :type node: list[HydroPrimitive]
        """
        ids = [s for s in nx.descendants(self.graph,node) if len(self.graph.out_edges(s))==0]
        return [self.graph.nodes[id]['primitive'] for id in ids]
    def node(self, node: int) -> HydroPrimitive:
        """Gets a reference to the node that corresponds to a given ID

        :param node: The ID of the node you wish to query
        :type node: int
        :return: A reference to the HydroPrimitive that corresponds to the ID
        :rtype: HydroPrimitive
        """
        return self.graph.nodes[node]['primitive']
    def dfsPostorderNodes(self) -> typing.List[HydroPrimitive]:
        """Returns a list of all nodes in the network in a *depth-first, postorder* order

        See `Depth-first search <https://en.wikipedia.org/wiki/Depth-first_search/>`_.

        :return: All nodes in the network
        :rtype: list[HydroPrimitive]
        """
        ids = list(nx.dfs_postorder_nodes(self.graph))
        return [self.graph.nodes[id]['primitive'] for id in ids]
    def pathToNode(self, origin: int, destination: int) -> typing.List[HydroPrimitive]:
        """Returns the the path between any two nodes (but they should be in the same river system)

        :param origin: One end of the path
        :type origin: int
        :param destination: The other end of the path
        :type destination: int
        :return: References to the HydroPrimitives that make up the path
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[n]['primitive'] for n in nx.shortest_path(self.graph,origin,destination)]
    def __len__(self) -> int:
        """Returns the number of nodes in the forest

        :return: The number of nodes in the forest
        :rtype: int
        """
        return len(self.graph.nodes)

def openCVFillPolyArray(points: typing.List[typing.Tuple[float,float]]) -> typing.List[np.ndarray]:
    """Formats a list of points into a format that OpenCV will understand

    :param points: The points for format
    :type points: list[tuple[float,float]]
    :return: Returns the points in a format that some OpenCV methods can use
    :rtype: list[np.array[[float,float]]]
    """
    return [ np.array( [ [int(p[0]),int(p[1])] for p in points ] ) ]

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
    def __init__(self, Q0: Q, Q1: Q, hasRiver: bool, isShore: bool, shoreSegment: typing.Tuple[int, int]=None) -> None:
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

    :param shore: The ShoreModel for the land area
    :type shore: ShoreModel
    :param hydrology: The filled-out HydrologyNetwork for the land area
    :type hydrology: HydrologyNetwork
    :param resolution: The resolution of the underlying rasters in meters per pixel
    :type resolution: float
    :param edgeLength: The edge length in the simulation
    :type edgeLength: float
    :param binaryFile: A binary file
    :type binaryFile: typing.IO

    .. note::
        If passing in a binary file, you must seek to the appropriate location.

    .. note::
       ``resolution`` should be the same that was passed to the ShoreModel.

    """
    def loadFromDB(self, resolution, edgeLength, shore, hydrology, db: sqlite3.Connection):
        db.row_factory = sqlite3.Row

        self.edgeLength = edgeLength
        self.shore = shore
        self.hydrology = hydrology

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
        for row in db.execute('SELECT DISTINCT Cells.rivernode, Edges.id FROM Cells JOIN Edges ON Edges.Q0 = Cells.q OR Edges.Q1 = Cells.q'):
            cellID = row['rivernode']
            edgeID = row['id']

            if cellID not in self.cellsEdges:
                self.cellsEdges[cellID] = [ ]
            self.cellsEdges[cellID].append(edges[edgeID])

        self.cellsDownstreamRidges: Dict[int, Edge] = { }
        # get all the pairs of children and their parents, and get the edges between them
        for row in db.execute('SELECT rivernode, downstreamEdge FROM DownstreamEdges'):
            nodeID = row['rivernode']
            downstreamEdgeID = row['downstreamEdge']

            self.cellsDownstreamRidges[nodeID] = edges[downstreamEdgeID]
    def saveToDB(self, db: sqlite3.Connection):
        #compile list of all primitives
        createdEdges: typing.Dict[int, Edge] = { }
        for cellID in range(len(self.hydrology)):
            for edge in self.cellEdges(cellID):
                if id(edge) not in createdEdges:
                    createdEdges[id(edge)] = edge

        with db:
            db.execute("DELETE FROM Qs")
            db.execute("DELETE FROM Cells")
            db.execute("DELETE FROM Edges")

            # write Qs
            db.executemany("INSERT INTO Qs (id, elevation, loc) VALUES (?, ?, MakePoint(?, ?, 347895))", [(id(q), q.elevation, q.position[0], q.position[1]) for q in self.qs])

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
    def cellVertices(self, nodeID: int) -> typing.List[Point]:
        """Gets the coordinates of the Qs that define the shape of the node's cell

        :param nodeID: The ID of the node whose shape you wish to query
        :type nodeID: int
        :return: The coordinates of the cell's shape
        :rtype: Math.Point
        """
        ridges = self.cellsEdges[nodeID] # the indices of the vertex boundaries
        return [ridge.Q0.position for ridge in ridges] # positions of all the vertices
    def cellArea(self, node: HydroPrimitive) -> float:
        """Calculates the area of a cell

        This method derives the area based on the cell's shape. It is accurate.

        :param node: The node that you wish to query
        :type node: HydroPrimitive
        """
        try:
            return Math.convexPolygonArea(
                node.position,
                self.cellVertices(node.id)
            )
        except:
            return self.resolution**2
    def cellQs(self, node: int) -> typing.List[Q]:
        """Returns all the Qs binding the cell that corresponds to the given node

        :param node: The node you wish to query
        :type node: int
        :return: List of Q instances
        :rtype: list[Q]
        """
        ridges = self.cellsEdges[node]
        return [ridge.Q0 for ridge in ridges]
    def allQs(self) -> typing.List[Q]:
        """Simply returns all Qs of the land

        Note: the index of a Q in this list does not correspond to anything significant

        :return: All Qs of the land
        :rtype: list[Q]
        """
        return self.qs.copy()
    def boundingBox(self, n: int) -> typing.Tuple[float,float,float,float]:
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
        return Math.pointInConvexPolygon(p, self.cellVertices(n), self.hydrology.node(n).position)
    def cellRidges(self, n: int) -> typing.List[Edge]:
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
    def nodeID(self, point: Point) -> int:
        """Returns the id of the node/cell in which the point is located

        :param point: The point you wish to test
        :type point: Math.Point
        :return: The ID of a node/cell (Returns None if it isn't in a valid cell)
        :rtype: int
        """
        # check hydrology nodes within a certain distance
        for id in self.hydrology.query_ball_point(point, self.edgeLength):
            # if this point is within the voronoi region of one of those nodes,
            # then that is the point's node
            if self.isInCell(point, id):
                return id
        return None

class T:
    """Terrain primitive

    Terrain primitives are created with a ``position`` and ``cell``
    attribute. The elevation is computed separately.

    :cvar position: The position of the primitive
    :vartype position: tuple[float,float]
    :cvar cell: The ID of the cell in which this primitive is situated
    :vartype cell: int
    :cvar elevation: The elevation of the primitive
    :vartype elevation: float
    """
    def __init__(self, position, cell):
        self.position = position
        self.cell = cell
        self.elevation = None

class Terrain:
    """Holds and organizes the terrain primitives (:class:`T`)

    :param hydrology: The HydrologyNetwork of the land
    :type hydrology: HydrologyNetwork
    :param cells: The TerrainHoneycomb of the land
    :type cells: TerrainHoneycomb
    :param num_points: (Roughly) the number of points in each cell
    :type num_points: int
    """
    def loadFromDB(self, db: sqlite3.Connection):
        db.row_factory = sqlite3.Row

        self.cellTsDict = { }
        self.tList = [ ]

        # get all the primitives
        for row in db.execute("SELECT rivercell, elevation, X(loc) AS locX, Y(loc) AS locY FROM Ts"):
            t = T((row["locX"], row["locY"]), row["rivercell"])
            t.elevation = row["elevation"]
            if row["rivercell"] not in self.cellTsDict:
                self.cellTsDict[row["rivercell"]] = [ ]
            self.cellTsDict[row["rivercell"]].append(t)
            self.tList.append(t)

        allpoints_list = [[t.position[0],t.position[1]] for t in self.allTs()]
        allpoints_nd = np.array(allpoints_list)
        self.apkd = cKDTree(allpoints_nd)
    def saveToDB(self, db: sqlite3.Connection):
        with db:
            db.execute("DELETE FROM Ts")
            db.executemany("INSERT INTO Ts (id, rivercell, elevation, loc) VALUES (?, ?, ?, MakePoint(?, ?, 347895))", [(idx, t.cell, t.elevation, t.position[0], t.position[1]) for idx, t in enumerate(self.tList)])
    def allTs(self) -> typing.List[T]:
        """Simply returns all the terrain primitives

        :return: A list of all the terrain primitives
        :rtype: list[T]
        """
        return self.tList.copy()
    def cellTsDict(self, cell: int) -> typing.List[T]:
        """Gets the terrain primitives within a given cell

        :param cell: The ID of the cell you wish to query
        :type cell: int
        :return: A list of the terrain primitives in the cell
        :rtype: list[T]
        """
        return self.Ts[cell].copy()
    def getT(self, tid: int) -> T:
        """Gets a terrain primitive identified by its index in the list of all primitives

        :param tid: The index of the primitive you wish to retrieve
        :type tid: int
        :return: The terrain primitive
        :rtype: T
        """
        return self.tList[tid]
    def query_ball_point(self, loc: typing.Tuple[float,float], radius: float) -> typing.List[T]:
        """Gets all terrain primitives within a given radius of a given location

        :param loc: The location you wish to test
        :type loc: tuple[float,float]
        :param radius: The search radius
        :type radius: float
        :return: A list of the primitives within that area
        :rtype: list[T]
        """
        return [self.tList[i] for i in self.apkd.query_ball_point(loc,radius)]
    def __len__(self) -> int:
        """Returns the number of nodes in the forest

        :return: The number of primitives on the map
        :rtype: int
        """
        return len(self.tList)

def readValue(type, stream):
    buffer = stream.read(struct.calcsize(type))
    return struct.unpack(type, buffer)[0]