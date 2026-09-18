#!/usr/bin/env python3
"""Read-only independent audit of a retained Phase 11.6 packet."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from phase11_6.audit import audit_directory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_directory(args.directory), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
