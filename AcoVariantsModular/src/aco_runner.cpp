#include "aco_runner.hpp"

#include "ant_builder.hpp"
#include "blind_aco.hpp"
#include "geometry.hpp"
#include "pheromone.hpp"

#include <algorithm>
#include <random>

namespace aco {

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
                params.end_evaporation
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

        result.history.push_back({
            iteration,
            iteration_best_distance,
            result.best_distance
        });
    }

    return result;
}

}  // namespace aco
