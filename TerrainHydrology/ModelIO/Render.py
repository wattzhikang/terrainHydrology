import typing
import matplotlib.pyplot as plt
import numpy as np
import shapely.geometry as geom
from multiprocessing import Process, Pipe, Queue, shared_memory, Value
import rasterio
from rasterio import Affine
import time
import math

from TerrainHydrology.DataModel import ShoreModel, HydrologyNetwork, TerrainHoneycomb, Terrain, TerrainHydrology
from TerrainHydrology.ModelIO import SaveFile
from TerrainHydrology.Utilities import Math

import sys
import typing

def renderDEM(inputFile: str, lat: float, lon: float, outputResolution: int, numProcs: int, outputDir: str, extremeMemory: bool,  progressOut: typing.IO=sys.stderr) -> None:
    # TODO: outputResolution is used as a global variable

    # Read the data model
    db = SaveFile.openDB(inputFile)
    edgeLength = SaveFile.getEdgeLength(db)
    shore: ShoreModel.ShoreModel = ShoreModel.ShoreModel() # TODO: This was a global variable
    shore.loadFromDB(db)
    hydrology: HydrologyNetwork.HydrologyNetwork = HydrologyNetwork.HydrologyNetwork(db) # TODO: This was a global variable
    cells: TerrainHoneycomb.TerrainHoneycomb = TerrainHoneycomb.TerrainHoneycomb()
    cells.loadFromDB(db)
    Ts: Terrain.Terrain = Terrain.Terrain()
    Ts.loadFromDB(db)
    terrainSystem = TerrainHydrology.TerrainHydrology(edgeLength) # TODO: This was a global variable
    terrainSystem.hydrology = hydrology
    terrainSystem.cells = cells

    # TODO: These need to be passed to the child processes. Previously, they were just global variables
    radius = edgeLength / 3
    rwidth = edgeLength / 2

    # oceanFloor is calculated ensure that all land appears as green in the output
    # image. It should be about 25% of the way up the color ramp
    maxq = max([q.elevation for q in cells.allQs() if q is not None])
    # TODO: This was also a global variable
    oceanFloor = 0 - 0.25 * maxq / 0.75

    # TODO: I think this was also a global variable 
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

    if not extremeMemory:
        counter = Value('i', 0)
        dataQueue = Queue()
        processes = []
        for p in range(numProcs):
            processes.append(Process(target=subroutine, args=(p, numProcs, outputResolution, outputShape, outputType, bufferString, radius, rwidth, oceanFloor, terrainSystem, shore, hydrology, Ts, counter)))
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
            processes.append(Process(target=subroutineExtremeMemory, args=(chunki*chunk,(chunki+1)*chunk, dataQueue, outputResolution, outputShape, outputType, bufferString, radius, rwidth, oceanFloor, terrainSystem, shore, hydrology, Ts)))
            processes[p].start()
            chunki += 1
        while chunki < math.ceil(outputResolution/chunk):
            dataQueue.get()
            processes.append(Process(target=subroutineExtremeMemory, args=(chunki*chunk,(chunki+1)*chunk, dataQueue, outputResolution, outputShape, outputType, bufferString, radius, rwidth, oceanFloor, terrainSystem, shore, hydrology, Ts)))
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

    projection = f'+proj=ortho +lat_0={lat} +lon_0={lon}' # Adjust lat_0 and lon_0 for location
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

def ijToxy(ij: typing.Tuple[float,float], outputResolution: int, shore: ShoreModel) -> typing.Tuple[float,float]:
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
def TerrainFunction(point: typing.Tuple[float,float], radius: float, rwidth: float, oceanFloor: float, terrainSystem: TerrainHydrology, shore: ShoreModel, hydrology: HydrologyNetwork, Ts: Terrain) -> float:
    
    # if imgray[point[1]][point[0]]==0: This is why a new data model was implemented
    if not shore.isOnLand(point):
        return oceanFloor

    # Gets and computes influence and elevation values for nearby terrain primitives
    ts = Ts.query_ball_point(point,radius) # Gets all terrain primitives within a radius of the point
    if len(ts) < 1: # if there just aren't any T points around, just put it in the ocean
        return 0
    wts = [w(Math.distance(point,t.position),radius) for t in ts] # "influence field" radii of those primitives
    # TODO: I think this ends up getting different heights for
    hts = [ht(point,t) for t in ts]          # elevations of those primitives

    # Blends the terrain primitives
    ht_ = height_b(hts,wts) # Blends those terrain primitives
    wt_ = wts[0]            # I guess this is supposed to be the influence radius of the closest primitive?
    
    wi=wt_ # IDK why he converts these here
    hi=ht_
    
    nodeID = terrainSystem.nodeOfPoint(point)
    if nodeID is None:
        return hi
    node = hydrology.node(nodeID)
    geomp = geom.Point(point[0],point[1]) # Creates a Shapely point out of the input point
    rs = [ ]
    hrs = [ ]
    wrs = [ ]
    if len(node.rivers) > 0:
        rs  = [e for e in node.rivers if geomp.distance(e) < radius ]
        hrs = [hr(geomp,e,rwidth) for e in rs]
        wrs = [w(geomp.distance(e),radius) for e in rs]
    else: # Sometimes there isn't a river, just a drainage point along the seeeee
        riverPoint = geom.Point(node.x(),node.y(),node.elevation)
        if geomp.distance(riverPoint) < radius:
            rs = [ geomp.distance(riverPoint) ]
            hrs = [ riverPoint.z ]
            wrs = [ w(geomp.distance(riverPoint),radius) ]
    
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

# Height of a terrain primitive
def ht(p: typing.Tuple[float, float], t: Terrain.T) -> float:
    return t.elevation# +pnoise2(p[0]/scale,p[1]/scale,octaves=octaves,persistence=persistence,lacunarity=lacunarity,repeatx=shore.shape[0],repeaty=shore.shape[1],base=0)*10

# Height of a river primitive?
def hr(p: typing.Tuple[float, float], r: float, rwidth: float) -> float:
    d=p.distance(r)
    # TODO profile based on Rosgen classification
    segma = 0.1 * min(rwidth**2,d**2) # I think this is the river profile
    projected = r.interpolate(r.project(p))
    return projected.z+segma

# This returns the "influence field" (Geneveaux et al §7)
def w(d: float, radius: float) -> float:
    if d <1:
        return 1;
    return (max(0,(radius+1)-d)/(((radius)+1)*d))**2

## This is the function that the rendering threads will run
def subroutine(threadID: int, numProcs: int, outputResolution: int, outputShape: typing.Tuple[int,int], outputType: np.dtype, bufferString: str, radius: float, rwidth: float, oceanFloor: float, terrainSystem: TerrainHydrology, shore: ShoreModel, hydrology: HydrologyNetwork, Ts: Terrain, counter: Value):
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
            imgOut[i,j] = max(oceanFloor,TerrainFunction(ijToxy((i,j), outputResolution, shore), radius, rwidth, oceanFloor, terrainSystem, shore, hydrology, Ts))
        # Increment the counter so the master thread can track progress
        with counter.get_lock():
            counter.value += 1

    # Free resources
    sharedBuffer.close()

## This is the function that the rendering threads will run
def subroutineExtremeMemory(start: int, end: int, q: Queue, outputResolution: int, outputShape: typing.Tuple[int,int], outputType: np.dtype, bufferString: str, radius: float, rwidth: float, oceanFloor: float, terrainSystem: TerrainHydrology, shore: ShoreModel, hydrology: HydrologyNetwork, Ts: Terrain):
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
            try:
                imgOut[i,j] = max(oceanFloor,TerrainFunction((j,i), radius, rwidth, oceanFloor, terrainSystem, shore, hydrology, Ts))
            except:
                print(f'Error at {i},{j}')
                raise
        # Increment the counter so the master thread can track progress
        # with counter.get_lock():
        #     counter.value += 1

    # Free resources
    sharedBuffer.close()

    # Nofity parent process
    q.put(0x0)