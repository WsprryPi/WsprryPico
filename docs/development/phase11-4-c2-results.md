# Phase 11.4 C2 completion

The remaining C2 deployment and Chrome Loaded observation passed on 2026-09-09.
The reviewed browser safeguards are installed and the actual page showed a
production-owned Loaded job with matching USB identity and disabled foreign
controls. Together with the earlier Armed/Running/Complete and foreign mutation
cases in [browser/production coverage](browser-production-coverage.md), this
closes bounded C2 acceptance. Phase 11.4 as a whole remains open.

The [execution prompt](phase11-4-c2-prompt.md) was prepared before deployment and
executed under the user's existing inhibited-device, browser, test and bounded
service-pause authorizations. No production source change was needed in this
continuation. The installed WsprryPi application and its configuration were
preserved; the existing isolated corrected client supplied production evidence.

## Identity and deployment

- Pico 2 W / RP2350 on wspr5, USB serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, Console `-if00`, WTP `-if02`.
- Standard inhibited firmware source `23ac5b1aee668a671ba494a05c555b89928faa2c`,
  embedded revision `23ac5b1aee66`, engine `inhibited-standalone-simulator`.
  UF2 SHA-256 `a7013feccf36abb9c9da17db057d4d12158942a019d74d787f56336f64a6c8f2`;
  ELF SHA-256 `3da56dd471c2848da9c83fa14cbe3a8efd819e948f9542ca7ae2f91523963690`.
- Before flash: revision `f88fa71eef5e`, boot
  `b3cf6adbca443d954750abaa161cde18`. After flash and throughout these cases:
  boot `1c4730e38aa4e6f8549cbc8c475846bd`, normal boot, deployment identity
  matched. The serial-selected existing picotool verified programmed data.
- Chrome used certified `wsprrypico-0a60df.local:18443`; fresh USB address
  `192.168.1.47` supplied the production TCP destination with independent expected
  DNS identity. Existing CA and separate browser/controller credentials remained
  unchanged. Server SHA-256:
  `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
- Authenticated TLS 1.3 GET `/app.js` matched the reviewed source byte for byte:
  SHA-256 `764dbc97bb652aecb05121a32a2662e3fb78ce00c6eda01a37010798f75f2439`.
  Chrome was reloaded from the device before observation.
- Unchanged isolated WsprryPi source
  `923ab570fe53ef2ccca7d12e519c9dc36adf7e93`, binary SHA-256
  `993ad62def487e5f03d82a5a7a1f5f82b972b16bd36eaa5b0d9a8c13a7166323`,
  at `/home/pi/wsprrypi-browser-coverage-20260909/src/build/bin/wsprrypi-browser-coverage`.
  Source cleanliness and executable hash were verified before both invocations.

## Physical observations

Exactly two finite production QRSS `E` plans were loaded, each nominally 20 seconds
at 3,570,100 Hz. The inhibited engine never enabled RF output. All times below
are UTC. Device/boot identity was checked independently over USB.

| Case | Observation and result |
| --- | --- |
| Reloaded idle page | At 13:42:15, Chrome showed empty, Inactive, Available, synchronized clock and the configured hostname; owner actions were disabled. |
| Production Loaded | Job `155b9fbd1b857e740000000000000001`, owner `71afc69008f0edce80208efda2f35f3c`. Existing host gdb temporarily stopped the actual client at `TransmissionController::execute_prepared()` after LOAD and before ARM. USB Console and WTP both showed Loaded; Chrome at 13:44:01 showed the same job/owner, Inactive, and disabled Abort, Release, submission, Save, Restart and Wi-Fi controls. |
| Held job cleanup | The automatic 20-second timer measured 20.0004 seconds including scheduling overhead, within the 60-second lease maximum. No debugger variable/code/clock change occurred. On resume, the client rejected the past start with `WTP start misses device lead time or horizon`; `arm_handed_off:false`, outcome failed, authoritative aborted job and cleanup OK. USB then showed empty, inactive, null owner/job. This intentional failed run is retained and is not counted as normal completion. |
| Unpaused production | Job `1003dfb770957aa20000000000000001`, owner `2a2a2f2ef753c8fcf7101214a6f0e617`, requested start 13:45:26. Production history contained Loaded/Armed/Running. Chrome showed Running at 13:45:27 and Complete at 13:45:46 with matching job/owner, Inactive and disabled foreign controls. The terminal report had outcome complete, ARM handed off, no adjustments, authoritative complete and cleanup OK. USB then showed empty/inactive/unowned with its matching complete terminal record. |
| Failed browser read | After independent idle cleanup, Console WIFI OFF was held for 45 seconds with automatic WIFI ON in a finally path. Chrome Refresh timed out and showed `Unknown · read failed`, RF/owner/clock/network/hostname/discovery Unknown, and disabled mutation controls. The prior job result remained explicitly timestamped as an earlier observation. No unknown state was injected into the live page. |

The unpaused Armed refresh completed after the start and therefore counts as
Running, not as a new Chrome Armed observation. The earlier actual Chrome Armed
case remains the evidence for that interval. The deliberately extended Loaded
interval proves concurrent display and authority behavior, not normal scheduling
latency. Earlier successful `NOT_OWNER` ABORT/RELEASE cases remain independently
recorded; no new foreign mutation was needed to repeat them.

## Adversarial assessments

**Round 1 — challenge execution and cleanup.** Reviewed exact source/image/client
binding, independent boot/owner checks, debugger breakpoint placement, lease and
fixed start, service restoration and device cleanup. Found that the private
runner could know the debugger PID before discovering its inferior, and that its
final Console check alone did not prove null WTP ownership. Before execution,
added exact-executable child discovery and an independent final WTP status/boot/
owner/output check. Both runs exercised the final verification and restoration.
The held run's missed deadline remained a failure with authoritative cleanup;
it was neither rescheduled nor replaced in the evidence.

**Round 2 — challenge deployment and claims.** Verified deployed JavaScript bytes,
fresh actual Chrome DOM, matched Loaded IDs against independent USB, reviewed
production terminal records and unchanged installed hashes. Corrected the
attempted Armed observation to Running because its response arrived after start.
The controlled failed read exercised real deployed unknown-state controls;
deterministic tests separately cover unknown output and lost CLAIM/LOAD/ARM
followed by failed reconciliation. Their results are not represented as physical
lost-reply qualification. The timer's measured overhead is retained above rather
than claiming an exact wall-clock upper bound of 20.0000 seconds.

**Final assessment.** Rechecked the scoped documentation and retained records
against these limits. No additional actionable production implementation finding
remains in C2. No new source repair, protocol change or interop-pin update was
necessary. Intermittent connectivity/watchdog behavior and overnight memory
reliability remain unresolved; this short successful run cannot close them.

## Validation and final state

The affected host suites `network_tests`, `network_browser_tests`,
`network_tls_tests`, `network_11_1_interop` and
`inhibited_network_acceptance_tests` passed **5/5**, 33.43 seconds. Actual TLS tests
ran outside the sandbox, sequentially where ports were shared. Standard inhibited
firmware cross-build and `scripts/check_standalone_image.py` passed, including
16 KiB stack allowance, heap separation and reserved journal boundaries. Existing
SDK/toolchain were used. No RF build was deployed.

Both bounded service pauses finished in under two minutes. Finally paths restored
`wsprrypi.service` to active and checked original installed executable/INI hashes;
provider output was explicitly false before, during and after each pause. USB
proved inactive/unowned state independently of process exit. Station
AA0NT/EM18/power20, disabled 120/0 schedules and watermark
`1788714601000000000` were preserved through flash and both jobs. Time server
remains `pool.ntp.org`. The subsequent Wi-Fi off/on check preserved the same boot,
station, schedules and watermark and restored Wi-Fi enabled. Chrome recovered
to Connected, empty, Inactive and Available at 13:48:40 UTC. Final installed
executable and INI SHA-256 remained respectively
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273` and
`e4158b2b041355f8cffea0388c8ce286c37d2a66d2d3a6e9c85e3af5f238bbc8`.

Private source manifests, test/build/flash logs, browser observation summaries,
served asset, USB evidence and helpers remain ignored in `build/phase11-4-c2/`.
The private production archive `remote-evidence.tar.gz` has SHA-256
`e142b576b52b6ba11caafb6f2f6f82efbd0b0eed4038bbcc0a064ac843d13d01`.
No credentials, generated firmware or raw private configurations are committed.

## Documentation Impact

Added the execution prompt and this result/review record; updated C2 in the joint
matrix and linked the prior deployment/Loaded limitations to this continuation.
Existing runtime behavior was deployed, so no operator setting or command changed
and no companion repository edit is needed. All other matrix gates keep their
previous evidence status, including UTC negatives, DHCP/link faults, conflict/
second-board tests, certificate cases and lost-reply/recovery scenarios. Phase
11.5 resources and Phase 11.6 RF qualification are separate.
