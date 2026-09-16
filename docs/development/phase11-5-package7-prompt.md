# Phase 11.5 Package 7 execution prompt

Status: authorized execution prompt for R4 authority and interruption.

Execute this prompt. Do not stop after planning. Preserve failed attempts, repair
actionable findings, repeat only affected work, perform a final adversarial
assessment, commit and push the attributable WsprryPico changes, and verify
remote parity.

## Objective

Close Phase 11.5 family R4 for the selected Pico 2 W configuration: RP2350 Arm,
138 MHz system clock, divider 1, GP2 PIO/DMA, RAM renderer and network listener
enabled. Preserve the closed R1-R3 families unless an exact source-impact review
shows that this work invalidates an accepted row. R5, R6, conducted per-mode RF
acceptance and broad clock/band comparison remain outside this package.

## Starting identity and authority

Work from clean WsprryPico `devel` at Package 6 commit `5e6799c31a4b7a9d714ac1f9a620e6c826ca6459`
and candidate source `2b25ca05c270819466a04498f9bc4894a4c5bace`.
The retained Pico A image has UF2 SHA-256
`16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`
and recorded boot `80d558e5804547749eca849c53ba27e1`. Re-inventory rather
than assuming those live values. Pico A is serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`; Pico B is serial
`CDDBF8767C506C07`, device `29f20b7342051ef947aa56cb9d4fab42`.

Use the September 15 standing authorization in
`phase11-5-completion-authorization-20260915.md`. It explicitly authorizes the
R4 owner/foreign-session, lost-operation, transport interruption, finite RF,
reviewed repair, fixture and restoration work. Use only the established isolated
fixture on `wspr5` and the existing authenticated credentials. Keep private keys,
packet captures, generated INIs and raw private evidence outside Git.

Read `README.md`, `CONTRACT.md`, `docs/architecture.md`, the Phase 11.5 plan,
completion matrix, acceptance ledger, Package 6 result/review, Phase 11.4 G4-G7
result and the applicable Group 1 records before execution. Inspect Pico and
WsprryPi source rather than relying on historical narrative.

## Frozen Package 7 closure matrix

Package 7 owns all eighteen R4 matrix rows. Three R4 rows already carry
accepted evidence and require exact applicability review:

- `R4.browser-armed-abort`
- `R4.browser-running-abort`
- `R4.acknowledged-loss`

The separately accepted cross-cutting `FEATURE.5` row also requires an overlap
applicability check, but it is not one of the eighteen R4 rows.

The following fifteen rows must gain current applicable evidence:

- foreign control and forbidden storage in claimed-empty, Loaded, Armed and
  Running states;
- production-owner abort in Armed and Running;
- lost LOAD, ARM and ABORT replies with exact same-session replay;
- distinct TCP reset/EOF and resolver-failure regressions.

Do not collapse state-specific assertions into one generic ownership test.
For every foreign operation, bind the owner session/principal, foreign
session/principal, boot, job and exact state. Attempt CLAIM, RELEASE and ABORT
where the contract prohibits them and require the specified `BUSY` or
`NOT_OWNER` result. Independently prove unchanged owner/job/state after each
refusal.

For every forbidden storage case, use the authenticated production management
route with the current ETag and a valid unchanged configuration candidate.
Require `409 busy` before persistence, then prove the ETag, public configuration,
schedules, network request state and watermark remain unchanged. Bind this
physical result to the reviewed source path that checks `scheduler_.idle()`
before parsing or calling `CONFIG`; do not claim flash non-write from unchanged
values alone.

## Packet A — direct current-image authority and lost replies

Use Pico A. Before acquiring the shared RF reservation, prove Pico B is
authoritatively Empty, inactive, unowned and schedule-disabled. Prove Pico A is
the exact candidate, storage healthy, schedule-disabled, Empty, inactive and
unowned; wait for a synchronized current clock on the isolated fixture.

Create one authenticated network WTP owner using the controller credential and
an independent USB WTP observer/foreign principal. Use a single finite Tone job
at nominal 135,500 Hz, no more than 12 seconds planned duration. Charge its full
planned duration before ARM.

Exercise the state matrix sequentially:

1. CLAIM and hold claimed-empty.
2. LOAD and hold Loaded.
3. ARM sufficiently ahead and hold Armed.
4. Observe actual Running and active output independently.

At every state, perform the foreign control and forbidden storage checks above.
Do not let lease expiry create the transition; renew the owner within the finite
packet as needed.

For LOAD, ARM and ABORT separately, attach the reviewed receive-drop filter only
to the exact task-owned network WTP socket immediately before sending the exact
request. Capture that four-tuple independently, require a complete request write,
server TCP acknowledgement and inbound response ciphertext, deliver zero reply
bytes to the application socket, and require no client ACK of response data.
Use USB to prove the operation took effect. Close the impaired socket, reconnect
with the original authenticated WTP session, reconcile STATUS, replay the exact
original request bytes and request ID, and require the cached result. Prove one
job and one terminal record with no duplicate execution.

For Running, require independent Console and WTP observations of the exact job,
owner, active output and unchanged boot before lost ABORT. Final reconciliation
must show Aborted, inactive output and exactly one terminal record; RELEASE must
leave Empty/inactive/unowned state.

Packet A permits one RF job and 12 planned RF seconds, no flash, BOOTSEL,
software reboot, Wi-Fi cycle, configuration write or allocation probe.

## Packets B and C — production-owner aborts

Use the real isolated WsprryPi production executable from a clean, exact source
revision. Review source impact from the last physically exercised client to the
current `devel` source. Do not replace the installed application. Record the
isolated binary hash, source revision, INI hash, credential-file hashes and raw
TLS observer hash. Pause the installed service only after proving Transmit is
disabled, boot policy is safe and the installed RP1 provider reports output
disabled; restore it in a `finally` path with original binary and INI hashes.

Run two separate finite production QRSS `ETE` jobs, one per packet, at nominal
135,500 Hz with a 33-second planned duration and sufficient future start lead.
For Packet B, wait for independent exact Armed state before sending one
owner-bound host browser API ABORT. For Packet C, wait for independent exact
Running/active state before the ABORT. Each request uses a fresh host browser
session/request identity, is fully written, and returns success for the selected
current host-owned job. An application process exit, local flag or UI label is
not cancellation evidence.

For each packet require raw TLS evidence for exactly one CLAIM, LOAD, ARM and
ABORT on the same production session/job; independent USB/Console evidence of
the intended pre-abort state; one matching Aborted terminal; inactive output;
ownership release; and a coherent production cancellation report. Preserve full
33-second charge for each job even when aborted early. Do not allow a second
scheduled dispatch.

Packets B and C each permit one RF job and 33 planned RF seconds, no flash,
BOOTSEL, software reboot, Wi-Fi cycle, configuration write or allocation probe.

## Regression and reuse work

Run the current WsprryPico job-service, network and TLS tests that cover owner
precedence, replay, response delivery, EOF/reset cleanup, resolver deadlines and
management idle checks. Run the applicable current WsprryPi WTP backend,
scheduler, browser API, TLS and network tests. Exact-diff both repositories from
the physically exercised revisions to current `devel`; transfer evidence only
when the changed files cannot affect the assertion.

The accepted browser Armed/Running aborts and acknowledged ARM-loss completion
may be reused only after checking source, image, engine, timing and authority
applicability. Retain their original failure components and limitations. Keep
the Phase 11.4 resolver and reset/EOF evidence as historical support; use
targeted current regressions for current code where physical repetition adds no
distinct mechanism.

## Execution safety and restoration

Use one shared RF reservation. No other board may be Armed, running RF or have
an enabled autonomous schedule while a packet holds it. A disconnect, timeout,
missing response or process exit never proves inactive output. On any unexpected
failure, stop dependent stimuli, preserve the raw record and reconcile with an
independent authoritative path before cleanup or another RF packet.

Across Package 7 use at most three RF jobs and 78 planned RF seconds. Use one
fixture session no longer than two hours plus 15 minutes reserved restoration.
No flash, BOOTSEL, controlled reboot, Wi-Fi cycle, configuration save or heap
probe is planned. Freeze fresh identifiers, source/image/helper hashes, deadlines
and restoration paths before execution.

Finally prove both boards Empty, inactive, unowned and schedule-disabled; Pico A
still on the same firmware/boot/configuration; the isolated network fixture fully
removed; management paths and Wi-Fi recovery timer restored; installed WsprryPi
service active with original binary/configuration hashes; and provider output
disabled.

## Evidence, review and publication

Keep immutable private raw evidence with a SHA-256 manifest. Publish a sanitized
machine-readable Package 7 result, an execution/review record and the updated
assertion matrix, progress record, plan and acceptance ledger. Add an offline
auditor that derives acceptance from raw evidence and targeted altered-evidence
tests. It must reject wrong source/image/boot/session/job/state, missing complete
writes or framing, a delivered lost reply, capture loss, foreign success, changed
owner/state, accepted storage write, duplicate mutation/execution, absent active
output, wrong production owner, missing ABORT, false terminal state, budget
inflation and incomplete restoration.

Perform an adversarial review after the first complete audit. Repair every
actionable finding, rerun affected checks and perform another adversarial
assessment. Close R4 only if all eighteen R4 rows have applicable evidence and no
contradiction remains. Phase 11.5 remains OPEN with R5-R6 outstanding.

Commit only attributable WsprryPico artifacts and tooling. Push `devel` without
force, independently compare local HEAD, upstream and `origin/devel`, and report
the exact board state, budgets, validations, adversarial findings, commit, push,
remote parity and working-tree state.
