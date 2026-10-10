"""Collect paired anchor/NMF metrics for the staged multi-sequence experiment."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

METRIC_KEYS = ["bitrate_kbps", "Y_PSNR_dB", "U_PSNR_dB", "V_PSNR_dB", "YUV_PSNR_dB"]

def parse_log(path):
    text = Path(path).read_text(errors="replace")
    number = r"([-+]?\d+(?:\.\d+)?)"
    rows = re.findall(r"^\s*32\s+a\s+" + r"\s+".join([number] * 5) + r"\s*$", text, re.M)
    if len(rows) != 1:
        raise ValueError(f"Expected one 32-frame SUMMARY in {path}; got {len(rows)}")
    result = dict(zip(METRIC_KEYS, map(float, rows[0])))
    timing = re.search(r"Total Time:\s+([\d.]+) sec\. \[user\]\s+([\d.]+) sec\. \[elapsed\]", text)
    if timing:
        result["user_seconds"], result["elapsed_seconds"] = map(float, timing.groups())
    result["audit_markers"] = sorted(set(re.findall(r"^.*NMF_(?:AUDIT|HYBRID).*$", text, re.M)))
    return result

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def expected_pairs(stage):
    if stage == "bcde":
        return [(s, q) for s in ("B1", "C1", "D1", "E1")
                for q in ([22, 27] if s == "B1" else [22, 27, 32, 37])]
    if stage == "a1":
        return [("A1", q) for q in (27, 32, 37)]
    raise ValueError(stage)

def main(stage):
    out = Path("batch_summary")
    out.mkdir(exist_ok=True)
    results, errors, rows = [], [], []
    for seq, qp in expected_pairs(stage):
        root = Path("results") / seq / f"QP{qp}"
        anchor, proposed = root / "anchor", root / "proposed"
        try:
            for name in ("commit.txt", "proposed-source.sha256", "input.sha256", "metadata.json"):
                if (anchor / name).read_bytes() != (proposed / name).read_bytes():
                    raise ValueError(f"Mismatched {name}")
            a = parse_log(anchor / "encode.log")
            p = parse_log(proposed / "encode.log")
            ah, ph = sha256(anchor / "output.vvc"), sha256(proposed / "output.vvc")
            differences = {k: p[k] - a[k] for k in METRIC_KEYS}
            bitrate_pct = 100.0 * differences["bitrate_kbps"] / a["bitrate_kbps"]
            result = {
                "sequence": seq, "qp": qp, "frames": 32, "MTS": 1, "LFNST": 0,
                "anchor": a, "proposed": p, "differences": differences,
                "bitrate_change_percent": bitrate_pct,
                "anchor_sha256": ah, "proposed_sha256": ph,
                "bitstream_identical": ah == ph,
                "same_runner": False,
                "note": "Variants ran on separate GitHub-hosted runners; runtime is descriptive."
            }
            results.append(result)
            for design, values in (("anchor", a), ("proposed", p)):
                rows.append({
                    "sequence": seq, "qp": qp, "design": design,
                    **{k: values.get(k) for k in METRIC_KEYS},
                    "elapsed_seconds": values.get("elapsed_seconds"),
                    "bitstream_identical": ah == ph,
                    "bitrate_change_percent": bitrate_pct if design == "proposed" else 0.0
                })
        except Exception as exc:
            errors.append({"sequence": seq, "qp": qp, "error": str(exc)})
    report = {
        "stage": stage, "expected_pairs": len(expected_pairs(stage)),
        "compared_pairs": len(results), "results": results, "errors": errors
    }
    (out / f"{stage}.json").write_text(json.dumps(report, indent=2) + "\n")
    fields = ["sequence", "qp", "design", *METRIC_KEYS, "elapsed_seconds",
              "bitstream_identical", "bitrate_change_percent"]
    with (out / f"{stage}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "| Sequence | QP | Design | kb/s | Y | U | V | YUV | Elapsed s | Δrate % |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[k]) for k in
                     ["sequence", "qp", "design", "bitrate_kbps", "Y_PSNR_dB",
                      "U_PSNR_dB", "V_PSNR_dB", "YUV_PSNR_dB",
                      "elapsed_seconds", "bitrate_change_percent"]) + " |")
    lines.extend(["", "Errors: " + json.dumps(errors)])
    (out / f"{stage}.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit("Incomplete pairs; see preserved summaries")

if __name__ == "__main__":
    main(sys.argv[1])
