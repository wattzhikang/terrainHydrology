import shapefile
from tqdm import trange

from TerrainHydrology.DataModel import ShoreModel, HydrologyNetwork, TerrainHoneycomb, Terrain

import TerrainHydrology.ModelIO.SaveFile as SaveFile

def writeNodeShapefile(progressBar: bool, inputFile: str, lat: float, lon: float, outputFile: str) -> None:
    ## Create the .prj file to be read by GIS software
    with open(f'{outputFile}.prj', 'w') as prj:
        # WKT string with latitude and longitude built in
        prjstr = f'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Orthographic"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Longitude_Of_Center",{lon}],PARAMETER["Latitude_Of_Center",{lat}],UNIT["Meter",1.0]]'
        prj.write(prjstr)
        prj.close()

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
        for nidx in trange(len(hydrology), disable=(not progressBar)):
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