import shapefile
from tqdm import trange
import typing
import sys

from TerrainHydrology.DataModel import ShoreModel, HydrologyNetwork, TerrainHoneycomb, Terrain

import TerrainHydrology.ModelIO.SaveFile as SaveFile

def writePrjFile(lat: float, lon: float, outputFile: str) -> None:
    ## Create the .prj file to be read by GIS software
    with open(f'{outputFile}.prj', 'w') as prj:
        # WKT string with latitude and longitude built in
        prjstr = f'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Orthographic"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Longitude_Of_Center",{lon}],PARAMETER["Latitude_Of_Center",{lat}],UNIT["Meter",1.0]]'
        prj.write(prjstr)
        prj.close()

def writeNodeShapefile(inputFile: str, lat: float, lon: float, outputFile: str, progressOut: typing.IO=sys.stderr) -> None:
    ## Create the .prj file to be read by GIS software
    writePrjFile(lat, lon, outputFile)

    # Read the data model
    db = SaveFile.openDB(inputFile)
    shore: ShoreModel.ShoreModel = ShoreModel.ShoreModel()
    shore.loadFromDB(db)
    hydrology: HydrologyNetwork.HydrologyNetwork = HydrologyNetwork.HydrologyNetwork(db)
    cells: TerrainHoneycomb.TerrainHoneycomb = TerrainHoneycomb.TerrainHoneycomb()
    cells.loadFromDB(db)
    Ts: Terrain.Terrain = Terrain.Terrain()
    Ts.loadFromDB(db)

    realShape = shore.realShape

    with shapefile.Writer(outputFile, shapeType=1) as w:
        # Relevant fields for nodes
        w.field('id', 'N')
        w.field('parent', 'N')
        w.field('elevation', 'F')
        w.field('localWatershed', 'F')
        w.field('inheritedWatershed', 'F')
        w.field('flow', 'F')

        # add every node
        for nidx in trange(len(hydrology), file=progressOut):
            node = hydrology.node(nidx)

            if node.parent is not None:
                w.record(
                    node.id, node.parent.id,
                    node.elevation, node.localWatershed,
                    node.inheritedWatershed, node.flow
                )
            else:
                # If the node has no parent, then None must be added manually
                w.record(
                    node.id, None,
                    node.elevation, node.localWatershed,
                    node.inheritedWatershed, node.flow
                )
            
            # Add node locations. Note that they must be transformed
            w.point(
                node.x(),
                node.y()
            )

        w.close()

def writeTerrainPrimitiveShapefile(inputFile: str, lat: float, lon: float, outputFile: str, progressOut: typing.IO=sys.stderr) -> None:
    ## Create the .prj file to be read by GIS software
    writePrjFile(lat, lon, outputFile)

    # Read the data model
    db = SaveFile.openDB(inputFile)
    shore: ShoreModel.ShoreModel = ShoreModel.ShoreModel()
    shore.loadFromDB(db)
    hydrology: HydrologyNetwork.HydrologyNetwork = HydrologyNetwork.HydrologyNetwork(db)
    cells: TerrainHoneycomb.TerrainHoneycomb = TerrainHoneycomb.TerrainHoneycomb()
    cells.loadFromDB(db)
    Ts: Terrain.Terrain = Terrain.Terrain()
    Ts.loadFromDB(db)

    with shapefile.Writer(outputFile, shapeType=1) as w:
        # Relevant fields for nodes
        w.field('cellID', 'N')
        w.field('elevation', 'F')

        # add every primitive
        for tidx in trange(len(Ts.allTs()), file=progressOut):
            t = Ts.getT(tidx)

            w.record(t.cell, t.elevation)

            # Add node locations. Note that they must be transformed
            w.point(
                t.position[0],
                t.position[1]
            )

        w.close()

def writeEdgeShapefile(inputFile: str, lat: float, lon: float, outputFile: str, progressOut: typing.IO=sys.stderr) -> None:
    ## Create the .prj file to be read by GIS software
    writePrjFile(lat, lon, outputFile)

    # Read the data model
    db = SaveFile.openDB(inputFile)
    shore: ShoreModel.ShoreModel = ShoreModel.ShoreModel()
    shore.loadFromDB(db)
    hydrology: HydrologyNetwork.HydrologyNetwork = HydrologyNetwork.HydrologyNetwork(db)
    cells: TerrainHoneycomb.TerrainHoneycomb = TerrainHoneycomb.TerrainHoneycomb()
    cells.loadFromDB(db)
    Ts: Terrain.Terrain = Terrain.Terrain()
    Ts.loadFromDB(db)

    with shapefile.Writer(outputFile, shapeType=3) as w:
        w.field('id', 'L')

        for cell in hydrology.allNodes():

            for ridge in cells.cellRidges(cell.id):
                coords = [ ]

                # print(cells.cellRidges(cell.id))

                coords.append(ridge.Q0.position)
                coords.append(ridge.Q1.position)
                
                coords = [(p[0],p[1]) for p in coords]

                w.record(True)

                w.line([list(coords)])

        w.close()

def writeDownstreamEdgeShapefile(inputFile: str, lat: float, lon: float, outputFile: str, progressOut: typing.IO=sys.stderr) -> None:
    ## Create the .prj file to be read by GIS software
    writePrjFile(lat, lon, outputFile)

    # Read the data model
    db = SaveFile.openDB(inputFile)
    shore: ShoreModel.ShoreModel = ShoreModel.ShoreModel()
    shore.loadFromDB(db)
    hydrology: HydrologyNetwork.HydrologyNetwork = HydrologyNetwork.HydrologyNetwork(db)
    cells: TerrainHoneycomb.TerrainHoneycomb = TerrainHoneycomb.TerrainHoneycomb()
    cells.loadFromDB(db)
    Ts: Terrain.Terrain = Terrain.Terrain()
    Ts.loadFromDB(db)

    realShape = shore.realShape

    with shapefile.Writer(outputFile, shapeType=3) as w:
        w.field('id', 'L')

        for edge in cells.cellsDownstreamRidges.values():
            coords = [ ]

            coords.append(edge.Q0.position)
            coords.append(edge.Q1.position)
            
            coords = [(p[0],p[1]) for p in coords]

            w.record(True)

            w.line([list(coords)])

        w.close()

def writeRiverShapefile(inputFile: str, lat: float, lon: float, outputFile: str, progressOut: typing.IO=sys.stderr) -> None:
    ## Create the .prj file to be read by GIS software
    writePrjFile(lat, lon, outputFile)

    # Read the data model
    db = SaveFile.openDB(inputFile)
    shore: ShoreModel.ShoreModel = ShoreModel.ShoreModel()
    shore.loadFromDB(db)
    hydrology: HydrologyNetwork.HydrologyNetwork = HydrologyNetwork.HydrologyNetwork(db)
    cells: TerrainHoneycomb.TerrainHoneycomb = TerrainHoneycomb.TerrainHoneycomb()
    cells.loadFromDB(db)
    Ts: Terrain.Terrain = Terrain.Terrain()
    Ts.loadFromDB(db)
    realShape = shore.realShape

    with shapefile.Writer(outputFile, shapeType=3) as w:
        # The only relevant field for rivers
        w.field('flow', 'F')

        # This loop adds rivers in the same way that they were created
        #for node in hydrology.allMouthNodes():
        for nidx in trange(len(hydrology), file=progressOut):
            node = hydrology.node(nidx)

            leaves = hydrology.allLeaves(node.id)
            for leafNode in leaves:
                # Path from the leaf to the sea
                path = hydrology.pathToNode(node.id, leafNode.id)
                path.reverse()

                # The flow of the river is the flow at the base of
                # its path to the sea, unless this stretch of the
                # river doesn't flow all the way to the sea
                riverFlow = path[len(path)-1].flow
                for ni in range(1,len(path)):
                    upstreamFlow = max([n.flow for n in hydrology.upstream(path[ni].id)])
                    # If this river is merely a tributary to a larger
                    # stream, terminate the course and record the
                    # flow at that point
                    if upstreamFlow > path[ni-1].flow:
                        riverFlow = path[ni].flow
                        break
                w.record(riverFlow)

                coords = list(leafNode.rivers[0].coords)
                # Transform the coordinates
                coords = [(p[0],p[1]) for p in coords]
                w.line([list(coords)])
        w.close()

def writeRidgePrimitiveShapefile(inputFile: str, lat: float, lon: float, outputFile: str, progressOut: typing.IO=sys.stderr) -> None:
    ## Create the .prj file to be read by GIS software
    writePrjFile(lat, lon, outputFile)

    # Read the data model
    db = SaveFile.openDB(inputFile)
    shore: ShoreModel.ShoreModel = ShoreModel.ShoreModel()
    shore.loadFromDB(db)
    hydrology: HydrologyNetwork.HydrologyNetwork = HydrologyNetwork.HydrologyNetwork(db)
    cells: TerrainHoneycomb.TerrainHoneycomb = TerrainHoneycomb.TerrainHoneycomb()
    cells.loadFromDB(db)
    Ts: Terrain.Terrain = Terrain.Terrain()
    Ts.loadFromDB(db)
    realShape = shore.realShape

    with shapefile.Writer(outputFile, shapeType=1) as w:
        # Relevant fields for nodes
        w.field('elevation', 'F')

        # add every primitive
        for qidx in trange(len(cells.qs)):
            q = cells.qs[qidx]

            if q is None:
                continue

            w.record(q.elevation)

            # Add node locations. Note that they must be transformed
            w.point(
                q.position[0],
                q.position[1]
            )

        w.close()