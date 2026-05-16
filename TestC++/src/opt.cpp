#include "opt.hpp"

#include <algorithm>
#include <set>

double orientation(const Point& a, const Point& b, const Point& c) {
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

bool edgesIntersect(
    int a,
    int b,
    int c,
    int d,
    const std::vector<Point>& coords,
    double eps
) {
    const std::set<int> unique_points = {a, b, c, d};

    if (unique_points.size() < 4) {
        return false;
    }

    const Point& p1 = coords[static_cast<std::size_t>(a)];
    const Point& p2 = coords[static_cast<std::size_t>(b)];
    const Point& p3 = coords[static_cast<std::size_t>(c)];
    const Point& p4 = coords[static_cast<std::size_t>(d)];

    const double o1 = orientation(p1, p2, p3);
    const double o2 = orientation(p1, p2, p4);
    const double o3 = orientation(p3, p4, p1);
    const double o4 = orientation(p3, p4, p2);

    return (
        ((o1 > eps && o2 < -eps) || (o1 < -eps && o2 > eps))
        && ((o3 > eps && o4 < -eps) || (o3 < -eps && o4 > eps))
    );
}

std::vector<int> twoOptCrossCheck(
    const std::vector<int>& path,
    const std::vector<Point>& coords
) {
    std::vector<int> optimized_path = path;
    const std::size_t n_cities = optimized_path.size();

    if (n_cities < 4) {
        return optimized_path;
    }

    bool changed = true;

    while (changed) {
        changed = false;

        for (std::size_t i = 0; i < n_cities - 1; ++i) {
            for (std::size_t j = i + 2; j < n_cities; ++j) {
                if (i == 0 && j == n_cities - 1) {
                    continue;
                }

                const int a = optimized_path[i];
                const int b = optimized_path[(i + 1) % n_cities];
                const int c = optimized_path[j];
                const int d = optimized_path[(j + 1) % n_cities];

                if (edgesIntersect(a, b, c, d, coords)) {
                    std::reverse(
                        optimized_path.begin()
                            + static_cast<std::ptrdiff_t>(i + 1),
                        optimized_path.begin()
                            + static_cast<std::ptrdiff_t>(j + 1)
                    );
                    changed = true;
                }
            }
        }
    }

    return optimized_path;
}
