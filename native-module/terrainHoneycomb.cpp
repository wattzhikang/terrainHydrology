#include "terrainHoneycomb.hpp"

TerrainHoneycomb::~TerrainHoneycomb()
{
  for (auto const& [index, ridge] : allRidges) {
    delete ridge;
  }

  for (auto const& [index, q] : allQs) {
    delete q;
  }
}

void TerrainHoneycomb::dumpQ
(
  size_t index, Point position, float elevation,
  std::vector<size_t> nodes
)
{
  Q *q = new Q(position, elevation, nodes);

  allQs[index] = q;
}

void TerrainHoneycomb::dumpRidge(
  size_t index, size_t Q0index, size_t Q1index
)
{
  Ridge *ridge = new Ridge(allQs[Q0index], allQs[Q1index]);

  allRidges[index] = ridge;
}

void TerrainHoneycomb::dumpCellRidge(size_t cellID, size_t ridgeIdx)
{
  cellRidges[cellID].push_back(allRidges[ridgeIdx]);
}

Q* TerrainHoneycomb::getQ(size_t idx)
{
  return allQs[idx];
}

std::vector<Ridge*> TerrainHoneycomb::getCellRidges(size_t nodeID)
{
  return cellRidges[nodeID];
}