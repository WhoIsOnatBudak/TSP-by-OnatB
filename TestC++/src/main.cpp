#include "aco.hpp"
#include "generation.hpp"
#include "plots.hpp"

#include <iomanip>
#include <iostream>

int main() {
    RandomContext rng(48, 48);

    const int n_cities = 101;
    DistanceData data = generateEuclideanDistances(
        n_cities,
        48,
        static_cast<double>(n_cities * 20),
        &rng
    );

    AcoParams params;
    params.n_ants = 100;
    params.n_iterations = 200;
    params.alpha = 1.0;
    params.beta = 3.0;
    params.evaporation = 0.6;
    params.q = static_cast<double>(n_cities * 20);
    params.end_evaporation = 0.2;
    params.base_pheromone = 1.0;
    params.nearest_neighbor_pheromone = 2;
    params.blind_stagnation_limit = 30;
    params.blind_iterations = 5;
    params.blind_blend_weight = 0.5;
    params.ant_parameter_variation = 0.1;
    params.use_min_max_pheromone = true;
    params.min_max_tau_ratio = 2.0;
    params.pheromone_deposit_top_ants = 1;
    params.evaporation_schedule=EvaporationSchedule::Exponential;
    params.evaporation_curve =-2.0;

    AcoResult result = runAco(
        data.distances,
        &data.coords,
        params,
        rng
    );

    std::cout << "Best Path: [";

    for (std::size_t index = 0; index < result.best_path.size(); ++index) {
        if (index > 0) {
            std::cout << ", ";
        }

        std::cout << result.best_path[index];
    }

    std::cout << "]\n";
    std::cout << std::fixed << std::setprecision(8);
    std::cout << "Best Distance: " << result.best_distance << "\n";
    std::cout << "Blind Rounds: " << result.blind_round_history.size()
              << "\n";

    writeOutputFiles("output", data.coords, result);
    std::cout << "Output files written to: output/\n";

    return 0;
}
