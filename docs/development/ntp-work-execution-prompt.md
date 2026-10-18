# NTP work in three parts

Execute only item 4 of the [Consolidated backlog](consolidated-backlog.md), in
this order: persistent standalone manual PPM; NTP filtering and UTC rate
discipline; NTP-derived RF calibration. Implement the three bounded parts,
record results and evidence closeout, perform independent adversarial review,
repair actionable findings and repeat affected checks/review, then commit and
push the scoped result.

This saved prompt does not start implementation, observation collection or
hardware testing. Preparing and publishing it leaves item 4 and its three
subitems not started.

## Entry and scope

Work in /Users/lbussy/GitHub/WsprryPico. Read AGENTS.md, README.md, CONTRACT.md,
docs/architecture.md, docs/development/README.md and the consolidated backlog
before implementation. Print the complete Finish now section, preserving its
order and NTP Work grouping, with ✅ finished, ⏳ in flight and ▧ not started.
That document is the sole authority for current and future work; do not create
a second roadmap or pending-work list.

Inspect branch, full HEAD, upstream, live remote devel tip, staged/unstaged
changes and untracked work. At publication preflight, devel and the queried
remote tip were fd508371bf7d2f396f7b8ad485a26651144d326e, including completed
contract reconciliation; unrelated documentation/cleanup edits remained in
progress. Refresh actual state and preserve all concurrent work. Recorded
identities are not reset targets. Mark only item 4 and the subpart actually
being executed ⏳ when execution starts.

Only WsprryPico implementation and publication are authorized. Other family
repositories are read-only references; do not modify WsprryPi, WsprryPi-Docs,
installed services, chrony/gpsd configuration or a shared harness. Do not invoke
repository cleanup or erase historical evidence, failures or accepted limits.

Keep standalone operation, configured-server NTP acquisition, one JobService
and local complete-job execution. Automatic NTP-server discovery, preference,
server ranking and new failover policies remain future work. A configured
local NTP host is optional; WsprryPi must not become a prerequisite. Preserve
the existing configured hostname/IPv4 behavior and default pool.ntp.org.

Direct GPS UTC/PPS, PPS pin allocation, Si5351/CLK2 feedback, external clock
switching, amplifier/LPF changes, a broad UI redesign, deployment CI, installer
and release publication are excluded. RF calibration here concerns carrier
NCO correction; symbol-duration/sample-count correction is a separate slice.
Do not change hardware tick rate, PLL settings or the nominal RF sample clock
to implement these three parts.

## Source and evidence baseline

Read the [clock-rate calculation methods](gpio-time-calibration-research-methods.md)
and current NTP implementation/diagnostics. Do not apply fitted PPM figures as
RF calibration or treat sparse INFO snapshots as a complete stream of
source-labelled NTP observations. Preserve the independent measurement gates.

Trace these current sources and the corresponding registered tests:

- src/time/sntp.hpp and sntp.cpp; src/time/server_lookup.hpp; the actual lwIP
  send/receive and polling paths in src/standalone/pico/adapters.cpp.
- src/time/observation.hpp, utc_discipline.hpp/cpp, controller_time.hpp/cpp and
  usb_time_source.hpp/cpp: observation authority, source arbitration, uncertainty,
  age, disagreement and qualified controller/USB/browser time.
- src/standalone/wtp_profile.hpp, scheduler.cpp, config.hpp/cpp and persistence/
  progress; src/wtp/job_service.hpp/cpp: schedule admission, pair consistency,
  source age, UTC windows, ARM conversion and explicit frequency-adjustment consent.
- src/rf/waveform.hpp/cpp, stream_engine.hpp/cpp, worker.hpp/cpp and
  src/rf/pico/worker.cpp: correction arithmetic, prepared plans, launch guards
  and the RF core's private clock copy.
- src/standalone/pico/main.cpp; src/application and src/network configuration,
  resource, capability and UI adapters; CMake, presets and maintained helpers.
- The exact retained pinned Pico SDK clock/tick/timer/PLL and PIO source used
  by the target build. Confirm its revision rather than relying on SDK defaults.

At preparation, Config has no persistent manual PPM field. The RF engine has
an idle-only signed correction setter and a ±100000 ppb carrier range. Positive
source-clock error reduces the NCO increment. UtcDiscipline is offset-only:
it projects one UTC nanosecond per raw monotonic nanosecond and ages uncertainty
with an assumed 50000 ppb allowance, not a measured correction.

The standalone clock profile is synchronized through 90 seconds and in
holdover through 180 seconds; launch source age is at most 90 seconds and
uncertainty at most 500 ms. Preserve these policies and each job's tighter
requested limit. Do not lengthen holdover, shrink uncertainty arbitrarily or
relax any RF/resource gate to make the new features appear successful.

The SNTP client uses a correlation nonce in its transmit timestamp field;
that wire token is not a usable local UTC T1. Read the actual exchange model
before applying four-timestamp equations. Use [RFC 5905](https://www.rfc-editor.org/rfc/rfc5905.html#section-10)
for filtering and [clock-discipline concepts](https://www.rfc-editor.org/rfc/rfc5905.html#section-11.3),
with its clock-adjust discussion in section 12. Implement a bounded client
appropriate to this firmware; do not claim full NTP daemon conformance or copy
unreviewed host/operating-system machinery into Pico.

## Part 1 Persistent standalone manual PPM

Implement a durable operator-entered RF source-clock correction usable without
NTP, Wi-Fi or a WsprryPi host. It is carrier correction, not UTC acquisition,
UTC rate discipline, measured RF power or permission to transmit.

Define explicit units, sign, precision, defaults and range. One ppm is 1000 ppb;
retain the current positive-fast convention and existing correction bounds.
For example, +10 ppm corresponds to +10000 ppb and reduces the synthesized
increment for a fixed requested RF frequency. Do not borrow another backend's
PPM sign or combine a receiver correction into the Pico setting.

Use bounded deterministic arithmetic and canonical serialization; storing
signed integer ppb while presenting decimal ppm is a suitable implementation
choice to evaluate. Exact new field/resource names are not frozen by this
prompt. Reject malformed, nonfinite, overflowing, out-of-range or excessive-
precision values rather than silently coercing or clamping them.

Default/missing manual correction is zero and preserves current behavior.
Use the existing atomic journal and management authority. Ordinary legacy or
partial saves preserve omission; deliberate complete replacement/reset follows
the documented default. Cover reboot, journal recovery, power interruption,
Wi-Fi/profile overlays and unsupported downgrade behavior. Do not introduce a
new flash partition, raise payload capacities or write flash on every poll.

Expose the minimum necessary supported configuration/UI/status paths with
exact target/revision and carrier admission. Preserve closed legacy resource
shapes; add explicit version/capability negotiation where required. Other
repositories' strict clients are not implicitly upgraded. If independently
saved progress is extended, define its validation and explicit apply semantics;
a draft save must neither program hardware nor establish transmit readiness.

Apply through one central engine-preparation authority, covering standalone
and other admitted job producers. Respect allow_frequency_adjustment and the
existing nonzero-correction refusal when adjustment is forbidden. Do not
silently ignore consent or double-correct a host-precompensated request.

Choose the effective correction before preparation and freeze it through
completion/abort. A saved change is idle/unowned and cannot retune a loaded,
armed or running job. Distinguish saved manual value, next-job selection and
the active prepared value. A Type 2/3 frozen pair must retain the same selected
RF calibration across both jobs. Preserve frequency-policy and realized-
frequency validation for every RF-on event, spacing and adjustment reporting.

Exit evidence: deterministic sign/units/range and persistence checks, source-
bound normal/inhibited builds, management compatibility and no mid-job change.
Independent RF observation, when available, must be reported separately from
host arithmetic and actual hardware register observations.

## Part 2 NTP filtering and UTC rate discipline

First establish a coherent observation path. Record bounded source-labelled
accepted measurements with observation ID, board/boot/image/clock epoch,
configured peer and actual resolved endpoint, local raw send/receive monotonic
timestamps, reference UTC estimate, server timestamps/quality fields, RTT,
uncertainty and admission/rejection reason. Distinguish packet acceptance,
filter selection and arbiter-selected time. Latest RTT or aggregate counters
must not masquerade as the sample that established the UTC anchor.

Keep network timestamp/processing latency in the error budget. Preserve peer/
UDP-port checks, originate correlation, malformed/replayed/stale packet
rejection, server processing-time checks, era handling, root delay/dispersion,
precision, leap policy, KoD handling and bounded retry/backoff. Never interpret
or manufacture a UTC transmit timestamp from the correlation nonce; keep its
role distinct from local send timing.

Implement bounded filtering before qualified rate learning. Specify sample
capacity, delay/outlier policy, age/dispersion handling, startup behavior and
per-update work. Partition or reset on peer/source/boot/clock-generation changes
and real steps; do not mix pool-server identities into an oscillator fit.
Retain the original measurement age when reusing/projecting an older selected
sample. Re-selection or smoothing cannot renew freshness, turn rejected input
into accepted data or reduce uncertainty merely because jitter looks smaller.

Compare baseline offset-only behavior, filtering alone and filter plus rate
using identical deterministic traces and withheld validation data. Include
constant delay, asymmetric/varying queues, delayed processing, spikes, loss,
duplicate samples, outages, phase steps, drift changes and source transitions.
Measure error against known truth, uncertainty coverage, jitter, freshness,
bootstrap/recovery and launch availability; include cases where filtering
cannot identify a bias. Historical sparse INFO may illustrate behavior, but
cannot prove absolute UTC accuracy or supply missing observations.

Keep the raw hardware monotonic clock unchanged. Build a bounded, rate-aware
software UTC mapping with explicit phase/rate units, reference epoch, model
generation, uncertainty and validity. Support bootstrap and safe reacquisition;
define controlled phase/rate changes and fail-closed handling of incompatible
steps/disagreement. A fitted rate does not provide UTC after a cold boot.

Provide consistent forward raw-monotonic-to-UTC projection and inverse
UTC-to-local-alarm conversion. Update all relevant consumers: JobService ARM,
local launch reprojection and deadline/window calculations, arbiter interval/
overlap checks, scheduler expiry and Type 2/3 pair consistency checks. A
non-unit healthy UTC rate must not be mistaken for rollback simply because
raw-monotonic and UTC elapsed intervals differ. Preserve genuine rollback,
leap, maximum-future, missed-launch and uncertainty checks.

Respect the microsecond local alarm grid and conservatively include inverse
rounding/rate uncertainty. Test forward/inverse round trips and boundary
decisions against an independent exact-arithmetic oracle. Do not subtract two
large epoch timestamps in low-precision floating point or allow signed/unsigned
overflow to create a valid-looking schedule. Invalid arithmetic fails closed.

Preserve source arbitration: healthy admitted SNTP priority, qualified USB/
controller/browser policies, same-session challenges, disagreement and fallback
remain explicit. Do not train an NTP oscillator estimate on browser assumptions
or already disciplined controller output, or relabel a source after filtering.

Publish a coherent fixed-size phase/rate/uncertainty snapshot to the RF core
through the existing ownership mechanism. Do not copy mutable estimator history
into an IRQ-visible clock object or allocate/log/fit in the launch interrupt.
Armed jobs retain their original requested UTC and permitted window; fresh
mapping changes may refine local projection only under existing guards. A
running prepared waveform remains unchanged by new NTP samples.

Exit evidence: reproducible three-way comparisons, bounded resources/work,
conservative uncertainty and freshness, source-transition correctness, coherent
RF-core snapshots and rate-aware scheduling/launch failure tests. Smoother
status alone is not an acceptance result.

## Part 3 NTP derived RF calibration

Share valid observations or a portable estimator with Part 2, while keeping
UTC discipline and RF application separate. Estimate underlying oscillator
error from reference UTC versus the unchanged raw timer. Never regress an
already rate-corrected UTC clock against itself, infer a correction from the
assumed 50 ppm uncertainty allowance, or use its own applied RF correction
as independent validation.

Prove applicability for the exact image and clock configuration. Trace raw
timer tick generation, clk_ref, XOSC, clk_sys/PLL and PIO sampling using the
pinned SDK, firmware and actual configuration. The retained SDK starts tick
generators from clk_ref and configures the normal system clock through the
XOSC-referenced PLL, but that source relationship alone is not an RF measurement.
Nominal clock_get_hz values are not frequency-counter evidence. Unsupported
clock topologies must refuse automatic RF correction, with a clear reason.

Define the rate mathematically and prove sign/reciprocal handling. If raw time
advances faster than reference time, positive oscillator error requires the
existing positive correction that reduces NCO increment. A fitted UTC-per-raw
slope is the reciprocal of raw-timer rate; it cannot simply be copied as ppm.
Account for units, quantization, clock ratios and round-off without changing
sample clock or symbol durations. Test positive, zero and negative known rates.

Qualify a candidate using explicit minimum independent observations, elapsed
span, bounded uncertainty, disjoint-window stability, outlier/step rejection,
freshness and identity/topology matching. Freeze justified numerical thresholds
before acceptance runs. Confidence in a smooth regression is not a bound on
network asymmetry or source accuracy; endpoint/systematic errors and server
quality must remain in the calibration uncertainty. Use held-out data and
independent methods rather than validating a fit on its own training window.

Select one RF correction authority. Preserve the persisted manual value as
fallback. Use an explicit advertised manual versus qualified-NTP mode, or an
equally clear minimal policy, with a conservative manual/zero legacy default.
Manual zero must not secretly enable auto calibration. Do not add manual and
NTP estimates of the same oscillator error together. A separate residual trim
is not required by this task and must not appear implicitly.

Expose candidate/qualified/selected/applied state, value, uncertainty, source,
sample count/span, age, generation and rejection/fallback reason. Unstable,
stale, restarted, source-changed or out-of-range learning selects the documented
manual fallback for future preparations. Never clamp an unqualified fit into
an apparently valid calibration. Do not let a frozen active job's correction
change when source health changes.

Keep learned RF estimates volatile by default; persistent automatic calibration
is not needed to satisfy persistent manual PPM. If persistence is necessary,
justify it with identity, clock/source provenance, validity/age and wear rules;
it cannot restore UTC or assumed freshness after reboot. Auto mode may be saved
without saving an unqualified numeric estimate.

Apply a newly qualified selection only at the existing idle/preparation boundary,
respecting adjustment consent and frequency policy. Freeze the selected RF
correction/generation through the complete job or frozen Type 2/3 pair. Keep
requested frequency, actual NCO selection and correction provenance distinct.

Require matching independent RF observations before claiming physical
calibration or enabling it on an unsupported topology. Use a genuinely
independent calibrated counter/receiver reference with its own uncertainty.
A nominal SDR dial, successful WSPR decode, low NTP jitter, attached GPSDO or
host PPS timestamp does not establish Pico carrier accuracy. Verify any actual
reference identity, lock, routing, level and receiver correction; do not turn
on a reference or add a signal path incidentally. If no valid independent
measurement exists, finish software/gating work and report the physical gate
as unresolved rather than inventing agreement.

## Validation and finite live work

Keep portable filtering, rate estimation, clock mapping and calibration
selection separate from Pico SDK, transports, storage and RF adapters. Use
fixed bounds and deterministic input. Maintain C++/CMake standards, dependency
pins, allocator/reserve policy, stacks, renderer placement and flash layout.
No change to WTP wire contracts, capacity, timing ceilings or output authority
is authorized merely to make the feature fit.

Add meaningful tests for the new behaviors, including malformed/range inputs,
legacy omission and atomic journal failures, save/reboot/reset, correction sign
and consent, NTP rejection/filter age, 2036 wrap and supported-era edges,
source/clock resets, fit instability, uncertainty growth, overflow, inverse
rounding, armed launch races, pair consistency, manual/auto fallback and
immutable active-job state. Test disabled/not-ready cases on inhibited firmware.

Read docs/development/README.md and actual CTest registration before choosing
commands. Existing entry points include bash scripts/check_host.sh and
python3 scripts/validate_wtp_contract.py. Run affected checks and justified
regressions; after repairs rerun affected checks rather than unrelated campaigns.
Build normal WsprryPico and explicit WsprryPico-Inhibited, and the compatibility
RF target if shared wiring changes, with retained pinned dependencies and fresh
task-local ignored build directories. Do not install tools or download an SDK
incidentally. Record actual build inputs, source, image hashes, failures/skips
and linked-image/resource checks.

For live work, use current operator setup statements and AGENTS.md authorization
without redundant per-job prompts. Use one identified Pico, finite NTP collection
and the existing conducted RF path when applicable. Recheck live board/boot/
firmware, clock, receiver and control ownership; preserve drive, correction
baseline, cabling, attenuation and unused reference state. Another active user
or missing measurement/reference fact is a concrete setup conflict to resolve.

Freeze a bounded acquisition plan first. Unless the operator sets another
limit, cap fresh raw NTP collection at two hours or 128 exchanges, whichever
comes first, using the accepted bounded polling policy; stop early when the
predeclared quality gate is met. Never extend collection indefinitely to force
a pass, speed-poll public servers or treat simulated elapsed time as live soak.
Missing quality at the limit is a recorded result, not permission for an
overnight monitor or a different server-discovery feature.

For an independently observable carrier check, use one fixed representative
frequency and at most six tone jobs, each at most five seconds, no more than
30 seconds total RF. Freeze zero/manual-sign/qualified-auto/fallback comparisons
before starting; charge every RF start including failures. No WSPR frame,
band sweep, second board or automatic retry is required. Extra RF requires
an explicit budget extension. Reuse captures for offline review. Do not change
transmitter PPM or receiver correction inside a captured comparison without
recording that change as the independent variable.

## Evidence closeout and review

Write ntp-work-results.md with the three parts in the requested order and a
sanitized machine-readable evidence manifest. Record configuration/API choices,
equations/units/sign, bounds and policy, exact source/build/images/tools, raw
observation provenance, replay/held-out methodology, uncertainty coverage,
forward/inverse behavior, oscillator topology, correction selection/freeze,
independent RF outcomes, actual live budget, failures and unqualified claims.
Keep credentials, raw network records, bulk captures, private backups and
generated firmware in ignored task-local storage. Bind retained inputs and
outputs with hashes without publishing secrets.

Use the canonical three subitems for progress; a results table is evidence,
not a second task list. Link the result from maintained time/configuration/RF
references as appropriate and preserve historical research conclusions within
their original source/data scope. Do not relabel old estimates as new calibration.

After live work, stop test schedules, verify inactive output and no remaining
test ownership, and restore original firmware/settings/receiver/reference/
services as applicable through supported procedures. Preserve consumed
watermarks and record restoration checks or failures. A saved PPM, accepted
clock sample or successful command response is not proof of restoration.

Use a separate read-only adversarial reviewer for the complete implementation,
tests, documentation, evidence and status wording. Require specific actionable
findings with source/evidence and consequence. Challenge PPM sign/reciprocal
errors, double correction, schema/persistence regressions, fake sample freshness,
reduced-but-unjustified uncertainty, peer/source contamination, epoch arithmetic,
raw versus disciplined feedback, inconsistent inverse conversion, RF-core races,
healthy-rate pair cancellation, hidden mid-job changes and circular RF proof.
Check bounded resources, current timing gates, deferred scope and restoration.

Repair actionable findings, rerun affected checks and obtain a fresh independent
assessment of the repaired final result. Repeat until no actionable finding
remains. Respect collection/RF budgets during review; if a required gate remains
unresolved, report it without fabricating closure or implementing another item.

## Commit and push

Update only item 4 and its three subitem markers in the consolidated backlog,
preserving their order/grouping, saved-prompt link and all other task statuses.
Mark each part ✅ only on its actual acceptance; item 4 is ✅ only when all
three parts and required evidence/review are complete. Preserve ⏳ for a material
unfinished acceptance gate, including unverified RF applicability/measurement.

Inspect final and staged diffs. Stage only attributable implementation/tests/
documentation/evidence and item 4 changes, using partial staging for files
shared with other work. Run scoped git diff --check and git diff --cached --check.
Commit and non-force push the scoped result to origin/devel; this is authorized
on execution without another routine confirmation. Do not reset, stash, clean,
force push or absorb concurrent changes. No tag, PR, release or site publication
is requested.

Independently query remote devel after push and compare with local HEAD/upstream.
Report each part's result, checks/skips, review findings/repairs, evidence and
limitations, actual collection/RF budget and restoration, commit/push/parity
and remaining working-tree state. Reprint the complete canonical punchlist
using ✅/⏳/▧. Stop after item 4.
