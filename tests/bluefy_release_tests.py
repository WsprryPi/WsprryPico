#!/usr/bin/env python3
"""Deterministic release, integrity, and offline-policy checks for Bluefy."""
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "docs" / "bluefy"
SOURCE = ROOT / "src" / "provisioning" / "web"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.integrity = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        reference = values.get("src") or values.get("href")
        if reference:
            self.references.append(reference)
            if "integrity" in values:
                self.integrity[reference] = values["integrity"]


def sha384(data):
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode("ascii")

def source_release():
    value = hashlib.sha256()
    for name in ("index.html", "app.js", "bluefy.js", "manifest.webmanifest",
                 "style.css", "sw.js"):
        data = (SOURCE / name).read_bytes()
        value.update(name.encode("ascii") + b"\0")
        value.update(str(len(data)).encode("ascii") + b"\0")
        value.update(data)
    return value.hexdigest()



def main():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_bluefy_release.py"),
                    "--check"], check=True)
    manifest = json.loads((RELEASE / "release-manifest.json").read_text())
    assert manifest["version"] == manifest["protocol"] == 1
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["release"])
    assert manifest["release"] == source_release()
    assert set(manifest["files"]) == {
        "app.js", "bluefy.js", "manifest.webmanifest", "style.css", "sw.js"
    }
    for name, record in manifest["files"].items():
        data = (RELEASE / name).read_bytes()
        assert record == {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    index = (RELEASE / "index.html").read_text()
    links = Links(); links.feed(index)
    assert all(not value.startswith(("http:", "https:", "//")) for value in links.references)
    assert manifest["release"] in index and "source-only" not in index
    assert "Find nearby WsprryPicos" in index and "readonly" in index
    for name in ("style.css", "bluefy.js", "app.js"):
        assert links.integrity[name] == sha384((RELEASE / name).read_bytes())

    worker = (RELEASE / "sw.js").read_text()
    assert f'wsprrypico-bluefy-{manifest["release"]}' in worker
    assert "self.skipWaiting()" in worker
    assert "cache.put" not in worker
    for name in ("index.html", "release-manifest.json", *manifest["files"]):
        assert f'"./{name}"' in worker
    app = (RELEASE / "app.js").read_text()
    for required in ("https_required", "release_asset_integrity", "navigator.serviceWorker.ready",
                     "updateViaCache", "client.connect()", "Confirm before authorizing"):
        assert required in app
    assert '"serviceWorker" in navigator' in app
    assert "Promise.race" in app and "offline_cache_timeout" in app
    assert 'online verified' in app
    assert 'connect.disabled = false' in app
    assert app.index("for (const name of releaseFiles) await verifyAsset") < app.index(
        "connect.disabled = false")
    assert "client.connect(form.elements.device_id.value)" not in app
    generic_release = "".join((RELEASE / name).read_text() for name in (
        "index.html", "app.js", "bluefy.js", "style.css", "sw.js"))
    for candidate_only in ("fd6127d11d6aca42a9905fa3fb1bf1d5", "88:a2:9e:0a:60:df",
                           "wspr-0a60df"):
        assert candidate_only not in generic_release
    for forbidden in ("localStorage", "sessionStorage", "indexedDB"):
        assert forbidden not in app + worker
    print(json.dumps({"ok": True, "release": manifest["release"]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
