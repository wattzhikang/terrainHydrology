#include <stdio.h>

#include <omp.h>

#include "hydrologyParameters.hpp"
#include "hydrologyFunctions.hpp"

/*
A list of data structures that will be used:
* A KDTree that will be used to query node locations
* A vector that will store actual node structs (this is where
  the node information will be, such as elevation, priority,
  etc). The tree will merely store an index in the vector
* Some data structure to represent the shore
* A graph
* A list of candidate nodes (this must be parallel)
*/

int main(int argc, char* argv[])
{
  if (argc < 2)
  {
    fprintf(stderr, "No input provided to buildRivers\n");
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

  HydrologyParameters params(db, argv[2], argv[3], argv[4], argv[5], argv[6], argv[7], argv[8], argv[9]);


  // perform computatons
  const uint8_t anotherNode = 0x2e, allDone = 0x21;
  #pragma omp parallel
  {
  // printf("Thread ID: %d\n", omp_get_thread_num());
  while (params.candidates.size() > 0)
  {
    params.lockCandidateVector();
    Primitive selectedCandidate = selectNode(params);
    params.unlockCandidateVector();

    alpha(selectedCandidate, params);

    #pragma omp critical
    {
    // write a byte to the calling program, signalling
    // that a candidate has been processed
    fwrite(&anotherNode, sizeof(uint8_t), 1, stdout);
    fflush(stdout);
    }
  }
  }

  //export outputs
  params.writeToDatabase(db);

  //free resources
  sqlite3_close(db);

  // signal to the calling program that processing
  // is complete
  fwrite(&allDone, sizeof(uint8_t), 1, stdout);
  fflush(stdout);

  return 0;
}