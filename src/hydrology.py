#!/usr/bin/env python

import datetime
import argparse
from os import read
import random
import traceback
import matplotlib.pyplot as plt
import cv2 as cv
import numpy as np
from scipy.spatial import voronoi_plot_2d
import networkx as nx
from scipy import interpolate
import shapely.geometry as geom
import numpy as np
from shapely.geometry import asLineString
from multiprocessing import Process, Pipe, Queue
from tqdm import trange
import math
import rasterio
from rasterio.transform import Affine
import subprocess
import os.path
import struct
import traceback

from lib import DataModel, HydrologyFunctions, Math, SaveFile, TerrainPrimitiveFunctions, RiverInterpolationFunctions, TerrainHoneycombFunctions, testcodegenerator

buildRiversExe = 'src/native-module/bin/buildRivers'
computePrimitivesExe = 'src/native-module/bin/terrainPrimitives'

# Get inputs

parser = argparse.ArgumentParser(
    description='Implementation of Genevaux et al., "Terrain Generation Using Procedural Models Based on Hydrology", ACM Transactions on Graphics, 2013'
)
parser.add_argument(
    '--lat',
    help='Center latitude for the project'' projection',
    dest='latitude',
    metavar='-43.2',
    required=True
)
parser.add_argument(
    '--lon',
    help='Center longitude for the project'' projection',
    dest='longitude',
    metavar='-103.8',
    required=True
)
parser.add_argument(
    '-g',
    '--gamma',
    help='An outline of the shore. Should be a grayscale image (but that doesn\'t have to be the actual color model) or an ESRI shapefile',
    dest='inputDomain',
    metavar='gamma.png / gamma.shp',
    required=True
)
parser.add_argument(
    '-s',
    '--river-slope',
    help='Slope of the rivers (not terrain slope). Values in grayscale.',
    dest='inputRiverSlope',
    metavar='rivers.png',
    required=True
)
parser.add_argument(
    '-t',
    '--terrain-slope',
    help='Slope of the terrain (not river slope). Values in grayscale.',
    dest='inputTerrain',
    metavar='terrain.png',
    required=True
)
parser.add_argument(
    '-ri',
    '--input-resolution',
    help='The spatial resolution of the input images in meters per pixel',
    dest='resolution',
    metavar='87.5',
    required=True
)
parser.add_argument(
    '-p',
    '--num-points',
    help='The (rough) number of terrain primitives for each cell',
    dest='num_points',
    metavar='50',
    required=True
)
parser.add_argument(
    '--num-rivers',
    help='The number of drainages along the coast',
    dest='numRivers',
    metavar='10',
    default=10,
    required=False
)
parser.add_argument(
    '--accelerate',
    help='Accelerate Your Life™ using parallel processing with a natively-compiled module',
    action='store_true',
    dest='accelerate',
    required=False
)
parser.add_argument(
    '--num-procs',
    help='The number of processes/threads to use for calculating terrain primitives. This should be the number of cores you have on your system.',
    dest='num_procs',
    metavar='4',
    default=4,
    required=False
)
parser.add_argument(
    '-o',
    '--output',
    help='File that will contain the data model',
    dest='outputFile',
    metavar='outputFile',
    required=True
)
args = parser.parse_args()


## Global Variables

# Inputs
inputDomain = args.inputDomain
inputTerrain = args.inputTerrain
inputRiverSlope = args.inputRiverSlope
resolution = float(args.resolution) # meters per pixel length

# Random Number Generation
globalseed=4314
random.seed(globalseed)

## Hydrology Parameters

# Number of river mouths
N_majorRivers=int(args.numRivers)

# Branching Parameters
Ps = 0.3 #0.05 ## probability of symetric branch
Pa = 0 #0.3 ## probability of asymetric branch
Pc = 1-(Ps+Pa) ## probability of continium (growth)
zeta = 100 # elevation range to include in candidate node selection
riverAngleDev = 1.7 # Used in picknewnodepos(). Standard Deviation of angle for new node. Increase for less straight rivers
maxTries = 15

# Hydrological slope parameters
slopeRate = 0.1 # Maximum rate at which rivers climb in vertical meters per horizontal meter

# Hydrological resolution parameters
edgeLength = 2320.5 #4000 # in meters
eta = .75   #   eta * edgeLength is the minimum distance from a node to the coast
sigma = .75 # sigma * edgeLength is the minimum distance between two nodes

## Terrain Parameters
terrainSlopeRate = 1.0 # Maximum rate at which ridges climb in vertical meters per horizontal meter
num_points = int(args.num_points) # The (rough) number of terrain primitives for each cell
numProcs = int(args.num_procs) # The number of processes to use in calculating terrain primitives

## Output File
outputFile = args.outputFile


# Check for the native module if the --accelerate flag is specified
if args.accelerate:
    if not os.path.exists(buildRiversExe) or not os.path.exists(computePrimitivesExe):
        print('One or both of the executables does not exist. Run "make" in the src/ directory to build them.')
        exit()

# Load input images

if inputDomain[-4:] == '.shp':
    shore = DataModel.ShoreModel(inputDomain)
else:
    # if the input is not a shapefile, complain and exit
    print('Input domain must be a shapefile. Use img-to-shp.py to convert an image to a shapefile.')
    exit()

terrainSlope = DataModel.RasterData(inputTerrain, resolution)
riverSlope = DataModel.RasterData(inputRiverSlope, resolution)

# Initialize the save file
db = SaveFile.createDB(outputFile, resolution, edgeLength, args.longitude, args.latitude)

# Save the shore dimensions
SaveFile.setShoreBoundaries(db, shore)

## Generate river mouths

try:

    hydrology = DataModel.HydrologyNetwork()

    # generate first node
    firstIdx = random.randint(0,len(shore)-1)
    point = shore[firstIdx]
    hydrology.addNode(point, 0, random.randint(1,N_majorRivers), contourIndex=firstIdx)

    dist = len(shore)/N_majorRivers
    for i in range(1,N_majorRivers):
        idx = int((firstIdx+i*dist+random.gauss(0, dist/6))%len(shore))
        point = shore[idx]
        hydrology.addNode(point, 0, 1, contourIndex=idx)


    ## Generate river nodes

    print('Generating rivers...')

    candidates = hydrology.allMouthNodes() # All mouth nodes are candidates
    params = HydrologyFunctions.HydrologyParameters(
        # These parameters will be needed to generate the hydrology network
        shore, hydrology, Pa, Pc, maxTries, riverAngleDev, edgeLength,
        sigma, eta, zeta, riverSlope, slopeRate, candidates
    )

    start, end = None, None

    if not args.accelerate: # Generate the hydrology in Python
        cyclesRun = 0
        start = datetime.datetime.now()
        while len(candidates)!=0:
            selectedCandidate = HydrologyFunctions.selectNode(candidates,zeta)
            HydrologyFunctions.alpha(selectedCandidate, candidates, params)
            print(f'\tCycles: {len(hydrology)}\t{cyclesRun/(datetime.datetime.now()-start).total_seconds()} cycles/sec\r', end='')
            cyclesRun = cyclesRun + 1
        end = datetime.datetime.now()
        print()
    else: # Generate the hydrology using the native module
        SaveFile.dumpMouthNodes(db, hydrology)
        SaveFile.createRiverSlopeRaster(db, riverSlope)
        shore.saveToDB(db)
        proc = subprocess.Popen( # start the native module
            [buildRiversExe, outputFile, str(Pa), str(Pc), str(sigma), str(eta), str(zeta), str(slopeRate), str(maxTries), str(riverAngleDev)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        print('\tData sent to native module...')

        # print(f'Process called: ./{buildRiversExe} {outputFile} {Pa} {Pc} {sigma} {eta} {zeta} {slopeRate} {maxTries} {riverAngleDev}')
        # exit()

        # Display updates as native module builds the network
        cyclesRun = 0
        start = datetime.datetime.now()
        readByte = proc.stdout.read(1)
        cyclesRun = cyclesRun + 1
        while struct.unpack('B', readByte)[0] == 0x2e:
            print(f'\tCycles: {cyclesRun}\t{cyclesRun/(datetime.datetime.now()-start).total_seconds()} cycles/sec\r', end='')
            readByte = proc.stdout.read(1)
            cyclesRun = cyclesRun + 1
        end = datetime.datetime.now()
        print()

        # Recreate hydrology with data from the native module
        print('\tReading data...')
        hydrology = DataModel.HydrologyNetwork(db)

    print(f'\tGenerated {len(hydrology)} nodes in {(end-start).total_seconds()} seconds')
    print(f'\tRate: {len(hydrology)/(end-start).total_seconds()} node/sec')

except Exception as e:
    print('Problem encountered in generating the hydrology. Saving shore model to export file.')
    print(e)

    print('Saving...')
    shore.saveToDB(db)
    hydrology.saveToDB(db)

    SaveFile.dropRiverSlopeRaster(db)

    db.close()

    exit()

try:

    ## Create terrain partition (voronoi cells)
    print('Generating terrain ridges...')
    cells = TerrainHoneycombFunctions.initializeTerrainHoneycomb(shore, hydrology)

    ## Calculate watershed areas
    print('Calculating watershed areas...')

    # calculate inherited watershed areas and flow
    for node in hydrology.dfsPostorderNodes():  # search nodes in a depth-first post-ordering manner
        node.localWatershed = HydrologyFunctions.getLocalWatershed(node, cells)
        node.inheritedWatershed = HydrologyFunctions.getInheritedWatershed(node, hydrology)
        node.flow = HydrologyFunctions.getFlow(node.inheritedWatershed)


    ## Classify river nodes
    print('Classifying river nodes...')
    for n in range(len(hydrology)):
        HydrologyFunctions.classify(hydrology.node(n), hydrology, edgeLength)


    ## Calculate ridge elevations
    print('Calculating ridge elevations...')

    for q in cells.allQs():
        if q is None:
            continue
        q.elevation = TerrainHoneycombFunctions.getRidgeElevation(q, hydrology, terrainSlope, terrainSlopeRate)

except Exception as e:
    print('Problem encountered in partitioning the terrain cells. Saving the shore model and hydrology network to file.')
    print(e)

    print('Saving...')
    shore.saveToDB(db)
    hydrology.saveToDB(db)
    cells.saveToDB(db)

    SaveFile.dropRiverSlopeRaster(db)

    db.close()

    exit()

try:

    ## Terrain pattern
    print('Generating terrain primitives...')
    Ts = TerrainPrimitiveFunctions.initializeTerrain(hydrology, cells, num_points)


    ## Generate river paths
    print('Interpolating river paths...')
    for node in hydrology.allMouthNodes():
        RiverInterpolationFunctions.computeRivers(node, hydrology, cells)

except Exception as ex:
    print('Problem encountered in generating the terrain primitives. Saving shore model, hydrology network, and terrain cells to export file.')
    print(ex.with_traceback())

    print('Saving...')
    shore.saveToDB(db)
    hydrology.saveToDB(db)
    cells.saveToDB(db)

    SaveFile.dropRiverSlopeRaster(db)

    db.close()

    exit()

## Calculate elevations of terrain primitives
print('Calculating terrain primitive elevations...')
def subroutine(conn: Pipe, q: Queue):
    try:
        threadID = conn.recv()
        for ti in range(threadID, len(Ts), numProcs):
            t = Ts.getT(ti)
            
            t.elevation = TerrainPrimitiveFunctions.computePrimitiveElevation(t, shore, hydrology, cells)

            q.put(t)

    except:
        traceback.print_exc()

        q.put(None)

        print('Thread closed')

try:

    # The terrain primitives will be calculated in parallel
    if not args.accelerate: # Calculate the elevations in Python
        dataQueue = Queue()
        pipes = []
        processes = []
        for p in range(numProcs):
            pipes.append(Pipe())
            processes.append(Process(target=subroutine, args=(pipes[p][1],dataQueue)))
            processes[p].start()
            pipes[p][0].send(p)
        for ti in trange(len(Ts)):
            t = dataQueue.get()
            if t is not None:
                Ts.tList[ti] = t
            else:
                raise Exception
        for p in range(numProcs):
            processes[p].join()
            pipes[p][0].close()
    else:
        # Save necessary information to the database
        hydrology.saveToDB(db)
        cells.saveToDB(db)
        Ts.saveToDB(db)

        # Run the native module
        primitivesProc = subprocess.Popen( # start the native module
            [computePrimitivesExe, outputFile],
            stdout=subprocess.PIPE
        )

        # Display updates as native module calculates the elevations
        for tid in trange(len(Ts)):
            readByte = primitivesProc.stdout.read(1)
        readByte = primitivesProc.stdout.read(1)
        assert struct.unpack('B',readByte)[0] == 0x21

        # Recreate the terrain primitives with data from the native module
        Ts = DataModel.Terrain()
        Ts.loadFromDB(db)

except Exception as e:
    print('Problem encountered in generating the terrain primitives. Saving shore model, hydrology network, and terrain cells to export file.')
    print(e)

    print('Saving...')
    shore.saveToDB(db)
    hydrology.saveToDB(db)
    cells.saveToDB(db)

    SaveFile.dropRiverSlopeRaster(db)

    db.close()

    exit()

## Save the data
print('Writing data model...')
shore.saveToDB(db)
hydrology.saveToDB(db)
cells.saveToDB(db)
Ts.saveToDB(db)
SaveFile.dropRiverSlopeRaster(db)
db.close() # TODO This should be implemented as a context manager
print('Complete')

# DEBUG
# code =  testcodegenerator.hydrologyToCode(hydrology)
# code += testcodegenerator.terrainHoneycombToCode(cells)
# code += testcodegenerator.hydrologyAttributesToCode(hydrology)
# code += testcodegenerator.riversToCode(hydrology)

# print(code)