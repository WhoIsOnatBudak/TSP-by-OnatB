#!/usr/bin/env python3

import csv
import html
import math
import sys
from collections import defaultdict
from pathlib import Path


BOUND_COLORS = {
    "0.9->0.2": "#2563eb",
    "0.8->0.2": "#16a34a",
    "0.8->0.3": "#dc2626",
    "0.7->0.3": "#9333ea",
    "0.7->0.4": "#d97706",
    "0.6->0.2": "#0891b2",
}

METRIC_LABELS = {
    "best_distance": "Best Distance",
    "blind_rounds": "Blind Rounds",
    "final_pheromone_min": "Final Pheromone Min",
    "final_pheromone_max": "Final Pheromone Max",
    "final_pheromone_mean": "Final Pheromone Mean",
}


def read_rows(path):
    rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append({
                "schedule": row["schedule"],
                "start_evaporation": float(row["start_evaporation"]),
                "end_evaporation": float(row["end_evaporation"]),
                "curve": float(row["curve"]),
                "seed_index": int(row["seed_index"]),
                "best_distance": float(row["best_distance"]),
                "blind_rounds": float(row["blind_rounds"]),
                "final_pheromone_min": float(row["final_pheromone_min"]),
                "final_pheromone_max": float(row["final_pheromone_max"]),
                "final_pheromone_mean": float(row["final_pheromone_mean"]),
            })

    if not rows:
        raise ValueError(f"No rows found in {path}")

    return rows


def bound_label(config):
    return (
        f"{config['start_evaporation']:.1f}"
        f"->{config['end_evaporation']:.1f}"
    )


def config_label(config):
    label = bound_label(config)

    if config["schedule"] != "linear":
        curve = config["curve"]
        curve_text = f"{curve:.0f}" if curve == round(curve) else f"{curve:g}"
        label = f"{label} c={curve_text}"

    return label


def group_configs(rows, metric):
    grouped = {}

    for row in rows:
        key = (
            row["schedule"],
            row["start_evaporation"],
            row["end_evaporation"],
            row["curve"],
        )
        grouped.setdefault(key, []).append(row)

    configs = []

    for key, values in grouped.items():
        schedule, start, end, curve = key
        average = sum(row[metric] for row in values) / len(values)
        configs.append({
            "schedule": schedule,
            "start_evaporation": start,
            "end_evaporation": end,
            "curve": curve,
            "rows": sorted(values, key=lambda row: row["seed_index"]),
            "average": average,
        })

    configs.sort(key=lambda item: (item["average"], item["start_evaporation"], item["end_evaporation"], item["curve"]))
    return configs


def nice_number(value, metric):
    if metric == "blind_rounds":
        return f"{value:.1f}"

    if "pheromone" in metric:
        return f"{value:.4f}"

    return f"{value:,.0f}"


def y_bounds(configs, metric):
    values = []

    for config in configs:
        values.append(config["average"])
        values.extend(row[metric] for row in config["rows"])

    lower = min(values)
    upper = max(values)

    if math.isclose(lower, upper):
        return lower - 1.0, upper + 1.0

    padding = (upper - lower) * 0.10
    return lower - padding, upper + padding


def project_y(value, y_min, y_max, top, height):
    if math.isclose(y_min, y_max):
        return top + height / 2

    return top + height - (value - y_min) / (y_max - y_min) * height


def average_marker_points(x, y, size=6):
    return " ".join([
        f"{x:.2f},{y - size:.2f}",
        f"{x + size:.2f},{y:.2f}",
        f"{x:.2f},{y + size:.2f}",
        f"{x - size:.2f},{y:.2f}",
    ])


def build_legend(configs, x, y):
    labels = sorted({bound_label(config) for config in configs}, reverse=True)
    parts = []

    parts.append(
        f'<text x="{x}" y="{y - 14}" font-family="Arial" font-size="13" '
        f'font-weight="700" fill="#111827">Evaporation bounds</text>'
    )

    for index, label in enumerate(labels):
        row_y = y + index * 22
        color = BOUND_COLORS.get(label, "#475569")
        parts.append(
            f'<circle cx="{x + 6}" cy="{row_y}" r="5" fill="{color}" opacity="0.82"/>'
        )
        parts.append(
            f'<text x="{x + 20}" y="{row_y + 4}" font-family="Arial" '
            f'font-size="12" fill="#111827">{html.escape(label)}</text>'
        )

    average_y = y + len(labels) * 22 + 12
    parts.append(
        f'<polygon points="{average_marker_points(x + 6, average_y, 5)}" '
        f'fill="#111827"/>'
    )
    parts.append(
        f'<text x="{x + 20}" y="{average_y + 4}" font-family="Arial" '
        f'font-size="12" fill="#111827">average</text>'
    )

    return "\n".join(parts)


def write_schedule_svg(schedule, configs, metric, output_path):
    left = 92
    right = 210
    top = 104
    chart_height = 520
    config_spacing = 56 if len(configs) > 12 else 96
    chart_width = max(760, (len(configs) - 1) * config_spacing)
    width = left + chart_width + right
    height = 760
    y_min, y_max = y_bounds(configs, metric)
    metric_label = METRIC_LABELS.get(metric, metric)
    overall_average = sum(config["average"] for config in configs) / len(configs)
    best_config = min(configs, key=lambda config: config["average"])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="28" y="38" font-family="Arial" font-size="24" '
        f'font-weight="700" fill="#111827">Evaporation Sweep - '
        f'{html.escape(schedule.title())}</text>',
        f'<text x="28" y="63" font-family="Arial" font-size="13" fill="#4b5563">'
        f'{html.escape(metric_label)} scatter. Dots are seed runs; black diamonds '
        f'and labels are configuration averages. Sorted by average; lower is better.'
        f'</text>',
        f'<text x="28" y="84" font-family="Arial" font-size="13" fill="#111827">'
        f'Overall average: {nice_number(overall_average, metric)} | Best average: '
        f'{html.escape(config_label(best_config))} = '
        f'{nice_number(best_config["average"], metric)}</text>',
        build_legend(configs, width - right + 38, 128),
    ]

    for tick in range(7):
        ratio = tick / 6
        value = y_min + ratio * (y_max - y_min)
        y = top + chart_height - ratio * chart_height
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_width}" '
            f'y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" font-family="Arial" '
            f'font-size="11" fill="#4b5563" text-anchor="end">'
            f'{nice_number(value, metric)}</text>'
        )

    parts.append(
        f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" '
        f'y2="{top + chart_height}" stroke="#9ca3af"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" '
        f'stroke="#9ca3af"/>'
    )

    for index, config in enumerate(configs):
        x = left + index * config_spacing
        label = config_label(config)
        color = BOUND_COLORS.get(bound_label(config), "#475569")
        rows = config["rows"]
        spread = 23.0

        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + chart_height}" stroke="#f8fafc" stroke-width="1"/>'
        )

        for row_index, row in enumerate(rows):
            if len(rows) == 1:
                jitter = 0.0
            else:
                jitter = -spread / 2 + spread * row_index / (len(rows) - 1)

            y = project_y(row[metric], y_min, y_max, top, chart_height)
            parts.append(
                f'<circle cx="{x + jitter:.2f}" cy="{y:.2f}" r="3.5" '
                f'fill="{color}" opacity="0.70"/>'
            )

        average_y = project_y(config["average"], y_min, y_max, top, chart_height)
        parts.append(
            f'<line x1="{x - 18:.2f}" y1="{average_y:.2f}" '
            f'x2="{x + 18:.2f}" y2="{average_y:.2f}" '
            f'stroke="#111827" stroke-width="2.3"/>'
        )
        parts.append(
            f'<polygon points="{average_marker_points(x, average_y)}" '
            f'fill="#111827"/>'
        )
        parts.append(
            f'<text x="{x + 8:.2f}" y="{average_y - 10:.2f}" '
            f'font-family="Arial" font-size="10" fill="#111827" '
            f'transform="rotate(-55 {x + 8:.2f} {average_y - 10:.2f})">'
            f'avg {nice_number(config["average"], metric)}</text>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{top + chart_height + 34}" '
            f'font-family="Arial" font-size="10.5" fill="#374151" '
            f'text-anchor="end" transform="rotate(-58 {x:.2f} '
            f'{top + chart_height + 34})">{html.escape(label)}</text>'
        )

    parts.extend([
        f'<text x="{left + chart_width / 2:.2f}" y="{height - 32}" '
        f'font-family="Arial" font-size="12" fill="#4b5563" '
        f'text-anchor="middle">Configuration</text>',
        f'<text x="20" y="{top + chart_height / 2:.2f}" '
        f'font-family="Arial" font-size="12" fill="#4b5563" '
        f'text-anchor="middle" transform="rotate(-90 20 '
        f'{top + chart_height / 2:.2f})">{html.escape(metric_label)}</text>',
        "</svg>",
    ])

    output_path.write_text("\n".join(parts), encoding="utf-8")


def write_svgs(rows, output_dir, metric):
    schedules = sorted({row["schedule"] for row in rows})
    output_paths = []

    for schedule in schedules:
        schedule_rows = [
            row for row in rows
            if row["schedule"] == schedule
        ]
        configs = group_configs(schedule_rows, metric)
        output_path = output_dir / f"evaporation_sweep_{schedule}_{metric}.svg"
        write_schedule_svg(schedule, configs, metric, output_path)
        output_paths.append(output_path)

    return output_paths


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/evaporation_sweep_detail.csv")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Rapor")
    metric = sys.argv[3] if len(sys.argv) > 3 else "best_distance"

    if metric not in METRIC_LABELS:
        metrics = ", ".join(sorted(METRIC_LABELS))
        raise ValueError(f"Unknown metric '{metric}'. Available metrics: {metrics}")

    rows = read_rows(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = write_svgs(rows, output_dir, metric)

    for output_path in output_paths:
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
