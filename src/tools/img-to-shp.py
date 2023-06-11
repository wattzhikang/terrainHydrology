#! /usr/bin/env python

import argparse
import cv2 as cv
import numpy as np
import shapefile
from typing import Tuple

parser = argparse.ArgumentParser(
    description='Converts a regular image to a shapefile'
)
parser.add_argument(
    '-i',
    '--input',
    help='The input image file',
    dest='inputImage',
    metavar='shoreline.png',
    required=True
)
parser.add_argument(
    '--lat',
    help='Center latitude for the input image',
    dest='latitude',
    metavar='-43.2',
    required=True,
    type=float
)
parser.add_argument(
    '--lon',
    help='Center longitude for the input image',
    dest='longitude',
    metavar='-103.8',
    required=True,
    type=float
)
parser.add_argument(
    '-r',
    '--resolution',
    help='The resolution of the image in meters per pixel',
    dest='resolution',
    metavar='1000',
    required=True,
    type=float
)
parser.add_argument(
    '-o',
    '--output',
    help='The name of the output shapefiles. Note that this will create several files with the same name but different extensions.',
    dest='outputFile',
    metavar='shoreline',
    required=True
)
args = parser.parse_args()

# Transforming from image coordinates to real-world coordinates can be a simple function,
# but it requires a few parameters that are specific to the image. This decorator returns
# a function that does that, but with the paramters already set.
def getCoordinateTransformFunction(imgSize: Tuple[float,float], resolution: float):
    def fromImageCoordinates(loc: Tuple[float,float]):
        x = loc[0]
        x -= imgSize[0] * 0.5
        x *= resolution

        y = loc[1]
        y = imgSize[1] * 0.5 - y
        y *= resolution

        return (x,y)
    
    return fromImageCoordinates

gammaFileName = args.inputImage
latitude = args.latitude
longitude = args.longitude
resolution = args.resolution
outputFile = args.outputFile

# Read the image and convert it to grayscale
img = cv.imread(gammaFileName)
imgray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

rasterShape = imgray.shape

# Find the contours in the image
ret, thresh = cv.threshold(imgray, 127, 255, 0)
contours, hierarchy = cv.findContours(thresh, cv.RETR_LIST, cv.CHAIN_APPROX_NONE)

# We assume that the first contour is the shoreline. If there are multiple contours, there's no way to know which is the shoreline, anyway.
if len(contours) > 1:
    print('WARNING: Multiple contours identified. The program may not have correctly')
    print('identified the shoreline.')
contour = contours[0]

# The shape of the contour array is (N, 1, 2), where N is the number of points in the contour. That middle dimension is unnecessary, so we remove it.
contour=contour.reshape(-1,2)
# Now the array is (N, 2).
# The order of the coordinates is (x,y), so there's no need to flip on that axis.
# But the points are in counterclockwise order. Pyshp expects clockwise order, so we flip the array on that axis.
contour=np.flip(contour,0)

# transform the contour to real-world coordinates
transform = getCoordinateTransformFunction(rasterShape, resolution)
contour = np.array([transform(loc) for loc in contour])

# TODO raise exception if dimensions not square
# TODO raise exception if multiple contours

# Write the shapefile
with shapefile.Writer(outputFile, shapeType=5) as shp:
    shp.field('name', 'C')

    shp.poly([ contour.tolist() ])
    shp.record('polygon0')

# Write the .prj file to be read by GIS software
with open(f'{outputFile}.prj', 'w') as prj:
    prjstr = f'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Orthographic"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Longitude_Of_Center",{args.longitude}],PARAMETER["Latitude_Of_Center",{args.latitude}],UNIT["Meter",1.0]]'
    prj.write(prjstr)
    prj.close()