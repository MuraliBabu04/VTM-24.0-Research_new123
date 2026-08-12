#!/usr/bin/env python3
"""Download a Class-B YUV/Y4M source and keep exactly N 1080p YUV420 frames."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path


WIDTH = 1920
HEIGHT = 1080
FRAME_SIZE = WIDTH * HEIGHT * 3 // 2


def read_exact(stream, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError(f"source ended with {remaining} frame bytes missing")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def download(url: str, target: Path) -> None:
    if "drive.google.com" in url:
        subprocess.run(
            ["python3", "-m", "gdown", url, "-O", str(target)], check=True
        )
        return
    with urllib.request.urlopen(url, timeout=120) as source, target.open("wb") as out:
        shutil.copyfileobj(source, out)


def extract_y4m(source_path: Path, output_path: Path, frames: int) -> None:
    with source_path.open("rb") as source, output_path.open("wb") as output:
        header = source.readline()
        if not header.startswith(b"YUV4MPEG2"):
            raise ValueError("input is not a Y4M stream")
        if b"W1920" not in header or b"H1080" not in header:
            raise ValueError(f"unexpected Y4M dimensions: {header!r}")
        for index in range(frames):
            marker = source.readline()
            if not marker.startswith(b"FRAME"):
                raise ValueError(f"missing FRAME marker at frame {index}")
            output.write(read_exact(source, FRAME_SIZE))


def extract_raw(source_path: Path, output_path: Path, frames: int) -> None:
    expected_size = FRAME_SIZE * frames
    actual_size = source_path.stat().st_size
    if actual_size < expected_size:
        raise ValueError(
            f"raw YUV is too small: {actual_size} bytes; need at least {expected_size}"
        )
    with source_path.open("rb") as source, output_path.open("wb") as output:
        output.write(read_exact(source, expected_size))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=64)
    args = parser.parse_args()

    if args.frames <= 0:
        raise ValueError("frames must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temporary_directory:
        downloaded = Path(temporary_directory) / "class_b_source"
        download(args.url, downloaded)
        with downloaded.open("rb") as source:
            is_y4m = source.read(9) == b"YUV4MPEG2"
        if is_y4m:
            extract_y4m(downloaded, args.output, args.frames)
        else:
            extract_raw(downloaded, args.output, args.frames)

    expected_size = FRAME_SIZE * args.frames
    actual_size = args.output.stat().st_size
    if actual_size != expected_size:
        raise ValueError(f"output size is {actual_size}; expected {expected_size}")
    print(f"Prepared {args.frames} frames at {args.output} ({actual_size} bytes)")


if __name__ == "__main__":
    main()
