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
        header = client / 'src/selected_probe.hpp'
        header.write_text('#define SELECTED_CLIENT_PROBE "' + marker + '\\n"\n')
        codec.write_text(original + '\n#include <cstdio>\n#include "selected_probe.hpp"\n'
                         'namespace { const bool selected_probe = [] { std::fputs(SELECTED_CLIENT_PROBE, stderr); return true; }(); }\n')
        configure = ["cmake", "-S", str(pico), "-B", str(build),
                     "-DCMAKE_BUILD_TYPE=Debug", "-DWSPRRY_PICO_BUILD_FIRMWARE=OFF",
                     "-DWSPRRY_PICO_BUILD_TESTS=ON", f"-DWSPRRY_PICO_WSPRRYPI_SOURCE={source}"]
        run(configure)
        run(["cmake", "--build", str(build), "--target", "host_client_interop_tests", "--parallel", "4"])
        assert marker in run([str(build / "host_client_interop_tests")])
        # No reconfigure or directory clearing: compiler dependency tracking must
        # invalidate the shared client object and relink its actual consumer.
        changed = "CHANGED_SELECTED_PI_HEADER_EXECUTED"
        header.write_text('#define SELECTED_CLIENT_PROBE "' + changed + '\\n"\n')
        run(["cmake", "--build", str(build), "--target", "host_client_interop_tests", "--parallel", "4"])
        output = run([str(build / "host_client_interop_tests")])
        assert changed in output and marker not in output
        codec.unlink()
        assert "Missing required WsprryPi client source" in run(configure, succeeds=False)
        codec.write_text(original + "\n#error INTENTIONAL_SELECTED_PI_COMPILER_ERROR\n")
        run(configure)
        failure = run(["cmake", "--build", str(build), "--target", "reference_host_client", "--parallel", "4"], succeeds=False)
        assert "INTENTIONAL_SELECTED_PI_COMPILER_ERROR" in failure
    print("Edited selected Pi source and incremental header executed; missing source and compiler errors rejected")


if __name__ == "__main__":
    main()
