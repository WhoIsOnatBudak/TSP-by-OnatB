#pragma once

#include "types.hpp"

#include <string>
#include <vector>

void writeOutputFiles(
    const std::string& directory,
    const std::vector<Point>& coords,
    const AcoResult& result
);
