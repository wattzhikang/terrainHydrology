from .Math import Point
from .HydrologyNetwork import HydrologyNetwork
from .TerrainHoneycomb import TerrainHoneycomb

class TerrainHydrology:
    """This class is intended to tie together the layers of a terrain model.
    
    To use this class, call the constructor and then set the layers as needed.

    """
    def __init__(self, edgeLength: float) -> None:
        self.edgeLength = edgeLength

    def nodeOfPoint(self, point: Point) -> int:
        """Returns the id of the node/cell in which the point is located

        :param point: The point you wish to test
        :type point: Math.Point
        :return: The ID of a node/cell (Returns None if it isn't in a valid cell)
        :rtype: int
        """

        # Throw MissingLayerException if the hydrology or terrain honeycomb layers have not been set
        if self.hydrology is None or self.cells is None:
            raise MissingLayerException


        # check hydrology nodes within a certain distance
        for id in self.hydrology.query_ball_point(point, self.edgeLength):
            # if this point is within the voronoi region of one of those nodes,
            # then that is the point's node
            if self.cells.isInCell(point, id):
                return id
        return None

class MissingLayerException(Exception):
    """This exception is thrown when a method is called that requires a layer that has not been set"""
    pass