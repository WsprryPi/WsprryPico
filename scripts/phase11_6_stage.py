#!/usr/bin/env python3
"""Create private Phase 11.6 fixture packets without exposing retained secrets."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from phase11_6.plan import digest, validate


SCHEMA = "phase11.6-fixture-v1"
AUTHORIZATION = "PHASE11.6-CONDUCTED-RF-20260918"
PLAN_SHA256 = "ef6624ccfa3be1b05ec914721071271fe1ef2bdb2afca5bffb200b1812ae279c"
CREDENTIALS = {
    "controller": {"ca": "credentials/controller/client-ca.crt",
                   "cert": "credentials/controller/client.crt",
                   "key": "credentials/controller/client.key"},
    "browser": {"ca": "credentials/browser/client-ca.crt",
                "cert": "credentials/browser/client.crt",
                "key": "credentials/browser/client.key"},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_wifi(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def root_and_inputs(args):
    root = args.root.resolve(strict=True)
    retained = args.retained.resolve(strict=True)
    require(root.is_dir() and not root.is_symlink() and root.stat().st_mode & 0o077 == 0,
            "fresh private fixture root")
    require(not (root / "packet.json").exists(), "fresh packet required")
    plan = validate(json.loads((root / "plan.json").read_text()))
    require(digest(plan) == PLAN_SHA256, "immutable Phase 11.6 plan")
    wifi = json.loads((retained / "retained-wifi.json").read_text())
    require(wifi.get("ssid") == "WsprryPico-Phase115"
            and wifi.get("ntp_ipv4") == "time.local"
            and isinstance(wifi.get("password"), str) and len(wifi["password"]) == 32,
            "retained accepted Wi-Fi")
    return root, retained, wifi


def remote_packet(args):
    root, retained, wifi = root_and_inputs(args)
    if (retained / "retained-wifi.json").resolve() != (root / "retained-wifi.json").resolve():
        shutil.copy2(retained / "retained-wifi.json", root / "retained-wifi.json")
    packet = {
        "schema": SCHEMA,
        "authorization": AUTHORIZATION,
        "root": str(root),
        "remote_host": "wspr4",
        "remote_host_boot_id": "5fbac52a-9d54-497f-8623-1476a380fcad",
        "remote_ap_if": "wlan1",
        "remote_ap_mac": "e8:4e:06:ac:f3:87",
        "client_address": "10.77.15.2",
        "dut_address": "10.77.15.10",
        "time_authority_address": "10.77.15.2",
        "runtime_seconds": 21_600,
        "restoration_seconds": 900,
        "plan_sha256": PLAN_SHA256,
        "wifi": wifi,
        "wifi_sha256": hashlib.sha256(canonical_wifi(wifi)).hexdigest(),
    }
    save_new(root / "packet.json", packet)
    print(json.dumps({"status": "STAGED", "role": "remote-ap",
                      "packet_sha256": sha(root / "packet.json")}))


def local_packet(args):
    root, retained, wifi = root_and_inputs(args)
    required_schema = root / "docs/protocol/wtp-1.schema.json"
    require(
        required_schema.is_file() and not required_schema.is_symlink(),
        "complete Phase 11.6 execution root",
    )
    remote_ready_path = args.remote_ready.resolve(strict=True)
    remote_ready = json.loads(remote_ready_path.read_text())
    require(remote_ready.get("schema") == "phase11.5-package11-remote-ap-ready-v1"
            and remote_ready.get("host") == "wspr4"
            and remote_ready.get("ap_mac") == "e8:4e:06:ac:f3:87"
            and remote_ready.get("wifi_sha256")
            == hashlib.sha256(canonical_wifi(wifi)).hexdigest(),
            "accepted remote AP attestation")
    attempts = root / "attempts"
    require(not attempts.exists(), "fresh attempts directory required")
    attempts.mkdir(mode=0o700)
    shutil.copy2(retained / "retained-wifi.json", root / "retained-wifi.json")
    shutil.copy2(remote_ready_path, root / "remote-ready.json")
    shutil.copytree(retained / "credentials", root / "credentials", symlinks=False)
    for name in ("browser-home", "chromium-etc"):
        source = retained / name
        require(source.is_dir() and not source.is_symlink(),
                "retained browser trust/profile directory")
        shutil.copytree(source, root / name, symlinks=False)
    for name in ("production-base.ini", "production-openssl.cnf", "observer.so"):
        source = retained / name
        if source.is_file() and not source.is_symlink():
            shutil.copy2(source, root / name)
    hashes = {}
    for role in ("controller", "browser"):
        for kind in ("ca", "cert", "key"):
            relative = CREDENTIALS[role][kind]
            path = root / relative
            info = path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size > 0,
                    "private credential file")
            hashes[relative] = sha(path)
    packet = {
        "schema": SCHEMA,
        "authorization": AUTHORIZATION,
        "root": str(root),
        "host_boot_id": "220e53ca-ca95-4206-9581-dbe28aa1eeb8",
        "client_if": "wlan2",
        "client_mac": "e8:4e:06:ae:d7:09",
        "remote_ap_mac": "e8:4e:06:ac:f3:87",
        "client_address": "10.77.15.2",
        "time_authority_address": "10.77.15.2",
        "network_runtime_seconds": 21_600,
        "network_restoration_seconds": 900,
        "plan_sha256": PLAN_SHA256,
        "wifi": wifi,
        "remote_ready": remote_ready,
        "credentials": CREDENTIALS,
        "credential_sha256": hashes,
        "tls_key_exchange_group": "X25519",
        "configuration_writes": 0,
        "controlled_reboots": 0,
        "flashes": 0,
        "bootsel": 0,
        "wifi_cycles": 0,
        "allocation_probes": 0,
        "installed_service_prepaused": True,
    }
    save_new(root / "packet.json", packet)
    print(json.dumps({"status": "STAGED", "role": "local-client",
                      "packet_sha256": sha(root / "packet.json"),
                      "credential_files": len(hashes)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="role", required=True)
    for role in ("remote", "local"):
        part = sub.add_parser(role)
        part.add_argument("--root", type=Path, required=True)
        part.add_argument("--retained", type=Path, required=True)
        if role == "local":
            part.add_argument("--remote-ready", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if args.role == "remote":
        remote_packet(args)
    else:
        local_packet(args)


if __name__ == "__main__":
    main()
