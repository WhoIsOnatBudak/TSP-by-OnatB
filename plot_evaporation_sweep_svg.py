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


def write_schedule_svg(
    schedule,
    configs,
    all_configs,
    metric,
    output_path,
    page_index,
    total_pages,
    max_columns=5,
    height=980,
    output_height_scale=1.0,
    highlight_best=False,
):
    width = 1280
    output_height = height * output_height_scale
    left = 158
    right = 54
    top = 136
    chart_width = width - left - right
    x_axis_label_y = height - 178
    legend_y = height - 128
    y_min, y_max = y_bounds(all_configs, metric)
    metric_label = METRIC_LABELS.get(metric, metric)
    best_config = min(all_configs, key=lambda config: config["average"])
    row_count = math.ceil(len(configs) / max_columns)
    row_slot_height = (x_axis_label_y - top) / row_count
    chart_height = row_slot_height - 70
    page_suffix = ""

    if page_index is not None and total_pages is not None and total_pages > 1:
        page_suffix = f" ({page_index + 1}/{total_pages})"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{output_height:.2f}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="48" y="84" font-family="Arial" font-size="52" '
        f'font-weight="700" fill="#111827">Evaporation Sweep - '
        f'{html.escape(schedule.title())}{page_suffix}</text>',
    ]

    for row_index in range(row_count):
        row_configs = configs[
            row_index * max_columns:(row_index + 1) * max_columns
        ]
        row_top = top + row_index * row_slot_height
        row_bottom = row_top + chart_height

        for tick in range(6):
            ratio = tick / 5
            value = y_min + ratio * (y_max - y_min)
            y = row_top + chart_height - ratio * chart_height
            parts.append(
                f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_width}" '
                f'y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1.4"/>'
            )
            parts.append(
                f'<text x="{left - 18}" y="{y + 10:.2f}" font-family="Arial" '
                f'font-size="28" fill="#4b5563" text-anchor="end">'
                f'{nice_number(value, metric)}</text>'
            )

        parts.append(
            f'<line x1="{left}" y1="{row_bottom:.2f}" '
            f'x2="{left + chart_width}" y2="{row_bottom:.2f}" '
            f'stroke="#9ca3af" stroke-width="1.5"/>'
        )
        parts.append(
            f'<line x1="{left}" y1="{row_top:.2f}" x2="{left}" '
            f'y2="{row_bottom:.2f}" stroke="#9ca3af" stroke-width="1.5"/>'
        )

        for config_index, config in enumerate(row_configs):
            x = left + (config_index + 0.5) * chart_width / len(row_configs)
            label = config_label(config)
            color = BOUND_COLORS.get(bound_label(config), "#475569")
            rows = config["rows"]
            spread = 58.0
            parts.append(
                f'<line x1="{x:.2f}" y1="{row_top:.2f}" x2="{x:.2f}" '
                f'y2="{row_bottom:.2f}" stroke="#f3f4f6" stroke-width="1.2"/>'
            )

            for run_index, row in enumerate(rows):
                if len(rows) == 1:
                    jitter = 0.0
                else:
                    jitter = -spread / 2 + spread * run_index / (len(rows) - 1)

                y = project_y(row[metric], y_min, y_max, row_top, chart_height)
                parts.append(
                    f'<circle cx="{x + jitter:.2f}" cy="{y:.2f}" r="5.8" '
                    f'fill="{color}" opacity="0.70"/>'
                )

            average_y = project_y(
                config["average"],
                y_min,
                y_max,
                row_top,
                chart_height,
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
            if highlight_best and config is best_config:
                parts.append(
                    f'<circle cx="{x:.2f}" cy="{average_y:.2f}" r="18" '
                    f'fill="none" stroke="#111827" stroke-width="2.8"/>'
                )
            parts.append(
                f'<text x="{x:.2f}" y="{average_y - 30:.2f}" '
                f'font-family="Arial" font-size="22" fill="#111827" '
                f'text-anchor="middle">avg '
                f'{nice_number(config["average"], metric)}</text>'
            )
            parts.append(
                f'<text x="{x:.2f}" y="{row_bottom + 44:.2f}" '
                f'font-family="Arial" font-size="26" fill="#374151" '
                f'text-anchor="middle">{html.escape(label)}</text>'
            )

    parts.extend([
        f'<text x="{left + chart_width / 2:.2f}" y="{x_axis_label_y}" '
        f'font-family="Arial" font-size="32" fill="#4b5563" '
        f'text-anchor="middle">Configuration</text>',
        f'<text x="42" y="{(top + x_axis_label_y) / 2:.2f}" '
        f'font-family="Arial" font-size="32" fill="#4b5563" '
        f'text-anchor="middle" transform="rotate(-90 42 '
        f'{(top + x_axis_label_y) / 2:.2f})">{html.escape(metric_label)}</text>',
        f'<circle cx="{left + 14}" cy="{legend_y}" r="10" '
        f'fill="#2563eb" opacity="0.70"/>',
        f'<text x="{left + 46}" y="{legend_y + 10}" font-family="Arial" '
        f'font-size="30" fill="#374151">Colored dots: individual test runs</text>',
        f'<line x1="{left}" y1="{legend_y + 68}" '
        f'x2="{left + 58}" y2="{legend_y + 68}" '
        f'stroke="#111827" stroke-width="3.8"/>',
        f'<polygon points="{average_marker_points(left + 29, legend_y + 68, 12)}" '
        f'fill="#111827"/>',
        f'<text x="{left + 84}" y="{legend_y + 78}" '
        f'font-family="Arial" font-size="30" fill="#374151">'
        f'Black marker: configuration average</text>',
        "</svg>",
    ])

    output_path.write_text("\n".join(parts), encoding="utf-8")


def full_svg_height(config_count, max_columns):
    top = 136
    footer_height = 178
    row_slot_height = 333
    row_count = math.ceil(config_count / max_columns)
    return max(980, int(top + row_count * row_slot_height + footer_height))


def write_svgs(rows, output_dir, metric):
    schedules = sorted({row["schedule"] for row in rows})
    output_paths = []
    configs_per_page = 10
    full_columns = 6

    for schedule in schedules:
        schedule_rows = [
            row for row in rows
            if row["schedule"] == schedule
        ]
        configs = group_configs(schedule_rows, metric)
        pages = [
            configs[index:index + configs_per_page]
            for index in range(0, len(configs), configs_per_page)
        ]

        for page_index, page_configs in enumerate(pages):
            if page_index == 0:
                output_path = output_dir / f"evaporation_sweep_{schedule}_{metric}.svg"
            else:
                output_path = (
                    output_dir
                    / f"evaporation_sweep_{schedule}_{metric}_part{page_index + 1:02d}.svg"
                )

            write_schedule_svg(
                schedule,
                page_configs,
                configs,
                metric,
                output_path,
                page_index,
                len(pages),
            )
            output_paths.append(output_path)

        full_output_path = (
            output_dir / f"evaporation_sweep_{schedule}_{metric}_full.svg"
        )
        write_schedule_svg(
            schedule,
            configs,
            configs,
            metric,
            full_output_path,
            None,
            None,
            max_columns=full_columns,
            height=full_svg_height(len(configs), full_columns),
            output_height_scale=0.81,
            highlight_best=True,
        )
        output_paths.append(full_output_path)

    return output_paths


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/sweep/evaporation_sweep_detail.csv")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Rapor/ImagesCSV")
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
