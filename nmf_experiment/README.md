# NMF MTS feasibility experiment

This directory contains an experiment for positive/negative non-negative
matrix factorization (NMF) of the VVC DCT-VIII and DST-VII forward transform
kernels. It is independent of the repository's CD-SATM/CSSATM experiments.

## Controlled configuration

- VTM 24.0 Random Access, B1 Kimono1, 1920x1080 at 24 Hz
- MTS enabled and LFNST disabled (`MTS=1`, `LFNST=0`)
- QPs 22, 27, 32, and 37 for the completed baseline comparison
- QPs 32 and 37 for the scale-calibration verification runs
- A short QP32/4-frame screening encode before the full proposed runs
- Normative VTM inverse transforms, so the encoder output remains decodable by
  an unmodified VTM decoder

## Reproducible factor selection

`nmf_rank_sweep.py` extracts the exact integer DCT-VIII and DST-VII kernels
from `RomTr.cpp` and evaluates positive/negative NMF ranks. The selected
positive-saving equal ranks are 1, 3, and 6 for sizes 8, 16, and 32. The
4-point transform remains normative because no equal-rank decomposition gives
a positive multiplication saving.

`generate_selected_factors.py` generates `NmfMtsFactors.h` using 8 fractional
bits and deterministic seeds. `TrQuant_EMT.cpp` evaluates the factors as two
fixed-point stages, `H*x` followed by `W*(H*x)`, independently for the positive
and negative parts. The factors model the low-precision MTS basis, while VTM's
forward kernels carry an additional 8-bit scale. The calibrated path therefore
uses `shift + 2 * factor_fractional_bits - 8`; the original feasibility path
omitted the final `- 8`, shrinking its NMF coefficients by about 256 times.
`TrQuant.cpp` routes only the forward 8/16/32-point
DCT-VIII and DST-VII paths to these functions after SIMD initialization.

The selected low ranks reduce the dense multiplication count by 50% for size
8 and 25% for sizes 16 and 32. The scale correction changes no ranks and adds
no multiplications; it only aligns coefficient magnitude with VTM's normative
forward-transform convention. They also have very large approximation error
(about 81--89% relative Frobenius error), so the short encode is a screening
test, not evidence of coding benefit.

## Commands

```bash
python3 nmf_experiment/nmf_rank_sweep.py
python3 nmf_experiment/generate_selected_factors.py
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target EncoderApp --parallel "$(nproc)"
```

Generated numerical records are stored under `nmf_results/`. No CD-SATM or
CSSATM log, bitstream, or proposed result is used by this experiment.

## Asymmetric-rank improvement

The second design keeps the mandatory 8-bit forward-scale correction and assigns
the positive and negative ranks independently under a strict multiplication
budget:

- DCT-VIII: 8=(1,2), 16=(4,3), 32=(8,6)
- DST-VII: 8=(2,1), 16=(3,4), 32=(7,7)

A non-negative least-squares gain calibrates each reconstructed transform row
and is absorbed into the W factors, so it adds no runtime multiplications.
Relative Frobenius error is reduced to about 0.765--0.805, compared with about
0.815--0.885 for the original equal-rank configuration. The retained dense
multiplication savings are 25% for size 8 and 12.5% for sizes 16 and 32.

QP32 and QP37 are used first as a controlled verification. A final BD-rate claim
still requires corrected QP22, QP27, QP32 and QP37 results.

## Scale-calibration verification

The `nmf-scale-calibrated-qp32-37` branch isolates the scale correction and
runs Kimono1 for 32 frames at QP32 and QP37 with `MTS=1` and `LFNST=0`.
This two-point check is an ablation, not a replacement for the four-QP BD-rate
experiment. If it improves both verification points, the next experiment is a
complexity-constrained asymmetric rank sweep.
