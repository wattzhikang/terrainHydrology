#ifndef HYDROPARAMS_H
#define HYDROPARAMS_H

#include <vector>
#include <random>

#include <sqlite3.h>
#include <opencv2/imgproc.hpp>

#include "raster.hpp"
#include "hydrology.hpp"
#include "shore.hpp"

/**
 * @brief A struct that holds all the necessary parameters to generate the river network
 * 
 */
class HydrologyParameters
{
    private:
    omp_lock_t candidateVectorLock;

    public:
    HydrologyParameters();
    /**
     * @brief Construct a blank Hydrology Parameters object
     * 
     * @param lowerLeft The lower left corner of the expected area
     * @param upperRight The upper right corner of the expected area
     */
    HydrologyParameters(Point lowerLeft, Point upperRight);
    /**
     * @brief Construct a new Hydrology Parameters object from a database
     * 
     * The databse should be properly set up with all the parameters, including
     * the raster data.
     * 
     * @param db The database to read the parameters from
     * @param paIn The Pa parameter as a string
     * @param pcIn The Pc parameter as a string
     * @param sigmaIn The sigma parameter as a string
     * @param etaIn The eta parameter as a string
     * @param zetaIn The zeta parameter as a string
     * @param slopeRateIn The slope rate parameter as a string
     * @param maxTriesIn The maximum number of tries parameter as a string
     * @param riverAngleDevIn The river angle standard deviation parameter as a string
     */
    HydrologyParameters(sqlite3 *db, char* paIn, char* pcIn, char* sigmaIn, char* etaIn, char* zetaIn, char* slopeRateIn, char* maxTriesIn, char* riverAngleDevIn);
    ~HydrologyParameters();
    HydrologyParameters(const HydrologyParameters& other);
    HydrologyParameters(HydrologyParameters&& other);

    HydrologyParameters& operator=(const HydrologyParameters& other);
    HydrologyParameters& operator=(HydrologyParameters&& other);

    float Pa, Pc;
    unsigned int maxTries;
    float riverAngleDev;
    float edgeLength;
    float sigma, eta, zeta;
    float slopeRate;
    float resolution;

    Raster<float> riverSlope;

    Shore shore;

    /**
     * @brief Acquires a lock on the vector of candidate nodes
     */
    void lockCandidateVector();
    std::vector<Primitive*> candidates;
    /**
     * @brief Releases the lock on the vector of candidate nodes
     */
    void unlockCandidateVector();
    Hydrology hydrology;

    /**
     * @brief Writes the nodes that have been generated to the database
     * 
     * @param db The database to write to
     */
    void writeToDatabase(sqlite3 *db);

    std::default_random_engine generator;
    std::normal_distribution<float> distribution;
};

#endif