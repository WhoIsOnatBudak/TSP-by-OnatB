#include "aco.hpp"
#include "generation.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

namespace {

struct ParameterCase {
    std::string parameter;
    std::string value;
    std::function<void(AcoParams&)> apply;
};

struct DetailRow {
    std::string parameter;
    std::string value;
    int seed_index = 0;
    unsigned int python_seed = 0;
    unsigned int city_seed = 0;
    double best_distance = 0.0;
    std::size_t blind_rounds = 0;
};

struct SummaryRow {
    std::string parameter;
    std::string value;
    int runs = 0;
    double average_best_distance = 0.0;
    double best_distance = std::numeric_limits<double>::infinity();
    double worst_distance = 0.0;
    double stddev_best_distance = 0.0;
    double average_blind_rounds = 0.0;
};

std::string formatDouble(double value) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(4) << value;
    return stream.str();
}

AcoParams makeBaseParams(int n_cities) {
    AcoParams params;
    params.n_ants = 100;
    params.n_iterations = 100;
    params.alpha = 1.0;
    params.beta = 3.0;
    params.evaporation = 0.8;
    params.q = static_cast<double>(n_cities * 20);
    params.end_evaporation = 0.3;
    params.cross_check = true;
    params.base_pheromone = 1.0;
    params.nearest_neighbor_pheromone = 2;
    params.blind_stagnation_limit = 30;
    params.blind_iterations = 5;
    params.blind_blend_weight = 0.5;
    params.ant_parameter_variation = 0.1;
    params.use_min_max_pheromone = true;
    params.min_max_tau_ratio = 2.0;
    params.pheromone_deposit_top_ants = 1;
    return params;
}

std::vector<ParameterCase> buildParameterCases() {
    std::vector<ParameterCase> cases;

    const std::vector<double> min_max_tau_ratios = {
        0.5,
        1.0,
        2.0,
        3.0,
        5.0,
        10.0,
        20.0
    };

    for (double value : min_max_tau_ratios) {
        cases.push_back({
            "min_max_tau_ratio",
            formatDouble(value),
            [value](AcoParams& params) {
                params.min_max_tau_ratio = value;
            }
        });
    }

    return cases;
}

DetailRow runSingleCase(
    const ParameterCase& parameter_case,
    int seed_index,
    int n_cities
) {
    const unsigned int python_seed = static_cast<unsigned int>(43 + seed_index);
    const unsigned int city_seed = static_cast<unsigned int>(47 + seed_index);
    RandomContext rng(python_seed, python_seed);

    DistanceData data = generateEuclideanDistances(
        n_cities,
        city_seed,
        static_cast<double>(n_cities * 20),
        &rng
    );

    AcoParams params = makeBaseParams(n_cities);
    parameter_case.apply(params);

    const AcoResult result = runAco(
        data.distances,
        &data.coords,
        params,
        rng
    );

    return {
        parameter_case.parameter,
        parameter_case.value,
        seed_index,
        python_seed,
        city_seed,
        result.best_distance,
        result.blind_round_history.size()
    };
}

std::vector<SummaryRow> summarizeRows(const std::vector<DetailRow>& rows) {
    std::vector<SummaryRow> summaries;

    for (const DetailRow& row : rows) {
        auto found = std::find_if(
            summaries.begin(),
            summaries.end(),
            [&](const SummaryRow& summary) {
                return summary.parameter == row.parameter
                    && summary.value == row.value;
            }
        );

        if (found == summaries.end()) {
            summaries.push_back({
                row.parameter,
                row.value
            });
            found = summaries.end() - 1;
        }

        ++found->runs;
        found->average_best_distance += row.best_distance;
        found->average_blind_rounds += static_cast<double>(row.blind_rounds);
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

        summary.average_best_distance /= static_cast<double>(summary.runs);
        summary.average_blind_rounds /= static_cast<double>(summary.runs);

        double variance = 0.0;

        for (const DetailRow& row : rows) {
            if (
                row.parameter != summary.parameter
                || row.value != summary.value
            ) {
                continue;
            }

            const double diff =
                row.best_distance - summary.average_best_distance;
            variance += diff * diff;
        }

        summary.stddev_best_distance = std::sqrt(
            variance / static_cast<double>(summary.runs)
        );
    }

    return summaries;
}

std::vector<SummaryRow> bestRowsByParameter(
    const std::vector<SummaryRow>& summaries
) {
    std::vector<SummaryRow> best_rows;

    for (const SummaryRow& summary : summaries) {
        auto found = std::find_if(
            best_rows.begin(),
            best_rows.end(),
            [&](const SummaryRow& candidate) {
                return candidate.parameter == summary.parameter;
            }
        );

        if (
            found == best_rows.end()
            || summary.average_best_distance < found->average_best_distance
        ) {
            if (found == best_rows.end()) {
                best_rows.push_back(summary);
            } else {
                *found = summary;
            }
        }
    }

    return best_rows;
}

void writeDetailCsv(
    const std::string& directory,
    const std::vector<DetailRow>& rows
) {
    std::ofstream file(std::filesystem::path(directory) / "parameter_sweep_detail.csv");
    file << "parameter,value,seed_index,python_seed,city_seed,"
         << "best_distance,blind_rounds\n";
    file << std::fixed << std::setprecision(8);

    for (const DetailRow& row : rows) {
        file << row.parameter << "," << row.value << ","
             << row.seed_index << "," << row.python_seed << ","
             << row.city_seed << "," << row.best_distance << ","
             << row.blind_rounds << "\n";
    }
}

void writeSummaryCsv(
    const std::string& directory,
    const std::vector<SummaryRow>& rows
) {
    std::ofstream file(std::filesystem::path(directory) / "parameter_sweep_summary.csv");
    file << "parameter,value,runs,average_best_distance,best_distance,"
         << "worst_distance,stddev_best_distance,average_blind_rounds\n";
    file << std::fixed << std::setprecision(8);

    for (const SummaryRow& row : rows) {
        file << row.parameter << "," << row.value << ","
             << row.runs << "," << row.average_best_distance << ","
             << row.best_distance << "," << row.worst_distance << ","
             << row.stddev_best_distance << ","
             << row.average_blind_rounds << "\n";
    }
}

void writeBestReport(
    const std::string& directory,
    const std::vector<SummaryRow>& best_rows,
    int n_cities,
    int runs_per_value
) {
    std::ofstream file(std::filesystem::path(directory) / "parameter_sweep_best.txt");
    file << "Parameter sweep report\n";
    file << "======================\n\n";
    file << "Base values are taken from TestC++/src/main.cpp.\n";
    file << "Each row changes exactly one parameter from the base setup.\n";
    file << "n_cities: " << n_cities << "\n";
    file << "runs_per_value: " << runs_per_value << "\n\n";
    file << "Recommended values by average best distance:\n";
    file << std::fixed << std::setprecision(8);

    for (const SummaryRow& row : best_rows) {
        file << "- " << row.parameter << " = " << row.value
             << " | avg_best=" << row.average_best_distance
             << " | stddev=" << row.stddev_best_distance
             << " | avg_blind_rounds=" << row.average_blind_rounds
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
    const int runs_per_value = argc > 1 ? parseInt(argv, 1, 20) : 10;
    const int n_cities = argc > 2 ? parseInt(argv, 2, 100) : 70;

    if (runs_per_value < 1 || n_cities < 2) {
        std::cout << "Usage: " << argv[0]
                  << " [runs_per_value=20] [n_cities=30]\n";
        return 1;
    }

    const std::vector<ParameterCase> cases = buildParameterCases();
    std::vector<DetailRow> detail_rows;
    const int total_runs = static_cast<int>(cases.size()) * runs_per_value;
    int completed_runs = 0;

    std::cout << "Parameter sweep started\n";
    std::cout << "Parameters tested: " << cases.size() << "\n";
    std::cout << "Runs per value: " << runs_per_value << "\n";
    std::cout << "Total runs: " << total_runs << "\n\n";

    for (const ParameterCase& parameter_case : cases) {
        std::cout << "Testing " << parameter_case.parameter
                  << " = " << parameter_case.value << "\n";

        for (int seed_index = 0; seed_index < runs_per_value; ++seed_index) {
            detail_rows.push_back(runSingleCase(
                parameter_case,
                seed_index,
                n_cities
            ));
            ++completed_runs;

            if (completed_runs % runs_per_value == 0) {
                std::cout << "  completed " << completed_runs << "/"
                          << total_runs << "\n";
            }
        }
    }

    std::vector<SummaryRow> summaries = summarizeRows(detail_rows);
    std::sort(
        summaries.begin(),
        summaries.end(),
        [](const SummaryRow& left, const SummaryRow& right) {
            if (left.parameter == right.parameter) {
                return left.average_best_distance < right.average_best_distance;
            }

            return left.parameter < right.parameter;
        }
    );

    std::vector<SummaryRow> best_rows = bestRowsByParameter(summaries);
    std::sort(
        best_rows.begin(),
        best_rows.end(),
        [](const SummaryRow& left, const SummaryRow& right) {
            return left.parameter < right.parameter;
        }
    );

    std::filesystem::create_directories("output");
    writeDetailCsv("output", detail_rows);
    writeSummaryCsv("output", summaries);
    writeBestReport("output", best_rows, n_cities, runs_per_value);

    std::cout << "\nBest values by parameter\n";
    std::cout << "------------------------\n";
    std::cout << std::fixed << std::setprecision(8);

    for (const SummaryRow& row : best_rows) {
        std::cout << std::left << std::setw(28) << row.parameter
                  << " value=" << std::setw(8) << row.value
                  << " avg_best=" << row.average_best_distance
                  << " stddev=" << row.stddev_best_distance
                  << " avg_blind_rounds=" << row.average_blind_rounds
                  << "\n";
    }

    std::cout << "\nFiles written to output/parameter_sweep_detail.csv, "
              << "output/parameter_sweep_summary.csv, and "
              << "output/parameter_sweep_best.txt\n";
    return 0;
}
