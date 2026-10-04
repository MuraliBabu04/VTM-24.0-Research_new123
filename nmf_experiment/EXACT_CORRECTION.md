# Exact correction experiment

Base: 59dd2e87fbc1abc534ea0908fd4b14e3160d7e3e. Eight-point MTS remains
normative. Sizes 16 and 32 compute the same equal-rank NMF products as the
previous hybrid, plus an exact integer correction. Ranks per sign remain 3
and 6. DCT-II, inverse transforms and quantization are normative.

Let F = W_positive H_positive - W_negative H_negative in Q16 integer scale.
The correction is E = 65536 * T_forward - F, where T_forward is the actual
compiled VTM forward matrix. For each line, compute F*x + E*x using int64
intermediates, then apply one rounding and right shift by (VTM_shift + 16).
This reproduces the normative sum and rounding within the verified integer
range. Neither the NMF term nor the correction is separately rounded.

The earlier approximate path unconditionally restored 2^8. That scale does
not apply to the default normal-precision build (RExt__HIGH_BIT_DEPTH_SUPPORT=0).
The exact path derives its correction from the compiled matrix and works with
both normal and high precision. Legacy approximate functions remain for
historical experiments but are not dispatched in this workflow.

## Cost finding

The correction is almost fully dense. Full-output normal-precision counts per
line, before specialized constant multiplication and other hardware optimization:

| Kernel | Size | Correction nonzeros | Dense multiplications | NMF+correction multiplications |
|---|---:|---:|---:|---:|
| DCT8 | 16 | 256/256 | 256 | 448 |
| DST7 | 16 | 256/256 | 256 | 448 |
| DCT8 | 32 | 1024/1024 | 1024 | 1792 |
| DST7 | 32 | 1023/1024 | 1024 | 1791 |

For the 32-point 16-row cutoff, the corrected count is 1088 versus 512 dense.
These counts exclude additions, wider arithmetic and setup/storage costs.
They compare against dense arithmetic, not VTM's optimized butterfly/SIMD.
This version is a numerical verification baseline, not an established
low-complexity or low-power architecture. Low-power claims need a different,
cheaper correction/factorization and measured hardware results.

## Checks

`verify_exact_correction.cpp` checks 5040 cases: six 1-D kernels, signed/zero/
impulse/random inputs, four shifts, skipped lines/full cutoffs, and rectangular
two-pass combinations with the VVC 32-point cutoff. It compares both normative
VTM functions and independent dense integer evaluation and audits E+F=65536*T.
Local normal/high precision and undefined-behavior checks are recorded by the
experiment workflow. Each encode records runtime kernel markers and build hashes.

The paired anchor uses the same source commit, build settings, config, input and
QP with NMF_EXACT_ANCHOR=ON, which leaves normative dispatch after SIMD setup.
Both paired encoders run sequentially in the same QP job; QP32/QP37 jobs run in
parallel. Results include both bitstreams, logs, hashes and metric comparisons.
Equality is required for both bitstream SHA-256 and reported bitrate/PSNR.
Single paired runtimes are diagnostic, not a controlled complexity benchmark.
