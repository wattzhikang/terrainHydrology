import argparse

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
    required=True
)
parser.add_argument(
    '--lon',
    help='Center longitude for the input image',
    dest='longitude',
    metavar='-103.8',
    required=True
)
parser.add_argument(
    '-r',
    '--resolution',
    help='The resolution of the image in meters per pixel',
    dest='resolution',
    metavar='1000',
    required=True
)
parser.add_argument(
    '-o',
    '--output',
    help='The output shapefile',
    dest='outputFile',
    metavar='shoreline.shp',
    required=True
)
args = parser.parse_args()
