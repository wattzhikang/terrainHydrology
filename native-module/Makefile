CPPFLAGS += -g -Wall -fopenmp -isystem /usr/include/opencv4

BIN = ./bin
GEN = $(BIN)/gen

GTEST_DIR = tst/googletest/googletest
GTEST_HEADERS = $(GTEST_DIR)/include/gtest/*.h \
				$(GTEST_DIR)/include/gtest/internal/*.h
GTEST_H = $(GTEST_DIR)/include/gtest/gtest.h

.PHONY: clean test all

all: $(BIN)/buildRivers $(BIN)/terrainPrimitives

$(GEN)/gtest-all.o : 
	@ echo "Compiling Google Test Framework (gtest-all)..."
	@ cd $(GTEST_DIR)/scripts/test && \
	make gtest-all.o && \
	mv gtest-all.o ../../../../../$(GEN)/

$(GEN)/gtest_main.o : 
	@ echo "Compiling Google Test Framework (gtest_main)"
	@ cd $(GTEST_DIR)/scripts/test && \
	make gtest_main.o && \
	mv gtest_main.o ../../../../../$(GEN)/

$(GEN)/testsuite.o : tst/testsuite.cpp kdtree.hpp raster.hpp forest.hpp $(GTEST_HEADERS)
	@ echo "Compiling Tests..."
	@ g++ $(CPPFLAGS) -isystem $(GTEST_DIR)/include $^ -c
	@ mv testsuite.o $(GEN)/

$(GEN)/saveTests.o : tst/saveTests.cpp kdtree.hpp raster.hpp forest.hpp $(GTEST_HEADERS)
	@ echo "Compiling Tests..."
	@ g++ $(CPPFLAGS) -isystem $(GTEST_DIR)/include $^ -c
	@ mv saveTests.o $(GEN)/

$(BIN)/testsuite : $(GEN)/testsuite.o $(GEN)/gtest-all.o $(GEN)/gtest_main.o $(GEN)/terrainHoneycomb.o $(GEN)/terrainElevation.o $(GEN)/hydrologyFunctions.o $(GEN)/hydrologyParameters.o $(GEN)/hydrology.o $(GEN)/floatEndian.o $(GEN)/shore.o
	g++ $(CPPFLAGS) $^ -lsqlite3 -lpthread -lopencv_core -lopencv_imgproc -lgeos_c -o $@

$(BIN)/saveTests : $(GEN)/saveTests.o $(GEN)/gtest-all.o $(GEN)/gtest_main.o $(GEN)/terrainHoneycomb.o $(GEN)/terrainElevation.o $(GEN)/hydrologyFunctions.o $(GEN)/hydrologyParameters.o $(GEN)/hydrology.o $(GEN)/floatEndian.o $(GEN)/shore.o $(GEN)/ts.o $(GEN)/terrainPrimitives.o
	g++ $(CPPFLAGS) $^ -lsqlite3 -lpthread -lopencv_core -lopencv_imgproc -lgeos_c -o $@

test : $(BIN)/testsuite $(BIN)/saveTests
	@ $(BIN)/testsuite
	@ $(BIN)/saveTests

$(GEN)/%.o : %.cpp
	g++ $(CPPFLAGS) -c -o $@ $^

$(BIN)/buildRivers: $(GEN)/hydrologyFunctions.o $(GEN)/hydrologyParameters.o $(GEN)/buildRivers.o $(GEN)/hydrology.o $(GEN)/floatEndian.o $(GEN)/shore.o
	g++ $^ $(CPPFLAGS) -lsqlite3 -lopencv_imgproc -lgeos_c -o $@

$(BIN)/terrainPrimitives: $(GEN)/ts.o $(GEN)/terrainElevation.o $(GEN)/terrainHoneycomb.o $(GEN)/hydrology.o $(GEN)/floatEndian.o $(GEN)/terrainPrimitives.o $(GEN)/processTerrainPrimitives.o $(GEN)/shore.o
	g++ $^ $(CPPFLAGS) -lsqlite3 -lopencv_imgproc -lgeos_c -o $@

clean :
	@ rm -f $(BIN)/buildRivers $(BIN)/terrainPrimitives $(BIN)/testsuite $(BIN)/saveTests $(BIN)/binaryFile *.gch $(GEN)/*
	@ cd $(GTEST_DIR)/scripts/test/ && make clean