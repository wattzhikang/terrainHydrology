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

img = cv.imread(gammaFileName)

imgray = cv.cvtColor(img, cv.COLOR_BGR2GRAY) # a black-and-white version of the input image
rasterShape = imgray.shape
realShape = (imgray.shape[0] * resolution, imgray.shape[1] * resolution)
ret, thresh = cv.threshold(imgray, 127, 255, 0)
contours, hierarchy = cv.findContours(thresh, cv.RETR_LIST, cv.CHAIN_APPROX_NONE)
if len(contours) > 1:
    print('WARNING: Multiple contours identified. The program may not have correctly')
    print('identified the shoreline.')
contour = contours[0]
contour=contour.reshape(-1,2)
contour=np.flip(contour,1)

# fromImageCoordinates(
#     (self.contour[index][1],self.contour[index][0]),
#     self.imgray.shape,
#     self.resolution)

print(f'Before transform: {contour}')
# transform the contour to real-world coordinates
transform = getCoordinateTransformFunction(rasterShape, resolution)
contour = np.array([transform(loc) for loc in contour])
print(f'After transform: {contour}')

# TODO raise exception if dimensions not square
# TODO raise exception if multiple contours

# with shapefile.Writer(outputFile, shapeType=5) as shp:
#     #         0         1          2          3          4          5           6         7        8         (beginning)
#     shape = [ [0,-437], [35,-113], [67,-185], [95,-189], [70,-150], [135,-148], [157,44], [33,77], [-140,8], [0,-437] ]
#     shape.reverse() # pyshp expects shapes to be clockwise

#     shp.field('name', 'C')

#     shp.poly([ shape ])
#     shp.record('polygon0')