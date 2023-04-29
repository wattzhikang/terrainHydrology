#include <stdio.h>

#include <sqlite3.h>
#include <omp.h>

#include "terrainPrimitives.hpp"
#include "terrainElevation.hpp"
#include "floatEndian.hpp"

int main(int argc, char* argv[])
{
  //initialize the GEOS library
  std::vector<GEOSContextHandle_t> geosContexts;
  for (int i = 0; i < omp_get_max_threads(); i++)
  {
    geosContexts.push_back(GEOS_init_r());
  }

  // if there is no input, complain to stderr and exit
  if (argc < 2)
  {
    fprintf(stderr, "No input provided to processTerrainPrimitives\n");
    exit(1);
  }

  // open the sqlite3 database
  // the path to the database is the first argument
  sqlite3 *db;
  if (sqlite3_open_v2(argv[1], &db, SQLITE_OPEN_READWRITE, NULL) != SQLITE_OK)
  {
    fprintf(stderr, "Unable to open the file");
    exit(1);
  }
  // load SpatiaLite as an extension
  sqlite3_enable_load_extension(db, 1);
  sqlite3_load_extension(db, "mod_spatialite", NULL, NULL);

  PrimitiveParameters params(db, geosContexts[0]);


  //perform computations
  const uint8_t anotherNode = 0x2e, allDone = 0x21;
  #pragma omp parallel for
  for (size_t i = 0; i < params.ts.numTs(); i++)
  {
    T& t = params.ts.getT(i);
    t.setElevation(computePrimitiveElevation(
      t, params.hydrology, params.cells, params.ts, params.shore,
      params.resolution, geosContexts[omp_get_thread_num()]
    ));
    fwrite(&anotherNode, sizeof(uint8_t), 1, stdout);
    fflush(stdout);
  }
  fwrite(&allDone, sizeof(uint8_t), 1, stdout);
  fflush(stdout);

  //export outputs
  params.writeToDatabase(db);

  //free resources
  sqlite3_close(db);

  for (GEOSContextHandle_t geosContext : geosContexts)
  {
    GEOS_finish_r(geosContext);
  }
}