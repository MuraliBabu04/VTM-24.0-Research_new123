#!/usr/bin/env python3
"""Generate deterministic scale-calibrated asymmetric NMF factors for VTM."""

from __future__ import annotations

import argparse
import json
import math
import warnings
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning

from nmf_rank_sweep import TRANSFORMS, factor_part, load_vtm_kernel


# Complexity-constrained choices from the positive/negative allocation sweep.
# Each total rank satisfies 2 * (r_pos + r_neg) < N, so the two-stage
# factorization retains a positive dense-multiplication saving.
SELECTED_RANKS = {
    "DCT8": {8: (1, 2), 16: (4, 3), 32: (8, 6)},
    "DST7": {8: (2, 1), 16: (3, 4), 32: (7, 7)},
}


def quantize(values: np.ndarray, fractional_bits: int) -> np.ndarray:
    scale = float(1 << fractional_bits)
    return np.rint(values * scale) / scale


def calibrate_rows(
    matrix: np.ndarray,
    wp: np.ndarray,
    hp: np.ndarray,
    wn: np.ndarray,
    hn: np.ndarray,
    fractional_bits: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply the non-negative least-squares gain that minimizes each row error."""
    approximation = wp @ hp - wn @ hn
    denominator = np.sum(approximation * approximation, axis=1)
    gains = np.divide(
        np.sum(matrix * approximation, axis=1),
        denominator,
        out=np.ones_like(denominator),
        where=denominator > 0,
    )
    gains = np.maximum(gains, 0.0)
    wp = quantize(wp * gains[:, None], fractional_bits)
    wn = quantize(wn * gains[:, None], fractional_bits)
    return wp, wn, gains


def c_array(name: str, values: np.ndarray) -> str:
    rows = []
    for row in values.astype(np.int64):
        rows.append("  { " + ", ".join(str(int(value)) for value in row) + " }")
    return (
        f"static constexpr int32_t {name}[{values.shape[0]}][{values.shape[1]}] = {{\n"
        + ",\n".join(rows)
        + "\n};\n"
    )


def main() -> None:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=Path("source/Lib/CommonLib/RomTr.cpp"))
    parser.add_argument("--header", type=Path, default=Path("source/Lib/CommonLib/NmfMtsFactors.h"))
    parser.add_argument("--metadata", type=Path, default=Path("nmf_results/selected_factors.json"))
    parser.add_argument("--fractional-bits", type=int, default=8)
    parser.add_argument("--forward-matrix-scale-bits", type=int, default=8)
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--max-iter", type=int, default=4000)
    args = parser.parse_args()

    scale = 1 << args.fractional_bits
    declarations = []
    rank_constants = []
    records = []

    for transform in TRANSFORMS:
        for size, (rank_positive, rank_negative) in SELECTED_RANKS[transform].items():
            matrix = load_vtm_kernel(args.rom, transform, size)
            positive = np.maximum(matrix, 0.0)
            negative = np.maximum(-matrix, 0.0)
            wp, hp, positive_error = factor_part(
                positive, rank_positive, args.fractional_bits, args.seeds, args.max_iter
            )
            wn, hn, negative_error = factor_part(
                negative, rank_negative, args.fractional_bits, args.seeds, args.max_iter
            )

            before_calibration = wp @ hp - wn @ hn
            wp, wn, row_gains = calibrate_rows(
                matrix, wp, hp, wn, hn, args.fractional_bits
            )
            approximation = wp @ hp - wn @ hn

            prefix = f"g_nmf{transform}P{size}"
            tag = f"NMF_{transform}_P{size}"
            rank_constants.extend(
                [
                    f"static constexpr int {tag}_POS_RANK = {rank_positive};",
                    f"static constexpr int {tag}_NEG_RANK = {rank_negative};",
                ]
            )
            factors = {
                "PosW": np.rint(wp * scale),
                "PosH": np.rint(hp * scale),
                "NegW": np.rint(wn * scale),
                "NegH": np.rint(hn * scale),
            }
            for suffix, values in factors.items():
                declarations.append(c_array(prefix + suffix, values))

            matrix_norm = float(np.linalg.norm(matrix, "fro"))
            delta = approximation - matrix
            total_rank = rank_positive + rank_negative
            records.append(
                {
                    "transform": transform,
                    "size": size,
                    "rank_positive": rank_positive,
                    "rank_negative": rank_negative,
                    "total_rank": total_rank,
                    "factor_fractional_bits": args.fractional_bits,
                    "forward_matrix_scale_bits": args.forward_matrix_scale_bits,
                    "multiplication_reduction_percent": 100.0 * (1.0 - 2.0 * total_rank / size),
                    "relative_frobenius_error_before_row_calibration": float(
                        np.linalg.norm(before_calibration - matrix, "fro") / matrix_norm
                    ),
                    "relative_frobenius_error": float(np.linalg.norm(delta, "fro") / matrix_norm),
                    "relative_spectral_error": float(np.linalg.norm(delta, 2) / np.linalg.norm(matrix, 2)),
                    "orthogonality_deviation": float(
                        np.linalg.norm(
                            (approximation / (64.0 * math.sqrt(size))).T
                            @ (approximation / (64.0 * math.sqrt(size)))
                            - np.eye(size),
                            "fro",
                        )
                    ),
                    "max_absolute_matrix_error": float(np.max(np.abs(delta))),
                    "row_gain_min": float(np.min(row_gains)),
                    "row_gain_max": float(np.max(row_gains)),
                    "positive_part_error": positive_error,
                    "negative_part_error": negative_error,
                    "factor_integer_min": int(min(np.min(value) for value in factors.values())),
                    "factor_integer_max": int(max(np.max(value) for value in factors.values())),
                }
            )

    header = f"""// Generated by nmf_experiment/generate_selected_factors.py.
// Scale-calibrated, complexity-constrained asymmetric positive/negative NMF.
#ifndef __NMF_MTS_FACTORS_H__
#define __NMF_MTS_FACTORS_H__

#include <cstdint>

static constexpr int NMF_FACTOR_FRACTIONAL_BITS = {args.fractional_bits};
static constexpr int NMF_FORWARD_MATRIX_SCALE_BITS = {args.forward_matrix_scale_bits};

""" + "\n".join(rank_constants) + "\n\n" + "\n".join(declarations) + "\n#endif // __NMF_MTS_FACTORS_H__\n"

    args.header.parent.mkdir(parents=True, exist_ok=True)
    args.header.write_text(header, encoding="utf-8")
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {args.header}")
    print(f"Wrote {args.metadata}")
    for record in records:
        print(
            f"{record['transform']}-{record['size']} "
            f"r+={record['rank_positive']} r-={record['rank_negative']} "
            f"saving={record['multiplication_reduction_percent']:.1f}% "
            f"relF={record['relative_frobenius_error']:.6f}"
        )


if __name__ == "__main__":
    main()
