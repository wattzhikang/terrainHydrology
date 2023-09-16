#!/bin/python3

import argparse

from TerrainHydrology.ModelIO import Export

def export(args: argparse.Namespace) -> None:
    if args.nodeOutput is not None:
        Export.writeNodeShapefile(args.inputFile, args.latitude, args.longitude, args.nodeOutput)
    if args.terrainOutput is not None:
        Export.writeTerrainPrimitiveShapefile(args.inputFile, args.latitude, args.longitude, args.terrainOutput)

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
parser_export.set_defaults(func=export)

args = parser.parse_args()
args.func(args)