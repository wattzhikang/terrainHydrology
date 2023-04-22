#include "terrainPrimitives.hpp"

#include <geos_c.h>

#include "floatEndian.hpp"

PrimitiveParameters::PrimitiveParameters(sqlite3 *db, GEOSContextHandle_t geosContext)
{
  /*
  //TODO: Update this commment after changing it to use the new save file
    This method is very similar to HydrologyParameters::HydrologyParameters()

    Though verbose, this method is very simple. Basically,
    1. A variable is declared (unless it is declared in the class)
    2. fread() data into that variable
    3. Adjust the endian order, if necessary
  */

  sqlite3_stmt *stmt;

  // load edgeLength from the Parameters table
  sqlite3_prepare_v2(db, "SELECT key, value FROM Parameters WHERE key='EdgeLength';", -1, &stmt, NULL);
  sqlite3_step(stmt);
  edgeLength = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  // load resolution from the Parameters table
  sqlite3_prepare_v2(db, "SELECT key, value FROM Parameters WHERE key='resolution'", -1, &stmt, NULL);
  sqlite3_step(stmt);
  resolution = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  // load minX, maxX, minY, maxY from the Parameters table
  float minX, maxX, minY, maxY;

  // they are separate records, so we need to query the database for each one
  sqlite3_prepare_v2(db, "SELECT minX FROM Parameters", -1, &stmt, NULL);
  sqlite3_step(stmt);
  minX = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  sqlite3_prepare_v2(db, "SELECT maxX FROM Parameters", -1, &stmt, NULL);
  sqlite3_step(stmt);
  maxX = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  sqlite3_prepare_v2(db, "SELECT minY FROM Parameters", -1, &stmt, NULL);
  sqlite3_step(stmt);
  minY = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  sqlite3_prepare_v2(db, "SELECT maxY FROM Parameters", -1, &stmt, NULL);
  sqlite3_step(stmt);
  maxY = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  hydrology = Hydrology(Point(minX,minY), Point(maxX,maxY), edgeLength);

  /* Read the contour vector, and encode it in a structure
     that OpenCV will understand
   */
  // now read in the points
  sqlite3_prepare_v2(db, "SELECT id, X(loc) AS locX, Y(loc) AS locY FROM Shoreline ORDER BY id", -1, &stmt, NULL);
  std::vector<Point> contour;
  while (sqlite3_step(stmt) == SQLITE_ROW)
  {
    // FYI, there is an implicit conversion from double to float here
    // Also, we aren't using the id column, which is 0
    contour.push_back(Point(sqlite3_column_double(stmt, 1), sqlite3_column_double(stmt, 2)));
  }
  sqlite3_finalize(stmt);

  shore = Shore(contour);

  /*
    Read in the hydrology nodes
  */
  // get records from the RiverNodes table
  sqlite3_stmt *riverRecords;
  sqlite3_prepare_v2(db, "SELECT id, rivernode, AsBinary(geometry) FROM Rivers WHERE rivernode = ?", -1, &riverRecords, NULL);

  sqlite3_prepare_v2(db, "SELECT id, X(loc) AS locX, Y(loc) AS locY, elevation, parent, contourIndex, localwatershed, inheritedwatershed, flow FROM RiverNodes", -1, &stmt, NULL);
  while (sqlite3_step(stmt) == SQLITE_ROW)
  {
    uint32_t nodeID = sqlite3_column_int(stmt, 0);
    float x = sqlite3_column_double(stmt, 1);
    float y = sqlite3_column_double(stmt, 2);
    float elevation = sqlite3_column_double(stmt, 3);
    uint32_t contourIndex = sqlite3_column_int(stmt, 5);
    float localWatershed = sqlite3_column_double(stmt, 6);
    float inheritedWatershed = sqlite3_column_double(stmt, 7);
    float flow = sqlite3_column_double(stmt, 8);

    // the parent column could be NULL, so we need to check for that
    uint32_t parentID;
    if (sqlite3_column_type(stmt, 4) == SQLITE_NULL)
    {
      // the way that we know that this is a root node is that the
      // parentID is the same as the nodeID
      parentID = nodeID;
    }
    else
    {
      parentID = sqlite3_column_int(stmt, 4);
    }

    /*
      Read in the rivers using the GEOS library
    */
    sqlite3_bind_int(riverRecords, 1, nodeID);

    std::vector<GEOSGeometry*> rivers;

    while (sqlite3_step(riverRecords) == SQLITE_ROW)
    {
      // load the WKB data
      // Note: The memory is managed by SQLite, so we don't need to free it
      const uint8_t *wkb = (uint8_t*) sqlite3_column_blob(riverRecords, 2);

      // assert that this geometry is, in fact, a line string
      assert(wkb[1] == 0x02);

      // get the number of points in the line string
      uint16_t numPoints = *((uint16_t*) wkb[5]);
      // determine the byte order
      if (wkb[0] == 0x01)
      {
        // little-endian / network byte order
        numPoints = le16toh(numPoints);
      }
      else
      {
        // big-endian
        numPoints = be16toh(numPoints);
      }

      GEOSCoordSequence *string = GEOSCoordSeq_create_r(geosContext, numPoints, 3);

      for (uint16_t point = 0; point < numPoints; point++)
      {
        // the array of points starts at byte 9
        // each point is 3 doubles, which are 8 bytes each
        size_t offset = 9 + (point * 3 * 8);

        float x,y,z;

        // determine the byte order
        if (wkb[0] == 0x01)
        {
          // little-endian
          uint64_t xOrig = le64toh(*((uint64_t*) (wkb + offset)));
          x = *((float*) &xOrig);
          uint64_t yOrig = le64toh(*((uint64_t*) (wkb + offset + 8)));
          y = *((float*) &yOrig);
          uint64_t zOrig = le64toh(*((uint64_t*) (wkb + offset + 16)));
          z = *((float*) &zOrig);
        }
        else
        {
          // big-endian / network byte order
          uint64_t xOrig = le64toh(*((uint64_t*) (wkb + offset)));
          x = *((float*) &xOrig);
          uint64_t yOrig = le64toh(*((uint64_t*) (wkb + offset + 8)));
          y = *((float*) &yOrig);
          uint64_t zOrig = le64toh(*((uint64_t*) (wkb + offset + 16)));
          z = *((float*) &zOrig);
        }

        GEOSCoordSeq_setXYZ_r(geosContext, string, point, x, y, z);
      }

      rivers.push_back(GEOSGeom_createLineString_r(geosContext, string));
    }

    if (parentID == nodeID)
    {
      hydrology.dumpMouthNode(
        Point(x,y), elevation, 0, contourIndex, rivers,
        inheritedWatershed, localWatershed, flow
      );
    }
    else
    {
      hydrology.dumpRegularNode(
        Point(x,y), elevation, 0, parentID, rivers,
        inheritedWatershed, localWatershed, flow
      );
    }
  }
  sqlite3_finalize(riverRecords);
  sqlite3_finalize(stmt);

  /*
    Read the ridge primitives
  */
  // read ridge primitives from the database

  // we'll need to read the cells that these ridge primitives are in
  sqlite3_stmt *neighborStmt;
  sqlite3_prepare_v2(db, "SELECT rivernode, q FROM Cells WHERE q = ?", -1, &neighborStmt, NULL);

  sqlite3_prepare_v2(db, "SELECT id, elevation, X(loc) AS locX, Y(loc) AS locY FROM Qs", -1, &stmt, NULL);

  while (sqlite3_step(stmt) == SQLITE_ROW)
  {
    uint64_t saveID = sqlite3_column_int64(stmt, 0);
    float elevation = sqlite3_column_double(stmt, 1);
    float x = sqlite3_column_double(stmt, 2);
    float y = sqlite3_column_double(stmt, 3);

    // uint8_t numNeighbors;
    // fread(&numNeighbors, sizeof(uint8_t), 1, stream);

    // get the neighbors
    sqlite3_bind_int64(neighborStmt, 1, saveID);

    std::vector<uint64_t> neighbors;
    while (sqlite3_step(neighborStmt) == SQLITE_ROW)
    {
      uint64_t neighborCellID = sqlite3_column_int64(neighborStmt, 0);
      neighbors.push_back(neighborCellID);
    }

    cells.dumpQ(saveID, Point(x,y), elevation, neighbors);
  }
  sqlite3_finalize(neighborStmt);
  sqlite3_finalize(stmt);

  /*
    Read in created edges
  */
  // read in edges from the Edges table in the database
  sqlite3_prepare_v2(db, "SELECT id, q0, q1 FROM Edges", -1, &stmt, NULL);
  while (sqlite3_step(stmt) == SQLITE_ROW)
  {
    uint64_t saveID = sqlite3_column_int64(stmt, 0);
    uint64_t q0Index = sqlite3_column_int64(stmt, 1);
    uint64_t q1Index = sqlite3_column_int64(stmt, 2);

    cells.dumpRidge(saveID, q0Index, q1Index);
  }

  /*
    Read in the dictionary that maps cells to their edges
  */
  // we can get this information from the EdgeCells view
  sqlite3_prepare_v2(db, "SELECT edge, node0, node1 FROM EdgeCells", -1, &stmt, NULL);
  while (sqlite3_step(stmt) == SQLITE_ROW)
  {
    uint64_t edgeID = sqlite3_column_int64(stmt, 0);
    uint64_t node0ID = sqlite3_column_int64(stmt, 1);
    uint64_t node1ID = sqlite3_column_int64(stmt, 2);

    cells.dumpCellRidge(node0ID, edgeID);
    cells.dumpCellRidge(node1ID, edgeID);
  }

  /*
    Read in the terrain primitives
  */
  // read these in from the Ts table
  sqlite3_prepare_v2(db, "SELECT id, X(loc) AS locX, Y(loc) AS locY FROM Ts", -1, &stmt, NULL);
  while (sqlite3_step(stmt) == SQLITE_ROW)
  {
    uint64_t saveID = sqlite3_column_int64(stmt, 0);
    float x = sqlite3_column_double(stmt, 1);
    float y = sqlite3_column_double(stmt, 2);

    ts.dumpT(Point(x,y), saveID);
  }
}