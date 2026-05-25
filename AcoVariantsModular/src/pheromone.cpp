#include "pheromone.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>

namespace aco {

Matrix createFlatPheromone(
    std::size_t n_cities,
    double base_pheromone
) {
    return Matrix(n_cities, std::vector<double>(n_cities, base_pheromone));
}

Matrix createInitialPheromone(
    const Matrix& distances,
    double base_pheromone,
    double nearest_neighbor_pheromone
) {
    const std::size_t n_cities = distances.size();
    Matrix pheromone(n_cities, std::vector<double>(n_cities, base_pheromone));

    if (n_cities < 2) {
        return pheromone;
    }

    for (std::size_t city = 0; city < n_cities; ++city) {
        double best_distance = std::numeric_limits<double>::infinity();
        std::size_t nearest_city = city;

        for (std::size_t candidate = 0; candidate < n_cities; ++candidate) {
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

void depositPheromone(
    Matrix& pheromone,
    const std::vector<int>& path,
    double distance,
    double q,
    double multiplier
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

void clampPheromone(
    Matrix& pheromone,
    double tau_min,
    double tau_max
) {
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

    if (matrix.size() < 2) {
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

}  // namespace aco
