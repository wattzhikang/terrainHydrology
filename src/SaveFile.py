import struct
import os

import typing

import DataModel

currentVersion = 3

def writeDataModel(path: str, edgeLength: float, shore: DataModel.ShoreModel, hydrology: DataModel.HydrologyNetwork=None, cells: DataModel.TerrainHoneycomb=None, Ts: DataModel.Terrain=None):
    with open(path, 'wb') as file:
        file.write(struct.pack('!H', currentVersion)) # version number. Increment every time a breaking change is made

        ## Contents ##
        tableOfContents = {
            'shore': 0,
            'hydrology': 0,
            'honeycomb': 0,
            'primitives': 0
        }
        file.write(struct.pack('!Q', 0))
        file.write(struct.pack('!Q', 0))
        file.write(struct.pack('!Q', 0))
        file.write(struct.pack('!Q', 0))

        tableOfContents['shore'] += struct.calcsize('!H') + struct.calcsize('!Q') + struct.calcsize('!Q') + struct.calcsize('!Q') + struct.calcsize('!Q')

        ## Parameters ##

        file.write(struct.pack('!B', 0)) # coordinate type
        file.write(struct.pack('!f', shore.resolution)) # resolution
        file.write(struct.pack('!f', edgeLength))

        sectionSize = struct.calcsize('!H') + struct.calcsize('!B') + struct.calcsize('!f')*2
        print(f"\tBasic parameters: {sectionSize} bytes")
        tableOfContents['shore'] += sectionSize

        ## Shore ##

        tableOfContents['hydrology'] = tableOfContents['shore']

        sectionSize = 0

        if isinstance(shore, DataModel.ShoreModelImage):
            file.write(struct.pack('!B', 0)) # Indicate that the shore was created from an image and not a shapefile
            sectionSize += struct.calcsize('!B')

            # write the imgray raster shape
            file.write(struct.pack('!Q', shore.rasterShape[0]))
            file.write(struct.pack('!Q', shore.rasterShape[1]))
            # write the imgray raster
            for d0 in range(shore.rasterShape[0]):
                for d1 in range(shore.rasterShape[1]):
                    file.write(struct.pack('!B', shore.imgray[d0][d1]))

            sectionSize += struct.calcsize('!Q')*2 + struct.calcsize('!B')*shore.rasterShape[0] * shore.rasterShape[1]
            print(f"\tshore.imgray: {sectionSize} bytes")
            tableOfContents['hydrology'] += sectionSize

            sectionSize = 0

            # write the shore contour
            file.write(struct.pack('!Q', len(shore.contour)))
            for point in shore.contour:
                file.write(struct.pack('!Q', point[0]))
                file.write(struct.pack('!Q', point[1]))

            sectionSize = struct.calcsize('!Q') + struct.calcsize('!Q') * 2 * len(shore.contour)
            print(f"\tShore contour: {sectionSize} bytes")
            tableOfContents['hydrology'] += sectionSize
        else:
            file.write(struct.pack('!B', 1)) # Indicate that the shore was created from a shapefile and not an image
            sectionSize += struct.calcsize('!B')

            # write the shore contour
            file.write(struct.pack('!Q', len(shore.contour)))
            sectionSize += struct.calcsize('!Q')
            for point in shore.contour:
                file.write(struct.pack('!f', point[0]))
                file.write(struct.pack('!f', point[1]))

                sectionSize += struct.calcsize('!f') * 2

            print(f"\tShore contour: {sectionSize} bytes")
            tableOfContents['hydrology'] += sectionSize

        ## Hydrology data structure ##

        if hydrology is None:
            # Abort writing the file; there's nothing left to write

            ## Write the table of contents ##
            file.seek(struct.calcsize('!H'))
            file.write(struct.pack('!Q', tableOfContents['shore']))
            file.write(struct.pack('!Q', 0))
            file.write(struct.pack('!Q', 0))
            file.write(struct.pack('!Q', 0))

            file.close()

            return

        tableOfContents['honeycomb'] = tableOfContents['hydrology']

        sectionSize = 0

        # write all hydrology primitives
        file.write(struct.pack('!Q', len(hydrology)))
        sectionSize += struct.calcsize('!Q')
        for node in hydrology.allNodes():
            file.write(struct.pack('!I', node.id))
            file.write(struct.pack('!f', node.x()))
            file.write(struct.pack('!f', node.y()))
            file.write(struct.pack('!f', node.elevation))
            file.write(struct.pack('!I', node.parent.id if node.parent is not None else node.id))
            file.write(struct.pack('!I', node.contourIndex if node.parent is None else 0))
            file.write(struct.pack('!B', len(node.rivers)))
            for river in node.rivers:
                file.write(struct.pack('!H', len(river.coords)))
                sectionSize += struct.calcsize('!H')
                for point in river.coords:
                    file.write(struct.pack('!f', point[0]))
                    file.write(struct.pack('!f', point[1]))
                    file.write(struct.pack('!f', point[2]))
                    sectionSize += struct.calcsize('!f')*3
            if cells is not None:
                file.write(struct.pack('!f', node.localWatershed))
                file.write(struct.pack('!f', node.inheritedWatershed))
                file.write(struct.pack('!f', node.flow))
            else:
                file.write(struct.pack('!f', 0.0))
                file.write(struct.pack('!f', 0.0))
                file.write(struct.pack('!f', 0.0))
            sectionSize += struct.calcsize('!I')*2 + struct.calcsize('!H') + struct.calcsize('!f')*6 + struct.calcsize('!B')

        print(f"\tHydrology nodes: {sectionSize} bytes")
        tableOfContents['honeycomb'] += sectionSize


        ## TerrainHoneycomb data structure ##

        if cells is None:
            # Abort writing the file; there's nothing left to write

            ## Write the table of contents ##
            file.seek(struct.calcsize('!H'))
            file.write(struct.pack('!Q', tableOfContents['shore']))
            file.write(struct.pack('!Q', tableOfContents['hydrology']))
            file.write(struct.pack('!Q', tableOfContents['honeycomb']))
            file.write(struct.pack('!Q', 0))

            file.close()

            return

        tableOfContents['primitives'] = tableOfContents['honeycomb']

        #compile list of all primitives
        createdQs: typing.Dict[int, DataModel.Q] = { }
        createdEdges: typing.Dict[int, DataModel.Edge] = { }
        cellsEdges: typing.Dict[int, typing.List[int]] = { }
        downstreamEdges: typing.Dict[int, int] = { }
        for cellID in range(len(hydrology)):
            for edge in cells.cellEdges(cellID):
                if id(edge.Q0) not in createdQs:
                    createdQs[id(edge.Q0)] = edge.Q0
                if id(edge.Q1) not in createdQs:
                    createdQs[id(edge.Q1)] = edge.Q1

                if id(edge) not in createdEdges:
                    createdEdges[id(edge)] = edge

                if cellID not in cellsEdges:
                    cellsEdges[cellID] = [ id(edge) ]
                else:
                    cellsEdges[cellID].append(id(edge))

            outflowRidge = cells.cellOutflowRidge(cellID)
            if outflowRidge is not None:
                downstreamEdges[cellID] = id(outflowRidge)

        # list of Qs
        sectionSize = 0
        file.write(struct.pack('!Q', len(createdQs)))
        for saveID, q in createdQs.items():
            file.write(struct.pack('!Q', saveID))
            file.write(struct.pack('!f', q.position[0]))
            file.write(struct.pack('!f', q.position[1]))
            file.write(struct.pack('!f', q.elevation))
            file.write(struct.pack('!B', len(q.nodes)))
            for node in q.nodes:
                file.write(struct.pack('!Q', node))
                sectionSize += struct.calcsize('!Q')
            sectionSize += struct.calcsize('!Q') + struct.calcsize('!f')*3 + struct.calcsize('!B')

        print(f"\tQs: {sectionSize} bytes")
        tableOfContents['primitives'] += sectionSize

        # list of edges
        sectionSize = 0
        file.write(struct.pack('!Q', len(createdEdges)))
        for saveID, edge in createdEdges.items():
            file.write(struct.pack('!Q', saveID))
            file.write(struct.pack('!Q', id(edge.Q0)))
            file.write(struct.pack('!Q', id(edge.Q1)))
            #bitmap
            file.write(struct.pack(
                '!B',
                (0x4 if edge.hasRiver else 0x0) | (0x2 if edge.isShore else 0x0) | (0x1 if edge.shoreSegment is not None else 0x0)
            ))
            if edge.shoreSegment is not None:
                file.write(struct.pack('!L', edge.shoreSegment[0]))
                file.write(struct.pack('!L', edge.shoreSegment[1]))
                sectionSize += struct.calcsize('!L')*2
            sectionSize += struct.calcsize('!Q')*3 + struct.calcsize('!B')

        print(f"\tEdges: {sectionSize} bytes")
        tableOfContents['primitives'] += sectionSize

        sectionSize = 0
        for cellID in range(len(hydrology)):
            file.write(struct.pack('!B', len(cellsEdges[cellID])))
            file.write(struct.pack('!B', 0x1 if cellID in downstreamEdges else 0x0))
            if cellID in downstreamEdges:
                file.write(struct.pack('!Q', downstreamEdges[cellID]))
                sectionSize += struct.calcsize('!Q')
            for edgeID in cellsEdges[cellID]:
                file.write(struct.pack('!Q', edgeID))
                sectionSize += struct.calcsize('!Q')
            sectionSize += struct.calcsize('!B')*2

        print(f"\tCells Edges: {sectionSize} bytes")
        tableOfContents['primitives'] += sectionSize


        ## Terrain primitives ##

        if Ts is None:
            # Abort writing the file; there's nothing left to write

            ## Write the table of contents ##
            file.seek(struct.calcsize('!H'))
            file.write(struct.pack('!Q', tableOfContents['shore']))
            file.write(struct.pack('!Q', tableOfContents['hydrology']))
            file.write(struct.pack('!Q', tableOfContents['honeycomb']))
            file.write(struct.pack('!Q', 0))

            file.close()

            return

        sectionSize = 0

        file.write(struct.pack('!Q', len(Ts)))
        sectionSize += struct.calcsize('!Q')
        for t in Ts.allTs():
            file.write(struct.pack('!f', t.position[0]))
            file.write(struct.pack('!f', t.position[1]))
            file.write(struct.pack('!I', t.cell))
            file.write(struct.pack('!f', t.elevation))
            sectionSize += struct.calcsize('!I') + struct.calcsize('!f')*3

        print(f"\tTerrain primitives: {sectionSize} bytes")

        ## Write the table of contents ##
        file.seek(struct.calcsize('!H'))
        file.write(struct.pack('!Q', tableOfContents['shore']))
        file.write(struct.pack('!Q', tableOfContents['hydrology']))
        file.write(struct.pack('!Q', tableOfContents['honeycomb']))
        file.write(struct.pack('!Q', tableOfContents['primitives']))

        file.close()

def writeToTerrainModule(pipe, shore, edgeLength, hydrology, cells, Ts):
    pipe.write(struct.pack('!f', 0))
    pipe.write(struct.pack('!f', 0))
    pipe.write(struct.pack('!f', shore.realShape[0]))
    pipe.write(struct.pack('!f', shore.realShape[1]))

    pipe.write(struct.pack('!f', edgeLength))
    pipe.write(struct.pack('!f', shore.resolution)) # resolution

    # write the shore contour
    pipe.write(struct.pack('!Q', len(shore.contour)))
    pipe.write(struct.pack('!I', shore.imgray.shape[0]))
    pipe.write(struct.pack('!I', shore.imgray.shape[1]))
    for point in shore.contour:
        pipe.write(struct.pack('!Q', point[0]))
        pipe.write(struct.pack('!Q', point[1]))

    # write all hydrology primitives
    pipe.write(struct.pack('!Q', len(hydrology)))
    for node in hydrology.allNodes():
        pipe.write(struct.pack('!I', node.id))
        pipe.write(struct.pack('!f', node.x()))
        pipe.write(struct.pack('!f', node.y()))
        pipe.write(struct.pack('!f', node.elevation))
        pipe.write(struct.pack('!I', node.parent.id if node.parent is not None else node.id))
        pipe.write(struct.pack('!I', node.contourIndex if node.parent is None else 0))
        pipe.write(struct.pack('!B', len(node.rivers)))
        for river in node.rivers:
            pipe.write(struct.pack('!H', len(river.coords)))
            for point in river.coords:
                pipe.write(struct.pack('!f', point[0]))
                pipe.write(struct.pack('!f', point[1]))
                pipe.write(struct.pack('!f', point[2]))
        pipe.write(struct.pack('!f', node.localWatershed))
        pipe.write(struct.pack('!f', node.inheritedWatershed))
        pipe.write(struct.pack('!f', node.flow if node.parent is not None else 0))

    # qs
    pipe.write(struct.pack('!Q', len(cells.qs)))
    for q in cells.qs:
        if q is None:
            pipe.write(struct.pack('!B', 0x00))
        else:
            pipe.write(struct.pack('!B', 0xff))
            pipe.write(struct.pack('!f', q.position[0]))
            pipe.write(struct.pack('!f', q.position[1]))
            pipe.write(struct.pack('!f', q.elevation))
            pipe.write(struct.pack('!Q', q.vorIndex))
            pipe.write(struct.pack('!B', len(q.nodes)))
            for node in q.nodes:
                pipe.write(struct.pack('!Q', node))

    # cellsRidges
    pipe.write(struct.pack('!Q', len(cells.cellsRidges)))
    for cellID in cells.cellsRidges:
        pipe.write(struct.pack('!Q', cellID))
        pipe.write(struct.pack('!B', len(cells.cellsRidges[cellID])))
        for ridge in cells.cellsRidges[cellID]:
            pipe.write(struct.pack('!B', len(ridge)))
            pipe.write(struct.pack('!Q', ridge[0].vorIndex))
            if len(ridge) > 1:
                pipe.write(struct.pack('!Q', ridge[1].vorIndex))

    pipe.write(struct.pack('!Q', len(Ts)))
    for t in Ts.allTs():
        pipe.write(struct.pack('!f', t.position[0]))
        pipe.write(struct.pack('!f', t.position[1]))
        pipe.write(struct.pack('!I', t.cell))

def readDataModel(path):
    with open(path, 'rb') as file:
        versionNumber = struct.unpack('!H', file.read(struct.calcsize('!H')))[0]
        if versionNumber != currentVersion:
            raise ValueError('This file was created with a previous version of the hydrology script. It is not compatible')

        # Just ignore the TOC for now
        file.seek(struct.calcsize('!Q') * 4, os.SEEK_CUR)

        coordinateType = struct.unpack('!B', file.read(struct.calcsize('!B')))[0]
        rasterResolution = struct.unpack('!f', file.read(struct.calcsize('!f')))[0]
        edgeLength = struct.unpack('!f', file.read(struct.calcsize('!f')))[0]

        isShapefile = True if struct.unpack('!B', file.read(struct.calcsize('!B')))[0] == 1 else False
        shore = None
        if isShapefile:
            shore = DataModel.ShoreModelShapefile(binaryFile=file)
        else:
            shore = DataModel.ShoreModelImage(rasterResolution, binaryFile=file)
        hydrology = DataModel.HydrologyNetwork(binaryFile=file)
        cells = DataModel.TerrainHoneycomb(resolution=rasterResolution, edgeLength=edgeLength, shore=shore, hydrology=hydrology, binaryFile=file)
        terrain = DataModel.Terrain(binaryFile=file)

        file.close()

        return (rasterResolution, edgeLength, shore, hydrology, cells, terrain)