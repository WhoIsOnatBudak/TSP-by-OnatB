#!/usr/bin/env python3

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path


METRICS = ("best_distance", "distance_per_city")

T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
    40: 2.021,
    50: 2.009,
    60: 2.000,
    80: 1.990,
    100: 1.984,
    120: 1.980,
}


def display_algorithm_name(algorithm):
    if algorithm.endswith("AS"):
        return f"{algorithm[:-2]}ACO"

    return algorithm


def t_critical_95(df):
    if df <= 0:
        return 0.0

    if df in T_CRITICAL_95:
        return T_CRITICAL_95[df]

    known_dfs = sorted(T_CRITICAL_95)

    if df > known_dfs[-1]:
        return 1.960

    for known_df in known_dfs:
        if df < known_df:
            return T_CRITICAL_95[known_df]

    return 1.960


def read_detail_rows(path):
    rows = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append(row)

    if not rows:
        raise ValueError(f"No rows found in {path}")

    return rows


def sample_stddev(values, mean):
    if len(values) < 2:
        return 0.0

    variance = sum((value - mean) ** 2 for value in values)
    variance /= len(values) - 1
    return math.sqrt(variance)


def summarize_values(values):
    n = len(values)
    mean = sum(values) / n
    stddev = sample_stddev(values, mean)
    standard_error = stddev / math.sqrt(n) if n > 0 else 0.0
    t_value = t_critical_95(n - 1)
    ci_half_width = t_value * standard_error

    return {
        "runs": n,
        "mean": mean,
        "stddev": stddev,
        "standard_error": standard_error,
        "confidence_level": 0.95,
        "t_value": t_value,
        "ci_half_width": ci_half_width,
        "ci_lower": mean - ci_half_width,
        "ci_upper": mean + ci_half_width,
        "best": min(values),
        "worst": max(values),
    }


def summarize_file(path):
    rows = read_detail_rows(path)
    grouped = defaultdict(list)

    for row in rows:
        algorithm = row["algorithm"]

        for metric in METRICS:
            if metric in row and row[metric] != "":
                grouped[(algorithm, metric)].append(float(row[metric]))

    summaries = []

    for (algorithm, metric), values in sorted(grouped.items()):
        summary = summarize_values(values)
        summary.update({
            "source_file": path.name,
            "algorithm": algorithm,
            "display_algorithm": display_algorithm_name(algorithm),
            "metric": metric,
        })
        summaries.append(summary)

    return summaries


def write_csv(rows, output_path):
    fieldnames = [
        "source_file",
        "algorithm",
        "display_algorithm",
        "metric",
        "runs",
        "mean",
        "stddev",
        "standard_error",
        "confidence_level",
        "t_value",
        "ci_half_width",
        "ci_lower",
        "ci_upper",
        "best",
        "worst",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            formatted = row.copy()

            for key in fieldnames:
                if isinstance(formatted.get(key), float):
                    formatted[key] = f"{formatted[key]:.8f}"

            writer.writerow(formatted)


def write_markdown(rows, output_path):
    best_distance_rows = [
        row for row in rows
        if row["metric"] == "best_distance"
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as file:
        file.write("# 95% Confidence Intervals\n\n")
        file.write(
            "Values are computed from the detail CSV files using "
            "`mean ± t * std / sqrt(n)`.\n\n"
        )
        current_file = None

        for row in best_distance_rows:
            if row["source_file"] != current_file:
                current_file = row["source_file"]
                file.write(f"\n## {current_file}\n\n")
                file.write("| Algorithm | Runs | Mean Tour Length | 95% CI |\n")
                file.write("| --- | ---: | ---: | ---: |\n")

            file.write(
                f"| {row['display_algorithm']} | {row['runs']} | "
                f"{row['mean']:.2f} | "
                f"[{row['ci_lower']:.2f}, {row['ci_upper']:.2f}] |\n"
            )


def main():
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor")
    output_csv = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else Path("Rapor/confidence_intervals.csv")
    )
    output_md = output_csv.with_suffix(".md")
    detail_paths = sorted(input_dir.glob("detail*.csv"))

    if not detail_paths:
        raise ValueError(f"No detail*.csv files found in {input_dir}")

    all_summaries = []

    for path in detail_paths:
        all_summaries.extend(summarize_file(path))

    write_csv(all_summaries, output_csv)
    write_markdown(all_summaries, output_md)
    print(f"Wrote {output_csv}")
    print(f"Wrote {output_md}")


if __name__ == "__main__":
    main()
