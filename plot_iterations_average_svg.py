#!/usr/bin/env python3

import csv
import html
import sys
from pathlib import Path


DEFAULT_INPUT = Path("AcoAverageBenchmark/output/iterations.csv")
DEFAULT_OUTPUT = Path("Rapor/ImagesCSV/iterations_average.svg")

COLORS = {
    "BlindBlendACO": "#7c3aed",
    "BaselineACO": "#2563eb",
    "ElitistACO": "#dc2626",
    "MaxMinACO": "#16a34a",
}


def normalize_algorithm_name(algorithm):
    if algorithm.endswith("AS"):
        return f"{algorithm[:-2]}ACO"

    return algorithm


def read_rows(path):
    rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append({
                "run_id": int(row["run_id"]),
                "n_cities": int(row["n_cities"]),
                "algorithm": normalize_algorithm_name(row["algorithm"]),
                "iteration": int(row["iteration"]),
                "global_best_distance": float(row["global_best_distance"]),
            })

    if not rows:
        raise ValueError(f"No rows found in {path}")

    return rows


def average_by_algorithm_and_iteration(rows):
    grouped = {}
    run_ids = {}

    for row in rows:
        algorithm = row["algorithm"]
        iteration = row["iteration"]
        grouped.setdefault(algorithm, {}).setdefault(iteration, []).append(
            row["global_best_distance"]
        )
        run_ids.setdefault(algorithm, set()).add(row["run_id"])

    averages = {}

    for algorithm, iteration_map in grouped.items():
        points = []

        for iteration, values in iteration_map.items():
            points.append((iteration, sum(values) / len(values)))

        points.sort(key=lambda item: item[0])
        averages[algorithm] = points

    return averages, {algorithm: len(ids) for algorithm, ids in run_ids.items()}


def final_averages(averages):
    result = {}

    for algorithm, points in averages.items():
        result[algorithm] = points[-1][1]

    return result


def nice_number(value):
    return f"{value:,.0f}"


def metric_bounds(averages):
    values = [
        value
        for points in averages.values()
        for _, value in points
    ]
    lower = min(values)
    upper = max(values)

    if lower == upper:
        return lower - 1.0, upper + 1.0

    padding = (upper - lower) * 0.08
    return lower - padding, upper + padding


def project(x, y, x_min, x_max, y_min, y_max, left, top, width, height):
    if x_max == x_min:
        px = left + width / 2
    else:
        px = left + (x - x_min) / (x_max - x_min) * width

    if y_max == y_min:
        py = top + height / 2
    else:
        py = top + height - (y - y_min) / (y_max - y_min) * height

    return px, py


def build_legend(averages, run_counts, x, y):
    finals = final_averages(averages)
    algorithms = sorted(averages)
    parts = []

    parts.append(
        f'<text x="{x}" y="{y}" font-family="Arial" font-size="13" '
        f'font-weight="700" fill="#111827">Algorithm averages</text>'
    )

    for index, algorithm in enumerate(algorithms):
        row_y = y + 28 + index * 34
        color = COLORS.get(algorithm, "#111827")
        parts.append(
            f'<line x1="{x}" y1="{row_y}" x2="{x + 30}" y2="{row_y}" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<text x="{x + 40}" y="{row_y - 2}" font-family="Arial" '
            f'font-size="12" fill="#111827">{html.escape(algorithm)}</text>'
        )
        parts.append(
            f'<text x="{x + 40}" y="{row_y + 14}" font-family="Arial" '
            f'font-size="11" fill="#4b5563">final avg '
            f'{nice_number(finals[algorithm])} | runs {run_counts[algorithm]}</text>'
        )

    return "\n".join(parts)


def build_svg(rows, averages, run_counts):
    width = 1180
    height = 720
    left = 92
    top = 112
    chart_width = 820
    chart_height = 500
    legend_x = 950
    legend_y = 132

    all_iterations = [
        iteration
        for points in averages.values()
        for iteration, _ in points
    ]
    x_min = min(all_iterations)
    x_max = max(all_iterations)
    y_min, y_max = metric_bounds(averages)
    city_counts = sorted({row["n_cities"] for row in rows})
    total_runs = len({row["run_id"] for row in rows})
    parts = []

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">'
    )
    parts.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    parts.append(
        '<text x="48" y="52" font-family="Arial" font-size="25" '
        'font-weight="700" fill="#111827">Average Convergence by Algorithm</text>'
    )
    city_label = (
        str(city_counts[0])
        if len(city_counts) == 1
        else f"{city_counts[0]}-{city_counts[-1]}"
    )
    parts.append(
        f'<text x="48" y="78" font-family="Arial" font-size="13" '
        f'fill="#4b5563">Mean global best per iteration | city count {city_label} '
        f'| total maps {total_runs}</text>'
    )

    for index in range(6):
        ratio = index / 5
        y = top + chart_height - ratio * chart_height
        value = y_min + ratio * (y_max - y_min)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_width}" '
            f'y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" font-family="Arial" '
            f'font-size="11" fill="#4b5563" text-anchor="end">'
            f'{nice_number(value)}</text>'
        )

    if x_max == x_min:
        x_ticks = [x_min]
    else:
        tick_candidates = [
            x_min,
            round(x_min + (x_max - x_min) * 0.25),
            round(x_min + (x_max - x_min) * 0.50),
            round(x_min + (x_max - x_min) * 0.75),
            x_max,
        ]
        x_ticks = []
        for tick in tick_candidates:
            if tick not in x_ticks:
                x_ticks.append(tick)

    for tick in x_ticks:
        x, _ = project(
            tick,
            y_min,
            x_min,
            x_max,
            y_min,
            y_max,
            left,
            top,
            chart_width,
            chart_height,
        )
        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + chart_height}" stroke="#f3f4f6" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{top + chart_height + 24}" '
            f'font-family="Arial" font-size="11" fill="#4b5563" '
            f'text-anchor="middle">{tick}</text>'
        )

    parts.append(
        f'<line x1="{left}" y1="{top + chart_height}" '
        f'x2="{left + chart_width}" y2="{top + chart_height}" '
        f'stroke="#9ca3af"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" '
        f'y2="{top + chart_height}" stroke="#9ca3af"/>'
    )
    parts.append(
        f'<text x="{left + chart_width / 2}" y="{top + chart_height + 58}" '
        f'font-family="Arial" font-size="13" fill="#374151" '
        f'text-anchor="middle">Iteration</text>'
    )
    parts.append(
        f'<text x="24" y="{top + chart_height / 2}" font-family="Arial" '
        f'font-size="13" fill="#374151" text-anchor="middle" '
        f'transform="rotate(-90 24 {top + chart_height / 2})">'
        f'Average global best tour length</text>'
    )

    for algorithm in sorted(averages):
        points = averages[algorithm]
        color = COLORS.get(algorithm, "#111827")
        polyline_points = []

        for iteration, value in points:
            x, y = project(
                iteration,
                value,
                x_min,
                x_max,
                y_min,
                y_max,
                left,
                top,
                chart_width,
                chart_height,
            )
            polyline_points.append(f"{x:.2f},{y:.2f}")

        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.6" '
            f'stroke-linejoin="round" stroke-linecap="round" opacity="0.92" '
            f'points="{" ".join(polyline_points)}"/>'
        )

    parts.append(build_legend(averages, run_counts, legend_x, legend_y))
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    rows = read_rows(input_path)
    averages, run_counts = average_by_algorithm_and_iteration(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_svg(rows, averages, run_counts),
        encoding="utf-8"
    )

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
