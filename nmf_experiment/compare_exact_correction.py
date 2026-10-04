"""Compare paired encodes from the same commit/config/input and host."""
import hashlib
import json
from pathlib import Path
import re
import sys


def parse(path):
    text = Path(path).read_text()
    number = r"([-+]?\d+(?:\.\d+)?)"
    rows = re.findall(r"^\s*32\s+a\s+" + r"\s+".join([number] * 5) + r"\s*$", text, re.M)
    if len(rows) != 1:
        raise ValueError(f"Expected one 32-frame SUMMARY in {path}; got {len(rows)}")
    names = ["bitrate_kbps", "Y_PSNR_dB", "U_PSNR_dB", "V_PSNR_dB", "YUV_PSNR_dB"]
    result = dict(zip(names, map(float, rows[0])))
    time = re.search(r"Total Time:\s+([\d.]+) sec\. \[user\]\s+([\d.]+) sec\. \[elapsed\]", text)
    if time:
        result["user_seconds"], result["elapsed_seconds"] = map(float, time.groups())
    result["exact_kernels_observed"] = sorted(set(re.findall(r"NMF_EXACT kernel=(DCT8|DST7) size=(16|32) ranks=(\d+,\d+) correction_nnz=(\d+) factor_bits=(\d+) forward_precision_bits=(\d+)", text)))
    return result


def compare(anchor_log, proposed_log, anchor_bitstream, proposed_bitstream, qp):
    anchor, proposed = parse(anchor_log), parse(proposed_log)
    hashes = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (anchor_bitstream, proposed_bitstream)]
    keys = ["bitrate_kbps", "Y_PSNR_dB", "U_PSNR_dB", "V_PSNR_dB", "YUV_PSNR_dB"]
    expected = {(t, n) for t in ("DCT8", "DST7") for n in ("16", "32")}
    observed = {(k[0], k[1]) for k in proposed["exact_kernels_observed"]}
    return {"qp": qp, "frames": 32, "LFNST": 0, "anchor": anchor, "proposed": proposed,
            "differences": {k: proposed[k] - anchor[k] for k in keys},
            "anchor_sha256": hashes[0], "proposed_sha256": hashes[1],
            "bitstream_identical": hashes[0] == hashes[1],
            "reported_metrics_identical": all(anchor[k] == proposed[k] for k in keys),
            "exact_kernels_not_observed": sorted(expected - observed),
            "note": "Exact correction has dense overhead; power savings are not established."}


if __name__ == "__main__":
    result = compare(*sys.argv[1:5], int(sys.argv[5]))
    print(json.dumps(result, indent=2))
    if not result["bitstream_identical"] or not result["reported_metrics_identical"]:
        raise SystemExit("FAIL: exact correction did not reproduce the paired anchor")
    if not result["proposed"]["exact_kernels_observed"]:
        raise SystemExit("FAIL: no exact NMF kernel was observed during encoding")
