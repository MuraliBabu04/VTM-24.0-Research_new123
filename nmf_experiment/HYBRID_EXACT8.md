# Exact 8-point / NMF 16- and 32-point verification

This isolated experiment starts from scale-corrected commit
`3d9f04ee8123ee1830063295586909ae9f04dfbc`.

* DCT-VIII and DST-VII: retain normative four-point transforms; restore exact
  eight-point forward transforms; retain equal positive/negative NMF ranks
  (3,3) at size 16 and (6,6) at size 32.
* Preserve the corrected forward matrix scale, factor values, DCT-II,
  quantization, inverse transforms and bitstream syntax.
* Kimono1, Random Access, 32 frames, QP32/QP37 in parallel, MTS=1, LFNST=0.

This removes the eight-point approximation error. It does not guarantee better
end-to-end PSNR or bitrate because mode selection and prediction interact.
The theoretical dense-matrix multiplication reduction at sizes 16/32 remains
25% (2*N*(r_positive+r_negative) versus N*N), excluding additions and overhead.
This is not a measured speedup over VTM's optimized implementation or a hardware
area/power result. There is no multiplication saving claimed at size 8.

## Validation and provenance

Configure with `-DNMF_VERIFY=ON` and build `EncoderApp NmfTransformCheck`.
The check exercises 432 cases: signed/zero/impulse inputs, multiple shifts,
skipped input lines and coefficient cutoffs. It compares the hybrid eight-point
wrappers with VTM and the larger factored kernels with independently reconstructed
dense fixed-point matrices. Release builds use explicit error checks.

The workflow copies the actual CMake EncoderApp target, verifies its hash at
each QP, and saves source/factor/config hashes and the commit ID. With
`NMF_AUDIT=1`, each exercised wrapper reports its kernel, size, ranks and scale
once. These markers prove a kernel was called, not that its mode was selected
in the final bitstream. Unobserved kernels are listed in the metrics JSON.

Historical anchors come from run 36857005811; equal-rank corrected results from
37100459875; asymmetric results from 37104817752. The latter two had identical
reported coding metrics. Their source rank settings and build logs were checked;
this alone does not establish why their outputs matched. No improvement is
claimed until the new measured metrics have been compared.

Two QPs and one short sequence are a screening experiment, not a final BD-rate
evaluation. Runtimes on separate hosted runners are diagnostic and do not prove
a speedup. Final publication requires a controlled complexity benchmark and a
broader rate-distortion evaluation. Any novelty claim needs a literature review.
