#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recursively convert media files from one extension to another using ffmpeg."
    )
    parser.add_argument("source_ext", help="Extension to convert from (e.g. flac).")
    parser.add_argument("target_ext", help="Extension to convert to (e.g. mp3).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the conversions that would happen without running ffmpeg.",
    )
    parser.add_argument(
        "--ffmpeg-path",
        default="ffmpeg",
        help="Path to the ffmpeg executable (default: %(default)s).",
    )
    return parser.parse_args()


def find_sources(root: Path, source_ext: str):
    extension = f".{source_ext.lower()}"
    for candidate in root.rglob("*"):
        if candidate.is_file() and candidate.suffix.lower() == extension:
            yield candidate


def convert_file(
    source: Path, destination: Path, ffmpeg_path: str, dry_run: bool
) -> tuple[bool, str]:
    if destination.exists():
        return False, f"skip (exists) {destination}"

    if dry_run:
        return True, f"dry-run {source} -> {destination}"

    command = [
        ffmpeg_path,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        str(destination),
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        return False, f"error ({exc.returncode}) {source}"

    return True, f"converted {source} -> {destination}"


def main() -> int:
    args = parse_args()
    ffmpeg = shutil.which(args.ffmpeg_path)
    if not ffmpeg:
        print("ffmpeg executable not found. Install ffmpeg or specify --ffmpeg-path.", file=sys.stderr)
        return 2

    cwd = Path.cwd()

    source_ext = args.source_ext.lstrip(".")
    target_ext = args.target_ext.lstrip(".")

    if source_ext.lower() == target_ext.lower():
        print("Source and target extensions are identical; nothing to convert.", file=sys.stderr)
        return 1

    total = 0
    converted = 0
    skipped = 0
    planned = 0
    failures = 0

    for source in find_sources(cwd, source_ext):
        total += 1
        destination = source.with_suffix(f".{target_ext}")
        ok, message = convert_file(source, destination, ffmpeg, args.dry_run)
        print(message)
        if ok:
            if message.startswith("dry-run"):
                planned += 1
            else:
                converted += 1
        elif message.startswith("skip"):
            skipped += 1
        else:
            failures += 1

    print(
        f"Processed {total} file(s): "
        f"{converted} converted, {skipped} skipped, {failures} failed."
    )

    if planned:
        print(f"{planned} file(s) would be converted (dry-run).")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
