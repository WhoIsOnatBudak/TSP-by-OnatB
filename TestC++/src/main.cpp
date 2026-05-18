#include "aco.hpp"
#include "generation.hpp"
#include "plots.hpp"

#include <iomanip>
#include <iostream>

int main() {
    RandomContext rng(43, 43);

    const int n_cities = 100;
    DistanceData data = generateEuclideanDistances(
        n_cities,
        47,
        static_cast<double>(n_cities * 20),
        &rng
    );

    AcoParams params;
    params.n_ants = 40;
    params.n_iterations = 50;
    params.alpha = 1.0;
    params.beta = 3.0;
    params.evaporation = 0.8;
    params.q = static_cast<double>(n_cities * 20);
    params.end_evaporation = 0.3;
    params.base_pheromone = 1.0;
    params.nearest_neighbor_pheromone = 1.1;
    params.blind_stagnation_limit = 20;
    params.blind_iterations = 5;
    params.blind_blend_weight = 0.5;

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
