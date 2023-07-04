import sqlite3
import numpy as np
from scipy.spatial import cKDTree

from typing import List, Tuple

class T:
    """Terrain primitive

    Terrain primitives are created with a ``position`` and ``cell``
    attribute. The elevation is computed separately.

    :cvar position: The position of the primitive
    :vartype position: tuple[float,float]
    :cvar cell: The ID of the cell in which this primitive is situated
    :vartype cell: int
    :cvar elevation: The elevation of the primitive
    :vartype elevation: float
    """
    def __init__(self, position, cell):
        self.position = position
        self.cell = cell
        self.elevation = None

class Terrain:
    """Holds and organizes the terrain primitives (:class:`T`)

    :param cells: The TerrainHoneycomb of the land
    :type cells: TerrainHoneycomb
    :param num_points: (Roughly) the number of points in each cell
    :type num_points: int
    """
    def loadFromDB(self, db: sqlite3.Connection):
        """Loads the terrain primitives from a database

        :param db: The database connection
        :type db: sqlite3.Connection
        """
        db.row_factory = sqlite3.Row

        self.cellTsDict = { }
        self.tList = [ ]

        # get all the primitives
        for row in db.execute("SELECT rivercell, elevation, X(loc) AS locX, Y(loc) AS locY FROM Ts"):
            t = T((row["locX"], row["locY"]), row["rivercell"])
            t.elevation = row["elevation"]
            if row["rivercell"] not in self.cellTsDict:
                self.cellTsDict[row["rivercell"]] = [ ]
            self.cellTsDict[row["rivercell"]].append(t)
            self.tList.append(t)

        allpoints_list = [[t.position[0],t.position[1]] for t in self.allTs()]
        allpoints_nd = np.array(allpoints_list)
        self.apkd = cKDTree(allpoints_nd)
    def saveToDB(self, db: sqlite3.Connection):
        """Saves the terrain primitives to a database

        :param db: The database connection
        :type db: sqlite3.Connection
        """
        with db:
            db.execute("DELETE FROM Ts")
            db.executemany("INSERT INTO Ts (id, rivercell, elevation, loc) VALUES (?, ?, ?, MakePoint(?, ?, 347895))", [(idx, t.cell, t.elevation, t.position[0], t.position[1]) for idx, t in enumerate(self.tList)])
    def allTs(self) -> List[T]:
        """Simply returns all the terrain primitives

        :return: A list of all the terrain primitives
        :rtype: list[T]
        """
        return self.tList.copy()
    def cellTsDict(self, cell: int) -> List[T]:
        """Gets the terrain primitives within a given cell

        :param cell: The ID of the cell you wish to query
        :type cell: int
        :return: A list of the terrain primitives in the cell
        :rtype: list[T]
        """
        return self.Ts[cell].copy()
    def getT(self, tid: int) -> T:
        """Gets a terrain primitive identified by its index in the list of all primitives

        :param tid: The index of the primitive you wish to retrieve
        :type tid: int
        :return: The terrain primitive
        :rtype: T
        """
        return self.tList[tid]
    def query_ball_point(self, loc: Tuple[float,float], radius: float) -> List[T]:
        """Gets all terrain primitives within a given radius of a given location

        :param loc: The location you wish to test
        :type loc: tuple[float,float]
        :param radius: The search radius
        :type radius: float
        :return: A list of the primitives within that area
        :rtype: list[T]
        """
        return [self.tList[i] for i in self.apkd.query_ball_point(loc,radius)]
    def __len__(self) -> int:
        """Returns the number of nodes in the forest

        :return: The number of primitives on the map
        :rtype: int
        """
        return len(self.tList)