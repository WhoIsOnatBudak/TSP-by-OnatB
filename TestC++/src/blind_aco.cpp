#include "blind_aco.hpp"

#include "opt.hpp"
#include "pheromone.hpp"
#include "tour.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <numeric>
#include <optional>
#include <random>

namespace {

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
    RandomContext& rng
) {
    Matrix pheromone = createInitialPheromone(
        distances,
        base_pheromone,
        std::nullopt
    );
    std::vector<double> best_per_iteration;

    for (int iteration = 0; iteration < n_iterations; ++iteration) {
        std::vector<std::vector<int>> all_paths;
        std::vector<double> all_distances;

        for (int ant = 0; ant < n_ants; ++ant) {
            std::vector<int> path = buildDistanceOnlyPath(distances, beta, rng);

            if (cross_check && coords != nullptr) {
                path = twoOptCrossCheck(path, *coords);
            }

            const double distance = calculateDistance(path, distances);
            all_paths.push_back(path);
            all_distances.push_back(distance);
        }

        best_per_iteration.push_back(
            *std::min_element(all_distances.begin(), all_distances.end())
        );

        for (std::vector<double>& row : pheromone) {
            for (double& value : row) {
                value *= (1.0 - evaporation);
            }
        }

        for (std::size_t index = 0; index < all_paths.size(); ++index) {
            depositPheromone(
                pheromone,
                all_paths[index],
                all_distances[index],
                q
            );
        }
    }

    return {pheromone, best_per_iteration};
}

Matrix blendPheromones(
    const Matrix& current_pheromone,
    Matrix blind_pheromone,
    double blind_weight
) {
    const double current_weight = 1.0 - blind_weight;
    const double current_mean = offDiagonalMean(current_pheromone);
    const double blind_mean = offDiagonalMean(blind_pheromone);

    if (blind_mean > 0.0) {
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
