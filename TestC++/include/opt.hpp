#pragma once

#include "types.hpp"

#include <vector>

double orientation(const Point& a, const Point& b, const Point& c);

bool edgesIntersect(
    int a,
    int b,
    int c,
    int d,
    const std::vector<Point>& coords,
    double eps = 1e-9
);

std::vector<int> twoOptCrossCheck(
    const std::vector<int>& path,
    const std::vector<Point>& coords
);
