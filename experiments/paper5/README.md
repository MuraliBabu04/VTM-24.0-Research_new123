# Paper 5 - RC-QRR primary pilot experiment

These are **planned paired runs**, not experimental results.

- **8 sequences, 15 paired QP cases, 1,056 input frames per encoder / 2,112 frames total (anchor plus proposed).**
- **Both anchor and proposed:** VTM-24.0 Random Access, MTS=1 (ON), LFNST=0 (OFF).
- **A1 Tango2:** QP37 only, 32 frames.
- **B1 Kimono1:** QP22 and QP32, 32 frames each.
- **C1 RaceHorses, C2 BQMall, C3 PartyScene:** QP22 and QP37, 96 frames each.
- **D1 RaceHorses, D2 BQSquare, D3 BlowingBubbles:** QP22 and QP37, 64 frames each.
- A1 QP22 and all other sequences/QPs are excluded from this pilot.

The Paper 2 MTS=1, LFNST=1 anchor results **cannot** be reused as an RC-QRR LFNST=0 comparison. Launch matched anchors with the LFNST=0 setting.

**Important:** The paper5-proposed workflow is deliberately blocked until RC-QRR candidate screening has been integrated into VTM itself; standard VTM runs must not be mislabeled as RC-QRR proposed results. The Python-only theoretical energy model is not encoder integration.

For each run record: exact source file and number of frames, encoder version, QP, Y/U/V PSNR, bitrate, encoding time, shortlist size, selected MTS candidate IDs, ground-truth best candidate when available, exact RDO candidate counts and hardware-power data separately. **BD-rate requires four QP operating points per sequence**; this two-QP pilot measures paired point differences, not conventional BD-rate.
