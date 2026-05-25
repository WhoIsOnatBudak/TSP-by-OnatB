#!/usr/bin/env python3

import csv
import html
import math
import sys
from collections import defaultdict
from pathlib import Path


PARAMETER_LABELS = {
    "ant_parameter_variation": "Ant Parameter Variation",
    "base_pheromone": "Base Pheromone",
    "blind_blend_weight": "Blind Blend Weight",
    "blind_iterations": "Blind Iterations",
    "blind_stagnation_limit": "Blind Stagnation Limit",
    "nearest_neighbor_pheromone": "Nearest Neighbor Pheromone",
}

PARAMETER_COLORS = {
    "ant_parameter_variation": "#7c3aed",
    "base_pheromone": "#0891b2",
    "blind_blend_weight": "#dc2626",
    "blind_iterations": "#16a34a",
    "blind_stagnation_limit": "#d97706",
    "nearest_neighbor_pheromone": "#2563eb",
}


def read_rows(path):
    rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append({
                "parameter": row["parameter"],
                "value_text": row["value"],
                "value": float(row["value"]),
                "seed_index": int(row["seed_index"]),
                "best_distance": float(row["best_distance"]),
                "blind_rounds": float(row["blind_rounds"]),
            })

    if not rows:
        raise ValueError(f"No rows found in {path}")

    return rows


def summarize(rows):
    groups = defaultdict(list)

    for row in rows:
        groups[(row["parameter"], row["value"], row["value_text"])].append(row)

    summaries = defaultdict(list)

    for (parameter, value, value_text), values in groups.items():
        best_distances = [row["best_distance"] for row in values]
        blind_rounds = [row["blind_rounds"] for row in values]
        average = sum(best_distances) / len(best_distances)
        round_average = sum(blind_rounds) / len(blind_rounds)
        variance = sum((distance - average) ** 2 for distance in best_distances)
        variance /= len(best_distances)

        summaries[parameter].append({
            "value": value,
            "value_text": value_text,
            "runs": len(values),
            "run_rows": sorted(values, key=lambda row: row["seed_index"]),
            "average_best_distance": average,
            "stddev_best_distance": math.sqrt(variance),
            "best_distance": min(best_distances),
            "worst_distance": max(best_distances),
            "average_blind_rounds": round_average,
        })

    for values in summaries.values():
        values.sort(key=lambda row: row["value"])

    return summaries


def nice_number(value):
    return f"{value:.2f}" if abs(value) < 1000 else f"{value:,.0f}"


def nice_value(value):
    if float(value).is_integer():
        return str(int(value))

    return f"{value:g}"


def y_bounds(points):
    values = []

    for point in points:
        values.append(point["average_best_distance"])
        values.extend(row["best_distance"] for row in point["run_rows"])

    lower = min(values)
    upper = max(values)

    if math.isclose(lower, upper):
        return lower - 1.0, upper + 1.0

    padding = (upper - lower) * 0.08
    return lower - padding, upper + padding


def project(x, y, x_min, x_max, y_min, y_max, left, top, width, height):
    if math.isclose(x_min, x_max):
        px = left + width / 2
    else:
        px = left + (x - x_min) / (x_max - x_min) * width

    if math.isclose(y_min, y_max):
        py = top + height / 2
    else:
        py = top + height - (y - y_min) / (y_max - y_min) * height

    return px, py


def average_marker_points(x, y, size=6):
    return " ".join([
        f"{x:.2f},{y - size:.2f}",
        f"{x + size:.2f},{y:.2f}",
        f"{x:.2f},{y + size:.2f}",
        f"{x - size:.2f},{y:.2f}",
    ])


def write_parameter_svg(parameter, points, output_path):
    width = 920
    height = 560
    left = 92
    right = 44
    top = 100
    bottom = 92
    chart_width = width - left - right
    chart_height = height - top - bottom
    color = PARAMETER_COLORS.get(parameter, "#111827")
    title = PARAMETER_LABELS.get(parameter, parameter)
    x_values = [point["value"] for point in points]
    x_min = min(x_values)
    x_max = max(x_values)
    x_padding = (x_max - x_min) * 0.08 if not math.isclose(x_min, x_max) else 1.0
    x_min -= x_padding
    x_max += x_padding
    y_min, y_max = y_bounds(points)
    best_point = min(points, key=lambda point: point["average_best_distance"])
    overall_average = (
        sum(point["average_best_distance"] for point in points) / len(points)
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="28" y="38" font-family="Arial" font-size="24" '
        f'font-weight="700" fill="#111827">{html.escape(title)}</text>',
        f'<text x="28" y="64" font-family="Arial" font-size="13" fill="#4b5563">'
        f'Each colored dot is one test run. Black diamonds and labels show '
        f'the average for each tested value ({points[0]["runs"]} runs per value). '
        f'Lower is better.</text>',
        f'<text x="28" y="84" font-family="Arial" font-size="13" fill="#111827">'
        f'Best value: {html.escape(nice_value(best_point["value"]))} = '
        f'{nice_number(best_point["average_best_distance"])} | '
        f'Overall average: {nice_number(overall_average)}</text>',
    ]

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

    for point in points:
        x, _ = project(
            point["value"],
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
            f'<text x="{x:.2f}" y="{top + chart_height + 26}" '
            f'font-family="Arial" font-size="12" fill="#374151" '
            f'text-anchor="middle">{html.escape(nice_value(point["value"]))}</text>'
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

    average_line_points = []

    for point in points:
        x, y = project(
            point["value"],
            point["average_best_distance"],
            x_min,
            x_max,
            y_min,
            y_max,
            left,
            top,
            chart_width,
            chart_height,
        )
        average_line_points.append(f"{x:.2f},{y:.2f}")

    parts.append(
        f'<polyline fill="none" stroke="#111827" stroke-width="1.4" '
        f'opacity="0.55" stroke-dasharray="5 5" '
        f'points="{" ".join(average_line_points)}"/>'
    )

    for point in points:
        x, average_y = project(
            point["value"],
            point["average_best_distance"],
            x_min,
            x_max,
            y_min,
            y_max,
            left,
            top,
            chart_width,
            chart_height,
        )
        spread = 34.0
        run_rows = point["run_rows"]

        for index, run in enumerate(run_rows):
            jitter = 0.0

            if len(run_rows) > 1:
                jitter = -spread / 2 + spread * index / (len(run_rows) - 1)

            _, y = project(
                point["value"],
                run["best_distance"],
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
                f'<circle cx="{x + jitter:.2f}" cy="{y:.2f}" r="3.2" '
                f'fill="{color}" opacity="0.68"/>'
            )

        parts.append(
            f'<line x1="{x - 18:.2f}" y1="{average_y:.2f}" '
            f'x2="{x + 18:.2f}" y2="{average_y:.2f}" '
            f'stroke="#111827" stroke-width="2.1"/>'
        )
        parts.append(
            f'<polygon points="{average_marker_points(x, average_y)}" '
            f'fill="#111827"/>'
        )
        if point is best_point:
            parts.append(
                f'<circle cx="{x:.2f}" cy="{average_y:.2f}" r="9" '
                f'fill="none" stroke="#111827" stroke-width="1.6"/>'
            )

        parts.append(
            f'<text x="{x:.2f}" y="{average_y - 15:.2f}" font-family="Arial" '
            f'font-size="11" fill="#111827" text-anchor="middle">'
            f'avg {nice_number(point["average_best_distance"])}</text>'
        )

    parts.extend([
        f'<text x="{left + chart_width / 2:.2f}" y="{height - 32}" '
        f'font-family="Arial" font-size="12" fill="#4b5563" '
        f'text-anchor="middle">Tested value</text>',
        f'<text x="20" y="{top + chart_height / 2:.2f}" '
        f'font-family="Arial" font-size="12" fill="#4b5563" '
        f'text-anchor="middle" transform="rotate(-90 20 '
        f'{top + chart_height / 2:.2f})">Best distance</text>',
        "</svg>",
    ])

    output_path.write_text("\n".join(parts), encoding="utf-8")


def write_svgs(summaries, output_dir):
    output_paths = []

    for parameter in sorted(summaries):
        output_path = output_dir / f"parameter_sweep_{parameter}.svg"
        write_parameter_svg(parameter, summaries[parameter], output_path)
        output_paths.append(output_path)

    return output_paths


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/parameter_sweep_detail.csv")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Rapor")
    rows = read_rows(input_path)
    summaries = summarize(rows)
    output_dir.mkdir(parents=True, exist_ok=True)

    for output_path in write_svgs(summaries, output_dir):
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
