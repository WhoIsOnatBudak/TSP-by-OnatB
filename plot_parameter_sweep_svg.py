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
    width = 1280
    height = 980
    left = 158
    right = 54
    top = 136
    bottom = 280
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
        f'<text x="48" y="84" font-family="Arial" font-size="52" '
        f'font-weight="700" fill="#111827">{html.escape(title)}</text>',
    ]

    for index in range(6):
        ratio = index / 5
        y = top + chart_height - ratio * chart_height
        value = y_min + ratio * (y_max - y_min)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_width}" '
            f'y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{left - 18}" y="{y + 10:.2f}" font-family="Arial" '
            f'font-size="28" fill="#4b5563" text-anchor="end">'
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
            f'y2="{top + chart_height}" stroke="#f3f4f6" stroke-width="1.2"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{top + chart_height + 44}" '
            f'font-family="Arial" font-size="28" fill="#374151" '
            f'text-anchor="middle">{html.escape(nice_value(point["value"]))}</text>'
        )

    parts.append(
        f'<line x1="{left}" y1="{top + chart_height}" '
        f'x2="{left + chart_width}" y2="{top + chart_height}" '
        f'stroke="#9ca3af" stroke-width="1.5"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" '
        f'y2="{top + chart_height}" stroke="#9ca3af" stroke-width="1.5"/>'
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
        f'<polyline fill="none" stroke="#111827" stroke-width="2.5" '
        f'opacity="0.60" stroke-dasharray="8 8" '
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
        spread = 58.0
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
                f'<circle cx="{x + jitter:.2f}" cy="{y:.2f}" r="5.8" '
                f'fill="{color}" opacity="0.68"/>'
            )

        parts.append(
            f'<line x1="{x - 28:.2f}" y1="{average_y:.2f}" '
            f'x2="{x + 28:.2f}" y2="{average_y:.2f}" '
            f'stroke="#111827" stroke-width="3.6"/>'
        )
        parts.append(
            f'<polygon points="{average_marker_points(x, average_y, 12)}" '
            f'fill="#111827"/>'
        )
        if point is best_point:
            parts.append(
                f'<circle cx="{x:.2f}" cy="{average_y:.2f}" r="18" '
                f'fill="none" stroke="#111827" stroke-width="2.8"/>'
            )

        parts.append(
            f'<text x="{x:.2f}" y="{average_y - 30:.2f}" font-family="Arial" '
            f'font-size="22" fill="#111827" text-anchor="middle">'
            f'avg {nice_number(point["average_best_distance"])}</text>'
        )

    legend_y = height - 128
    parts.extend([
        f'<circle cx="{left + 14}" cy="{legend_y}" r="10" '
        f'fill="{color}" opacity="0.68"/>',
        f'<text x="{left + 46}" y="{legend_y + 10}" font-family="Arial" '
        f'font-size="30" fill="#374151">Colored dots: individual test runs '
        f'({points[0]["runs"]} runs per value)</text>',
        f'<line x1="{left}" y1="{legend_y + 68}" '
        f'x2="{left + 58}" y2="{legend_y + 68}" '
        f'stroke="#111827" stroke-width="3.8"/>',
        f'<polygon points="{average_marker_points(left + 29, legend_y + 68, 12)}" '
        f'fill="#111827"/>',
        f'<text x="{left + 84}" y="{legend_y + 78}" '
        f'font-family="Arial" font-size="30" fill="#374151">'
        f'Black marker: average for tested value</text>',
    ])

    parts.extend([
        f'<text x="{left + chart_width / 2:.2f}" y="{top + chart_height + 96}" '
        f'font-family="Arial" font-size="32" fill="#4b5563" '
        f'text-anchor="middle">Tested value</text>',
        f'<text x="42" y="{top + chart_height / 2:.2f}" '
        f'font-family="Arial" font-size="32" fill="#4b5563" '
        f'text-anchor="middle" transform="rotate(-90 42 '
        f'{top + chart_height / 2:.2f})">Best distance</text>',
        "</svg>",
    ])

    output_path.write_text("\n".join(parts), encoding="utf-8")


def write_svgs(summaries, output_dir, selected_parameter):
    output_paths = []

    parameters = sorted(summaries)

    if selected_parameter != "all":
        if selected_parameter not in summaries:
            available = ", ".join(parameters)
            raise ValueError(
                f"Parameter '{selected_parameter}' not found. "
                f"Available parameters: {available}"
            )

        parameters = [selected_parameter]

    for parameter in parameters:
        output_path = output_dir / f"parameter_sweep_{parameter}.svg"
        write_parameter_svg(parameter, summaries[parameter], output_path)
        output_paths.append(output_path)

    return output_paths


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/sweep/parameter_sweep_detail.csv")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Rapor/ImagesCSV")
    selected_parameter = sys.argv[3] if len(sys.argv) > 3 else "all"
    rows = read_rows(input_path)
    summaries = summarize(rows)
    output_dir.mkdir(parents=True, exist_ok=True)

    for output_path in write_svgs(summaries, output_dir, selected_parameter):
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
