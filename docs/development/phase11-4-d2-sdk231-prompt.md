# Phase 11.4 D2: released-SDK shutdown and goodbye assessment

Execute this prompt in `/Users/lbussy/GitHub/WsprryPico`, initially devel
`ea053f8c4bd922545e66efb964deb8d9d3a9e166`. Read AGENTS.md, README.md,
CONTRACT.md, architecture, development commands, the D1–D3 acceptance record,
loop/shutdown investigations and latest B2 SDK update/results. Preserve the
existing shutdown-results edit and untracked soak report/script. Do not edit
sibling repositories or the SDK. Save this prompt, exact evidence and assessment,
perform adversarial review, fix actionable findings and reassess, then commit
and push only owned work to the existing WsprryPi/WsprryPico devel branch.

## Question and boundaries

Test whether SDK 2.3.1's corrected RP2350 event/timer waits eliminate the observed
shutdown watchdog, and independently determine whether orderly mDNS withdrawal
and recovery satisfy D2. A short period without a reset is bounded evidence,
not proof of the cause of every historical stage-14/16/27 watchdog. Preserve
all missing-goodbye and failed recovery attempts, including failures without
resets. Do not close B2, D1, the eight-hour soak, or general RF qualification.

All network testing uses Bohica-IoT, the user-described simple 2.4 GHz bridge.
Use wspr5 USB wlan1, MAC `90:de:80:47:b9:da`, current profile
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`, address `192.168.1.117` and its active,
boot-enabled recovery timer. Never use onboard wlan0. Keep the original profile,
router, reservations, installed WsprryPi service and trust configuration unchanged.
The Mac's Bohica-IoT association was user-confirmed. Record actual radio BSSIDs;
association-dependent B2 failures may confound packet/cache/recovery results.
Do not conceal them by flushing caches, adding neighbors or locking radios.

Primary subject A is Pico 2 W/RP2350, serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, certified name
`wsprrypico-0a60df.local`. Comparator B is serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`, MAC `88:a2:9e:0a:9d:89`, certified name
`wsprrypico-0a9d89.local`. Console and WTP endpoints use their serial-specific
by-id aliases ending if00 and if02. Exclude unrelated GPSDO/SDR endpoints.

Use the existing standard inhibited images, SDK 2.3.1 commit
`079c6f39023649b154152db30f1d781e884879bc`, default 150 MHz system clock, no RF
mode. Runtime revision is `dbf1d86f0885-dirty`; use the committed B2 manifest's
per-board UF2 hashes and recorded deployments to bind that shared revision.
A UF2 is `06d18600a3605e874f71c8fa4e7e7df1a1ef5983b5e1dcf6d0b1e695f01716e5`;
B UF2 is `93a8db32967db004ef26a8bd85fb9efb52e86802c8861976032622f77d293183`.
Revalidate actual boot IDs; do not assume deployment metadata proves the board's
current state. Preserve AA0NT/EM18/20, disabled schedules, expiry, journals,
watermarks, short names and independent certificate identities.

The user's instruction to execute D2 authorizes bounded read-only USB/LAN
inspection and captures, native resolver/TLS reads, and idle Console WIFI OFF/ON
on the exact identified inhibited primary device. Firmware changes/deployment
are conditional on a concrete defect: prepare, test, build, check and hash a
standard inhibited candidate before any exact serial-bound deployment. No RF,
LOAD/ARM, owner changes, arbitrary reboot, debugger, GPIO or flash erase is part
of the baseline campaign. Retain original breadcrumbs before a separately bound
recovery if a watchdog occurs; stop dependent mutations on unknown output,
identity mismatch or a recovery boot.

## Procedure and verdicts

1. Verify clean dependency inputs and the deployed candidate's stack/journal,
   shutdown interception and corrected event-drain image checks. Snapshot exact
   host state, both devices' Console INFO and WTP HELLO/CAPS/STATUS. Require healthy
   storage, empty/unowned/inactive inhibited output and disabled schedules.
2. Prepare a new owner-only evidence directory. Retain command arguments,
   source/tool/image hashes, UTC and monotonic timestamps, raw WTP bytes and
   decoded frames, USB INFO/NETTRACE, native Mac callbacks and Linux captures.
   Independent USB sampling must continue through slow network failures. Never
   open a second reader on a Console/WTP interface while an observer owns it.
3. Before each OFF, attempt and record genuine native Mac/Linux resolution,
   verified HTTPS and actual positive Pico mDNS packets. A missing baseline
   disqualifies full acceptance. A clearly labeled shutdown-only diagnostic may
   still proceed after fresh USB identity/output checks, to answer the watchdog
   question; it must never acquire a full D2 PASS or erase that baseline failure.
4. Keep the first case's network clients idle before shutdown when trace coverage
   can establish that condition; later cases may use normal bounded read traffic.
   Do not infer an idle interval from a flag or an attempted connection alone.
5. Arm an independent local restoration timer before each bounded systemd runner.
   The restorer must stop and verify termination of the observer before opening
   USB, validate exact device and original boot, and issue WIFI ON only if that
   identity and healthy inhibited state remain authoritative. An unresponsive
   or recovery boot is a stop condition, not permission to reset blindly.
6. Issue one WIFI OFF, keep observing through the existing one-second withdrawal
   opportunity and physical station disable, and hold OFF for at least 150 seconds.
   Run six distributed bounded native Linux negative lookups. Preserve actual
   Pico-sourced TTL-zero A/PTR goodbye records, absence/presence of later positive
   answers, Mac Add/Remove callbacks and Linux lookup results. Check packet
   origin, TTL/class/name/address/PTR identity and zero-drop capture completeness.
7. Issue one WIFI ON on the same boot. Preserve the existing 40-second local
   activation and 120-second peer recovery limits, with at least five successful
   checks spanning 30 seconds. Capture actual same-name probes, positive current-
   address announcements and Mac re-add. Recovery errors are retained separately
   from shutdown evidence. Verify saved state and output authority throughout.
8. Report three independent results for each attempt: USB-observed shutdown and
   watchdog behavior; goodbye/cache withdrawal; native/authenticated recovery.
   Full D2 requires all prerequisites and evidence. Eight clean complete cases
   are required for the existing bounded repeatability conclusion. Never replace
   missing packets with driver submission counters, or qualified recovery with
   a late successful retry.

Run no more than eight physical shutdown cases. Stop immediately for a new
watchdog, identity/output uncertainty, observer/capture failure, unsafe cleanup,
or three unresolved failed cases. Preserve every invalid or failed admission;
a repaired observer starts a separately labeled attempt, never an erased retry.
Do not continue accumulating the same known failure merely to reach eight.
If delivery prevents a complete series, report the valid shutdown sub-results
and exact blocked gate without lowering the full acceptance threshold.

## Adversarial assessment and completion

Challenge: original versus new boot/image, missing reset intervals, maximum USB
sample gaps, independent WTP framing/ownership, command allowlist and journal
preservation, exact capture windows and kernel drops, positive-baseline existence,
Pico packet origin and matching goodbye records, native resolver/cache behavior,
first-failure retention, deadline enforcement, association drift, restoration
independence and whether any claim confuses no recurrence with causal repair.
Fix actionable implementation/observer/audit findings, run affected deterministic
checks and re-assess actual retained evidence. Do not alter prior failed records.

Finish with authoritative USB checks on both Picos, actual Mac/Linux reachability,
original Bohica-IoT host profile and active/enabled recovery. Stop all task-owned
observers/timers; preserve failures before clearing only their transient unit
bookkeeping. Save sanitized results and an evidence hash manifest; private keys,
credentials, captures and firmware remain ignored. Preserve the same remaining
rows B2, D1, D2, E1 and eight-hour soak with ownership, evidence-bound status and
remaining work. Commit and push reviewed owned files, verify remote parity and
report limitations and remaining user changes explicitly.

## Retained execution refinement

Case 1 used a shutdown-diagnostic runner because Mac/Linux authenticated and
packet baselines were missing. Its USB shutdown observation remains valid, but
its original failures prevent full acceptance. After normal reconnection moved A
to the host's radio and authenticated reachability returned, later cases add an
explicit post-cleanup native lookup/HTTPS record so the existing full withdrawal/
recovery auditor can evaluate them. Preserve both helper versions and every case;
this does not restart the campaign or erase case 1.

Case 2 exposed a recovery-observer defect: it attempted TLS while authoritative
USB still reported an unsynchronized clock, when firmware deliberately rejects
TLS because certificate time is unavailable. Match the firmware readiness gate
before attempting recovery HTTPS, without resetting the original 120-second
deadline or hiding attempted-read failures. Add deterministic regression tests.
The initial series stopped after its third failed case; retain all three. Run at
most one separately labeled observer verification, requiring positive Mac/Linux
and captured packet baselines before OFF. Failed admission ends that validation
without another shutdown. A later pass does not erase the stopped series or
satisfy the eight-clean-case acceptance gate.
