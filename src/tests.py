#! /bin/python

from concurrent.futures import process
from operator import truediv
import unittest
from unittest import mock
from unittest.mock import Mock, MagicMock

import shapefile
from PIL import Image
from PIL import ImageDraw
from matplotlib.pyplot import draw
import os.path

import HydrologyFunctions
from DataModel import *
import Math

from TerrainPrimitiveFunctions import computePrimitiveElevation
from RiverInterpolationFunctions import computeRivers
import TerrainHoneycombFunctions

import testcodegenerator
from testcodegenerator import RasterDataMock

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
        shore = ShoreModelShapefile(inputFileName='inputShape')

        closestIndices = shore.closestNPoints((80,-185), 1)

        self.assertEqual(2, closestIndices[0])

        closestIndices = shore.closestNPoints((80,-185), 2)

        self.assertEqual(2, len(closestIndices))
        self.assertEqual(2, closestIndices[0])
        self.assertEqual(3, closestIndices[1])

    def tearDown(self) -> None:
        os.remove('inputShape.shp')
        os.remove('inputShape.dbf')
        os.remove('inputShape.shx')

# class HydrologyFunctionTests(unittest.TestCase):
#     def setUp(self):
#         #create shore
#         r = 100
#         image = Image.new('L', (4*r,4*r))

#         drawer = ImageDraw.Draw(image)

#         #Keep in mind that these are _image_ coordinates
#         drawer.polygon([(150,134),(100,200),(150,286),(250,286),(300,200),(250,134)], 255)
#         #This should work out to (-500,660), (-1000,0), (-500,-860), (500,-860), (1000,0), (500,660)

#         image.save('imageFile.png')

#         shore = ShoreModel(10, 'imageFile.png')

#         #create candidate nodes
#         candidateNodes = [ ]

#         candidateNodes.append(HydroPrimitive(0, None,  4.0, 1, None))
#         candidateNodes.append(HydroPrimitive(1, None,  6.0, 2, None))
#         candidateNodes.append(HydroPrimitive(2, None, 14.0, 3, None))
#         candidateNodes.append(HydroPrimitive(3, None,  8.0, 3, None))
#         candidateNodes.append(HydroPrimitive(4, None, 24.0, 1, None))
#         candidateNodes.append(HydroPrimitive(5, None, 23.0, 4, None))

#         #create hydrology
#         hydrology = HydrologyNetwork()

#         #create real mouth nodes
#         self.node0 = hydrology.addNode(shore[215], 0, 0, 215) # This should be (130,-860)
#         hydrology.addNode(shore[225], 0, 0, 225) # This should be (230,-860)
#         hydrology.addNode(shore[235], 0, 0, 235) # This should be (330,-860)

#         hydrology.addNode((130,-760), 10, 0, parent=self.node0)
        
#         #create the parameters object
#         edgelength = 100
#         sigma = 0.75
#         eta = 0.5
#         zeta = 14
#         self.params = HydrologyFunctions.HydrologyParameters(shore, hydrology, None, None, None, None, edgelength, sigma, eta, zeta, None, None, candidateNodes)

#     def test_select_node(self):
#         selectedNode = HydrologyFunctions.selectNode(self.params.candidates, self.params.zeta)

#         self.assertEqual(self.params.zeta, 14.0)
#         self.assertEqual(selectedNode.id, 3)
    
#     def test_is_acceptable_position_not_on_land(self):
#         acceptable0 = HydrologyFunctions.isAcceptablePosition((-100,-900), self.params)
#         acceptable1 = HydrologyFunctions.isAcceptablePosition((-100,-700), self.params)
        
#         self.assertFalse(acceptable0)
#         self.assertTrue(acceptable1)
    
#     def test_is_acceptable_position_too_close_to_seeee(self):
#         acceptable = HydrologyFunctions.isAcceptablePosition((-100,-830), self.params)

#         self.assertFalse(acceptable)
    
#     def test_is_acceptable_position_too_close_to_nodes_or_edges(self):
#         acceptable0 = HydrologyFunctions.isAcceptablePosition((80,-800), self.params)
#         acceptable1 = HydrologyFunctions.isAcceptablePosition((100,-600), self.params)
        
#         self.assertFalse(acceptable0)
#         self.assertTrue(acceptable1)
    
#     def test_coast_normal(self):
#         angle = HydrologyFunctions.coastNormal(self.node0, self.params)
        
#         self.assertAlmostEqual(angle, math.pi * 0.5, places=3)

#     # def test_pick_new_node_position(self):
#     #     pass
    
#     def tearDown(self) -> None:
#         os.remove('imageFile.png')

# class ExtendedHydrologyFunctionTests(unittest.TestCase):
#     def setUp(self) -> None:
#         self.edgeLength, self.shore, self.hydrology, self.cells = testcodegenerator.getPredefinedObjects0()
    
#     def test_localWatershedTest(self) -> None:
#         node = self.hydrology.node(14)
#         cellArea = self.cells.cellArea(node)
#         self.assertEqual(HydrologyFunctions.getLocalWatershed(node, self.cells), cellArea)

#     def test_inheritedWatershedTest(self) -> None:
#         node = self.hydrology.node(14)
#         upstreamInherited = self.hydrology.node(27).inheritedWatershed
#         self.assertEqual(HydrologyFunctions.getInheritedWatershed(node, self.hydrology), node.localWatershed + upstreamInherited)

#     def test_flowTest(self) -> None:
#         node = self.hydrology.node(14)
#         expectedFlow = 0.42 * node.inheritedWatershed**0.69
#         self.assertEqual(HydrologyFunctions.getFlow(node.inheritedWatershed), expectedFlow)
#         pass

#     def tearDown(self) -> None:
#         os.remove('imageFile.png')

class MathTests(unittest.TestCase):
    def setUp(self) -> None:
        # self.edgeLength, self.shore, self.hydrology, self.cells = testcodegenerator.getPredefinedObjects0()
        pass

    def test_intersection_test_0(self) -> None:
        intersection: Point = Math.edgeIntersection((0,5), (5,10), (0,10), (5,5))

        self.assertAlmostEqual(intersection[0], 2.5, delta=0.01)
        self.assertAlmostEqual(intersection[1], 7.5, delta=0.01)
    
    def test_intersection_test_1(self) -> None:
        intersection: Point = Math.edgeIntersection((-12.5,-5), (-5,-12.5), (-10,-15), (-5,-5))

        self.assertAlmostEqual(intersection[0], -7.5, delta=0.01)
        self.assertAlmostEqual(intersection[1], -10.0, delta=0.01)
    
    def test_intersection_test_2(self) -> None:
        intersection: Point = Math.edgeIntersection([83.8,-63.9], [61.4,-98.4], (22.1,-56.4), (93.4,-88.0))

        self.assertAlmostEqual(intersection[0], 74.11, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.72, delta=1.0)

    def tearDown(self) -> None:
        # os.remove('imageFile.png')
        pass

class HoneycombTests(unittest.TestCase):
    def setUp(self) -> None:
        # self.edgeLength, self.shore, self.hydrology, self.cells = testcodegenerator.getPredefinedObjects0()
        pass

    def test_order_vertices0(self) -> None:
        ridge_vertices = { 1: [5, 3] }
        vertices = { 5: (5,-10), 3: (10,-12) }

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = (5, -15)
        
        TerrainHoneycombFunctions.orderVertices(1, node, vor)

        self.assertEqual(vor.ridge_vertices[1][0], 3)
    def test_order_vertices1(self) -> None:
        ridge_vertices = { 1: [3, 5] }
        vertices = { 5: (5,-10), 3: (10,-12) }

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = (5, -15)
        
        TerrainHoneycombFunctions.orderVertices(1, node, vor)

        self.assertEqual(vor.ridge_vertices[1][0], 3)
    def test_order_vertices2(self) -> None:
        ridge_vertices = { 20: [4, 14] }
        vertices = { 4: (-29,-8), 14: (-31,-7) }

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = (-28,-6)
        
        TerrainHoneycombFunctions.orderVertices(20, node, vor)

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
        
        TerrainHoneycombFunctions.orderVertices(78, node, vor)

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

        orderedEdges = TerrainHoneycombFunctions.orderEdges(edgeIDs, nodeLoc, vor, shore)

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

        TerrainHoneycombFunctions.orderCreatedEdges(edgeIDs, vor, createdEdges)
        
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

        self.assertTrue(TerrainHoneycombFunctions.hasRiver(83, vor, hydrology))
        self.assertFalse(TerrainHoneycombFunctions.hasRiver(93, vor, hydrology))
        self.assertTrue(TerrainHoneycombFunctions.hasRiver(78, vor, hydrology))
        self.assertFalse(TerrainHoneycombFunctions.hasRiver(40, vor, hydrology))
        self.assertTrue(TerrainHoneycombFunctions.hasRiver(20, vor, hydrology))
        self.assertFalse(TerrainHoneycombFunctions.hasRiver(32, vor, hydrology))

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

        processedEdges = TerrainHoneycombFunctions.processRidge(edgeIDs, [ ], createdEdges, createdQs, vor, shore, hydrology)

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

        intersection: Point = Math.edgeIntersection(
            TerrainHoneycombFunctions.getVertex0(32, vor),
            TerrainHoneycombFunctions.getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.11, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.72, delta=1.0)

        processedEdges = TerrainHoneycombFunctions.processRidge(edgeIDs, [ ], createdEdges, createdQs, vor, shore, hydrology)

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

        intersection: Point = Math.edgeIntersection(
            TerrainHoneycombFunctions.getVertex0(32, vor),
            TerrainHoneycombFunctions.getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.11, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.72, delta=1.0)

        processedEdges = TerrainHoneycombFunctions.processRidge(edgeIDs, [ ], createdEdges, createdQs, vor, shore, hydrology)

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

        intersection: Point = Math.edgeIntersection(
            TerrainHoneycombFunctions.getVertex0(32, vor),
            TerrainHoneycombFunctions.getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.2, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.7, delta=1.0)

        processedEdges = TerrainHoneycombFunctions.processRidge(edgeIDs, [ ], createdEdges, createdQs, vor, shore, hydrology)

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
        # edgeLength, shore, hydrology, cells = testcodegenerator.getPredefinedObjects0()

        with shapefile.Writer('inputShape', shapeType=5) as shp:
            #         0           1         2             3             4          5          (beginning)
            shape = [(100, 132), (200, 0), (100, -172), (-100, -172), (-200, 0), (-100, 132), (100, 132)]
            shape.reverse() # pyshp expects shapes to be clockwise

            shp.field('name', 'C')

            shp.poly([ shape ])
            shp.record('polygon0')
        shore = ShoreModelShapefile(inputFileName='inputShape')
        os.remove('inputShape.shp')
        os.remove('inputShape.dbf')
        os.remove('inputShape.shx')

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

        points = [node.position for node in hydrology.allNodes()]

        # Add corners so that the entire area is covered
        points.append((-shore.realShape[0],-shore.realShape[1]))
        points.append((-shore.realShape[0],shore.realShape[1]))
        points.append((shore.realShape[0],shore.realShape[1]))
        points.append((shore.realShape[0],-shore.realShape[1]))
        
        vor = Voronoi(points,qhull_options='Qbb Qc Qz Qx')

        outputFile = '/home/zjwatt/software-projects/terrainHydrology/in/test-example/out/voronoi-edges/voronoi-edges'
        ## Create the .prj file to be read by GIS software
        with open(f'{outputFile}.prj', 'w') as prj:
            prjstr = f'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Orthographic"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Longitude_Of_Center",{0.0}],PARAMETER["Latitude_Of_Center",{0.0}],UNIT["Meter",1.0]]'
            prj.write(prjstr)
            prj.close()
        with shapefile.Writer(outputFile, shapeType=3) as w:
            w.field('id', 'L')
            # print(vor.ridge_vertices)
            for vertexID in len(vor.ridge_vertices):
                vertex = vor.ridge_vertices[vertexID]
                if vertex[0] == -1 or vertex[1] == -1:
                    continue
                # if len(ridge) < 2:
                # continue
                coords = [ ]
                coords.append(vor.vertices[vertex[0]])
                coords.append(vor.vertices[vertex[1]])
                coords = [(p[0],p[1]) for p in coords]
                w.record(vertexID)
                w.line([list(coords)])
            w.close()

        outputFile = '/home/zjwatt/software-projects/terrainHydrology/in/test-example/out/voronoi-vertices/voronoi-vertices'
        ## Create the .prj file to be read by GIS software
        with open(f'{outputFile}.prj', 'w') as prj:
            prjstr = f'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Orthographic"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Longitude_Of_Center",{0.0}],PARAMETER["Latitude_Of_Center",{0.0}],UNIT["Meter",1.0]]'
            prj.write(prjstr)
            prj.close()
        with shapefile.Writer(outputFile, shapeType=1) as w:
            w.field('id', 'L')
            # print(vor.vertices)
            for vertexID in len(vor.vertices):
                vertex = vor.vertices[vertexID]
                # if vertex[0] == -1 or vertex[1] == -1:
                    # continue
                # if len(ridge) < 2:
                # continue
                # coords = [ ]
                # coords.append(vor.vertices[vertex[0]])
                # coords.append(vor.vertices[vertex[1]])
                # coords = [(p[0],p[1]) for p in coords]
                w.record(vertexID)
                w.point(vertex)
            w.close()

    def test_findShoreSegment0(self) -> None:
        mockShore = Mock()
        mockShore.__getitem__ = Mock()
        mockShore.__getitem__.side_effect = lambda index : [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8] ][index]
        mockShore.__len__ = Mock()
        mockShore.__len__.return_value = 9
        mockShore.closestNPoints.return_value = [2, 3, 4, 5]

        p0 = (80,-185)
        p1 = (80,-200)
        segment = TerrainHoneycombFunctions.findIntersectingShoreSegment(p0, p1, mockShore)

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
        segment = TerrainHoneycombFunctions.findIntersectingShoreSegment(p0, p1, mockShore)

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
        segment = TerrainHoneycombFunctions.findIntersectingShoreSegment(p0, p1, mockShore)

        self.assertEqual(7, segment[0])
        self.assertEqual(8, segment[1])

    def tearDown(self) -> None:
        # os.remove('imageFile.png')
        pass

# class RiverTests(unittest.TestCase):
#     def setUp(self) -> None:
#         self.edgeLength, self.shore, self.hydrology, self.cells = testcodegenerator.getPredefinedObjects0()
    
#     def test_test(self) -> None:
#         node = self.hydrology.node(3)
#         node.rivers = [ ]

#         computeRivers(node, self.hydrology, self.cells)

#         # ensure that the river does not intersect any of the mountain ridges of any cells that it flows through
#         allRidges = self.cells.cellRidges(3)
#         allRidges += self.cells.cellRidges(14)
#         allRidges += self.cells.cellRidges(27)
#         allRidges += self.cells.cellRidges(34)

#         self.assertEqual(1, len(node.rivers))

#         river = list(node.rivers[0].coords)
#         for i in range(len(river)-2):
#             p0 = river[i]
#             p1 = river[i+1]
#             for ridge in allRidges:
#                 if len(ridge) < 2:
#                     continue
#                 self.assertFalse(Math.segments_intersect_tuple(p0, p1, ridge[0].position, ridge[1].position))
    
#     def test_always_rising(self) -> None:
#         node = self.hydrology.node(3)
#         node.rivers = [ ]

#         computeRivers(node, self.hydrology, self.cells)

#         river = list(node.rivers[0].coords)
        
#         prevPoint = river[0]
#         for point in river[1:]:
#             self.assertTrue(prevPoint[2] > point[2])
#             prevPoint = point

#     def tearDown(self) -> None:
#         os.remove('imageFile.png')

# class TerrainTests(unittest.TestCase):
#     def setUp(self) -> None:
#         self.edgeLength, self.shore, self.hydrology, self.cells = testcodegenerator.getPredefinedObjects0()

#     def test_test(self) -> None:
#         t = T((1519,-734), 34)

#         z = computePrimitiveElevation(t, self.shore, self.hydrology, self.cells)
        
#         self.assertAlmostEqual(z, 933.975, delta=10.0)

#     def tearDown(self) -> None:
#         os.remove('imageFile.png')