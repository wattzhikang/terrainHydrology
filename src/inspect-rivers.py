#! /usr/bin/env python

import argparse
from math import sqrt
import matplotlib.pyplot as plt
import numpy as np

from lib.HydrologyFunctions import HydrologyParameters, isAcceptablePosition, selectNode, coastNormal, getLocalWatershed, getInheritedWatershed, getFlow
from lib.ShoreModel import ShoreModel
from lib.HydrologyNetwork import HydrologyNetwork, HydroPrimitive
from lib.TerrainHoneycomb import TerrainHoneycomb, Q, Edge
from lib.Terrain import Terrain, T
from lib.Math import Point, edgeIntersection, segments_intersect_tuple
from lib.TerrainPrimitiveFunctions import computePrimitiveElevation
from lib.RiverInterpolationFunctions import computeRivers
from lib.TerrainHoneycombFunctions import orderVertices, orderEdges, orderCreatedEdges, hasRiver, processRidge, getVertex0, getVertex1, ridgesToPoints, findIntersectingShoreSegment, initializeTerrainHoneycomb
import lib.SaveFile

parser = argparse.ArgumentParser(
    description='Implementation of Genevaux et al., "Terrain Generation Using Procedural Models Based on Hydrology", ACM Transactions on Graphics, 2013'
)
parser.add_argument(
    '-i',
    '--input',
    help='The file that contains the data model you wish to render',
    dest='inputFile',
    metavar='output/data',
    required=True
)
args = parser.parse_args()

inputFile = args.inputFile

## Read the data
resolution, edgeLength, shore, hydrology, cells, Ts = SaveFile.readDataModel(
    inputFile
)

print(list(hydrology.node(3).rivers[0].coords))

# zs = [coord[2] for coord in hydrology.node(3).rivers[0].coords]
# xs = np.arange(0, len(hydrology.node(3).rivers[0].coords))

coords = hydrology.node(3).rivers[0].coords

zs = [coords[0][2]]
xs = [0]

prevCoord = coords[0]
for coord in coords[1:]:
    xs.append(abs(np.linalg.norm(np.subtract(coord[0:2], prevCoord[0:2]))))
    zs.append(coord[2])

fig, ax = plt.subplots()
ax.plot(xs, zs, marker='o')
ax.grid()

plt.show()