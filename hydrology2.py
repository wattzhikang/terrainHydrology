#!/bin/python3

import argparse

from TerrainHydrology.ModelIO import Export, Render

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

def render(args: argparse.Namespace) -> None:
    Render.renderDEM(args.inputFile, args.latitude, args.longitude, args.outputResolution, args.num_procs, args.outputDir, args.extremeMemory)

parser = argparse.ArgumentParser(
    description='Terrain system based on Genevaux et al., "Terrain Generation Using Procedural Models Based on Hydrology", ACM Transactions on Graphics, 2013'
)

subparsers = parser.add_subparsers(
    title='subcommands',
    description='valid subcommands',
    help='sub-command help'
)

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

args = parser.parse_args()
args.func(args)