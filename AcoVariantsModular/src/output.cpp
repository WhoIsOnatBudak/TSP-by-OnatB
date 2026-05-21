#include "output.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>

namespace aco {

void writeSummaryCsv(
    const std::string& directory,
    const std::vector<AcoResult>& results
) {
    std::ofstream file(std::filesystem::path(directory) / "summary.csv");
    file << "algorithm,best_distance,best_path\n";
    file << std::fixed << std::setprecision(8);

    for (const AcoResult& result : results) {
        file << result.name << "," << result.best_distance << ",";

        for (std::size_t index = 0; index < result.best_path.size(); ++index) {
            if (index > 0) {
                file << " ";
            }

            file << result.best_path[index];
        }

        file << "\n";
    }
}

void writeConvergenceCsv(
    const std::string& directory,
    const std::vector<AcoResult>& results
) {
    std::ofstream file(std::filesystem::path(directory) / "convergence.csv");
    file << "algorithm,iteration,iteration_best,global_best\n";
    file << std::fixed << std::setprecision(8);

    for (const AcoResult& result : results) {
        for (const IterationRecord& record : result.history) {
            file << result.name << "," << record.iteration << ","
                 << record.iteration_best << "," << record.global_best
                 << "\n";
        }
    }
}

void writeConvergenceSvg(
    const std::string& directory,
    const std::vector<AcoResult>& results
) {
    const double width = 1000.0;
    const double height = 620.0;
    const double padding = 70.0;
    const std::vector<std::string> colors = {
        "#7c3aed",
        "#2563eb",
        "#dc2626",
        "#16a34a"
    };

    double min_value = std::numeric_limits<double>::infinity();
    double max_value = -std::numeric_limits<double>::infinity();
    int max_iteration = 1;

    for (const AcoResult& result : results) {
        for (const IterationRecord& record : result.history) {
            min_value = std::min(min_value, record.global_best);
            max_value = std::max(max_value, record.global_best);
            max_iteration = std::max(max_iteration, record.iteration);
        }
    }

    if (min_value == max_value) {
        min_value -= 1.0;
        max_value += 1.0;
    }

    std::ofstream file(std::filesystem::path(directory) / "convergence.svg");
    file << "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" << width
         << "\" height=\"" << height << "\" viewBox=\"0 0 " << width
         << " " << height << "\">\n";
    file << "<rect width=\"100%\" height=\"100%\" fill=\"white\"/>\n";
    file << "<text x=\"24\" y=\"34\" font-family=\"Arial\" font-size=\"20\""
         << " fill=\"#111827\">ACO Variant Convergence</text>\n";
    file << "<line x1=\"" << padding << "\" y1=\"" << height - padding
         << "\" x2=\"" << width - padding << "\" y2=\"" << height - padding
         << "\" stroke=\"#94a3b8\"/>\n";
    file << "<line x1=\"" << padding << "\" y1=\"" << padding
         << "\" x2=\"" << padding << "\" y2=\"" << height - padding
         << "\" stroke=\"#94a3b8\"/>\n";

    const double plot_width = width - 2.0 * padding;
    const double plot_height = height - 2.0 * padding;

    auto project = [&](int iteration, double value) {
        const double x = padding
            + static_cast<double>(iteration)
                / static_cast<double>(std::max(max_iteration, 1))
                * plot_width;
        const double y = height - padding
            - (value - min_value) / (max_value - min_value) * plot_height;
        return Point{x, y};
    };

    for (std::size_t result_index = 0; result_index < results.size(); ++result_index) {
        const AcoResult& result = results[result_index];
        const std::string& color = colors[result_index % colors.size()];

        file << "<polyline fill=\"none\" stroke=\"" << color
             << "\" stroke-width=\"2.2\" points=\"";

        for (const IterationRecord& record : result.history) {
            const Point point = project(record.iteration, record.global_best);
            file << point.x << "," << point.y << " ";
        }

        file << "\"/>\n";

        const double legend_x = width - 260.0;
        const double legend_y = 72.0 + static_cast<double>(result_index) * 24.0;
        file << "<line x1=\"" << legend_x << "\" y1=\"" << legend_y
             << "\" x2=\"" << legend_x + 28.0 << "\" y2=\"" << legend_y
             << "\" stroke=\"" << color << "\" stroke-width=\"3\"/>\n";
        file << "<text x=\"" << legend_x + 38.0 << "\" y=\""
             << legend_y + 4.0 << "\" font-family=\"Arial\""
             << " font-size=\"13\" fill=\"#111827\">" << result.name
             << "</text>\n";
    }

    file << "</svg>\n";
}

void printSummary(const std::vector<AcoResult>& results) {
    std::cout << std::fixed << std::setprecision(8);
    std::cout << "Algorithm comparison\n";
    std::cout << "--------------------\n";

    for (const AcoResult& result : results) {
        std::cout << std::left << std::setw(12) << result.name
                  << " best distance: " << result.best_distance << "\n";
    }
}

}  // namespace aco

