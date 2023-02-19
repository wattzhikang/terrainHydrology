import struct
import os
import sqlite3

import typing

import DataModel
from DataModel import ShoreModel, HydrologyNetwork, TerrainHoneycomb, Terrain

currentVersion = 3

def createDB(dbPath: str, resolution: float, edgeLength: float, lon: float, lat: float) -> sqlite3.Connection:
    initScript = None
    with open(os.path.split(os.path.realpath(__file__))[0] + '/db-init.sql', 'r') as initScriptFile:
        initScript = initScriptFile.read()

    conn = sqlite3.connect(dbPath)

    with conn:
        conn.enable_load_extension(True)
        conn.executescript(initScript) # this method will automatically commit the transaction

        conn.execute('INSERT OR REPLACE INTO Parameters (key, value) VALUES (?, ?)', ('edgeLength', edgeLength))
        conn.execute('INSERT OR REPLACE INTO Parameters (key, value) VALUES (?, ?)', ('resolution', resolution))

        # set the custom projection
        conn.execute('UPDATE spatial_ref_sys SET auth_name = ?, auth_srid = ?, proj4text = ?, srtext = ? WHERE srid = ?', ('custom', 347895, f'+proj=ortho +lat_0={lat} +lon_0={lon}', f'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Orthographic"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Longitude_Of_Center",{lon}],PARAMETER["Latitude_Of_Center",{lat}],UNIT["Meter",1.0]]', 347895))
    
    return conn

def openDB(dbPath: str) -> sqlite3.Connection:
    conn = sqlite3.connect(dbPath)
    conn.enable_load_extension(True)
    conn.execute('SELECT load_extension("mod_spatialite")')
    return conn

def getEdgeLength(db: sqlite3.Connection) -> float:
    with db:
        return float(db.execute('SELECT value FROM Parameters WHERE key = ?', ('edgeLength',)).fetchone()[0])

def getResolution(db: sqlite3.Connection) -> float:
    with db:
        return float(db.execute('SELECT value FROM Parameters WHERE key = ?', ('resolution',)).fetchone()[0])