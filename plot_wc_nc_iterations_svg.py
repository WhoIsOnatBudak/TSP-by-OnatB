#!/usr/bin/env python3

import csv
import html
import sys
from pathlib import Path


DEFAULT_INPUT_DIR = Path("AcoAverageBenchmark/output")
DEFAULT_OUTPUT_DIR = Path("Rapor/ImagesCSV")
DEFAULT_SIZES = [100, 150, 200, 250]
REFERENCE_ALGORITHM = "BlindBlendACO"

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


def nice_number(value):
    return f"{value:,.0f}"


def read_detail_rows(path, dataset):
    rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append({
                "source_index": int(row.get("run_id") or row["n_cities"]),
                "algorithm": normalize_algorithm_name(row["algorithm"]),
                "best_distance": float(row["best_distance"]),
                "dataset": dataset,
            })

    if not rows:
        raise ValueError(f"No rows found in {path}")

    apply_reference_sort(rows)
    return rows


def read_iteration_rows(path, dataset):
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
                "dataset": dataset,
            })

    if not rows:
        raise ValueError(f"No rows found in {path}")

    return rows


def apply_reference_sort(rows):
    reference_by_source = {
        row["source_index"]: row["best_distance"]
        for row in rows
        if row["algorithm"] == REFERENCE_ALGORITHM
    }
    ordered_sources = sorted(
        {row["source_index"] for row in rows},
        key=lambda source: (
            reference_by_source.get(source, float("inf")),
            source,
        )
    )
    run_index_by_source = {
        source: index + 1
        for index, source in enumerate(ordered_sources)
    }

    for row in rows:
        row["run_index"] = run_index_by_source[row["source_index"]]


def detail_points_by_algorithm(rows):
    grouped = {}

    for row in rows:
        grouped.setdefault(row["algorithm"], []).append(
            (row["run_index"], row["best_distance"])
        )

    for points in grouped.values():
        points.sort(key=lambda item: item[0])

    return grouped


def detail_averages(rows):
    grouped = {}

    for row in rows:
        grouped.setdefault(row["algorithm"], []).append(row["best_distance"])

    return {
        algorithm: sum(values) / len(values)
        for algorithm, values in grouped.items()
    }


def average_iterations(rows):
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


def bounds(values):
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


def x_ticks(x_min, x_max):
    if x_min == x_max:
        return [x_min]

    candidates = [
        x_min,
        round(x_min + (x_max - x_min) * 0.25),
        round(x_min + (x_max - x_min) * 0.50),
        round(x_min + (x_max - x_min) * 0.75),
        x_max,
    ]
    ticks = []

    for tick in candidates:
        if tick not in ticks:
            ticks.append(tick)

    return ticks


def draw_axes(parts, left, top, width, height, x_min, x_max, y_min, y_max):
    for index in range(5):
        ratio = index / 4
        y = top + height - ratio * height
        value = y_min + ratio * (y_max - y_min)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + width}" '
            f'y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{left - 16}" y="{y + 8:.2f}" font-family="Arial" '
            f'font-size="22" fill="#4b5563" text-anchor="end">'
            f'{nice_number(value)}</text>'
        )

    for tick in x_ticks(x_min, x_max):
        x, _ = project(
            tick,
            y_min,
            x_min,
            x_max,
            y_min,
            y_max,
            left,
            top,
            width,
            height,
        )
        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + height}" stroke="#f3f4f6" stroke-width="1.2"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{top + height + 38}" '
            f'font-family="Arial" font-size="22" fill="#4b5563" '
            f'text-anchor="middle">{tick}</text>'
        )

    parts.append(
        f'<line x1="{left}" y1="{top + height}" x2="{left + width}" '
        f'y2="{top + height}" stroke="#9ca3af" stroke-width="1.5"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" '
        f'y2="{top + height}" stroke="#9ca3af" stroke-width="1.5"/>'
    )


def build_detail_panel(rows, title, top, panel_height, chart_width):
    left = 132
    plot_top = top + 82
    width = chart_width - left - 28
    height = panel_height - 162
    grouped = detail_points_by_algorithm(rows)
    averages = detail_averages(rows)
    all_x = [row["run_index"] for row in rows]
    all_y = [row["best_distance"] for row in rows]
    x_min = min(all_x)
    x_max = max(all_x)
    y_min, y_max = bounds(all_y)
    parts = []

    parts.append(
        f'<text x="{left}" y="{top + 42}" font-family="Arial" '
        f'font-size="34" font-weight="700" fill="#111827">'
        f'{html.escape(title)}</text>'
    )
    draw_axes(parts, left, plot_top, width, height, x_min, x_max, y_min, y_max)

    for algorithm in sorted(grouped):
        color = COLORS.get(algorithm, "#111827")
        average = averages[algorithm]
        _, average_y = project(
            x_min,
            average,
            x_min,
            x_max,
            y_min,
            y_max,
            left,
            plot_top,
            width,
            height,
        )
        parts.append(
            f'<line x1="{left}" y1="{average_y:.2f}" '
            f'x2="{left + width}" y2="{average_y:.2f}" stroke="{color}" '
            f'stroke-width="2.2" stroke-dasharray="8 8" opacity="0.42"/>'
        )

        polyline_points = []

        for run_index, value in grouped[algorithm]:
            x, y = project(
                run_index,
                value,
                x_min,
                x_max,
                y_min,
                y_max,
                left,
                plot_top,
                width,
                height,
            )
            polyline_points.append(f"{x:.2f},{y:.2f}")

        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3.5" '
            f'opacity="0.86" points="{" ".join(polyline_points)}"/>'
        )

        for run_index, value in grouped[algorithm]:
            x, y = project(
                run_index,
                value,
                x_min,
                x_max,
                y_min,
                y_max,
                left,
                plot_top,
                width,
                height,
            )
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.2" '
                f'fill="{color}" opacity="0.86"/>'
            )

    return "\n".join(parts)


def build_iteration_panel(iteration_rows, title, top, panel_height, chart_width):
    left = 132
    plot_top = top + 82
    width = chart_width - left - 28
    height = panel_height - 162
    averages, _ = average_iterations(iteration_rows)
    all_x = [
        iteration
        for points in averages.values()
        for iteration, _ in points
    ]
    all_y = [
        value
        for points in averages.values()
        for _, value in points
    ]
    x_min = min(all_x)
    x_max = max(all_x)
    y_min, y_max = bounds(all_y)
    parts = []

    parts.append(
        f'<text x="{left}" y="{top + 42}" font-family="Arial" '
        f'font-size="34" font-weight="700" fill="#111827">'
        f'{html.escape(title)}</text>'
    )
    draw_axes(parts, left, plot_top, width, height, x_min, x_max, y_min, y_max)

    for algorithm in sorted(averages):
        color = COLORS.get(algorithm, "#111827")
        polyline_points = []

        for iteration, value in averages[algorithm]:
            x, y = project(
                iteration,
                value,
                x_min,
                x_max,
                y_min,
                y_max,
                left,
                plot_top,
                width,
                height,
            )
            polyline_points.append(f"{x:.2f},{y:.2f}")

        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="4.2" '
            f'stroke-linejoin="round" stroke-linecap="round" opacity="0.92" '
            f'points="{" ".join(polyline_points)}"/>'
        )

    return "\n".join(parts)


def build_mode_legend(detail_rows, x, y, width):
    averages = detail_averages(detail_rows)
    algorithms = sorted(averages)
    legend_columns = 2
    column_width = width / legend_columns
    row_height = 92
    parts = []

    parts.append(
        f'<text x="{x}" y="{y}" font-family="Arial" font-size="30" '
        f'font-weight="700" fill="#111827">Algorithm final averages</text>'
    )

    for index, algorithm in enumerate(algorithms):
        item_x = x + (index % legend_columns) * column_width
        row_y = y + 58 + (index // legend_columns) * row_height
        color = COLORS.get(algorithm, "#111827")
        average_text = nice_number(averages[algorithm])
        parts.append(
            f'<line x1="{item_x}" y1="{row_y}" x2="{item_x + 44}" y2="{row_y}" '
            f'stroke="{color}" stroke-width="6"/>'
        )
        parts.append(
            f'<text x="{item_x + 58}" y="{row_y + 7}" font-family="Arial" '
            f'font-size="22" fill="#111827">{html.escape(algorithm)}</text>'
        )
        parts.append(
            f'<text x="{item_x + 58}" y="{row_y + 42}" font-family="Arial" '
            f'font-size="22" fill="#374151">Average: {average_text}</text>'
        )

    return "\n".join(parts)


def build_mode_svg(size, mode_title, detail_rows, iteration_rows):
    width = 1280
    panel_height = 430
    top_start = 118
    panel_gap = 72
    chart_width = width - 48
    legend_x = 132
    legend_width = width - legend_x - 84
    legend_y = top_start + 2 * panel_height + panel_gap + 58
    height = legend_y + 220
    parts = []

    panel_tops = [
        top_start,
        top_start + panel_height + panel_gap,
    ]

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">'
    )
    parts.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    parts.append(
        f'<text x="48" y="74" font-family="Arial" font-size="44" '
        f'font-weight="700" fill="#111827">{size}-City {html.escape(mode_title)} '
        f'Results</text>'
    )
    parts.append(
        build_detail_panel(
            detail_rows,
            "Final tour length by sorted run",
            panel_tops[0],
            panel_height,
            chart_width,
        )
    )
    parts.append(
        build_iteration_panel(
            iteration_rows,
            "Average global best by iteration",
            panel_tops[1],
            panel_height,
            chart_width,
        )
    )
    parts.append(
        build_mode_legend(
            detail_rows,
            legend_x,
            legend_y,
            legend_width,
        )
    )
    parts.append("</svg>")
    return "\n".join(parts)


def paths_for_size(input_dir, size):
    return {
        "wc_detail": input_dir / f"detail_wc_all{size}.csv",
        "wc_iterations": input_dir / f"iterations_wc_all{size}.csv",
        "nc_detail": input_dir / f"detail_nc_all{size}.csv",
        "nc_iterations": input_dir / f"iterations_nc_all{size}.csv",
    }


def render_size(input_dir, output_dir, size):
    paths = paths_for_size(input_dir, size)
    missing = [str(path) for path in paths.values() if not path.exists()]

    if missing:
        raise FileNotFoundError(
            "Missing required input files:\n" + "\n".join(missing)
        )

    wc_detail = read_detail_rows(paths["wc_detail"], "With Cross Check")
    wc_iterations = read_iteration_rows(
        paths["wc_iterations"],
        "With Cross Check"
    )
    nc_detail = read_detail_rows(
        paths["nc_detail"],
        "Without Cross Check"
    )
    nc_iterations = read_iteration_rows(
        paths["nc_iterations"],
        "Without Cross Check"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    wc_output_path = output_dir / f"wc_iterations_all{size}.svg"
    nc_output_path = output_dir / f"nc_iterations_all{size}.svg"
    wc_output_path.write_text(
        build_mode_svg(
            size,
            "With Cross Check",
            wc_detail,
            wc_iterations,
        ),
        encoding="utf-8",
    )
    nc_output_path.write_text(
        build_mode_svg(
            size,
            "Without Cross Check",
            nc_detail,
            nc_iterations,
        ),
        encoding="utf-8",
    )
    return wc_output_path, nc_output_path


def parse_sizes():
    if len(sys.argv) <= 1:
        return DEFAULT_SIZES

    if sys.argv[1].lower() == "all":
        return DEFAULT_SIZES

    return [int(sys.argv[1])]


def main():
    sizes = parse_sizes()
    input_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INPUT_DIR
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_OUTPUT_DIR

    for size in sizes:
        output_paths = render_size(input_dir, output_dir, size)

        for output_path in output_paths:
            print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
