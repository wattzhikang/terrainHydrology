#!/bin/python3

import argparse
import unittest

from TerrainHydrology.ModelIO import Export, Render
from TerrainHydrology.Utilities import BitmapToShapefile
from TerrainHydrology.GeneratorClassic import GeneratorClassic

from TerrainHydrology.TestSuite.tests import *

def generateClassic(args: argparse.Namespace) -> None:
    GeneratorClassic.generateClassic(
        args.inputDomain,
        args.inputTerrain,
        args.inputRiverSlope,
        args.resolution,
        args.numRivers,
        args.num_procs,
        args.num_points,
        args.outputFile,
        args.latitude,
        args.longitude,
        args.accelerate
    )

def export(args: argparse.Namespace) -> None:
    if args.nodeOutput is not None:
        Export.writeNodeShapefile(args.inputFile, args.latitude, args.longitude, args.nodeOutput)
    if args.terrainOutput is not None:
        Export.writeTerrainPrimitiveShapefile(args.inputFile, args.latitude, args.longitude, args.terrainOutput)
    if args.edgeOutput is not None:
        Export.writeEdgeShapefile(args.inputFile, args.latitude, args.longitude, args.edgeOutput)
    if args.downstreamEdgeOutput is not None:
        Export.writeDownstreamEdgeShapefile(args.inputFile, args.latitude, args.longitude, args.downstreamEdgeOutput)
    if args.riverOutput is not None:
        Export.writeRiverShapefile(args.inputFile, args.latitude, args.longitude, args.riverOutput)
    if args.ridgePrimitiveOutput is not None:
        Export.writeRidgePrimitiveShapefile(args.inputFile, args.latitude, args.longitude, args.ridgePrimitiveOutput)

def render(args: argparse.Namespace) -> None:
    Render.renderDEM(args.inputFile, args.latitude, args.longitude, args.outputResolution, args.num_procs, args.outputDir, args.extremeMemory)

def img_to_shp(args: argparse.Namespace) -> None:
    BitmapToShapefile.img_to_shp(args.inputImage, args.latitude, args.longitude, args.resolution, args.outputFile)

parser = argparse.ArgumentParser(
    description='Terrain system based on Genevaux et al., "Terrain Generation Using Procedural Models Based on Hydrology", ACM Transactions on Graphics, 2013'
)

subparsers = parser.add_subparsers(
    title='subcommands',
    description='valid subcommands',
    help='sub-command help'
)

parser_generatorClassic = subparsers.add_parser('generate', help='generate help')
parser_generatorClassic.add_argument(
    '--lat',
    help='Center latitude for the project'' projection',
    dest='latitude',
    metavar='-43.2',
    required=True
)
parser_generatorClassic.add_argument(
    '--lon',
    help='Center longitude for the project'' projection',
    dest='longitude',
    metavar='-103.8',
    required=True
)
parser_generatorClassic.add_argument(
    '-g',
    '--gamma',
    help='An outline of the shore. Should be an ESRI shapefile',
    dest='inputDomain',
    metavar='gamma.shp',
    required=True
)
parser_generatorClassic.add_argument(
    '-s',
    '--river-slope',
    help='Slope of the rivers (not terrain slope). Values in grayscale.',
    dest='inputRiverSlope',
    metavar='rivers.png',
    required=True
)
parser_generatorClassic.add_argument(
    '-t',
    '--terrain-slope',
    help='Slope of the terrain (not river slope). Values in grayscale.',
    dest='inputTerrain',
    metavar='terrain.png',
    required=True
)
parser_generatorClassic.add_argument(
    '-ri',
    '--input-resolution',
    help='The spatial resolution of the input images in meters per pixel',
    dest='resolution',
    metavar='87.5',
    required=True
)
parser_generatorClassic.add_argument(
    '-p',
    '--num-points',
    help='The (rough) number of terrain primitives for each cell',
    dest='num_points',
    metavar='50',
    required=True
)
parser_generatorClassic.add_argument(
    '--num-rivers',
    help='The number of drainages along the coast',
    dest='numRivers',
    metavar='10',
    default=10,
    required=False
)
parser_generatorClassic.add_argument(
    '--accelerate',
    help='Accelerate Your Life™ using parallel processing with a natively-compiled module',
    action='store_true',
    dest='accelerate',
    required=False
)
parser_generatorClassic.add_argument(
    '--num-procs',
    help='The number of processes/threads to use for calculating terrain primitives. This should be the number of cores you have on your system.',
    dest='num_procs',
    metavar='4',
    default=4,
    required=False
)
parser_generatorClassic.add_argument(
    '-o',
    '--output',
    help='File that will contain the data model',
    dest='outputFile',
    metavar='outputFile',
    required=True
)
parser_generatorClassic.set_defaults(func=generateClassic)

parser_export = subparsers.add_parser('export', help='export help')
parser_export.add_argument(
    '--input',
    '-i',
    metavar='data',
    help='File that contains a data model',
    type=str,
    dest='inputFile',
    required=True,
)
parser_export.add_argument(
    '--lat',
    metavar='-43.2',
    help='Center latitude for the output shapefile',
    type=float,
    dest='latitude',
    required=True
)
parser_export.add_argument(
    '--lon',
    metavar='-103.8',
    help='Center longitude for the output shapefile',
    type=float,
    dest='longitude',
    required=True
)
parser_export.add_argument(
    '--output-node',
    '-on',
    metavar='nodes',
    help='Name for the shapefile that will contain the river nodes. Note that shapefiles are composed of multiple files. Thus, if the name of the output is "nodes", the files "nodes.shp", "nodes.shx", "nodes.dbf", "nodes.prj" will be created.',
    type=str,
    dest='nodeOutput',
    required=False
)
parser_export.add_argument(
    '--output-terrain-primitive',
    '-ot',
    metavar='terrainPrimitives',
    help='Name for the shapefile that will contain the terrian primitives. Note that shapefiles are composed of multiple files. Thus, if the name of the output is "nodes", the files "nodes.shp", "nodes.shx", "nodes.dbf", "nodes.prj" will be created.',
    type=str,
    dest='terrainOutput',
    required=False
)
parser_export.add_argument(
    '--output-edges',
    '-oe',
    metavar='edges',
    help='Name for the shapefile that will contain the cell ridges. (This does not include the shoreline, nor edges that rivers flow through.) Note that shapefiles are composed of multiple files. Thus, if the name of the output is "nodes", the files "nodes.shp", "nodes.shx", "nodes.dbf", "nodes.prj" will be created.',
    type=str,
    dest='edgeOutput',
    required=False
)
parser_export.add_argument(
    '--output-ridge-primitive',
    '-oq',
    metavar='ridgePrimitives',
    help='Name for the shapefile that will contain the ridge primitives. Note that shapefiles are composed of multiple files. Thus, if the name of the output is "nodes", the files "nodes.shp", "nodes.shx", "nodes.dbf", "nodes.prj" will be created.',
    type=str,
    dest='ridgePrimitiveOutput',
    required=False
)
parser_export.add_argument(
    '--output-downstream-edge',
    '-ode',
    metavar='downstreamEdges',
    help='Name for the shapefile that will contain the downstream edges. Note that shapefiles are composed of multiple files. Thus, if the name of the output is "nodes", the files "nodes.shp", "nodes.shx", "nodes.dbf", "nodes.prj" will be created.',
    type=str,
    dest='downstreamEdgeOutput',
    required=False
)
parser_export.add_argument(
    '--output-rivers',
    '-or',
    metavar='rivers',
    help='Name for the shapefile that will contain the river paths. Note that shapefiles are composed of multiple files. Thus, if the name of the output is "nodes", the files "nodes.shp", "nodes.shx", "nodes.dbf", "nodes.prj" will be created.',
    type=str,
    dest='riverOutput',
    required=False
)
parser_export.set_defaults(func=export)

parser_render = subparsers.add_parser('render', help='render help')
parser_render.add_argument(
    '-i',
    '--input',
    help='The file that contains the data model you wish to render',
    dest='inputFile',
    metavar='output/data',
    required=True
)
parser_render.add_argument(
    '--lat',
    metavar='-43.2',
    help='Center latitude for the output GeoTIFF',
    type=float,
    dest='latitude',
    required=True
)
parser_render.add_argument(
    '--lon',
    metavar='-103.8',
    help='Center longitude for the output GeoTIFF',
    type=float,
    dest='longitude',
    required=True
)
parser_render.add_argument(
    '-ro',
    '--output-resolution',
    metavar='1000',
    help='The number of pixels/samples on each side of the output raster',
    dest='outputResolution',
    type=int,
    required=True
)
parser_render.add_argument(
    '--num-procs',
    metavar='4',
    help='The number of processes/threads to use in rendering. This should be the number of cores you have on your system.',
    dest='num_procs',
    type=int,
    default=4,
    required=False
)
parser_render.add_argument(
    '-o',
    '--output-dir',
    help='Folder in which to dump all the data generated by this program (including debug data)',
    dest='outputDir',
    metavar='output/',
    required=True
)
parser_render.add_argument(
    '--extreme-memory',
    help='An experimental method of conserving memory when rendering large terrains',
    dest='extremeMemory',
    action='store_true',
    required=False
)
parser_render.set_defaults(func=render)

parser_img_to_shp = subparsers.add_parser('img-to-shp', help='img-to-shp help')
parser_img_to_shp.add_argument(
    '-i',
    '--input',
    help='The input image file',
    dest='inputImage',
    metavar='shoreline.png',
    required=True
)
parser_img_to_shp.add_argument(
    '--lat',
    help='Center latitude for the input image',
    dest='latitude',
    metavar='-43.2',
    required=True,
    type=float
)
parser_img_to_shp.add_argument(
    '--lon',
    help='Center longitude for the input image',
    dest='longitude',
    metavar='-103.8',
    required=True,
    type=float
)
parser_img_to_shp.add_argument(
    '-r',
    '--resolution',
    help='The resolution of the image in meters per pixel',
    dest='resolution',
    metavar='1000',
    required=True,
    type=float
)
parser_img_to_shp.add_argument(
    '-o',
    '--output',
    help='The name of the output shapefiles. Note that this will create several files with the same name but different extensions.',
    dest='outputFile',
    metavar='shoreline',
    required=True
)
parser_img_to_shp.set_defaults(func=img_to_shp)

parser_test = subparsers.add_parser('test', help='test help')
parser_test.set_defaults(func=lambda _: unittest.main())

args = parser.parse_args()
args.func(args)