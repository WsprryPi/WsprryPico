# Execute Phase 11.5 R3 to an evidence-backed disposition

This is the comprehensive prompt rendered for the user's instruction to complete
R3, execute the work, adversarially review it, fix findings, repeat the assessment,
commit/push and report. It is a work specification; generated packet fields do
not themselves supply hardware authorization.

## Objective and starting point

Work in `/Users/lbussy/GitHub/WsprryPico`, branch `devel`, initially
`1f2b688472cbafcddbdf926cd72378330e55d0be`. The companion is
`/Users/lbussy/GitHub/WsprryPi`, branch `devel`, initially
`2350eb402cd91dff1296371e60ff7162e07a35d1`. Preserve newer user work. Read each
repository's applicable instructions. Do not touch `Wsprry_Pi_Docs`.

Complete R3 saturation/reclamation under the current Phase 11.5 plan. R1 remains
5/5 and R2 7/7 under their existing change-impact review. R3 has zero accepted
physical assertions; A1 and A1b failed in tooling. Preserve both attempts,
including missing A1b HTTP bytes and the incomplete observation. Do not call
those target failures or acceptance passes. R4–R6, Phase 11.6 and Phase 13 are
outside this work. No automatic expansion of QRSS duration is included.

The initial-state descriptions below are historical admission inputs, not live
device status. The [current review](phase11-5-r3-completion-review.md) records
A1c/A1e/A1f execution and the unexecuted A1g proposal. R3 remains incomplete.

Current source candidate: `2e43110f05304efdc2ae25c298baa0ef6426955b`, embedded
`2e43110f0530`, physical 138 MHz/divider 1/RAM/listener on, GP2 PIO/DMA. Physical
UF2 SHA-256: `7e6e732cc7a9e196609413dfe228781a725ece56bed1b4a99a96d1cc8741baf6`.
Changes to Python acceptance tools do not change this firmware identity.

DUT A: serial `0BF4B4AEC9FFB344`, WTP ID `fd6127d11d6aca42a9905fa3fb1bf1d5`;
last verified boot `9c5aec394269e0b57ca16d73ad3d12b6`. Last state was Complete,
inactive, unowned, with job `91bd2c3d57e3e74f7de183203796f463` retained. Verify
again: terminal expiry may have changed it. B is read-only serial
`CDDBF8767C506C07`, WTP ID `29f20b7342051ef947aa56cb9d4fab42`, inhibited boot
`feffcd075ab6cb0b74e7e0c2fde6c87f`. Unknown output, unexpected boot or firmware
fault stops dependent hardware work; never infer inactivity from a closed port.

The user chose **keep the test configuration**. Preserve disabled schedules,
test SSID/credentials and time.local configuration. Actual cumulative CONFIG
saves are 37 and heap probes six. This work plans zero CONFIG saves, heap probes,
flashes, reboots or Wi-Fi OFF/ON commands. The old device-restoration timer was
cancelled. Do not reactivate original-configuration restoration. Reuse the
hash-bound retained Wi-Fi input when creating the isolated AP, rather than
regenerating a password and rewriting Pico configuration.

Host is `wspr5`, boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`. Use SSH outside the
sandbox. Keep installed WsprryPi PID 1957 and executable SHA-256
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273` unchanged.
Use the existing pinned test executable from production source
`6f65d5c7d202569102459ab68d7c9ea079b96f35`, binary SHA-256
`122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`, and native
TLS observer SHA-256 `fd70cde276b04aa08e771e12b83335a89aae24e050e2f2c5e56ed6848eb1a7bc`.
Private credentials stay on wspr5; never commit them or disclose configuration
secrets in evidence summaries.

After A1c exposed persistent rejoin authentication failure, the separately frozen
[A1e packet](phase11-5-r3-retained-a1e-execution.md) adds one bounded idle Wi-Fi
OFF/ON recovery cycle. It prospectively amends the zero-Wi-Fi-command assumption
for A1e only, preserves zero CONFIG/flashes and does not claim R5 acceptance.
Automatic approval review initially rejected the added hardware action. The
user then explicitly approved A1e; its one OFF/ON cycle was executed and consumed.
A1e completed one Tone before a harness failure. A1f subsequently completed two
Tones but failed its frozen audit; neither attempt supplies acceptance. The
[A1g proposal](phase11-5-r3-retained-a1g-execution.md) requires agreement on its
explicit prospective observer criterion before execution. It adds no Wi-Fi cycle.

## Physical envelope and authorization handling

The prior unchanged-wiring confirmation remains applicable: each Pico GP2 and
the conducted GPSDO input enters the combiner through 20 dB; combiner output
passes through 20 + 10 + 10 dB to the SDR, 60 dB per path, with 50-ohm loads and
no filters. Preserve B output, GPSDO settings, SDR settings, management links,
wspr5 GPIO4 and the physical wiring.

Render each concrete packet before execution: frozen helper/input hashes,
unique root/nonce/job IDs, exact triggers and expected rejections, deadlines,
RF-on total, cleanup and stop conditions. The current user instruction requests
execution of this completion work; retain that instruction and the prior wiring
confirmation in the execution record. Do not reuse spent A1/A1b packets. If
approval review requires more explicit authority for a concrete action, complete
unblocked preparation/review first and report the exact rejected action/reason.
Never broaden or conceal an approval-review rejection.

Use only finite Tone jobs at 135,500 Hz, each at most the CAPS limit of
110.592 seconds, maximum 162 events. Multiple same-frequency events may exercise
maximum valid event allocation. At most 40 separately frozen jobs and
4,423.68 seconds RF-on across this completion effort, including failed attempts.
The ordinary TLS/slot case uses two 100-second jobs. These are ceilings, not
permission for undefined traffic or for resetting a faulted device. New firmware
or a different RF envelope requires its own concrete review before execution.

Use the existing isolated three-radio host fixture: wlan0 AP
`2c:cf:67:62:76:66`, wlan2 client `e8:4e:06:ae:d7:09`; retain management eth0
`2c:cf:67:62:76:64` and wlan1 `90:de:80:47:b9:da`. AP/client/DUT are
10.77.15.1/.2/.10. No NAT, forwarding or management default-route changes.
Independently arm owned host cleanup before setup; maximum fixture window
14,400 seconds plus 600 seconds cleanup. Preserve permanent time.local,
chrony/GPS-PPS/Avahi and installed WsprryPi. If a separate later window is needed,
freeze it explicitly rather than extending an active timer implicitly.

## Execute in this order

1. Verify repositories, staged artifacts and current host/device identities.
   Reconcile the retained job using fresh STATUS. If already Empty, do not
   issue a cleanup mutation. If the exact job is Complete/inactive/unowned,
   a bounded cleanup CLAIM/RELEASE may remove current-job state while preserving
   terminal history. No LOAD/ARM/ABORT belongs to that cleanup session. A failed
   or output-unknown job is not eligible for this operation.
2. Implement a retained-configuration fixture/controller lifecycle. Test it
   hardware-free, including stale identities, modified helper/input hashes,
   missing raw evidence, failed workers, completed owner expiry, cleanup failure
   and packet replay. Keep ordinary acceptance validation separate from failure
   observation. Preserve bytes before parsing and use actual response producers
   or recorded target bytes for integration fixtures.
3. Execute corrected TLS/slot assertions first with the existing actual RF-off
   production controller. Audit the full run before claiming any assertion.
   On failure stop dependent injections/jobs, retain observation where possible,
   reconcile terminal output, and preserve the attempt. Diagnose and repair
   locally, review/test, and freeze a new attempt if within the stated bounds.
4. Implement and execute all remaining independently scored paths below. Valid
   allocation must be established idle where mutation under ownership is
   prohibited; BUSY under RF cannot establish valid maximum capacity. Keep
   intended overload separate from supported load. Compare the measured resource
   costs before selecting reclamation repetitions.
5. Run three equivalent reclamation cycles of the measured highest-resource
   path. Establish equivalent cache/session/job/terminal cardinality and warm-up.
   Include 360-second replay/session expiry observations where needed. A terminal
   expiry assertion requires at least 3,660 seconds or another source-supported
   observation bound; do not infer it from a short quiet period or a reboot.
6. Run the complete raw evidence audit, followed by an adversarial assessment.
   Mutate identities, raw frames, byte lengths, counters, deadlines, job/epoch
   brackets, outcomes and final-state equivalence; every corruption must fail
   the applicable gate. Review source against every claimed mechanism. Fix
   actionable findings, rerun affected checks and repeat the assessment. Physical
   claims invalidated by repairs require affected fresh physical evidence.
7. Update the ledger/results/reports. Commit and push reviewed scoped changes
   to origin/devel in each authorized changed repository; verify clean state and
   remote parity. Report remaining blockers precisely if R3 cannot be closed.

## Mandatory R3 assertion register

| IDs | Required independently evidenced paths |
| --- | --- |
| TLS-VALID | Fresh authenticated TLS 1.3 HTTPS control, correct peer/ALPN and actual status framing/body during independently observed Running RF. |
| TLS-FAIL | Each distinct target failed-handshake lifetime, including alert acknowledgement and bounded failed-alert wait where independently reachable. Reuse unchanged certificate semantics only through explicit source-impact mapping. |
| TLS-SLOW | Activated silent/slow handshake deadline, distinct from pending expiry; fresh authenticated recovery. |
| SLOT | Supported active connections, pending admission, excess rejection, pending expiry and the separate post-handshake duplicate-WTP rejection. |
| HTTP-PARTIAL | Partial headers and partial bodies; each intended timeout origin and fresh recovery. |
| PROGRESS | Stalled client writer and stalled client reader/output; distinguish HTTP's activation deadline from established WTP progress timeout and endpoint backpressure. |
| JOB-MAX | Successful idle admission of CAPS maximum valid duration/events, then complete physical execution with the corresponding traffic and resource observations. |
| WTP-MAX | Individual 65,536-byte WTP payload boundary and defined over-bound rejection, with correctly framed bytes and intended parser/admission-layer evidence. |
| HTTP-MAX | Individual 32,768-byte HTTP body boundary and over-bound rejection; distinguish transport size admission from application validity and ownership. |
| BROWSER-MAX | Actual 30,000-byte browser file admission and 30,001-byte rejection through the browser path; do not replace browser admission with a direct HTTP client. |
| COMBINED | Predeclared unsupported simultaneous maxima, classified rejection at the intended layer and bounded recovery without RF starvation or corruption. |
| USB | Parser pressure and unread-output/backpressure, independently observing the RF owner without stealing the sole USB endpoint. |
| RETAINED | Replay capacity, logical-session capacity, terminal capacity, overflow, measured expiry and ordinary reuse; use current source/CAPS rather than assumed legacy counts. |
| RECLAIM | Recovery for each distinct trigger and three equivalent cycles of the measured highest-resource path, with resource equivalence and expiry accounted for. |

Split grouped IDs into concrete subcase IDs before freezing the relevant packet.
A claim of unreachable/equivalent paths needs exact source evidence and a review
of the governing requirement; it must not silently remove a physical gate.

## Evidence and completion rules

Console INFO contains scheduler status and top-level RF launch/resource metrics;
WTP STATUS contains job/owner authority. `/api/v1/status` uses `job`, `standalone`
and `transport`. HTTP status-code validation must not assume reason phrase `OK`.
Bind every pressure interval to fresh raw-audited INFO/STATUS, exact boot/job/owner
and launch epoch. Preserve the final raw response even if sample validation fails.

Retain 32 KiB heap reserve, both 4 KiB stack guards, unchanged unexpected failure
counters and R1's demonstrated largest-request bound unless a separately measured
valid capacity case establishes a reviewed replacement. Full-block critical
budget is 2,849,391 ns at 138 MHz. Short predecessors need their own word counts
and 25% reserve; never add overlapping maxima or relabel cumulative maxima as
per-job results. Validate launch, complete tail, RF continuity and authoritative
inactivity independently of browser/STATUS success.

For existing production load, retain `single-flight-admin-v1`, its five-second
transaction bound and recorded eligible-offer delay. Ordinary browser traffic
and injected pressure are distinct. Preserve 10/15/30-second target mechanisms,
applicable observation allowance and authenticated recovery within 15 seconds.
Do not relax these after a failure to obtain a pass.

Close R3 only when every mandatory subcase has applicable evidence, three
reclamation cycles pass, all actionable review findings are resolved, and final
output/configuration/host state is verified. One completed Tone, a passing unit
suite, a repaired parser or a passing initial TLS packet is insufficient.
Report the exact passed/failed/not-run assertion counts and remaining work;
never report preparation as physical acceptance. Keep the user's retained test
baseline and all historical failures intact.
