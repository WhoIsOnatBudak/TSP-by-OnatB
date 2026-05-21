#include "blind_aco.hpp"

#include "opt.hpp"
#include "pheromone.hpp"
#include "tour.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <numeric>
#include <random>

namespace {

double varyParameter(
    double value,
    double variation,
    RandomContext& rng
) {
    if (variation <= 0.0) {
        return value;
    }

    const double lower_multiplier = std::max(0.0, 1.0 - variation);
    const double upper_multiplier = 1.0 + variation;
    std::uniform_real_distribution<double> distribution(
        lower_multiplier,
        upper_multiplier
    );

    return value * distribution(rng.python_rng);
}

int chooseByWeights(
    const std::vector<double>& weights,
    double total_weight,
    RandomContext& rng
) {
    std::uniform_real_distribution<double> distribution(0.0, total_weight);
    const double target = distribution(rng.numpy_rng);
    double cumulative = 0.0;

    for (std::size_t city = 0; city < weights.size(); ++city) {
        cumulative += weights[city];

        if (target <= cumulative) {
            return static_cast<int>(city);
        }
    }

    return static_cast<int>(weights.size() - 1);
}

std::vector<int> chooseCandidate(
    const std::vector<bool>& visited
) {
    std::vector<int> candidates;

    for (std::size_t city = 0; city < visited.size(); ++city) {
        if (!visited[city]) {
            candidates.push_back(static_cast<int>(city));
        }
    }

    return candidates;
}

std::vector<int> buildDistanceOnlyPath(
    const Matrix& distances,
    double beta,
    RandomContext& rng
) {
    const int n_cities = static_cast<int>(distances.size());
    std::uniform_int_distribution<int> start_distribution(0, n_cities - 1);
    const int start_city = start_distribution(rng.python_rng);

    std::vector<int> visited_path = {start_city};
    std::vector<bool> visited(static_cast<std::size_t>(n_cities), false);
    visited[static_cast<std::size_t>(start_city)] = true;

    while (static_cast<int>(visited_path.size()) < n_cities) {
        const int current = visited_path.back();
        std::vector<double> probabilities(
            static_cast<std::size_t>(n_cities),
            0.0
        );

        for (int city = 0; city < n_cities; ++city) {
            if (!visited[static_cast<std::size_t>(city)]) {
                probabilities[static_cast<std::size_t>(city)] =
                    std::pow(
                        1.0 / distances[static_cast<std::size_t>(current)]
                            [static_cast<std::size_t>(city)],
                        beta
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
            const std::vector<int> candidates = chooseCandidate(visited);
            std::uniform_int_distribution<int> candidate_distribution(
                0,
                static_cast<int>(candidates.size()) - 1
            );
            next_city = candidates[
                static_cast<std::size_t>(candidate_distribution(rng.python_rng))
            ];
        } else {
            next_city = chooseByWeights(probabilities, total_probability, rng);
        }

        visited_path.push_back(next_city);
        visited[static_cast<std::size_t>(next_city)] = true;
    }

    return visited_path;
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

double offDiagonalMean(const Matrix& matrix) {
    const std::size_t n_rows = matrix.size();

    if (n_rows == 0) {
        return 0.0;
    }

    if (n_rows < 2) {
        double total = 0.0;
        std::size_t count = 0;

        for (const std::vector<double>& row : matrix) {
            for (double value : row) {
                total += value;
                ++count;
            }
        }

        return count == 0 ? 0.0 : total / static_cast<double>(count);
    }

    double total = 0.0;
    std::size_t count = 0;

    for (std::size_t row = 0; row < matrix.size(); ++row) {
        for (std::size_t col = 0; col < matrix[row].size(); ++col) {
            if (row != col) {
                total += matrix[row][col];
                ++count;
            }
        }
    }

    return count == 0 ? 0.0 : total / static_cast<double>(count);
}

} // namespace

BlindAcoResult runBlindAco(
    const Matrix& distances,
    const std::vector<Point>* coords,
    int n_ants,
    int n_iterations,
    double beta,
    double evaporation,
    double q,
    double base_pheromone,
    bool cross_check,
    double beta_variation,
    bool use_min_max_pheromone,
    double min_max_tau_ratio,
    std::optional<std::pair<double, double>> pheromone_bounds,
    RandomContext& rng
) {
    (void)use_min_max_pheromone;

    const int n_cities = static_cast<int>(distances.size());
    Matrix edge_usage_counts = createFlatPheromone(
        static_cast<std::size_t>(n_cities),
        0.0
    );
    std::vector<double> best_per_iteration;
    double best_distance_so_far = std::numeric_limits<double>::infinity();

    for (int iteration = 0; iteration < n_iterations; ++iteration) {
        std::vector<double> all_distances;

        for (int ant = 0; ant < n_ants; ++ant) {
            const double ant_beta = varyParameter(beta, beta_variation, rng);
            std::vector<int> path = buildDistanceOnlyPath(
                distances,
                ant_beta,
                rng
            );

            if (cross_check && coords != nullptr) {
                path = twoOptCrossCheck(path, *coords);
            }

            const double distance = calculateDistance(path, distances);
            all_distances.push_back(distance);
            countPathEdges(edge_usage_counts, path);
        }

        const double iteration_best_distance =
            *std::min_element(all_distances.begin(), all_distances.end());
        best_per_iteration.push_back(iteration_best_distance);
        best_distance_so_far = std::min(
            best_distance_so_far,
            iteration_best_distance
        );
    }

    if (!pheromone_bounds.has_value()) {
        double tau_min = 0.0;
        double tau_max = 0.0;

        if (calculateMinMaxPheromoneBounds(
            q,
            evaporation,
            best_distance_so_far,
            n_cities,
            min_max_tau_ratio,
            tau_min,
            tau_max
        )) {
            pheromone_bounds = std::make_pair(tau_min, tau_max);
        }
    }

    if (!pheromone_bounds.has_value()) {
        pheromone_bounds = std::make_pair(base_pheromone, base_pheromone);
    }

    Matrix pheromone = createUsageBasedPheromone(
        edge_usage_counts,
        pheromone_bounds->first,
        pheromone_bounds->second
    );

    return {pheromone, best_per_iteration};
}

Matrix blendPheromones(
    const Matrix& current_pheromone,
    Matrix blind_pheromone,
    double blind_weight,
    bool normalize_blind
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
