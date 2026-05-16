#pragma once

#include "types.hpp"

DistanceData generateEuclideanDistances(
    int n_cities,
    unsigned int seed = 42,
    double scale = 100.0,
    RandomContext* rng = nullptr
);
