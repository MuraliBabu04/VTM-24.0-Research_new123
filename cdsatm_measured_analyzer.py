#!/usr/bin/env python3
"""Summarize measured CD-SATM horizontal-transform column activity."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


COUNTER_FIELDS = (
    "blocks",
    "total_columns",
    "zero_columns",
    "active_columns",
    "baseline_reads",
    "cdsatm_reads",
    "baseline_cycles",
    "cdsatm_cycles",
)


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"No measured transform records found in {path}")
    for row in rows:
        for field in COUNTER_FIELDS:
            row[field] = int(row[field])
        row["width"] = int(row["width"])
        row["height"] = int(row["height"])
    return rows


def aggregate(rows):
    result = {field: 0 for field in COUNTER_FIELDS}
    for row in rows:
        for field in COUNTER_FIELDS:
            result[field] += row[field]
    return result


def percent(saved, baseline):
    return 0.0 if baseline == 0 else 100.0 * saved / baseline


def print_metrics(label, values):
    sparsity = percent(values["zero_columns"], values["total_columns"])
    read_reduction = percent(
        values["baseline_reads"] - values["cdsatm_reads"], values["baseline_reads"]
    )
    cycle_reduction = percent(
        values["baseline_cycles"] - values["cdsatm_cycles"], values["baseline_cycles"]
    )
    print(
        f"{label:<12} blocks={values['blocks']:>10,d}  "
        f"zero_cols={values['zero_columns']:>12,d}/{values['total_columns']:<12,d}  "
        f"sparsity={sparsity:7.3f}%  read_reduction={read_reduction:7.3f}%  "
        f"cycle_reduction={cycle_reduction:7.3f}%"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--seq", required=True)
    parser.add_argument("--qp", required=True, type=int)
    parser.add_argument("--frames", required=True, type=int)
    args = parser.parse_args()

    rows = load_rows(args.csv)
    overall = aggregate(rows)
    by_size = defaultdict(list)
    for row in rows:
        by_size[(row["width"], row["height"])].append(row)

    print("\n================ CD-SATM MEASURED SPARSITY ================")
    print(f"Sequence: {args.seq} | QP: {args.qp} | Frames: {args.frames}")
    print("Measurement point: after horizontal transform, before vertical transform")
    print("Scope: executed primary 2-D transform calls, including encoder RDO candidates")
    print_metrics("OVERALL", overall)
    print("\nPer transform size:")
    for (width, height), size_rows in sorted(by_size.items()):
        print_metrics(f"{width}x{height}", aggregate(size_rows))

    print("\nExact workload counters:")
    print(f"Baseline coefficient reads : {overall['baseline_reads']:,}")
    print(f"CD-SATM coefficient reads  : {overall['cdsatm_reads']:,}")
    print(f"Baseline transform cycles  : {overall['baseline_cycles']:,}")
    print(f"CD-SATM transform cycles   : {overall['cdsatm_cycles']:,}")
    print("Power note: no power value is claimed; exact power requires RTL VCD/SAIF analysis.")
    print("============================================================")


if __name__ == "__main__":
    main()
