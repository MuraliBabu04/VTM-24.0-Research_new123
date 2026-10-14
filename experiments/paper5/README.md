# Paper 5 RC-QRR VTM experimental matrix

This file is a planned configuration, not a claim of completed results.

- **13 sequences, 51 QP runs, 3,168 encoded frames**.
- Reuse Paper 2 anchor framing: A1 32, B 32, C 96, D 64, E 64 frames per QP.
- **A1 Tango2 QP22 is intentionally excluded**; A1 QP27/32/37 only.
- **MTS=1, LFNST=1**, matching previous anchor workflows. RC-QRR applies to the primary MTS candidate screening only, not to LFNST.
- Random Access with cfg/encoder_randomaccess_vtm.cfg plus sequence cfg.
- Report Y/U/V PSNR, bitrate, encoding time, candidate ranking/recall, exact candidates tested, and BD-rate only after QP curves are complete.
- IMPORTANT: Existing standard VTM or other NMF/CD-SATM modified jobs do **not** count as RC-QRR proposed results. The proposed encoder must contain the corrected weighted factor generation and a real screening hook with normative final RDO.
- Baselines may be reused only if sequence bytes/frames, encoder settings, QPs, and code version match; otherwise re-encode matched anchor.

| Group | QPs | Frames per QP | QP runs | Total frames |
|---|---|---:|---:|---:|
| A1 | 27,32,37 | 32 | 3 | 96 |
| B1-B3 | 22,27,32,37 | 32 | 12 | 384 |
| C1-C3 | 22,27,32,37 | 96 | 12 | 1152 |
| D1-D3 | 22,27,32,37 | 64 | 12 | 768 |
| E1-E3 | 22,27,32,37 | 64 | 12 | 768 |
