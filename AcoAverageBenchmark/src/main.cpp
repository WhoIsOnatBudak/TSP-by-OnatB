#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <string>
#include <vector>

struct Point {
    double x = 0.0;
    double y = 0.0;
};

using Matrix = std::vector<std::vector<double>>;

struct DistanceData {
    Matrix distances;
    std::vector<Point> coords;
};

enum class EvaporationSchedule {
    Linear,
    Exponential,
    Logarithmic
};

struct Params {
    int n_cities = 100;
    int n_ants = 100;
    int n_iterations = 200;
    double alpha = 1.0;
    double beta = 3.0;
    double evaporation = 0.6;
    double end_evaporation = 0.2;
    double classic_evaporation = 0.5;
    double q = 2000.0;
    double base_pheromone = 1.0;
    double nearest_neighbor_pheromone = 2.0;
    double ant_parameter_variation = 0.1;
    bool cross_check = false;
    int blind_stagnation_limit = 30;
    int blind_iterations = 5;
    double blind_blend_weight = 0.5;
    bool use_min_max_pheromone = true;
    double min_max_tau_ratio = 2.0;
    int pheromone_deposit_top_ants = 1;
    int elitist_weight = 5;
    double max_min_p_best = 0.05;
    EvaporationSchedule evaporation_schedule = EvaporationSchedule::Exponential;
    double evaporation_curve = -2.0;
};

struct AcoResult {
    std::string name;
    std::vector<int> best_path;
    double best_distance = std::numeric_limits<double>::infinity();
};

struct DetailRow {
    int n_cities = 0;
    std::string algorithm;
    double best_distance = 0.0;
    double distance_per_city = 0.0;
};

struct AverageRow {
    std::string algorithm;
    int runs = 0;
    double average_best_distance = 0.0;
    double average_distance_per_city = 0.0;
    double best_distance = std::numeric_limits<double>::infinity();
    double worst_distance = 0.0;
};

enum class Variant {
    BlindBlendAS,
    BaselineAS,
    ElitistAS,
    MaxMinAS
};

std::vector<Variant> allVariants() {
    return {
        Variant::BlindBlendAS,
        Variant::BaselineAS,
        Variant::ElitistAS,
        Variant::MaxMinAS
    };
}

std::string variantName(Variant variant) {
    switch (variant) {
        case Variant::BlindBlendAS:
            return "BlindBlendAS";
        case Variant::BaselineAS:
            return "BaselineAS";
        case Variant::ElitistAS:
            return "ElitistAS";
        case Variant::MaxMinAS:
            return "MaxMinAS";
    }

    return "Unknown";
}

bool usesProjectAdditions(Variant variant) {
    return variant == Variant::BlindBlendAS;
}

double calculateDistance(const std::vector<int>& path, const Matrix& distances) {
    double total = 0.0;

    for (std::size_t index = 0; index + 1 < path.size(); ++index) {
        total += distances[static_cast<std::size_t>(path[index])]
            [static_cast<std::size_t>(path[index + 1])];
    }

    total += distances[static_cast<std::size_t>(path.back())]
        [static_cast<std::size_t>(path.front())];

    return total;
}

double orientation(const Point& a, const Point& b, const Point& c) {
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

bool edgesIntersect(
    int a,
    int b,
    int c,
    int d,
    const std::vector<Point>& coords,
    double eps = 1e-9
) {
    if (a == b || a == c || a == d || b == c || b == d || c == d) {
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

DistanceData generateEuclideanDistances(
    int n_cities,
    unsigned int seed,
    double scale
) {
    std::mt19937 rng(seed);
    std::uniform_real_distribution<double> unit_distribution(0.0, 1.0);
    std::vector<Point> coords(static_cast<std::size_t>(n_cities));

    for (Point& point : coords) {
        point.x = unit_distribution(rng) * scale;
        point.y = unit_distribution(rng) * scale;
    }

    Matrix distances(
        static_cast<std::size_t>(n_cities),
        std::vector<double>(static_cast<std::size_t>(n_cities), 0.0)
    );

    for (int i = 0; i < n_cities; ++i) {
        for (int j = 0; j < n_cities; ++j) {
            const double dx = coords[static_cast<std::size_t>(i)].x
                - coords[static_cast<std::size_t>(j)].x;
            const double dy = coords[static_cast<std::size_t>(i)].y
                - coords[static_cast<std::size_t>(j)].y;
            distances[static_cast<std::size_t>(i)][static_cast<std::size_t>(j)] =
                std::sqrt(dx * dx + dy * dy);
        }
    }

    return {distances, coords};
}

Matrix createFlatPheromone(std::size_t n_cities, double base_pheromone) {
    return Matrix(n_cities, std::vector<double>(n_cities, base_pheromone));
}

Matrix createInitialPheromone(
    const Matrix& distances,
    double base_pheromone,
    double nearest_neighbor_pheromone
) {
    Matrix pheromone = createFlatPheromone(distances.size(), base_pheromone);

    if (distances.size() < 2) {
        return pheromone;
    }

    for (std::size_t city = 0; city < distances.size(); ++city) {
        double best_distance = std::numeric_limits<double>::infinity();
        std::size_t nearest_city = city;

        for (std::size_t candidate = 0; candidate < distances.size(); ++candidate) {
            if (candidate != city && distances[city][candidate] < best_distance) {
                best_distance = distances[city][candidate];
                nearest_city = candidate;
            }
        }

        pheromone[city][nearest_city] = nearest_neighbor_pheromone;
        pheromone[nearest_city][city] = nearest_neighbor_pheromone;
    }

    return pheromone;
}

double getEvaporationRate(
    int iteration,
    int n_iterations,
    double start_evaporation,
    double end_evaporation
) {
    if (n_iterations <= 1) {
        return start_evaporation;
    }

    const double progress = static_cast<double>(iteration)
        / static_cast<double>(n_iterations - 1);
    return start_evaporation
        - (start_evaporation - end_evaporation) * progress;
}

double clamp01(double value) {
    return std::clamp(value, 0.0, 1.0);
}

double exponentialProgress(double progress, double curve) {
    if (std::abs(curve) < 1e-12) {
        return progress;
    }

    const double numerator = std::exp(curve * progress) - 1.0;
    const double denominator = std::exp(curve) - 1.0;

    if (std::abs(denominator) < 1e-12) {
        return progress;
    }

    return clamp01(numerator / denominator);
}

double logarithmicProgress(double progress, double curve) {
    const double bend = std::abs(curve);

    if (bend < 1e-12) {
        return progress;
    }

    const double denominator = std::log1p(bend);

    if (denominator <= 0.0) {
        return progress;
    }

    if (curve >= 0.0) {
        return clamp01(std::log1p(bend * progress) / denominator);
    }

    return clamp01(
        1.0 - std::log1p(bend * (1.0 - progress)) / denominator
    );
}

double getEvaporationRate(
    int iteration,
    int n_iterations,
    double start_evaporation,
    double end_evaporation,
    EvaporationSchedule schedule,
    double curve
) {
    if (n_iterations <= 1) {
        return start_evaporation;
    }

    const double progress = static_cast<double>(iteration)
        / static_cast<double>(n_iterations - 1);
    double shaped_progress = progress;

    switch (schedule) {
        case EvaporationSchedule::Linear:
            shaped_progress = progress;
            break;
        case EvaporationSchedule::Exponential:
            shaped_progress = exponentialProgress(progress, curve);
            break;
        case EvaporationSchedule::Logarithmic:
            shaped_progress = logarithmicProgress(progress, curve);
            break;
    }

    return start_evaporation
        - (start_evaporation - end_evaporation) * shaped_progress;
}

double varyParameter(double value, double variation, std::mt19937& rng) {
    if (variation <= 0.0) {
        return value;
    }

    const double lower_multiplier = std::max(0.0, 1.0 - variation);
    const double upper_multiplier = 1.0 + variation;
    std::uniform_real_distribution<double> distribution(
        lower_multiplier,
        upper_multiplier
    );

    return value * distribution(rng);
}

int chooseByWeights(
    const std::vector<double>& weights,
    double total_weight,
    std::mt19937& rng
) {
    std::uniform_real_distribution<double> distribution(0.0, total_weight);
    const double target = distribution(rng);
    double cumulative = 0.0;

    for (std::size_t city = 0; city < weights.size(); ++city) {
        cumulative += weights[city];

        if (target <= cumulative) {
            return static_cast<int>(city);
        }
    }

    return static_cast<int>(weights.size() - 1);
}

std::vector<int> unvisitedCandidates(const std::vector<bool>& visited) {
    std::vector<int> candidates;

    for (std::size_t city = 0; city < visited.size(); ++city) {
        if (!visited[city]) {
            candidates.push_back(static_cast<int>(city));
        }
    }

    return candidates;
}

std::vector<int> buildAntPath(
    const Matrix& distances,
    const Matrix& pheromone,
    const Params& params,
    double parameter_variation,
    std::mt19937& rng
) {
    const int n_cities = static_cast<int>(distances.size());
    std::uniform_int_distribution<int> start_distribution(0, n_cities - 1);
    const int start_city = start_distribution(rng);
    const double ant_alpha = varyParameter(params.alpha, parameter_variation, rng);
    const double ant_beta = varyParameter(params.beta, parameter_variation, rng);

    std::vector<int> path = {start_city};
    std::vector<bool> visited(static_cast<std::size_t>(n_cities), false);
    visited[static_cast<std::size_t>(start_city)] = true;

    while (static_cast<int>(path.size()) < n_cities) {
        const int current = path.back();
        std::vector<double> probabilities(
            static_cast<std::size_t>(n_cities),
            0.0
        );

        for (int city = 0; city < n_cities; ++city) {
            if (!visited[static_cast<std::size_t>(city)]) {
                const double tau = std::pow(
                    pheromone[static_cast<std::size_t>(current)]
                        [static_cast<std::size_t>(city)],
                    ant_alpha
                );
                const double eta = std::pow(
                    1.0 / distances[static_cast<std::size_t>(current)]
                        [static_cast<std::size_t>(city)],
                    ant_beta
                );
                probabilities[static_cast<std::size_t>(city)] = tau * eta;
            }
        }

        const double total_probability = std::accumulate(
            probabilities.begin(),
            probabilities.end(),
            0.0
        );

        int next_city = 0;

        if (total_probability == 0.0) {
            const std::vector<int> candidates = unvisitedCandidates(visited);
            std::uniform_int_distribution<int> candidate_distribution(
                0,
                static_cast<int>(candidates.size()) - 1
            );
            next_city = candidates[
                static_cast<std::size_t>(candidate_distribution(rng))
            ];
        } else {
            next_city = chooseByWeights(probabilities, total_probability, rng);
        }

        path.push_back(next_city);
        visited[static_cast<std::size_t>(next_city)] = true;
    }

    return path;
}

std::vector<int> buildDistanceOnlyPath(
    const Matrix& distances,
    const Params& params,
    std::mt19937& rng
) {
    const int n_cities = static_cast<int>(distances.size());
    std::uniform_int_distribution<int> start_distribution(0, n_cities - 1);
    const int start_city = start_distribution(rng);
    const double ant_beta = varyParameter(
        params.beta,
        params.ant_parameter_variation,
        rng
    );

    std::vector<int> path = {start_city};
    std::vector<bool> visited(static_cast<std::size_t>(n_cities), false);
    visited[static_cast<std::size_t>(start_city)] = true;

    while (static_cast<int>(path.size()) < n_cities) {
        const int current = path.back();
        std::vector<double> probabilities(
            static_cast<std::size_t>(n_cities),
            0.0
        );

        for (int city = 0; city < n_cities; ++city) {
            if (!visited[static_cast<std::size_t>(city)]) {
                probabilities[static_cast<std::size_t>(city)] = std::pow(
                    1.0 / distances[static_cast<std::size_t>(current)]
                        [static_cast<std::size_t>(city)],
                    ant_beta
                );
            }
        }

        const double total_probability = std::accumulate(
            probabilities.begin(),
            probabilities.end(),
            0.0
        );

        int next_city = 0;

        if (total_probability == 0.0) {
            const std::vector<int> candidates = unvisitedCandidates(visited);
            std::uniform_int_distribution<int> candidate_distribution(
                0,
                static_cast<int>(candidates.size()) - 1
            );
            next_city = candidates[
                static_cast<std::size_t>(candidate_distribution(rng))
            ];
        } else {
            next_city = chooseByWeights(probabilities, total_probability, rng);
        }

        path.push_back(next_city);
        visited[static_cast<std::size_t>(next_city)] = true;
    }

    return path;
}

void depositPheromone(
    Matrix& pheromone,
    const std::vector<int>& path,
    double distance,
    double q,
    double multiplier = 1.0
) {
    const double deposit = multiplier * q / distance;

    for (std::size_t index = 0; index + 1 < path.size(); ++index) {
        const std::size_t a = static_cast<std::size_t>(path[index]);
        const std::size_t b = static_cast<std::size_t>(path[index + 1]);
        pheromone[a][b] += deposit;
        pheromone[b][a] += deposit;
    }

    const std::size_t a = static_cast<std::size_t>(path.back());
    const std::size_t b = static_cast<std::size_t>(path.front());
    pheromone[a][b] += deposit;
    pheromone[b][a] += deposit;
}

std::vector<std::size_t> selectPheromoneDepositIndices(
    const std::vector<double>& all_distances,
    int deposit_top_ants
) {
    std::vector<std::size_t> indices(all_distances.size());
    std::iota(indices.begin(), indices.end(), 0);

    if (deposit_top_ants < 0) {
        return indices;
    }

    const std::size_t deposit_count = std::min(
        static_cast<std::size_t>(deposit_top_ants),
        all_distances.size()
    );

    if (deposit_count == 0) {
        return {};
    }

    std::sort(
        indices.begin(),
        indices.end(),
        [&](std::size_t left, std::size_t right) {
            return all_distances[left] < all_distances[right];
        }
    );
    indices.resize(deposit_count);
    return indices;
}

void evaporate(Matrix& pheromone, double evaporation) {
    for (std::vector<double>& row : pheromone) {
        for (double& value : row) {
            value *= (1.0 - evaporation);
        }
    }
}

void clampPheromone(Matrix& pheromone, double tau_min, double tau_max) {
    for (std::vector<double>& row : pheromone) {
        for (double& value : row) {
            value = std::clamp(value, tau_min, tau_max);
        }
    }
}

bool calculateMinMaxBounds(
    double q,
    double evaporation,
    double best_distance,
    int n_cities,
    double tau_ratio,
    double& tau_min,
    double& tau_max
) {
    if (
        n_cities <= 0
        || best_distance <= 0.0
        || !std::isfinite(best_distance)
    ) {
        return false;
    }

    tau_max = q / std::max(evaporation * best_distance, 1e-12);
    tau_min = tau_max / std::max(
        tau_ratio * static_cast<double>(n_cities),
        1.0
    );
    return true;
}

bool calculateMmasBounds(
    double q,
    double evaporation,
    double best_distance,
    int n_cities,
    double p_best,
    double& tau_min,
    double& tau_max
) {
    if (
        n_cities <= 1
        || best_distance <= 0.0
        || !std::isfinite(best_distance)
        || p_best <= 0.0
        || p_best >= 1.0
    ) {
        return false;
    }

    tau_max = q / std::max(evaporation * best_distance, 1e-12);

    const double p_decision = std::pow(
        p_best,
        1.0 / static_cast<double>(n_cities)
    );
    const double average_choices = static_cast<double>(n_cities) / 2.0;
    const double denominator = (average_choices - 1.0) * p_decision;

    if (denominator <= 0.0) {
        tau_min = tau_max;
        return true;
    }

    tau_min = tau_max * (1.0 - p_decision) / denominator;
    tau_min = std::clamp(tau_min, 0.0, tau_max);
    return true;
}

void applyMinMaxPheromone(
    Matrix& pheromone,
    double q,
    double evaporation,
    double best_distance,
    int n_cities,
    double tau_ratio
) {
    double tau_min = 0.0;
    double tau_max = 0.0;

    if (!calculateMinMaxBounds(
        q,
        evaporation,
        best_distance,
        n_cities,
        tau_ratio,
        tau_min,
        tau_max
    )) {
        return;
    }

    clampPheromone(pheromone, tau_min, tau_max);
}

double offDiagonalMean(const Matrix& matrix) {
    if (matrix.empty()) {
        return 0.0;
    }

    double total = 0.0;
    std::size_t count = 0;

    for (std::size_t row = 0; row < matrix.size(); ++row) {
        for (std::size_t col = 0; col < matrix[row].size(); ++col) {
            if (matrix.size() < 2 || row != col) {
                total += matrix[row][col];
                ++count;
            }
        }
    }

    return count == 0 ? 0.0 : total / static_cast<double>(count);
}

Matrix blendPheromones(
    const Matrix& current_pheromone,
    Matrix blind_pheromone,
    double blind_weight,
    bool normalize_blind = true
) {
    const double current_weight = 1.0 - blind_weight;
    const double current_mean = offDiagonalMean(current_pheromone);
    const double blind_mean = offDiagonalMean(blind_pheromone);

    if (normalize_blind && blind_mean > 0.0) {
        const double scale = current_mean / blind_mean;

        for (std::vector<double>& row : blind_pheromone) {
            for (double& value : row) {
                value *= scale;
            }
        }
    }

    Matrix blended = current_pheromone;

    for (std::size_t row = 0; row < blended.size(); ++row) {
        for (std::size_t col = 0; col < blended[row].size(); ++col) {
            blended[row][col] = current_weight * current_pheromone[row][col]
                + blind_weight * blind_pheromone[row][col];
        }
    }

    return blended;
}

void countPathEdges(Matrix& edge_usage_counts, const std::vector<int>& path) {
    for (std::size_t index = 0; index + 1 < path.size(); ++index) {
        const std::size_t a = static_cast<std::size_t>(path[index]);
        const std::size_t b = static_cast<std::size_t>(path[index + 1]);
        edge_usage_counts[a][b] += 1.0;
        edge_usage_counts[b][a] += 1.0;
    }

    const std::size_t a = static_cast<std::size_t>(path.back());
    const std::size_t b = static_cast<std::size_t>(path.front());
    edge_usage_counts[a][b] += 1.0;
    edge_usage_counts[b][a] += 1.0;
}

Matrix createUsageBasedPheromone(
    const Matrix& edge_usage_counts,
    double tau_min,
    double tau_max
) {
    const std::size_t n_cities = edge_usage_counts.size();
    Matrix pheromone = createFlatPheromone(n_cities, tau_min);

    if (n_cities < 2) {
        return pheromone;
    }

    double min_count = std::numeric_limits<double>::infinity();
    double max_count = -std::numeric_limits<double>::infinity();

    for (std::size_t row = 0; row < n_cities; ++row) {
        for (std::size_t col = 0; col < n_cities; ++col) {
            if (row == col) {
                continue;
            }

            min_count = std::min(min_count, edge_usage_counts[row][col]);
            max_count = std::max(max_count, edge_usage_counts[row][col]);
        }
    }

    if (max_count == min_count) {
        const double middle = (tau_min + tau_max) / 2.0;

        for (std::size_t row = 0; row < n_cities; ++row) {
            for (std::size_t col = 0; col < n_cities; ++col) {
                if (row != col) {
                    pheromone[row][col] = middle;
                }
            }
        }

        return pheromone;
    }

    for (std::size_t row = 0; row < n_cities; ++row) {
        for (std::size_t col = 0; col < n_cities; ++col) {
            if (row == col) {
                continue;
            }

            const double normalized_count =
                (edge_usage_counts[row][col] - min_count)
                / (max_count - min_count);
            pheromone[row][col] = tau_min
                + normalized_count * (tau_max - tau_min);
        }
    }

    return pheromone;
}

Matrix runBlindAco(
    const Matrix& distances,
    const std::vector<Point>& coords,
    const Params& params,
    double evaporation,
    std::mt19937& rng,
    bool has_pheromone_bounds = false,
    double bound_tau_min = 0.0,
    double bound_tau_max = 0.0
) {
    Matrix edge_usage_counts = createFlatPheromone(
        distances.size(),
        0.0
    );
    double best_distance_so_far = std::numeric_limits<double>::infinity();

    for (int iteration = 0; iteration < params.blind_iterations; ++iteration) {
        std::vector<double> all_distances;

        for (int ant = 0; ant < params.n_ants; ++ant) {
            std::vector<int> path = buildDistanceOnlyPath(distances, params, rng);

            if (params.cross_check) {
                path = twoOptCrossCheck(path, coords);
            }

            all_distances.push_back(calculateDistance(path, distances));
            countPathEdges(edge_usage_counts, path);
        }

        best_distance_so_far = std::min(
            best_distance_so_far,
            *std::min_element(all_distances.begin(), all_distances.end())
        );
    }

    double tau_min = bound_tau_min;
    double tau_max = bound_tau_max;

    if (!has_pheromone_bounds) {
        has_pheromone_bounds = calculateMinMaxBounds(
            params.q,
            evaporation,
            best_distance_so_far,
            params.n_cities,
            params.min_max_tau_ratio,
            tau_min,
            tau_max
        );
    }

    if (!has_pheromone_bounds) {
        tau_min = params.base_pheromone;
        tau_max = params.base_pheromone;
    }

    return createUsageBasedPheromone(edge_usage_counts, tau_min, tau_max);
}

AcoResult runVariant(
    Variant variant,
    const Matrix& distances,
    const std::vector<Point>& coords,
    const Params& params,
    unsigned int seed
) {
    std::mt19937 rng(seed);
    Matrix pheromone = usesProjectAdditions(variant)
        ? createInitialPheromone(
            distances,
            params.base_pheromone,
            params.nearest_neighbor_pheromone
        )
        : createFlatPheromone(distances.size(), params.base_pheromone);

    AcoResult result;
    result.name = variantName(variant);
    int stagnation_counter = 0;

    for (int iteration = 0; iteration < params.n_iterations; ++iteration) {
        std::vector<std::vector<int>> all_paths;
        std::vector<double> all_distances;
        bool improved_this_iteration = false;

        for (int ant = 0; ant < params.n_ants; ++ant) {
            std::vector<int> path = buildAntPath(
                distances,
                pheromone,
                params,
                usesProjectAdditions(variant)
                    ? params.ant_parameter_variation
                    : 0.0,
                rng
            );

            if (params.cross_check) {
                path = twoOptCrossCheck(path, coords);
            }

            const double distance = calculateDistance(path, distances);
            all_paths.push_back(path);
            all_distances.push_back(distance);

            if (distance < result.best_distance) {
                result.best_distance = distance;
                result.best_path = path;
                improved_this_iteration = true;
            }
        }

        const auto iteration_best_it = std::min_element(
            all_distances.begin(),
            all_distances.end()
        );
        const std::size_t iteration_best_index =
            static_cast<std::size_t>(
                std::distance(all_distances.begin(), iteration_best_it)
            );
        const double iteration_best_distance = *iteration_best_it;
        const double current_evaporation = usesProjectAdditions(variant)
            ? getEvaporationRate(
                iteration,
                params.n_iterations,
                params.evaporation,
                params.end_evaporation,
                params.evaporation_schedule,
                params.evaporation_curve
            )
            : params.classic_evaporation;

        evaporate(pheromone, current_evaporation);

        if (
            variant == Variant::BlindBlendAS
            || variant == Variant::BaselineAS
            || variant == Variant::ElitistAS
        ) {
            const std::vector<std::size_t> deposit_indices =
                variant == Variant::BlindBlendAS
                    ? selectPheromoneDepositIndices(
                        all_distances,
                        params.pheromone_deposit_top_ants
                    )
                    : selectPheromoneDepositIndices(all_distances, -1);

            for (std::size_t index : deposit_indices) {
                depositPheromone(
                    pheromone,
                    all_paths[index],
                    all_distances[index],
                    params.q
                );
            }

            if (variant == Variant::ElitistAS && !result.best_path.empty()) {
                depositPheromone(
                    pheromone,
                    result.best_path,
                    result.best_distance,
                    params.q,
                    static_cast<double>(params.elitist_weight)
                );
            }

            if (variant == Variant::BlindBlendAS) {
                if (params.use_min_max_pheromone) {
                    applyMinMaxPheromone(
                        pheromone,
                        params.q,
                        current_evaporation,
                        result.best_distance,
                        params.n_cities,
                        params.min_max_tau_ratio
                    );
                }

                if (improved_this_iteration) {
                    stagnation_counter = 0;
                } else {
                    ++stagnation_counter;
                }

                if (
                    stagnation_counter >= params.blind_stagnation_limit
                    && params.blind_iterations > 0
                    && params.blind_blend_weight > 0.0
                ) {
                    double blind_tau_min = 0.0;
                    double blind_tau_max = 0.0;
                    const bool has_blind_pheromone_bounds =
                        params.use_min_max_pheromone
                        && calculateMinMaxBounds(
                            params.q,
                            current_evaporation,
                            result.best_distance,
                            params.n_cities,
                            params.min_max_tau_ratio,
                            blind_tau_min,
                            blind_tau_max
                        );

                    Matrix blind_pheromone = runBlindAco(
                        distances,
                        coords,
                        params,
                        current_evaporation,
                        rng,
                        has_blind_pheromone_bounds,
                        blind_tau_min,
                        blind_tau_max
                    );
                    pheromone = blendPheromones(
                        pheromone,
                        blind_pheromone,
                        params.blind_blend_weight,
                        !has_blind_pheromone_bounds
                    );
                    if (params.use_min_max_pheromone) {
                        applyMinMaxPheromone(
                            pheromone,
                            params.q,
                            current_evaporation,
                            result.best_distance,
                            params.n_cities,
                            params.min_max_tau_ratio
                        );
                    }
                    stagnation_counter = 0;
                }
            }
        } else if (variant == Variant::MaxMinAS) {
            const std::vector<int>& deposit_path = result.best_path.empty()
                ? all_paths[iteration_best_index]
                : result.best_path;
            const double deposit_distance = result.best_path.empty()
                ? iteration_best_distance
                : result.best_distance;

            depositPheromone(
                pheromone,
                deposit_path,
                deposit_distance,
                params.q
            );

            double tau_min = 0.0;
            double tau_max = 0.0;
            if (calculateMmasBounds(
                params.q,
                current_evaporation,
                result.best_distance,
                params.n_cities,
                params.max_min_p_best,
                tau_min,
                tau_max
            )) {
                clampPheromone(pheromone, tau_min, tau_max);
            }
        }
    }

    return result;
}

int parseIntArg(char** argv, int index, int fallback) {
    if (argv[index] == nullptr) {
        return fallback;
    }

    return std::atoi(argv[index]);
}

std::vector<AverageRow> buildAverageRows(
    const std::vector<DetailRow>& detail_rows
) {
    std::vector<AverageRow> averages;

    for (Variant variant : allVariants()) {
        AverageRow average;
        average.algorithm = variantName(variant);

        for (const DetailRow& row : detail_rows) {
            if (row.algorithm != average.algorithm) {
                continue;
            }

            ++average.runs;
            average.average_best_distance += row.best_distance;
            average.average_distance_per_city += row.distance_per_city;
            average.best_distance = std::min(
                average.best_distance,
                row.best_distance
            );
            average.worst_distance = std::max(
                average.worst_distance,
                row.best_distance
            );
        }

        if (average.runs > 0) {
            average.average_best_distance /= static_cast<double>(average.runs);
            average.average_distance_per_city /= static_cast<double>(average.runs);
        }

        averages.push_back(average);
    }

    return averages;
}

void writeDetailCsv(
    const std::string& directory,
    const std::vector<DetailRow>& rows
) {
    std::ofstream file(std::filesystem::path(directory) / "detail.csv");
    file << "n_cities,algorithm,best_distance,distance_per_city\n";
    file << std::fixed << std::setprecision(8);

    for (const DetailRow& row : rows) {
        file << row.n_cities << "," << row.algorithm << ","
             << row.best_distance << "," << row.distance_per_city << "\n";
    }
}

void writeAverageCsv(
    const std::string& directory,
    const std::vector<AverageRow>& rows
) {
    std::ofstream file(std::filesystem::path(directory) / "average.csv");
    file << "algorithm,runs,average_best_distance,"
         << "average_distance_per_city,best_distance,worst_distance\n";
    file << std::fixed << std::setprecision(8);

    for (const AverageRow& row : rows) {
        file << row.algorithm << "," << row.runs << ","
             << row.average_best_distance << ","
             << row.average_distance_per_city << ","
             << row.best_distance << "," << row.worst_distance << "\n";
    }
}

void printUsage(const char* executable) {
    std::cout << "Usage:\n"
              << "  " << executable
              << " <start_city> <x> [n_ants] [n_iterations] [cross_check]\n\n"
              << "Example:\n"
              << "  " << executable << " 100 10 80 150 1\n\n"
              << "This runs city counts start_city..start_city+x inclusive.\n";
}

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--help") {
        printUsage(argv[0]);
        return 0;
    }

    const int start_city = argc > 1 ? parseIntArg(argv, 1, 100) : 100;
    const int city_span = argc > 2 ? parseIntArg(argv, 2, 10) : 100;
    const int n_ants = argc > 3 ? parseIntArg(argv, 3, 100) : 100;
    const int n_iterations = argc > 4 ? parseIntArg(argv, 4, 200) : 200;
    const bool cross_check = argc > 5 ? parseIntArg(argv, 5, 1) != 0 : true;

    if (start_city < 2 || city_span < 0 || n_ants < 1 || n_iterations < 1) {
        printUsage(argv[0]);
        return 1;
    }

    std::vector<DetailRow> detail_rows;
    std::cout << std::fixed << std::setprecision(8);
    std::cout << "Running city counts " << start_city << ".."
              << start_city + city_span << " inclusive\n";

    for (int spa = start_city; spa <= start_city + city_span; ++spa) {
        int n_cities=250;
        Params params;
        params.n_cities = n_cities;
        params.n_ants = n_ants;
        params.n_iterations = n_iterations;
        params.cross_check = cross_check;
        params.q = static_cast<double>(n_cities * 20);

        const DistanceData data = generateEuclideanDistances(
            n_cities,
            static_cast<unsigned int>(47 + spa),
            static_cast<double>(n_cities * 20)
        );

        std::cout << "\nCities: " << spa << "\n";

        for (Variant variant : allVariants()) {
            const AcoResult result = runVariant(
                variant,
                data.distances,
                data.coords,
                params,
                static_cast<unsigned int>(43 + n_cities)
            );
            const double distance_per_city =
                result.best_distance / static_cast<double>(n_cities);

            detail_rows.push_back({
                spa,
                result.name,
                result.best_distance,
                distance_per_city
            });

            std::cout << "  " << std::left << std::setw(12) << result.name
                      << " best=" << std::right << result.best_distance
                      << " per_city=" << distance_per_city << "\n";
        }
    }

    const std::vector<AverageRow> averages = buildAverageRows(detail_rows);
    std::filesystem::create_directories("output");
    writeDetailCsv("output", detail_rows);
    writeAverageCsv("output", averages);

    std::cout << "\nAverage results\n";
    std::cout << "---------------\n";

    for (const AverageRow& row : averages) {
        std::cout << std::left << std::setw(12) << row.algorithm
                  << " avg_best=" << std::right << row.average_best_distance
                  << " avg_per_city=" << row.average_distance_per_city
                  << " best=" << row.best_distance
                  << " worst=" << row.worst_distance << "\n";
    }

    std::cout << "\nFiles written to output/detail.csv and output/average.csv\n";
    return 0;
}
