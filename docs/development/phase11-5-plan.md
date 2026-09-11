# Phase 11.5 target resources and contention

Status: **OPEN; instrumentation and campaign preparation. P0 read-only inventory completed; no flash, jobs or RF campaign executed.**
This is the joint implementation and acceptance plan, coordinated by Pico.
The [review](phase11-5-review.md) records findings and executed checks. Phase 11.4
is [closed within its inhibited matrix](phase11-4-controlled-soak-run.md).
Neither that idle soak nor the host tests below establishes physical RF-worker
contention. Phase 11.6 independently measures conducted RF; 11.7 is joint closure.

## Clock acceptance ownership

User-confirmed division on September 11, 2026:

- **11.5:** resource and contention acceptance for each PIO clock selected for
  11.6; memory, both stacks, refill/launch and contention results bind the exact
  firmware and actual clock. Recalculate every deadline for each tested clock.
- **11.6:** per-band/per-mode conducted RF acceptance at those selected clocks.
  Investigate an alternative clock only for a failure or unresolved selection.
  Selecting another clock requires repeating the affected 11.5 checks before
  accepting that configuration.
- **13:** systematic band x mode x clock comparison, final supported
  configurations, filters, spectral qualification and release firmware.

| PIO clock | Selection for this campaign | 11.5 accepted configurations |
| --- | --- | --- |
| 138 MHz | Selected candidate for 11.6 | None yet; physical checks pending |
| 132 MHz | Not selected | Untested for 11.5 |
| 150 MHz | Not selected | Untested for physical 11.5; inhibited 150 MHz evidence is separate |

No comprehensive RF band/clock sweep belongs to this campaign. Publish the
accepted exact image/clock list only after its required evidence passes.

## Ownership and starting identities

Pico owns firmware instrumentation, this matrix, evidence admission and normative
WTP. Pi owns its production client, load generation, host API and companion
`docs/development/phase11-5-review.md`. No operator-manual repository changes.

- Pico: clean devel `f20ae5d9fd091155b9f96b6869053029a86891b7`, independently
  matching origin/devel on September 11, 2026.
- Pi Mac: clean devel `89f23e5d10c8a46ead9f37c7cefa8867280ac4df`; origin/devel
  advanced to `a4eb591813b19ece8bba30f6ca072066670c7d1d`. Incoming source
  `923ab570fe53ef2ccca7d12e519c9dc36adf7e93` adds bounded STATUS keepalives
  during future scheduling. After direct user confirmation, the clean Mac checkout
  was fast-forwarded to that exact revision; the original approval rejection is
  retained in the review.
- wspr5 source: clean devel `a4eb591813b19ece8bba30f6ca072066670c7d1d`.
  Installed `/usr/local/bin/wsprrypi` is a different artifact: SHA-256
  `c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`.
  Initial installed INI SHA-256:
  `e4158b2b041355f8cffea0388c8ce286c37d2a66d2d3a6e9c85e3af5f238bbc8`.
  No installed executable or config replacement is part of this plan.

OS inventory only, at approximately 11:05 UTC:

| Role | Observed identity | Initial state |
| --- | --- | --- |
| Pico A candidate | USB `0BF4B4AEC9FFB344`, Console if00 / WTP if02 | P0 verified inhibited, empty, unowned, output false; ttyACM3/4 |
| Pico B comparator | USB `CDDBF8767C506C07`, Console if00 / WTP if02 | P0 verified inhibited, empty, unowned, output false; older image remains distinct |
| Ethernet management | `2c:cf:67:62:76:64`, eth0 | Up, 192.168.1.54 |
| Initial test AP candidate | `2c:cf:67:62:76:66`, wlan0 | Down |
| Ordinary management radio | `90:de:80:47:b9:da`, wlan1 | Up, 192.168.1.117; preserve role |
| Independent client candidate | `e8:4e:06:ae:d7:09`, wlan2 | Down |

wspr5 boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`; installed service active,
Wi-Fi recovery timer enabled and active. Initial temperature 49.9 C and throttle
flags zero. Both USB topology and network routes must be recorded again at run
admission. Names and IPs in this table are observations, never selection keys.

P0 independently verified these full device IDs and certified names:

- A: `fd6127d11d6aca42a9905fa3fb1bf1d5`, station `88:a2:9e:0a:60:df`,
  `wsprrypico-0a60df.local`.
- B: `29f20b7342051ef947aa56cb9d4fab42`, station `88:a2:9e:0a:9d:89`,
  `wsprrypico-0a9d89.local`.

P0 readbacks on September 11, 2026:

| Board | Runtime revision | Boot |
| --- | --- | --- |
| A | `802c91a7b86e-dirty` | `6dde51620f660879680d8335d8bbc71c` |
| B | `dbf1d86f0885-dirty` | `4e2fb851c08b278dd4b977104d2c2aaa` |

Both reported `inhibited-standalone-simulator`, disabled schedules, empty
terminal history and synchronized UTC. Their old INFO does not expose system
clock configuration; the historical 150 MHz identity is not a fresh clock
readback. No present UF2 hash is inferred solely from a revision string.

Current user-confirmed wiring: both GP2 outputs and the GPSDO each enter the
combiner through 20 dB attenuation; the combined path adds 20 + 10 + 10 dB
before the SDR. Each input therefore has 60 dB fixed attenuation, plus combiner
insertion loss. The attenuators provide the reported 50 ohm load. There are no
filters. USB inventory identifies the SDR as RSP1B. This setup supports a bounded
conducted diagnostic proposal, not spectral or output-network qualification.

The user's requested read-only GPSDO query used `/home/pi/lbgpsdo/lbe142x.py`
from clean revision `541abd200210145fb36e83c9d6137cb56cdb5dcf`.
USB serial `0673ED0FA107` identifies an **LBE-1421**, firmware 1.9 (the user had
called it LB-1420). Both outputs were enabled at 10 MHz, LOW drive, PPS not
selected, satellite/PLL locked, antenna OK. No GPSDO setting was changed.
The record does not infer which of its two sockets enters the combiner.

## Implementation sequence and measurement contracts

1. Review current source and history; preserve failed 11.4 attempts and add
   current-status pointers to historical introductions. Render this plan.
2. Repair observer effects in RF worker snapshots. Ordinary RPCs must not scan
   the core-1 canary; an explicit metrics request runs the probe on its owning
   core and reports probe count and maximum elapsed cost. Service-gap maxima
   already include preceding poll/probe work; do not add max_poll a second time.
3. Add narrow, allocation-free RF observations with explicit sequence/epoch and
   timer semantics. IRQ entry is later than DMA completion. Prefer actual
   successor DMA remaining-word observations around descriptor preparation to
   expose the remaining hardware reserve; never label IRQ entry as hardware
   completion. Cover full, short, tail and launch paths. Missing instrumentation
   or coverage leaves the deadline gate open, even if STATUS succeeds.
4. Establish allocator identity from the actual ELF/map and pinned toolchain.
   Separate allocator live/peak use, arena free space, uncommitted linker heap,
   TLS subset, fixed lwIP arena/pools, static RF buffers and two reserved stacks.
   A linker-capacity-minus-uordblks estimate is not largest-block availability.
   Any largest-block allocation probe is separately idle-only; no destructive
   probing during Armed/Running. General allocation-failure instrumentation and
   transient peak coverage require their own proof before memory acceptance.
5. Host negative tests, separate ASan/UBSan and worker TSan; four linked images
   with current dependencies; static stack/call-chain review and clean-source
   actual interop in both directions. Freeze exact artifacts and budgets before
   requesting the physical campaign. No circular metadata-only repinning.
6. Authorized physical baseline, short cases, review, then sustained mixed load.
   Repair a failed case using a new attempt and preserve the original. A changed
   image needs new affected physical results. Commit sanitized evidence only.

Firmware build inputs remain SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`, Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, CYW43
`055d64274b014dd7b1c2fc94d26e8a18face7124`, TinyUSB
`86ad6e56c1700e85f1c5678607a762cfe3aa2f47`. Run current CMake verification,
including actual linked path overrides. Never substitute the obsolete SDK 2.3.0.

Candidate physical clock: **138 MHz**. Configure it explicitly and verify the
actual target configuration before accepting a result. Standard inhibited firmware runs at 150 MHz; it is a separate baseline.
The 16,384-word buffer represents 524,288 samples: 3,799,188.406 ns at 138 MHz,
3,495,253.333 ns at 150 MHz. Ten zero words form the finite tail; short data
blocks have their own smaller intervals. Timer samples are integer microseconds,
even where serialized in nanoseconds. Allow at least one tick per endpoint when
bounding differences; no sub-microsecond physical precision claim.

Detailed endpoint semantics, missing coverage and allocator limitations are in
[Phase 11.5 metric definitions](phase11-5-metrics.md).

Both stacks reserve 16 KiB in the physical image. Canary observations are lower
bounds on touched extent; combine compiler .su frames, reachable call chains,
interrupt nesting, exception frames and a justified allowance for unobserved
paths. Record scan time and its contribution to contention. The standard image
does not execute the physical core-1 worker. Inhibited packet/shutdown tracing
is absent from the physical image; do not transfer its timing observations.

## Predeclared workload matrix

The following are proposed bounded execution packets. Every result must name
its final image hash, boot, job IDs and actual payload lengths. Numerical pass
budgets below are candidate engineering criteria, not a measured envelope.
The [checked acceptance register](phase11-5-register.json) tracks readiness
without treating NOT RUN as PASS. Validate it with
`python3 scripts/validate_phase11_5.py docs/development/phase11-5-register.json`.
The checker rejects cross-image/clock/device gate reuse; reviewed references
still require independent raw-evidence assessment.

Common nominal load N: one authenticated production WTP controller, one logical
session, fresh request IDs, STATUS at 1 Hz when the integration supports it;
its normal scheduler policy remains authoritative. One browser principal uses
manual-equivalent HTTPS status at 0.2 Hz and one page reload per 30 seconds.
USB INFO at 1 Hz and a separate USB WTP observer at 0.2 Hz, with one exclusive
owner per endpoint and a persistent logical observer session. Measure achieved
rates; skipped work or backpressure cannot silently reduce the declared load.
The embedded page contains its own script/style; also fetch the real asset paths
individually. No UI redesign or browser trust changes are proposed.

Common quiet period Q: 360 seconds before/after a family, all test network
contexts closed, same USB sampling phase and controlled retained job/history
cardinality. Replay/session expiry is 300 seconds; TCP state and DNS caches must
be measured, not presumed expired. Terminal history lasts 3,600 seconds and
must be compared at equal cardinality or after a separate 3,660-second quiet
observation. Retain warm-up allocations and distinguish their provenance.

| ID | Workload, duration and repetitions | Expected result and evidence |
| --- | --- | --- |
| A1 | Network control off/on, standard/physical linked layouts; four builds | Actual static/heap/stack/journal limits and component hashes; compile only |
| A2 | Inhibited and physical idle; Q each; controller alone then N for 180 s each | Matching boot/engine/clock, rates, heap/stack/TLS/lwIP; no unexplained failure |
| A3 | Physical Loaded, Armed, Running; three finite 10 s Tone jobs, N | Distinct state coverage, exact owner and no idle-only management while owned |
| B1 | Persistent WTP plus actual browser page/assets/status, N for 300 s, 3 repeats | All nominal exchanges within declared latency, no owner interruption |
| B2 | Fresh valid handshake every 5 s; wrong CA/client/name and malformed input separately, 20 each | Positive controls pass; each negative classified at its intended layer |
| B3 | Slow handshake 12 s, partial headers/body 17 s, stalled readers/writers 32 s; 3 each | Existing 10/15/30 s and WTP 5 s bounds; measured recovery, no false inactivity |
| B4 | Two active contexts, one pending, then fourth client; 20 sets at 5 s spacing | Supported slots retained; excess client rejected; timeout is not valid-auth rejection |
| C1 | CAPS-max valid jobs; WTP 65,536-byte payload and HTTP 32,768-byte body separately, 3 each, then together | Exact individual admission vs deliberate simultaneous overload; no promise all maxima fit |
| C2 | USB parser and unread-output pressure during N for 180 s, 3 repeats | Bounded per-endpoint rejection; independent observation and owner preserved |
| C3 | Retain 8 terminal records; 8 replay entries/session; 16 logical sessions, then 17th; one sequence | Explicit exhaustion vs normal session reuse; recovery after measured expiry; no hidden churn |
| C4 | Foreign USB/browser CLAIM/ABORT/RELEASE during Loaded/Armed/Running, 3 each | BUSY/NOT_OWNER at correct precedence; matching job and owner unchanged |
| D1 | Disconnect after acknowledged ARM; one 20 s finite job, 3 repeats | Local completion, same-session HELLO/STATUS reconciliation, no automatic LOAD/ARM |
| D2 | Lost LOAD/ARM/ABORT responses, one each; TCP reset/EOF and delayed resolver, 3 each | Bound request effects and exact replay; preserve unknown until authority returns |
| D3 | Isolated DUT lease .10 to .20 and external AP link loss for 15 s, one each under N | Stable certified name/boot/job; native NSS plus production recovery; no ordinary-LAN changes |
| D4 | Idle-only Wi-Fi OFF/ON after cleanup, 3 cycles of 150 s OFF | Actual goodbye/cache/probes, recovery within 120 s; retain DNS/SNTP competition |
| E1 | Idle config/schedule change and restoration; at most 32 journal writes, one rotation only if achievable within cap | Readback, revision, watermark and flash-lockout service recovery; otherwise rotation remains open |
| E2 | Same writes attempted while owned/Armed/Running, 3 each | Rejected without flash write, owner loss or job disruption |
| F1 | Tone, QRSS, FSKCW, DFCW, WSPR from CAPS; 3 launches each under N | Actual PIO/DMA continuity, launch guard, short block and zero tail; not independent RF decoding |
| F2 | Browser-owner and production-owner abort during N; 3 Running and 3 Armed each | Matching terminal abort and confirmed shutdown; no foreign-owner bypass |
| G1 | After A-F pass: 30 min N, finite jobs totaling at most 20 min RF, interleaved 5 min quiet observations, then Q | Zero nominal resets/faults, complete observers, bounded retained memory at equal state |

F1 proposals use nominal 135,500 Hz (four-tone WSPR spacing 375/256 Hz;
FSKCW/DFCW shift 5 Hz), zero configured correction, three-second QRSS-family
elements, short off tails and full WSPR 110.592 s. Maximum physical event count
is 162, not the generic WTP maximum 512. Exact encoded jobs and total RF-on
time must be generated, checked against observed CAPS and included in the final
authorization packet. No RF frequency or path is approved by this document.

## Candidate pass budgets and stop rules

Freeze before running, with reviewed instrumentation and actual artifact identity:

- Full-block critical-path bound at most 75% of the actual buffer interval
  (2,849,391 ns at 138 MHz), leaving at least 25% for unobserved variability.
  This is an engineering margin, not WCET. Matched reserve observations must
  additionally pass for short blocks and tail preparation. Separate maxima may
  only be used as a documented conservative bound with overlap accounted for.
- Both stacks: measured touched extent plus reviewed unobserved/IRQ allowance
  must leave at least 4,096 bytes. The allowance cannot be zero or an invented
  fixed number; derive it from the linked call chains before admission.
- General heap: preserve the existing 32,768-byte recovery reserve; demonstrate
  the largest necessary allocation for each accepted combination and allocation
  failure recovery. TLS counts are a subset of that heap, never an extra arena.
- Nominal end-to-end STATUS/abort confirmation: at most 5 s for persistent
  authenticated control; fresh HTTPS including handshake at most 15 s. These
  are proposed operating targets within existing transport ceilings, not changes
  to the protocol's output-disable deadline or an observed pass.
- Overload cleanup: classify rejection within the relevant 10/15/30 s server
  deadline plus 2 s observation allowance; fresh authenticated recovery within
  15 s after slot reclamation. Network lifecycle recovery retains 120 s.
- USB observation gap at most 2 s at 1 Hz; host-health gap at most 6 s at 5 s;
  no dropped critical RF observations, missing finish markers, observer death,
  truncated packet records or kernel capture drops. Deliberate RF trace sampling
  must report exact coverage and cannot prove unobserved continuity.
- Equivalent quiet retained heap must not grow monotonically across the final
  three equal-state windows and must stay within 1,024 bytes of the matched
  post-cache baseline. Explain every retained difference and retain the initial
  warm-up; this finite run cannot prove absence of every leak.
- Zero unexplained reset, corruption, deadlock, DMA error, TXSTALL, starvation,
  owner violation or duplicate submission in nominal cases. Allocation failures
  are allowed only in declared overload with bounded, authority-safe recovery.

Stop dependent actions on the first unexpected fault, boot change or failed
cleanup. Preserve raw data. No automatic reboot/reflash/job retry/fault clearing.
Disconnected output remains unknown. The mailbox's 100 ms and watchdog's 8 s
are recovery bounds, never RF timing margins.

## Authorization packets and restoration

P0 (authorized and completed; final repeat authorized): on wspr5, serial-bound Console INFO and WTP
HELLO/CAPS/GET_CLOCK/STATUS/PING on A and B, one bounded inspection per board,
at most 60 s each; exclusive endpoint access, no mutations or inherited fixture
empty-state assumptions. Record firmware, boot, clocks, saved-state digest and
explicit output authority. Reuse read-only inspection for final confirmation.

P1 (not ready): wiring and P0 are now recorded. Select A as the candidate DUT;
preserve B as comparator. Resolve the measurement gates in
[metric definitions](phase11-5-metrics.md), then build exact candidate and inhibited-restoration images,
hash them and define the finite jobs before requesting flash/RF permission.
GP2 production output must execute the real PIO program, chained data DMA,
finite zero-tail DMA and actual dual-core memory path. A pin override or dummy
sink cannot qualify that path. No wspr5 GPIO4, GPSDO or comparator RF activation.

P2 (not ready): stage reviewed helpers and separately built production executable
under a new private wspr5 directory. AP wlan0/client wlan2 with separate network
and mount namespaces, NSS and Avahi; wlan1 remains ordinary management. Bind
roles by MAC and verify Ethernet route before mutation. No NAT, forwarding or
test default route into the LAN. A second independent radio/cache case may
temporarily move wlan1 only under its explicit packet. Save and restore the
Wi-Fi recovery service/timer active state and original boot enablement.

P3 (not ready): use the actual Pi application with ancillary GPIO excluded,
explicit WTP selection, separate INI and ports. Preserve singleton 1234. Either
use the existing approved isolation arrangement after reinspection, or request
a bounded installed-service pause only after authoritative provider inactivity
and restart-policy inspection. No installer or installed-binary replacement.

Every physical packet includes an independent bounded restoration service armed
before mutations, owned process/unit/namespace names, disk preflight, host-health
observer, raw fsynced start/end/exit records and independent USB/network workers.
Supervision runs on wspr5 and survives SSH loss. Cleanup cannot blindly reboot an
unknown-output device; retain the blocker and restore only safe host resources.
On successful cleanup restore original device configuration, disabled schedules,
approved inhibited image, radios/routes/power/service states and verify both
boards independently. No trust-store modification is currently proposed.

## Evidence and documentation

Each immutable attempt must bind source revisions and dirty manifests, ELF/UF2
and executable hashes, board/device/boot/clock/engine, compiler/dependencies,
public certificate fingerprints and DNS names, radio/namespace/routes/BSSID,
job/session/request IDs, workload bytes/rates, observer hashes/lifetimes/exits,
timer meaning, coverage/drops and restoration. Host request latency is distinct
from device execution time; correlate clocks using measured uncertainty.
Keep credentials, private config, credential-bearing firmware and raw captures
outside Git. Sanitized results must never turn a runner success flag into proof.

Documentation Impact: update this plan, joint manifest, Pico review, companion
review, relevant metric definitions and stale current-status introductions.
Consider WTP, shared identity, browser API and architecture unchanged unless a
real contract change is needed. The separate Wsprry_Pi_Docs remains read-only;
follow-up paths are `docs/Advanced_Operations/ini_configuration/transmitter_backends.md`,
`docs/Command_Line_Operations/transmitter_backends.md`,
`docs/User_Interface/Setup/Transmitter/index.md`,
`docs/User_Interface/Operations/index.md`, `docs/Advanced_Operations/rest_api.md`
and `docs/User_Interface/Maintenance/network_safety.md`. Publish only measured
limits there after acceptance; no generic RF/band/spectral/release claim.
