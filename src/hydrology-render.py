#! /usr/bin/env python

import typing
import matplotlib.pyplot as plt
import argparse
import numpy as np
import shapely.geometry as geom
from multiprocessing import Process, Pipe, Queue, shared_memory, Value
import rasterio
from rasterio.transform import Affine
import time
import math

import DataModel
import SaveFile
import Math

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
parser.add_argument(
    '--lat',
    help='Center latitude for the output GeoTIFF',
    dest='latitude',
    metavar='-43.2',
    required=True
)
parser.add_argument(
    '--lon',
    help='Center longitude for the output GeoTIFF',
    dest='longitude',
    metavar='-103.8',
    required=True
)
parser.add_argument(
    '-ro',
    '--output-resolution',
    help='The number of pixels/samples on each side of the output raster',
    dest='outputResolution',
    metavar='1000',
    required=True
)
parser.add_argument(
    '--num-procs',
    help='The number of processes/threads to use in rendering. This should be the number of cores you have on your system.',
    dest='num_procs',
    metavar='4',
    default=4,
    required=False
)
parser.add_argument(
    '-o',
    '--output-dir',
    help='Folder in which to dump all the data generated by this program (including debug data)',
    dest='outputDir',
    metavar='output/',
    required=True
)
parser.add_argument(
    '--extreme-memory',
    help='An experimental method of conserving memory when rendering large terrains',
    dest='extremeMemory',
    action='store_true',
    required=False
)
args = parser.parse_args()

inputFile = args.inputFile
outputDir = args.outputDir + '/'
outputResolution = int(args.outputResolution) # in pixels
numProcs = int(args.num_procs)
latitude = float(args.latitude)
longitude = float(args.longitude)

# Read the data model
db = SaveFile.openDB(inputFile)
resolution = SaveFile.getResolution(db)
edgeLength = SaveFile.getEdgeLength(db)
shore: DataModel.ShoreModel = DataModel.ShoreModel()
shore.loadFromDB(db)
hydrology: DataModel.HydrologyNetwork = DataModel.HydrologyNetwork(db)
cells: DataModel.TerrainHoneycomb = DataModel.TerrainHoneycomb()
cells.loadFromDB(resolution, edgeLength, shore, hydrology, db)
Ts: DataModel.Terrain = DataModel.Terrain()
Ts.loadFromDB(db)

radius = edgeLength / 3
rwidth = edgeLength / 2

# oceanFloor is calculated ensure that all land appears as green in the output
# image. It should be about 25% of the way up the color ramp
maxq = max([q.elevation for q in cells.allQs() if q is not None])
oceanFloor = 0 - 0.25 * maxq / 0.75

outputShape = (outputResolution,outputResolution) # shape of the output matrix
outputType = np.single # dtype of the output matrix

# Create an array that is all water by default
imgInit = np.full(outputShape, oceanFloor,dtype=outputType)

# create a region of shared memory for processes to write to
bufferString = 'HydrologyRender-sklvv482'
sharedBuffer = shared_memory.SharedMemory(
    bufferString, create=True, size=imgInit.nbytes
)

# The image will be written to the shared memory as in a numpy matrix
imgOut = np.ndarray(outputShape, dtype=outputType, buffer=sharedBuffer.buf)
imgOut[:] = imgInit[:] # Load ocean floor fill
del imgInit # This matrix is no longer needed

def ijToxy(ij: typing.Tuple[float,float]) -> typing.Tuple[float,float]:
    i = ij[0]
    i -= outputResolution * 0.5
    i /= (outputResolution * 0.5)
    i *= (shore.realShape[0] if shore.realShape[0] > shore.realShape[1] else shore.realShape[1]) * 0.5

    j = ij[1]
    j -= outputResolution * 0.5
    j /= (outputResolution * 0.5)
    j *= (shore.realShape[0] if shore.realShape[0] > shore.realShape[1] else shore.realShape[1]) * 0.5
 
    return (i,j)

## Functions that calculate the height of a point

# This function calculates the elevation of a single point on the output raster
def TerrainFunction(point: typing.Tuple[float,float]) -> float:
    
    # if imgray[point[1]][point[0]]==0: This is why a new data model was implemented
    if not shore.isOnLand(point):
        return oceanFloor

    # Gets and computes influence and elevation values for nearby terrain primitives
    ts = Ts.query_ball_point(point,radius) # Gets all terrain primitives within a radius of the point
    if len(ts) < 1: # if there just aren't any T points around, just put it in the ocean
        return 0
    wts = [w(Math.distance(point,t.position)) for t in ts] # "influence field" radii of those primitives
    # TODO: I think this end up getting different heights for
    hts = [ht(point,t) for t in ts]          # elevations of those primitives

    # Blends the terrain primitives
    ht_ = height_b(hts,wts) # Blends those terrain primitives
    wt_ = wts[0]            # I guess this is supposed to be the influence radius of the closest primitive?
    
    wi=wt_ # IDK why he converts these here
    hi=ht_
    
    nodeID = cells.nodeID(point)
    if nodeID is None:
        return hi
    node = hydrology.node(nodeID)
    geomp = geom.Point(point[0],point[1]) # Creates a Shapely point out of the input point
    rs = [ ]
    hrs = [ ]
    wrs = [ ]
    if len(node.rivers) > 0:
        rs  = [e for e in node.rivers if geomp.distance(e) < radius ]
        hrs = [hr(geomp,e) for e in rs]
        wrs = [w(geomp.distance(e)) for e in rs]
    else: # Sometimes there isn't a river, just a drainage point along the seeeee
        riverPoint = geom.Point(node.x(),node.y(),node.elevation)
        if geomp.distance(riverPoint) < radius:
            rs = [ geomp.distance(riverPoint) ]
            hrs = [ riverPoint.z ]
            wrs = [ w(geomp.distance(riverPoint)) ]
    
    # Height and "influence field" calculation per the last equation in Section 7
    # This is the so-called "replacement operator"
    for i in range(len(rs)): 
        hi=(1-wrs[i])*hi+wrs[i]*hrs[i] 
        wi = (1-wrs[i])*wi+wrs[i]**2

    if hi<0:
        pass
    
    return hi

# height function of a blend node (Geneveaux et al §7)
def height_b(h: typing.List[float], w: typing.List[float]) -> float:
    try:
        ret = np.sum(np.multiply(h,w))/(np.sum(w))
        assert(ret>=0)
        assert(not np.isnan(ret)) # make sure ret is a number
        return ret
    except:
        return 0

scale = 100.0 # I think adjusting these values could be useful
octaves = 6
persistence = 0.5
lacunarity = 2.0
# Height of a terrain primitive
def ht(p: typing.Tuple[float, float], t: DataModel.T) -> float:
    return t.elevation# +pnoise2(p[0]/scale,p[1]/scale,octaves=octaves,persistence=persistence,lacunarity=lacunarity,repeatx=shore.shape[0],repeaty=shore.shape[1],base=0)*10

# Height of a river primitive?
def hr(p: typing.Tuple[float, float], r: float) -> float:
    d=p.distance(r)
    # TODO profile based on Rosgen classification
    segma = 0.1 * min(rwidth**2,d**2) # I think this is the river profile
    projected = r.interpolate(r.project(p))
    return projected.z+segma

# This returns the "influence field" (Geneveaux et al §7)
def w(d: float) -> float:
    if d <1:
        return 1;
    return (max(0,(radius+1)-d)/(((radius)+1)*d))**2


## This is the function that the rendering threads will run
def subroutineExtremeMemory(start: int, end: int, q: Queue):
    # Access the shared memory region
    sharedBuffer = shared_memory.SharedMemory(
        bufferString, create=False
    )
    imgOut = np.ndarray( # Access the shared memory through a numpy matrix
        outputShape,
        dtype=outputType,
        buffer=sharedBuffer.buf
    )

    # Render lines that are assigned to this thread
    for i in range(start, end):
        # Render a line
        for j in range(outputResolution):
            imgOut[i,j] = max(oceanFloor,TerrainFunction((j,i)))
        # Increment the counter so the master thread can track progress
        # with counter.get_lock():
        #     counter.value += 1

    # Free resources
    sharedBuffer.close()

    # Nofity parent process
    q.put(0x0)

def subroutine(threadID: int):
    # Access the shared memory region
    sharedBuffer = shared_memory.SharedMemory(
        bufferString, create=False
    )
    imgOut = np.ndarray( # Access the shared memory through a numpy matrix
        outputShape,
        dtype=outputType,
        buffer=sharedBuffer.buf
    )

    # Render lines that are assigned to this thread
    for i in range(threadID, outputResolution, numProcs):
        # Render a line
        for j in range(outputResolution):
            imgOut[i,j] = max(oceanFloor,TerrainFunction(ijToxy((i,j))))
        # Increment the counter so the master thread can track progress
        with counter.get_lock():
            counter.value += 1

    # Free resources
    sharedBuffer.close()


## Render the terrain

plt.figure(figsize=(20,20))

if not args.extremeMemory:
    counter = Value('i', 0)
    dataQueue = Queue()
    processes = []
    for p in range(numProcs):
        processes.append(Process(target=subroutine, args=(p,)))
        processes[p].start()
    print('Rendering terrain...')
    while counter.value < outputResolution:
        for i in range(15):
            time.sleep(1)
            print(f'\tRendered {100.0*(counter.value)/(outputResolution)}%', end='\r')

        plt.clf()
        plt.imshow(imgOut, cmap=plt.get_cmap('terrain'))
        plt.colorbar()
        plt.tight_layout()                                # DEBUG
        plt.savefig(outputDir + 'out-color.png')
    for p in range(numProcs):
        processes[p].join()
else:
    chunk = 500
    chunki = 0
    processes = []
    dataQueue = Queue()
    persist = Value('B', 0)
    for p in range(numProcs):
        processes.append(Process(target=subroutineExtremeMemory, args=(chunki*chunk,(chunki+1)*chunk, dataQueue)))
        processes[p].start()
        chunki += 1
    while chunki < math.ceil(outputResolution/chunk):
        dataQueue.get()
        processes.append(Process(target=subroutineExtremeMemory, args=(chunki*chunk,(chunki+1)*chunk, dataQueue)))
        processes[len(processes)-1].start()
        chunki += 1
    persist.value = 1
    for p in processes:
        p.join()

print()

plt.clf()
plt.imshow(imgOut, cmap=plt.get_cmap('terrain'))
plt.colorbar()
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + 'out-color.png')


## Write the GeoTIFF

imgOut[imgOut==oceanFloor] = -5000.0 # For actual heightmap output, set 'ocean' to the nodata value
imgOut = imgOut.transpose()

projection = f'+proj=ortho +lat_0={latitude} +lon_0={longitude}' # Adjust lat_o and lon_0 for location
transform = Affine.translation(-shore.realShape[0]*0.5,-shore.realShape[1]*0.5) * Affine.scale(1/outputResolution) * Affine.scale(shore.realShape[0])
new_dataset = rasterio.open(
    outputDir + '/out-geo.tif',
    'w',
    driver='GTiff',
    height=imgOut.shape[0],
    width=imgOut.shape[1],
    count=1,
    dtype=imgOut.dtype,
    crs=projection,
    transform=transform,
    nodata=-5000.0
)
new_dataset.write(imgOut, 1)
print(new_dataset.meta)
new_dataset.close()

sharedBuffer.unlink()