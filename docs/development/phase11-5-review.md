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
