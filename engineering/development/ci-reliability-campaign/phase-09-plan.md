# Phase 09 predeclared qualification

Reliability and complete execution govern acceptance. Candidate scheduling uses
CTest `--parallel 2`; preserve every existing RUN_SERIAL exclusion, test timeout,
registration, framework count, standalone browser command, trigger, required
`verify` identity, artifact contract, and fresh reproducibility build. Do not
split jobs: setup, SDK/toolchain verification, and artifact aggregation would be
duplicated without evidence of a net benefit.

Resource map: the seven native network/interop contexts own fixed 18443/18444,
shared generated test credentials, and paired drivers; existing RUN_SERIAL keeps
them exclusive across CTest. The session pilot also remains RUN_SERIAL. Native
profile qualification owns disjoint 19439, 19459/19461, and 19479–19488; standalone
browser contexts retain sequential 19139 ownership (pilot 19149). Chrome startup
uses private profiles, observed gates, and ephemeral ports. Asset, companion-source,
package, generated-control, and installer fixtures use private scratch directories.
Other native C/C++ cases own process-local state. No mutable compiler/object cache
is introduced. Keep CTest concurrency at two, below the existing four build workers.
Full canonical registration and exact framework completion remain mandatory.

Before measuring, freeze implementation and case inventory. Run ABBA locally:
serial, two workers, two workers, serial. Use the same built candidate, registered
cases, dependencies, container resources, private per-test scratch, and output
limits. Do not run other CPU-intensive campaign work during this window. Retain
all four first-attempt results, individual durations, and XML; compare paired
serial/parallel observations without treating small samples as a reliable flake
rate. No speed threshold or retry-until-green. Any source change or failed run
invalidates acceptance of that window and must be explained before a fresh window.
Canonical hosted timing is separate observational evidence, not a controlled
comparison against earlier phases with different coverage.

Adversarial qualification includes an observed cold-start clock crossing the old
20-second cutoff; actual SIGTERM after READY and during spawn registration; owned
worker cleanup; explicit serial/lock and two-worker budgets; stalled/failing and
cancelled CTest workers; wrong workflow/run/attempt/source/job/URI/repository and
artifact provenance; existing partial archive/upload/aggregation refusals. Verify
all affected suites, both actual production source-pair recipes, a first-attempt
canonical run, downloaded immutable audit/deployment evidence, and unchanged strict
required-status settings. Keep completed historical bundles readable and Actions
expiry support. Record any deliberate failed/cancelled diagnostic separately.

## Revised window after qualified failure

The first frozen candidate a8950ed3 produced serial 204.21 s, parallel 161.45 s,
parallel 161.93 s, then a failed closing serial observation (187.99 s; 212/213
passed). The real production interop reported HOST_DRY_RUN_MISSED with 134800 ns
poll lateness and a 1-ms uncertainty allowance. The old diagnostic cannot identify
which predicate failed. Do not accept that window, discard the failed sample, or
infer the parallel setting caused or repaired the failure.

Deterministic production-engine checks reproduce two existing fixture hazards:
a fractional timestamp can leave a one-nanosecond UTC-second launch window, and
independently sampled/changing wall/monotonic correlation can fail strict mapping.
The selected Pi fixture now anchors one logical UTC epoch to monotonic progression,
selects a complete future UTC second, retains true late/narrow-window and bad-clock
refusals, removes the unused host-time scaling override, and logs the exact window
and mapping on a miss. Product engine and uncertainty/window policy are unchanged.
Clock projection, overflow/backward refusal, and actual engine policies have
independent checks; three deliberate mutants reach their intended assertions.

Freeze the repaired Pico candidate and companion 28915d31026b2c9a97f451c01d48820fb52c097f on
codex/pico-ci-reliability-companion. The original Pi devel remains unchanged.
Repeat a new full ABBA window with the same acceptance rules, now 214 available
local registrations (canonical 234), including the new actual-engine clock case.
Hash both tracked source trees, check clean paired refs throughout, and restore
the same owned scheduler-cost seed before every observation. Keep all first-window
logs/results as failure evidence. No same-source retry or tolerance expansion.

## Hosted companion findings after the completed window

The repaired 4117a37c / Pi 28915d31 ABBA window completed all four first attempts:
209.56, 170.11, 170.28, and 209.57 seconds (214 local CTest registrations, 47
available frameworks). Its canonical Pico run 42118794855 passed 234 registrations,
57 frameworks, and 27 command records; immutable archive digests and full bundle
receipts were independently verified. These records retain their actual source
identities, not the later fixes described here.

The actual Pi workflow 42118908771 selected Pico 4117a37c and exposed two lifecycle
regressions invoked from the companion working directory. Relative worker paths
resolved in Pi rather than Pico; the cases waited for nonexistent initialization.
The test module now resolves its own worker URL and observes closed-child status
plus bounded stderr. A real missing-worker regression refuses on its actual exit
and diagnostic. Restoring either relative launch fails at that qualified oracle.
All 40 lifecycle cases pass from both repository directories. The additional case
is standalone browser-lifecycle coverage, not a CTest registration; no CTest command,
resource exclusion, or scheduling setting changes after the completed window.

The same intended-pair run's USB job passed. PR run 42118910865's USB job exhausted
its unchanged 15-minute budget downloading duplicate distribution CMake/Node
packages. Trusted logs show the exact archive transfers/retries, while the named
Ubuntu image inventory provides CMake 3.31.6 and Node 22.23.4 outside dpkg. Replace
only that USB lane's redundant installation with executable/version/OpenSSL checks;
keep every actual CMake configure, compile/link, client, negative, and production
pair command. The real Linux preflight passes; injected unusable CMake, Node, and
pkg-config each preserve exit 17 without fallback. All 12 existing execution-graph
regressions pass. The pipeline's actual subsequent builds remain the compiler/
header/link qualification; tool inventory is not byte-reproducible system provenance.

The final paired companion ref is d3ffc3b26d50f55f205382bb5aac7cdfee054d99 on the same feature branch.
A new full source-pair execution and canonical/companion hosted qualification must
bind the final Pico source and this companion. Preserve older failure/cancellation
classifications; superseded diagnostic runs are not accepted successes. Local
scheduling observations remain explicitly scoped to the completed 4117a37c /
28915d31 window; later standalone-lifecycle/setup changes are separately charged.
