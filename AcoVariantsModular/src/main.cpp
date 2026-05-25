#include "aco_runner.hpp"
#include "geometry.hpp"
#include "output.hpp"
#include "types.hpp"

#include <filesystem>
#include <iostream>
#include <vector>

int main() {
    aco::Params params;
    params.q = static_cast<double>(params.n_cities * 20);

    const aco::DistanceData data = aco::generateEuclideanDistances(
        params.n_cities,
        47,
        static_cast<double>(params.n_cities * 20)
    );

    std::cout<<params.n_cities<<"\n"; 

    std::vector<aco::AcoResult> results;
    results.push_back(aco::runVariant(
        aco::Variant::BlindBlendAS,
        data.distances,
        data.coords,
        params,
        43
    ));
    results.push_back(aco::runVariant(
        aco::Variant::BaselineAS,
        data.distances,
        data.coords,
        params,
        43
    ));
    results.push_back(aco::runVariant(
        aco::Variant::ElitistAS,
        data.distances,
        data.coords,
        params,
        43
    ));
    results.push_back(aco::runVariant(
        aco::Variant::MaxMinAS,
        data.distances,
        data.coords,
        params,
        43
    ));

    std::filesystem::create_directories("output");
    aco::writeSummaryCsv("output", results);
    aco::writeConvergenceCsv("output", results);
    aco::writeConvergenceSvg("output", results);
    aco::printSummary(results);
    std::cout << "Files written to output/summary.csv, output/convergence.csv,"
              << " and output/convergence.svg\n";

    return 0;
}

