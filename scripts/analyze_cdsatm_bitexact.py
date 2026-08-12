#!/usr/bin/env python3
"""Validate CD-SATM zero-skip coefficients against the untouched VTM transform path."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


FIELDS = ("blocks", "coefficients", "mismatches", "max_abs_error")


def load_rows(path: Path) -> list[dict[str, int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))
    if not raw_rows:
        raise SystemExit(f"No CD-SATM verification records found in {path}")

    rows: list[dict[str, int]] = []
    for raw in raw_rows:
        row = {name: int(raw[name]) for name in raw if name is not None and raw[name] is not None}
        rows.append(row)
    return rows


def aggregate(rows: list[dict[str, int]]) -> dict[str, int]:
    result = {field: 0 for field in FIELDS}
    for row in rows:
        result["blocks"] += row["blocks"]
        result["coefficients"] += row["coefficients"]
        result["mismatches"] += row["mismatches"]
        result["max_abs_error"] = max(result["max_abs_error"], row["max_abs_error"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()

    rows = load_rows(args.csv)
    totals = aggregate(rows)
    by_size: dict[tuple[int, int], list[dict[str, int]]] = defaultdict(list)
    for row in rows:
        by_size[(row["width"], row["height"])].append(row)

    print("================ CD-SATM BIT-EXACT VERIFICATION ================")
    print("Reference: untouched VTM vertical transform")
    print("Proposed : packed active columns with inactive lines skipped")
    print(f"Verified transform blocks : {totals['blocks']:,}")
    print(f"Compared coefficients     : {totals['coefficients']:,}")
    print(f"Coefficient mismatches    : {totals['mismatches']:,}")
    print(f"Maximum absolute error    : {totals['max_abs_error']:,}")
    print()
    print("Per transform size:")
    for (width, height), size_rows in sorted(by_size.items()):
        values = aggregate(size_rows)
        print(
            f"{width:>2}x{height:<2}  blocks={values['blocks']:>12,d}  "
            f"coefficients={values['coefficients']:>16,d}  "
            f"mismatches={values['mismatches']:>8,d}  "
            f"max_error={values['max_abs_error']}"
        )
    print("================================================================")

    if totals["mismatches"] != 0 or totals["max_abs_error"] != 0:
        raise SystemExit("CD-SATM zero-skip output is not bit-exact against VTM")


if __name__ == "__main__":
    main()
