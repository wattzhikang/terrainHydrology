#! /bin/python

import unittest
from unittest.mock import Mock

import io

import shapefile
from PIL import Image
from PIL import ImageDraw
from matplotlib.pyplot import draw
import os.path
from typing import Dict, List
import math

from lib.HydrologyFunctions import HydrologyParameters, isAcceptablePosition, selectNode, coastNormal, getLocalWatershed, getInheritedWatershed, getFlow
from lib.ShoreModel import ShoreModel
from lib.HydrologyNetwork import HydrologyNetwork, HydroPrimitive
from lib.TerrainHoneycomb import TerrainHoneycomb, Q, Edge
from lib.Terrain import Terrain, T
from lib.Math import Point, edgeIntersection, segments_intersect_tuple, polygonArea
from lib.TerrainPrimitiveFunctions import computePrimitiveElevation
from lib.RiverInterpolationFunctions import computeRivers
from lib.TerrainHoneycombFunctions import orderVertices, orderEdges, orderCreatedEdges, hasRiver, processRidge, getVertex0, getVertex1, ridgesToPoints, findIntersectingShoreSegment, initializeTerrainHoneycomb
import lib.SaveFile

from .testcodegenerator import getPredefinedObjects0

class ShapefileShoreTests(unittest.TestCase):
    def setUp(self):
        with shapefile.Writer('inputShape', shapeType=5) as shp:
            #         0         1          2          3          4          5           6         7        8         (beginning)
            shape = [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8], [0,-437] ]
            shape.reverse() # pyshp expects shapes to be clockwise

            shp.field('name', 'C')

            shp.poly([ shape ])
            shp.record('polygon0')

    def test_closestNPoints(self):
        shore = ShoreModel(inputFileName='inputShape')

        closestIndices = shore.closestNPoints((80,-185), 1)

        self.assertEqual(2, closestIndices[0])

        closestIndices = shore.closestNPoints((80,-185), 2)

        self.assertEqual(2, len(closestIndices))
        self.assertEqual(2, closestIndices[0])
        self.assertEqual(3, closestIndices[1])
    
    def test_onLand(self) -> None:
        shore = ShoreModel(inputFileName='inputShape')

        self.assertTrue(shore.isOnLand((0,-100)))
        self.assertTrue(shore.isOnLand((50,-100)))
        self.assertFalse(shore.isOnLand((35,-120)))

    def tearDown(self) -> None:
        os.remove('inputShape.shp')
        os.remove('inputShape.dbf')
        os.remove('inputShape.shx')

class HydrologyFunctionTests(unittest.TestCase):
    def setUp(self):
        #create shore
        # r = 100
        # image = Image.new('L', (4*r,4*r))

        # drawer = ImageDraw.Draw(image)

        #Keep in mind that these are _image_ coordinates
        # drawer.polygon([(150,134),(100,200),(150,286),(250,286),(300,200),(250,134)], 255)
        #This should work out to (-500,660), (-1000,0), (-500,-860), (500,-860), (1000,0), (500,660)

        # image.save('imageFile.png')

        # shore = ShoreModelImage(10, 'imageFile.png')

        shpBuf = io.BytesIO()
        shxBuf = io.BytesIO()
        dbfBuf = io.BytesIO()

        with shapefile.Writer(shp=shpBuf, shx=shxBuf, dbf=dbfBuf, shapeType=5) as shp:
            #         0           1          2            3           4           5         6          (beginning)
            shape = [ (-500,660), (-1000,0), (-500,-860), (130,-860), (500,-860), (1000,0), (500,660), (-500,660) ]
            shape.reverse() # pyshp expects shapes to be clockwise

            shp.field('name', 'C')

            shp.poly([ shape ])
            shp.record('polygon0')

        shore = ShoreModel(shpFile=shpBuf, shxFile=shxBuf, dbfFile=dbfBuf)

        #create candidate nodes
        candidateNodes = [ ]

        candidateNodes.append(HydroPrimitive(0, None,  4.0, 1, None))
        candidateNodes.append(HydroPrimitive(1, None,  6.0, 2, None))
        candidateNodes.append(HydroPrimitive(2, None, 14.0, 3, None))
        candidateNodes.append(HydroPrimitive(3, None,  8.0, 3, None))
        candidateNodes.append(HydroPrimitive(4, None, 24.0, 1, None))
        candidateNodes.append(HydroPrimitive(5, None, 23.0, 4, None))

        #create hydrology
        hydrology = HydrologyNetwork()

        #create real mouth nodes
        self.node0 = hydrology.addNode(shore[3], 0, 0, 3) # This should be (130,-860)
        hydrology.addNode(shore[2], 0, 0, 2) # This should be (230,-860)
        hydrology.addNode(shore[4], 0, 0, 4) # This should be (330,-860)

        hydrology.addNode((130,-760), 10, 0, parent=self.node0)
        
        #create the parameters object
        edgelength = 100
        sigma = 0.75
        eta = 0.5
        zeta = 14
        self.params = HydrologyParameters(shore, hydrology, None, None, None, None, edgelength, sigma, eta, zeta, None, None, candidateNodes)

    def test_select_node(self):
        selectedNode = selectNode(self.params.candidates, self.params.zeta)

        self.assertEqual(self.params.zeta, 14.0)
        self.assertEqual(selectedNode.id, 3)
    
    def test_is_acceptable_position_not_on_land(self):
        acceptable0 = isAcceptablePosition((-100,-900), self.params)
        acceptable1 = isAcceptablePosition((-100,-700), self.params)
        
        self.assertFalse(acceptable0)
        self.assertTrue(acceptable1)
    
    def test_is_acceptable_position_too_close_to_seeee(self):
        acceptable = isAcceptablePosition((-100,-830), self.params)

        self.assertFalse(acceptable)
    
    def test_is_acceptable_position_too_close_to_nodes_or_edges(self):
        acceptable0 = isAcceptablePosition((80,-800), self.params)
        acceptable1 = isAcceptablePosition((100,-600), self.params)
        
        self.assertFalse(acceptable0)
        self.assertTrue(acceptable1)
    
    def test_coast_normal(self):
        angle = coastNormal(self.node0, self.params)
        
        self.assertAlmostEqual(angle, math.pi * 0.5, places=3)

class ExtendedHydrologyFunctionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.edgeLength, self.shore, self.hydrology, self.cells = getPredefinedObjects0()
    
    def test_localWatershedTest(self) -> None:
        node = self.hydrology.node(14)
        cellArea = self.cells.cellArea(node.id)
        self.assertEqual(getLocalWatershed(node, self.cells), cellArea)

    def test_inheritedWatershedTest(self) -> None:
        node = self.hydrology.node(14)
        upstreamInherited = self.hydrology.node(27).inheritedWatershed
        self.assertEqual(getInheritedWatershed(node, self.hydrology), node.localWatershed + upstreamInherited)

    def test_flowTest(self) -> None:
        node = self.hydrology.node(14)
        expectedFlow = 0.42 * node.inheritedWatershed**0.69
        self.assertEqual(getFlow(node.inheritedWatershed), expectedFlow)
        pass

class MathTests(unittest.TestCase):
    def setUp(self) -> None:
        # self.edgeLength, self.shore, self.hydrology, self.cells = getPredefinedObjects0()
        pass

    def test_intersection_test_0(self) -> None:
        intersection: Point = edgeIntersection((0,5), (5,10), (0,10), (5,5))

        self.assertAlmostEqual(intersection[0], 2.5, delta=0.01)
        self.assertAlmostEqual(intersection[1], 7.5, delta=0.01)
    
    def test_intersection_test_1(self) -> None:
        intersection: Point = edgeIntersection((-12.5,-5), (-5,-12.5), (-10,-15), (-5,-5))

        self.assertAlmostEqual(intersection[0], -7.5, delta=0.01)
        self.assertAlmostEqual(intersection[1], -10.0, delta=0.01)
    
    def test_intersection_test_2(self) -> None:
        intersection: Point = edgeIntersection([83.8,-63.9], [61.4,-98.4], (22.1,-56.4), (93.4,-88.0))

        self.assertAlmostEqual(intersection[0], 74.11, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.72, delta=1.0)

    def test_polygon_area_test_0(self) -> None:
        area = polygonArea([(0,0), (10,0), (10,10), (0,10)])

        self.assertEqual(area, 100)

    def test_polygon_area_test_1(self) -> None:
        area = polygonArea([(10,20), (0, 30), (-10, 20), (-1, 20), (-1, 10), (-10, 10), (0, 5), (10, 10), (1, 10), (1, 20)])

        self.assertEqual(area, 170)

    def tearDown(self) -> None:
        # os.remove('imageFile.png')
        pass

class HoneycombTests(unittest.TestCase):
    def setUp(self) -> None:
        # self.edgeLength, self.shore, self.hydrology, self.cells = getPredefinedObjects0()
        pass

    def test_order_vertices0(self) -> None:
        ridge_vertices = { 1: [5, 3] }
        vertices = { 5: (5,-10), 3: (10,-12) }

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = (5, -15)
        
        orderVertices(1, node, vor)

        self.assertEqual(vor.ridge_vertices[1][0], 3)
    def test_order_vertices1(self) -> None:
        ridge_vertices = { 1: [3, 5] }
        vertices = { 5: (5,-10), 3: (10,-12) }

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = (5, -15)
        
        orderVertices(1, node, vor)

        self.assertEqual(vor.ridge_vertices[1][0], 3)
    def test_order_vertices2(self) -> None:
        ridge_vertices = { 20: [4, 14] }
        vertices = { 4: (-29,-8), 14: (-31,-7) }

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = (-28,-6)
        
        orderVertices(20, node, vor)

        self.assertEqual(vor.ridge_vertices[20][0], 14)
    def test_order_vertices3(self) -> None:
        ridge_vertices = { 83: [16, 57], 93: [57, 52], 78: [52, 46], 40: [46, 23], 20: [23, 31], 32: [31, 16] }
        vertices = { 16: [61.443429,-98.40846], 57: [81.16758,-127.24641], 52: [122.02123,-126.7665], 46: [140.51944,-97.614588], 23: [119.10888,-65.079382], 31: [83.812318,-63.929693] }

        # I think this test is failing because Inkscape uses a left-handed coordinate system
        # you should be able to fix it by making all the y values negative

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = (102.7, -97.7)
        
        orderVertices(78, node, vor)

        self.assertEqual(vor.ridge_vertices[78][0], 52)

    def test_order_edges0(self) -> None:
        edgeIDs = [78,93,83,32,20,40]

        nodeLoc = (102.7, -97.7)

        vor = Mock()
        ridge_vertices = { 83: [16, 57], 93: [57, 52], 78: [52, 46], 40: [46, 23], 20: [23, 31], 32: [31, 16] }
        vor.ridge_vertices = ridge_vertices
        # this shape is just a hexagon
        vertices = { 16: [61.4,-98.4], 57: [81.1,-127.2], 52: [122.0,-126.7], 46: [140.5,-97.6], 23: [119.1,-65.0], 31: [83.8,-63.9] }
        vor.vertices = vertices

        shore = Mock()
        shore.isOnLand.return_value = True

        orderedEdges = orderEdges(edgeIDs, nodeLoc, vor, shore)

        self.assertEqual(78, orderedEdges[0])
        self.assertEqual(40, orderedEdges[1])
        self.assertEqual(20, orderedEdges[2])
        self.assertEqual(32, orderedEdges[3])
        self.assertEqual(83, orderedEdges[4])
        self.assertEqual(93, orderedEdges[5])
    def test_orderCreatedEdges0(self) -> None:
        edgeIDs = [32,83,93,78,40,20]

        nodeLoc = (102.7, -97.7)

        vor = Mock()
        ridge_vertices = { 83: [16, 57], 93: [57, 52], 78: [52, 46], 40: [46, 23], 20: [23, 31], 32: [31, 16] }
        vor.ridge_vertices = ridge_vertices
        # this shape is just a hexagon
        vertices = { 16: [61.4,-98.4], 57: [81.1,-127.2], 52: [122.0,-126.7], 46: [140.5,-97.6], 23: [119.1,-65.0], 31: [83.8,-63.9] }
        vor.vertices = vertices

        shore = Mock()
        # isOnLandDict = { vertices[31]: True, vertices[16]: False, vertices[57]: False, vertices[52]: True, vertices[46]: True, vertices[23]: True }
        shore.isOnLand.side_effect = lambda vertex : not vertex == vertices[16] and not vertex == vertices[57]
        shorePoints = { 15: (56.1,-49.1), 16: (130.3,-173.9) }
        shore.__getitem__ = Mock()
        shore.__getitem__.side_effect = lambda shoreIdx : shorePoints[shoreIdx]
        # shore.__len__ = Mock(return_value=420)
        # shore.closestNPoints.return_value = [ 15, 16 ] # This is technically wrong, but it's fine


        q52 = Q(vertices[52])
        q23 = Q(vertices[23])
        q31 = Q(vertices[31])
        createdQs = {
            52: q52,
            23: q23,
            31: q31
        }
        edge93 = Edge(createdQs[52], Q((102.6,-127.5)), hasRiver=False, isShore=False, shoreSegment=(17,18))
        edge20 = Edge(createdQs[31], createdQs[23], hasRiver=False, isShore=False)
        createdEdges = {
            93: edge93,
            20: edge20
        }

        orderCreatedEdges(edgeIDs, vor, createdEdges)
        
        self.assertEqual(edge93.Q0.position, (102.6,-127.5))
        self.assertEqual(edge93.Q1, q52)
        self.assertEqual(edge20.Q0, q23)
        self.assertEqual(edge20.Q1, q31)

    def test_hasRiver(self) -> None:
        vor = Mock()
        ridge_points = { 83: [64,4], 93: [64,6], 78: [64,65], 40: [64,20], 20: [64,13], 32: [64,95] }
        vor.ridge_points = ridge_points

        node4 = Mock()
        node64 = Mock()
        node64.parent = node4
        node13 = Mock()
        node13.parent = node64
        node65 = Mock()
        node65.parent = node64
        node6 = Mock()
        node95 = Mock()
        node20 = Mock()
        nodes = { 4: node4, 64: node64, 13: node13, 65: node65, 6: node6, 95: node95, 20: node20 }
        hydrology = Mock()
        hydrology.node.side_effect = lambda nodeID: nodes[nodeID]

        self.assertTrue(hasRiver(83, vor, hydrology))
        self.assertFalse(hasRiver(93, vor, hydrology))
        self.assertTrue(hasRiver(78, vor, hydrology))
        self.assertFalse(hasRiver(40, vor, hydrology))
        self.assertTrue(hasRiver(20, vor, hydrology))
        self.assertFalse(hasRiver(32, vor, hydrology))

    def test_regularCell(self) -> None:
        edgeIDs = [78,40,20,32,83,93]

        nodeLoc = (102.7, -97.7)

        vor = Mock()
        ridge_points = { 83: [64,4], 93: [64,6], 78: [64,65], 40: [64,20], 20: [64,13], 32: [64,95] }
        vor.ridge_points = ridge_points
        ridge_vertices = { 83: [16, 57], 93: [57, 52], 78: [52, 46], 40: [46, 23], 20: [23, 31], 32: [31, 16] }
        vor.ridge_vertices = ridge_vertices
        # this shape is just a hexagon
        vertices = { 16: [61.4,-98.4], 57: [81.1,-127.2], 52: [122.0,-126.7], 46: [140.5,-97.6], 23: [119.1,-65.0], 31: [83.8,-63.9] }
        vor.vertices = vertices

        node4 = Mock()
        node64 = Mock()
        node64.parent = node4
        node13 = Mock()
        node13.parent = node64
        node65 = Mock()
        node65.parent = node64
        node6 = Mock()
        node95 = Mock()
        node20 = Mock()
        nodes = { 4: node4, 64: node64, 13: node13, 65: node65, 6: node6, 95: node95, 20: node20 }
        hydrology = Mock()
        hydrology.node.side_effect = lambda nodeID: nodes[nodeID]

        shore = Mock()
        shore.isOnLand.return_value = True

        createdEdges = { }
        createdQs = { }
        shoreQs = [ ]

        processedEdges = processRidge(edgeIDs, [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

        self.assertEqual(len(processedEdges), 6)
        self.assertEqual(processedEdges[0].Q0.position, vor.vertices[52])
        self.assertEqual(processedEdges[0].Q1, processedEdges[1].Q0)
        self.assertTrue(processedEdges[0].hasRiver)
        self.assertFalse(processedEdges[0].isShore)
        self.assertIsNone(processedEdges[0].shoreSegment)

        self.assertEqual(processedEdges[1].Q0.position, vor.vertices[46])
        self.assertEqual(processedEdges[1].Q1, processedEdges[2].Q0)
        self.assertFalse(processedEdges[1].hasRiver)
        self.assertFalse(processedEdges[1].isShore)
        self.assertIsNone(processedEdges[1].shoreSegment)

        self.assertEqual(processedEdges[2].Q0.position, vor.vertices[23])
        self.assertEqual(processedEdges[2].Q1, processedEdges[3].Q0)
        self.assertTrue(processedEdges[2].hasRiver)
        self.assertFalse(processedEdges[2].isShore)
        self.assertIsNone(processedEdges[2].shoreSegment)

        self.assertEqual(processedEdges[3].Q0.position, vor.vertices[31])
        self.assertEqual(processedEdges[3].Q1, processedEdges[4].Q0)
        self.assertFalse(processedEdges[3].hasRiver)
        self.assertIsNone(processedEdges[3].shoreSegment)

        self.assertFalse(processedEdges[4].isShore)
        self.assertIsNone(processedEdges[4].shoreSegment)
        self.assertEqual(processedEdges[4].Q0.position, vor.vertices[16])
        self.assertEqual(processedEdges[4].Q1, processedEdges[5].Q0)
        self.assertTrue(processedEdges[4].hasRiver)
        self.assertIsNone(processedEdges[4].shoreSegment)

        self.assertFalse(processedEdges[5].isShore)
        self.assertEqual(processedEdges[5].Q0.position, vor.vertices[57])
        self.assertEqual(processedEdges[5].Q1, processedEdges[0].Q0)
        self.assertFalse(processedEdges[5].hasRiver)
        self.assertFalse(processedEdges[5].isShore)
        self.assertIsNone(processedEdges[5].shoreSegment)
    def test_coastCell(self) -> None:
        edgeIDs = [32,83,93,78,40,20]

        nodeLoc = (102.7, -97.7)

        vor = Mock()
        ridge_points = { 83: [64,4], 93: [64,6], 78: [64,65], 40: [64,20], 20: [64,13], 32: [64,95] }
        vor.ridge_points = ridge_points
        ridge_vertices = { 83: [16, 57], 93: [57, 52], 78: [52, 46], 40: [46, 23], 20: [23, 31], 32: [31, 16] }
        vor.ridge_vertices = ridge_vertices
        # this shape is just a hexagon
        vertices = { 16: [61.4,-98.4], 57: [81.1,-127.2], 52: [122.0,-126.7], 46: [140.5,-97.6], 23: [119.1,-65.0], 31: [83.8,-63.9] }
        vor.vertices = vertices

        node4 = Mock()
        node64 = Mock()
        node64.parent = node4
        node13 = Mock()
        node13.parent = node64
        node65 = Mock()
        node65.parent = node64
        node6 = Mock()
        node95 = Mock()
        node20 = Mock()
        nodes = { 4: node4, 64: node64, 13: node13, 65: node65, 6: node6, 95: node95, 20: node20 }
        hydrology = Mock()
        hydrology.node.side_effect = lambda nodeID: nodes[nodeID]

        shore = Mock()
        # isOnLandDict = { vertices[31]: True, vertices[16]: False, vertices[57]: False, vertices[52]: True, vertices[46]: True, vertices[23]: True }
        shore.isOnLand.side_effect = lambda vertex : not vertex == vertices[16] and not vertex == vertices[57]
        shorePoints = { 18: (96.3,-181.2), 17: (107.2,-102.4), 16: (93.4,-88.0), 15: (22.1,-56.4) }
        shore.__getitem__ = Mock()
        shore.__getitem__.side_effect = lambda shoreIdx : shorePoints[shoreIdx]
        shore.__len__ = Mock(return_value=420)
        shore.closestNPoints.return_value = [ 15, 16, 17, 18 ]

        createdEdges = { }
        createdQs = { }
        shoreQs = [ ]

        intersection: Point = edgeIntersection(
            getVertex0(32, vor),
            getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.11, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.72, delta=1.0)

        processedEdges = processRidge(edgeIDs, [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

        self.assertEqual(len(processedEdges),8)

        self.assertEqual(processedEdges[0].Q0.position, vertices[31])
        self.assertAlmostEqual(processedEdges[0].Q1.position[0], 74.3, delta=1.0)
        self.assertAlmostEqual(processedEdges[0].Q1.position[1], -79.9, delta=1.0)

        self.assertEqual(processedEdges[1].Q0, processedEdges[0].Q1)
        self.assertEqual(processedEdges[1].Q1.position, shore[16])

        self.assertEqual(processedEdges[2].Q0, processedEdges[1].Q1)
        self.assertEqual(processedEdges[2].Q1.position, shore[17])

        self.assertEqual(processedEdges[3].Q0, processedEdges[2].Q1)
        self.assertAlmostEqual(processedEdges[3].Q1.position[0], 103.9, delta=1.0)
        self.assertAlmostEqual(processedEdges[3].Q1.position[1], -127.1, delta=1.0)

        self.assertEqual(processedEdges[4].Q0, processedEdges[3].Q1)
        self.assertEqual(processedEdges[4].Q1.position, vertices[52])

        self.assertEqual(processedEdges[5].Q0, processedEdges[4].Q1)
        self.assertEqual(processedEdges[5].Q1.position, vertices[46])

        self.assertEqual(processedEdges[6].Q0, processedEdges[5].Q1)
        self.assertEqual(processedEdges[6].Q1.position, vertices[23])

        self.assertEqual(processedEdges[7].Q0, processedEdges[6].Q1)
        self.assertEqual(processedEdges[7].Q1.position, vertices[31])

        self.assertEqual(processedEdges[0], createdEdges[32])
        self.assertEqual(processedEdges[4], createdEdges[93])
        self.assertEqual(processedEdges[5], createdEdges[78])
        self.assertEqual(processedEdges[6], createdEdges[40])
        self.assertEqual(processedEdges[7], createdEdges[20])

        self.assertEqual(processedEdges[0].Q0, createdQs[31])
        self.assertEqual(processedEdges[4].Q1, createdQs[52])
        self.assertEqual(processedEdges[5].Q1, createdQs[46])
        self.assertEqual(processedEdges[6].Q1, createdQs[23])
        self.assertEqual(processedEdges[7].Q1, createdQs[31])
    def test_coastCellWithEdgesCreated(self) -> None:
        edgeIDs = [32,83,93,78,40,20]

        nodeLoc = (102.7, -97.7)

        vor = Mock()
        ridge_points = { 83: [64,4], 93: [64,6], 78: [64,65], 40: [64,20], 20: [64,13], 32: [64,95] }
        vor.ridge_points = ridge_points
        ridge_vertices = { 83: [16, 57], 93: [57, 52], 78: [52, 46], 40: [46, 23], 20: [23, 31], 32: [31, 16] }
        vor.ridge_vertices = ridge_vertices
        # this shape is just a hexagon
        vertices = { 16: [61.4,-98.4], 57: [81.1,-127.2], 52: [122.0,-126.7], 46: [140.5,-97.6], 23: [119.1,-65.0], 31: [83.8,-63.9] }
        vor.vertices = vertices

        node4 = Mock()
        node64 = Mock()
        node64.parent = node4
        node13 = Mock()
        node13.parent = node64
        node65 = Mock()
        node65.parent = node64
        node6 = Mock()
        node95 = Mock()
        node20 = Mock()
        nodes = { 4: node4, 64: node64, 13: node13, 65: node65, 6: node6, 95: node95, 20: node20 }
        hydrology = Mock()
        hydrology.node.side_effect = lambda nodeID: nodes[nodeID]

        shore = Mock()
        # isOnLandDict = { vertices[31]: True, vertices[16]: False, vertices[57]: False, vertices[52]: True, vertices[46]: True, vertices[23]: True }
        shore.isOnLand.side_effect = lambda vertex : not vertex == vertices[16] and not vertex == vertices[57]
        shorePoints = { 18: (96.3,-181.2), 17: (107.2,-102.4), 16: (93.4,-88.0), 15: (22.1,-56.4) }
        shore.__getitem__ = Mock()
        shore.__getitem__.side_effect = lambda shoreIdx : shorePoints[shoreIdx]
        shore.__len__ = Mock(return_value=420)
        shore.closestNPoints.return_value = [ 15, 16, 17, 18 ]

        q52 = Q(vertices[52])
        q23 = Q(vertices[23])
        q31 = Q(vertices[31])
        createdQs = {
            52: q52,
            23: q23,
            31: q31
        }
        # declare these separately to test whether or not the function overwrites them
        # in the dictionary
        edge93 = Edge(Q((103.9,-127.1)), createdQs[52], hasRiver=False, isShore=False, shoreSegment=(17,18))
        edge20 = Edge(createdQs[23], createdQs[31], hasRiver=False, isShore=False)
        createdEdges = {
            93: edge93,
            20: edge20
        }
        shoreQs = [ ]

        intersection: Point = edgeIntersection(
            getVertex0(32, vor),
            getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.11, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.72, delta=1.0)

        processedEdges = processRidge(edgeIDs, [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

        self.assertEqual(len(processedEdges),8)

        self.assertEqual(processedEdges[0].Q0.position, vertices[31])
        self.assertAlmostEqual(processedEdges[0].Q1.position[0], 74.3, delta=1.0)
        self.assertAlmostEqual(processedEdges[0].Q1.position[1], -79.9, delta=1.0)

        self.assertEqual(processedEdges[1].Q0, processedEdges[0].Q1)
        self.assertEqual(processedEdges[1].Q1.position, shore[16])

        self.assertEqual(processedEdges[2].Q0, processedEdges[1].Q1)
        self.assertEqual(processedEdges[2].Q1.position, shore[17])

        self.assertEqual(processedEdges[3].Q0, processedEdges[2].Q1)
        self.assertAlmostEqual(processedEdges[3].Q1.position[0], 103.9, delta=1.0)
        self.assertAlmostEqual(processedEdges[3].Q1.position[1], -127.1, delta=1.0)

        self.assertEqual(processedEdges[4].Q0, processedEdges[3].Q1)
        self.assertEqual(processedEdges[4].Q1.position, vertices[52])

        self.assertEqual(processedEdges[5].Q0, processedEdges[4].Q1)
        self.assertEqual(processedEdges[5].Q1.position, vertices[46])

        self.assertEqual(processedEdges[6].Q0, processedEdges[5].Q1)
        self.assertEqual(processedEdges[6].Q1.position, vertices[23])

        self.assertEqual(processedEdges[7].Q0, processedEdges[6].Q1)
        self.assertEqual(processedEdges[7].Q1.position, vertices[31])

        self.assertEqual(processedEdges[0], createdEdges[32])
        self.assertEqual(processedEdges[4], createdEdges[93])
        self.assertEqual(processedEdges[5], createdEdges[78])
        self.assertEqual(processedEdges[6], createdEdges[40])
        self.assertEqual(processedEdges[7], createdEdges[20])

        self.assertEqual(processedEdges[0].Q0, createdQs[31])
        self.assertEqual(processedEdges[4].Q1, createdQs[52])
        self.assertEqual(processedEdges[5].Q1, createdQs[46])
        self.assertEqual(processedEdges[6].Q1, createdQs[23])
        self.assertEqual(processedEdges[7].Q1, createdQs[31])

        self.assertEqual(createdEdges[93], edge93)
        self.assertEqual(createdEdges[20], edge20)

        self.assertEqual(createdQs[52], q52)
        self.assertEqual(createdQs[23], q23)
        self.assertEqual(createdQs[31], q31)
    def test_coastCellOneSegment(self) -> None:
        edgeIDs = [32,83,93,78,40,20]

        nodeLoc = (102.7, -97.7)

        vor = Mock()
        ridge_points = { 83: [64,4], 93: [64,6], 78: [64,65], 40: [64,20], 20: [64,13], 32: [64,95] }
        vor.ridge_points = ridge_points
        ridge_vertices = { 83: [16, 57], 93: [57, 52], 78: [52, 46], 40: [46, 23], 20: [23, 31], 32: [31, 16] }
        vor.ridge_vertices = ridge_vertices
        # this shape is just a hexagon
        vertices = { 16: [61.4,-98.4], 57: [81.1,-127.2], 52: [122.0,-126.7], 46: [140.5,-97.6], 23: [119.1,-65.0], 31: [83.8,-63.9] }
        vor.vertices = vertices

        node4 = Mock()
        node64 = Mock()
        node64.parent = node4
        node13 = Mock()
        node13.parent = node64
        node65 = Mock()
        node65.parent = node64
        node6 = Mock()
        node95 = Mock()
        node20 = Mock()
        nodes = { 4: node4, 64: node64, 13: node13, 65: node65, 6: node6, 95: node95, 20: node20 }
        hydrology = Mock()
        hydrology.node.side_effect = lambda nodeID: nodes[nodeID]

        shore = Mock()
        # isOnLandDict = { vertices[31]: True, vertices[16]: False, vertices[57]: False, vertices[52]: True, vertices[46]: True, vertices[23]: True }
        shore.isOnLand.side_effect = lambda vertex : not vertex == vertices[16] and not vertex == vertices[57]
        shorePoints = { 15: (56.1,-49.1), 16: (130.3,-173.9) }
        shore.__getitem__ = Mock()
        shore.__getitem__.side_effect = lambda shoreIdx : shorePoints[shoreIdx]
        shore.__len__ = Mock(return_value=420)
        shore.closestNPoints.return_value = [ 15, 16 ] # This is technically wrong, but it's fine

        createdQs = { }
        createdEdges = { }
        shoreQs = [ ]

        intersection: Point = edgeIntersection(
            getVertex0(32, vor),
            getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.2, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.7, delta=1.0)

        processedEdges = processRidge(edgeIDs, [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

        self.assertEqual(len(processedEdges),6)

        self.assertEqual(processedEdges[0].Q0.position, vertices[31])
        self.assertAlmostEqual(processedEdges[0].Q1.position[0], 74.2, delta=1.0)
        self.assertAlmostEqual(processedEdges[0].Q1.position[1], -79.7, delta=1.0)

        self.assertEqual(processedEdges[1].Q0, processedEdges[0].Q1)
        self.assertAlmostEqual(processedEdges[1].Q1.position[0], 102.4, delta=1.0)
        self.assertAlmostEqual(processedEdges[1].Q1.position[1], -127.7, delta=1.0)

        self.assertEqual(processedEdges[2].Q0, processedEdges[1].Q1)
        self.assertEqual(processedEdges[2].Q1.position, vertices[52])

        self.assertEqual(processedEdges[3].Q0, processedEdges[2].Q1)
        self.assertEqual(processedEdges[3].Q1.position, vertices[46])

        self.assertEqual(processedEdges[4].Q0, processedEdges[3].Q1)
        self.assertEqual(processedEdges[4].Q1.position, vertices[23])

        self.assertEqual(processedEdges[5].Q0, processedEdges[4].Q1)
        self.assertEqual(processedEdges[5].Q1.position, vertices[31])

        self.assertEqual(processedEdges[0], createdEdges[32])
        self.assertEqual(processedEdges[2], createdEdges[93])
        self.assertEqual(processedEdges[3], createdEdges[78])
        self.assertEqual(processedEdges[4], createdEdges[40])
        self.assertEqual(processedEdges[5], createdEdges[20])

        self.assertEqual(processedEdges[0].Q0, createdQs[31])
        self.assertEqual(processedEdges[2].Q1, createdQs[52])
        self.assertEqual(processedEdges[3].Q1, createdQs[46])
        self.assertEqual(processedEdges[4].Q1, createdQs[23])
        self.assertEqual(processedEdges[5].Q1, createdQs[31])

    def test_many_cells(self) -> None:
        with shapefile.Writer('inputShape', shapeType=5) as shp:
            #         0                 1              2                  3                 4             5           (beginning)
            shape = [(-4623.8,6201.5), (-9299.9,0.0), (-4629.4,-8124.4), (4751.4,-8114.7), (9417.8,0.0), (4741,6209), (-4623.8,6201.5) ]
            shape.reverse() # pyshp expects shapes to be clockwise

            shp.field('name', 'C')

            shp.poly([ shape ])
            shp.record('polygon0')
        shore = ShoreModel(inputFileName='inputShape')
        os.remove('inputShape.shp')
        os.remove('inputShape.dbf')
        os.remove('inputShape.shx')

        self.assertFalse(shore.isOnLand((-24954,17780)))
        self.assertTrue(shore.isOnLand((-6591,1545)))
        self.assertFalse(shore.isOnLand((-7144.4,-5165.1)))

        hydrology = HydrologyNetwork()

        hydrology.addNode((-7768.799999999999, 2059.2), 0, 2, contourIndex=44) # ID: 0
        hydrology.addNode((-8049.599999999999, -2246.3999999999996), 0, 1, contourIndex=90) # ID: 1
        hydrology.addNode((-5054.4, -7394.4), 0, 1, contourIndex=145) # ID: 2
        hydrology.addNode((1123.1999999999998, -8049.599999999999), 0, 1, contourIndex=214) # ID: 3
        hydrology.addNode((4305.599999999999, -8049.599999999999), 0, 1, contourIndex=248) # ID: 4
        hydrology.addNode((6458.4, -5054.4), 0, 1, contourIndex=284) # ID: 5
        hydrology.addNode((8049.599999999999, 1684.8), 0, 1, contourIndex=356) # ID: 6
        hydrology.addNode((6832.799999999999, 3369.6), 0, 1, contourIndex=374) # ID: 7
        hydrology.addNode((280.79999999999995, 6177.599999999999), 0, 2, contourIndex=451) # ID: 8
        hydrology.addNode((-4867.2, 5990.4), 0, 1, contourIndex=2) # ID: 9
        hydrology.addNode((-6246.780372888135, 307.5788923724788), 173.81, 2, parent=hydrology.node(0)) # ID: 10
        hydrology.addNode((-5449.5362946522855, 2134.9371444985295), 173.81, 1, parent=hydrology.node(0)) # ID: 11
        hydrology.addNode((-5738.2285044404125, -2452.02601857411), 173.81, 1, parent=hydrology.node(1)) # ID: 12
        hydrology.addNode((-3779.8747892700185, -5455.249222671507), 173.81, 1, parent=hydrology.node(2)) # ID: 13
        hydrology.addNode((1735.4047436340666, -5811.313690817918), 173.81, 1, parent=hydrology.node(3)) # ID: 14
        hydrology.addNode((3913.3561082532797, -5762.491568073916), 173.81, 1, parent=hydrology.node(4)) # ID: 15
        hydrology.addNode((4575.801759157646, -3697.733455274554), 173.81, 1, parent=hydrology.node(5)) # ID: 16
        hydrology.addNode((6588.2148673450665, -117.71872224815615), 173.81, 1, parent=hydrology.node(6)) # ID: 17
        hydrology.addNode((4551.139609616782, 2946.8162338070397), 173.81, 1, parent=hydrology.node(7)) # ID: 18
        hydrology.addNode((1686.515368282502, 4331.337680237612), 173.81, 1, parent=hydrology.node(8)) # ID: 19
        hydrology.addNode((-267.90201010200553, 3922.9057071722514), 173.81, 1, parent=hydrology.node(8)) # ID: 20
        hydrology.addNode((-3628.3824225111284, 4028.245250826377), 173.81, 1, parent=hydrology.node(9)) # ID: 21
        hydrology.addNode((-3981.7104458665694, 811.7400528187368), 347.62, 1, parent=hydrology.node(10)) # ID: 22
        hydrology.addNode((-4397.990228017062, -1094.8102298855324), 347.62, 1, parent=hydrology.node(10)) # ID: 23
        hydrology.addNode((-3139.1312650010427, 2351.151965827316), 347.62, 1, parent=hydrology.node(11)) # ID: 24
        hydrology.addNode((-3652.2156918437145, -3468.52530321843), 347.62, 1, parent=hydrology.node(12)) # ID: 25
        hydrology.addNode((-1636.5946626095852, -4565.8277541525395), 347.62, 1, parent=hydrology.node(13)) # ID: 26
        hydrology.addNode((1544.4836554558808, -3498.6811242200897), 347.62, 1, parent=hydrology.node(14)) # ID: 27
        hydrology.addNode((4066.8172916595668, -1433.742496404423), 347.62, 1, parent=hydrology.node(16)) # ID: 28
        hydrology.addNode((4397.765121188957, 648.2121881900088), 347.62, 1, parent=hydrology.node(17)) # ID: 29
        hydrology.addNode((2306.434717613504, 2358.5814186043426), 347.62, 1, parent=hydrology.node(18)) # ID: 30
        hydrology.addNode((-1017.1741446275356, 1726.701818999854), 347.62, 1, parent=hydrology.node(20)) # ID: 31
        hydrology.addNode((-2307.913817105099, -795.4702929502098), 521.4300000000001, 1, parent=hydrology.node(22)) # ID: 32
        hydrology.addNode((-1496.566016258495, -2609.517313645959), 521.4300000000001, 1, parent=hydrology.node(25)) # ID: 33
        hydrology.addNode((1363.0351974719795, -1185.2860634716526), 521.4300000000001, 1, parent=hydrology.node(27)) # ID: 34
        hydrology.addNode((2670.0365109674985, 419.2884533342087), 521.4300000000001, 1, parent=hydrology.node(28)) # ID: 35
        hydrology.addNode((707.4833463640621, 676.8933493181478), 521.4300000000001, 1, parent=hydrology.node(30)) # ID: 36

        vor = Mock()
        vor.vertices = [ [-46506.08407643312, -9.094947017729282e-13], [2.6147972675971687e-12, 44226.7005988024], [46543.64331210191, -2.5011104298755527e-12], [5.9117155615240335e-12, -46570.47133757962], [-3525.521902377971, 39972.85231539425], [13558.459960328704, 28110.80657410031], [26619.009606328877, 16377.840271237523], [-26698.104702750665, -16541.770008873114], [-5342.427753303965, -39560.66167400881], [35441.20183078683, -8340.111543380222], [-43498.34278442353, 2227.431051158057], [-24953.50872483222, 17779.580249280923], [5109.0255814912725, 8395.459690146301], [-1996.7447595539256, -8015.650590079869], [2714.3999999999996, -43216.37197452229], [23612.9992884097, -19655.530738544476], [11641.06983801728, -2720.635933976302], [5208.635601476787, -547.9650058651541], [6239.082845541137, 1659.004277335266], [5986.536369278422, 1676.7167717523037], [543.7155555507849, 4919.503757045385], [-6680.865690904744, 4292.62943852493], [2628.517404889034, -2249.842814561697], [-1696.5804304393203, -7448.368722268813], [3110.058763294175, -2838.0481729036733], [6058.009213215691, -2175.2977391683517], [6801.766437182614, -2593.381713240389], [4914.451075025957, 7354.28618418668], [5962.499774105598, 1698.2241612392727], [-1737.0018899900447, 3198.198620213414], [-5633.518041727106, 4134.436097778672], [-4356.371628548453, 2905.9619113121926], [-1959.7548342358916, 3605.116544637308], [-2298.865028087399, 6239.788272403492], [-1899.9120949673852, 5514.184556143233], [-4268.698468751132, 1969.1135115758668], [-2399.7332856176777, 946.1571866549236], [-7144.421744184177, -5165.081742070794], [-6474.766974314268, -5072.428085853662], [-6591.153478267191, 1545.413655907815], [-5811.891997043897, -1038.939525126176], [-5198.408619217473, 937.7837124750154], [-4997.4197777103145, 34.791145253456364], [-8437.747093365531, -59.129537389204245], [-6793.440632041436, -1219.8235314997867], [-2914.5426686927153, -4513.388678872556], [-5375.002315597173, -4355.289179137266], [-4425.902874448049, -2407.591207703676], [3011.7878956964087, -4334.590606933651], [5534.547354333574, -6661.643410927256], [5070.911181167803, -4995.22841079101], [3638.270932588358, 1853.3084656616168], [3152.2050915292384, 3708.1364069236884], [942.0084255460736, 3013.6037341770443], [576.1703235384243, 2402.732591397016], [574.891904979788, 2409.4569155464214], [-2378.928797097079, -3529.5263151107347], [203.50001261420107, -2440.0462406337037], [-161.45820480964403, -3688.2482638015335], [2796.866017821202, -4559.486873042995], [-408.331712981741, -6427.83647054344], [202.65938098626384, -4773.653516381512], [2714.3999999999996, -7281.950244970516], [2854.2932737297983, -7121.312605780729], [1781.7422398560416, 1256.4731251250837], [3397.988338982509, 1559.506235989755], [1610.0097690595885, -51.86421349350661], [3644.2791292781067, -299.29466596039265], [2745.5022729159978, -976.7761938725419], [-3198.719658880232, -2022.0344053429003], [-2924.745798906439, -2159.8181666861387], [-3444.7439420729106, -304.2230231495334], [-2361.878510549001, 823.5052256503409], [-854.634656375734, 52.16237023542806], [-449.7788363341592, -776.981365945501], [-480.5358806262716, -1066.624705116723] ]
        vor.ridge_vertices = [ [-1, 2], [1, 5], [-1, 1], [2, 6], [5, 6], [-1, 3], [0, 7], [-1, 0], [3, 8], [7, 8], [0, 10], [1, 4], [4, 11], [10, 11], [2, 9], [3, 14], [9, 15], [14, 15], [9, 16], [6, 18], [16, 18], [16, 26], [17, 19], [18, 19], [17, 25], [25, 26], [5, 12], [12, 27], [19, 28], [27, 28], [30, 31], [30, 33], [31, 32], [32, 34], [33, 34], [11, 21], [4, 33], [21, 30], [12, 20], [20, 34], [29, 32], [31, 35], [29, 36], [35, 36], [7, 37], [8, 13], [13, 38], [37, 38], [39, 41], [39, 43], [40, 44], [40, 42], [41, 42], [43, 44], [21, 39], [35, 41], [10, 43], [37, 44], [38, 46], [13, 23], [23, 45], [45, 46], [40, 47], [46, 47], [24, 48], [24, 25], [26, 50], [48, 50], [15, 49], [49, 50], [27, 52], [28, 51], [51, 52], [20, 53], [52, 53], [29, 55], [53, 55], [59, 63], [59, 61], [60, 61], [60, 62], [62, 63], [48, 59], [49, 63], [22, 57], [22, 24], [57, 58], [58, 61], [23, 60], [56, 58], [45, 56], [14, 62], [64, 65], [64, 66], [65, 67], [66, 68], [67, 68], [54, 55], [51, 65], [54, 64], [17, 67], [22, 68], [69, 70], [69, 71], [70, 75], [71, 72], [72, 73], [73, 74], [74, 75], [47, 69], [56, 70], [42, 71], [57, 75], [36, 72], [54, 73], [66, 74] ]
        vor.ridge_points = [ [39, 40], [39, 8], [39, 38], [39, 6], [39, 7], [37, 40], [37, 1], [37, 38], [37, 3], [37, 2], [38, 1], [38, 8], [38, 9], [38, 0], [40, 6], [40, 3], [40, 5], [40, 4], [6, 5], [6, 7], [6, 17], [17, 5], [17, 29], [17, 7], [17, 28], [17, 16], [7, 8], [7, 19], [7, 29], [7, 18], [21, 11], [21, 9], [21, 24], [21, 20], [21, 8], [9, 0], [9, 8], [9, 11], [8, 19], [8, 20], [24, 20], [24, 11], [24, 31], [24, 22], [2, 1], [2, 3], [2, 13], [2, 12], [10, 11], [10, 0], [10, 12], [10, 23], [10, 22], [10, 1], [11, 0], [11, 22], [0, 1], [1, 12], [13, 12], [13, 3], [13, 26], [13, 25], [12, 23], [12, 25], [16, 27], [16, 28], [16, 5], [16, 15], [5, 4], [5, 15], [18, 19], [18, 29], [18, 30], [19, 20], [19, 30], [20, 31], [20, 30], [14, 15], [14, 27], [14, 26], [14, 3], [14, 4], [15, 27], [15, 4], [27, 34], [27, 28], [27, 33], [27, 26], [26, 3], [26, 33], [26, 25], [3, 4], [35, 30], [35, 36], [35, 29], [35, 34], [35, 28], [30, 31], [30, 29], [30, 36], [29, 28], [28, 34], [32, 25], [32, 23], [32, 33], [32, 22], [32, 31], [32, 36], [32, 34], [25, 23], [25, 33], [23, 22], [33, 34], [22, 31], [31, 36], [36, 34] ]

        point_ridges: Dict[int, List[int]] = ridgesToPoints(vor)

        createdQs: Dict[int, Q] = { }
        createdEdges: Dict[int, Edge] = { }
        shoreQs: List[Q] = [ ]

        cells = { }
        for node in hydrology.allNodes():
            # order the cell edges in counterclockwise order
            point_ridges[node.id] = orderEdges(point_ridges[node.id], node.position, vor, shore)
            orderCreatedEdges(point_ridges[node.id], vor, createdEdges)

            # then we have to organize and set up all the edges of the cell
            cells[node.id] = processRidge(point_ridges[node.id], [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

        self.assertEqual(5, len(cells[35]))
        self.assertTrue(createdEdges[92] in cells[35])
        self.assertTrue(createdQs[65] == createdEdges[92].Q0 or createdQs[65] == createdEdges[92].Q1)
        self.assertTrue(createdQs[64] == createdEdges[92].Q0 or createdQs[64] == createdEdges[92].Q1)
        self.assertFalse(createdEdges[92].hasRiver)
        self.assertTrue(createdEdges[93] in cells[35])
        self.assertTrue(createdQs[64] == createdEdges[93].Q0 or createdQs[64] == createdEdges[93].Q1)
        self.assertTrue(createdQs[66] == createdEdges[93].Q0 or createdQs[66] == createdEdges[93].Q1)
        self.assertFalse(createdEdges[93].hasRiver)
        self.assertTrue(createdEdges[95] in cells[35])
        self.assertTrue(createdQs[66] == createdEdges[95].Q0 or createdQs[66] == createdEdges[95].Q1)
        self.assertTrue(createdQs[68] == createdEdges[95].Q0 or createdQs[68] == createdEdges[95].Q1)
        self.assertFalse(createdEdges[95].hasRiver)
        self.assertTrue(createdEdges[96] in cells[35])
        self.assertTrue(createdQs[68] == createdEdges[96].Q0 or createdQs[68] == createdEdges[96].Q1)
        self.assertTrue(createdQs[67] == createdEdges[96].Q0 or createdQs[67] == createdEdges[96].Q1)
        self.assertTrue(createdEdges[96].hasRiver)
        self.assertTrue(createdEdges[94] in cells[35])
        self.assertTrue(createdQs[67] == createdEdges[94].Q0 or createdQs[67] == createdEdges[94].Q1)
        self.assertTrue(createdQs[65] == createdEdges[94].Q0 or createdQs[65] == createdEdges[94].Q1)
        self.assertFalse(createdEdges[94].hasRiver)

        self.assertEqual(5, len(cells[7]))
        self.assertTrue(createdEdges[29] in cells[7])
        self.assertTrue(createdEdges[28] in cells[7])
        self.assertTrue(createdEdges[23] in cells[7])
        self.assertTrue(createdEdges[19] in cells[7])

        self.assertEqual(6, len(cells[3]))
        self.assertTrue(createdEdges[45] in cells[3])
        self.assertTrue(createdEdges[59] in cells[3])
        self.assertTrue(createdEdges[88] in cells[3])
        self.assertTrue(createdEdges[80] in cells[3])
        self.assertTrue(createdEdges[91] in cells[3])
        self.assertEqual(1, len([edge for edge in cells[3] if edge.isShore]))
        shoreEdge: Edge = [edge for edge in cells[3] if edge.isShore][0]
        self.assertEqual((2,3), shoreEdge.shoreSegment)

        self.assertEqual(4, len(cells[1]))
        self.assertTrue(createdEdges[57] in cells[1])
        self.assertTrue(createdEdges[53] in cells[1])
        self.assertTrue(createdEdges[56] in cells[1])
        self.assertEqual(1, len([edge for edge in cells[1] if edge.isShore]))
        shoreEdge: Edge = [edge for edge in cells[1] if edge.isShore][0]
        self.assertEqual((1,2), shoreEdge.shoreSegment)

        self.assertEqual(4, len(cells[6]))
        self.assertTrue(createdEdges[19] in cells[6])
        self.assertTrue(createdEdges[20] in cells[6])
        self.assertEqual(2, len([edge for edge in cells[6] if edge.isShore]))
        shoreEdge: Edge = [edge for edge in cells[6] if edge.isShore][0]
        self.assertEqual((3,4), shoreEdge.shoreSegment)
        shoreEdge = [edge for edge in cells[6] if edge.isShore][1]
        self.assertEqual((4,5), shoreEdge.shoreSegment)

    def test_findShoreSegment0(self) -> None:
        mockShore = Mock()
        mockShore.__getitem__ = Mock()
        mockShore.__getitem__.side_effect = lambda index : [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8] ][index]
        mockShore.__len__ = Mock()
        mockShore.__len__.return_value = 9
        mockShore.closestNPoints.return_value = [2, 3, 4, 5]

        p0 = (80,-185)
        p1 = (80,-200)
        segment = findIntersectingShoreSegment(p0, p1, mockShore)

        self.assertEqual(2, segment[0])
        self.assertEqual(3, segment[1])
    def test_findShoreSegment1(self) -> None:
        mockShore = Mock()
        mockShore.__getitem__ = Mock()
        mockShore.__getitem__.side_effect = lambda index : [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8] ][index]
        mockShore.__len__ = Mock()
        mockShore.__len__.return_value = 9
        mockShore.closestNPoints.return_value = [4, 2, 3, 1]

        p0 = (67,-150)
        p1 = (30,-160)
        segment = findIntersectingShoreSegment(p0, p1, mockShore)

        self.assertEqual(1, segment[0])
        self.assertEqual(2, segment[1])
    def test_findShoreSegment2(self) -> None:
        mockShore = Mock()
        mockShore.__getitem__ = Mock()
        mockShore.__getitem__.side_effect = lambda index : [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8] ][index]
        mockShore.__len__ = Mock()
        mockShore.__len__.return_value = 9
        mockShore.closestNPoints.side_effect = [ [4, 2, 3, 1], [4, 2, 3, 1, 5, 6, 7, 8, 0, 9, 9, 9, 9, 9, 9, 9] ]

        p0 = (67,-150)
        p1 = (0,100)
        segment = findIntersectingShoreSegment(p0, p1, mockShore)

        self.assertEqual(7, segment[0])
        self.assertEqual(8, segment[1])

    def tearDown(self) -> None:
        pass

class RiverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.edgeLength, self.shore, self.hydrology, self.cells = getPredefinedObjects0()
    
    def test_test(self) -> None:
        node = self.hydrology.node(3)
        node.rivers = [ ]

        computeRivers(node, self.hydrology, self.cells)

        # ensure that the river does not intersect any of the mountain ridges of any cells that it flows through
        allRidges = self.cells.cellRidges(3)
        allRidges += self.cells.cellRidges(14)
        allRidges += self.cells.cellRidges(27)
        allRidges += self.cells.cellRidges(34)

        self.assertEqual(1, len(node.rivers))

        river = list(node.rivers[0].coords)
        for i in range(len(river)-2):
            p0 = river[i]
            p1 = river[i+1]
            for ridge in allRidges:
                self.assertFalse(segments_intersect_tuple(p0, p1, ridge[0].position, ridge[1].position))
    
    def test_always_rising(self) -> None:
        node = self.hydrology.node(3)
        node.rivers = [ ]

        computeRivers(node, self.hydrology, self.cells)

        river = list(node.rivers[0].coords)
        
        prevPoint = river[0]
        for point in river[1:]:
            self.assertTrue(prevPoint[2] > point[2])
            prevPoint = point

    def tearDown(self) -> None:
        pass

class TerrainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.edgeLength, self.shore, self.hydrology, self.cells = getPredefinedObjects0()

    def test_test(self) -> None:
        t = T((1909,-766), 34)

        z = computePrimitiveElevation(t, self.shore, self.hydrology, self.cells)
        
        self.assertAlmostEqual(z, 1140, delta=10.0)

    def tearDown(self) -> None:
        pass

class SaveFileShoreLoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shape = [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8], [0,-437] ]

        self.db = lib.SaveFile.createDB(':memory:', 2000, 2000, 0, 0)
        with self.db:
            self.db.executemany('INSERT INTO Shoreline VALUES (?, MakePoint(?, ?, 347895))', [ (idx, x, y) for idx, (x,y) in enumerate(self.shape) ])

        self.shore = ShoreModel()
        self.shore.loadFromDB(self.db)
    
    def test_loadLength0(self) -> None:
        self.assertEqual(len(self.shape), len(self.shore))
    
    def tearDown(self) -> None:
        self.db.close()

class SaveFileShoreSaveTests(unittest.TestCase):
    def setUp(self) -> None:
        shpBuf = io.BytesIO()
        shxBuf = io.BytesIO()
        dbfBuf = io.BytesIO()

        with shapefile.Writer(shp=shpBuf, shx=shxBuf, dbf=dbfBuf, shapeType=5) as shp:
            #         0         1          2          3          4          5           6         7        8         (beginning)
            shape = [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8], [0,-437] ]
            shape.reverse() # pyshp expects shapes to be clockwise

            shp.field('name', 'C')

            shp.poly([ shape ])
            shp.record('polygon0')

        self.shore = ShoreModel(shpFile=shpBuf, shxFile=shxBuf, dbfFile=dbfBuf)

        self.db = lib.SaveFile.createDB(':memory:', 2000, 2000, 0, 0)
        self.shore.saveToDB(self.db)

    def test_save0(self) -> None:
        with self.db:
            rowCount = self.db.execute('SELECT COUNT(*) FROM Shoreline').fetchone()[0]
            self.assertEqual(len(self.shore), rowCount)
    
    def tearDown(self) -> None:
        self.db.close()

class SaveFileHydrologyLoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = lib.SaveFile.createDB(':memory:', 2000, 2000, 0, 0)
        with self.db:
            self.db.execute('INSERT INTO RiverNodes VALUES (0, NULL,  0,  0, 30, 32, NULL, MakePoint(0, 0, 347895))')
            self.db.execute('INSERT INTO RiverNodes VALUES (1,    0, 10, 10, 10, 16, NULL, MakePoint(0, 0, 347895))')
            self.db.execute('INSERT INTO RiverNodes VALUES (2,    0, 12, 10, 10, 16, NULL, MakePoint(0, 0, 347895))')
        
        self.hydrology = HydrologyNetwork(self.db)

    def test_load0(self) -> None:
        self.assertEqual(3, len(self.hydrology))
        
        self.assertEqual(0, self.hydrology.node(2).parent.id)
        self.assertEqual(0, self.hydrology.node(1).parent.id)

    def tearDown(self) -> None:
        self.db.close()

class SaveFileHydrologySaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hydrology = HydrologyNetwork()

        node0 = self.hydrology.addNode((0, 0), 0, 0)
        node1 = self.hydrology.addNode((0, 0), 10, 0, parent=node0)
        node2 = self.hydrology.addNode((0, 0), 12, 0, parent=node0)

        node0.localWatershed = 10
        node1.localWatershed = 10
        node2.localWatershed = 10
        node0.inheritedWatershed = 30
        node1.inheritedWatershed = 10
        node2.inheritedWatershed = 10
        node0.flow = 32
        node1.flow = 16
        node2.flow = 16

        self.db = lib.SaveFile.createDB(':memory:', 2000, 2000, 0, 0)
        self.hydrology.saveToDB(self.db)

    def test_save0(self) -> None:
        with self.db:
            rowCount = self.db.execute('SELECT COUNT(*) FROM RiverNodes').fetchone()[0]
            self.assertEqual(len(self.hydrology), rowCount)
    
    def tearDown(self) -> None:
        self.db.close()

class SaveFileHoneycombLoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = lib.SaveFile.createDB(':memory:', 2000, 2000, 0, 0)
        with self.db:
            self.db.execute('INSERT INTO RiverNodes VALUES (0, NULL,  0,  0, 30, 32, NULL, MakePoint(0, 0, 347895))')
            self.db.execute('INSERT INTO RiverNodes VALUES (1,    0, 10, 10, 10, 16, NULL, MakePoint(1850, 500, 347895))')
            self.db.execute('INSERT INTO RiverNodes VALUES (2,    0, 12, 10, 10, 16, NULL, MakePoint(700, 1750, 347895))')

            self.db.execute('INSERT INTO Qs VALUES (0, 50, MakePoint(750, 750, 347895))')
            self.db.execute('INSERT INTO Qs VALUES (1, 50, MakePoint(-250, 1250, 347895))')
            self.db.execute('INSERT INTO Qs VALUES (2, 50, MakePoint(1000, -250, 347895))')
            self.db.execute('INSERT INTO Qs VALUES (3, 50, MakePoint(1750, 1750, 347895))')

            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (0, 0, 2)')
            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (0, 1, 0)')
            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (0, 2, 1)')
            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (1, 0, 3)')
            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (1, 1, 0)')
            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (1, 2, 2)')
            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (2, 0, 1)')
            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (2, 1, 0)')
            self.db.execute('INSERT INTO Cells (rivernode, polygonorder, q) VALUES (2, 2, 3)')

            self.db.execute('INSERT INTO Edges VALUES (0, 2, 0, 1, 0, NULL, NULL)')
            self.db.execute('INSERT INTO Edges VALUES (1, 0, 1, 1, 0, NULL, NULL)')
            self.db.execute('INSERT INTO Edges VALUES (2, 3, 0, 1, 0, NULL, NULL)')

        shore = Mock()
        hydrology = Mock()

        self.cells = TerrainHoneycomb()
        self.cells.loadFromDB(self.db)

    def test_load0(self) -> None:
        vertices = self.cells.cellVertices(0)
        
        # cellVertices() will no longer find all of the vertices for this
        # test because the edges in this test data do not form a closed
        # polygon.  This is not a problem for the actual application
        # because edges generated by the program will always form a
        # closed polygon.
        self.assertEqual(2, len(vertices))
        self.assertTrue((750, 750) in vertices)
        self.assertTrue((1000, -250) in vertices)
        # self.assertTrue((-250, 1250) in vertices)
        self.assertTrue((1750, 1750) not in vertices)

    def tearDown(self) -> None:
        self.db.close()

class SaveFileHoneycombSaveTests(unittest.TestCase):
    def setUp(self) -> None:
        shpBuf = io.BytesIO()
        shxBuf = io.BytesIO()
        dbfBuf = io.BytesIO()

        with shapefile.Writer(shp=shpBuf, shx=shxBuf, dbf=dbfBuf, shapeType=5) as shp:
            #         0                 1              2                  3                 4             5           (beginning)
            shape = [(-4623.8,6201.5), (-9299.9,0.0), (-4629.4,-8124.4), (4751.4,-8114.7), (9417.8,0.0), (4741,6209), (-4623.8,6201.5) ]
            shape.reverse() # pyshp expects shapes to be clockwise

            shp.field('name', 'C')

            shp.poly([ shape ])
            shp.record('polygon0')
        self.shore = ShoreModel(shpFile=shpBuf, dbfFile=dbfBuf, shxFile=shxBuf)

        self.hydrology = HydrologyNetwork()

        self.hydrology.addNode((-7768.799999999999, 2059.2), 0, 2, contourIndex=44) # ID: 0
        self.hydrology.addNode((-8049.599999999999, -2246.3999999999996), 0, 1, contourIndex=90) # ID: 1
        self.hydrology.addNode((-5054.4, -7394.4), 0, 1, contourIndex=145) # ID: 2
        self.hydrology.addNode((1123.1999999999998, -8049.599999999999), 0, 1, contourIndex=214) # ID: 3
        self.hydrology.addNode((4305.599999999999, -8049.599999999999), 0, 1, contourIndex=248) # ID: 4
        self.hydrology.addNode((6458.4, -5054.4), 0, 1, contourIndex=284) # ID: 5
        self.hydrology.addNode((8049.599999999999, 1684.8), 0, 1, contourIndex=356) # ID: 6
        self.hydrology.addNode((6832.799999999999, 3369.6), 0, 1, contourIndex=374) # ID: 7
        self.hydrology.addNode((280.79999999999995, 6177.599999999999), 0, 2, contourIndex=451) # ID: 8
        self.hydrology.addNode((-4867.2, 5990.4), 0, 1, contourIndex=2) # ID: 9
        self.hydrology.addNode((-6246.780372888135, 307.5788923724788), 173.81, 2, parent=self.hydrology.node(0)) # ID: 10
        self.hydrology.addNode((-5449.5362946522855, 2134.9371444985295), 173.81, 1, parent=self.hydrology.node(0)) # ID: 11
        self.hydrology.addNode((-5738.2285044404125, -2452.02601857411), 173.81, 1, parent=self.hydrology.node(1)) # ID: 12
        self.hydrology.addNode((-3779.8747892700185, -5455.249222671507), 173.81, 1, parent=self.hydrology.node(2)) # ID: 13
        self.hydrology.addNode((1735.4047436340666, -5811.313690817918), 173.81, 1, parent=self.hydrology.node(3)) # ID: 14
        self.hydrology.addNode((3913.3561082532797, -5762.491568073916), 173.81, 1, parent=self.hydrology.node(4)) # ID: 15
        self.hydrology.addNode((4575.801759157646, -3697.733455274554), 173.81, 1, parent=self.hydrology.node(5)) # ID: 16
        self.hydrology.addNode((6588.2148673450665, -117.71872224815615), 173.81, 1, parent=self.hydrology.node(6)) # ID: 17
        self.hydrology.addNode((4551.139609616782, 2946.8162338070397), 173.81, 1, parent=self.hydrology.node(7)) # ID: 18
        self.hydrology.addNode((1686.515368282502, 4331.337680237612), 173.81, 1, parent=self.hydrology.node(8)) # ID: 19
        self.hydrology.addNode((-267.90201010200553, 3922.9057071722514), 173.81, 1, parent=self.hydrology.node(8)) # ID: 20
        self.hydrology.addNode((-3628.3824225111284, 4028.245250826377), 173.81, 1, parent=self.hydrology.node(9)) # ID: 21
        self.hydrology.addNode((-3981.7104458665694, 811.7400528187368), 347.62, 1, parent=self.hydrology.node(10)) # ID: 22
        self.hydrology.addNode((-4397.990228017062, -1094.8102298855324), 347.62, 1, parent=self.hydrology.node(10)) # ID: 23
        self.hydrology.addNode((-3139.1312650010427, 2351.151965827316), 347.62, 1, parent=self.hydrology.node(11)) # ID: 24
        self.hydrology.addNode((-3652.2156918437145, -3468.52530321843), 347.62, 1, parent=self.hydrology.node(12)) # ID: 25
        self.hydrology.addNode((-1636.5946626095852, -4565.8277541525395), 347.62, 1, parent=self.hydrology.node(13)) # ID: 26
        self.hydrology.addNode((1544.4836554558808, -3498.6811242200897), 347.62, 1, parent=self.hydrology.node(14)) # ID: 27
        self.hydrology.addNode((4066.8172916595668, -1433.742496404423), 347.62, 1, parent=self.hydrology.node(16)) # ID: 28
        self.hydrology.addNode((4397.765121188957, 648.2121881900088), 347.62, 1, parent=self.hydrology.node(17)) # ID: 29
        self.hydrology.addNode((2306.434717613504, 2358.5814186043426), 347.62, 1, parent=self.hydrology.node(18)) # ID: 30
        self.hydrology.addNode((-1017.1741446275356, 1726.701818999854), 347.62, 1, parent=self.hydrology.node(20)) # ID: 31
        self.hydrology.addNode((-2307.913817105099, -795.4702929502098), 521.4300000000001, 1, parent=self.hydrology.node(22)) # ID: 32
        self.hydrology.addNode((-1496.566016258495, -2609.517313645959), 521.4300000000001, 1, parent=self.hydrology.node(25)) # ID: 33
        self.hydrology.addNode((1363.0351974719795, -1185.2860634716526), 521.4300000000001, 1, parent=self.hydrology.node(27)) # ID: 34
        self.hydrology.addNode((2670.0365109674985, 419.2884533342087), 521.4300000000001, 1, parent=self.hydrology.node(28)) # ID: 35
        self.hydrology.addNode((707.4833463640621, 676.8933493181478), 521.4300000000001, 1, parent=self.hydrology.node(30)) # ID: 36

        cells = initializeTerrainHoneycomb(self.shore, self.hydrology)

        self.db = lib.SaveFile.createDB(':memory:', 2000, 2320.5, 0, 0)
        cells.saveToDB(self.db)


    def test_save0(self) -> None:
        cells = TerrainHoneycomb()
        cells.loadFromDB(self.db)

        self.assertEqual(len(cells.qs), 78)

    def tearDown(self) -> None:
        self.db.close()

class SaveFileTerrainLoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = lib.SaveFile.createDB(':memory:', 2000, 2000, 0, 0)
        with self.db:
            self.db.execute('INSERT INTO Ts VALUES (0, 0, 12.3, MakePoint(10.5, 5.10, 347895))')
            self.db.execute('INSERT INTO Ts VALUES (5, 0, 13.2, MakePoint(20.1, 12.6, 347895))')
            self.db.execute('INSERT INTO Ts VALUES (7, 0, 15.5, MakePoint(17.5, 15.10, 347895))')
            self.db.execute('INSERT INTO Ts VALUES (2, 0, 15.5, MakePoint(18.6, 0.3, 347895))')
            self.db.execute('INSERT INTO Ts VALUES (6, 0, 10.7, MakePoint(0.8, 0.7, 347895))')
    
    def test_load0(self) -> None:
        Ts = Terrain()
        Ts.loadFromDB(self.db)

        self.assertEqual(len(Ts.tList), 5)
    
    def tearDown(self) -> None:
        self.db.close()
