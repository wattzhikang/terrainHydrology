from PIL import Image
import struct

from typing import Tuple

class RasterData:
    """A simple abstraction of raster data based on an image.

    Simply input a path to an image and a resolution, and this class will
    allow you to access the data for each point on the surface.

    :param inputFileName: This should be a path to the image
    :type inputFileName: str
    :param resolution: The resolution of the input image in meters per pixel
    :type resolution: float
    
    The image should be
    readable by PIL. The image should represent raster data that covers
    the entire area that will be accessed by the algorithm. The values
    are represented by the grayscale value of each pixel. The image's
    actual color model does not model, as it will be converted to
    grayscale in the constructor.
    """
    def __init__(self, inputFileName: str, resolution: float):
        self.raster = Image.open(inputFileName)
        self.xSize = self.raster.size[0]
        self.ySize = self.raster.size[1]
        self.raster = self.raster.convert('L')
        self.raster = self.raster.load()
        self.resolution = resolution
    def __getitem__(self, loc: Tuple[float,float]) -> float:
        """Gets the value for a particular location

        :param loc: The location to interrogate
        :type loc: tuple[float,float]
        :return: The value of the data at loc
        :rtype: float
        """
        loc = toImageCoordinates(loc, (self.xSize,self.ySize), self.resolution)

        return self.raster[int(loc[0]), int(loc[1])]
    def toBinary(self):
        binary = None
        for y in range(self.ySize):
            # print(f'Working on row {y}')
            row = None
            for x in range(self.xSize):
                if row is not None:
                    row = row + struct.pack('!f', self.raster[x,y])
                else:
                    row = struct.pack('!f', self.raster[x,y])
            if binary is not None:
                binary = binary + row
            else:
                binary = row
        return binary

def toImageCoordinates(loc: Tuple[float,float], imgSize: Tuple[float,float], resolution: float) -> Tuple[float,float]:
    x = loc[0]
    x /= resolution
    x += imgSize[0] * 0.5

    y = loc[1]
    y /= resolution
    y = imgSize[1] * 0.5 - y

    return (x,y)

def fromImageCoordinates(loc: Tuple[float,float], imgSize: Tuple[float,float], resolution: float) -> Tuple[float,float]:
    x = loc[0]
    x -= imgSize[0] * 0.5
    x *= resolution

    y = loc[1]
    y = imgSize[1] * 0.5 - y
    y *= resolution

    return (x,y)