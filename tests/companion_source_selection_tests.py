#!/usr/bin/env python3
"""Compile and execute edited selected Pi sources; reject missing sources and real compiler errors."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(args, succeeds=True):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=180)
    if (result.returncode == 0) != succeeds:
        raise AssertionError(f"Unexpected result {result.returncode}: {args}\n{result.stdout[-12000:]}")
    return result.stdout


def main():
    selected = Path(sys.argv[1]).resolve()
    pico = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="wsprrypico-selected-pi-") as temp:
        root = Path(temp)
        source, build = root / "pi", root / "host"
        client = source / "src/WTP-Client"
        for directory in ("src", "include"):
            shutil.copytree(selected / "src/WTP-Client" / directory, client / directory)
        codec = client / "src/codec.cpp"
        original = codec.read_text()
        marker = "EDITED_SELECTED_PI_CLIENT_EXECUTED"
        codec.write_text(original + '\n#include <cstdio>\nnamespace { const bool selected_probe = [] { std::fputs("' + marker + '\\n", stderr); return true; }(); }\n')
        configure = ["cmake", "-S", str(pico), "-B", str(build),
                     "-DCMAKE_BUILD_TYPE=Debug", "-DWSPRRY_PICO_BUILD_FIRMWARE=OFF",
                     "-DWSPRRY_PICO_BUILD_TESTS=ON", f"-DWSPRRY_PICO_WSPRRYPI_SOURCE={source}"]
        run(configure)
        run(["cmake", "--build", str(build), "--target", "host_client_interop_tests", "--parallel", "4"])
        assert marker in run([str(build / "host_client_interop_tests")])
        codec.unlink()
        assert "Missing required WsprryPi client source" in run(configure, succeeds=False)
        codec.write_text(original + "\n#error INTENTIONAL_SELECTED_PI_COMPILER_ERROR\n")
        run(configure)
        failure = run(["cmake", "--build", str(build), "--target", "reference_host_client", "--parallel", "4"], succeeds=False)
        assert "INTENTIONAL_SELECTED_PI_COMPILER_ERROR" in failure
    print("Edited selected Pi source without Git metadata compiled and executed; missing source and compiler errors rejected")


if __name__ == "__main__":
    main()
