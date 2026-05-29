#!/usr/bin/env python3

import csv
import html
import sys
from pathlib import Path


COLORS = {
    "BlindBlendACO": "#7c3aed",
    "BaselineACO": "#2563eb",
    "ElitistACO": "#dc2626",
    "MaxMinACO": "#16a34a",
}

REFERENCE_ALGORITHM = "BlindBlendACO"


def normalize_algorithm_name(algorithm):
    if algorithm.endswith("AS"):
        return f"{algorithm[:-2]}ACO"

    return algorithm


def apply_reference_sort(rows, reference_algorithm):
    reference_by_source = {
        row["source_index"]: row["best_distance"]
        for row in rows
        if row["algorithm"] == reference_algorithm
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


def read_rows(path, label):
    rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            best_distance = float(row["best_distance"])
            distance_per_city = float(row.get("distance_per_city", 0.0))
            rows.append({
                "source_index": int(row["n_cities"]),
                "algorithm": normalize_algorithm_name(row["algorithm"]),
                "best_distance": best_distance,
                "actual_city_count": (
                    round(best_distance / distance_per_city)
                    if distance_per_city > 0.0
                    else None
                ),
                "dataset": label,
            })

    if not rows:
        raise ValueError(f"No rows found in {path}")

    apply_reference_sort(rows, REFERENCE_ALGORITHM)
    return rows


def group_by_algorithm(rows):
    grouped = {}

    for row in rows:
        grouped.setdefault(row["algorithm"], []).append(
            (row["run_index"], row["best_distance"])
        )

    for points in grouped.values():
        points.sort(key=lambda item: item[0])

    return grouped


def averages_by_algorithm(rows):
    grouped = {}

    for row in rows:
        grouped.setdefault(row["algorithm"], []).append(row["best_distance"])

    return {
        algorithm: sum(values) / len(values)
        for algorithm, values in grouped.items()
    }


def nice_number(value):
    return f"{value:,.0f}"


def metric_bounds(all_rows):
    values = [row["best_distance"] for row in all_rows]
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


def build_legend(all_rows, x, y):
    averages = {
        row["dataset"]: averages_by_algorithm([
            item for item in all_rows
            if item["dataset"] == row["dataset"]
        ])
        for row in all_rows
    }
    algorithms = sorted({row["algorithm"] for row in all_rows})
    parts = []

    parts.append(
        f'<text x="{x}" y="{y}" font-family="Arial" font-size="13" '
        f'font-weight="700" fill="#111827">Algorithm colors</text>'
    )

    for index, algorithm in enumerate(algorithms):
        row_y = y + 26 + index * 24
        color = COLORS.get(algorithm, "#111827")
        parts.append(
            f'<line x1="{x}" y1="{row_y}" x2="{x + 28}" y2="{row_y}" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<text x="{x + 38}" y="{row_y + 4}" font-family="Arial" '
            f'font-size="12" fill="#111827">{html.escape(algorithm)}</text>'
        )

    average_y = y + 26 + len(algorithms) * 24 + 24
    parts.append(
        f'<text x="{x}" y="{average_y}" font-family="Arial" font-size="13" '
        f'font-weight="700" fill="#111827">Tour length averages</text>'
    )

    for dataset_index, dataset in enumerate(sorted(averages)):
        row_y = average_y + 22 + dataset_index * 84
        parts.append(
            f'<text x="{x}" y="{row_y}" font-family="Arial" font-size="12" '
            f'font-weight="700" fill="#374151">{html.escape(dataset)}</text>'
        )

        for alg_index, algorithm in enumerate(algorithms):
            value = averages[dataset][algorithm]
            color = COLORS.get(algorithm, "#111827")
            item_y = row_y + 18 + alg_index * 15
            parts.append(
                f'<circle cx="{x + 5}" cy="{item_y - 4}" r="4" '
                f'fill="{color}"/>'
            )
            parts.append(
                f'<text x="{x + 16}" y="{item_y}" font-family="Arial" '
                f'font-size="11" fill="#4b5563">{html.escape(algorithm)}: '
                f'{nice_number(value)}</text>'
            )

    return "\n".join(parts)


def build_panel(rows, title, top, panel_height, chart_width, y_min, y_max):
    left = 88
    width = chart_width - left - 34
    height = panel_height - 74
    plot_top = top + 42
    grouped = group_by_algorithm(rows)
    averages = averages_by_algorithm(rows)
    x_values = [row["run_index"] for row in rows]
    x_min = min(x_values)
    x_max = max(x_values)
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
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + width}" '
            f'y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" font-family="Arial" '
            f'font-size="11" fill="#4b5563" text-anchor="end">'
            f'{nice_number(value)}</text>'
        )

    x_ticks = [1, 20, 40, 60, 80, x_max]
    for tick in x_ticks:
        x, _ = project(tick, y_min, x_min, x_max, y_min, y_max, left, plot_top, width, height)
        parts.append(
            f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" '
            f'y2="{plot_top + height}" stroke="#f3f4f6" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{plot_top + height + 22}" '
            f'font-family="Arial" font-size="11" fill="#4b5563" '
            f'text-anchor="middle">{tick}</text>'
        )

    parts.append(
        f'<line x1="{left}" y1="{plot_top + height}" x2="{left + width}" '
        f'y2="{plot_top + height}" stroke="#9ca3af"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{plot_top}" x2="{left}" '
        f'y2="{plot_top + height}" stroke="#9ca3af"/>'
    )

    for algorithm, points in grouped.items():
        color = COLORS.get(algorithm, "#111827")
        average = averages[algorithm]
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


def write_svg(wc_rows, nc_rows, output_path):
    all_rows = wc_rows + nc_rows
    width = 1220
    height = 820
    chart_width = 960
    panel_height = 310
    y_min, y_max = metric_bounds(all_rows)
    source_min = min(row["source_index"] for row in all_rows)
    source_max = max(row["source_index"] for row in all_rows)
    run_min = min(row["run_index"] for row in all_rows)
    run_max = max(row["run_index"] for row in all_rows)
    city_counts = [
        row["actual_city_count"]
        for row in all_rows
        if row["actual_city_count"] is not None
    ]
    city_count = (
        max(set(city_counts), key=city_counts.count)
        if city_counts
        else None
    )
    title = (
        f"Tour Length Comparison - {city_count}-City Maps"
        if city_count is not None
        else "Tour Length Comparison"
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="28" y="36" font-family="Arial" font-size="24" '
        f'font-weight="700" fill="#111827">{html.escape(title)}</text>',
        f'<text x="28" y="61" font-family="Arial" font-size="13" fill="#4b5563">'
        f'Only tour length is shown. Source {source_min}-{source_max} values are sorted '
        f'within each panel by {REFERENCE_ALGORITHM} tour length: {run_min}-{run_max}.</text>',
        build_legend(all_rows, 980, 38),
        build_panel(wc_rows, "With Cross Check", 94, panel_height, chart_width, y_min, y_max),
        build_panel(nc_rows, "Without Cross Check", 440, panel_height, chart_width, y_min, y_max),
        '<text x="500" y="790" font-family="Arial" font-size="12" '
        'fill="#4b5563" text-anchor="middle">Sorted map / run index</text>',
        '<text x="20" y="412" font-family="Arial" font-size="12" '
        'fill="#4b5563" text-anchor="middle" transform="rotate(-90 20 412)">Tour length</text>',
        "</svg>",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def main():
    wc_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/detail_wc_all200.csv")
    nc_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Rapor/detail_nc_all200.csv")
    output_path = (
        Path(sys.argv[3])
        if len(sys.argv) > 3
        else Path("Rapor/ImagesCSV/detail_wc_nc_all200_tour_length.svg")
    )

    wc_rows = read_rows(wc_path, "With Cross Check")
    nc_rows = read_rows(nc_path, "Without Cross Check")
    write_svg(wc_rows, nc_rows, output_path)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
