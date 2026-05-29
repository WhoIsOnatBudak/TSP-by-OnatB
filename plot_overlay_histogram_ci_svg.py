#!/usr/bin/env python3

import csv
import html
import math
import sys
from collections import defaultdict
from pathlib import Path


ALGORITHMS = [
    "BlindBlendACO",
    "MaxMinACO",
    "ElitistACO",
    "BaselineACO",
]

COLORS = {
    "BlindBlendACO": "#7c3aed",
    "BaselineACO": "#2563eb",
    "ElitistACO": "#dc2626",
    "MaxMinACO": "#16a34a",
}

T_CRITICAL_95 = {
    19: 2.093,
    29: 2.045,
    40: 2.021,
    50: 2.009,
    60: 2.000,
    80: 1.990,
    100: 1.984,
    120: 1.980,
}


def normalize_algorithm_name(algorithm):
    if algorithm.endswith("AS"):
        return f"{algorithm[:-2]}ACO"

    return algorithm


def read_rows(path, dataset):
    rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            best_distance = float(row["best_distance"])
            distance_per_city = float(row.get("distance_per_city", 0.0))
            rows.append({
                "source_file": path.name,
                "dataset": dataset,
                "algorithm": normalize_algorithm_name(row["algorithm"]),
                "best_distance": best_distance,
                "actual_city_count": (
                    round(best_distance / distance_per_city)
                    if distance_per_city > 0.0
                    else None
                ),
            })

    if not rows:
        raise ValueError(f"No rows found in {path}")

    return rows


def t_critical_95(df):
    if df <= 0:
        return 0.0

    if df in T_CRITICAL_95:
        return T_CRITICAL_95[df]

    known = sorted(T_CRITICAL_95)

    if df > known[-1]:
        return 1.960

    for known_df in known:
        if df < known_df:
            return T_CRITICAL_95[known_df]

    return 1.960


def summarize(values):
    n = len(values)
    mean = sum(values) / n

    if n < 2:
        stddev = 0.0
    else:
        stddev = math.sqrt(
            sum((value - mean) ** 2 for value in values) / (n - 1)
        )

    standard_error = stddev / math.sqrt(n) if n > 0 else 0.0
    ci_half_width = t_critical_95(n - 1) * standard_error

    return {
        "runs": n,
        "mean": mean,
        "ci_lower": mean - ci_half_width,
        "ci_upper": mean + ci_half_width,
        "ci_half_width": ci_half_width,
    }


def nice_number(value):
    return f"{value:,.0f}"


def metric_bounds(rows):
    values = [row["best_distance"] for row in rows]
    lower = min(values)
    upper = max(values)

    if lower == upper:
        return lower - 1.0, upper + 1.0

    padding = (upper - lower) * 0.05
    return lower - padding, upper + padding


def histogram_counts(values, x_min, x_max, bin_count):
    width = (x_max - x_min) / bin_count
    counts = [0 for _ in range(bin_count)]

    for value in values:
        if value >= x_max:
            index = bin_count - 1
        else:
            index = int((value - x_min) / width)
            index = max(0, min(bin_count - 1, index))

        counts[index] += 1

    return counts


def project_x(value, x_min, x_max, left, width):
    if x_max == x_min:
        return left + width / 2

    return left + (value - x_min) / (x_max - x_min) * width


def project_y(value, y_max, top, height):
    if y_max <= 0:
        return top + height

    return top + height - value / y_max * height


def histogram_outline_points(counts, left, top, width, height, y_max):
    bin_width = width / len(counts)
    points = []
    baseline = top + height

    points.append(f"{left:.2f},{baseline:.2f}")

    for index, count in enumerate(counts):
        x0 = left + index * bin_width
        x1 = x0 + bin_width
        y = project_y(count, y_max, top, height)
        points.append(f"{x0:.2f},{y:.2f}")
        points.append(f"{x1:.2f},{y:.2f}")

    points.append(f"{left + width:.2f},{baseline:.2f}")
    return " ".join(points)


def build_legend(rows, dataset, x, y):
    parts = [
        f'<text x="{x}" y="{y}" font-family="Arial" font-size="13" '
        f'font-weight="700" fill="#111827">Mean and 95% CI</text>'
    ]

    for index, algorithm in enumerate(ALGORITHMS):
        values = [
            row["best_distance"]
            for row in rows
            if row["dataset"] == dataset and row["algorithm"] == algorithm
        ]

        if not values:
            continue

        summary = summarize(values)
        row_y = y + 26 + index * 38
        color = COLORS.get(algorithm, "#111827")
        parts.append(
            f'<line x1="{x}" y1="{row_y}" x2="{x + 30}" y2="{row_y}" '
            f'stroke="{color}" stroke-width="4"/>'
        )
        parts.append(
            f'<text x="{x + 40}" y="{row_y - 2}" font-family="Arial" '
            f'font-size="12" fill="#111827">{html.escape(algorithm)}</text>'
        )
        parts.append(
            f'<text x="{x + 40}" y="{row_y + 14}" font-family="Arial" '
            f'font-size="11" fill="#4b5563">mean {nice_number(summary["mean"])} '
            f'| CI +/- {nice_number(summary["ci_half_width"])}</text>'
        )

    return "\n".join(parts)


def build_x_axis(left, y, width, x_min, x_max):
    parts = []

    for index in range(6):
        ratio = index / 5
        value = x_min + ratio * (x_max - x_min)
        x = left + ratio * width
        parts.append(
            f'<text x="{x:.2f}" y="{y}" font-family="Arial" '
            f'font-size="11" fill="#4b5563" text-anchor="middle">'
            f'{nice_number(value)}</text>'
        )

    return "\n".join(parts)


def build_overlay_panel(
    rows,
    dataset,
    x_min,
    x_max,
    y_max,
    bin_count,
    left,
    top,
    width,
    height
):
    parts = [
        f'<text x="{left}" y="{top - 24}" font-family="Arial" '
        f'font-size="18" font-weight="700" fill="#111827">'
        f'{html.escape(dataset)}</text>'
    ]

    for tick in range(5):
        ratio = tick / 4
        count = ratio * y_max
        y = project_y(count, y_max, top, height)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + width}" '
            f'y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" font-family="Arial" '
            f'font-size="11" fill="#4b5563" text-anchor="end">'
            f'{count:.0f}</text>'
        )

    for index in range(6):
        ratio = index / 5
        x = left + ratio * width
        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + height}" stroke="#f3f4f6" stroke-width="1"/>'
        )

    for algorithm in ALGORITHMS:
        values = [
            row["best_distance"]
            for row in rows
            if row["dataset"] == dataset and row["algorithm"] == algorithm
        ]

        if not values:
            continue

        color = COLORS.get(algorithm, "#111827")
        summary = summarize(values)
        counts = histogram_counts(values, x_min, x_max, bin_count)
        outline_points = histogram_outline_points(
            counts,
            left,
            top,
            width,
            height,
            y_max,
        )
        ci_left = project_x(summary["ci_lower"], x_min, x_max, left, width)
        ci_right = project_x(summary["ci_upper"], x_min, x_max, left, width)
        mean_x = project_x(summary["mean"], x_min, x_max, left, width)

        parts.append(
            f'<rect x="{ci_left:.2f}" y="{top}" '
            f'width="{max(ci_right - ci_left, 1.0):.2f}" '
            f'height="{height}" fill="{color}" opacity="0.08"/>'
        )
        parts.append(
            f'<polyline fill="{color}" fill-opacity="0.10" '
            f'stroke="{color}" stroke-width="2.2" '
            f'points="{outline_points}"/>'
        )
        parts.append(
            f'<line x1="{mean_x:.2f}" y1="{top}" '
            f'x2="{mean_x:.2f}" y2="{top + height}" '
            f'stroke="{color}" stroke-width="2.4"/>'
        )

    parts.append(
        f'<line x1="{left}" y1="{top + height}" x2="{left + width}" '
        f'y2="{top + height}" stroke="#9ca3af"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" '
        f'y2="{top + height}" stroke="#9ca3af"/>'
    )
    parts.append(build_x_axis(left, top + height + 24, width, x_min, x_max))
    parts.append(build_legend(rows, dataset, left + width + 34, top + 4))
    return "\n".join(parts)


def write_svg(rows, output_path):
    width = 1220
    height = 760
    left = 84
    panel_width = 820
    panel_height = 250
    bin_count = 16
    x_min, x_max = metric_bounds(rows)
    grouped_values = defaultdict(list)
    city_counts = [
        row["actual_city_count"]
        for row in rows
        if row["actual_city_count"] is not None
    ]
    city_count = (
        max(set(city_counts), key=city_counts.count)
        if city_counts
        else None
    )

    for row in rows:
        grouped_values[(row["dataset"], row["algorithm"])].append(
            row["best_distance"]
        )

    y_max = 1

    for values in grouped_values.values():
        y_max = max(y_max, max(histogram_counts(values, x_min, x_max, bin_count)))

    title = (
        f"Overlayed Tour Length Histograms - {city_count}-City Maps"
        if city_count is not None
        else "Overlayed Tour Length Histograms"
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="28" y="36" font-family="Arial" font-size="24" '
        f'font-weight="700" fill="#111827">{html.escape(title)}</text>',
        '<text x="28" y="61" font-family="Arial" font-size="13" '
        'fill="#4b5563">All algorithms are drawn in the same histogram per condition. '
        'Colored vertical lines show means; light colored bands show 95% confidence intervals.</text>',
        build_overlay_panel(
            rows,
            "With Cross Check",
            x_min,
            x_max,
            y_max,
            bin_count,
            left,
            118,
            panel_width,
            panel_height,
        ),
        build_overlay_panel(
            rows,
            "Without Cross Check",
            x_min,
            x_max,
            y_max,
            bin_count,
            left,
            448,
            panel_width,
            panel_height,
        ),
        f'<text x="{left + panel_width / 2:.2f}" y="744" '
        f'font-family="Arial" font-size="12" fill="#4b5563" '
        f'text-anchor="middle">Tour length</text>',
        '<text x="20" y="390" font-family="Arial" font-size="12" '
        'fill="#4b5563" text-anchor="middle" '
        'transform="rotate(-90 20 390)">Run count</text>',
        "</svg>",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def build_pair(wc_path, nc_path, output_path):
    rows = []
    rows.extend(read_rows(wc_path, "With Cross Check"))
    rows.extend(read_rows(nc_path, "Without Cross Check"))
    write_svg(rows, output_path)
    print(f"Wrote {output_path}")


def main():
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/ImagesCSV")
    build_pair(
        Path("Rapor/detail_wc_all100.csv"),
        Path("Rapor/detail_nc_all100.csv"),
        output_dir / "detail_wc_nc_all100_overlay_histogram_ci.svg",
    )
    build_pair(
        Path("Rapor/detail_wc_all200.csv"),
        Path("Rapor/detail_nc_all200.csv"),
        output_dir / "detail_wc_nc_all200_overlay_histogram_ci.svg",
    )


if __name__ == "__main__":
    main()
