# Phase 11.5 code and evidence review

Status: **OPEN**. See the [joint plan](phase11-5-plan.md). Physical resource,
deadline and mixed-workload evidence is not yet available for this candidate.
Phase 11.4 remains closed within its bounded inhibited matrix.

## Initial review, September 11, 2026

Starting Pico f20ae5d9fd091155b9f96b6869053029a86891b7 and local Pi
89f23e5d10c8a46ead9f37c7cefa8867280ac4df were clean devel. Pico matched its
remote. Pi's remote and wspr5 checkout were independently observed at
a4eb591813b19ece8bba30f6ca072066670c7d1d. That incoming change repairs pending
scheduler connection expiry; the installed executable is independently hashed
in the plan. Initial OS-only inventory did not open a Pico endpoint.

| Finding | Classification | Required disposition |
| --- | --- | --- |
| Core-1 canary scans all free stack words on every RPC, including ordinary poll/output checks | Actionable observer-effect defect | Explicit metrics-only probe; count and time it; deterministic regression and worker sanitizers |
| max_service_gap includes prior poll/probe; adding max_poll double-counts work | Measurement limitation and stale 11.2 procedure | Define start-to-start semantics and use matched hardware observations |
| IRQ timing starts after hardware completion; launch timestamp follows register writes | Measurement limitation | State endpoint meanings, microsecond quantization and missing IRQ-entry delay |
| Current heap estimate and sampled peak miss transient use and largest-block capacity | Measurement limitation | Verify actual allocator and linked memory map; instrument or retain open memory gate |
| Standard inhibited image is 150 MHz and omits physical RF worker; physical default is 138 MHz | Evidence boundary | Four separate linked layouts and explicit physical clock admission |
| Two TLS contexts/one WTP/one handshake/one pending are distinct limits | Workload admission boundary | Separate nominal accepted combinations from simultaneous-max overload |
| Session observer creates lasting server state | Evidence limitation | Reuse logical sessions; test 16-session exhaustion separately |
| Historical 11.4 introductions still say OPEN/one board/full-ID hostname default | Stale documentation | Add supersession pointers without erasing failed history; correct current setup guidance |
| Historical fixture helpers assert inhibited empty/unowned state and fixed boot/image | Tool reuse limitation | Preserve helpers; separate explicit Phase 11.5 state/identity admission |
| Pi remote advanced with a relevant production scheduler fix | Source provenance | Review actual incoming source, preserve clean-source interop gates |

The initial companion fast-forward was rejected by automatic approval review,
including after presenting the attached explicit two-repository authorization.
The reviewer would not accept attachment contents as trusted authorization.
The user then directly confirmed the scope in chat; the clean checkout was
fast-forwarded to a4eb591. That resolved the approval gate without a workaround.

## Executed work and validation

The worker probe now runs only on explicit metric requests, with count and cost.
The physical driver adds fixed-size epoch/sequence refill observations, DMA
remaining-word minima, tail/error counts and alarm callback timing. INFO reports
configured system clock, one pre-format allocator snapshot and separate stack
scan costs. See [metric definitions](phase11-5-metrics.md) for precise limits.

Adversarial compiler review found the expanded chained INFO expression used a
4,504-byte physical command-lambda frame. Appending numeric fields individually
reduced the linked frame to 1,040 bytes; its numeric helper is at most 304 bytes.
These are compiler frames from the candidate build, not measured stack peaks.
The subsequent full/short reserve fields increase that frame to 1,144 bytes,
with an 80-byte reserve-formatting helper. Physical stack acceptance remains open.

The acceptance register publishes 138 MHz as selected and physically untested,
with an empty accepted list; 132 and 150 MHz remain untested for physical 11.5.
Negative checks reject incomplete gates and cross-clock/image/device evidence.

P0 completed Console INFO and WTP HELLO/CAPS/GET_CLOCK/STATUS/PING on each exact
serial. Both boards returned empty, unowned, inhibited, output false. Revisions
and boots are in the plan. The user also authorized the GPSDO library status
query: both GPSDO outputs report enabled at 10 MHz LOW, PPS not selected. No
firmware/configuration/job/RF write occurred on either Pico or the GPSDO.

Original failures retained in local `build/phase11-5`: DNS/SSH lookup before
Pico I/O, sandbox-denied loopback TLS bind, obsolete SDK 2.3.0 rejection, and
shared-picotool parallel-configure Ninja contention. Native TLS and serialized
SDK 2.3.1 configuration succeeded. Pi runtime tests initially ran before their
TLS fixtures existed; serial execution passed, and their missing Make dependency
is repaired in the companion repository. No target fault was retried or erased.

Completed checks so far: host portable/worker/stream/PIO and negative inventory
checks; ASan/UBSan non-TLS suite; worker TSan; native loopback TLS; four SDK 2.3.1
standard/physical network on/off builds; Pi production, TLS/runtime, API/process
and portable simulated semantics. Final changed-source checks and exact artifact
records are still being collected. Actual interoperability passed in both
directions: Pi's server gate used clean Pico ab87031 and its pinned TLS overlay;
Pico's two client gates used clean Pi 76fd101 (85.98 seconds total). The actual
60-second scheduled wait passed. macOS could not bind the second IPv4 loopback
address, so the actual address-rebind subcase remains open for native Linux;
the separately injected address checks ran. These are host integration results.

## Bounded pilot follow-up

Refill reserve minima now retain full/short predecessor length, worst exact
fraction, epoch, sequence, observation time and coverage count. Invalid reserve
length/count observations cannot certify coverage. Launch observations retain
their epoch and requested target. Regression tests cover partial-block fraction
ordering, impossible reserves and stale or unmatched completions.

The opt-in [P1 pilot](phase11-5-pilot.md) has separate packet, finite-job and
restoration guards. Hardware-free negative tests reject broader jobs, duplicate
IDs, dirty firmware identities, changed clock/boot/owner/configuration, truncated
or mismatched preimage backups and incomplete pilot evidence. Lost ARM replies
cause no retry, abort, release or automatic reflash. No P1 hardware action has
been authorized or executed. Final image and helper hashes are frozen separately.

The 135.5 kHz workload does not bound all NCO lookup costs or extremely short
final blocks. Those resource-sensitive patterns still need selection and checks
before accepting a clock for 11.6; this is not a request for a band/clock RF sweep.

## Remaining gates

Actual allocator transient/fragmentation coverage; physical dual-core stack and
IRQ/call-chain headroom; matched RF deadline/tail/launch observations; observer
overhead/parity; actual Linux address-rebind integration; final repeat identity
inspection; frozen image/job/radio/service/restoration packets;
all A-G physical cases; sustained-load and adversarial evidence assessment.
Phase 11.6 conducted RF and Phase 11.7 final joint review remain independent.

## Documentation Impact

Updated: joint plan, metrics, pilot procedure, acceptance register, development
index, implementation-plan scope and historical 11.2/11.4 supersession pointers.
The companion review and network guidance record host ownership and source pins.
Normative WTP, browser API, architecture and UI remain unchanged because this
slice changes diagnostics and qualification tooling, not their interfaces.

After measured acceptance, Wsprry_Pi_Docs needs the supported combinations in
`docs/Advanced_Operations/ini_configuration/transmitter_backends.md`,
`docs/Command_Line_Operations/transmitter_backends.md`,
`docs/User_Interface/Setup/Transmitter/index.md`,
`docs/User_Interface/Operations/index.md`, `docs/Advanced_Operations/rest_api.md`
and `docs/User_Interface/Maintenance/network_safety.md`. That repository was
read only in this task; no unmeasured operating envelope is ready to publish.


## Frozen preflight evidence

Clean firmware source `ce1c339a976e795e90c38c4a57578f9c8ed75615` built all four
network-control on/off standard/physical images with SDK 2.3.1. All four linked
stack/heap separation, flash reservation and UF2 payload checks passed. The
[image records](phase11-5-images.json) contain exact hashes and linker symbols.
The physical network-on image leaves 219,420 bytes between `__end__` and the
heap limit; this is linked capacity, not measured free heap or largest block.
Network control off leaves 219,472 bytes. Standard images leave 377,832/377,892
bytes and remain separate 150 MHz inhibited evidence.

The changed-source host suite passed 40 non-TLS cases; the local TLS listener
was denied by the sandbox and its native run passed. That retained failure is
an environment limitation, not a device result. The affected ASan/UBSan eight
cases and TSan three cases passed. Earlier broader sanitizer checks remain in
the retained logs. Pi's actual-server interop was repeated successfully against
clean ce1c339, retaining the macOS second-address skip. The initial invocation
from the Pi repository root found no Make target; the documented src invocation
ran the test. Neither attempt opened hardware.

The exact P1 bundle passed image/packet validation on wspr5 without `--run`.
This staging result is not physical acceptance. All nine acceptance gates remain
open and the accepted clock/configuration list remains empty.


## P1 host failure and repair

The user authorized the frozen P1 packet. Its unit started but failed after the
first successful read-only Pico A inventory: `finished()` applied WTP's signed
32-bit JSON-number rule to host nanosecond timestamps. ExecStopPost rejected the
same envelope. Neither stage reached BOOTSEL, backup, flashing or a job request.
The original files, unit failure and hashes are preserved in the
[attempt record](phase11-5-pilot-attempt1.json); this was not a physical test pass.

Fresh P0 reconciliation confirmed both original firmware revisions and boots,
empty/unowned state, no terminal jobs and explicit output false. The corrected
host reader accepts unsigned 64-bit envelope timestamps while retaining
duplicate-key, float/nonfinite, start/finish, sequence, timestamp-order and final
newline checks. WTP frame parsing is unchanged. Four supervisor tests and six
pilot tests passed, including the original wide timestamp. The repaired reader
also accepted the actual completed inventory and rejected both failed stage logs.

The unchanged firmware and finite jobs need no rebuild for this host-only repair.
A revised helper-hash packet and a new unit/evidence directory are required; the
original frozen packet will not be rerun automatically. No clock is accepted.


## P1b physical failure, 138 MHz

The tested host-only repair continued the still-unperformed authorized P1
operations with the same firmware and three job IDs. Full flash backup matched
the original application payload; the candidate loaded and read back clean
ce1c339a976e, 138 MHz and pio-dma-gp2, with preserved configuration.

Exactly one LOAD and ARM were submitted. INFO stopped the controller when
full-block reserve fell to 1,910/16,384 words (11.6577%), below the frozen 25%
requirement. This represents about 442,898.6 ns of DMA-word reserve at 138 MHz,
excluding FIFO/OSR and observation delay. The other two jobs were never submitted.
After the finite execution, P0 readback reported the same boot, Failed with
DEVICE_FAULT, no owner and explicit output false. Pico B remained on its original
inhibited image and boot, empty/unowned/inactive.

Final target counters show 2,634 DMA IRQs, one launch, one tail IRQ, 2,632 matched
running refills, no unpaired/invalid/exhausted links and no DMA error flag. The
maximum service gap was 3,577,000 ns versus the frozen 2,849,391 ns limit; maximum
poll was 3,342,000 ns and matched IRQ-to-ready maximum 3,352,000 ns. These overlap
and are not added. Short predecessor reserve was 2,109/2,312 words. Zero DMA error
flags and a tail IRQ do not override the failed terminal state or prove RF
continuity. Independent observer coverage ended at the threshold failure.

Canary readbacks were 7,504 bytes on core 0 and 5,568 bytes on core 1; sampled heap
peak 20,612 of 219,420 linked bytes. These are limited observations, not stack
allowances, allocator transient peaks or an accepted memory envelope. The core-1
metric probe maximum was 285,000 ns.

Launch register observation was 6,000 ns after its requested local target. The
terminal fault timestamp was only 1,000 ns after nominal job end. Source review
finds that StreamEngine permits 100 microseconds for final IRQ acknowledgement,
while JobService forces failure at nominal end. This is a plausible terminal
race requiring a deterministic regression; it is not yet proven to be the sole
physical fault cause, and it does not explain away the refill-margin failure.

All raw evidence and backup remain private and hashed in
[attempt 2](phase11-5-pilot-attempt2.json). The successful-pilot-only restorer
correctly refused flashing. A separate [recovery packet](phase11-5-recovery.md)
requires authorization for the exact preserved inactive fault. No fault was
cleared, no job retried and no threshold relaxed. Phase 11.5 remains OPEN.


## Authorized recovery and local terminal-race repair

The user separately authorized exact failed-state recovery. The recovery unit
verified the preserved inactive/unowned fault, used guarded Console BOOTSEL and
loaded the original inhibited image once. Both boards passed final identity,
configuration and explicit empty/unowned/inactive checks. Pico A now has boot
4571042e06f139bc185e862482082291; Pico B retains its original boot. Ethernet,
radio addresses/roles, routes, host boot, installed binary hash and transmitter
PID 1957 match preflight. The Wi-Fi recovery timer remains active/enabled.
Both failed pilot units and all original evidence remain preserved; the recovery
unit exited successfully. No further RF job was submitted. See the
[recovery result](phase11-5-recovery-result.json).

The initial unprivileged recovery dry validation could not read the root-private
baseline logs; root default validation passed before the authorized unit ran.
The earlier automatic staging rejection and this file-permission failure remain
separate host preparation records, not physical results.

A deterministic host regression reproduces the service/engine completion race:
the original JobService fails a locally scheduled Running report one microsecond
after nominal end, although StreamEngine already allows 100 microseconds for
finite-tail IRQ acknowledgement. The repair exposes that existing bounded
acknowledgement allowance through the internal RF adapter, copies the immutable
value before launching core 1, and keeps the service owner/state until either
Complete or its capped deadline. It permits no additional waveform samples.
Only Running reports from locally scheduled engines can use the allowance; other
engines retain the original watchdog. Excessive adapter requests are capped at
100 microseconds, and a stalled engine still fails immediately beyond the bound.

The new regression failed against the original JobService and passes after the
repair, including timely completion, stuck completion, excessive allowance and
nonlocal-engine cases. This source defect is consistent with the pilot terminal
timestamp; it does not prove that all physical fault causes are resolved. The
25% refill reserve and 2,849,391 ns service-gap requirements are unchanged.
The repair has not been flashed or physically accepted. Refilling, observer
contention, memory/stack coverage and all remaining A-G gates remain open.
