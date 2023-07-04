from re import I
import cv2 as cv
from networkx.algorithms.operators import binary
import numpy as np
import networkx as nx
from scipy.spatial import cKDTree
from scipy.spatial import Voronoi
from PIL import Image
import shapely.geometry as geom
import struct
import math
from tqdm import trange
import datetime
import shapefile
import abc
import sqlite3

import typing
from typing import List
from typing import Dict

def openCVFillPolyArray(points: typing.List[typing.Tuple[float,float]]) -> typing.List[np.ndarray]:
    """Formats a list of points into a format that OpenCV will understand

    :param points: The points for format
    :type points: list[tuple[float,float]]
    :return: Returns the points in a format that some OpenCV methods can use
    :rtype: list[np.array[[float,float]]]
    """
    return [ np.array( [ [int(p[0]),int(p[1])] for p in points ] ) ]

def readValue(type, stream):
    buffer = stream.read(struct.calcsize(type))
    return struct.unpack(type, buffer)[0]