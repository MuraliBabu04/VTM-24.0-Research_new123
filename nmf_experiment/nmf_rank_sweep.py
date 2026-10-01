#!/usr/bin/env python3
"""Sweep positive/negative NMF ranks on the exact VTM integer MTS kernels."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import warnings
from pathlib import Path

import numpy as np
from sklearn.decomposition import NMF
from sklearn.exceptions import ConvergenceWarning


TRANSFORMS = ("DCT8", "DST7")
SIZES = (4, 8, 16, 32)


def _extract_macro_body(text: str, name: str) -> tuple[list[str], list[list[str]]]:
    pattern = re.compile(
        rf"#define\s+{name}\(([^)]*)\)\s*\\\n(.*?)"
        rf"(?=\n\n#define|\n// DST-7|\n// -+|\n#if|\nconst TMatrixCoeff)",
        re.S,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Macro {name} not found")
    params = [item.strip() for item in match.group(1).split(",")]
    rows = []
    for row in re.findall(r"\{\s*([^{}]+?)\s*\}", match.group(2)):
        tokens = [item.strip() for item in row.replace("\\", "").split(",") if item.strip()]
        if tokens:
            rows.append(tokens)
    return params, rows


def _extract_integer_arguments(text: str, name: str) -> list[int]:
    # Use the non-high-precision (#else) VTM matrices, whose forward and inverse
    # coefficient sets are identical and use the normative small integers.
    marker = text.find("#else")
    if marker < 0:
        raise ValueError("Expected #else section containing VTM integer kernels")
    tail = text[marker:]
    match = re.search(rf"{name}\s*\(([^)]*)\)", tail, re.S)
    if not match:
        raise ValueError(f"Integer invocation {name} not found")
    return [int(item.strip()) for item in match.group(1).split(",")]


def load_vtm_kernel(rom_path: Path, transform: str, size: int) -> np.ndarray:
    text = rom_path.read_text(encoding="utf-8")
    name = f"DEFINE_{transform}_P{size}_MATRIX"
    params, symbolic_rows = _extract_macro_body(text, name)
    values = _extract_integer_arguments(text, name)
    if len(params) != len(values):
        raise ValueError(f"Parameter mismatch for {name}")
    mapping = dict(zip(params, values))
    numeric_rows: list[list[int]] = []
    for row in symbolic_rows:
        numeric_row = []
        for token in row:
            sign = -1 if token.startswith("-") else 1
            symbol = token[1:] if token.startswith(("-", "+")) else token
            if symbol == "0":
                numeric_row.append(0)
            else:
                numeric_row.append(sign * mapping[symbol])
        numeric_rows.append(numeric_row)
    matrix = np.asarray(numeric_rows, dtype=np.float64)
    if matrix.shape != (size, size):
        raise ValueError(f"Unexpected {name} shape {matrix.shape}")
    return matrix


def balance_factors(w: np.ndarray, h: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Normalize every W column and absorb its scale into the H row."""
    w = w.copy()
    h = h.copy()
    for index in range(w.shape[1]):
        scale = float(np.max(np.abs(w[:, index])))
        if scale > 0:
            w[:, index] /= scale
            h[index, :] *= scale
    return w, h


def quantize(values: np.ndarray, fractional_bits: int) -> np.ndarray:
    scale = float(1 << fractional_bits)
    return np.rint(values * scale) / scale


def factor_part(
    part: np.ndarray,
    rank: int,
    fractional_bits: int,
    seeds: int,
    max_iter: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    best: tuple[np.ndarray, np.ndarray, float] | None = None
    norm = max(float(np.linalg.norm(part, "fro")), 1.0)
    for seed in range(seeds):
        model = NMF(
            n_components=rank,
            init="random",
            random_state=seed,
            solver="mu",
            beta_loss="frobenius",
            max_iter=max_iter,
            tol=1e-7,
        )
        w = model.fit_transform(part)
        h = model.components_
        w, h = balance_factors(w, h)
        wq = quantize(w, fractional_bits)
        hq = quantize(h, fractional_bits)
        error = float(np.linalg.norm(part - wq @ hq, "fro") / norm)
        if best is None or error < best[2]:
            best = (wq, hq, error)
    assert best is not None
    return best


def candidate_ranks(size: int) -> list[int]:
    candidates = {
        4: [1, 2],
        8: [1, 2, 3, 4],
        16: [1, 2, 3, 4, 6, 8],
        32: [2, 4, 6, 8, 12, 16],
    }
    return candidates[size]


def sweep_kernel(
    matrix: np.ndarray,
    transform: str,
    size: int,
    fractional_bits: int,
    seeds: int,
    max_iter: int,
) -> list[dict[str, float | int | str]]:
    positive = np.maximum(matrix, 0.0)
    negative = np.maximum(-matrix, 0.0)
    matrix_norm = float(np.linalg.norm(matrix, "fro"))
    normalization = 64.0 * math.sqrt(size)
    results = []
    for rank in candidate_ranks(size):
        wp, hp, positive_error = factor_part(positive, rank, fractional_bits, seeds, max_iter)
        wn, hn, negative_error = factor_part(negative, rank, fractional_bits, seeds, max_iter)
        approximation = wp @ hp - wn @ hn
        delta = approximation - matrix
        relative_frobenius = float(np.linalg.norm(delta, "fro") / matrix_norm)
        spectral_error = float(np.linalg.norm(delta, 2) / np.linalg.norm(matrix, 2))
        normalized = approximation / normalization
        orthogonality = float(np.linalg.norm(normalized.T @ normalized - np.eye(size), "fro"))
        total_rank = 2 * rank
        multiplication_reduction = 100.0 * (1.0 - 2.0 * total_rank / size)
        results.append(
            {
                "transform": transform,
                "size": size,
                "rank_positive": rank,
                "rank_negative": rank,
                "total_rank": total_rank,
                "fractional_bits": fractional_bits,
                "multiplication_reduction_percent": multiplication_reduction,
                "relative_frobenius_error": relative_frobenius,
                "relative_spectral_error": spectral_error,
                "orthogonality_deviation": orthogonality,
                "positive_part_error": positive_error,
                "negative_part_error": negative_error,
                "max_absolute_matrix_error": float(np.max(np.abs(delta))),
                "nonzero_factor_entries": int(
                    np.count_nonzero(wp) + np.count_nonzero(hp) + np.count_nonzero(wn) + np.count_nonzero(hn)
                ),
            }
        )
    return results


def main() -> None:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rom",
        type=Path,
        default=Path("source/Lib/CommonLib/RomTr.cpp"),
        help="Path to VTM RomTr.cpp",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("nmf_results/rank_sweep"))
    parser.add_argument("--fractional-bits", type=int, default=8)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--max-iter", type=int, default=3000)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, float | int | str]] = []
    for transform in TRANSFORMS:
        for size in SIZES:
            matrix = load_vtm_kernel(args.rom, transform, size)
            all_results.extend(
                sweep_kernel(
                    matrix,
                    transform,
                    size,
                    args.fractional_bits,
                    args.seeds,
                    args.max_iter,
                )
            )

    csv_path = args.output_dir / "nmf_rank_sweep.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_results[0]))
        writer.writeheader()
        writer.writerows(all_results)

    json_path = args.output_dir / "nmf_rank_sweep.json"
    json_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print("\nBest positive-saving point by transform and size:")
    for transform in TRANSFORMS:
        for size in SIZES:
            candidates = [
                row
                for row in all_results
                if row["transform"] == transform
                and row["size"] == size
                and row["multiplication_reduction_percent"] > 0
            ]
            if not candidates:
                print(f"{transform}-{size}: no positive-saving equal-rank point")
                continue
            best = min(candidates, key=lambda row: float(row["relative_frobenius_error"]))
            print(
                f"{transform}-{size}: r+ = r- = {best['rank_positive']}, "
                f"saving={best['multiplication_reduction_percent']:.2f}%, "
                f"relF={best['relative_frobenius_error']:.6f}, "
                f"orth={best['orthogonality_deviation']:.6f}"
            )


if __name__ == "__main__":
    main()
