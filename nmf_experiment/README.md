# NMF MTS feasibility experiment

This directory contains an experiment for positive/negative non-negative
matrix factorization (NMF) of the VVC DCT-VIII and DST-VII forward transform
kernels. It is independent of the repository's CD-SATM/CSSATM experiments.

## Controlled configuration

- VTM 24.0 Random Access, B1 Kimono1, 1920x1080 at 24 Hz
- MTS enabled and LFNST disabled (`MTS=1`, `LFNST=0`)
- QPs 22, 27, 32, and 37 for the final 32-frame comparison
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
and negative parts. `TrQuant.cpp` routes only the forward 8/16/32-point
DCT-VIII and DST-VII paths to these functions after SIMD initialization.

The selected low ranks reduce the dense multiplication count by 50% for size
8 and 25% for sizes 16 and 32. They also have very large approximation error
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
