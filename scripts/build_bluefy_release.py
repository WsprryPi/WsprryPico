#!/usr/bin/env python3
"""Build or verify the deterministic, offline-capable Bluefy web release."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "provisioning" / "web"
STATIC_FILES = ("app.js", "bluefy.js", "manifest.webmanifest", "style.css")
RELEASE_INPUT_FILES = ("index.html", *STATIC_FILES, "sw.js")
VERIFIED_FILES = (*STATIC_FILES, "sw.js")


def digest(data, algorithm="sha256"):
    return hashlib.new(algorithm, data).digest()


def integrity(data):
    return "sha384-" + base64.b64encode(digest(data, "sha384")).decode("ascii")


def release_id(files):
    value = hashlib.sha256()
    for name in RELEASE_INPUT_FILES:
        data = files[name]
        value.update(name.encode("ascii") + b"\0")
        value.update(str(len(data)).encode("ascii") + b"\0")
        value.update(data)
    return value.hexdigest()


def render():
    source = {name: (SOURCE / name).read_bytes() for name in RELEASE_INPUT_FILES}
    release = release_id(source)
    files = {name: source[name] for name in STATIC_FILES}
    source_sw = source["sw.js"].decode("utf-8")
    marker = 'const CACHE_NAME = "wsprrypico-bluefy-source";'
    if source_sw.count(marker) != 1:
        raise ValueError("Bluefy service-worker release marker is missing or ambiguous")
    files["sw.js"] = source_sw.replace(
        marker, f'const CACHE_NAME = "wsprrypico-bluefy-{release}";').encode("utf-8")

    inventory = {
        name: {"bytes": len(files[name]), "sha256": digest(files[name]).hex()}
        for name in sorted(VERIFIED_FILES)
    }
    manifest = {
        "version": 1,
        "protocol": 1,
        "release": release,
        "files": inventory,
    }
    files["release-manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")

    index = source["index.html"].decode("utf-8")
    replacements = {
        'content="source-only"': f'content="{release}"',
        'rel="stylesheet" href="style.css"':
            f'rel="stylesheet" href="style.css" integrity="{integrity(files["style.css"])}" crossorigin="anonymous"',
        '<script src="bluefy.js"></script>':
            f'<script src="bluefy.js" integrity="{integrity(files["bluefy.js"])}" crossorigin="anonymous"></script>',
        '<script src="app.js"></script>':
            f'<script src="app.js" integrity="{integrity(files["app.js"])}" crossorigin="anonymous"></script>',
    }
    for old, new in replacements.items():
        if index.count(old) != 1:
            raise ValueError(f"Bluefy index marker is missing or ambiguous: {old}")
        index = index.replace(old, new)
    files["index.html"] = index.encode("utf-8")
    return files


def compare(destination, expected):
    actual_names = {path.name for path in destination.iterdir() if path.is_file()}
    if actual_names != set(expected):
        missing = sorted(set(expected) - actual_names)
        extra = sorted(actual_names - set(expected))
        raise ValueError(f"Bluefy release inventory drift: missing={missing}, extra={extra}")
    for name, data in expected.items():
        if (destination / name).read_bytes() != data:
            raise ValueError(f"Bluefy release content drift: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "bluefy")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    destination = args.output.resolve()
    if args.write:
        destination.mkdir(parents=True, exist_ok=True)
        for name, data in expected.items():
            (destination / name).write_bytes(data)
    else:
        compare(destination, expected)
    print(json.loads(expected["release-manifest.json"])["release"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
