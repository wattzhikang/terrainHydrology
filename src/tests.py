#! /bin/python

from concurrent.futures import process
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