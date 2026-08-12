#!/usr/bin/env python3
"""Calculate sequence-level BD-rate and BD-PSNR from anchor/proposed VTM logs."""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path


SUMMARY_RE = re.compile(
    r"^\s*(?P<frames>\d+)\s+a\s+"
    r"(?P<bitrate>[0-9.]+)\s+(?P<y>[0-9.]+)\s+"
    r"(?P<u>[0-9.]+)\s+(?P<v>[0-9.]+)\s+(?P<yuv>[0-9.]+)",
    re.MULTILINE,
)
NAME_RE = re.compile(r"(?P<sequence>.+)_QP(?P<qp>22|27|32|37)_(?P<kind>anchor|cdsatm)\.log$")


def solve(matrix: list[list[float]], values: list[float]) -> list[float]:
    size = len(values)
    augmented = [row[:] + [values[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-15:
            raise ValueError("singular polynomial fit")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                augmented[row][index] - factor * augmented[column][index]
                for index in range(size + 1)
            ]
    return [augmented[row][-1] for row in range(size)]


def polynomial_coefficients(x_values: list[float], y_values: list[float]) -> list[float]:
    if len(x_values) != 4 or len(y_values) != 4:
        raise ValueError("exactly four RD points are required")
    matrix = [[x ** power for power in range(4)] for x in x_values]
    return solve(matrix, y_values)


def integral(coefficients: list[float], lower: float, upper: float) -> float:
    return sum(
        coefficient * (upper ** (power + 1) - lower ** (power + 1)) / (power + 1)
        for power, coefficient in enumerate(coefficients)
    )


def bd_rate(anchor: list[tuple[float, float]], proposed: list[tuple[float, float]]) -> float:
    anchor_rate = [math.log(point[0]) for point in anchor]
    anchor_psnr = [point[1] for point in anchor]
    proposed_rate = [math.log(point[0]) for point in proposed]
    proposed_psnr = [point[1] for point in proposed]
    lower = max(min(anchor_psnr), min(proposed_psnr))
    upper = min(max(anchor_psnr), max(proposed_psnr))
    if upper <= lower:
        raise ValueError("anchor and proposed PSNR ranges do not overlap")
    anchor_fit = polynomial_coefficients(anchor_psnr, anchor_rate)
    proposed_fit = polynomial_coefficients(proposed_psnr, proposed_rate)
    average_difference = (
        integral(proposed_fit, lower, upper) - integral(anchor_fit, lower, upper)
    ) / (upper - lower)
    return 100.0 * (math.exp(average_difference) - 1.0)


def bd_psnr(anchor: list[tuple[float, float]], proposed: list[tuple[float, float]]) -> float:
    anchor_log_rate = [math.log(point[0]) for point in anchor]
    anchor_psnr = [point[1] for point in anchor]
    proposed_log_rate = [math.log(point[0]) for point in proposed]
    proposed_psnr = [point[1] for point in proposed]
    lower = max(min(anchor_log_rate), min(proposed_log_rate))
    upper = min(max(anchor_log_rate), max(proposed_log_rate))
    if upper <= lower:
        raise ValueError("anchor and proposed bitrate ranges do not overlap")
    anchor_fit = polynomial_coefficients(anchor_log_rate, anchor_psnr)
    proposed_fit = polynomial_coefficients(proposed_log_rate, proposed_psnr)
    return (
        integral(proposed_fit, lower, upper) - integral(anchor_fit, lower, upper)
    ) / (upper - lower)


def parse_log(path: Path) -> tuple[int, float, float]:
    match = SUMMARY_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        raise ValueError(f"VTM summary row not found in {path}")
    return int(match["frames"]), float(match["bitrate"]), float(match["y"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    grouped: dict[str, dict[int, dict[str, tuple[int, float, float]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for path in args.results.rglob("*.log"):
        match = NAME_RE.match(path.name)
        if not match:
            continue
        grouped[match["sequence"]][int(match["qp"])][match["kind"]] = parse_log(path)

    if not grouped:
        raise SystemExit(f"No anchor/proposed VTM logs found under {args.results}")

    rows: list[dict[str, str]] = []
    for sequence, qp_records in sorted(grouped.items()):
        if set(qp_records) != {22, 27, 32, 37}:
            raise SystemExit(f"{sequence} does not contain all four QPs")
        anchor: list[tuple[float, float]] = []
        proposed: list[tuple[float, float]] = []
        max_rate_delta = 0.0
        max_psnr_delta = 0.0
        for qp in (22, 27, 32, 37):
            if set(qp_records[qp]) != {"anchor", "cdsatm"}:
                raise SystemExit(f"{sequence} QP{qp} lacks an anchor/proposed pair")
            anchor_frames, anchor_rate, anchor_psnr = qp_records[qp]["anchor"]
            proposed_frames, proposed_rate, proposed_psnr = qp_records[qp]["cdsatm"]
            if anchor_frames != proposed_frames:
                raise SystemExit(f"{sequence} QP{qp} frame counts differ")
            anchor.append((anchor_rate, anchor_psnr))
            proposed.append((proposed_rate, proposed_psnr))
            max_rate_delta = max(max_rate_delta, abs(proposed_rate - anchor_rate))
            max_psnr_delta = max(max_psnr_delta, abs(proposed_psnr - anchor_psnr))

        rate_result = bd_rate(anchor, proposed)
        psnr_result = bd_psnr(anchor, proposed)
        rows.append(
            {
                "sequence": sequence,
                "bd_rate_percent": f"{rate_result:.9f}",
                "bd_psnr_db": f"{psnr_result:.9f}",
                "max_bitrate_delta": f"{max_rate_delta:.9f}",
                "max_y_psnr_delta_db": f"{max_psnr_delta:.9f}",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(
            f"{row['sequence']}: BD-rate={row['bd_rate_percent']}%  "
            f"BD-PSNR={row['bd_psnr_db']} dB  "
            f"max bitrate delta={row['max_bitrate_delta']}  "
            f"max Y-PSNR delta={row['max_y_psnr_delta_db']} dB"
        )

    if any(
        float(row["max_bitrate_delta"]) != 0.0
        or float(row["max_y_psnr_delta_db"]) != 0.0
        for row in rows
    ):
        raise SystemExit("Anchor and proposed RD points are not identical")


if __name__ == "__main__":
    main()
