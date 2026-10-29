# Amplifier timing validation

The [amplifier contract](amplifier-enable.md#lead-and-tail-timing) defines 200 ms default lead and tail, independent integer settings from 0 to 1000 ms, restart activation and unchanged encoded RF duration. The production amplifier GPIO remains disabled by default. GP17 is a temporary external LED fixture only.

## Candidate and build identity

| Component | Qualified candidate |
| --- | --- |
| Pico source | `14cbb5d465c6df489a3a8088ecb97339df4b4b2e` |
| Pi source | `e8d10e11c155cfbb4f441e39ae2e42f5f7e08915` |
| WsprryPi-Docs source | `9dc709e4c46d8c6834a2c4471783854f0bb36819` |
| Pico SDK | 2.3.1, `079c6f39023649b154152db30f1d781e884879bc` |
| Compiler | Arm GNU 15.3.1 |
| Paired crypto dependency | Mbed TLS `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` |
| Firmware variant / board | Normal PIO/DMA RF application, Pico 2 W / RP2350 |
| Developer image SHA-256 | `a67e11df51d67a6e9cdc8ea257033dee7de09224616162db05544b1fb2022c3d` |
| Source input SHA-256 | `bbac6f21d33b3dd98af98456898abf8cd3acf6445302affa43e1cdf91c56ec9e` |

The developer bundle contains the exact UF2 and `local-build.json`, with clean source identity `14cbb5d465c6`. It is retained under `build/amplifier-hardware/timed-bundle` and `/home/pi/amplifier-timing-20261028-e88fa03/timed-bundle` on wspr5. Installation uses `scripts/usb_installer.py`; no direct programming replaces its transaction or same-board reference. The final image transaction is `/var/lib/wsprrypi/pico-usb/0BF4B4AEC9FFB344-qzk4k11_/transaction.json`.

## Software evidence

The Linux host suite passes 136/136 tests on the exact Pico source. The macOS profile with retained Mbed TLS passes 160/161 tests; `event_storage_tests` has the same retained-history headroom failure on untouched baseline `b37e920307900963e40b2a47312f0ee5ba15488a`. The nine affected amplifier, PIO/DMA, worker and core checks pass after the changes. The Linux/CI profiles are the reproducible software baseline; the macOS failure is not target timing evidence.

Both actual network and USB source-pair suites pass for these revisions, including all three network management carriers. [Pico software/firmware CI](https://github.com/WsprryPi/WsprryPico/actions/runs/40790651718) and [Pi CI with the full Pico SHA selected explicitly](https://github.com/WsprryPi/WsprryPi/actions/runs/40790757171) succeed. Firmware publication is skipped; these are checks and retained developer bundles.

The actual source-pair recipes select the candidate sources explicitly. `/work/amplifier-final-pico` and `/work/amplifier-final-pi` are isolated Git checkouts of the revisions above; retained npm dependency symlinks supply the pinned packages. `/work/mbedtls` is the independent pinned crypto checkout. These commands exercise production clients, Pico handlers, crypto, framing/ACK, persistence, UI producers and negative contracts:

```sh
cmake -S /work/amplifier-final-pico -B /work/amplifier-final-host \
  -DWSPRRY_PICO_BUILD_FIRMWARE=OFF -DWSPRRY_PICO_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build /work/amplifier-final-host -j4
NODE_OPTIONS=--experimental-global-webcrypto ctest --test-dir /work/amplifier-final-host --output-on-failure -j4

cd /work/amplifier-final-pi/src
WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 make wtp-network-runtime-test wtp-network-interop-test wtp-config-interop-test \
  BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= \
  PICO_SOURCE=/work/amplifier-final-pico MBEDTLS_SOURCE=/work/mbedtls
cd /work/amplifier-final-pi
make -C src wtp-usb-pair-client-build wtp-usb-management-test SUDO=
node WsprryPi-UI/tests/wtp_usb_settings_test.js
WSPRRYPI_GPIO_DRIVE_REQUIRED=1 node WsprryPi-UI/tests/wtp_usb_pair_test.js \
  src/build/wtp-network/wtp_usb_pair_client /work/amplifier-final-host/usb_management_driver
```

Production browser checks pass on Chrome 156.0.8078.48 using the Pico HTTP/AEAD fixture and the Pi PHP fixture, including desktop/mobile layout, locked public reads, drafts, revision and uncertain-save recovery. `node tests/amplifier_timing_browser_tests.js` additionally rejects array-valued identities and contradictory saved/boot timing without a restart latch. The same shared editor source is shipped by both applications. The independent Impeccable reviewer scored the Pi help-text contradiction and obsolete Pico no-delay sentence resolved; those verdicts cover the listed UI corrections only. The documenter checked the maintained operating instructions. No independent core/RF review is claimed.

The remaining executed checks use the existing pinned SDK/picotool paths supplied through the environment. The developer build directory is new for each installer plan; commands shown here identify the retained run.

```sh
python3 scripts/usb_installer.py plan --branch devel --local-build "$PWD" \
  --source-revision 14cbb5d465c6df489a3a8088ecb97339df4b4b2e \
  --build-dir "$PWD/build/amplifier-timed-candidate" \
  --output "$PWD/build/amplifier-hardware/timed-bundle" --json-only
cmake --build build/amplifier-timed-candidate --target WsprryPico-Inhibited --parallel 4
ctest --test-dir build/amplifier-host --output-on-failure -R 'amplifier|pio_dma|rf_worker|wsprrypico_core'
node tests/operator_cleanup_browser.mjs build/amplifier-host/consumer_session_driver build/amplifier-ui
# From the Pi checkout, using the isolated PHP fixture:
WSPRRYPI_UI_FIXTURE_URL=http://127.0.0.1:60873/ node WsprryPi-UI/tests/wtp_network_ui_integration_test.js
# From the Pico checkout:
docs/.venv/bin/python -m sphinx -W --keep-going -b html docs docs/_build/html
docs/.venv/bin/python scripts/check_documentation.py
python3 scripts/validate_wtp_contract.py
```

The WTP artifact validator passes 23 schema, seven raw-JSON, one framing and eight transition cases. Both documentation sites build strictly, local links validate and `git diff --check` passes. The final closeout changes documentation only; the installed/tested code identity remains the candidate listed above.

Both normal and inhibited firmware cross-build, with linked FLASH/journal, USB topology, heap, stack and renderer-placement audits. The final normal ELF reports 2,737,600 text bytes and 381,572 BSS bytes. Arm ABI object sizes change as follows: `AmplifierEnable` 8→16 bytes, sink 184→272, Config 240→248, Scheduler 848→856 and WorkerEngine 1,256→1,392; the 166,176-byte StreamEngine is unchanged. Core 1 retains its dedicated 16 KiB BSS stack, the primary stack remains 32 KiB, and reserved journals begin at `0x103ec000`. Timing state and observations add fixed storage; launch interrupts add no allocation, logging, network, storage or cross-core waits.

## Physical GPIO acceptance

Physical GPIO acceptance passed the ten-case matrix and a separate two-job continuity check. The board is Pico A, USB serial `0BF4B4AEC9FFB344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`, running the normal 138 MHz PIO/DMA engine. The user confirmed the current conducted path on 2026-10-28: GP2 through its 20 dB attenuator, combiner and 40 dB attenuation to RSP1B `2404058C60` on wspr5, with no antenna. No amplifier is attached. The existing active-high external LED on GP17 is temporarily reassigned to amplifier enable; it is restored to its indicator role afterward.

The accepted observation method is the board's GPIO/function/direction readback and local PIO launch boundary, returned afterward in Console INFO as `amplifier-readback/1`. The timing source uses the production USB UTC exchange against PPS-disciplined wspr5; healthy SNTP retains its normal priority. Test ARM uses the existing 500 ms uncertainty ceiling without changing firmware admission limits. Each job is a finite 600 ms tone or keyed QRSS event job at 14.097100 MHz; the keyed job includes an internal off gap. These observations qualify local commanded logic and timing, not amplifier readiness, RF power, antenna use or independently measured RF silence.

Acceptance bounds are fixed before measurement: lead is at least the configured value and no more than 2 ms longer; normal tail is at least the configured value and no more than 1 ms longer; launch-to-verified-off readback is within 1 ms after the unchanged encoded interval. This is an observation-latency bound, not a measured extension of emitted RF; the hardware DMA sample budget and clock are checked separately. Zero selects immediate ordering, disabled configuration produces no enable/disable observations, late ARM must refuse without activation, lead cancellation must prevent RF launch and tail cancellation must bypass the remaining dwell. Startup must be inactive and original settings/services must be restored.

The measured intervals below use Pico monotonic timestamps after checked GPIO observations. The RF column is launch to verified-off readback, including observer latency; every accepted RF job retains the 600 ms encoded sample budget. Each matrix case has a fresh boot; the first two default results are retained from the preceding successful pass of the same image. The separate continuity check uses one boot and one ownership/session for two jobs.

| Case | Lead (ms) | Normal tail (ms) | RF launch to verified-off (ms) | Result |
| --- | ---: | ---: | ---: | --- |
| Default tone 1 | 200.735 | 200.078 | 600.156 | Complete |
| Default tone 2 | 200.807 | 200.133 | 600.186 | Complete |
| Default keyed QRSS events | 200.851 | 200.119 | 600.089 | Complete, including an internal gap |
| Zero lead/tail | 0.009 | 0.029 | 600.205 | Immediate ordering, no scheduled dwell |
| Maximum lead/tail | 1000.813 | 1000.064 | 600.225 | Complete |
| Active-low, 200/200 | 200.893 | 200.105 | 600.082 | Complete |
| Late ARM | — | — | — | Refused; previous timing/GPIO observation unchanged |
| Abort during lead | — | — | No RF launch | Enable deasserted; checked after canceled launch deadline |
| Abort during tail | 1000.655 | 166.971 before abort completion | 600.133 | Remaining 1000 ms tail bypassed |
| Amplifier disabled | No observation | No observation | 600.075 | Complete without artificial enable/disable timestamps |

Two consecutive 600 ms tone jobs also complete under one WTP ownership/session and boot `ec4534f48896ace448b6d78b0981a23c`, with verified inactive output between jobs. The final readback has epoch 2, 200.860 ms lead and 200.164 ms tail. This confirms ordinary follow-on execution without a reboot between jobs.

The initial stress harness repeatedly combined full Console diagnostics and STATUS/session traffic; a later LOAD did not reach preparation and its logical stream closed before ARM. A diagnostic heap observation reported 56,656 available bytes, consistent with the source’s conservative 65,536-byte decode-plus-authority admission requirement under that traffic. Outputs remained inactive and settings were restored. The event-driven, same-session two-job path passes without that traffic. Maximum capacity under combined diagnostic/reply-cache pressure remains unqualified; no reserve, limit, validator or protocol version was relaxed to obtain the timing results. An initially requested `cw` test mode was explicitly refused before output; the keyed test uses the advertised `qrss` mode.

Private raw evidence, exact probe scripts, installer records and restoration snapshots are retained under `build/amplifier-hardware/board` and `/home/pi/amplifier-timing-20261028-e88fa03` on wspr5. The final matrix is `evidence-completion/summary.json` and the continuity check is `evidence-adjacent/summary.json`. Probe SHA-256 values are `a5811f3cc61622b401299e5f41b3f8939343696afb0c3e4dd0d378e907b8854c` for `campaign.py` and `75ed596c5d22df14fed66520d2ac819e9de56f12e29855da56ee61d6639732b5` for `adjacent.py`. The matrix command selects serial `0BF4B4AEC9FFB344`, full source `14cbb5d465c6df489a3a8088ecb97339df4b4b2e` and the explicit `--run-conducted` gate; both scripts use the production installer management/USB/WTP helpers.

Final readback reports source `14cbb5d465c6`, original saved settings, amplifier pin null, active-high external indicator GP17, 200/200 ms saved and boot timing, no pending restart, inactive outputs and an empty/unowned job. Logging, UDP logging, network enablement, station/Wi-Fi, schedules, progress, calibration, drive, frequency and watermarks match the original saved semantics. `wsprrypi.service` is active. Picos B and C still report source `604907dade70`, their original external LED plans, disabled schedules and empty/unowned jobs; they were not flashed. The retained same-board image reference matches the final bundle.

## Adversarial findings and closure

| Finding | Correction and verification |
| --- | --- |
| P1: a shortened/refined UTC target could consume the required settling interval | Monotonic checked enable time starts the minimum interval; earlier refinement, delayed activation and stale callbacks fail safely in lifecycle tests. |
| P1: reasserting a changed enable pad at RF launch could masquerade as completed settling | The launch adapter performs a nonmutating pad/function/direction check; failure prevents RF and deasserts enable. Adapter and lifecycle tests cover mismatch and both polarities. |
| P1: a static advertised ARM minimum could disagree with timing admission | CAPS and ARM share `max(existing minimum, lead + 2 ms)` at boot. The production Pi scheduler consumes that capability; lifecycle tests check the advertised 202 ms default. |
| P1: a nominal-end watchdog could reject a valid tail after late RF-off observation | The actual RF-off-anchored deadline now travels through sink, worker and service; the target-derived 167 µs regression fails the previous implementation and passes the corrected production path. |
| P1: cached armed activity could confuse lead/tail with RF | Explicit internal phase and launch history distinguish waiting, lead, RF and tail, while ownership remains held through verified cleanup. Worker/service tests cover these transitions. |
| P1: extending historical public-read/1 would redefine a closed contract | The original route list stays exact; independently selected public-read/2 contains only timing. Historical/current and hostile shape tests pass. |
| P1: a blank store could be dereferenced while selecting boot timing | Boot selection checks the optional Config before access; default, blank and corrupt-store paths retain inactive admission. |
| P2: a shared editor could coerce an array identity into text or accept contradictory boot timing | Explicit string identity types and saved/boot/restart consistency are checked; new negative tests and both production browser workflows pass. |
| P2: help text contradicted the new feature | Both stale sentences were corrected and the independent UI reviewer scored them resolved. |

The first target pass exposed a P1 nominal-end watchdog error: an RF-off readback 167 µs after the encoded end left a correct 200 ms dwell outside the nominal-end allowance. The regression reproduces that delay, fails the preceding implementation and passes after the sink, worker and service carry the RF-off-anchored tail deadline. The 100 µs unconfirmed-RF acknowledgement rule is unchanged. The initial 100 µs launch-to-RF-off-readback criterion also conflated IRQ observation latency with physical RF duration; subsequent readback acceptance explicitly allows 1 ms of instrumentation latency while checking unchanged sample count, lead and tail independently. The initial tail-jitter target of 100 µs was also exceeded by a normally completed job. The feature specifies minimum whole-millisecond intervals; subsequent acceptance uses a 1 ms GPIO scheduling envelope and retains the raw observation before assertions. These revised measurement limits are defined before the final repeat campaign. No 100 µs target-jitter guarantee is claimed.

The final assessment checks the unchanged waveform path, immutable per-boot policy, bounded local alarms, arithmetic, lease extension, immediate fault cancellation, deassertion before fallible DMA cleanup, no reactivation after cancellation, independent version negotiation and saved-state preservation. The target-derived completion finding is closed by the failing-before/passing-after regression and the corrected-image measurements. All required local source-pair checks and exact-source CI are successful. The remaining limits concern the stated GPIO observation method and resource-stress capacity, rather than an unfinished timing acceptance case.
