# Phase 09 acceptance

Accepted Pico `1a383a993833f05ab0ea574286dc5eec8ba4d09b` with companion
`d3ffc3b26d50f55f205382bb5aac7cdfee054d99`. Both feature branches are pushed;
original devel checkouts and remote tips remain Pico c9fd28ef and Pi 1e15b248.
Delivery is on the feature branches, with draft PRs
[Pico 16](https://github.com/WsprryPi/WsprryPico/pull/16) and
[Pi 469](https://github.com/WsprryPi/WsprryPi/pull/469). No merge or deployment.

## Scheduling and preserved work

CTest uses two workers. All existing RUN_SERIAL exclusions, fixed-port ownership,
timeouts, registrations, triggers, required statuses, browser contexts, and fresh
independent reproducibility builds remain. Native network/interop 18443/18444 and
the session pilot stay exclusive. Private profiles/journals/scratch, ephemeral
startup ports, and separate native-profile port ranges remain isolated. The
selected-source compilation test already caps its nested build at four workers;
the generated-control refusal stops before compiling. No job split or object
cache is introduced. Additional setup/download/build/transfer aggregation without
a demonstrated graph benefit would add work.

The predeclared warm local ABBA window at Pico 4117a37c / Pi 28915d31 passed all
214 available CTest registrations and 47 available framework summaries each time:

| Order | Workers | CTest wall seconds | Outcome |
| --- | ---: | ---: | --- |
| A | 1 | 209.56 | Passed |
| B | 2 | 170.11 | Passed |
| B | 2 | 170.28 | Passed |
| A | 1 | 209.57 | Passed |

Mean wall time decreased about 39.37 seconds (18.8%). This small, controlled
Docker window is not a hosted speed guarantee or a flake-rate estimate. The
container exposed 18 CPUs, no per-container CPU/memory quota, and a reaping init;
the hosted baseline remains Ubuntu 24.04 with its recorded resources. Each trial
restored the same scheduler-cost seed, reconciled exact commands/results/counts,
and checked frozen paired inputs. Ten framework suites and 20 registrations need
canonical SDK inputs and were unavailable locally; the full policy still refuses
that subset. Later standalone lifecycle and hosted setup fixes do not relabel the
window's source identities. The exact observations, seed digest, file hashes,
added-code costs, and missing local contexts are in
[phase-09-measurements.json](phase-09-measurements.json).

## Qualified failures and adversarial closure

- Actual SIGTERM previously left a detached command child alive with no receipt.
  Ownership now covers signal arrival during spawn registration and cleanup;
  repeated cancellation cannot interrupt finalization or mask the original error.
  Actual READY-gated cancellation reaps the child and records failure. The child
  retains normal signal behavior. All 24 execution regressions pass.
- Real CTest probes qualified lock exclusion, a two-worker peak, early failure,
  a stalled worker, cancellation, and cleanup. Deliberately allowing three workers
  exceeded an independently counted budget and failed. Every observed owned
  worker was reaped; no partial success receipt qualified.
- The former real 21-second startup stimulus now holds an observed child state,
  advances an injected clock to 21000 ms, and releases actual page discovery.
  Production readiness and its 60000-ms budget remain. A restored 20000-ms cutoff
  reaches the intended startup failure without a real 21-second delay.
- The initial a8950ed3 comparison passed three observations, then the closing
  serial trial failed HOST_DRY_RUN_MISSED (134800-ns lateness). That window is
  invalidated, not filtered. Its old diagnostic cannot distinguish the exact
  predicate. Deterministic real-engine checks reproduce both possible fixture
  hazards: a fractional UTC instant can leave a one-nanosecond window, and torn
  wall/monotonic correlation can violate mapping. Pi now advances one logical UTC
  epoch with monotonic time and chooses a complete future UTC second. Actual
  engine/uncertainty/window policies remain. Projection, backward/overflow,
  narrow-window, late-start, and torn-clock checks pass. Three actual compiled
  mutants reach their independent clock/window/mapping assertions.
- The actual companion workflow exposed cwd-dependent lifecycle worker paths at
  Pico 4117a37c. Module-relative paths and observed closed-child diagnostics now
  refuse the real missing-worker cause. All 40 lifecycle cases pass from both
  repositories; restored relative launches fail at that exact oracle. Cancellation
  requires live owners, and abrupt-exit coverage checks actual SIGKILL termination.
  All four remaining Pico browser invocations also pass from the Pi directory.
- A PR USB job exhausted its 15-minute budget during duplicate APT CMake/Node
  downloads. The named runner supplies those tools outside dpkg. The USB lane now
  checks executable availability, versions, and OpenSSL flags, and retains every
  actual configure/build/client/negative/production pair command. Real Linux tool
  qualification passes; unusable CMake/Node/pkg-config each preserve exit 17.
  All 12 execution-graph regressions pass. The latest USB job took 96 seconds,
  with a one-second preflight, versus 808 seconds and 692 seconds of dependency
  installation in an earlier successful run. These different-source single-job
  observations are not a controlled whole-workflow speed comparison. The 15-minute
  job budget was not increased.
- Downloader and standalone installer share trusted Actions provenance checks:
  repository/workflow/run/attempt/source/branch, unique job IDs, and exact run/job/
  check-run URIs. Artifact origin is bound before transfer. Wrong or missing
  metadata, partial upload, corrupt archives, failed aggregation, and false
  producer names refuse. All 70 bundle and 115 installer cases pass; immutable
  published receipts remain readable after Actions expiry. Deployment/control/
  storage version boundaries do not change.

## Intended source pair and hosted evidence

Both full checked-in Pi recipe command sets passed at the accepted source pair:
actual Pico usb_management_driver; Pi wtp-network-runtime-test,
wtp-network-interop-test, wtp-config-interop-test, wtp-usb-pair-client-build,
wtp-usb-management-test; and both USB UI producer/pair scripts, including required
GPIO drive coverage. BACKENDS=simulated, ANCILLARY_GPIO=0, SUDO=, explicit
PICO_SOURCE/MBEDTLS_SOURCE, and WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 were selected.
Mbed TLS is 0bebf8b8c7f07abe3571ded48a11aa907a1ffb20; recursive framework is
dff9da04438d712f7647fd995bc90fadd0c0e2ce. No network prerequisite was skipped.
Exact commands and logs are build/campaign-phase09-qualified-pair.sh and its
qualified-network, qualified-usb, and qualified-source-pair logs.

[Canonical run 42123196548](https://github.com/WsprryPi/WsprryPico/actions/runs/42123196548)
passed attempt 1, using actual merge d26376f277ae4b763f3b527f6dc71197e8c707b3
(parents c9fd28ef and 1a383a99; tree equals the feature candidate). Independently
verified immutable audit 13460620996 and firmware 13461515078 archives bind all
234 CTest registrations, 57 framework summaries, 27 command records, source/tree,
inputs, receipts, file hashes, policies, and UF2 payloads. Linked-image inspectors
passed hosted CI; independent inspect=False verification does not rerun those
target tools. Verify job elapsed 994 seconds; summed command spans 855.478 seconds.
These are observations across unlike inputs/runners, not causal whole-CI savings.
Top-level stage logs total 2496 compilations and 156 links; nested test builds and
qualification subprocesses are additional. The 50% whole-job/compile/link/code
reduction targets remain unmet. No requirement was weakened to reach a quota.

[Exact-pair Pi run 42123604429](https://github.com/WsprryPi/WsprryPi/actions/runs/42123604429)
passed all nine jobs with Pico 1a383a99 and Pi d3ffc3b2. Trusted API provenance and
actual checkout/execution logs bind that selection. Foreign-directory lifecycle
coverage is 35/35 in the Pi recipe (the additional five contextual-help cases are
part of Pico's 40-case lane). The companion PR run
[42122599642](https://github.com/WsprryPi/WsprryPi/actions/runs/42122599642) also
passed; its default Pico devel selection is separate evidence.

Current accepted runs are first attempts for their respective candidates. Phase
09 required three Pico candidates and two companion commits to close qualified
findings. Earlier API-green runs a8950ed3/4117a37c do not erase their local/companion
failures. Old Pi manual 42118908771 failed, and PR 42118910865 was cancelled;
cancellation requests found both already complete and interrupted no jobs.
Do not infer general reliability or an exhaustive historical failure rate.

Strict current-candidate verify from Actions app 15368, PR merging, administrator
enforcement, no force push, and no deletion were read back on Pico devel. Main
and unrelated settings remain unchanged. Both feature worktrees and both original
devel checkouts are clean before this documentation-only acceptance update.

Documentation impact: Pi's development guide describes logical fixture clocks,
runner-provided tools, and software-only evidence limits. Pico engineering guide
consolidation and obsolete-fixture decisions belong to phase 10. Operator behavior,
product interfaces, physical timing, devices, host services, and RF are unchanged.
