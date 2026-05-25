#!/usr/bin/env python3

import csv
import html
import sys
from pathlib import Path


COLORS = {
    "BlindBlendAS": "#7c3aed",
    "BaselineAS": "#2563eb",
    "ElitistAS": "#dc2626",
    "MaxMinAS": "#16a34a",
}


def read_rows(path):
    raw_rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            raw_rows.append({
                "source_index": int(row["n_cities"]),
                "algorithm": row["algorithm"],
                "best_distance": float(row["best_distance"]),
                "distance_per_city": float(row["distance_per_city"]),
            })

    if not raw_rows:
        raise ValueError(f"No rows found in {path}")

    ordered_sources = sorted({row["source_index"] for row in raw_rows})
    run_index_by_source = {
        source: index + 1
        for index, source in enumerate(ordered_sources)
    }

    for row in raw_rows:
        row["run_index"] = run_index_by_source[row["source_index"]]

    return raw_rows


def group_by_algorithm(rows, metric):
    grouped = {}

    for row in rows:
        grouped.setdefault(row["algorithm"], []).append(
            (row["run_index"], row[metric])
        )

    for points in grouped.values():
        points.sort(key=lambda item: item[0])

    return grouped


def averages_by_algorithm(rows):
    grouped = {}

    for row in rows:
        grouped.setdefault(row["algorithm"], []).append(row)

    averages = {}

    for algorithm, values in grouped.items():
        averages[algorithm] = {
            "best_distance": sum(row["best_distance"] for row in values) / len(values),
            "distance_per_city": sum(row["distance_per_city"] for row in values) / len(values),
        }

    return averages


def nice_number(value):
    return f"{value:.2f}" if abs(value) < 1000 else f"{value:,.0f}"


def metric_bounds(rows, metric):
    values = [row[metric] for row in rows]
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


def build_panel(rows, metric, title, top, panel_height, chart_width, averages):
    left = 88
    width = chart_width - left - 34
    height = panel_height - 76
    plot_top = top + 42
    x_values = [row["run_index"] for row in rows]
    x_min = min(x_values)
    x_max = max(x_values)
    y_min, y_max = metric_bounds(rows, metric)
    grouped = group_by_algorithm(rows, metric)
    parts = []

    parts.append(
        f'<text x="{left}" y="{top + 24}" font-family="Arial" '
        f'font-size="18" font-weight="700" fill="#111827">{html.escape(title)}</text>'
    )

    for index in range(6):
        ratio = index / 5
        y = plot_top + height - ratio * height
        value = y_min + ratio * (y_max - y_min)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + width}" y2="{y:.2f}" '
            f'stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" font-family="Arial" '
            f'font-size="11" fill="#4b5563" text-anchor="end">{nice_number(value)}</text>'
        )

    x_ticks = [1, 20, 40, 60, 80, x_max]
    for tick in x_ticks:
        x, _ = project(tick, y_min, x_min, x_max, y_min, y_max, left, plot_top, width, height)
        parts.append(
            f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" '
            f'y2="{plot_top + height}" stroke="#f3f4f6" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{plot_top + height + 22}" font-family="Arial" '
            f'font-size="11" fill="#4b5563" text-anchor="middle">{tick}</text>'
        )

    parts.append(
        f'<line x1="{left}" y1="{plot_top + height}" x2="{left + width}" '
        f'y2="{plot_top + height}" stroke="#9ca3af"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{plot_top}" x2="{left}" y2="{plot_top + height}" '
        f'stroke="#9ca3af"/>'
    )

    for algorithm, points in grouped.items():
        color = COLORS.get(algorithm, "#111827")
        average = averages[algorithm][metric]
        _, average_y = project(x_min, average, x_min, x_max, y_min, y_max, left, plot_top, width, height)
        polyline_points = []

        parts.append(
            f'<line x1="{left}" y1="{average_y:.2f}" x2="{left + width}" '
            f'y2="{average_y:.2f}" stroke="{color}" stroke-width="1.2" '
            f'stroke-dasharray="5 5" opacity="0.45"/>'
        )

        for run_index, value in points:
            x, y = project(run_index, value, x_min, x_max, y_min, y_max, left, plot_top, width, height)
            polyline_points.append(f"{x:.2f},{y:.2f}")

        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.0" '
            f'opacity="0.88" points="{" ".join(polyline_points)}"/>'
        )

        for run_index, value in points:
            x, y = project(run_index, value, x_min, x_max, y_min, y_max, left, plot_top, width, height)
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.2" '
                f'fill="{color}" opacity="0.90"/>'
            )

    return "\n".join(parts)


def build_legend(rows, x, y):
    averages = averages_by_algorithm(rows)
    algorithms = sorted(averages)
    parts = []

    parts.append(
        f'<text x="{x}" y="{y}" font-family="Arial" font-size="13" '
        f'font-weight="700" fill="#111827">Algorithm averages</text>'
    )

    for index, algorithm in enumerate(algorithms):
        row_y = y + 26 + index * 30
        color = COLORS.get(algorithm, "#111827")
        best_average = averages[algorithm]["best_distance"]
        per_city_average = averages[algorithm]["distance_per_city"]
        parts.append(
            f'<line x1="{x}" y1="{row_y}" x2="{x + 26}" y2="{row_y}" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<text x="{x + 36}" y="{row_y - 2}" font-family="Arial" '
            f'font-size="12" fill="#111827">{html.escape(algorithm)}</text>'
        )
        parts.append(
            f'<text x="{x + 36}" y="{row_y + 14}" font-family="Arial" '
            f'font-size="11" fill="#4b5563">avg {nice_number(best_average)} / '
            f'{per_city_average:.2f}</text>'
        )

    return "\n".join(parts)


def write_svg(rows, output_path):
    width = 1220
    height = 850
    chart_width = 960
    panel_height = 330
    run_min = min(row["run_index"] for row in rows)
    run_max = max(row["run_index"] for row in rows)
    averages = averages_by_algorithm(rows)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="28" y="36" font-family="Arial" font-size="24" '
        'font-weight="700" fill="#111827">ACO Detail - 200-City Maps</text>',
        f'<text x="28" y="61" font-family="Arial" font-size="13" fill="#4b5563">'
        f'All runs are 200-city instances. The original 100-200 values are shown here '
        f'as map/run order: {run_min}-{run_max}.</text>',
        build_legend(rows, 980, 38),
        build_panel(rows, "best_distance", "Best Distance by Map Run", 96, panel_height, chart_width, averages),
        build_panel(rows, "distance_per_city", "Distance Per City by Map Run", 470, panel_height, chart_width, averages),
        '<text x="500" y="820" font-family="Arial" font-size="12" '
        'fill="#4b5563" text-anchor="middle">Map / iteration index</text>',
        "</svg>",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/detail_all200.csv")
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Rapor/detail_all200_visualization.svg")
    rows = read_rows(input_path)
    write_svg(rows, output_path)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
