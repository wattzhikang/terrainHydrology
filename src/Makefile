CPPFLAGS += -g -Wall -fopenmp -isystem /usr/include/opencv4

GTEST_DIR = tst/googletest/googletest
GTEST_HEADERS = $(GTEST_DIR)/include/gtest/*.h \
				$(GTEST_DIR)/include/gtest/internal/*.h
GTEST_H = $(GTEST_DIR)/include/gtest/gtest.h

.PHONY: clean test

gtest-all.o : 
	@ echo "Compiling Google Test Framework (gtest-all)..."
	@ cd $(GTEST_DIR)/scripts/test && \
	make gtest-all.o && \
	mv gtest-all.o ../../../../../

gtest_main.o : 
	@ echo "Compiling Google Test Framework (gtest_main)"
	@ cd $(GTEST_DIR)/scripts/test && \
	make gtest_main.o && \
	mv gtest_main.o ../../../../../

testsuite.o : tst/testsuite.cpp kdtree.hpp raster.hpp forest.hpp $(GTEST_HEADERS)
	@ echo "Compiling Tests..."
	@ g++ $(CPPFLAGS) -isystem $(GTEST_DIR)/include $^ -c

testsuite : testsuite.o gtest-all.o gtest_main.o terrainHoneycomb.o terrainElevation.o hydrologyFunctions.o hydrologyParameters.o hydrology.o floatEndian.o
	g++ $(CPPFLAGS) $^ -lpthread -lopencv_core -lopencv_imgproc -lgeos_c -o $@

test : testsuite
	@ ./testsuite

floatEndian.o : floatEndian.cpp

hydrology.o : hydrology.cpp hydrology.hpp point.hpp kdtree.hpp forest.hpp

buildRivers.o : buildRivers.cpp hydrology.hpp

hydrologyParameters.o : hydrologyParameters.cpp raster.hpp hydrology.hpp

hydrologyFunctions.o : hydrologyFunctions.cpp hydrologyFunctions.hpp hydrology.hpp hydrologyParameters.hpp

buildRivers: hydrologyFunctions.o hydrologyParameters.o buildRivers.o hydrology.o floatEndian.o
	g++ $^ $(CPPFLAGS) -lopencv_imgproc -lgeos_c -o $@

terrainHoneycomb.o : terrainHoneycomb.cpp terrainHoneycomb.hpp

terrainPrimitives.o : terrainPrimitives.cpp terrainPrimitives.hpp

terrainElevation.o : terrainElevation.cpp terrainElevation.hpp

ts.o : ts.cpp ts.hpp

processTerrainPrimitives.o : processTerrainPrimitives.cpp

terrainPrimitives: ts.o terrainElevation.o terrainHoneycomb.o hydrology.o floatEndian.o terrainPrimitives.o processTerrainPrimitives.o
	g++ $^ $(CPPFLAGS) -lopencv_imgproc -lgeos_c -o $@

clean :
	@ rm -vf terrainPrimitives buildRivers testsuite *.gch *.o
	@ cd $(GTEST_DIR)/scripts/test/ && make clean