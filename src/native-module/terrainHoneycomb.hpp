#ifndef HONEYCOMB_H
#define HONEYCOMB_H

#include <vector>
#include <map>

#include <cstddef>

#include "point.hpp"

/**
 * @brief Represents a ridge point
 * 
 */
class Q
{
private:
  Point position;
  float elevation;
  std::vector<size_t> nodes;
public:
  /**
   * @brief Construct a new Q object using data from the Python stream
   * 
   * @param position This primitive's location
   * @param elevation This primitive's elevation
   * @param nodes IDs of the hydrology primitives that this Q borders
   */
  Q
  (
    Point position, float elevation, std::vector<size_t> nodes
  ):
  position(position), elevation(elevation), nodes(nodes)
  {}
  ~Q() = default;
  /**
   * @brief Get the location of this Q
   * 
   * @return const Point The location
   */
  const Point getPosition() const {return position;}
  /**
   * @brief Get the elevation of this Q
   * 
   * @return float The elevation (in meters)
   */
  float getElevation() const {return elevation;}
  /**
   * @brief Get the IDs of the hydrology nodes that this Q borders
   * 
   * @return std::vector<size_t> 
   */
  std::vector<size_t> getNodes() const {return nodes;}
};

/**
 * @brief Represents a ridge, comprised of two Q primitives
 * 
 */
class Ridge
{
private:
  Q *point0, *point1;
public:
  /**
   * @brief Construct a new Ridge object from two Q primitives
   * 
   * @param point0 
   * @param point1 
   */
  Ridge(Q *point0, Q *point1)
  : point0(point0), point1(point1)
  {}
  /**
   * @brief Get end 0 of the ridge
   * 
   * @return Q* 
   */
  Q* getPoint0() const {return point0;}
  /**
   * @brief Get the other end of the ridge
   * 
   * @return Q* 
   */
  Q* getPoint1() const {return point1;}
};

/**
 * @brief This class associates Q primitives with cells and ridges
 * 
 * This class is a subset of the functionality of its analogous
 * Python class. Specifically, it only contains cell _ridges_,
 * which are a subset of edges that consists of edges that are
 * not transected by a river, and are not on the shore. The other
 * edges are not needed for this module's calculations.
 * 
 */
class TerrainHoneycomb
{
private:
  std::map<size_t, Q*> allQs;
  std::map<size_t, Ridge*> allRidges;
  std::map<size_t, std::vector<Ridge*>> cellRidges;
public:
  TerrainHoneycomb() = default;
  ~TerrainHoneycomb();

  /**
   * @brief Creates a Q primitive with the specified properties and appends it ot the vector
   * 
   * This is intended for creating primitives from a binary data stream
   * 
   * @param index The index that the new Q should be created with
   * @param position The position of the new Q
   * @param elevation The elevation of the new Q
   * @param nodes The hydrology primitives that this Q borders, as a vector of cell indices
   */
  void dumpQ(
    size_t index, Point position, float elevation,
    std::vector<size_t> nodes
  );

  /**
   * @brief This is intended for creating a ridge from a binary data stream
   * 
   * This creates a ridge and adds 2 Qs specified by the indices. The ridge
   * will be associated with `index`, and this `index` can be used in
   * `dumpCellRidge()`.
   * 
   * @param index The index for the new ridge
   * @param Q0index The index of an already-existing Q
   * @param Q1index The index of another already-existing Q
   */
  void dumpRidge(
    size_t index, size_t Q0index, size_t Q1index
  );

  /**
   * @brief Associates a Ridge with the ID of a hydrology primitive
   * 
   * This is intended for creating a TerrainHoneycomb from a binary data stream
   * 
   * @param cellID The ID of the hydrology primitive that this ridge encloses
   * @param ridge The ridge
   */
  void dumpCellRidge(size_t cellID, size_t ridgeIdx);

  /**
   * @brief Gets a pointer to the Q primitive at an index within the map
   * 
   * @param idx The index within the map
   * @return Q* This pointer may be NULL if that is what is found at the index
   */
  Q* getQ(size_t idx);

  /**
   * @brief Gets the ridges that enclose a hydrology cell
   * 
   * @param nodeID The ID of the cell
   * @return std::vector<Ridge*> The ridges that enclose it
   */
  std::vector<Ridge*> getCellRidges(size_t nodeID);
};

#endif