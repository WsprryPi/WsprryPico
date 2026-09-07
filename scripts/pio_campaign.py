#!/usr/bin/env python3
"""Plan or explicitly execute the bounded Pico PIO band/mode campaign."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from campaign.plan import BANDS, compose, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    plan = sub.add_parser("plan", help="hardware-free canonical plan")
    plan.add_argument("output", type=Path)
    plan.add_argument("--band", action="append", choices=list(BANDS))
    check = sub.add_parser(
        "validate", help="read-only artifact and matrix verification"
    )
    check.add_argument("directory", type=Path)
    run = sub.add_parser("run", help="explicit conducted hardware campaign")
    run.add_argument("plan", type=Path)
    run.add_argument("output", type=Path)
    run.add_argument("--enable-rf", action="store_true", required=True)
    run.add_argument("--time-port", required=True)
    run.add_argument("--wtp-port", required=True)
    run.add_argument("--device-id", required=True)
    run.add_argument("--revision", required=True)
    run.add_argument("--firmware", required=True, type=Path)
    run.add_argument("--sdr-serial", required=True)
    run.add_argument("--gpsdo-serial", required=True)
    run.add_argument("--gpsdo-output", required=True, type=int, choices=[1, 2])
    run.add_argument("--receiver-host", default="wspr5")
    run.add_argument(
        "--capture-helper", default="/tmp/wsprrypico-capture-build/wspq-capture-soapy"
    )
    run.add_argument("--wsprd", type=Path, required=True)
    run.add_argument("--screen-only", action="store_true")
    args = parser.parse_args()
    if args.action == "plan":
        document = compose(args.band)
        with args.output.open("x") as output:
            output.write(json.dumps(document, indent=2) + "\n")
    elif args.action == "validate":
        from campaign.evidence import verify

        print(json.dumps(verify(args.directory), indent=2))
    else:
        document = validate(json.loads(args.plan.read_text()))
        from campaign.live import execute

        return execute(document, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
