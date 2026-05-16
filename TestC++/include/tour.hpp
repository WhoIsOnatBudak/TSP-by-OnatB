#pragma once

#include "types.hpp"

#include <vector>

double calculateDistance(
    const std::vector<int>& path,
    const Matrix& distances
);

void depositPheromone(
    Matrix& pheromone,
    const std::vector<int>& path,
    double distance,
    double q
);
