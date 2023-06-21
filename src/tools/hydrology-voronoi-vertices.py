#! /usr/bin/env python

import shapefile
from scipy.spatial import Voronoi

def writeVoronoiEdges(outputFile: str, vor: Voronoi) -> None:

    ## Create the .prj file to be read by GIS software
    with open(f'{outputFile}.prj', 'w') as prj:
        prjstr = f'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Orthographic"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Longitude_Of_Center",{args.longitude}],PARAMETER["Latitude_Of_Center",{args.latitude}],UNIT["Meter",1.0]]'
        prj.write(prjstr)
        prj.close()

    with shapefile.Writer(outputFile, shapeType=1) as w:
        w.field('id', 'N')
        # print(vor.vertices)
        for vertexID, vertex in enumerate(vor.vertices):
            w.record(vertexID)
            w.point(vertex[0], vertex[1])
        w.close()