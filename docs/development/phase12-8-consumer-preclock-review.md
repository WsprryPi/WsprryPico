# P12.8 consumer pre-clock boot: execution and adversarial review

Status: **SOURCE CHECKPOINT; P12.8 AND PHASE 12 OPEN** (2026-09-27).
This is one bounded part of the
[consumer activation execution prompt](phase12-8-consumer-activation-execution-prompt.md).
No owner route can write source 5 in the production image.

## Change and evidence

`RuntimeProfile` now parses a committed source-5 payload, compares its full
device ID, owns and scrubs its fields, and selects `ConsumerPreClock`. It
provides the embedded Wi-Fi and station fields as an overlay without writing
the standalone schedule or watermark stores. The default Pico 2 W image may
associate to that Wi-Fi for time even when no standalone config exists.
The scheduler is suspended at boot. USB WTP, BLE GATT, console mutations and
the existing engineering TLS listener remain unavailable. The open AP serves
only the recovery page and public status for this source; the older
WiFi-Bootstrap/1 mutation still requires blank generation zero. `INFO` and
public status label the state `consumer_preclock`, so structural admission is
never reported as activated consumer authority.

Host build and the default Pico 2 W cross-build passed with the pinned Pico
SDK `079c6f39023649b154152db30f1d781e884879bc` and Arm GCC 15.3.1.
The focused runtime/storage and transport-contract tests passed. The full
host run passed 110/111 inside the sandbox; its mock TLS server could not
bind loopback there (`TLS start error -1`). That same test passed with
loopback access, giving 111/111 across the two runs. The target build linked
the SRAM BOOTSEL callback without a core-1 launcher/reader. These are source,
host and link observations, not live-device acceptance. No image was flashed,
and no USB, GPIO or RF action was taken.

## Adversarial assessment and repairs

| Finding | Repair and reassessment |
| --- | --- |
| Making runtime source 5 load successfully could accidentally enable the old USB WTP or BLE path, both previously gated only on `runtime_profile_loaded`. | Added explicit source-5 denial at both USB connection/read points and GATT start. The Pico cross-build and transport-contract test passed after the change. |
| A valid source-5 record with an empty standalone store would never start station and could not obtain UTC. | Added a default config overlay only for source-5 pre-clock boot. A host test verifies the selected network and disabled schedule baseline. |
| The old standalone schedule could run after source-5 structural admission. | Boot sends `STOP` for `ConsumerPreClock`; the scheduler retains its suspension through polling. Console mutation stays denied. |
| The AP status would call a healthy source-5 journal a fault or imply that Wi-Fi-only setup was active. | Public status now reports `consumer_preclock` and connection readiness; the setup page remains read-only because blank authority is false. |

Second assessment of the changed graph found no further actionable issue
within this pre-clock, read-only checkpoint. It does **not** assess a live
owner route, crypto validation, source-5 activation, AP/STA resource margins
or target behavior; those components do not exist as an integrated path yet.

## Remaining execution gates

Wire the exact owner claim and session routes, physical gesture, station
trial, trusted UTC, on-Pico trust generation, journal commit, response
reconciliation and post-clock source-5 validation. Then prove owner readback
and the P12.9–P12.12 physical and robustness rows. Until that work is done,
source 5 must remain read-only and P12.8 must not be marked complete.
