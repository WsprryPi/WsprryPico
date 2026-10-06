#!/usr/bin/env python3
"""Exercise the actual target-only checkpoint hook with Linux SDK/USB doubles."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEADERS = {
    'hardware/structs/watchdog.h': '#pragma once\n#include <cstdint>\nstruct watchdog_stub { std::uint32_t scratch[8]; };\nextern watchdog_stub* watchdog_hw;\n',
    'hardware/watchdog.h': '#pragma once\nbool watchdog_caused_reboot();\nvoid watchdog_reboot(unsigned,unsigned,unsigned);\nvoid watchdog_update();\n',
    'pico/platform.h': '#pragma once\nvoid tight_loop_contents();\n',
    'pico/time.h': '#pragma once\n#include <cstdint>\nstd::uint64_t time_us_64();\n',
    'tusb.h': '#pragma once\nvoid tud_task();\n',
}
HARNESS = r'''
#include "provisioning/pico/phase12_fault_fixture.hpp"
#include "hardware/structs/watchdog.h"
#include "usb/transport.hpp"
#include <stdexcept>
#include <string>
#include <iostream>
watchdog_stub storage{};
watchdog_stub* watchdog_hw = &storage;
bool caused = false, rebooted = false;
unsigned updates = 0, tasks = 0, services = 0, tries = 0, cues = 0;
std::uint64_t now = 0;
std::string delivered;
bool watchdog_caused_reboot() { return caused; }
void watchdog_reboot(unsigned, unsigned, unsigned delay) {
    if (delay != 1) throw std::runtime_error("unexpected watchdog delay");
    rebooted = true;
}
void watchdog_update() { ++updates; }
void tight_loop_contents() {
    if (rebooted) throw std::runtime_error("expected reboot");
#ifdef WSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE
    now += 1'000'000;
    if (updates == 1000) throw std::runtime_error("operator power removal");
#endif
}
std::uint64_t time_us_64() { now += 1'000'000; return now; }
void tud_task() { ++tasks; }
namespace wsprrypico::usb {
void service() { ++services; }
bool console_connected() { return tasks > 2; }
bool console_write(std::string_view text) {
    // Backpressure must retry the cue without delivering it twice.
    if (++tries == 1) return false;
    ++cues; delivered = text; return true;
}
}
void check(bool value, const char* label) {
    if (!value) throw std::runtime_error(label);
}
void trigger() {
    using namespace wsprrypico::provisioning;
    if (WSPRRY_PICO_PHASE12_FAULT_STAGE == 1)
        phase12_reset_checkpoint(ResetCheckpoint::Intent);
    else
        phase12_profile_programmed(0);
}
void expect_interruption() {
    try { trigger(); throw std::runtime_error("checkpoint returned"); }
    catch (const std::runtime_error& e) {
#ifdef WSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE
        check(std::string(e.what()) == "operator power removal", e.what());
#else
        check(std::string(e.what()) == "expected reboot", e.what());
#endif
    }
}
int main() {
    using namespace wsprrypico::provisioning;
    phase12_fault_capture_boot();
    check(!phase12_fault_consumed(), "fresh boot consumed");
    phase12_reset_checkpoint(ResetCheckpoint::PreservationComplete);
    phase12_profile_programmed(256);
    check(!rebooted && tasks == 0, "wrong checkpoint acted");
    expect_interruption();
    check(phase12_fault_consumed(), "same-boot consumption absent");
#ifdef WSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE
    check(updates == 1000 && now > 120'000'000 && !rebooted,
          "operator wait expired or watchdog service stopped");
    check(tasks == services && tasks == updates, "USB service incomplete");
    check(cues == 1 && tries == 2, "cue duplicated or backpressure not retried");
    const auto expected = WSPRRY_PICO_PHASE12_FAULT_STAGE == 1
        ? "{\"phase12_physical_cut_ready\":1}\n"
        : "{\"phase12_physical_cut_ready\":9}\n";
    check(delivered == expected, "cue has wrong checkpoint");
#else
    check(tasks == 0 && updates == 0 && cues == 0, "default fixture acquired pause");
#endif
    const auto count = updates;
    rebooted = false;
    trigger();
    check(!rebooted && updates == count, "same boot checkpoint replayed");
    caused = true;
    phase12_fault_capture_boot();
    trigger();
    check(!rebooted && updates == count, "watchdog boot checkpoint replayed");
    caused = false;
    phase12_fault_capture_boot();
    check(!phase12_fault_consumed(), "cold boot must not infer volatile consumption");
    std::cout << "PASS actual checkpoint, operator wait, cue, backpressure, consumption\n";
}
'''


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux C++ validation only')
class PhysicalCutFixtureTests(unittest.TestCase):
    def test_actual_hook_for_both_selected_checkpoints_and_default(self):
        with tempfile.TemporaryDirectory(prefix='phase12-cut-') as directory:
            work = pathlib.Path(directory)
            for name, text in HEADERS.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            harness = work / 'harness.cpp'
            harness.write_text(HARNESS)
            for stage, pause in ((1, True), (9, True), (1, False), (9, False)):
                with self.subTest(stage=stage, pause=pause):
                    executable = work / f'case-{stage}-{pause}'
                    command = ['g++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                               '-I', str(work), '-I', str(ROOT / 'src'),
                               '-DWSPRRY_PICO_RF_OUTPUT_DISABLED=1',
                               f'-DWSPRRY_PICO_PHASE12_FAULT_STAGE={stage}']
                    if pause:
                        command.append('-DWSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE=1')
                    command += [str(ROOT / 'src/provisioning/pico/phase12_fault_fixture.cpp'),
                                str(harness), '-o', str(executable)]
                    subprocess.run(command, check=True, capture_output=True, timeout=30)
                    result = subprocess.run([str(executable)], check=True, capture_output=True,
                                            text=True, timeout=5)
                    self.assertIn('PASS actual checkpoint', result.stdout)


if __name__ == '__main__':
    unittest.main()
