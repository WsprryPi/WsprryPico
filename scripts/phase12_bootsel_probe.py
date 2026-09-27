#!/usr/bin/env python3
"""Bounded, opt-in USB probe of runtime BOOTSEL on an identified Pico."""

import argparse
import json
import threading
import time
import urllib.request

import serial


def exchange(port, command):
    port.write((command + "\n").encode("ascii"))
    line = port.readline()
    if not line:
        raise RuntimeError(f"No response to {command}")
    return json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--ap-traffic", action="store_true")
    parser.add_argument("--expect-press-release", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run or not 1 <= args.samples <= 100 or not 0 <= args.interval <= 5:
        parser.error("--run and bounded samples/interval are required")
    with serial.Serial(args.port, 115200, timeout=5, write_timeout=5, exclusive=True) as port:
        info = exchange(port, "INFO")
        if info.get("device_id") != args.device_id:
            raise RuntimeError("Unexpected Pico device ID")
        status = exchange(port, "STATUS")
        if status.get("state") != "empty" or status.get("output_active") is not False:
            raise RuntimeError("Pico is not empty and output inactive")
        print(json.dumps({"revision": info.get("revision"), "device_id": args.device_id,
                          "boot_id": status.get("boot_id"), "engine": status.get("engine")}),
              flush=True)
        stop = threading.Event()
        traffic = {"ok": 0, "fail": 0}

        def fetch_ap():
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            while not stop.is_set():
                try:
                    with opener.open("http://192.168.4.1/", timeout=2) as reply:
                        if reply.status == 200:
                            traffic["ok"] += 1
                        else:
                            traffic["fail"] += 1
                except Exception:
                    traffic["fail"] += 1
                stop.wait(0.05)

        worker = threading.Thread(target=fetch_ap, daemon=True) if args.ap_traffic else None
        if worker:
            worker.start()
        saw_press = saw_release = False
        try:
            for _ in range(args.samples):
                sample = exchange(port, "BOOTSEL PROBE")
                print(json.dumps(sample, sort_keys=True), flush=True)
                if sample.get("ok") is not True:
                    raise RuntimeError("BOOTSEL safe-zone probe failed")
                if sample.get("pressed") is True:
                    saw_press = True
                elif sample.get("pressed") is False:
                    if saw_press:
                        saw_release = True
                    elif not args.expect_press_release:
                        pass
                else:
                    raise RuntimeError("Missing BOOTSEL button state")
                if not args.expect_press_release and saw_press:
                    raise RuntimeError("Unexpected BOOTSEL press during released check")
                time.sleep(args.interval)
        finally:
            stop.set()
            if worker:
                worker.join(timeout=3)
                print(json.dumps({"ap_get_200": traffic["ok"],
                                  "ap_get_fail": traffic["fail"]}), flush=True)
                if traffic["ok"] == 0 or traffic["fail"]:
                    raise RuntimeError("AP traffic failed during BOOTSEL probe")
        if args.expect_press_release and not (saw_press and saw_release):
            raise RuntimeError("BOOTSEL press/release transition was not observed")


if __name__ == "__main__":
    main()
