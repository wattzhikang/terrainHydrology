import shapefile
import sqlite3
import cv2 as cv
import numpy as np
from scipy.spatial import cKDTree

from typing import List

from .Math import Point

class ShoreModel:
    """This class represents the shoreline of the land area.

    Fundamentally, a shoreline is a list of points that make a polygon. This
    polygon represents the land area.

    There are 2 ways to initialize this class. If all of your shapefile files have the same
    name (eg myshore.shp, myshore.shx, myshore.dbf), you can pass in the path to the shapefile,
    minus the extension (eg mydirectory/myshore). If your files have different names, or you
    want to pass in file-like objects, you can pass in the individual files.
    
    :param inputFileName: The path to the shapefile files. Note that this is not a path to a file, but a path to the file minus the extension. Thus, you can only use this parameter if all of your shapefile files have the same name.
    :type inputFileName: str
    :param shpFile: A file-like object containing the .shp file
    :type shpFile: typing.IO
    :param shxFile: A file-like object containing the .shx file
    :type shxFile: typing.IO
    :param dbfFile: A file-like object containing the .dbf file
    :type dbfFile: typing.IO
    """
    def __init__(self, inputFileName: str=None, shpFile=None, shxFile=None, dbfFile=None) -> None:
        reader = None

        if inputFileName is not None:
            reader = shapefile.Reader(inputFileName, shapeType=5)
        elif shpFile is not None and dbfFile is not None:
            reader = shapefile.Reader(shp=shpFile, dbf=dbfFile, shapeType=5)
        elif shpFile is not None and shxFile is not None and dbfFile is not None:
            reader = shapefile.Reader(shp=shpFile, shx=shxFile, dbf=dbfFile, shapeType=5)
        else:
            return

        with reader:
            self.contour = reader.shape(0).points[1:] # the first and last points are identical, so remove them
            self.contour.reverse() # pyshp stores shapes in clockwise order, but we want counterclockwise
            self.contour = np.array(self.contour, dtype=np.dtype(np.float32))

        self.realShape = (max([p[0] for p in self.contour])-min([p[0] for p in self.contour]),max([p[1] for p in self.contour])-min([p[1] for p in self.contour]))
        self.pointTree = cKDTree(self.contour)
    def closestNPoints(self, loc: Point, n: int) -> List[int]:
        """Gets the closest N shoreline points to a given point

        :param loc: The location to test
        :type loc: `Math.Point`
        :param n: The number of points to retrieve
        :type n: int
        :return: The closest N points to loc
        :rtype: List[Math.Point]
        """
        # ensure that the result is un-squeezed
        n = n if n > 1 else [n]
        distances, indices = self.pointTree.query(loc, k=n)
        return indices
    def distanceToShore(self, loc: Point) -> float:
        """Gets the distance between a point and the shore

        The distance is in meters.

        :param loc: The location to test
        :type loc: `Math.Point`
        :return: The distance between `loc` and the shore in meters
        :rtype: float
        """
        # in this class, the contour is stored as x,y, so we put the test points in as x,y
        return cv.pointPolygonTest(self.contour, (loc[0],loc[1]), True)
    def isOnLand(self, loc: Point) -> bool:
        """Determines whether or not a point is on land

        :param loc: The location to test
        :type loc: `Math.Point`
        :return: True if the point is on land, False if otherwise
        :rtype: bool
        """
        return self.distanceToShore(loc) >= 0
    def __getitem__(self, index: int):
        """Gets a point on the shore by index

        :param index: The index
        :type index: int
        :return: The index-th coordinate of the shoreline
        :rtype: `Math.Point`
        """
        # no need to flip the points, since they're stored as x,y
        # no need to convert from a coordinate system, since shapefiles are expected to be in the same coordinate system as the project
        return self.contour[index]
    def __len__(self):
        """The number of points that make up the shore

        :return: The number of points that make up the shore
        :rtype: int
        """
        return len(self.contour)
    def saveToDB(self, db: sqlite3.Connection) -> None:
        """Writes the shoreline to a database

        NOTE: No matter the provenance of a shoreline, whether from an image
        or shapefile, it will be written to the database as a list of points
        in the project coordinate system. So regardless of the source, a
        shoreline should be loaded from the database as a Shapefile shoreline.

        :param db: The database to write to
        :type db: sqlite3.Connection
        """
        with db:
            db.execute('DELETE FROM Shoreline')
            # executemany() opens and closes transactions itself, so we don't need to
            db.executemany("INSERT INTO Shoreline (id, loc) VALUES (?, MakePoint(?, ?, 347895))", [(idx, float(point[0]), float(point[1])) for idx, point in enumerate(self)])
    def loadFromDB(self, db: sqlite3.Connection) -> None:
        """Loads the shoreline from a database

        :param db: The database to load from
        :type db: sqlite3.Connection
        """
        db.row_factory = sqlite3.Row
        cursor = db.execute('SELECT X(loc) AS locX, Y(loc) AS locY FROM Shoreline ORDER BY id')
        self.contour = [(row['locX'], row['locY']) for row in cursor]
        self.contour = np.array(self.contour, dtype=np.float32)

        self.pointTree = cKDTree(self.contour)

        # This will be a problem if the original object was a ShoreModelImage, but we're going to axe that class anyway
        self.realShape = (max([p[0] for p in self.contour])-min([p[0] for p in self.contour]),max([p[1] for p in self.contour])-min([p[1] for p in self.contour]))
