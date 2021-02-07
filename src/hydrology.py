#!/usr/bin/env python

import argparse
import random
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

import DataModel
import HydrologyFunctions
import Math


# Get inputs

parser = argparse.ArgumentParser(
    description='Implementation of Genevaux et al., "Terrain Generation Using Procedural Models Based on Hydrology", ACM Transactions on Graphics, 2013'
)
parser.add_argument(
    '-g',
    '--gamma',
    help='An outline of the shore. Should be a grayscale image (but that doesn\'t have to be the actual color model)',
    dest='inputDomain',
    metavar='gamma.png',
    required=True
)
parser.add_argument(
    '-r',
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
    '-o',
    '--output-dir',
    help='Folder in which to dump all the data generated by this program (including debug data)',
    dest='outputDir',
    metavar='output/',
    required=True
)
args = parser.parse_args()

outputDir = args.outputDir + '/'


### Global Variables

## Inputs
inputDomain = args.inputDomain
inputTerrain = args.inputTerrain
inputRiverSlope = args.inputRiverSlope
resolution = 279.6 # meters per pixel length

## Random Number Generation
globalseed=4314

## Hydrology Parameters

# Number of river mouths
N_majorRivers=10

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
edgeLength = 8000 #4000 # in meters
eta = .75   #   eta * edgeLength is the minimum distance from a node to the coast
sigma = .75 # sigma * edgeLength is the minimum distance between two nodes

## Terrain Parameters
terrainSlopeRate = 1.0 # Maximum rate at which ridges climb in vertical meters per horizontal meter
num_points = 50 # The (rough) number of terrain primitives for each cell

## Rendering Parameters
rwidth = edgeLength / 2

## Multiprocessing Parameters
numProcs = 4

## Output Resolution
outputResolution = 1000 # in pixels
radius = edgeLength / 3


random.seed(globalseed)


# Load input images

shore = DataModel.ShoreModel(inputDomain, resolution)
plt.imshow(shore.imgOutline)                    # DEBUG
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + '0-riverCellNetwork.png') # DEBUG

imStretch = (0,int(shore.rasterShape[0]*resolution),int(shore.rasterShape[1]*resolution),0) # used to stretch debug images

terrainSlope = DataModel.RasterData(inputTerrain, resolution)

riverSlope = DataModel.RasterData(inputRiverSlope, resolution)


# Generate river mouths

hydrology = DataModel.HydrologyNetwork()

firstIdx = random.randint(0,len(shore)-1)
point = shore[firstIdx]
hydrology.addNode(point, 0, random.randint(1,N_majorRivers), contourIndex=firstIdx)

dist = len(shore)/N_majorRivers
for i in range(1,N_majorRivers):
    idx = int((firstIdx+i*dist+random.gauss(0, dist/6))%len(shore))
    point = shore[idx]
    hydrology.addNode(point, 0, random.randint(1,N_majorRivers), contourIndex=idx)

# DEBUG
imgMouthDots = shore.imgOutline.copy()
for node in hydrology.allMouthNodes():
    cv.circle(imgMouthDots, (int(node.x()/resolution),int(node.y()/resolution)), int((shore.rasterShape[0]/512)*10), (255,0,0), -1)
plt.imshow(imgMouthDots)
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + '3-riverMouths.png')


# Generate river nodes

print('Generating rivers...')

params = HydrologyFunctions.HydrologyParameters(
    shore, hydrology, Pa, Pc, maxTries, riverAngleDev, edgeLength, sigma, eta, riverSlope, slopeRate
)
candidates = hydrology.allMouthNodes()
while len(candidates)!=0:
    selectedCandidate = HydrologyFunctions.selectNode(candidates,zeta)
    HydrologyFunctions.alpha(selectedCandidate, candidates, params)
    HydrologyFunctions.calculateHorton_Strahler(selectedCandidate, hydrology)
    print(f'\tNodes Created: {len(hydrology)} \r', end='')  # use display(f) if you encounter performance issues

print()


# Create terrain partition (voronoi cells)

print('Generating terrain ridges...')

cells = DataModel.TerrainHoneycomb(shore, hydrology, resolution)

print('Terrain ridges generated')

pos = [node.position for node in hydrology.allNodes()]
labels = dict(zip(range(len(hydrology)),range(len(hydrology))))
imgRiverHeights = np.zeros(shore.rasterShape,dtype=np.uint16)
for n in range(len(hydrology)):
    if cells.vor_region_id(n) == -1:
        continue
    positions = [(int(p[0]/resolution),int(p[1]/resolution)) for p in cells.ridgePositions(n)]
    #print(f'Node ID: {n}, Positions: {positions}')
    cv.fillPoly(
        imgRiverHeights,
        DataModel.openCVFillPolyArray(positions),
        np.int16(hydrology.node(n).elevation).item()
    )

# DEBUG
fig = plt.figure(figsize=(20,20))
ax = fig.add_subplot(111)
ax.imshow(shore.img, extent=imStretch)
ylim=ax.get_ylim();
xlim=ax.get_xlim();
nx.draw(hydrology.graph,pos,node_size=60,labels=labels,ax=ax)
voronoi_plot_2d(cells.vor, point_size=10, ax=ax,line_colors=['yellow']) # draws the voronoi cells?
ax.set_ylim(ylim);
ax.set_xlim(xlim);
kernel = cv.getStructuringElement(cv.MORPH_RECT,(2,2))#I have no idea what this is, and it isn't used anywhere else
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + '4-riverCellNetwork.png', dpi=100)
plt.clf()

# DEBUG
plt.imshow(cells.imgvoronoi)
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + '5-imgvoronoi.png')
plt.clf()

# DEBUG
plt.imshow(imgRiverHeights, cmap=plt.get_cmap('terrain'))
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + '6-riverHeights.png')

### Breakdown of the image
# Giant red circles identify river mouths
# Blue dots identify river nodes
# Black arrows point upstream
# Black numbers identify the order of the nodes
# Green outline identifies the coast
# Yellow lines outline the voronoi cells around each river node
# Yellow dots identify the vertices of the voronoi cells


# Calculate watershed areas
print('Calculating watershed areas...')

# local watershed areas
for n in range(len(hydrology)):
    node = hydrology.node(n)
    node.localWatershed = cells.cellArea(node.position)
    node.inheritedWatershed = 0

# calculate inherited watershed areas and flow
for node in hydrology.dfsPostorderNodes():  # search nodes in a depth-first post-ordering manner
    watershed = node.localWatershed + sum([n.inheritedWatershed for n in hydrology.upstream(node.id)])
    node.inheritedWatershed=watershed  # calculate total watershed area
    node.flow = 0.42 * watershed**0.69 # calculate river flow


# Calculate ridge elevations
print('Calculating ridge elevations...')

for q in cells.allQs():
    if q is None:
        continue
    nodes = [hydrology.node(n) for n in q.nodes]
    maxElevation = max([node.elevation for node in nodes])
    d = np.linalg.norm(q.position - nodes[0].position)
    slope = terrainSlopeRate * terrainSlope[q.position[0],q.position[1]] / 255
    q.elevation = maxElevation + d * slope


# Classify river nodees

for n in range(len(hydrology)):
    HydrologyFunctions.classify(hydrology.node(n), hydrology, edgeLength)


# DEBUG This is a node graph, like the voronoi graph earlier. But the arrows are weighted by flow

plt.figure(num=None, figsize=(16, 16), dpi=80)
nodes = hydrology.allNodes()
ids = [node.id for node in nodes]
positions = [node.position for node in nodes]
normalizer = max([node.flow for node in nodes])
weights = [6*u.flow/normalizer for u,v in hydrology.allEdges()]
plt.imshow(shore.img, extent=imStretch)
nx.draw(hydrology.graph,positions,node_size=10,labels=labels,width=weights)
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + '7-river-flow.png', dpi=100)


# DEBUG Same thing, but over imgvoronoi instead of the map

plt.figure(num=None, figsize=(16, 16), dpi=80)
plt.imshow(imgRiverHeights, plt.get_cmap('terrain'), extent=imStretch)
nx.draw(hydrology.graph,positions,node_size=60,labels=labels,width=weights)
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + '8-river-flow-terrain.png')

# Terrain pattern

print('Generating terrain primitives...')
Ts = DataModel.Terrain(hydrology, cells, num_points)

# Generate river paths
print('Interpolating river paths...')
for node in hydrology.allMouthNodes():
    # remember that out_edges gets upstream nodes
    leaves = hydrology.allLeaves(node.id)
    for leafNode in leaves: # essentially, this loops through all the highest nodes of a particular mouth
        # path to the leaf (there's only one, so it's the shortest)
        path = hydrology.pathToNode(node.id,leafNode.id)
        path.reverse()

        # terminates the path if there is another path with greater flow, and adds the downflow ridge as a point
        for ni in range(1,len(path)):
            #print(f'path: {[n.id for n in path]}')
            #print(f'ni: {ni}')
            #print(f'Upstream of node {path[ni].id} ({path[ni].position}): {[n.id for n in hydrology.upstream(path[ni].id)]}')
            upstreamFlow = max([n.flow for n in hydrology.upstream(path[ni].id)])
            if upstreamFlow > path[ni-1].flow:
                path = path[0:ni+1]
                break
        
        x = [ ]
        y = [ ]
        z = [ ]
        for pi in range(len(path)):
            p = path[pi]
            x.append(p.x())
            y.append(p.y())
            z.append(p.elevation)
            if p.parent is not None and pi < len(path)-1 and cells.cellOutflowRidge(p.id) is not None:
                ridge0, ridge1 = cells.cellOutflowRidge(p.id)
                x.append((ridge0[0] + ridge1[0])/2)
                y.append((ridge0[1] + ridge1[1])/2)
                z.append((p.elevation + p.parent.elevation)/2)

        #x = np.array([p.x() for p in path])
        #y = np.array([p.y() for p in path])
        #z = np.array([p.elevation for p in path])
        
        # it seems to me that, if the path is short, this block
        # adjusts the positions of the first three nodes
        if len(x)<4:
            x1 = (x[0]+x[1])/2
            x2 = (x[0]+x1)/2
            y1 = (y[0]+y[1])/2
            y2 = (y[0]+y1)/2
            z1 = (z[0]+z[1])/2
            z2 = (z[0]+z1)/2
            tmp = x[1:]
            x = [x[0],x2,x1]+list(tmp)
            x = np.array(x)
            tmp=y[1:]
            y = [y[0],y2,y1]+list(tmp)
            y = np.array(y)
            tmp=z[1:]
            z = [z[0],z2,z1]+list(tmp)
            z = np.array(z)
        
        # I think that this is where the river paths are smoothed
        tck, u = interpolate.splprep([x, y,z], s=0)
        unew = np.arange(0, 1.01, 0.05)
        out = interpolate.splev(unew, tck)
        
        lstr=[] # lstr is apparently "line string"
        dbg=[] # I think this is to verify that altitude increases continually
        for i in range(len(out[0])): # loops through each coordinate created in interpolation
            lstr.append((out[0][i],out[1][i],int(out[2][i])))
            dbg.append(int(out[2][i]))
        line = asLineString(lstr)
        
        for p in path: # for each node in the path to this particular leaf
            # I'm pretty sure this loop ensures that
            # the path to the sea is up to date
            p.rivers.append(line)

# DEBUG
fig = plt.figure(figsize=(20,20))
ax = fig.add_subplot(111)
ax.imshow(shore.img, extent=imStretch)
ylim=ax.get_ylim();
xlim=ax.get_xlim();
voronoi_plot_2d(cells.vor, point_size=10, ax=ax,line_colors=['yellow']) # draws the voronoi cells?
ax.set_ylim(ylim);
ax.set_xlim(xlim);
for mouth in hydrology.allMouthNodes():
    for leaf in hydrology.allLeaves(mouth.id):
        x = [coord[0] for coord in leaf.rivers[0].coords]
        y = [coord[1] for coord in leaf.rivers[0].coords]
        plt.plot(x,y)
for node in hydrology.allNodes():
    plt.text(node.x(),node.y(),node.id)
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + '9-interpolatedRiverCellNetwork.png', dpi=100)

# Calculate elevations of terrain primitives
print('Calculating terrain primitive elevations...')
progressCounter = 0
numTs = len(Ts.allTs())
for t in Ts.allTs():
    ridges = cells.cellRidges(t.cell)
    # find distance to closest sgment, and elevation at that point
    closestRdist = None
    ridgeElevation = None
    for ridge in ridges:
        if len(ridge) < 2:
            q0 = ridge[0]
            dist = Math.distance(q0.position,t.position)
            if closestRdist is None or dist < closestRdist:
                closestRdist = dist
                ridgeElevation = q0.elevation
            continue
        
        q0 = ridge[0]
        q1 = ridge[1]
        dist, isToEndpoint = Math.point_segment_distance_is_endpoint(
            t.position[0],t.position[1],
            q0.position[0],q0.position[1],
            q1.position[0],q1.position[1]
        )
        if closestRdist is not None and dist > closestRdist:
            continue
        if isToEndpoint:
            if Math.distance(q0.position,t.position) < Math.distance(q1.position,t.position):
                closestRdist = Math.distance(q0.position,t.position)
                ridgeElevation = q0.elevation
            else:
                closestRdist = Math.distance(q1.position,t.position)
                ridgeElevation = q1.elevation
        else:
            closestRdist = dist
            ridgeElevation = q0.elevation + (math.sqrt(Math.distance(q0.position,t.position)**2 - dist**2) / Math.distance(q0.position,q1.position)) * (q1.elevation - q0.elevation)
    
    # see if the seeeeee is closer
    dist_gamma = shore.distanceToShore(t.position)
    if closestRdist is None or (dist_gamma < closestRdist):
        closestRdist = dist_gamma
        ridgeElevation = 0
    
    point = geom.Point(t.position[0],t.position[1])
    projected = None
    distancefromN = None
    node = hydrology.node(t.cell)
    if len(node.rivers) > 0:
        local_rivers = node.rivers # tries to get a line to the seeeee
        # index of the point on the interpolated river line that is closest to the Tee point
        rividx = [point.distance(x) for x in local_rivers].index(min([point.distance(x) for x in local_rivers]))
        # gets the point along the river that is the distance along the river to the point nearest to the Tee
        projected = local_rivers[rividx].interpolate(local_rivers[rividx].project(point))
        distancefromN = point.distance(local_rivers[rividx]) # distance to that point
    else: # handle cases of stub rivers
        projected = geom.Point(node.x(),node.y(),node.elevation)
        distancefromN = point.distance(projected)
    
    if distancefromN==0 and closestRdist==0:
        distancefromN=1
    
    lerpedelevation = projected.z*(closestRdist/(closestRdist+distancefromN))+ridgeElevation*(distancefromN/(closestRdist+distancefromN))
    
    t.elevation = lerpedelevation
    
    progressCounter = progressCounter + 1
    print(f'\tPrimitives computed: {progressCounter} out of {numTs} \r', end='')  # use display(f) if you encounter performance issues
print()

# DEBUG
print('Generating terrain primitives image...')
fig = plt.figure(figsize=(16,16))
ax = fig.add_subplot(111)
ax.imshow(shore.img, extent=imStretch)
ax.scatter(*zip(*[t.position for t in Ts.allTs()]), c=[t.elevation for t in Ts.allTs()], cmap=plt.get_cmap('terrain'), s=5, lw=0)
ylim=ax.get_ylim();
xlim=ax.get_xlim();
nx.draw(hydrology.graph,positions,node_size=0,labels=labels,ax=ax)
voronoi_plot_2d(cells.vor, point_size=1, ax=ax,line_colors=['yellow'])
ax.set_ylim(ylim);
ax.set_xlim(xlim);
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + 'a-terrain-primitives.png', dpi=500)

# Render output image

imgOut = np.zeros((outputResolution,outputResolution),dtype=np.double)

def TerrainFunction(prePoint):
    point = [int(prePoint[0] * (shore.realShape[0] / outputResolution)),int(prePoint[1] * (shore.realShape[1] / outputResolution))]
    
    # if imgray[point[1]][point[0]]==0: This is why a new data model was implemented
    if not shore.isOnLand(point):
        return 0

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
    geomp = geom.Point(point[0],point[1])     # Creates a Shapely point out of the input point
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

def height_b(h,w): # height function of a blend node (section 7)
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
def ht(p,t): # Height of a terrain primitive
    return t.elevation# +pnoise2(p[0]/scale,p[1]/scale,octaves=octaves,persistence=persistence,lacunarity=lacunarity,repeatx=shore.shape[0],repeaty=shore.shape[1],base=0)*10

def hr(p,r): # Height of a river primitive?
    d=p.distance(r)
    # TODO profile based on Rosgen classification
    segma = 0.1 * min(rwidth**2,d**2) # I think this is the river profile
    projected = r.interpolate(r.project(p))
    return projected.z+segma

def w(d): # This returns the "influence field" (section 7)
    if d <1:
        return 1;
    return (max(0,(radius+1)-d)/(((radius)+1)*d))**2

def subroutine(conn, q):
    #print(f'Thread ID: {conn.recv()}')
    threadID = conn.recv()
    for i in range(threadID, outputResolution, numProcs):
        arr = np.zeros(outputResolution,dtype=np.double)
        for j in range(outputResolution):
            arr[j] = max(0,TerrainFunction((j,i)))
        try:
            q.put((i,arr.tobytes()))
        except:
            conn.close()
            exit()
        #print(f'row {i} complete')
    
    #conn.send(len(shore))
    conn.close()

# DEBUG
print(f'Highest riverbed elevation: {max([node.elevation for node in hydrology.allNodes()])}')
print(f'Highest ridge elevation: {max([q.elevation for q in cells.allQs() if q is not None])}')


dataQueue = Queue()
pipes = []
processes = []
outputCounter = 0
for p in range(numProcs):
    pipes.append(Pipe())
    processes.append(Process(target=subroutine, args=(pipes[p][1],dataQueue)))
    processes[p].start()
    pipes[p][0].send(p)
for i in trange(outputResolution):
    data = dataQueue.get()
    imgOut[data[0]] = np.frombuffer(data[1],dtype=np.double)

    if outputCounter > 19:
        plt.clf()
        plt.imshow(imgOut, cmap=plt.get_cmap('terrain'))
        plt.colorbar()
        plt.tight_layout()                                # DEBUG
        plt.savefig(outputDir + 'out-color.png')
        outputCounter = 0
    outputCounter += 1
for p in range(numProcs):
    processes[p].join()
    pipes[p][0].close()

plt.clf()
plt.imshow(imgOut, cmap=plt.get_cmap('terrain'))
plt.colorbar()
plt.tight_layout()                                # DEBUG
plt.savefig(outputDir + 'out-color.png')

immtt = np.array(imgOut)
normalizedImg = immtt.copy()
cv.normalize(immtt,  normalizedImg, 0, 255, cv.NORM_MINMAX)
normalizedImg = normalizedImg.astype('uint8')
cv.imwrite(outputDir + "out.png",normalizedImg)