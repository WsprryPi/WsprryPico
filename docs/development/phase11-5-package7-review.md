# Phase 11.5 Package 7 execution and adversarial review

## Outcome

Package 7 is **COMPLETE** and R4 is **CLOSED**. All eighteen R4 rows are
`accepted/applicable`: fifteen rows gain Package 7 evidence and three existing
browser/loss rows pass exact applicability review. Phase 11.5 advances to **4 of
6 families closed**. R5, R6 and full Phase 11.5 remain open; Package 8 is next.

The [execution prompt](phase11-5-package7-prompt.md) and
[corrective amendment](phase11-5-package7-amendment.md) define the bounded work.
The [machine result](phase11-5-package7-result.json) contains the sanitized
closure record and hashes of the private raw evidence. The
[adversarial result](phase11-5-package7-adversarial-result.json) records the
final altered-summary assessment, and the
[raw adversarial result](phase11-5-package7-raw-adversarial-result.json) records
the offline altered-evidence assessment performed on private copies.

## Candidate and boundaries

The exercised Pico A image remains source
`2b25ca05c270819466a04498f9bc4894a4c5bace`, UF2 SHA-256
`16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`,
device `fd6127d11d6aca42a9905fa3fb1bf1d5` and unchanged boot
`80d558e5804547749eca849c53ba27e1`. It is the selected Pico 2 W / RP2350 Arm,
138 MHz, divider 1, GP2 PIO/DMA, RAM-rendered, network-configured candidate.
Pico B remains device `29f20b7342051ef947aa56cb9d4fab42`, boot
`6684b4b197d80cfa0ce83b3aaf205cb0`.

The production-owner cases use WsprryPi source
`820e6980e880ce8b20418a20c15f4ac2311f8ca0`. The isolated executable, TLS
observer, decoder and installed service/configuration identities are bound in
the private record or raw auditor. No Pico runtime source under `src/`,
`include/`, `firmware/` or `cmake/` changed after the exercised candidate.
Package 7 adds evidence tools, fixture support, tests and documentation; it does
not relabel another image as current physical evidence.

## Accepted evidence

### State-specific authority and storage

The direct current-image run establishes foreign CLAIM, RELEASE and ABORT
precedence in claimed-empty, Loaded and Armed. The production Running run adds
the fourth state. CLAIM returns `BUSY`; RELEASE and ABORT return `NOT_OWNER`.
The owner, job, state and boot remain unchanged after each refusal.

Authenticated configuration GET/PUT/GET triples cover claimed-empty, Loaded,
Armed and Running. Every PUT returns `409 busy`; the public configuration and
ETag remain identical. The Armed refusal completed before its scheduled launch.
The source review binds these observations to the idle-before-persistence gate;
unchanged values alone are not treated as proof of a non-write.

### Lost replies and exact replay

LOAD, ARM and ABORT each use a complete task-owned request write, independent
packet capture, inbound response ciphertext and zero reply bytes delivered to
the impaired application socket. Independent USB WTP state proves the effect.
After reconnecting with the original authenticated session, replay of the exact
request bytes and request ID returns the cached result. LOAD and ARM remain on
one job; ABORT uses its separately frozen tail job. The accepted ABORT tail
records Running/active before the loss, one Aborted terminal, inactive output
and final Empty/released authority. Captures report zero kernel drops.

### Production owner abort

Two finite production QRSS `ETE` jobs independently reach the intended state
with exact WsprryPi host ownership, a valid lease, matching session/job/owner and
matching Pico state. The Armed and Running browser API requests return success
for their frozen request IDs. Both jobs produce exactly one Aborted terminal, a
cancelled production report and final Empty/released authority.

The decoded production TLS streams contain one CLAIM, LOAD, ARM, ABORT and
RELEASE, in that order, on the same session and job, with successful responses
and no duplicate mutation. The Armed stream contains 207 observer records and
40 WTP requests; the Running stream contains 409 records and 80 requests. The
Running case also has independent Console Running/active evidence and supplies
the Running foreign-control and forbidden-storage checks.

### Regressions and reused rows

Current WsprryPi checks pass distinct TCP reset/EOF cleanup, resolver failure,
backend/session behavior, production configuration/runtime behavior and network
lifecycle. The retained log reports 1,122,306 backend checks, 6,871 production
checks and a passing network lifecycle check. Exact source impact preserves the
already accepted browser Armed abort, browser Running abort and acknowledged
ARM-loss rows. Their original identities, limitations and failed components
remain unchanged.

## Budget and retained failures

Package 7 charges **9 RF jobs / 213 planned RF seconds**, within the standing
ceiling of 16 jobs / 14,400 seconds. Three attempts are accepted final packets;
six charged attempts are retained failures. Six failures occurred before live
RF output, including preflight and admission defects, while the conservative
accounting still charges any already reserved job duration. The public manifest
hashes eleven distinct failed-attempt directories. None receives row credit.

The failures identified real harness assumptions rather than new firmware
faults: a direct state-transition timing overrun, production Armed transition
timing, missing live Console job fields, a queued decrypted event before the
receive-drop filter, a stale WsprryPi ownership snapshot and the same Console
schema assumption in Running. Each retry was limited to its affected gap and
the earlier record was preserved.

Configuration writes, flashes, BOOTSEL transitions, controlled reboots, Pico
Wi-Fi cycles and allocation probes remain zero.

## Execution repairs

The executor was adjusted to use WTP for exact live job identity while keeping
Console as the independent state/output observer, drain queued network events
before installing the receive-drop filter, and wait for WsprryPi's reconciled
owner/lease/remote-state snapshot before production abort. The raw auditor was
also corrected to distinguish the direct run's initial storage baseline from a
production case's single GET/PUT/GET triple.

Fixture restoration originally required reuse of the preflight process ID.
That condition is invalid when an authorized packet deliberately pauses and
restarts the installed service. The fixture now requires both preflight and
restored process IDs to identify active processes, while the existing host
checks still require the service active, the exact installed binary, enabled
and active recovery timer, restored routes/interfaces and removed namespace.
Twenty-one focused fixture tests pass, including the new Package 7 bounds,
retained-Wi-Fi and restarted-service cases.

## Adversarial review and repair

The first adversarial review found two publication defects:

1. the prompt counted the accepted cross-cutting `FEATURE.5` row as a nineteenth
   R4 row, although the machine matrix contains eighteen R4 rows; and
2. the sanitized-result validator bound source/image/boot/device but omitted
   the selected clock, divider, engine, renderer and listener configuration.

The prompt now distinguishes eighteen R4 rows from `FEATURE.5`. The validator
binds the complete candidate, exact row partition, packet identity, every
charged attempt, foreign/storage states, lost-operation relationships,
production identities and mutation order, current regressions, source impact,
eleven failure hashes, both final inventories, all restoration gates and the
24-file raw-evidence hash manifest.

The broad suite then exposed a historical-auditor drift: Package 6 compared its
recorded CMake hash with the current worktree, so Package 7's host-test
registration invalidated an otherwise immutable Package 6 result. The Package
6 auditor now binds that CMake assertion to the Package 6 closeout commit while
still rejecting any current Pico runtime source drift. Its four focused tests
pass again.

The final Package 7 summary assessment rejects all **33** independent mutations and
revalidates the intact publication before and after the mutation set. It covers
status and row count, full candidate identity, packet and budget changes,
foreign/storage evidence, each lost-operation relationship, production state,
terminal, request and wire mutation order, regressions, source impact, failure
retention, final state, restoration and evidence hashes. A separate private
raw-evidence assessment rejects 21 alterations, including wrong source, image,
boot, session and job; incomplete writes and framing; delivered or acknowledged
lost replies; capture loss; foreign success; changed ownership; an accepted
storage write; production owner, state, ABORT, terminal and wire defects; budget
inflation; and incomplete restoration. It revalidates the intact raw set
afterward and performs no device or network operation. No actionable finding
remains.

## Validation and final state

The private raw-evidence auditor passes after the final validator strengthening
and reproduces the sanitized result. The focused Package 7 suite passes seven
tests; the fixture suite passes twenty-one. Python syntax, JSON parsing and
repository whitespace checks pass. A host configure/build succeeds and the
complete registered host suite passes **70/70** after the Package 6 historical
auditor repair.

Final independent inventories show both boards Empty, inactive, unowned and
schedule-disabled. Pico A retains its exact source/image/boot. The shared RF
reservation is Released. The isolated namespace and fixture subnet are absent.
The installed WsprryPi binary and INI hashes match their baselines, its service
is active, Transmit is disabled, the `rp1-gpclk` backend remains selected, boot
enablement remains Never and the Wi-Fi recovery timer is active/enabled.

## Remaining boundary

Package 8 owns R5 network, storage and autonomous lifecycle. Package 9 owns R6
sustained mixed operation after R1-R5 pass. R5, R6 and full Phase 11.5 remain
open; there is still no accepted complete Phase 11.5 configuration.
