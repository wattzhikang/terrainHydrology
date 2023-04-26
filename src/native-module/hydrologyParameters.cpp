#include "hydrologyParameters.hpp"

#include <stdio.h>
#include <endian.h>

HydrologyParameters::HydrologyParameters(Point lowerLeft, Point upperRight)
{
  float dimension;
  // this just figures out a nice way to divide the area into tiles
  if (upperRight.x() - lowerLeft.x() > upperRight.y() - lowerLeft.y())
  {
    dimension = (upperRight.x() - lowerLeft.x()) / 10;
  }
  else
  {
    dimension = (upperRight.y() - lowerLeft.y()) / 10;
  }
  hydrology = Hydrology(lowerLeft, upperRight, dimension);
}

HydrologyParameters::HydrologyParameters(sqlite3 *db, char* paIn, char* pcIn, char* sigmaIn, char* etaIn, char* zetaIn, char* slopeRateIn, char* maxTriesIn, char* riverAngleDevIn)
{
  sqlite3_stmt *stmt;

  /* Read the size of the area */

  // load minX, maxX, minY, maxY from the Parameters table
  float minX, maxX, minY, maxY;

  // they are separate records, so we need to query the database for each one
  sqlite3_prepare_v2(db, "SELECT value FROM Parameters WHERE key='minX'", -1, &stmt, NULL);
  sqlite3_step(stmt);
  minX = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  sqlite3_prepare_v2(db, "SELECT value FROM Parameters WHERE key='maxX'", -1, &stmt, NULL);
  sqlite3_step(stmt);
  maxX = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  sqlite3_prepare_v2(db, "SELECT value FROM Parameters WHERE key='minY'", -1, &stmt, NULL);
  sqlite3_step(stmt);
  minY = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  sqlite3_prepare_v2(db, "SELECT value FROM Parameters WHERE key='maxY'", -1, &stmt, NULL);
  sqlite3_step(stmt);
  maxY = sqlite3_column_double(stmt, 0);
  sqlite3_finalize(stmt);

  /* Read in various parameters */

  // parse the parameters from input strings
  Pa = strtof(paIn, NULL);
  Pc = strtof(pcIn, NULL);
  sigma = strtof(sigmaIn, NULL);
  eta = strtof(etaIn, NULL);
  zeta = strtof(zetaIn, NULL);
  slopeRate = strtof(slopeRateIn, NULL);
  maxTries = (int) strtol(maxTriesIn, NULL, 10);
  riverAngleDev = strtof(riverAngleDevIn, NULL);

  // load the edge length from the Parameters table
  sqlite3_prepare_v2(db, "SELECT key, value FROM Parameters WHERE key = 'edgeLength'", -1, &stmt, NULL);
  sqlite3_step(stmt);
  edgeLength = sqlite3_column_double(stmt, 1);
  sqlite3_finalize(stmt);

  // load the resolution from the Parameters table as well
  sqlite3_prepare_v2(db, "SELECT key, value FROM Parameters WHERE key = 'resolution'", -1, &stmt, NULL);
  sqlite3_step(stmt);
  resolution = sqlite3_column_double(stmt, 1);
  sqlite3_finalize(stmt);

  hydrology = Hydrology(Point(minX,minY), Point(maxX,maxY), edgeLength);

  /* Read in the raster data */
  //first, figure out the size of the raster by querying the database
  // find max x and y
  sqlite3_prepare_v2(db, "SELECT MAX(x) FROM RiverSlope", -1, &stmt, NULL);
  sqlite3_step(stmt);
  size_t rasterXsize = sqlite3_column_int(stmt, 0) + 1;
  sqlite3_finalize(stmt);

  sqlite3_prepare_v2(db, "SELECT MAX(y) FROM RiverSlope", -1, &stmt, NULL);
  sqlite3_step(stmt);
  size_t rasterYsize = sqlite3_column_int(stmt, 0) + 1;
  sqlite3_finalize(stmt);

  riverSlope = Raster<float>(rasterYsize, rasterXsize, resolution);
  sqlite3_prepare_v2(db, "SELECT x, y, slope FROM RiverSlope", -1, &stmt, NULL);
  while (sqlite3_step(stmt) == SQLITE_ROW)
  {
    size_t x = sqlite3_column_int(stmt, 0);
    size_t y = sqlite3_column_int(stmt, 1);
    float slope = sqlite3_column_double(stmt, 2);
    riverSlope.set(x, y, slope);
  }
  sqlite3_finalize(stmt);

  /* read in mouth nodes */
  sqlite3_prepare_v2(db, "SELECT id, priority, contourIndex, X(loc) AS locX, Y(loc) AS locY FROM RiverNodes ORDER BY id", -1, &stmt, NULL);
  while (sqlite3_step(stmt) == SQLITE_ROW)
  {
    uint32_t priority = sqlite3_column_int(stmt, 1);
    uint64_t contourIndex = sqlite3_column_int64(stmt, 2);
    float x = sqlite3_column_double(stmt, 3);
    float y = sqlite3_column_double(stmt, 4);
    candidates.push_back(
      hydrology.addMouthNode(
        Point(x,y), 0.0f, priority, contourIndex
      )
    );
  }

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

  distribution = std::normal_distribution<float>(0.0, riverAngleDev);

  omp_init_lock(&candidateVectorLock);
}

HydrologyParameters::HydrologyParameters()
{
  omp_init_lock(&candidateVectorLock);
}

HydrologyParameters::~HydrologyParameters()
{
  omp_destroy_lock(&candidateVectorLock);
}

HydrologyParameters::HydrologyParameters(const HydrologyParameters& other)
: Pa(other.Pa), Pc(other.Pc), maxTries(other.maxTries), riverAngleDev(other.riverAngleDev),
  edgeLength(other.edgeLength), sigma(other.sigma), eta(other.eta), zeta(other.zeta),
  slopeRate(other.slopeRate), resolution(other.resolution), riverSlope(other.riverSlope),
  shore(other.shore), candidates(other.candidates)
{
  omp_init_lock(&candidateVectorLock);
  distribution = std::normal_distribution<float>(0.0, riverAngleDev);
}

HydrologyParameters::HydrologyParameters(HydrologyParameters&& other)
: Pa(std::move(other.Pa)), Pc(std::move(other.Pc)), maxTries(std::move(other.maxTries)),
  riverAngleDev(std::move(other.riverAngleDev)), edgeLength(std::move(other.edgeLength)),
  sigma(std::move(other.sigma)), eta(std::move(other.eta)), zeta(std::move(other.zeta)),
  slopeRate(std::move(other.slopeRate)), resolution(std::move(other.resolution)),
  riverSlope(std::move(other.riverSlope)), shore(std::move(other.shore)),
  candidates(std::move(other.candidates))
{
  omp_init_lock(&candidateVectorLock);
  distribution = std::normal_distribution<float>(0.0, riverAngleDev);
}

HydrologyParameters& HydrologyParameters::operator=(const HydrologyParameters& other)
{
  if (this == &other)
  {
    return *this;
  }

  Pa = other.Pa;
  Pc = other.Pc;
  maxTries = other.maxTries;
  riverAngleDev = other.riverAngleDev;
  edgeLength = other.edgeLength;
  sigma = other.sigma;
  eta = other.eta;
  zeta = other.zeta;
  slopeRate = other.slopeRate;
  resolution = other.resolution;
  riverSlope = other.riverSlope;
  shore = other.shore;
  candidates = other.candidates;

  omp_init_lock(&candidateVectorLock);
  distribution = std::normal_distribution<float>(0.0, riverAngleDev);

  return *this;
}

HydrologyParameters& HydrologyParameters::operator=(HydrologyParameters&& other)
{
  if (this == &other)
  {
    return *this;
  }

  Pa = std::move(other.Pa);
  Pc = std::move(other.Pc);
  maxTries = std::move(other.maxTries);
  riverAngleDev = std::move(other.riverAngleDev);
  edgeLength = std::move(other.edgeLength);
  sigma = std::move(other.sigma);
  eta = std::move(other.eta);
  zeta = std::move(other.zeta);
  slopeRate = std::move(other.slopeRate);
  resolution = std::move(other.resolution);
  riverSlope = std::move(other.riverSlope);
  shore = std::move(other.shore);
  candidates = std::move(other.candidates);

  omp_init_lock(&candidateVectorLock);
  distribution = std::normal_distribution<float>(0.0, riverAngleDev);

  return *this;
}

void HydrologyParameters::lockCandidateVector()
{
  omp_set_lock(&candidateVectorLock);
}

void HydrologyParameters::unlockCandidateVector()
{
  omp_unset_lock(&candidateVectorLock);
}

void HydrologyParameters::writeToDatabase(sqlite3 *db) {
  sqlite3_stmt *stmt;

  // clear existing nodes from the RiverNodes table
  sqlite3_prepare_v2(db, "DELETE FROM RiverNodes", -1, &stmt, NULL);
  sqlite3_step(stmt);
  sqlite3_finalize(stmt);

  // prepare to write nodes to the RiverNodes table
  sqlite3_prepare_v2(db, "INSERT INTO RiverNodes (id, parent, elevation, contourIndex, loc) VALUES (?, ?, ?, ?, MakePoint(?, ?, 347895))", -1, &stmt, NULL);

  // write all river nodes
  // loop through the hydrology's nodes with a foreach loop
  for (Primitive *node : hydrology.allNodes()) {
    // write the node to the database
    sqlite3_bind_int64(stmt, 1, node->getID());
    sqlite3_bind_int64(stmt, 3, node->getElevation());
    sqlite3_bind_int64(stmt, 4, node->getContourIndex());
    sqlite3_bind_double(stmt, 5, node->getLoc().x());
    sqlite3_bind_double(stmt, 6, node->getLoc().y());

    // if the node has no parent, then set its parent ID to the node's own ID
    if (node->getParent() == NULL) {
      sqlite3_bind_int64(stmt, 2, node->getID());
    } else {
      sqlite3_bind_int64(stmt, 2, node->getParent()->getID());
    }

    // execute the statement
    int result = sqlite3_step(stmt);
    // exit with an error if the result was not SQLITE_OK
    if (result != SQLITE_OK && result != SQLITE_DONE) {
      std::cerr << "Error writing river node to database: " << sqlite3_errmsg(db) << std::endl;
      exit(1);
    }

    // clear the bindings
    sqlite3_clear_bindings(stmt);

    // reset the statement
    sqlite3_reset(stmt);
  }

  sqlite3_finalize(stmt);
}