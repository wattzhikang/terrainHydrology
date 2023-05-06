#ifndef TERRAIN_PRIMITIVES_H
#define TERRAIN_PRIMITIVES_H

#include <vector>

#include <sqlite3.h>
#include <opencv2/imgproc.hpp>

#include "hydrology.hpp"
#include "terrainHoneycomb.hpp"
#include "ts.hpp"
#include "shore.hpp"

/**
 * @brief Reads data from the Python module
 * 
 */
class PrimitiveParameters
{
public:
  float edgeLength;
  float resolution;
  Shore shore;
  Hydrology hydrology;
  TerrainHoneycomb cells;
  Terrain ts;
public:
  /**
   * @brief Construct a new Primitive Parameters object
   * 
   * @param db The database to read the context from
   * @param geosContext A GEOSContextHandle will be needed to re-encode the rivers
   */
  PrimitiveParameters(sqlite3 *db, GEOSContextHandle_t geosContext);
  ~PrimitiveParameters() = default;

  /**
   * @brief Writes the terrain primitive elevations to the database
   * 
   * @param db The database to write to
   */
  void writeToDatabase(sqlite3 *db);
};

#endif