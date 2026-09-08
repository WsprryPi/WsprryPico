#!/usr/bin/env python3
"""Read-only identity check for optional Phase 10 actual-client tests."""

from pathlib import Path
import subprocess
import sys

REVISION = "2819f0b8ccb05f12d7f978a4cee2cac830997bbf"


def verify(source):
    source = Path(source).resolve(strict=True)

    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args])

    if Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve() != source:
        raise ValueError("Select the WsprryPi repository root")
    if git("rev-parse", "HEAD").decode().strip() != REVISION:
        raise ValueError("WsprryPi HEAD differs from the reviewed host revision")
    paths = git("ls-tree", "-r", "--name-only", REVISION, "src/WTP-Client").decode().splitlines()
    if not paths:
        raise ValueError("Missing WTP client sources")
    for name in paths:
        if (source / name).read_bytes() != git("show", f"{REVISION}:{name}"):
            raise ValueError(f"WTP client differs from reviewed source: {name}")
    # Untracked headers could shadow tracked headers in the compiler's search path.
    component = source / "src/WTP-Client"
    for directory in (component / "src", component / "include"):
        for path in directory.rglob("*"):
            if path.is_file() and str(path.relative_to(source)) not in paths:
                raise ValueError(f"Unreviewed client source/header: {path}")
    print(f"Verified WsprryPi client {REVISION}: {len(paths)} tracked files")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_wsprrypi_client.py WSPRRYPI_SOURCE")
    try:
        verify(sys.argv[1])
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error
