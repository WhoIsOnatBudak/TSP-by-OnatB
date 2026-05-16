#include "plots.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <string>

namespace {

struct PlotEvent {
    std::string type;
    int iteration = 0;
    int blind_iteration = -1;
    double best_distance = 0.0;
};

struct Bounds {
    double min_x = 0.0;
    double max_x = 1.0;
    double min_y = 0.0;
    double max_y = 1.0;
};

std::string pathJoin(const std::string& directory, const std::string& file) {
    return (std::filesystem::path(directory) / file).string();
}

Bounds getBounds(const std::vector<Point>& coords) {
    Bounds bounds;

    if (coords.empty()) {
        return bounds;
    }

    bounds.min_x = bounds.max_x = coords.front().x;
    bounds.min_y = bounds.max_y = coords.front().y;

    for (const Point& point : coords) {
        bounds.min_x = std::min(bounds.min_x, point.x);
        bounds.max_x = std::max(bounds.max_x, point.x);
        bounds.min_y = std::min(bounds.min_y, point.y);
        bounds.max_y = std::max(bounds.max_y, point.y);
    }

    if (bounds.max_x == bounds.min_x) {
        bounds.max_x += 1.0;
    }

    if (bounds.max_y == bounds.min_y) {
        bounds.max_y += 1.0;
    }

    return bounds;
}

Point projectPoint(
    const Point& point,
    const Bounds& bounds,
    double width,
    double height,
    double padding
) {
    const double drawable_width = width - 2.0 * padding;
    const double drawable_height = height - 2.0 * padding;
    const double x = padding
        + (point.x - bounds.min_x) / (bounds.max_x - bounds.min_x)
        * drawable_width;
    const double y = height - padding
        - (point.y - bounds.min_y) / (bounds.max_y - bounds.min_y)
        * drawable_height;

    return {x, y};
}

void writeSvgStart(
    std::ofstream& file,
    double width,
    double height,
    const std::string& title
) {
    file << "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" << width
         << "\" height=\"" << height << "\" viewBox=\"0 0 " << width
         << " " << height << "\">\n";
    file << "<rect width=\"100%\" height=\"100%\" fill=\"white\"/>\n";
    file << "<text x=\"20\" y=\"28\" font-family=\"Arial\" font-size=\"18\""
         << " fill=\"#111827\">" << title << "</text>\n";
}

void writeSvgEnd(std::ofstream& file) {
    file << "</svg>\n";
}

void writeCitiesCsv(
    const std::string& directory,
    const std::vector<Point>& coords
) {
    std::ofstream file(pathJoin(directory, "cities.csv"));
    file << "city,x,y\n";
    file << std::fixed << std::setprecision(8);

    for (std::size_t city = 0; city < coords.size(); ++city) {
        file << city << "," << coords[city].x << "," << coords[city].y
             << "\n";
    }
}

void writeCitiesSvg(
    const std::string& directory,
    const std::vector<Point>& coords
) {
    const double width = 900.0;
    const double height = 650.0;
    const double padding = 60.0;
    const Bounds bounds = getBounds(coords);
    std::ofstream file(pathJoin(directory, "cities.svg"));

    writeSvgStart(file, width, height, "Generated Cities");

    for (std::size_t city = 0; city < coords.size(); ++city) {
        const Point point = projectPoint(
            coords[city],
            bounds,
            width,
            height,
            padding
        );
        file << "<circle cx=\"" << point.x << "\" cy=\"" << point.y
             << "\" r=\"4\" fill=\"#2563eb\"/>\n";
        file << "<text x=\"" << point.x + 6.0 << "\" y=\"" << point.y - 6.0
             << "\" font-family=\"Arial\" font-size=\"10\" fill=\"#111827\">"
             << city << "</text>\n";
    }

    writeSvgEnd(file);
}

void writeBestTourCsv(
    const std::string& directory,
    const std::vector<Point>& coords,
    const std::vector<int>& best_path
) {
    std::ofstream file(pathJoin(directory, "best_tour.csv"));
    file << "order,city,x,y\n";
    file << std::fixed << std::setprecision(8);

    for (std::size_t order = 0; order < best_path.size(); ++order) {
        const int city = best_path[order];
        const Point& point = coords[static_cast<std::size_t>(city)];
        file << order << "," << city << "," << point.x << "," << point.y
             << "\n";
    }

    if (!best_path.empty()) {
        const int city = best_path.front();
        const Point& point = coords[static_cast<std::size_t>(city)];
        file << best_path.size() << "," << city << "," << point.x << ","
             << point.y << "\n";
    }
}

void writeBestTourSvg(
    const std::string& directory,
    const std::vector<Point>& coords,
    const std::vector<int>& best_path
) {
    const double width = 900.0;
    const double height = 650.0;
    const double padding = 60.0;
    const Bounds bounds = getBounds(coords);
    std::ofstream file(pathJoin(directory, "best_tour.svg"));

    writeSvgStart(file, width, height, "Best Tour Found by ACO");

    for (std::size_t order = 0; order < best_path.size(); ++order) {
        const int current_city = best_path[order];
        const int next_city = best_path[(order + 1) % best_path.size()];
        const Point current = projectPoint(
            coords[static_cast<std::size_t>(current_city)],
            bounds,
            width,
            height,
            padding
        );
        const Point next = projectPoint(
            coords[static_cast<std::size_t>(next_city)],
            bounds,
            width,
            height,
            padding
        );

        file << "<line x1=\"" << current.x << "\" y1=\"" << current.y
             << "\" x2=\"" << next.x << "\" y2=\"" << next.y
             << "\" stroke=\"#334155\" stroke-width=\"1.2\""
             << " opacity=\"0.75\"/>\n";
    }

    for (std::size_t city = 0; city < coords.size(); ++city) {
        const Point point = projectPoint(
            coords[city],
            bounds,
            width,
            height,
            padding
        );
        file << "<circle cx=\"" << point.x << "\" cy=\"" << point.y
             << "\" r=\"4\" fill=\"#2563eb\"/>\n";
        file << "<text x=\"" << point.x + 6.0 << "\" y=\"" << point.y - 6.0
             << "\" font-family=\"Arial\" font-size=\"10\" fill=\"#111827\">"
             << city << "</text>\n";
    }

    writeSvgEnd(file);
}

std::vector<PlotEvent> buildConvergenceEvents(const AcoResult& result) {
    std::map<int, std::vector<BlindRoundRecord>> grouped_blind_rounds;

    for (const BlindRoundRecord& blind_round : result.blind_round_history) {
        grouped_blind_rounds[blind_round.aco_iteration].push_back(blind_round);
    }

    std::vector<PlotEvent> events;

    for (
        std::size_t iteration = 0;
        iteration < result.best_per_iteration.size();
        ++iteration
    ) {
        events.push_back({
            "aco",
            static_cast<int>(iteration),
            -1,
            result.best_per_iteration[iteration]
        });

        std::vector<BlindRoundRecord>& blind_rounds =
            grouped_blind_rounds[static_cast<int>(iteration)];
        std::sort(
            blind_rounds.begin(),
            blind_rounds.end(),
            [](const BlindRoundRecord& left, const BlindRoundRecord& right) {
                return left.blind_iteration < right.blind_iteration;
            }
        );

        for (const BlindRoundRecord& blind_round : blind_rounds) {
            events.push_back({
                "blind",
                static_cast<int>(iteration),
                blind_round.blind_iteration,
                blind_round.best_distance
            });
        }
    }

    return events;
}

void writeConvergenceCsv(
    const std::string& directory,
    const AcoResult& result
) {
    const std::vector<PlotEvent> events = buildConvergenceEvents(result);
    std::ofstream file(pathJoin(directory, "convergence.csv"));
    file << "event_order,type,aco_iteration,blind_iteration,best_distance\n";
    file << std::fixed << std::setprecision(8);

    for (std::size_t index = 0; index < events.size(); ++index) {
        file << index + 1 << "," << events[index].type << ","
             << events[index].iteration << ","
             << events[index].blind_iteration << ","
             << events[index].best_distance << "\n";
    }
}

void writeLinePlotSvg(
    const std::string& path,
    const std::string& title,
    const std::vector<double>& values,
    const std::string& stroke
) {
    const double width = 900.0;
    const double height = 520.0;
    const double padding = 60.0;
    std::ofstream file(path);

    writeSvgStart(file, width, height, title);

    if (values.empty()) {
        writeSvgEnd(file);
        return;
    }

    const auto [min_it, max_it] = std::minmax_element(
        values.begin(),
        values.end()
    );
    double min_value = *min_it;
    double max_value = *max_it;

    if (min_value == max_value) {
        min_value -= 1.0;
        max_value += 1.0;
    }

    const double plot_width = width - 2.0 * padding;
    const double plot_height = height - 2.0 * padding;

    file << "<polyline fill=\"none\" stroke=\"" << stroke
         << "\" stroke-width=\"2\" points=\"";

    for (std::size_t index = 0; index < values.size(); ++index) {
        const double x = padding
            + (values.size() == 1
                ? 0.0
                : static_cast<double>(index)
                    / static_cast<double>(values.size() - 1) * plot_width);
        const double y = height - padding
            - (values[index] - min_value) / (max_value - min_value)
            * plot_height;
        file << x << "," << y << " ";
    }

    file << "\"/>\n";

    for (std::size_t index = 0; index < values.size(); ++index) {
        const double x = padding
            + (values.size() == 1
                ? 0.0
                : static_cast<double>(index)
                    / static_cast<double>(values.size() - 1) * plot_width);
        const double y = height - padding
            - (values[index] - min_value) / (max_value - min_value)
            * plot_height;
        file << "<circle cx=\"" << x << "\" cy=\"" << y
             << "\" r=\"3\" fill=\"" << stroke << "\"/>\n";
    }

    writeSvgEnd(file);
}

void writeConvergenceSvg(
    const std::string& directory,
    const AcoResult& result
) {
    const std::vector<PlotEvent> events = buildConvergenceEvents(result);
    const double width = 900.0;
    const double height = 520.0;
    const double padding = 60.0;
    std::ofstream file(pathJoin(directory, "convergence.svg"));

    writeSvgStart(file, width, height, "Best Distance per Iteration");

    if (events.empty()) {
        writeSvgEnd(file);
        return;
    }

    double min_value = std::numeric_limits<double>::infinity();
    double max_value = -std::numeric_limits<double>::infinity();

    for (const PlotEvent& event : events) {
        min_value = std::min(min_value, event.best_distance);
        max_value = std::max(max_value, event.best_distance);
    }

    if (min_value == max_value) {
        min_value -= 1.0;
        max_value += 1.0;
    }

    const double plot_width = width - 2.0 * padding;
    const double plot_height = height - 2.0 * padding;

    auto project = [&](std::size_t index, double value) {
        const double x = padding
            + (events.size() == 1
                ? 0.0
                : static_cast<double>(index)
                    / static_cast<double>(events.size() - 1) * plot_width);
        const double y = height - padding
            - (value - min_value) / (max_value - min_value) * plot_height;
        return Point{x, y};
    };

    for (std::size_t index = 1; index < events.size(); ++index) {
        const Point previous = project(index - 1, events[index - 1].best_distance);
        const Point current = project(index, events[index].best_distance);
        const bool blind_segment = events[index].type == "blind";

        file << "<line x1=\"" << previous.x << "\" y1=\"" << previous.y
             << "\" x2=\"" << current.x << "\" y2=\"" << current.y
             << "\" stroke=\"" << (blind_segment ? "#f97316" : "#2563eb")
             << "\" stroke-width=\"2\""
             << (blind_segment ? " stroke-dasharray=\"6 4\"" : "")
             << "/>\n";
    }

    for (std::size_t index = 0; index < events.size(); ++index) {
        const Point point = project(index, events[index].best_distance);

        if (events[index].type == "blind") {
            file << "<rect x=\"" << point.x - 4.0 << "\" y=\"" << point.y - 4.0
                 << "\" width=\"8\" height=\"8\" fill=\"#f97316\""
                 << " stroke=\"#dc2626\"/>\n";
        } else {
            file << "<circle cx=\"" << point.x << "\" cy=\"" << point.y
                 << "\" r=\"4\" fill=\"#2563eb\"/>\n";
        }
    }

    file << "<circle cx=\"680\" cy=\"28\" r=\"4\" fill=\"#2563eb\"/>\n";
    file << "<text x=\"692\" y=\"33\" font-family=\"Arial\" font-size=\"12\""
         << " fill=\"#111827\">ACO Iterations</text>\n";
    file << "<rect x=\"795\" y=\"24\" width=\"8\" height=\"8\""
         << " fill=\"#f97316\" stroke=\"#dc2626\"/>\n";
    file << "<text x=\"810\" y=\"33\" font-family=\"Arial\" font-size=\"12\""
         << " fill=\"#111827\">Blind Rounds</text>\n";

    writeSvgEnd(file);
}

void writeEvaporationCsv(
    const std::string& directory,
    const std::vector<double>& evaporation_history
) {
    std::ofstream file(pathJoin(directory, "evaporation.csv"));
    file << "iteration,evaporation\n";
    file << std::fixed << std::setprecision(8);

    for (std::size_t iteration = 0; iteration < evaporation_history.size(); ++iteration) {
        file << iteration << "," << evaporation_history[iteration] << "\n";
    }
}

void writePheromoneCsv(
    const std::string& directory,
    const Matrix& pheromone
) {
    std::ofstream file(pathJoin(directory, "pheromone.csv"));
    file << std::fixed << std::setprecision(8);

    for (const std::vector<double>& row : pheromone) {
        for (std::size_t col = 0; col < row.size(); ++col) {
            if (col > 0) {
                file << ",";
            }

            file << row[col];
        }

        file << "\n";
    }
}

} // namespace

void writeOutputFiles(
    const std::string& directory,
    const std::vector<Point>& coords,
    const AcoResult& result
) {
    std::filesystem::create_directories(directory);

    writeCitiesCsv(directory, coords);
    writeCitiesSvg(directory, coords);
    writeBestTourCsv(directory, coords, result.best_path);
    writeBestTourSvg(directory, coords, result.best_path);
    writeConvergenceCsv(directory, result);
    writeConvergenceSvg(directory, result);
    writeEvaporationCsv(directory, result.evaporation_history);
    writeLinePlotSvg(
        pathJoin(directory, "evaporation.svg"),
        "Evaporation Rate per Iteration",
        result.evaporation_history,
        "#16a34a"
    );
    writePheromoneCsv(directory, result.pheromone);
}
