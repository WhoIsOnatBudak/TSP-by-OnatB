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


def read_detail_csv(path):
    rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append({
                "n_cities": int(row["n_cities"]),
                "algorithm": row["algorithm"],
                "best_distance": float(row["best_distance"]),
                "distance_per_city": float(row["distance_per_city"]),
            })

    if not rows:
        raise ValueError(f"No rows found in {path}")

    return rows


def group_by_algorithm(rows, metric):
    grouped = {}

    for row in rows:
        grouped.setdefault(row["algorithm"], []).append(
            (row["n_cities"], row[metric])
        )

    for values in grouped.values():
        values.sort(key=lambda item: item[0])

    return grouped


def nice_number(value):
    return f"{value:.2f}" if abs(value) < 1000 else f"{value:,.0f}"


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


def metric_bounds(rows, metric):
    values = [row[metric] for row in rows]
    lower = min(values)
    upper = max(values)

    if lower == upper:
        return lower - 1.0, upper + 1.0

    padding = (upper - lower) * 0.08
    return lower - padding, upper + padding


def build_panel(rows, metric, title, top, panel_height, chart_width):
    left = 82
    width = chart_width - left - 34
    height = panel_height - 72
    plot_top = top + 42
    x_values = [row["n_cities"] for row in rows]
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

    x_tick_count = min(8, max(2, x_max - x_min + 1))
    for index in range(x_tick_count):
        ratio = index / (x_tick_count - 1)
        city = round(x_min + ratio * (x_max - x_min))
        x, _ = project(city, y_min, x_min, x_max, y_min, y_max, left, plot_top, width, height)
        parts.append(
            f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_top + height}" '
            f'stroke="#f3f4f6" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{plot_top + height + 22}" font-family="Arial" '
            f'font-size="11" fill="#4b5563" text-anchor="middle">{city}</text>'
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
        polyline_points = []

        for city, value in points:
            x, y = project(city, value, x_min, x_max, y_min, y_max, left, plot_top, width, height)
            polyline_points.append(f"{x:.2f},{y:.2f}")

        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.4" '
            f'points="{" ".join(polyline_points)}"/>'
        )

        for city, value in points:
            x, y = project(city, value, x_min, x_max, y_min, y_max, left, plot_top, width, height)
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.6" fill="{color}"/>'
            )

    return "\n".join(parts)


def build_legend(rows, x, y):
    algorithms = sorted({row["algorithm"] for row in rows})
    parts = []

    for index, algorithm in enumerate(algorithms):
        color = COLORS.get(algorithm, "#111827")
        row_y = y + index * 24
        parts.append(
            f'<line x1="{x}" y1="{row_y}" x2="{x + 28}" y2="{row_y}" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<text x="{x + 38}" y="{row_y + 4}" font-family="Arial" '
            f'font-size="13" fill="#111827">{html.escape(algorithm)}</text>'
        )

    return "\n".join(parts)


def write_svg(rows, output_path):
    width = 1120
    height = 860
    panel_height = 345
    chart_width = 920
    city_min = min(row["n_cities"] for row in rows)
    city_max = max(row["n_cities"] for row in rows)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="28" y="36" font-family="Arial" font-size="24" '
        'font-weight="700" fill="#111827">ACO Benchmark Detail</text>',
        f'<text x="28" y="60" font-family="Arial" font-size="13" fill="#4b5563">'
        f'City range: {city_min}-{city_max}. Lower values are better.</text>',
        build_legend(rows, 920, 34),
        build_panel(rows, "best_distance", "Best Distance", 86, panel_height, chart_width),
        build_panel(rows, "distance_per_city", "Distance Per City", 470, panel_height, chart_width),
        '<text x="470" y="832" font-family="Arial" font-size="12" '
        'fill="#4b5563" text-anchor="middle">Number of cities</text>',
        "</svg>",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/detail_wc_100.csv")
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Rapor/detail_visualization.svg")
    rows = read_detail_csv(input_path)
    write_svg(rows, output_path)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
