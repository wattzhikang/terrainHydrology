#include "gtest/gtest.h"

#include <vector>

#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>

#include "../hydrologyFunctions.hpp"
#include "../kdtree.hpp"
#include "../hydrology.hpp"
#include "../forest.hpp"
#include "../terrainElevation.hpp"
#include "../terrainPrimitives.hpp"

namespace
{
    TEST(HydrologyParametersTest, LoadTest) {
        sqlite3 *db;
        sqlite3_open_v2(":memory:", &db, SQLITE_OPEN_READWRITE, NULL);
        sqlite3_enable_load_extension(db, 1);
        sqlite3_load_extension(db, "mod_spatialite", NULL, NULL);

        // initialize database
        // open the file db-init.sql
        // read its contents into a single string and execute it
        FILE *initFile = fopen("../TerrainHydrology/ModelIO/db-init.sql", "r");
        // check for error in opening file
        if (initFile == NULL)
        {
            fprintf(stderr, "Unable to open db-init.sql\n");
            exit(1);
        }
        fseek(initFile, 0, SEEK_END);
        long initFileSize = ftell(initFile);
        rewind(initFile);
        char *initFileContents = (char *)malloc(initFileSize + 1);
        fread(initFileContents, 1, initFileSize, initFile);
        fclose(initFile);
        initFileContents[initFileSize] = '\0';
        sqlite3_exec(db, initFileContents, NULL, NULL, NULL);

        // insert parameters into the Parameters table
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('minX', 0)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('maxX', 297)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('minY', 0)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('maxY', 626)", NULL, NULL, NULL);

        // insert edge length and resolution into the Parameters table
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('edgeLength', 200)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('resolution', 100)", NULL, NULL, NULL);

        // create the table for the river slope raster
        sqlite3_exec(db, "CREATE TABLE RiverSlope (x INTEGER, y INTEGER, slope REAL);", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (0, 0, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (0, 1, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (1, 0, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (1, 1, 0.23)", NULL, NULL, NULL);

        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (0, MakePoint(0, -437, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (1, MakePoint(35, -113, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (2, MakePoint(67, -185, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (3, MakePoint(95, -189, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (4, MakePoint(70, -150, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (5, MakePoint(135, -148, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (6, MakePoint(157, 44, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (7, MakePoint(33, 77, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (8, MakePoint(-140, 8, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (9, MakePoint(0, -437, 347895))", NULL, NULL, NULL);

        sqlite3_exec(db, "ALTER TABLE RiverNodes ADD COLUMN priority INTEGER DEFAULT NULL;", NULL, NULL, NULL);

        sqlite3_exec(db, "INSERT INTO RiverNodes (id, priority, contourIndex, loc) VALUES (0, 1, 0, MakePoint(0, -437, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, priority, contourIndex, loc) VALUES (1, 1, 4, MakePoint(70, -150, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, priority, contourIndex, loc) VALUES (2, 1, 8, MakePoint(-140, 8, 347895))", NULL, NULL, NULL);

        HydrologyParameters params(db, "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9");

        EXPECT_EQ(params.riverSlope.getColumns(), 2);
        EXPECT_EQ(params.riverSlope.getRows(), 2);

        EXPECT_EQ(params.candidates.size(), 3);

        sqlite3_close(db);
    }

    TEST(HydrologyParametersTest, SaveTest) {
        sqlite3 *db;
        sqlite3_open_v2(":memory:", &db, SQLITE_OPEN_READWRITE, NULL);
        sqlite3_enable_load_extension(db, 1);
        sqlite3_load_extension(db, "mod_spatialite", NULL, NULL);

        // initialize database
        // open the file db-init.sql
        // read its contents into a single string and execute it
        FILE *initFile = fopen("../TerrainHydrology/ModelIO/db-init.sql", "r");
        // check for error in opening file
        if (initFile == NULL)
        {
            fprintf(stderr, "Unable to open db-init.sql\n");
            exit(1);
        }
        fseek(initFile, 0, SEEK_END);
        long initFileSize = ftell(initFile);
        rewind(initFile);
        char *initFileContents = (char *)malloc(initFileSize + 1);
        fread(initFileContents, 1, initFileSize, initFile);
        fclose(initFile);
        initFileContents[initFileSize] = '\0';
        sqlite3_exec(db, initFileContents, NULL, NULL, NULL);

        // insert parameters into the Parameters table
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('minX', 0)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('maxX', 297)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('minY', 0)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('maxY', 626)", NULL, NULL, NULL);

        // insert edge length and resolution into the Parameters table
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('edgeLength', 200)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('resolution', 100)", NULL, NULL, NULL);

        // create the table for the river slope raster
        sqlite3_exec(db, "CREATE TABLE RiverSlope (x INTEGER, y INTEGER, slope REAL);", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (0, 0, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (0, 1, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (1, 0, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (1, 1, 0.23)", NULL, NULL, NULL);

        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (0, MakePoint(0, -437, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (1, MakePoint(35, -113, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (2, MakePoint(67, -185, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (3, MakePoint(95, -189, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (4, MakePoint(70, -150, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (5, MakePoint(135, -148, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (6, MakePoint(157, 44, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (7, MakePoint(33, 77, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (8, MakePoint(-140, 8, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (9, MakePoint(0, -437, 347895))", NULL, NULL, NULL);

        sqlite3_exec(db, "ALTER TABLE RiverNodes ADD COLUMN priority INTEGER DEFAULT NULL;", NULL, NULL, NULL);

        sqlite3_exec(db, "INSERT INTO RiverNodes (id, priority, contourIndex, loc) VALUES (0, 1, 0, MakePoint(0, -437, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, priority, contourIndex, loc) VALUES (1, 1, 4, MakePoint(70, -150, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, priority, contourIndex, loc) VALUES (2, 1, 8, MakePoint(-140, 8, 347895))", NULL, NULL, NULL);

        HydrologyParameters params(db, "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9");

        //add nodes to the hydrology
        params.hydrology.addRegularNode(Point(10, 10), 10.0, 0, 0);
        params.hydrology.addRegularNode(Point(20, 20), 20.0, 0, 0);
        params.hydrology.addRegularNode(Point(30, 30), 30.0, 0, 0);

        params.writeToDatabase(db);

        // verify that the correct number of nodes were added
        sqlite3_stmt *stmt;
        sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM RiverNodes;", -1, &stmt, NULL);
        sqlite3_step(stmt);
        EXPECT_EQ(sqlite3_column_int(stmt, 0), 6); // 3 original nodes + 3 new nodes
        sqlite3_finalize(stmt);

        sqlite3_close(db);
    }

    TEST(TerrainPrimitivesTest, LoadTest) {
        sqlite3 *db;
        sqlite3_open_v2(":memory:", &db, SQLITE_OPEN_READWRITE, NULL);
        sqlite3_enable_load_extension(db, 1);
        sqlite3_load_extension(db, "mod_spatialite", NULL, NULL);

        // initialize database
        // open the file db-init.sql
        // read its contents into a single string and execute it
        FILE *initFile = fopen("../TerrainHydrology/ModelIO/db-init.sql", "r");
        // check for error in opening file
        if (initFile == NULL)
        {
            fprintf(stderr, "Unable to open db-init.sql\n");
            exit(1);
        }
        fseek(initFile, 0, SEEK_END);
        long initFileSize = ftell(initFile);
        rewind(initFile);
        char *initFileContents = (char *)malloc(initFileSize + 1);
        fread(initFileContents, 1, initFileSize, initFile);
        fclose(initFile);
        initFileContents[initFileSize] = '\0';
        sqlite3_exec(db, initFileContents, NULL, NULL, NULL);

        // insert parameters into the Parameters table
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('minX', 0)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('maxX', 297)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('minY', 0)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('maxY', 626)", NULL, NULL, NULL);

        // insert edge length and resolution into the Parameters table
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('edgeLength', 200)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Parameters (key, value) VALUES ('resolution', 100)", NULL, NULL, NULL);

        // create the table for the river slope raster
        sqlite3_exec(db, "CREATE TABLE RiverSlope (x INTEGER, y INTEGER, slope REAL);", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (0, 0, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (0, 1, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (1, 0, 0.23)", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverSlope (x, y, slope) VALUES (1, 1, 0.23)", NULL, NULL, NULL);

        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (0, MakePoint(0, -437, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (1, MakePoint(35, -113, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (2, MakePoint(67, -185, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (3, MakePoint(95, -189, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (4, MakePoint(70, -150, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (5, MakePoint(135, -148, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (6, MakePoint(157, 44, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (7, MakePoint(33, 77, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (8, MakePoint(-140, 8, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Shoreline VALUES (9, MakePoint(0, -437, 347895))", NULL, NULL, NULL);

        sqlite3_exec(db, "ALTER TABLE RiverNodes ADD COLUMN priority INTEGER DEFAULT NULL;", NULL, NULL, NULL);

        sqlite3_exec(db, "INSERT INTO RiverNodes (id, parent, contourIndex, loc) VALUES (0, NULL, 0, MakePoint(0, -437, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, parent, contourIndex, loc) VALUES (1, NULL, 4, MakePoint(70, -150, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, parent, contourIndex, loc) VALUES (2, NULL, 8, MakePoint(-140, 8, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, parent, contourIndex, loc) VALUES (3, 0, NULL, MakePoint(10, 10, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, parent, contourIndex, loc) VALUES (3, 0, NULL, MakePoint(20, 20, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO RiverNodes (id, parent, contourIndex, loc) VALUES (3, 0, NULL, MakePoint(30, 30, 347895))", NULL, NULL, NULL);

        // insert some terrain primitives into the database
        sqlite3_exec(db, "INSERT INTO Ts (id, rivercell, elevation, loc) VALUES (0, 0, NULL, MakePoint(0, 0, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Ts (id, rivercell, elevation, loc) VALUES (1, 0, NULL, MakePoint(1, 1, 347895))", NULL, NULL, NULL);
        sqlite3_exec(db, "INSERT INTO Ts (id, rivercell, elevation, loc) VALUES (2, 0, NULL, MakePoint(2, 2, 347895))", NULL, NULL, NULL);

        //initialize the GEOS library
        GEOSContextHandle_t geosContext = GEOS_init_r();

        PrimitiveParameters params(db, geosContext);

        T& t0 = params.ts.getT(0);
        t0.setElevation(0.1);
        T& t1 = params.ts.getT(1);
        t1.setElevation(1.2);
        T& t2 = params.ts.getT(2);
        t2.setElevation(2.3);

        params.writeToDatabase(db);

        // verify that the Ts' elevations were properly recorded
        sqlite3_stmt* stmt;
        sqlite3_prepare_v2(db, "SELECT elevation FROM Ts WHERE id = 0", -1, &stmt, NULL);
        sqlite3_step(stmt);
        double elevation = sqlite3_column_double(stmt, 0);
        sqlite3_finalize(stmt);
        EXPECT_NEAR(0.1, elevation, 0.0001);

        sqlite3_prepare_v2(db, "SELECT elevation FROM Ts WHERE id = 1", -1, &stmt, NULL);
        sqlite3_step(stmt);
        elevation = sqlite3_column_double(stmt, 0);
        sqlite3_finalize(stmt);
        EXPECT_NEAR(1.2, elevation, 0.0001);
        
        sqlite3_prepare_v2(db, "SELECT elevation FROM Ts WHERE id = 2", -1, &stmt, NULL);
        sqlite3_step(stmt);
        elevation = sqlite3_column_double(stmt, 0);
        sqlite3_finalize(stmt);
        EXPECT_NEAR(2.3, elevation, 0.0001);

        GEOS_finish_r(geosContext);
        sqlite3_close(db);
    }
}