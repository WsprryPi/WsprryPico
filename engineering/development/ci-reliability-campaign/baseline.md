# Campaign baseline

Phase 01 completed on November 5, 2026. This is the active comparison baseline,
not a claim that any implementation finding has been repaired. The exact
per-file inventory, hashes, pins, historical CTest timings/results, and CI run
identities are in [baseline.json](baseline.json).

## Identity and reproducibility

Executable Pico source is `c9fd28ef57265c942900bdfe0595f90a31926ff9`; the campaign
parent before execution is `abed2b5ac97f1eeba9acbab26eb6270a3754e976`. Only campaign
Markdown and the backlog differ from that executable base. The initial execution
status/authority edit was an uncommitted README change while inventory ran; the
inventory reads immutable Git objects, not that working file. Original devel is
clean. Current server devel matches the executable base. Pi devel is clean at
`1e15b2485ac6e1b9cbb6ff435afc0f0232528804`; its server tip agrees. Pico's own CI
pins Pi `309db1d85c02ae51e8db1c5cb13583e9ae766b37`, which is compatibility evidence,
not current-peer coverage. SDK/tool/submodule hashes are recorded in the JSON.

Inventory membership is every tracked path under .github/, scripts/, cmake/,
tests/, and src/network/bootstrap_web/, plus the ten exact extra paths in the
JSON. Sorted paths joined by LF with final LF hash to
`cf5ce2800cc73c504e9a44486fcd08d4ce44c20e0b739548c6a665c2214be6da`.
Physical lines count byte splitlines including comments/blank lines. This is a
mixed envelope: 497 files, 85,843 lines, and 4,836,592 bytes. Planning growth is
excluded from active-harness savings and disclosed separately.

| Decision | Files | Lines | Bytes |
| --- | ---: | ---: | ---: |
| DELETE | 0 | 0 | 0 |
| REWRITE | 30 | 7,848 | 548,982 |
| RETAIN | 459 | 76,456 | 4,197,344 |
| HOLD | 8 | 1,539 | 90,266 |

These are decisions to investigate qualified changes, not whole-file removable
budgets. The JSON explicitly enumerates every member; RETAIN is the exact
complement of the named REWRITE/HOLD sets. Original production/contracts outside
the universe remain protected. Embedded orchestration cannot yet be separated
completely from assertions/scenarios, so total harness-code and active-file
reduction denominators remain unqualified. No percentage is claimed for them.

## Owners and obligations

| Slice and actual caller | Context and obligation | Candidate and qualification gate |
| --- | --- | --- |
| Workflow verify → run.py inputs/host_checks/build → CMake/CTest/npm/browser runners | Every maintained push/PR/tag/manual check; fail incomplete work before distribution | Phase 02 evidence/status handling; malformed, missing, failed, and skipped outcomes must refuse |
| run.py execute; bundle.py required_tests/verify; downloader/publisher readers | Preserve exact source/run/artifact and independent linked-image verification | Explicit per-suite completion and finite phase diagnostics; update affected strict readers/tests together |
| FixtureProcess.command/stop; UI server initialization/stop; Python Peer/read/cleanup owners | Imported session and browser runners, endpoint/network CTest entries | Phase 03 ownership/partial-read/late-exit sensitivity; preserve real payload/crypto boundaries |
| Session timeout startup/send/until/finalization | run.py native browser command; idle/absolute expiry, draft/readback/no-write obligations | Phase 04; one selected profile and production handler identity must be observed |
| Remaining browser Cdp/until/startup/cleanup and existing progress/operator helpers | All thirteen native-browser commands and imported current/opt-in contexts | Phase 05; no source/shipped/carrier/assertion loss or authenticated-state sharing |
| UI fixture definitions loop, seven native command invocations | Ten synthetic driver starts per invocation, eight consumed profiles total | Preserve all definitions and original offsets; 70→8 is source-derived only; charge new regressions |
| network_tls_tests.control/time waits; network_tls_driver command loop; mock time_us_64; hostname cancellation observation | Real MbedTLS/handler tests and shipped browser cancellation | Phase 06 ACK/state and controlled-clock seams; exact boundaries and negative oracles retained |
| usb_tool_download_tests.py, installer/bootstrap callers | Documented 39 methods absent from ordinary registration | Phase 07 activates unique coverage, charges full runtime, and rejects required internal skips |
| host_client_interop/network_client_interop CMake libraries | Actual selected companion sources in CTest | Five repeated source compilations; reuse only after flags/includes/ABI and edited-source refusal checks |
| run.py firmware/build and firmware target wiring | Normal, inhibited, compatibility, independently fresh normal build | 175 overlapping object paths are only a ceiling; compare complete inputs and keep independent reproducibility |
| CTest serial properties, fixed UI ports, workflow job graph | Resource ownership, every required context, exact result aggregation | Phase 09 bounded isolation; no reduced frequency, permissive aggregation, or partial bundle |
| ntp_timeout_pair, legacy_pi_config_request, provenance fixtures | No maintained local callers found; possible independent negative/provenance duties | HOLD until import/external-use and replacement-sensitivity reconciliation; unused retirement earns zero credit |
| setup.py and inputs.json | Verified immutable dependencies and companion identity | HOLD cache/pin changes for phases 07/08; no cache hit replaces verification |
| docs/RTD, hardware/reference opt-in trees | Current manual, separate physical/reference evidence | Preserve active contexts; do not run devices to validate source cleanup |

CMake registration owners reconcile to 186 root, 21 network host, eight mDNS,
two host-client, and one network-client entry: 218. Conditional dependencies are
explicitly enabled in canonical CI; local subsets do not imply the full lane.
The workflow has one verification context, not a matrix, and optional manual
publication. Read the Docs owns manual builds. Physical and external-reference
tools are independent opt-in contexts. Every recursively imported producer,
handler, crypto, frame/ACK, journal, and image validator remains protected evidence.

## Historical execution and reliability

[Pico run 42033174494](https://github.com/WsprryPi/WsprryPico/actions/runs/42033174494)
passed on attempt 1 at the executable base; publication was intentionally skipped.
Its 218 CTest entries passed with no CTest skip/failure in 321.26 seconds wall time
(321.2166 seconds summed entry times). Thirteen native-browser commands took
about 67.66 seconds. Verification job elapsed was 1,152 seconds, versus a 576-second
50% threshold. Recorded top-level Ninja actions total 2,668 compilations and
164 links; nested test subprocess work is additional and is not inferred from
lexical assertions or compile_commands declarations.

| Observed interval | Seconds, approximately |
| --- | ---: |
| Dependency acquisition | 68 |
| Host configure/build | 3.48 / 107.04 |
| CTest | 321.59 including runner transition |
| WTP/npm/bundle regressions | 6.06 |
| Lifecycle regressions | 22.79 |
| Native browsers | 67.66 |
| Consumer/inhibited build and inspection intervals | 149.94 / 139.87 |
| Compatibility target | 58.61 |
| Independent build and remaining packaging interval | about 154 |

The last interval is not pure compile time. Remaining configure/setup/upload/job
overhead accounts for the remainder; do not sum overlapping intervals or call
job spans billed cost. No comparable warm baseline or same-source timing
distribution exists. No before/after causal claim or percentile is justified.

[Pi run 42033231271](https://github.com/WsprryPi/WsprryPi/actions/runs/42033231271)
passed both actual network and USB jobs using Pico c9fd28ef and Pi f1413634.
Current Pi devel differs from that Pi revision only in the release punchlist.
These results do not qualify any later changed candidate.

The thirty Pico records span November 2–5, 2026: 21 successes, six failures, and
three cancellations; all report attempt 1. Two repeated-source pairs are different
PR/manual events, not equivalent reruns. Failed records include unsupported
manual-input refusals, companion/control expectation mismatches, and browser
timeout/target failures. Those signatures do not establish a harness-flakiness
rate or prove root causes; retain unresolved classifications. A passing rerun does
not erase a first failure. Devel protection API currently reports Branch not
protected and applicable branch rules are empty; phase 02 must establish actual
enforcement rather than treating workflow success as a merge requirement.

## Remaining measurements and adversarial closure

Phase 04/05 must measure selected owned starts and actual handler routing, including
all new regression starts. Phase 06 must establish acknowledged fault/transition
states and qualified boundary assertions before replacing waits. Phase 07 must
measure added suite execution and prove intended current-pair refusal paths.
Phase 08 must compare real compiler inputs/invalidation and count actual work.
Phase 09 must compare equivalent current-coverage cold runs, report resource and
transfer overhead, and distinguish local scheduling from hosted status/artifacts.
All phases retain local/cumulative deltas without silently changing this baseline.

Adversarial assessment corrected three accounting hazards: documentation-only
source revisions are not new runtime behavior; compile_commands entries are not
executed compilations; seventy-to-eight starts are not whole-CI savings. Counts
and membership sums were independently reconciled against immutable source and
existing reports. Ambiguous semantic denominators remain explicitly unestimable.
Read-only Git/source/API inspection and existing archive parsing completed;
no new behavioral tests, builds, dependency installs, or device operations ran.
