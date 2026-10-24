#!/usr/bin/env python3
"""Validate caller-selected client sources; Git identity is informational."""

from pathlib import Path
import subprocess
import sys

REQUIRED = (
    "src/codec.cpp", "src/frame_parser.cpp", "src/wire.cpp", "src/session.cpp",
    "src/detail/json.cpp", "include/wtp/codec.hpp", "include/wtp/session.hpp",
)


def verify(source):
    source = Path(source).resolve(strict=True)
    client = source / "src/WTP-Client"
    for name in REQUIRED:
        if not (client / name).is_file():
            raise ValueError(f"Missing required WsprryPi client source: {client / name}")
    print(f"Selected WsprryPi client source: {source}", flush=True)
    for args in (("rev-parse", "HEAD"), ("status", "--short")):
        try:
            result = subprocess.run(["git", "-C", str(source), *args], text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            print(result.stdout.strip() if result.returncode == 0 else "Git identity unavailable", flush=True)
        except OSError:
            print("Git identity unavailable", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_wsprrypi_client.py WSPRRYPI_SOURCE")
    try:
        verify(sys.argv[1])
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
