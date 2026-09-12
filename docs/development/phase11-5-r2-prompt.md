# Phase 11.5 R2 execution prompt

**Execution record and subsequent amendment:** the original frozen e20ae8b
attempt below ran with explicit R2 fixture/wiring authorization. Its first Tone
became MISSED_START; six jobs did not run. Both boards and the host were restored.
Current counts are 0/7 R2 jobs complete, Phase 11.5 1/6, and 28/32 configuration
writes. The original packet is spent; do not restart it.

The user subsequently directed: “We should only CANCEL if we are unable to get
within the expected second, and use telemetry for the delay otherwise.” Implement
the requested UTC-second window, not a rolling +1 s allowance: aim for the target,
never intentionally launch early, allow lateness before the next UTC-second
boundary, and preserve clock-validity checks. Report target/observed timestamps
and delay. Preserve the complete waveform and anchor completion to its actual
launch. Keep DMA/refill deadlines and all modes' event durations unchanged.
Update the shared WTP contract, host tests and inhibited simulator. Adversarially
check fractional targets, the exclusive boundary, overflow/leap safety, delayed
foreground/IRQ handling, completion, output authority and diagnostic units.
Cross-link without flashing as software validation. Commit/push the reviewed
source and failed-run evidence. This source change creates a new candidate:
freeze its clean identity and repeat affected R1 memory/stack/timing checks before
accepting it in R2. Preserve the failed e20ae8b evidence and its R1-only closure.

The following is the original execution scope; its old candidate and 26-write
starting count describe that preserved attempt, not permission to replay it.

Execute R2 on the candidate whose R1 is closed. The current baseline is R1 5/5,
Phase 11.5 1/6 families, no accepted configuration, 26/32 configuration writes.
Read AGENTS.md, README.md, CONTRACT.md, architecture, development instructions,
the current plan/ledger and the R1 review/result before implementation. Work on
devel in WsprryPico and, only as necessary, WsprryPi. Preserve unrelated changes,
historical failures and exact evidence identities. Commit/push are requested.

## Scope and sequence

Reuse candidate source `e20ae8bea2d5237af017dbd5f73bfe9332ce144e`, physical
138 MHz, divider 1, RAM renderer and listener enabled. Verify the ELF and UF2
hashes recorded in the ledger. Inhibited 150 MHz remains separate regression
context; R1 need not be repeated for host helper/documentation changes. No
firmware rebuild, clock comparison, independent RF decode or band sweep.

Run three complete ten-second Tone jobs first. Audit that gate before one job
each in QRSS (35 s), FSKCW (35 s), DFCW (17 s), and WSPR (110.592 s). Base
frequency is 135.5 kHz; keyed jobs use the established ETE/three-second-dot
patterns and WSPR uses AA0NT EM18 37. Freeze complete events, frequencies,
durations and unique job identities before each packet. At least seven jobs
are required, with actual production-owned, browser-owned and USB-reference
submission represented across the campaign, never concurrent ownership.

The first concrete packet is intentionally only the three browser-owned Tone
jobs under N300/USB360. It cannot close the family, remaining modes or the other
two submission paths. Prepare later packets with explicit source-bound production
scheduler cadence and USB endpoint ownership. Do not label a custom TLS client
as production submission or open a second reader on the observer's USB endpoint.
Do not perform dependent RF jobs before the Tone timing gate passes.

## Workload and numerical gates

Normal browser N300 initializes at 0 s, refreshes at 30/70/110/190/230/270 s,
and reloads at 150 s. Initialization/reload issue four sequential GETs: `/`,
`/api/v1/capabilities`, `/api/v1/status`, `/api/v1/config`. Exactly eight actions,
fourteen GETs, six explicit refreshes; no recurring CSS/JS asset stress.

Keep action-start lateness at most 15 s, fresh HTTPS requests at most 15 s,
whole page actions at most 60 s, and finish all actions within the interval.
Browser job mutations share the browser lane and retain the existing five-second
transaction deadline. Grant a mutation only with a complete five-second request
plus one-second margin before the next scheduled action. Preserve R1 and legacy
S behavior. Record admission waits separately from request latency.

The idle production observer offers STATUS at 1 Hz, at least seconds minus two
successful requests, maximum two-second start gap and five-second native
SSL-write-entry-to-response deadline. This applies to its idle scheduler while
another principal owns the job. A production-owned job needs its actual separate
state policy frozen from source before execution; do not substitute idle cadence.

Independent Console INFO is 1 Hz, maximum two-second gap; USB STATUS/health is
0.2 Hz, maximum six-second gap. Individual USB requests must finish within five
seconds. Keep USB observation running to its bounded deadline if network work
fails; stop the actor and all dependent mutations. Failed observation is never
silently dropped from the audit.

Require exact Loaded/Armed/Running/Complete and output/owner coverage, zero
unexpected allocator/TLS failure, heap reserve at least 32,768 bytes, both
16 KiB stacks with valid 4 KiB MSPLIM reserves, and zero unexplained faults,
DMA errors, starvation or resets. Reuse R1 allocation feasibility only within
its recorded limits; compare actual new high-water and largest request values.

At 138 MHz a 16,384-word block lasts 3,799,188.406 ns, with a 75% budget of
2,849,391 ns. Keep matched full and short predecessor reserve at least 25%;
calculate short deadlines from actual predecessor word counts. Remaining-word
samples occur after installing the successor and account for time consumed
before IRQ entry; the IRQ-entry-to-ready counter alone omits entry latency.
Never add overlapping maxima to manufacture a margin.

For each Tone, audit exact per-job DMA, paired-refill, running-successor, alarm,
and zero-tail deltas. Bind distinct launch epochs and monotonic targets to ARM
UTC within recorded clock uncertainty. Require a successful guarded launch and
post-enable software observation, reporting its offset without inventing a
mode-level microsecond tolerance. Alarm callback duration is diagnostic, not
an R2 acceptance deadline. The initial 10-microsecond post-enable and
250-microsecond callback limits were withdrawn after the user's review because
they lacked a use-case justification. This does not turn a cancelled/Missed job
into a successful execution. The subsequent explicit UTC-second policy supersedes the proposed 250 ms
window. The failed frozen image still has the old strict guard; the amended
source/contract require a new candidate and affected R1 checks before physical
acceptance. Post-enable telemetry is not an exact electrical-edge measurement.
Keep the separate full-block IRQ/refill and actual predecessor reserve budgets.
Missing, unpaired or inconsistent evidence fails its assertion.

## Hardware, network and authorization

DUT A: USB `0BF4B4AEC9FFB344`, WTP ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`. Comparator B: USB `CDDBF8767C506C07`,
WTP ID `29f20b7342051ef947aa56cb9d4fab42`; keep B read-only.
Refresh boots, revisions, configurations and authoritative output/ownership.
Do not admit a historical boot following an unexplained reboot.

Before RF, confirm the current GP2 paths still provide 50-ohm loading and
60 dB attenuation per input: Pico through 20 dB into the combiner, then
20+10+10 dB to the SDR; no filters; GPSDO is the other attenuated input.
Do not change GPSDO output, GPIO4, either output path, or the comparator.

Use SSH outside the sandbox. Preserve Ethernet management, wlan1 and the
installed WsprryPi executable/process. The isolated fixture uses wlan0 AP and
wlan2 client, a temporary Wi-Fi recovery timer pause, chrony ACL for
10.77.15.0/24 and fixture-scoped time.local publication. The user subsequently confirmed the unchanged wiring and explicitly authorized
the bounded R2 fixture in chat. That approval covers this campaign and its
guarded restoration; do not ask again for the same scope. It does not permit
unbounded RF retries or silently substituting another firmware candidate.

Read `/usr/local/share/doc/time-local/README.md` on wspr5. Preserve permanent
chrony/GPS/PPS, Avahi, time.local publication/DHCP refresh, Internet fallback and
wspr5.local. Pico configuration stores hostname `time.local` in `wifi.ntp_ipv4`;
`server time.local iburst` is a chrony-client directive, not Pico configuration.
Verify native mDNS and valid stratum 1/PPS NTP from the wlan2 namespace to
10.77.15.1 before flashing, then target resolution/synchronization. No NAT,
LAN route, hosts-file or literal-IP bypass. Capture both fixture interfaces.

Prepare/test/freeze first. Expected hardware work is 20–40 minutes per ordinary
packet, not required soak time. Device work is bounded to 45 minutes plus
10 minutes restoration; host fixture 70 minutes plus 10 minutes cleanup. Arm
independent cleanup before mutation. Do not extend deadlines. Carry the actual
26/32 configuration count and three historical R1 probes forward; R2 performs
no heap probes. Normal setup/restoration uses two additional writes. Reserve
remaining R5 schedule/rotation and final restoration capacity rather than reset
the administrative counter.

Use a new private attempt directory and exclusive endpoints. Stop dependent
actions on failure. Never auto-retry a job, clear journal/fault state, reflash an
unknown device or infer inactivity from a disconnect. Restore original approved
image/config only after authoritative safe-state admission. Independently restore
host resources without resetting an unknown Pico. Verify both boards and the
permanent time service after cleanup. Preserve all failed attempts.

## Review, closure and publication

Run focused deterministic tests for finite packet admission, source/hash/clock
identity, normal action/mutation scheduling, time service admission, complete
raw wire evidence, per-job counters, timing/epoch binding and failure/cleanup.
Preserve historical auditors and result formats. Mock evidence is not target
acceptance. Keep failed subcases and not-run subcases distinct.

After each hardware packet, audit raw evidence before dependent work. After
execution, adversarially review source, inputs, actual timing/resource evidence,
observer effects, restoration, scope and reported counts. Fix actionable
in-scope findings, rerun affected checks and review again. Never weaken a gate
or relabel a hardware failure to close review. An actual blocker remains open.

Update the prompt, packet, results, review, development pointers and ledger.
Publish the accepted configuration list only after all mandatory families pass;
R2 alone cannot accept the configuration. Selecting another clock in 11.6
requires the affected 11.5 checks again. Phase 13 retains the systematic clock,
band, mode, filter and spectral comparison. Do not claim SDR calibration from NTP.

Commit scoped changes in each changed repository to devel, push origin/devel,
verify remote parity and report worktree state. Report completed jobs/assertions,
family count, exact image/clock coverage, tests/review, remaining gates, final
board/host state, configuration writes, artifacts and commits. No credentials,
firmware, private configuration or raw captures enter Git. Operator documentation
is outside scope until measured operating limits can be published.
