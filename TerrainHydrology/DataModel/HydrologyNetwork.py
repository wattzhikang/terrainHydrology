import sqlite3
import numpy as np
import networkx as nx
import shapely.geometry as geom
from scipy.spatial import cKDTree

from typing import Tuple, List, Dict

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
    def __init__(self, id: int, loc: Tuple[float,float], elevation: float, priority: int, parent: 'HydroPrimitive'):
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
        """Loads the hydrology network from a database

        :param db: The database to load from
        :type db: sqlite3.Connection
        """
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
        """Writes the hydrology network to a database

        :param db: The database to write to
        :type db: sqlite3.Connection
        """
        with db:
            db.execute('DELETE FROM RiverNodes')
            # write river nodes
            db.executemany("INSERT INTO RiverNodes (id, parent, elevation, localwatershed, inheritedwatershed, flow, loc) VALUES (?, ?, ?, ?, ?, ?, MakePoint(?, ?, 347895))", [(node.id, node.parent.id if node.parent is not None else None, node.elevation, node.localWatershed, node.inheritedWatershed, node.flow, float(node.x()), float(node.y())) for node in self.allNodes()])

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
    def addNode(self, loc: Tuple[float,float], elevation: float, priority: int, contourIndex: int=None, parent: HydroPrimitive=None) -> HydroPrimitive:
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
    def query_ball_point(self, loc: Tuple[float,float], radius: float) -> List[int]:
        """Gets all nodes that are within a certain distance of a location

        :param loc: The location to test
        :type loc: tuple[float,float]
        :param radius: The radius to search in
        :type radius: float
        :return: The IDs of all nodes that are within ``radius`` of ``loc``
        :rtype: list[int]
        """
        return self.graphkd.query_ball_point(loc,radius)
    def edgesWithinRadius(self, loc: Tuple[float,float], radius: float) -> List[Tuple[HydroPrimitive,HydroPrimitive]]:
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
    def upstream(self, node: int) -> List[HydroPrimitive]:
        """Gets all the nodes that flow into this node

        :param node: The ID of the node whose ancestors you wish to query
        :type node: int
        :return: A list of nodes that are upstream of this one
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[n]['primitive'] for n in self.graph.successors(node)]
    def adjacentNodes(self, node: int) -> List[HydroPrimitive]:
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
    def allUpstream(self, node: int) -> List[HydroPrimitive]:
        """Gets *all* nodes that are upstream of this one---all the way out to the leaf nodes

        :param node: The node whose upstream nodes you wish to identify
        :type node: int
        :return: All nodes that are upstream of this one
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[n]['primitive'] for n in nx.descendants(self.graph, node)]
    def allNodes(self) -> List[HydroPrimitive]:
        """All nodes in the graph

        This can be used if it is more convenient than ``range(len(hydrology))``

        :return: All nodes in the graph
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[node]['primitive'] for node in list(self.graph.nodes)]
    def allEdges(self) -> List[Tuple[HydroPrimitive,HydroPrimitive]]:
        """Gets all edges in the graph

        :return: Every edge in the graph
        :rtype: list[tuple[HydroPrimitive,Hydroprimitive]]
        """
        return [(self.graph.nodes[u]['primitive'],self.graph.nodes[v]['primitive']) for u,v in self.graph.edges]
    def allMouthNodes(self) -> List[HydroPrimitive]:
        """Gets all the mouth nodes (those that drain to the sea)

        :return: Every mouth node
        :rtype: list[HydroPrimitive]
        """
        return [self.graph.nodes[id]['primitive'] for id in self.mouthNodes]
    def allLeaves(self, node) -> List[HydroPrimitive]:
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
    def dfsPostorderNodes(self) -> List[HydroPrimitive]:
        """Returns a list of all nodes in the network in a *depth-first, postorder* order

        See `Depth-first search <https://en.wikipedia.org/wiki/Depth-first_search/>`_.

        :return: All nodes in the network
        :rtype: list[HydroPrimitive]
        """
        ids = list(nx.dfs_postorder_nodes(self.graph))
        return [self.graph.nodes[id]['primitive'] for id in ids]
    def pathToNode(self, origin: int, destination: int) -> List[HydroPrimitive]:
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
