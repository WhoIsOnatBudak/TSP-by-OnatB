#include "aco.hpp"
#include "generation.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

namespace {

struct EvaporationCase {
    EvaporationSchedule schedule = EvaporationSchedule::Linear;
    double start_evaporation = 0.8;
    double end_evaporation = 0.3;
    double curve = 1.0;
};

struct PheromoneStats {
    double min_value = std::numeric_limits<double>::infinity();
    double max_value = -std::numeric_limits<double>::infinity();
    double mean_value = 0.0;
};

struct DetailRow {
    EvaporationCase evaporation_case;
    int seed_index = 0;
    unsigned int python_seed = 0;
    unsigned int city_seed = 0;
    double best_distance = 0.0;
    std::size_t blind_rounds = 0;
    PheromoneStats pheromone_stats;
};

struct SummaryRow {
    EvaporationCase evaporation_case;
    int runs = 0;
    double average_best_distance = 0.0;
    double best_distance = std::numeric_limits<double>::infinity();
    double worst_distance = 0.0;
    double stddev_best_distance = 0.0;
    double average_blind_rounds = 0.0;
    double average_pheromone_min = 0.0;
    double average_pheromone_max = 0.0;
    double average_pheromone_mean = 0.0;
};

std::string formatDouble(double value) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(4) << value;
    return stream.str();
}

bool sameCase(const EvaporationCase& left, const EvaporationCase& right) {
    return left.schedule == right.schedule
        && left.start_evaporation == right.start_evaporation
        && left.end_evaporation == right.end_evaporation
        && left.curve == right.curve;
}

AcoParams makeBaseParams(int n_cities) {
    AcoParams params;
    params.n_ants = 50;
    params.n_iterations = 50;
    params.alpha = 1.0;
    params.beta = 3.0;
    params.evaporation = 0.8;
    params.q = static_cast<double>(n_cities * 20);
    params.end_evaporation = 0.3;
    params.cross_check = true;
    params.base_pheromone = 1.0;
    params.nearest_neighbor_pheromone = 2.0;
    params.blind_stagnation_limit = 10;
    params.blind_iterations = 3;
    params.blind_blend_weight = 0.5;
    params.ant_parameter_variation = 0.1;
    params.use_min_max_pheromone = true;
    params.min_max_tau_ratio = 2.0;
    params.pheromone_deposit_top_ants = 1;
    return params;
}

std::vector<EvaporationCase> buildEvaporationCases() {
    const std::vector<std::pair<double, double>> bounds = {
        {0.9, 0.2},
        {0.8, 0.2},
        {0.8, 0.3},
        {0.7, 0.3},
        {0.7, 0.4},
        {0.6, 0.2}
    };
    const std::vector<double> exponential_curves = {
        -4.0,
        -2.0,
        -1.0,
        1.0,
        2.0,
        4.0
    };
    const std::vector<double> logarithmic_curves = {
        -9.0,
        -3.0,
        -1.0,
        1.0,
        3.0,
        9.0
    };

    std::vector<EvaporationCase> cases;

    for (const auto& bound : bounds) {
        cases.push_back({
            EvaporationSchedule::Linear,
            bound.first,
            bound.second,
            1.0
        });

        for (double curve : exponential_curves) {
            cases.push_back({
                EvaporationSchedule::Exponential,
                bound.first,
                bound.second,
                curve
            });
        }

        for (double curve : logarithmic_curves) {
            cases.push_back({
                EvaporationSchedule::Logarithmic,
                bound.first,
                bound.second,
                curve
            });
        }
    }

    return cases;
}

PheromoneStats calculatePheromoneStats(const Matrix& pheromone) {
    PheromoneStats stats;
    double total = 0.0;
    std::size_t count = 0;

    for (std::size_t row = 0; row < pheromone.size(); ++row) {
        for (std::size_t col = 0; col < pheromone[row].size(); ++col) {
            if (row == col) {
                continue;
            }

            const double value = pheromone[row][col];
            stats.min_value = std::min(stats.min_value, value);
            stats.max_value = std::max(stats.max_value, value);
            total += value;
            ++count;
        }
    }

    if (count == 0) {
        stats.min_value = 0.0;
        stats.max_value = 0.0;
        stats.mean_value = 0.0;
        return stats;
    }

    stats.mean_value = total / static_cast<double>(count);
    return stats;
}

DetailRow runSingleCase(
    const EvaporationCase& evaporation_case,
    int seed_index,
    int n_cities
) {
    const unsigned int python_seed = static_cast<unsigned int>(48 + seed_index);
    const unsigned int city_seed = static_cast<unsigned int>(48 + seed_index);
    RandomContext rng(python_seed, python_seed);

    DistanceData data = generateEuclideanDistances(
        n_cities,
        city_seed,
        static_cast<double>(n_cities * 20),
        &rng
    );

    AcoParams params = makeBaseParams(n_cities);
    params.evaporation = evaporation_case.start_evaporation;
    params.end_evaporation = evaporation_case.end_evaporation;
    params.evaporation_schedule = evaporation_case.schedule;
    params.evaporation_curve = evaporation_case.curve;

    const AcoResult result = runAco(
        data.distances,
        &data.coords,
        params,
        rng
    );

    return {
        evaporation_case,
        seed_index,
        python_seed,
        city_seed,
        result.best_distance,
        result.blind_round_history.size(),
        calculatePheromoneStats(result.pheromone)
    };
}

std::vector<SummaryRow> summarizeRows(const std::vector<DetailRow>& rows) {
    std::vector<SummaryRow> summaries;

    for (const DetailRow& row : rows) {
        auto found = std::find_if(
            summaries.begin(),
            summaries.end(),
            [&](const SummaryRow& summary) {
                return sameCase(summary.evaporation_case, row.evaporation_case);
            }
        );

        if (found == summaries.end()) {
            summaries.push_back({row.evaporation_case});
            found = summaries.end() - 1;
        }

        ++found->runs;
        found->average_best_distance += row.best_distance;
        found->average_blind_rounds += static_cast<double>(row.blind_rounds);
        found->average_pheromone_min += row.pheromone_stats.min_value;
        found->average_pheromone_max += row.pheromone_stats.max_value;
        found->average_pheromone_mean += row.pheromone_stats.mean_value;
        found->best_distance = std::min(
            found->best_distance,
            row.best_distance
        );
        found->worst_distance = std::max(
            found->worst_distance,
            row.best_distance
        );
    }

    for (SummaryRow& summary : summaries) {
        if (summary.runs == 0) {
            continue;
        }

        const double runs = static_cast<double>(summary.runs);
        summary.average_best_distance /= runs;
        summary.average_blind_rounds /= runs;
        summary.average_pheromone_min /= runs;
        summary.average_pheromone_max /= runs;
        summary.average_pheromone_mean /= runs;

        double variance = 0.0;

        for (const DetailRow& row : rows) {
            if (!sameCase(summary.evaporation_case, row.evaporation_case)) {
                continue;
            }

            const double diff =
                row.best_distance - summary.average_best_distance;
            variance += diff * diff;
        }

        summary.stddev_best_distance = std::sqrt(variance / runs);
    }

    return summaries;
}

void writeDetailCsv(
    const std::string& directory,
    const std::vector<DetailRow>& rows
) {
    std::ofstream file(std::filesystem::path(directory) / "evaporation_sweep_detail.csv");
    file << "schedule,start_evaporation,end_evaporation,curve,"
         << "seed_index,python_seed,city_seed,best_distance,blind_rounds,"
         << "final_pheromone_min,final_pheromone_max,final_pheromone_mean\n";
    file << std::fixed << std::setprecision(8);

    for (const DetailRow& row : rows) {
        file << evaporationScheduleName(row.evaporation_case.schedule) << ","
             << row.evaporation_case.start_evaporation << ","
             << row.evaporation_case.end_evaporation << ","
             << row.evaporation_case.curve << ","
             << row.seed_index << "," << row.python_seed << ","
             << row.city_seed << "," << row.best_distance << ","
             << row.blind_rounds << ","
             << row.pheromone_stats.min_value << ","
             << row.pheromone_stats.max_value << ","
             << row.pheromone_stats.mean_value << "\n";
    }
}

void writeSummaryCsv(
    const std::string& directory,
    const std::vector<SummaryRow>& rows
) {
    std::ofstream file(std::filesystem::path(directory) / "evaporation_sweep_summary.csv");
    file << "schedule,start_evaporation,end_evaporation,curve,runs,"
         << "average_best_distance,best_distance,worst_distance,"
         << "stddev_best_distance,average_blind_rounds,"
         << "average_pheromone_min,average_pheromone_max,"
         << "average_pheromone_mean\n";
    file << std::fixed << std::setprecision(8);

    for (const SummaryRow& row : rows) {
        file << evaporationScheduleName(row.evaporation_case.schedule) << ","
             << row.evaporation_case.start_evaporation << ","
             << row.evaporation_case.end_evaporation << ","
             << row.evaporation_case.curve << ","
             << row.runs << "," << row.average_best_distance << ","
             << row.best_distance << "," << row.worst_distance << ","
             << row.stddev_best_distance << ","
             << row.average_blind_rounds << ","
             << row.average_pheromone_min << ","
             << row.average_pheromone_max << ","
             << row.average_pheromone_mean << "\n";
    }
}

void writeCurveCsv(
    const std::string& directory,
    const std::vector<EvaporationCase>& cases,
    int n_iterations
) {
    std::ofstream file(std::filesystem::path(directory) / "evaporation_sweep_curves.csv");
    file << "schedule,start_evaporation,end_evaporation,curve,"
         << "iteration,evaporation\n";
    file << std::fixed << std::setprecision(8);

    for (const EvaporationCase& evaporation_case : cases) {
        for (int iteration = 0; iteration < n_iterations; ++iteration) {
            file << evaporationScheduleName(evaporation_case.schedule) << ","
                 << evaporation_case.start_evaporation << ","
                 << evaporation_case.end_evaporation << ","
                 << evaporation_case.curve << ","
                 << iteration << ","
                 << getEvaporationRate(
                    iteration,
                    n_iterations,
                    evaporation_case.start_evaporation,
                    evaporation_case.end_evaporation,
                    evaporation_case.schedule,
                    evaporation_case.curve
                 )
                 << "\n";
        }
    }
}

void writeBestReport(
    const std::string& directory,
    const std::vector<SummaryRow>& summaries,
    int n_cities,
    int runs_per_case
) {
    std::ofstream file(std::filesystem::path(directory) / "evaporation_sweep_best.txt");
    file << "Evaporation sweep report\n";
    file << "========================\n\n";
    file << "n_cities: " << n_cities << "\n";
    file << "runs_per_case: " << runs_per_case << "\n\n";
    file << "Top 10 by average best distance:\n";
    file << std::fixed << std::setprecision(8);

    const int count = std::min(static_cast<int>(summaries.size()), 10);

    for (int index = 0; index < count; ++index) {
        const SummaryRow& row = summaries[static_cast<std::size_t>(index)];
        file << index + 1 << ". "
             << evaporationScheduleName(row.evaporation_case.schedule)
             << " start=" << row.evaporation_case.start_evaporation
             << " end=" << row.evaporation_case.end_evaporation
             << " curve=" << row.evaporation_case.curve
             << " | avg_best=" << row.average_best_distance
             << " | stddev=" << row.stddev_best_distance
             << " | avg_blind_rounds=" << row.average_blind_rounds
             << " | avg_pheromone_mean=" << row.average_pheromone_mean
             << "\n";
    }

    file << "\nBest per schedule:\n";

    for (EvaporationSchedule schedule : {
        EvaporationSchedule::Linear,
        EvaporationSchedule::Exponential,
        EvaporationSchedule::Logarithmic
    }) {
        auto found = std::find_if(
            summaries.begin(),
            summaries.end(),
            [&](const SummaryRow& row) {
                return row.evaporation_case.schedule == schedule;
            }
        );

        if (found == summaries.end()) {
            continue;
        }

        file << "- " << evaporationScheduleName(schedule)
             << " start=" << found->evaporation_case.start_evaporation
             << " end=" << found->evaporation_case.end_evaporation
             << " curve=" << found->evaporation_case.curve
             << " | avg_best=" << found->average_best_distance
             << "\n";
    }
}

int parseInt(char** argv, int index, int fallback) {
    if (argv[index] == nullptr) {
        return fallback;
    }

    try {
        return std::stoi(argv[index]);
    } catch (...) {
        return fallback;
    }
}

} // namespace

int main(int argc, char** argv) {
    const int runs_per_case = argc > 1 ? parseInt(argv, 1, 20) : 10;
    const int n_cities = argc > 2 ? parseInt(argv, 2, 101) : 60;

    if (runs_per_case < 1 || n_cities < 2) {
        std::cout << "Usage: " << argv[0]
                  << " [runs_per_case=20] [n_cities=101]\n";
        return 1;
    }

    const AcoParams base_params = makeBaseParams(n_cities);
    const std::vector<EvaporationCase> cases = buildEvaporationCases();
    std::vector<DetailRow> detail_rows;
    const int total_runs = static_cast<int>(cases.size()) * runs_per_case;
    int completed_runs = 0;

    std::cout << "Evaporation sweep started\n";
    std::cout << "Cases: " << cases.size() << "\n";
    std::cout << "Runs per case: " << runs_per_case << "\n";
    std::cout << "Total runs: " << total_runs << "\n\n";

    for (const EvaporationCase& evaporation_case : cases) {
        std::cout << "Testing "
                  << evaporationScheduleName(evaporation_case.schedule)
                  << " start=" << formatDouble(evaporation_case.start_evaporation)
                  << " end=" << formatDouble(evaporation_case.end_evaporation)
                  << " curve=" << formatDouble(evaporation_case.curve)
                  << "\n";

        for (int seed_index = 0; seed_index < runs_per_case; ++seed_index) {
            detail_rows.push_back(runSingleCase(
                evaporation_case,
                seed_index,
                n_cities
            ));
            ++completed_runs;
        }

        std::cout << "  completed " << completed_runs << "/"
                  << total_runs << "\n";
    }

    std::vector<SummaryRow> summaries = summarizeRows(detail_rows);
    std::sort(
        summaries.begin(),
        summaries.end(),
        [](const SummaryRow& left, const SummaryRow& right) {
            return left.average_best_distance < right.average_best_distance;
        }
    );

    std::filesystem::create_directories("output");
    writeDetailCsv("output", detail_rows);
    writeSummaryCsv("output", summaries);
    writeCurveCsv("output", cases, base_params.n_iterations);
    writeBestReport("output", summaries, n_cities, runs_per_case);

    std::cout << "\nTop 10 evaporation settings\n";
    std::cout << "---------------------------\n";
    std::cout << std::fixed << std::setprecision(8);

    const int count = std::min(static_cast<int>(summaries.size()), 10);

    for (int index = 0; index < count; ++index) {
        const SummaryRow& row = summaries[static_cast<std::size_t>(index)];
        std::cout << index + 1 << ". "
                  << evaporationScheduleName(row.evaporation_case.schedule)
                  << " start=" << row.evaporation_case.start_evaporation
                  << " end=" << row.evaporation_case.end_evaporation
                  << " curve=" << row.evaporation_case.curve
                  << " avg_best=" << row.average_best_distance
                  << " stddev=" << row.stddev_best_distance
                  << "\n";
    }

    std::cout << "\nFiles written to output/evaporation_sweep_detail.csv, "
              << "output/evaporation_sweep_summary.csv, "
              << "output/evaporation_sweep_curves.csv, and "
              << "output/evaporation_sweep_best.txt\n";
    return 0;
}

