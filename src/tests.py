#! /bin/python

import unittest
from unittest.mock import Mock

import io

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

import SaveFile

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
    
    def test_onLand(self) -> None:
        shore = ShoreModelShapefile(inputFileName='inputShape')

        self.assertTrue(shore.isOnLand((0,-100)))
        self.assertTrue(shore.isOnLand((50,-100)))
        self.assertFalse(shore.isOnLand((35,-120)))

    def tearDown(self) -> None:
        os.remove('inputShape.shp')
        os.remove('inputShape.dbf')
        os.remove('inputShape.shx')

class ImageShoreTests(unittest.TestCase):
    def setUp(self):
        #create shore
        r = 100
        image = Image.new('L', (4*r,4*r))

        drawer = ImageDraw.Draw(image)

        #Keep in mind that these are _image_ coordinates
        drawer.polygon([(150,134),(100,200),(150,286),(250,286),(300,200),(250,134)], 255)
        #This should work out to (-500,660), (-1000,0), (-500,-860), (500,-860), (1000,0), (500,660)

        image.save('imageFile.png')

        self.shore = ShoreModelImage(10, 'imageFile.png')

    def test_closestNPoints(self):
        closestIndices = self.shore.closestNPoints((-500,670), 4)

        self.assertEqual(4, len(closestIndices))
        self.assertEqual(0, closestIndices[0])

    def test_onLand(self) -> None:
        self.assertTrue(self.shore.isOnLand((-287,326)))
        self.assertTrue(self.shore.isOnLand((723,-370)))
        self.assertFalse(self.shore.isOnLand((-853,308)))

    def tearDown(self) -> None:
        os.remove('imageFile.png')

class ImageShoreTests1(unittest.TestCase):
    def setUp(self):
        #create shore
        r = 100
        image = Image.new('L', (4*r,4*r))

        drawer = ImageDraw.Draw(image)

        #Keep in mind that these are _image_ coordinates
        drawer.polygon([(150,134),(100,200),(150,286),(250,286),(300,200),(250,134)], 255)
        #This should work out to (-500,660), (-1000,0), (-500,-860), (500,-860), (1000,0), (500,660)

        image.save('imageFile.png')

        self.shore = ShoreModelImage(93.6, 'imageFile.png')

        self.shore.contour = np.array([(134, 150), (135, 149), (136, 148), (137, 148), (138, 147), (139, 146), (140, 145), (141, 145), (142, 144), (143, 143), (144, 142), (145, 142), (146, 141), (147, 140), (148, 139), (149, 139), (150, 138), (151, 137), (152, 136), (153, 136), (154, 135), (155, 134), (156, 133), (157, 133), (158, 132), (159, 131), (160, 130), (161, 130), (162, 129), (163, 128), (164, 127), (165, 127), (166, 126), (167, 125), (168, 124), (169, 123), (170, 123), (171, 122), (172, 121), (173, 120), (174, 120), (175, 119), (176, 118), (177, 117), (178, 117), (179, 116), (180, 115), (181, 114), (182, 114), (183, 113), (184, 112), (185, 111), (186, 111), (187, 110), (188, 109), (189, 108), (190, 108), (191, 107), (192, 106), (193, 105), (194, 105), (195, 104), (196, 103), (197, 102), (198, 102), (199, 101), (200, 100), (201, 101), (202, 101), (203, 102), (204, 102), (205, 103), (206, 103), (207, 104), (208, 105), (209, 105), (210, 106), (211, 106), (212, 107), (213, 108), (214, 108), (215, 109), (216, 109), (217, 110), (218, 110), (219, 111), (220, 112), (221, 112), (222, 113), (223, 113), (224, 114), (225, 115), (226, 115), (227, 116), (228, 116), (229, 117), (230, 117), (231, 118), (232, 119), (233, 119), (234, 120), (235, 120), (236, 121), (237, 122), (238, 122), (239, 123), (240, 123), (241, 124), (242, 124), (243, 125), (244, 126), (245, 126), (246, 127), (247, 127), (248, 128), (249, 128), (250, 129), (251, 130), (252, 130), (253, 131), (254, 131), (255, 132), (256, 133), (257, 133), (258, 134), (259, 134), (260, 135), (261, 135), (262, 136), (263, 137), (264, 137), (265, 138), (266, 138), (267, 139), (268, 140), (269, 140), (270, 141), (271, 141), (272, 142), (273, 142), (274, 143), (275, 144), (276, 144), (277, 145), (278, 145), (279, 146), (280, 147), (281, 147), (282, 148), (283, 148), (284, 149), (285, 149), (286, 150), (286, 151), (286, 152), (286, 153), (286, 154), (286, 155), (286, 156), (286, 157), (286, 158), (286, 159), (286, 160), (286, 161), (286, 162), (286, 163), (286, 164), (286, 165), (286, 166), (286, 167), (286, 168), (286, 169), (286, 170), (286, 171), (286, 172), (286, 173), (286, 174), (286, 175), (286, 176), (286, 177), (286, 178), (286, 179), (286, 180), (286, 181), (286, 182), (286, 183), (286, 184), (286, 185), (286, 186), (286, 187), (286, 188), (286, 189), (286, 190), (286, 191), (286, 192), (286, 193), (286, 194), (286, 195), (286, 196), (286, 197), (286, 198), (286, 199), (286, 200), (286, 201), (286, 202), (286, 203), (286, 204), (286, 205), (286, 206), (286, 207), (286, 208), (286, 209), (286, 210), (286, 211), (286, 212), (286, 213), (286, 214), (286, 215), (286, 216), (286, 217), (286, 218), (286, 219), (286, 220), (286, 221), (286, 222), (286, 223), (286, 224), (286, 225), (286, 226), (286, 227), (286, 228), (286, 229), (286, 230), (286, 231), (286, 232), (286, 233), (286, 234), (286, 235), (286, 236), (286, 237), (286, 238), (286, 239), (286, 240), (286, 241), (286, 242), (286, 243), (286, 244), (286, 245), (286, 246), (286, 247), (286, 248), (286, 249), (286, 250), (285, 251), (284, 251), (283, 252), (282, 252), (281, 253), (280, 253), (279, 254), (278, 255), (277, 255), (276, 256), (275, 256), (274, 257), (273, 258), (272, 258), (271, 259), (270, 259), (269, 260), (268, 260), (267, 261), (266, 262), (265, 262), (264, 263), (263, 263), (262, 264), (261, 265), (260, 265), (259, 266), (258, 266), (257, 267), (256, 267), (255, 268), (254, 269), (253, 269), (252, 270), (251, 270), (250, 271), (249, 272), (248, 272), (247, 273), (246, 273), (245, 274), (244, 274), (243, 275), (242, 276), (241, 276), (240, 277), (239, 277), (238, 278), (237, 278), (236, 279), (235, 280), (234, 280), (233, 281), (232, 281), (231, 282), (230, 283), (229, 283), (228, 284), (227, 284), (226, 285), (225, 285), (224, 286), (223, 287), (222, 287), (221, 288), (220, 288), (219, 289), (218, 290), (217, 290), (216, 291), (215, 291), (214, 292), (213, 292), (212, 293), (211, 294), (210, 294), (209, 295), (208, 295), (207, 296), (206, 297), (205, 297), (204, 298), (203, 298), (202, 299), (201, 299), (200, 300), (199, 299), (198, 298), (197, 298), (196, 297), (195, 296), (194, 295), (193, 295), (192, 294), (191, 293), (190, 292), (189, 292), (188, 291), (187, 290), (186, 289), (185, 289), (184, 288), (183, 287), (182, 286), (181, 286), (180, 285), (179, 284), (178, 283), (177, 283), (176, 282), (175, 281), (174, 280), (173, 280), (172, 279), (171, 278), (170, 277), (169, 277), (168, 276), (167, 275), (166, 274), (165, 273), (164, 273), (163, 272), (162, 271), (161, 270), (160, 270), (159, 269), (158, 268), (157, 267), (156, 267), (155, 266), (154, 265), (153, 264), (152, 264), (151, 263), (150, 262), (149, 261), (148, 261), (147, 260), (146, 259), (145, 258), (144, 258), (143, 257), (142, 256), (141, 255), (140, 255), (139, 254), (138, 253), (137, 252), (136, 252), (135, 251), (134, 250), (134, 249), (134, 248), (134, 247), (134, 246), (134, 245), (134, 244), (134, 243), (134, 242), (134, 241), (134, 240), (134, 239), (134, 238), (134, 237), (134, 236), (134, 235), (134, 234), (134, 233), (134, 232), (134, 231), (134, 230), (134, 229), (134, 228), (134, 227), (134, 226), (134, 225), (134, 224), (134, 223), (134, 222), (134, 221), (134, 220), (134, 219), (134, 218), (134, 217), (134, 216), (134, 215), (134, 214), (134, 213), (134, 212), (134, 211), (134, 210), (134, 209), (134, 208), (134, 207), (134, 206), (134, 205), (134, 204), (134, 203), (134, 202), (134, 201), (134, 200), (134, 199), (134, 198), (134, 197), (134, 196), (134, 195), (134, 194), (134, 193), (134, 192), (134, 191), (134, 190), (134, 189), (134, 188), (134, 187), (134, 186), (134, 185), (134, 184), (134, 183), (134, 182), (134, 181), (134, 180), (134, 179), (134, 178), (134, 177), (134, 176), (134, 175), (134, 174), (134, 173), (134, 172), (134, 171), (134, 170), (134, 169), (134, 168), (134, 167), (134, 166), (134, 165), (134, 164), (134, 163), (134, 162), (134, 161), (134, 160), (134, 159), (134, 158), (134, 157), (134, 156), (134, 155), (134, 154), (134, 153), (134, 152), (134, 151)])
        self.shore.imgray.shape = (400,400)

    def test_isVertex49OnLand(self) -> None:
        print(self.shore.distanceToShore((5534.5,-6661.6)))
        self.assertFalse(self.shore.isOnLand((5534.5,-6661.6)))

    def tearDown(self) -> None:
        os.remove('imageFile.png')

class HydrologyFunctionTests(unittest.TestCase):
    def setUp(self):
        #create shore
        r = 100
        image = Image.new('L', (4*r,4*r))

        drawer = ImageDraw.Draw(image)

        #Keep in mind that these are _image_ coordinates
        drawer.polygon([(150,134),(100,200),(150,286),(250,286),(300,200),(250,134)], 255)
        #This should work out to (-500,660), (-1000,0), (-500,-860), (500,-860), (1000,0), (500,660)

        image.save('imageFile.png')

        shore = ShoreModelImage(10, 'imageFile.png')

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
        self.node0 = hydrology.addNode(shore[215], 0, 0, 215) # This should be (130,-860)
        hydrology.addNode(shore[225], 0, 0, 225) # This should be (230,-860)
        hydrology.addNode(shore[235], 0, 0, 235) # This should be (330,-860)

        hydrology.addNode((130,-760), 10, 0, parent=self.node0)
        
        #create the parameters object
        edgelength = 100
        sigma = 0.75
        eta = 0.5
        zeta = 14
        self.params = HydrologyFunctions.HydrologyParameters(shore, hydrology, None, None, None, None, edgelength, sigma, eta, zeta, None, None, candidateNodes)

    def test_select_node(self):
        selectedNode = HydrologyFunctions.selectNode(self.params.candidates, self.params.zeta)

        self.assertEqual(self.params.zeta, 14.0)
        self.assertEqual(selectedNode.id, 3)
    
    def test_is_acceptable_position_not_on_land(self):
        acceptable0 = HydrologyFunctions.isAcceptablePosition((-100,-900), self.params)
        acceptable1 = HydrologyFunctions.isAcceptablePosition((-100,-700), self.params)
        
        self.assertFalse(acceptable0)
        self.assertTrue(acceptable1)
    
    def test_is_acceptable_position_too_close_to_seeee(self):
        acceptable = HydrologyFunctions.isAcceptablePosition((-100,-830), self.params)

        self.assertFalse(acceptable)
    
    def test_is_acceptable_position_too_close_to_nodes_or_edges(self):
        acceptable0 = HydrologyFunctions.isAcceptablePosition((80,-800), self.params)
        acceptable1 = HydrologyFunctions.isAcceptablePosition((100,-600), self.params)
        
        self.assertFalse(acceptable0)
        self.assertTrue(acceptable1)
    
    def test_coast_normal(self):
        angle = HydrologyFunctions.coastNormal(self.node0, self.params)
        
        self.assertAlmostEqual(angle, math.pi * 0.5, places=3)

    # def test_pick_new_node_position(self):
    #     pass
    
    def tearDown(self) -> None:
        os.remove('imageFile.png')

class ExtendedHydrologyFunctionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.edgeLength, self.shore, self.hydrology, self.cells = testcodegenerator.getPredefinedObjects0()
    
    def test_localWatershedTest(self) -> None:
        node = self.hydrology.node(14)
        cellArea = self.cells.cellArea(node)
        self.assertEqual(HydrologyFunctions.getLocalWatershed(node, self.cells), cellArea)

    def test_inheritedWatershedTest(self) -> None:
        node = self.hydrology.node(14)
        upstreamInherited = self.hydrology.node(27).inheritedWatershed
        self.assertEqual(HydrologyFunctions.getInheritedWatershed(node, self.hydrology), node.localWatershed + upstreamInherited)

    def test_flowTest(self) -> None:
        node = self.hydrology.node(14)
        expectedFlow = 0.42 * node.inheritedWatershed**0.69
        self.assertEqual(HydrologyFunctions.getFlow(node.inheritedWatershed), expectedFlow)
        pass

    def tearDown(self) -> None:
        os.remove('imageFile.png')

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
        shoreQs = [ ]

        processedEdges = TerrainHoneycombFunctions.processRidge(edgeIDs, [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

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

        intersection: Point = Math.edgeIntersection(
            TerrainHoneycombFunctions.getVertex0(32, vor),
            TerrainHoneycombFunctions.getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.11, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.72, delta=1.0)

        processedEdges = TerrainHoneycombFunctions.processRidge(edgeIDs, [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

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

        intersection: Point = Math.edgeIntersection(
            TerrainHoneycombFunctions.getVertex0(32, vor),
            TerrainHoneycombFunctions.getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.11, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.72, delta=1.0)

        processedEdges = TerrainHoneycombFunctions.processRidge(edgeIDs, [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

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

        intersection: Point = Math.edgeIntersection(
            TerrainHoneycombFunctions.getVertex0(32, vor),
            TerrainHoneycombFunctions.getVertex1(32, vor),
            shore[15],
            shore[16]
        )
        self.assertAlmostEqual(intersection[0], 74.2, delta=1.0)
        self.assertAlmostEqual(intersection[1], -79.7, delta=1.0)

        processedEdges = TerrainHoneycombFunctions.processRidge(edgeIDs, [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

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
        shore = ShoreModelShapefile(inputFileName='inputShape')
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

        point_ridges: typing.Dict[int, typing.List[int]] = TerrainHoneycombFunctions.ridgesToPoints(vor)

        createdQs: typing.Dict[int, Q] = { }
        createdEdges: typing.Dict[int, Edge] = { }
        shoreQs: typing.List[Q] = [ ]

        cells = { }
        for node in hydrology.allNodes():
            # order the cell edges in counterclockwise order
            point_ridges[node.id] = TerrainHoneycombFunctions.orderEdges(point_ridges[node.id], node.position, vor, shore)
            TerrainHoneycombFunctions.orderCreatedEdges(point_ridges[node.id], vor, createdEdges)

            # then we have to organize and set up all the edges of the cell
            cells[node.id] = TerrainHoneycombFunctions.processRidge(point_ridges[node.id], [ ], createdEdges, createdQs, shoreQs, vor, shore, hydrology)

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

class RiverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.edgeLength, self.shore, self.hydrology, self.cells = testcodegenerator.getPredefinedObjects0()
    
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
                self.assertFalse(Math.segments_intersect_tuple(p0, p1, ridge[0].position, ridge[1].position))
    
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
        os.remove('imageFile.png')

class TerrainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.edgeLength, self.shore, self.hydrology, self.cells = testcodegenerator.getPredefinedObjects0()

    def test_test(self) -> None:
        t = T((1909,-766), 34)

        z = computePrimitiveElevation(t, self.shore, self.hydrology, self.cells)
        
        self.assertAlmostEqual(z, 1140, delta=10.0)

    def tearDown(self) -> None:
        os.remove('imageFile.png')

class SaveFileShoreLoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shape = [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8], [0,-437] ]

        self.db = SaveFile.createDB(':memory:', 2000, 2000, 0, 0)
        with self.db:
            self.db.executemany('INSERT INTO Shoreline VALUES (?, MakePoint(?, ?, 347895))', [ (idx, x, y) for idx, (x,y) in enumerate(self.shape) ])

        self.shore = ShoreModelShapefile()
        self.shore.loadFromDB(self.db)
    
    def test_loadLength0(self) -> None:
        self.assertEqual(len(self.shape), len(self.shore))
    
    def tearDown(self) -> None:
        self.db.close()

class SaveFileShoreSaveTests(unittest.TestCase):
    def setUp(self) -> None:
        shpBuf = io.BytesIO()
        dbfBuf = io.BytesIO()

        with shapefile.Writer(shp=shpBuf, dbf=dbfBuf, shapeType=5) as shp:
            #         0         1          2          3          4          5           6         7        8         (beginning)
            shape = [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8], [0,-437] ]
            shape.reverse() # pyshp expects shapes to be clockwise

            shp.field('name', 'C')

            shp.poly([ shape ])
            shp.record('polygon0')

        self.shore = ShoreModelShapefile(shpFile=shpBuf, dbfFile=dbfBuf)

        self.db = SaveFile.createDB(':memory:', 2000, 2000, 0, 0)
        self.shore.saveToDB(self.db)

    def test_save0(self) -> None:
        with self.db:
            rowCount = self.db.execute('SELECT COUNT(*) FROM Shoreline').fetchone()[0]
            self.assertEqual(len(self.shore), rowCount)
    
    def tearDown(self) -> None:
        self.db.close()

# class SaveFileTests(unittest.TestCase):
#     def shore_save_0_test(self) -> None:
#         pass
#     def shore_load_0_test(self) -> None:


#         self.assertEqual(len(shape), len(shore))
#     def hydrology_save_0_test(self) -> None:
#         pass
#     def hydrology_load_0_test(self) -> None:
#         pass
#     def honeycomb_save_0_test(self) -> None:
#         pass
#     def honeycomb_load_0_test(self) -> None:
#         pass
#     def terrain_save_0_test(self) -> None:
#         pass
#     def terrain_load_0_test(self) -> None:
#         pass