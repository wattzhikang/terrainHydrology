#! /bin/python

import unittest
from unittest.mock import Mock, MagicMock

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

        node = Mock()
        node.x = 5
        node.y = -15
        
        TerrainHoneycombFunctions.orderVertices(1, node, vor)

        self.assertEqual(vor.ridge_vertices[1][0], 3)
    def test_order_vertices1(self) -> None:
        ridge_vertices = { 1: [3, 5] }
        vertices = { 5: (5,-10), 3: (10,-12) }

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = Mock()
        node.x = 5
        node.y = -15
        
        TerrainHoneycombFunctions.orderVertices(1, node, vor)

        self.assertEqual(vor.ridge_vertices[1][0], 3)
    def test_order_vertices2(self) -> None:
        ridge_vertices = { 20: [4, 14] }
        vertices = { 4: (-29,-8), 14: (-31,-7) }

        vor = Mock()
        vor.ridge_vertices = ridge_vertices
        vor.vertices = vertices

        node = Mock()
        node.x = -28
        node.y = -6
        
        TerrainHoneycombFunctions.orderVertices(20, node, vor)

        self.assertEqual(vor.ridge_vertices[20][0], 14)

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