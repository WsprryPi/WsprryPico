# Phase 02 execution evidence

## Result path

The unchanged workflow `verify` job invokes `run.py`; every owned command now
records source, workflow run/attempt, argv, working directory, monotonic elapsed
time, exit, completion context, and a hashed log slice. Exit-zero alone does not
qualify Node, Python, WTP, CTest, or native browser suites. Each requires its
actual nonempty completion summary or the result emitted after its assertions.
CTest inventory must match exact unique names and must contain no failed or
required skipped cases. Native contexts retain real handlers and crypto.

The audit sidecar is `ci-execution/1`; a closed `ci-execution-policy/1` selected
from the frozen producer source names required contexts. Bundle verification
revalidates identity, shape, required contexts, hashed command output, and
completion facts. There is no deployment-manifest format change. Frozen older
producers without this sidecar policy remain verifiable; a Git read error does
not select that case. The successful whole-run requirement in `download.py` and
manual publication in `publish.py` remain enforced by their existing tests.

A command timeout is a failed outcome. The enclosing 60-minute job budget is a
finite hang watchdog, never a readiness or performance assertion. Owned command
groups are terminated and the leader reaped on errors. Primary, cleanup, and
evidence-persistence failures remain visible together. Failure artifact uploads
retain logs, execution receipts, registered names, and JUnit. An upload failure
cannot turn the already failed verifier green.

## Adversarial findings and corrections

- Empty/duplicate/mismatched Node summaries, internally skipped Python cases,
  mismatched CTest names, and absent browser completion facts now refuse.
- Last leader exit with a live owned descendant is reproduced with an observed
  child READY handshake; it fails instead of becoming a successful command.
- Absent or empty submission/section check lists refuse. A log-read failure
  cannot hide the original child failure.
- A controlled watchdog plus signal denial preserves both failures. A real
  exit-17 plus simulated full evidence storage also preserves both failures.
- A wrong-attempt receipt remains rejected after an attacker reseals the bundle
  inventory. Exact source/run/attempt and command output are independently bound.
- Synthetic distribution/download tests required explicit frozen-old-producer
  adapters after the new policy became committed. Those adapters isolate their
  pre-existing manifest scenarios; dedicated tests exercise missing and valid
  new-sidecar verification, wrong attempts, malformed policies, and Git errors.
- Current Pi's strict READY reader exposed Pico's alias of its diagnostic driver
  as the companion server. The adapter now compiles the selected Pi server and
  TCP harness with actual candidate Pico handlers. No readiness grammar is
  relaxed. The CI companion pin selects current devel
  `1e15b2485ac6e1b9cbb6ff435afc0f0232528804`; this necessary pair dependency was
  pulled forward from phase 07, which still owns coverage-gap closure.

## Local checks

Original Pico devel: `c9fd28ef57265c942900bdfe0595f90a31926ff9`.
Pi selected source: `1e15b2485ac6e1b9cbb6ff435afc0f0232528804`, clean.
Candidate implementation evolves on the campaign feature branch; the hosted
accepted source and final paired evidence will be recorded below after success.

- Python `tests/ci_execution_tests.py`: 12 passed on macOS and Linux.
- Python `tests/ci_bundle_tests.py`: 59 passed on macOS and Linux. Includes the
  distribution, download, manual/optional publication, and frozen-source cases.
- Native Linux browser probes: all 13 invocation contexts accepted their actual
  completion evidence against the candidate production bootstrap/session drivers.
  Logs/results retained under ignored `build/campaign-native-audit-2`.
- Linux `node --test tests/ui_process_cleanup.test.mjs
  tests/chrome_startup.test.mjs tests/contextual_help_cleanup.test.mjs`: 28 passed,
  zero skipped/cancelled/todo. The deliberate observed cold-start stimulus remains.
- Bootstrap `npm test`: 26 passed, zero skipped/cancelled/todo.
- `scripts/validate_wtp_contract.py`: 23 schema, 7 raw JSON, 1 framing,
  and 8 transition cases passed.
- Host CTest initially passed 198/199; the single failure reproduced the adapter
  mismatch above. This local configuration lacks the 20 SDK/harness-dependent
  registrations, so it is not represented as the full canonical suite. The repaired
  current-source `network_11_1_interop` then passed in 102.36 seconds; the other
  198 tests had passed with the same unmodified production handlers.
- Actual USB commands: `make -C <Pi>/src wtp-usb-pair-client-build
  wtp-usb-management-test SUDO=` and `WSPRRYPI_GPIO_DRIVE_REQUIRED=1 node
  <Pi>/WsprryPi-UI/tests/wtp_usb_pair_test.js
  <Pi>/src/build/wtp-network/wtp_usb_pair_client
  <Pico>/build/campaign-host/usb_management_driver`: passed, including negotiated
  schema, persistence, strict limits/types, boot binding, refusal-before-writes,
  and all GPIO drive strengths.

Linux checks run as nonroot UID 501 in the isolated campaign container. This
local environment uses Debian/GCC 12/Node 22 and the repository hash-pinned Python
dependencies. Canonical Ubuntu/GCC/Node versions require hosted evidence.
MbedTLS is the clean exact `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` dependency.
A certificate-copy permission failure on macOS-backed storage was resolved by
using a native Linux build directory (`WTP_NETWORK_BUILD_DIR=/home/campaign/pair-network`).
A local fixed-port overlap between two owned integration invocations was an
orchestration error; the affected run remains unsuccessful and is rerun only
after the conflicting owner exits. Phase 09 must preserve port isolation.

## Remote enforcement and pending acceptance

The prepared [enforcement policy](../software-build-ci.md#merge-gates-and-performance-observations) was applied under the
standing authority. Remote readback confirms devel requires strict/up-to-date
`verify` from GitHub Actions application 15368, enforces administrators, requires
a PR, and prohibits force pushes/deletion. Optional `publish` is not required.
No unrelated branch or repository settings changed. Draft PR:
https://github.com/WsprryPi/WsprryPico/pull/16.

Both actual local source-pair suites are successful: the runtime recipe completed
34 TLS cases and the plain/runtime cases; the serialized network/config recipe
completed IPv4 rebind, idle lifetime, real scheduled execution, replay, all three
carriers, journals, current policy, GPIO, GPS/Si5351, and native Pi runtime plus two
shipped-browser crypto contexts. Exact commands and logs are retained in ignored
`build/campaign-network-native.log`, `build/campaign-network-pair-final.log`, and
`build/campaign-usb.log`. The selected implementation is Pico
`5aa416a1ccb3d09476eed18df400f91f52107426` with the final receipt/test-only edits
subsequently committed as `7d41f381b134ec42da46e5afe9941e6f90bf10bd`; Pi remains
`1e15b2485ac6e1b9cbb6ff435afc0f0232528804`. No production handler differs between
those Pico candidates.

Canonical candidate [run 42064334122](https://github.com/WsprryPi/WsprryPico/actions/runs/42064334122)
passed for feature head `7d41f381b134ec42da46e5afe9941e6f90bf10bd` and its actual
PR merge source `1c068c0d34a7389e5f83e74ecc9f1fb3b72b9227`. The downloaded audit
independently passed the current strict receipt/log validators: 28 successful
commands, all 18 required host contexts, and 219 exact CTest names with no
required skips. The canonical job itself passed the linked-image, inhibited,
compatibility, fresh reproducibility, bundle, and provenance gates. The publisher
was intentionally skipped. Verification took 950 seconds; recorded child command
wall time totals 835.345 seconds. This is a single observation, not an attributed
speed improvement over the baseline's different runner instance.

The required hosted pair jobs also passed in
[Pi run 42062554127, attempt 2](https://github.com/WsprryPi/WsprryPi/actions/runs/42062554127/attempts/2):
network job 127389906711 and USB job 127389901037. Their selected Pico is the
phase's earlier `86f8a13818115d61c1b044038e83609de96da4dc`; later Pico changes in
this phase affect the CI runner/receipts, companion test adapter/pin, and tests,
not the production handler source exercised by that pair. The complete local
recipes above cover the final intended production source pair as well.

The first USB job was cancelled during downloads from azure.archive.ubuntu.com,
before any source-pair checks ran. The targeted rerun passed in 137 seconds;
no integration assertion, deadline, or job budget was relaxed. The full Pi run
still has an unrelated cancelled 30-minute Ubuntu release-build job and is not
represented as a successful whole workflow. This separate scheduling observation
is retained for phase 09's investigation, not used as accepted paired evidence.

Phase 02 is complete. The additional receipts, validators, source-pair fixture,
and regressions add maintenance/runtime; this correctness cost is charged to the
campaign rather than hidden as savings. Existing reduction targets remain
subordinate to reliability and efficacy. Phase 03 is in progress.
