"""Extract measured VTM results; historical comparisons are pointwise, not BD-rate."""
import json
from pathlib import Path
import re
import sys

KEYS = ["bitrate_kbps", "Y_PSNR_dB", "U_PSNR_dB", "V_PSNR_dB", "YUV_PSNR_dB"]
ANCHOR = {32: [1031.5860, 37.5103, 40.6433, 42.7146, 38.4230],
          37: [499.9080, 34.8490, 39.6294, 41.0330, 35.9459]}
EQUAL_RANK = {32: [1046.3340, 37.4875, 40.6516, 42.7012, 38.4024],
              37: [505.7040, 34.8314, 39.6230, 40.9820, 35.9251]}


def parse(text, qp):
    number = r"([-+]?\d+(?:\.\d+)?)"
    rows = re.findall(r"^\s*32\s+a\s+" + r"\s+".join([number] * 5) + r"\s*$", text, re.M)
    if len(rows) != 1:
        raise ValueError(f"Expected one 32-frame summary; got {len(rows)}")
    values = list(map(float, rows[0]))
    kernels = sorted(set(re.findall(r"NMF_AUDIT kernel=(DCT8|DST7) size=(\d+) mode=(exact|nmf) ranks=(\d+,\d+) scale_bits=(\d+)", text)))
    expected = {(t, str(n), "exact" if n == 8 else "nmf", rank, "8")
                for t in ("DCT8", "DST7") for n, rank in ((8, "0,0"), (16, "3,3"), (32, "6,6"))}
    if not set(kernels).issubset(expected) or not kernels:
        raise ValueError("Missing or unexpected hybrid kernel diagnostics")
    result = {"qp": qp, "frames": 32, "LFNST": 0, "measured": dict(zip(KEYS, values)),
              "kernels_exercised": kernels, "kernels_not_observed": sorted(expected - set(kernels))}
    for label, reference in (("anchor", ANCHOR[qp]), ("equal_rank", EQUAL_RANK[qp])):
        result["vs_" + label] = {"bitrate_percent": 100 * (values[0] / reference[0] - 1),
                                  **{k: v - b for k, v, b in zip(KEYS[1:], values[1:], reference[1:])}}
    times = re.search(r"Total Time:\s+([\d.]+) sec\. \[user\]\s+([\d.]+) sec\. \[elapsed\]", text)
    if times:
        result["user_seconds"], result["elapsed_seconds"] = map(float, times.groups())
    result["reference_runs"] = {"anchor": 36857005811, "equal_rank": 37100459875, "asymmetric": 37104817752}
    return result


if __name__ == "__main__":
    print(json.dumps(parse(Path(sys.argv[1]).read_text(), int(sys.argv[2])), indent=2))
