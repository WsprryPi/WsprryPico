# μChrony packet, phase and independent-clock validation prompt

Execute this prompt in the primary WsprryPico `devel` checkout. Complete the
investigation, implementation, validation and adversarial review cycles, then
commit and push the authorized NTP/μChrony work and report the results. Do not
stop at writing a plan. This prompt is reusable: identify and record the actual
source, evidence and hardware state on every execution rather than assuming
that an earlier hash or device state is current.

## Objective and acceptance

Establish how the original MIT μChrony implementation differs from unmodified
Chrony 4.9 at packet admission, adaptive history, delay-asymmetry correction,
source combination and clock control. Explain the adverse indicated UTC-phase
result and A's remaining source-fit difference. Correct demonstrated defects
without tuning toward a measured RF result or weakening quality gates. Evaluate
accuracy against independently known error; reference agreement alone is not
an accuracy criterion. Produce reproducible failing cases and numerical results,
including exclusions and adverse results.

The previous cold captured-subset replay starts after packet admission and has
missing boot history and different RTC acquisition. Its matching stale periods
do not establish matching packet rejection. Its phase RMS is an indicated,
uncalibrated timestamp-path diagnostic, not a certified absolute UTC result.

## Workspace and preservation

1. Read applicable AGENTS instructions, README, CONTRACT, architecture and the
   current development guide. Inspect branch, HEAD, index, dirty/untracked files,
   existing processes and relevant work before editing.
2. Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Preserve an advanced
   branch; never reset, stash, broadly stage or overwrite other work. Do not
   create another worktree. Other repositories remain independent.
3. Preserve the initial working state and hashes privately. Inventory earlier
   NTP/pulse work that this execution depends upon. The concurrent UI and USB
   installer changes are outside the implementation and commit scope. Shared
   files require exact hunk ownership. Pause on an actual conflicting edit or
   hardware/resource owner; do not overwrite it.
4. Keep captures, credentials, backups, generated firmware, upstream source,
   external GPL binaries and bulk receipts in ignored private storage. Publish
   only original source, tests, technical documentation and sanitized results.

## Licensing and preserved behavior

Chrony source must not be copied, translated, vendored or linked into μChrony
or firmware. Derive original implementations from rules, mathematics and
independently observed behavior. The private reference may link unmodified
upstream Chrony 4.9 objects through original test drivers; record upstream
version/license, objects, driver, executable and offered-input hashes.

Keep manual PPM separate and persistent. Preserve saved settings, UTC/RF
authority boundaries, age/uncertainty/ownership/job launch limits, RF candidate
and physical qualification gates, maximum drift/update skew and source-quality
thresholds. Smaller reported errors never substitute for independent evidence.
Preserve the 32 KiB engine limit and bounded original history. Keep the normal
`WsprryPico` image as the only deployment image for this task.

## Packet admission comparison

1. Extend the external oracle to exercise Chrony's actual request/reply packet
   processing before admission. Use controlled in-process IO/clock adapters;
   no host-clock adjustment, daemon/service mutation or real public NTP traffic
   is needed for deterministic validation. Fail on unexpected IO.
2. Supply identical offered wire packets, raw send/receive events, source
   identities, timestamp precision, response fields and documented profile
   settings. Record offered, correlated, valid and accepted observations
   separately. Do not feed Chrony only μChrony's accepted samples.
3. Test malformed/uncorrelated/duplicate/stale/unsynchronized replies, era and
   timestamp boundaries, processing delay, symmetric/one-way queues, changing
   jitter and loss. Include known rejected low-jitter queue fixtures. Distinguish
   a reference-profile difference from an implementation defect.
4. Minimize the first unexpected divergence, preserve its prefix and raw
   offered input, diagnose the rule/quantity responsible, fix original code if
   defective, and add meaningful positive and negative regressions. Preserve
   every threshold; compare arithmetic and state rather than bypassing checks.

## Adaptive history and phase investigation

1. Trace A's first divergent history/asymmetry decision. Log the active and
   predecessor horizon, coefficient evidence, residual runs, weights, fit center,
   covariance, combination and applied frequency at the same causal event.
2. Compare old, revised and reference implementations with matched starting
   phase/frequency and explicitly controlled acquisition. Compare common input
   histories; do not reconstruct missing boot state or relabel it complete.
3. Isolate weighting-only, asymmetry-only and combined changes. Test startup,
   warmup, constant bias, phase steps, oscillator ramps and network asymmetry.
   Keep the existing full covariance and identifiability safeguards. Explain
   deliberate conservative differences rather than forcing numerical equality.
4. Independently verify phase signs, epoch translation, clock cooking/uncooking,
   finite-slew endpoint arithmetic, raw-to-UTC mapping and pulse/GPIO timestamp
   interpretation. Preserve causal-prefix and probe-grid checks. Score UTC phase
   and pure frequency separately; exclude intentional phase slew from oscillator
   frequency accuracy.
5. Retain the adverse captured-pulse RMS result. Determine whether it comes from
   a replay defect, startup/history assumption, source bias or controller behavior.
   Verify any repaired analysis against an independent arithmetic oracle and
   synthetic fixtures with known UTC and frequency error.

## Bounded rejection diagnostics and hardware readiness

If new live evidence is necessary, provide bounded USB diagnostics for offered
rejected observations with immutable board/boot/image, source slot/endpoint,
epoch, raw timestamps, wire fields, decision and sequence/gap identities. Do
not expose credentials or inflate compact UI status. Prove overflow behavior
and retained/omitted visibility. Do not discard passive evidence on sync loss.

Before live work, write a concrete readiness verdict based on the offline
results. An unresolved harmful controller/analysis defect, missing setup identity,
foreign resource owner or UI conflict is a no-go. Complete offline work and
report that blocker honestly; do not replace failed acceptance with more logging.
If readiness passes, the user's instruction authorizes the following finite
physical comparison using the previously described conducted setup.

## Finite physical comparison, conditional on readiness

Verify wspr5 and both exact Pico identities, firmware/settings, GPIO22 pulse
wiring to Pi GPIO22/23 and ground, GPS/PPS health, GPSDO lock/control/routing,
attenuation/combiner and SDR identity. Respect existing OS locks and owners.
Preserve credentials/settings/services. Both boards use `pool.ntp.org`; saved
schedules stay disabled and boards remain inactive/unowned between exact finite
checkpoints. Do not restart or extend any completed campaign.

Before starting, record and print start time and deadline in America/Chicago
and UTC. Create a new campaign with independent process identity/deadline guard
and explicit restoration. Bounds: at most 120 minutes total including at least
five minutes for restoration; 600 physical pulses and query delta 800 per board;
512 MiB total raw evidence; four RF attempts per board maximum, each a two-second
conducted tone. Count failed attempts and both crossover phases against these
same limits. No automatic extension or unbounded retry is permitted.

Use a controlled before/after board crossover only if both exact normal images
and protocol compatibility are verified. Record reset/persisted-seed effects and
warmup. If a valid crossover cannot be constructed, use an explicitly narrower
physical verification and label its limits. Capture original offered/accepted/
rejected histories, immutable baseline frontiers, raw pulse edges and reference
health. A missed time hack or existing quality-gate rejection is passive data,
not by itself a reason to stop observation; RF stays subject to every gate.

Measure native oscillator/RF error with simultaneous GPSDO reference lines in
the same SDR recording. Bind application clock snapshots before/after each
checkpoint. Evaluate pure UTC frequency correction separately from phase slew,
manual PPM and physical carrier correction. Retain an uncalibrated GPIO/reference
delay allowance; do not claim certified absolute UTC. Restore and independently
verify source/settings, GPIO/reference, exact firmware identity and both boards
inactive/unowned. Verify actual observer/guard exit before releasing evidence.

## Checks, reviews and publication

1. Run affected deterministic tests, complete supported host validation and the
   existing reference suites without relaxing assertions. Provide required test
   dependencies in a private environment if needed. Cross-build the normal
   firmware using installed pinned dependencies; verify linked resource guards.
2. Write a source-bound engineering report, sanitized machine-readable results,
   convergence figures and reproduction instructions. Clearly separate known
   truth, NTP consistency, target application, physical RF and timestamp-path
   evidence. Repair actionable analysis findings as well as implementation bugs.
3. Perform a deliberately adversarial assessment of code, fixtures, arithmetic,
   provenance, visibility, experimental controls, restoration, conclusions and
   commit scope. Record concrete findings and severity. Fix every actionable
   issue, rerun affected checks, then perform a fresh adversarial assessment.
   Repeat until no actionable finding remains; do not silently waive a failure.
4. Inspect the complete staged diff and untracked dependencies. Stage only the
   authorized NTP/μChrony/pulse implementation and results, including required
   earlier work. Preserve unrelated UI/installer hunks and private files. Check
   formatting, links, confidentiality and reproducibility. Commit on `devel`,
   push without force, then independently verify the remote branch SHA matches
   the local commit. Preserve any newly advanced remote changes safely.
5. Report concrete fixes and measurements, unresolved physical limitations,
   readiness/live-run outcome, review cycles, test results, commit and remote
   parity, plus any unrelated working-tree changes deliberately left in place.
