# Group 2 capacity and pressure execution basis

Group 1 is CLOSED at checkpoint 043. Group 2 is OPEN. This record now includes
C1–C5, E5 and R5. Checkpoint 048 ends diagnostic period 2 OPEN. Older preparation
statements below are historical, not live fixture state.

## Latest component 6 result

[Component 6](phase11-5-r3-v2-component6-review.md) verified the same installed
image and retained E6 record. The corrected observer passed, but Pico network
readiness remained blocked: firmware reported no IP and CYW43 authentication
failure status -3. No primary LOAD, replay or RF operation ran. Host readiness
and deadline defects are repaired and tested offline; both fixture instances
and independent final A/B state are restored. No new assertion closed. One idle
Pico Wi-Fi recovery cycle is proposed and requires extending the zero-cycle scope.

## Historical component 5 result

[Component 5](phase11-5-r3-v2-component5-review.md) installed the repaired source
`e256633` and completed retained-state preparation. A host observer compared
`launch_epoch` string `"0"` with integer zero and stopped the attempt before
primary LOAD. Raw INFO shows zero allocation failures and faults. The observer
and cleanup defects are fixed with offline regression and altered-evidence tests.
No primary/replay/RF check ran, and no new Group 2 assertion closed. The fixture
is restored; independent A/B inventories verify Empty/inactive/unowned state.
A remains on the repaired candidate. Exact pressure validation needs a newly
bounded continuation; no extra physical attempt was taken.

## Historical component 4 result

The [component 4 review](phase11-5-r3-v2-component4-review.md) records exact C7
host replay, the modeled encoder-refusal path and shared immutable adjustment
storage. Regression and adversarial checks pass; physical acceptance remains
pending. No device access or new hardware allowance was used. Component 3 below
retains its historical result and last verified physical state.

## Historical component 3 result

E6 passed seven idle checks on source `4dad112c8a4c`. C7 stopped before ARM:
LOAD entered Loaded but returned no USB response bytes; the following STATUS
also timed out. No RF or maximum-input stimulus occurred. No new Group 2
assertion closed. Final A/B are Empty/inactive/unowned; F7 is restored.
See the [component 3 review](phase11-5-r3-v2-component3-review.md) and
[result](phase11-5-r3-v2-component3-result.json). Checkpoint 048 remains a
historical old-image assessment; its RF passes do not qualify this candidate.
The remaining entries below preserve their recorded stage in the campaign.

## Closure period 3: executing Option 1, 2026-09-14

Component 2 completed the hardware-free candidate build and review. Source
`4dad112c8a4c0ce4e5be77ecba5c3c460496472c` includes iterative JSON key sorting to remove
additional sort recursion with paged input views. Both inhibited and Standalone
RF images passed their checks. No hardware acceptance assertion closed.
See the [build/review record](phase11-5-r3-v2-component2-review.md) and
[exact candidate identities](phase11-5-r3-v2-component2-result.json).
The component 1 and C6 entries below retain their historical state at completion.

Component 1 is a separate hardware-free step authorized after the prompt was
split into smaller tasks. It corrects the two test setups: JSON boundary values
are placed inside the required object envelope, and reply allocation measurement
begins on the final input byte, including cached LOAD responses. The seventh
reply-page failure and unchanged preparation count are asserted explicitly.

The affected core, endpoint, network, browser, standalone configuration, USB,
RF-stream and PIO-DMA host test groups pass. The maximum input test permits only
4 KiB allocations; failure cases cover the first and later pages, parser closure,
no payload delivery and fresh-parser recovery. JSON boundary tests check Unicode,
escapes, integer limits, invalid inputs and an exact maximum-request SHA-256.
See `phase11-5-r3-v2-component1-result.json` for final checks and source hashes.

Review found no remaining actionable host-side finding in this component.
Target image layout, stack/resource observations and physical C6 workload
acceptance remain unverified. No firmware candidate was built or flashed in
Component 1, and no hardware operations or Git publication were performed.
The working changes remain uncommitted for the next bounded component.

Update after C6: the 65552-byte input allocation failed at core-0 caller
0x1000f361 / input caller 0x1008c1b3. Exact ELF symbolication identifies
`InputBuffer::reserve` in `FrameParser::feed`. Full raw evidence is preserved
under `build/phase11-5-r3-v2-capacity-c6/evidence`; this is a failed supported
case, not overload acceptance. One ARM charged 128 seconds. Final A inventory
confirms the same boot, Complete terminal record, inactive output and no owner;
no completion-audit PASS is assigned after the failed exchange. No new assertion
has closed in this period. C2/C3 historical causality is not retroactively proved.

The narrowly related archived paged-input work is now being completed against
this captured allocation site. It remains uncommitted and unvalidated: initial
builds exposed flat-view call-site adaptations; test allocation accounting also
needs correction and expanded page-boundary checks are pending compilation.
No candidate firmware has been selected, flashed or physically qualified.

The user requested another prompt rewrite. F6 cleanup completed; independent
host checks confirm temporary services inactive, protected files unchanged and
the installed process identity unchanged. Evidence: this period's `f6-state.json`,
`f6-log.json`, and `final-host.json`. The original budget clock continues; 772 RF
seconds remain. A future packet must use a newly established fixture identity,
not the restored F6 namespace or deadline.

The user authorized rendering and executing the closure campaign, adversarial
review, repair/reassessment and commit/push. Four hours monotonic, 30-minute
cleanup reserve and 900 newly charged RF seconds; budget persists in
`build/phase11-5-r3-group2-closure-period3-20260914/budget.json`. Preserve the
previous periods and all 117 pre-existing dirty/untracked files, recorded with
hashes. Pico starts at 1d75d37; Pi starts clean at 820e698. No firmware change is
selected. A/B identities and inactive/unowned state match checkpoint 048;
C4's terminal record has now expired normally, while C5's Complete record remains.

Source-impact review before hardware: between 8921a70 and retained 4da3672, only
`network/api.cpp`, heap metrics C/header and standalone INFO construction change.
The exact RF, job/codec, endpoint/parser and transport timeout implementation
paths checked are unchanged. The API change replaces static-asset string copies
with paged output and changes that asset's memory admission; INFO avoids a
large concatenation copy and adds failure metadata. This supports mechanism
reuse candidates, but is not enough by itself to transfer physical heap/timing
credit. C5 establishes bounded current-image Tone behavior, not maximum-event
or TLS-pressure equivalence. Six partially covered assertions (2.1a/c and
2.2c–f) receive explicit evidence review; no PASS is granted merely for matching
source. HTTP stalled-reader behavior is specifically affected by static-body
allocation and remains subject to targeted physical/resource applicability.

C2/C3 vs C5: allocator/parser logic is unchanged; boot/heap history and TLS
context occupancy differ, and failure metadata exists only on the later image.
Aggregate free memory does not establish that a contiguous allocation fits.
The first combined packet tests the actual required allocation rather than
assuming that C5 repaired it.

Planned RF allocation: C6 is one 128-second FSKCW job, 512 alternating
135500/135495-Hz events of 250 ms, with current 512-event idle admission already
covered by E5. It adds one maximum WTP request plus the original oversize/recovery
pair, persistent native WTP/TLS and three HTTP boundaries on A. This leaves
772 charged RF seconds for separately frozen timeout/USB/overload packets and,
only if justified, an affected repair retest. Each later packet needs its exact
stimulus, count, rate, mechanism, independent observer and deadline before ARM;
this allocation is not permission to run unspecified traffic. No firmware
change, flash, reboot, CONFIG save, Wi-Fi command or heap probe is selected.

The supported combination for C6 is the final 512-event plan/job and retained
state, one resident USB WTP input of 65552 bytes, one established native TLS/WTP
context and independent INFO/status observations. The HTTP maximum cases run at
separate declared HTTPS opportunities; they do not claim simultaneous residence
of both maximum WTP and HTTP bodies. C1's historical 181580-byte peak leaves
38748 bytes against its linked 220328-byte heap, so the additional capacity
case remains a real admission/fragmentation test, not an assumed budget pass.
The current 32768-byte reserve gate and all timing gates remain binding.

The existing, previously prepared Group 2 HTTP probe and auditor changes in
`phase11_5_r3_v2_nominal_load.py` and `audit_phase11_5_r3_v2_hour.py` are being
reviewed for this directly related scope. Their initial bytes are preserved;
publication will identify any adopted existing helper changes explicitly and
exclude unrelated browser/native work.

C6 frozen before ARM: packet `da89cf9f703f126ef71e463336674000373749df3c70f98ec7a2bff9fc7a7373`, archive
`c6be9221978f91aa88c57f2c765e1f087172878856a233bf8001028c2c0aa6dd`, owner `b135b6929baad519552e35c807055ff2`,
job `13b794ae029409ef78740f675c0dd3b8`. F6 deadline 361139582642000 host monotonic ns.
Audit closure manifest `c139adf8cd6d477cde0105393f702996f24bfefc5e434fb31003a22917f18ad9`.
One attempt, 128 seconds charged on ARM; no retry.

Current assertion status before this period's physical work:

| ID | Status | Accepted component or exact remaining requirement |
| --- | --- | --- |
| 2.1a | PARTIAL | E5 revalidates 512-event admission; C1 completion remains accepted on its old identity. C5 verifies one Tone; 512-event contention equivalence remains unproven. |
| 2.1b | PASS | E5 independently verifies 513 and overduration rejection plus exact maximum idle LOAD on the diagnostic image. |
| 2.1c | PARTIAL | Prior maximum-plan, hour and WSPR records remain; complete assertion-level source/resource reuse is not established. No repeated hour campaign. |
| 2.1d | PASS | C5 full 65552-byte frame with valid 65536-byte STATUS payload and owned Running response under independently observed 90-second Tone; exact diagnostic identity above. Original C2/C3 failures retained and unrepaired. |
| 2.1e | PARTIAL | E5 verifies 65537 framing rejection and same-connection recovery while idle; RF case unexecuted. |
| 2.1f | PARTIAL | BF4 exact HTTP maximum remains B-only evidence; A under-RF valid 32768-byte API body unexecuted. |
| 2.1g | PARTIAL | BF4 B HTTP limit/recovery retained; A under-RF 32769 rejection and authenticated recovery unexecuted. |
| 2.2a | FAILED | C2 supported simultaneous allocation failed. No final workload/overlap allocation succeeded. |
| 2.2b | NOT_RUN | Intended unsupported allocation, preserved owner/RF and authenticated recovery missing. Failed supported input is not overload acceptance. |
| 2.2c | PARTIAL | T4 TLS handshake timeout/reuse retained on its identity; diagnostic resource applicability unproven. |
| 2.2d | PARTIAL | T5 failed-alert ACK/unacknowledged lifetimes retained on its identity; diagnostic resource applicability unproven. |
| 2.2e | PARTIAL | T4/T5 slot, one-WTP and pending mechanisms retained; diagnostic resource applicability unproven. |
| 2.2f | PARTIAL | T5 HTTP header/body/stalled reader retained; diagnostic resource applicability unproven. |
| 2.3a | NOT_RUN | Distinct 30-second drained WTP inactivity, closure and authenticated reuse absent. |
| 2.3b | NOT_RUN | Five-second incomplete-input mechanism and recovery absent physically. |
| 2.3c | NOT_RUN | Five-second no-output-progress mechanism and recovery absent physically. |
| 2.3d | NOT_RUN | Actual USB parser pressure during independently observed finite RF absent. |
| 2.3e | NOT_RUN | Actual unread USB output pressure during independently observed finite RF and authenticated recovery absent. |

## Diagnostic period 2: completed, checkpoint 048, 2026-09-14

Execution began at Mac monotonic 713401316391750 ns. The new four-hour budget
reserves 30 minutes for restoration, at most one additional diagnostic image
and one <=90-second physical attempt. The prior period and its charge remain.
No new firmware is selected: source 4da3672 and A boot 0bd82f1324920c360d796988cf31cb5b
are independently confirmed unchanged. B is unchanged, inactive and unowned.

Offline replay through the production StreamEngine/PIO-DMA guard reproduces
Missed with the recorded 25.805 ms refinement and 9.629566 ms pre-launch
uncertainty. The unchanged-mapping control launches. Four pre-launch INFO samples
already show that mapping disagreement after accepted SNTP sample five. This
strongly supports a clock-guard refusal; the interrupt snapshot and hardware
branch were not captured, so C4's exact historical branch remains unproved.
The first host replay used the generic service's 1 ms uncertainty limit and was
rejected at ARM; selecting the deployed 500 ms standalone policy corrected the
replay setup. No firmware guard or uncertainty threshold changed.

The next packet will LOAD only within five seconds of a recent accepted SNTP
sample, verify matching INFO/GET_CLOCK mapping and <=15-second age before ARM,
and start ten seconds ahead. The source schedules its ordinary next SNTP request
64 seconds after an accepted reply. This avoids the observed ordinary-update
window but cannot guarantee that an unexpected network reset will not change it.

R5 is one exact-C4 idle CLAIM/RELEASE, zero ARM/flash/CONFIG/Wi-Fi/probe operations,
packet d7329b92520247345ecc7fd8ed6c8e6074217bb94a84a22c4db3060e874effec.
Host tests reject active output, ownership, identity drift and altered terminal
history. Independent Console capture now latches failure and stops further
stimuli while retaining bounded same-identity read-only evidence. Normal
acceptance still rejects the failure. One valid maximum request is planned;
the oversized-input follow-up is excluded. R5 completed Empty/inactive/unowned,
preserving the exact C4 terminal record; raw audit and four missing-file mutations
pass. R5 evidence archive d5e0b94f8111c37628baba7e1ede78d07ac52f30e2cad29545e2679c93e24199.

### C5 frozen diagnostic schedule

F5 is a new host-only fixture, packet
074c732a455f07ad7a9a9fbbe0f2d54184871562aff8e0f8b9b99ce1af0e1f47,
3600 seconds runtime plus 900 seconds cleanup. Its actual absolute cleanup timer
is 354040071090000 host monotonic ns. No former fixture deadline is extended.
C5 packet d46edf56bd1eaaaae095139ec6cfb39edb627470c769f4d758bed8d7a3d2da83,
archive a88c10762141dee34fd3b9d228e09fd736b20d940b64c99523be5509f2959562,
is frozen with a local auditor dependency manifest before ARM.

One Tone job `0ec6f9c02e30398015c359eb3610497a`, 90 seconds at 135500 Hz, unchanged
conducted route, source/image/boot above. Charge the entire 90 seconds before
ARM. One USB WTP owner/stimulus connection, owner `6757e0a0a2ab27fa905e8ef45d9a4a82`,
session `a832940eb8960757dadf270fca6b7716`. Console if00 remains an independent observer;
WTP if02 is opened once. No B operation in C5, HTTP load, native TLS load,
configuration write, Wi-Fi command, reboot, flash or heap probe.

After the recent-clock admission above, require both WTP and fresh independent
INFO to show Running/output-active before the only capacity request. Existing
`wtp_capacity_frame` generates valid 65536-byte JSON STATUS payload, 65552 bytes
including framing/CRC, request `f797d96e4d1e65e2db06eeefbfdd569f`,
frame SHA-256 `d695d406962f1ddde4506b1a4abef60b611622ed61ee555146d485eb4e99a818`.
Writes are at most 4096 bytes each on that same connection, one five-second
exchange deadline beginning at the stimulus. No retry or oversized follow-up.
A passing transfer requires all bytes written and a same-boot owned Running
STATUS reply. A failure is retained and cannot receive capacity acceptance.

INFO starts every second under the existing single-flight policy; WTP STATUS and
host health every five seconds, each reply within five seconds. Any invariant
failure stops test mutations. Independent Console and host observations continue
to the original 240-second deadline, retaining allocation operation/request/site,
caller PC, observed heap figures and RF telemetry through terminal state. Normal
successful RELEASE follows matching Complete/inactive; after failure there are
no stimulus/release retries. Final independent inventory has a 150-second reserve
and must prove inactive/unowned before host fixture cleanup is credited. An
unknown output state remains unknown and is handled under existing recovery
authority, never inferred from transport loss. No replacement physical attempt.

Source impact: only host harness, auditor and regression test changes. Deployed
allocator/parser/RF/clock code and the diagnostic image are unchanged; E5 is not
rerun. Prior RF equivalence gaps remain. This packet seeks diagnosis, not Group 2
closure, parser repair or acceptance of expected allocation failure.

### Checkpoint 048 outcome and assertion disposition

**One new assertion is closed: 2.1d. No entire sub-issue (2.1, 2.2 or 2.3) is
closed; Group 2 remains OPEN.** R5 retired C4's inactive slot with exact retained
terminal history. C5 then launched once, transferred all 65552 frame bytes and
received the valid maximum STATUS response while the same owner/job was Running.
The exchange took 2.058418207 seconds. Its original result is
`CAPTURED_REQUIRES_AUDIT`; the auditor frozen before ARM independently returns
`FINITE_RF_WIRE_VERIFIED`. Ten altered-evidence cases are rejected. No threshold
was relaxed and no historical failure was rescored.

C5's 141 independent INFO samples, 29 STATUS and 29 host-health observations meet
the original cadence/deadline gates. The 90-second Tone completed and RELEASE
returned Empty/inactive/unowned. Launch delay was 8000 ns, expected DMA/refill/tail
deltas matched, worst refill-to-ready was 2088000 ns and worst RF service gap
2129000 ns. Short-predecessor reserve was 4164/4424 words (94.1%). Allocator peak
140152 of 220328 bytes leaves an 80176-byte sampled aggregate reserve; this is
not a largest-free-block or complete transient-peak measurement.

**The allocation failure did not reproduce.** Every sampled allocator failure
count and retained failure entry/size/caller/input-caller/core remained zero;
TLS allocation failures and DMA errors also remained zero. There is no failed
PC to symbolize. C2/C3 remain valid failed observations on their older image and
boot; differences in boot history, heap layout, prior E5 admission and R5 cleanup
prevent treating C5 as proof of a repair or disproving the earlier defect.
No allocator/parser source changed, no repair was selected, and the abandoned
paged-input work remains archived and withdrawn. The improved post-failure
capture path is host-tested; C5 did not physically exercise that failure path.

R5 and C5 results and raw/archive hashes are in `phase11-5-r3-v2-r5-result.json`
and `phase11-5-r3-v2-capacity-c5-result.json`. F5 was restored at host monotonic
350807833112278 ns, before its unchanged 354040071090000 ns deadline. Cleanup
reported zero failures; independent checks verify permanent host files/services,
installed PID 1957 and executable hash unchanged, fixture units inactive and
both Picos Empty/inactive/unowned with scheduling disabled and configurations
unchanged. A retains the same diagnostic firmware/boot, and C4's Missed record
remains present. B is unchanged on boot 6684b4b197d80cfa0ce83b3aaf205cb0.

This period consumed one job and 90 charged RF seconds, with one launch and
completion. Zero firmware candidates, flashes, BOOTSEL, extra reboots,
configuration writes, commanded Wi-Fi cycles or heap probes. No E5 replay on
hardware, replacement attempt, parser repair or Group 3 work occurred.

The exact historical C4 rejection branch remains unproved; the recorded mapping
change strongly supports the production guard mechanism reproduced offline.
The smallest next decision is whether to authorize a new bounded investigation
of C2/C3 versus C5 heap/boot conditioning before another failure reproduction,
or proceed separately with the remaining acceptance assertions. Either requires
new direction; this period admits no further RF. A repair requires an observed
failed allocation site or comparably decisive source evidence first.

| ID | Status | Accepted component or exact remaining requirement |
| --- | --- | --- |
| 2.1a | PARTIAL | E5 revalidates 512-event admission; C1 completion remains accepted on its old identity. C5 verifies one Tone; 512-event contention equivalence remains unproven. |
| 2.1b | PASS | E5 independently verifies 513 and overduration rejection plus exact maximum idle LOAD on the diagnostic image. |
| 2.1c | PARTIAL | Prior maximum-plan, hour and WSPR records remain; complete assertion-level source/resource reuse is not established. No repeated hour campaign. |
| 2.1d | PASS | C5 full 65552-byte frame with valid 65536-byte STATUS payload and owned Running response under independently observed 90-second Tone; exact diagnostic identity above. Original C2/C3 failures retained and unrepaired. |
| 2.1e | PARTIAL | E5 verifies 65537 framing rejection and same-connection recovery while idle; RF case unexecuted. |
| 2.1f | PARTIAL | BF4 exact HTTP maximum remains B-only evidence; A under-RF valid 32768-byte API body unexecuted. |
| 2.1g | PARTIAL | BF4 B HTTP limit/recovery retained; A under-RF 32769 rejection and authenticated recovery unexecuted. |
| 2.2a | FAILED | C2 supported simultaneous allocation failed. No final workload/overlap allocation succeeded. |
| 2.2b | NOT_RUN | Intended unsupported allocation, preserved owner/RF and authenticated recovery missing. Failed supported input is not overload acceptance. |
| 2.2c | PARTIAL | T4 TLS handshake timeout/reuse retained on its identity; diagnostic resource applicability unproven. |
| 2.2d | PARTIAL | T5 failed-alert ACK/unacknowledged lifetimes retained on its identity; diagnostic resource applicability unproven. |
| 2.2e | PARTIAL | T4/T5 slot, one-WTP and pending mechanisms retained; diagnostic resource applicability unproven. |
| 2.2f | PARTIAL | T5 HTTP header/body/stalled reader retained; diagnostic resource applicability unproven. |
| 2.3a | NOT_RUN | Distinct 30-second drained WTP inactivity, closure and authenticated reuse absent. |
| 2.3b | NOT_RUN | Five-second incomplete-input mechanism and recovery absent physically. |
| 2.3c | NOT_RUN | Five-second no-output-progress mechanism and recovery absent physically. |
| 2.3d | NOT_RUN | Actual USB parser pressure during independently observed finite RF absent. |
| 2.3e | NOT_RUN | Actual unread USB output pressure during independently observed finite RF and authenticated recovery absent. |

## Historical checkpoint 047: bounded attempt ended OPEN

The sole diagnostic C4 was admitted once and reported `MISSED_START` before the
capacity trigger. Raw ARM acknowledgment, JOB_STATE/MISSED_START events, Console
launch epoch zero and both final inventories agree: zero launches, zero capacity
stimuli, zero capacity bytes and zero new allocator failures on this diagnostic
boot. The full 90-second ARM charge is retained. The original runner result stays
`STOPPED_FINAL_STATE_UNVERIFIED`; its admission helper excludes Missed even though
raw final STATUS is authoritative. A separate raw replay verifies Missed, inactive
and unowned. It does not turn the failed physical attempt into a pass.

The allocation defect remains unidentified. C2/C3's two failures remain attached
to their original source and boot. C4 provides no failed-allocation site to resolve.
No repair was selected, the archived parser refactor remains withdrawn, and no
replacement physical test or Group 3 work was attempted. The smallest next
decision is whether to authorize another bounded diagnostic period after reviewing
C4's launch/clock guard evidence and freezing one revised diagnostic schedule.
That decision must precede any further physical attempt or parser repair.

C4's ARM clock and first Missed sample differ in UTC-minus-monotonic offset by
25.805 ms. `StreamEngine::check_clock` can refuse launch after a clock refinement
that makes the armed mapping exceed the current uncertainty. This is a possible
explanation, not a demonstrated cause: the exact guard snapshot/rejection branch
was not captured. No timing threshold, guard or clock policy was changed.

### Historical checkpoint 047 assertion disposition on diagnostic source 4da3672

E5 and C4 use source `4da36726ac6809bdf4e73d281fe13b2393dd3b31`,
UF2 `0153107c517b673bfad7850957c8387a7dbfb12ddb0a3b1e90edb94b804b9a9f`,
ELF `8855dd77cb0057ff8f33f91d02a3447cf39ca96cb2782b606c51f2e44e4f7353`,
boot `0bd82f1324920c360d796988cf31cb5b` on A, Pico 2 W/RP2350,
PIO/DMA GP2, 138 MHz/divider 1/RAM rendering. Historical identity keys and the
pre-change table below remain unchanged. No allocator or parser repair exists.
The diagnostic adds retained failure metadata and INFO output; host behavior is
covered, but physical resource/timing equivalence remains unestablished.

| ID | Status | Accepted component or exact remaining requirement |
| --- | --- | --- |
| 2.1a | PARTIAL | E5 revalidates 512-event admission; C1 completion remains accepted on its old identity. New diagnostic timing/resource equivalence is unproven. |
| 2.1b | PASS | E5 independently verifies 513 and overduration rejection plus exact maximum idle LOAD on the diagnostic image. |
| 2.1c | PARTIAL | Prior maximum-plan, hour and WSPR records remain; complete assertion-level source/resource reuse is not established. No repeated hour campaign. |
| 2.1d | FAILED | C2/C3 supported WTP maximum attempts failed at 4096 bytes. E5 idle passes; C4 sent zero capacity bytes. RF case unresolved. |
| 2.1e | PARTIAL | E5 verifies 65537 framing rejection and same-connection recovery while idle; RF case unexecuted. |
| 2.1f | PARTIAL | BF4 exact HTTP maximum remains B-only evidence; A under-RF valid 32768-byte API body unexecuted. |
| 2.1g | PARTIAL | BF4 B HTTP limit/recovery retained; A under-RF 32769 rejection and authenticated recovery unexecuted. |
| 2.2a | FAILED | C2 supported simultaneous allocation failed. No final workload/overlap allocation succeeded. |
| 2.2b | NOT_RUN | Intended unsupported allocation, preserved owner/RF and authenticated recovery missing. Failed supported input is not overload acceptance. |
| 2.2c | PARTIAL | T4 TLS handshake timeout/reuse retained on its identity; diagnostic resource applicability unproven. |
| 2.2d | PARTIAL | T5 failed-alert ACK/unacknowledged lifetimes retained on its identity; diagnostic resource applicability unproven. |
| 2.2e | PARTIAL | T4/T5 slot, one-WTP and pending mechanisms retained; diagnostic resource applicability unproven. |
| 2.2f | PARTIAL | T5 HTTP header/body/stalled reader retained; diagnostic resource applicability unproven. |
| 2.3a | NOT_RUN | Distinct 30-second drained WTP inactivity, closure and authenticated reuse absent. |
| 2.3b | NOT_RUN | Five-second incomplete-input mechanism and recovery absent physically. |
| 2.3c | NOT_RUN | Five-second no-output-progress mechanism and recovery absent physically. |
| 2.3d | NOT_RUN | Actual USB parser pressure during independently observed finite RF absent. |
| 2.3e | NOT_RUN | Actual unread USB output pressure during independently observed finite RF and authenticated recovery absent. |

### Evidence, validation and restoration

E5's seven idle assertions passed independent raw replay and ten evidence
mutations. R4's one prior-state CLAIM/RELEASE passed raw replay and four missing
evidence mutations; zero RF. C4's normal acceptance audit rejects the final
state. Separate failure classification verifies raw framing/CRC, identities,
single ARM, absence of capacity writes and final inactive/unowned authority.
The originally frozen C4 auditor omitted C4 from its packet whitelist. The later
independent audit adds only that identity and still rejects the run; the frozen
closure and original result are preserved. No retroactive threshold relaxation.

Validation: 70/70 current host CTests; 23 WTP schema, seven raw, one framing and
eight transition fixtures; 101 R3 v2 Python tests (85 passed, 16 private-evidence
skips), plus selected E5/R4 raw tests. Both firmware targets built using the
pinned SDK 2.3.1 and Arm 15.3.1. Linked allocator hooks, stack guards and RAM
placement checks passed. Sixty compared RAM functions are byte/address identical
to the old ELF; veneers/static addresses changed, heap capacity fell by 20 bytes
to 220328. This does not establish physical timing equivalence. The original
expired test credentials and sandbox loopback failure remain recorded; refreshed
ephemeral credentials and permitted localhost access produced the passing run.
The optional historical companion-source TLS interop target was not selected.

F3 was restored without extending its original deadline before fresh F4. F4 was
restored at host monotonic 347850093812794 ns, before its unchanged deadline
357877820026000. Both cleanup records have zero failures and matching protected
file hashes. Fixture units/namespace/subnet are gone and WLAN radios are back
down. Permanent time.local, chrony, GPSD/PPS and Avahi checks passed. Installed
WsprryPi remained active as PID 1957, binary SHA-256
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`.
Host boot remains `220e53ca-ca95-4206-9581-dbe28aa1eeb8`.

Post-restoration raw Console and WTP inventories independently confirm A on the
diagnostic identity above, Missed/inactive/unowned, job
`9f0ae5cb9bf19c6366c53c33a75d86e0`; B on the unchanged BF4 identity,
Empty/inactive/unowned. Scheduling remains disabled and configuration unchanged.
The diagnostic image is retained; no restoration flash was performed.

This attempt consumed one diagnostic candidate, zero repair candidates, one A
flash, one BOOTSEL, zero extra reboots, one 90-second charged ARM, zero RF launches
or completed jobs, zero CONFIG saves, zero commanded Wi-Fi cycles and zero heap
probes. The original four-hour monotonic budget was not restarted. Restoration
began early after the sole failed diagnostic; another work period needs direction.
Checkpoint 047 records elapsed time and evidence/tool hashes. Private raw captures,
frozen scripts, generated images, credentials and the refactor archive stay under
ignored build/private roots. Unrelated pending R3 work and `.impeccable/` remain.

## Bounded attempt, 2026-09-14

Four-hour monotonic budget: start 710199726832375 ns on this Mac, 14,400 seconds;
reserve at least 1,800 seconds for restoration/reporting. New RF ceiling 900 seconds.
No Group 3 work. At most one diagnostic candidate and one focused repair candidate.
Initial reconciled source was `a740dbb8e7319beb20c4807b35f6672bf9fdfd27` after
withdrawing only the attributable unfinished paged-input refactor. All 12 files,
including two untracked headers, are retained with hashes and the original diff in
`build/phase11-5-r3-group2-bounded-20260914/withdrawn-paged-input/manifest.json`.
Unrelated R3 work and `.impeccable/` are preserved.

Read-only admission confirms A source/boot E4 below, Complete/inactive/unowned,
C3 job `c0779e0176119170554cb961d2991c11`, allocator failures two, no DMA/TLS
allocation errors, and scheduling disabled. B remains Empty/inactive/unowned on
BF4 identity. F3 live host boot matches its record; original deadline remains
348101486890000 ns. It was not expired at initial inspection (346425413770994 ns).
No new fixture lifetime is inferred from this observation.

### Assertion table before any firmware change

Identity keys (source / UF2 / boot):

- E4 and C1–C3, A: `a740dbb8e7319beb20c4807b35f6672bf9fdfd27` /
  `454e03e5165143463d6b5f965ea8f1f3704138f08bfc7057704e3fef8f10ebe4` /
  `2b4583bd3d79a38f030a08c82ed96939`.
- BF4, B: `8921a70081839f168edef5926e92445f251d8e1d` /
  `67c27f20da8212097d60cd6b58fbbb4e774286df728ed7ea3e2746b5c6a59f58` /
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- T4/T5, A: `8921a70081839f168edef5926e92445f251d8e1d` /
  `3899b498d05ca5b39e23a45e455c44b2784bcf2aca35f62a8ef4db644cc7241b` /
  `fc90d1a04eb0acc703de907917277921`.

Evidence refers to the corresponding existing `phase11-5-r3-v2-*-result.json`.
Statuses apply to the complete assertion, so an idle component cannot pass its
under-RF requirement. No repair has been selected. Proposed diagnostic telemetry
changes only failed-allocation retention and INFO fields, but its layout/INFO
cost needs new linked/host checks and physical timing/resource observation.
Any later repair must replace this prospective impact assessment before flashing.

| ID | Required assertion | Status | Evidence / missing test and reuse | Proposed diagnostic impact |
| --- | --- | --- | --- | --- |
| 2.1a | 512-event admission and actual completion under contention | PASS | E4 idle plus C1 512-event FSKCW, 384 s; exact current A source. Original C1 observer/result failure retained; no native host-HTTP credit. | Functional plan unchanged; new image timing/resource observation required. |
| 2.1b | 513-event and over-3600 s atomic rejection; exact maximum admission | PASS | E4 seven assertions on current A; parser/service unchanged. | Host regression; no limit change. |
| 2.1c | Worst 32-character plans, physical 3600 s QRSS/FSKCW/DFCW, ordinary WSPR and rejection precedence | PARTIAL | Existing Group 1/hour and compatibility records retained; assertion-level source-impact mapping still required before complete reuse. | No automatic hour repetition; assess layout and measured instrumentation impact. |
| 2.1d | Valid WTP 65536 full transfer and success during RF | FAILED | E4 idle only; C2/C3 supported attempts fail at 4096 host-written bytes. | Failure-site diagnostic needed. |
| 2.1e | WTP 65537 correct framing/CRC rejection, full transfer and same-connection recovery during RF | PARTIAL | E4 idle pass; C2/C3 never reached case. | Framing unchanged; physical case missing. |
| 2.1f | Exact valid HTTP API body 32768 success during RF | PARTIAL | BF4 B idle only; no A RF credit. | API unchanged; physical case missing. |
| 2.1g | HTTP 32769 intended HTTP rejection and authenticated recovery during RF | PARTIAL | BF4 B header-limit/recovery only; no A RF credit. | API unchanged; physical case missing. |
| 2.2a | Declared supported simultaneous allocation with final event plan | FAILED | C1 nominal traffic is not maximum simultaneous capacity; C2 failed; overlap schedule missing. | Diagnostic first; resource budget must be demonstrated. |
| 2.2b | Declared memory overload at intended boundary, owner/RF preserved and authenticated recovery | NOT_RUN | C2/C3 are failed supported cases; slot rejection is not allocation overload. | No overload reclassification. |
| 2.2c | Activated TLS handshake timeout and authenticated reuse | PARTIAL | T4 mechanisms accepted on its identity; A static-response and INFO changes need explicit current-image resource applicability. | New INFO cost/layout assessment. |
| 2.2d | Failed TLS alert ACK and unacknowledged lifetime | PARTIAL | T5 distinct mechanisms retained; same source-impact boundary as 2.2c. | New INFO cost/layout assessment. |
| 2.2e | Both active slots, one-WTP restriction, pending expiry/excess and reuse | PARTIAL | T4/T5 mechanisms retained; source implementation unchanged, resource reuse assessment outstanding. | New INFO cost/layout assessment. |
| 2.2f | HTTP partial header/body activation deadlines and stalled reader recovery | PARTIAL | T5 distinct mechanisms retained; no five-second WTP credit. | Static response change may affect reader allocation; assess specifically. |
| 2.3a | Distinct 30 s WTP inactivity from drained exchange, closure and authenticated reuse | NOT_RUN | No earlier timeout may substitute; schedule and independent observation missing. | Mechanism unchanged; physical activation required. |
| 2.3b | Five-second incomplete-input mechanism with correct progress origin/recovery | NOT_RUN | Existing host coverage only; physical mechanism not established. | Mechanism unchanged; physical activation required. |
| 2.3c | Five-second no-output-progress mechanism, distinct from queue saturation | NOT_RUN | Existing host coverage only; physical mechanism not established. | Mechanism unchanged; physical activation required. |
| 2.3d | Actual USB parser pressure under finite RF and independent authority | NOT_RUN | C3 failed input does not establish intended pressure/recovery. | Physical stimulus/observer required. |
| 2.3e | Actual USB unread-output pressure under finite RF and independent authenticated authority | NOT_RUN | No accepted case; USB interface must have one exclusive opener. | Physical stimulus/observer required. |

### Diagnosis basis

C3's raw files and source do not identify the exact failed allocator call.
`FrameParser` requests 65552 contiguous bytes after a valid header; nullable
`InputBuffer::reserve` may fail, but other allocator paths remain possible.
Cumulative largest-request/free totals do not identify that failure. The existing
panic-only last-attempt fields are overwritten by later successful allocations.
Retaining last failure size, allocator entry and input-allocation context in the
existing locked metrics is the proposed bounded diagnostic, not an OOM repair.

## Historical preparation (superseded by the reconciliation above)


Group 1 is CLOSED at checkpoint 043. Group 2 remains OPEN. No new Group 2
RF job has run.

Reuse the established RF observer, capacity exchange, TLS/transport pressure
and raw-evidence auditors. Coordinate their bounded invocations and add only
missing stimuli. Do not introduce a replacement campaign application.

Preserve E4 current-image idle WTP 65536/65537, 512/513-event and 3600/+1 ns
admission evidence; BF4 B-specific HTTP bounds; and T4/T5 individually audited
timeout mechanisms. These do not substitute for A's enlarged-job allocation
under RF. Do not repeat the completed QRSS, FSKCW and DFCW physical hours.

The proposed new C0 runner was retired before execution following the user's
scope correction. Its packet hash is
`ae660d464f1e3a0e54505f24944fe01808599351966c65fc9b33563aaf9334a1`.
Its 19 new runner/auditor/test files were removed from proposed repository
changes after byte-for-byte archival in
`build/phase11-5-r3-v2-capacity-c0/stage/`. The retirement manifest is
`build/phase11-5-r3-v2-capacity-c0/retirement.json`. Its remote result marks it
RETIRED_NOT_EXECUTED and prevents admission from replaying that packet.
C0 consumed zero RF jobs and zero RF duration. Local harness tests are not
physical evidence or Group 2 acceptance.

F2 is restored. Fresh F3 is active with 7200 seconds execution plus 900 seconds
cleanup, exact deadline 348101486890000 host monotonic nanoseconds, client
PID 553798. The installed Pi PID 1957 and executable hash are preserved.
Read-only preflight confirmed A's retained a740dbb image/source and boot
2b4583bd3d79a38f030a08c82ed96939, Empty/inactive/unowned. A associated to F3
but had no IPv4 lease or synchronized clock after more than 240 seconds.
This is an unresolved network-acquisition prerequisite, not an RF failure.
One separately bounded idle Wi-Fi recovery packet W1 is prepared; it has not
yet executed. Its result must be audited before RF admission.

Remaining mechanisms: actual 512-event RF; maximum WTP and HTTP payloads
under RF; supported simultaneous allocations; bounded unsupported allocation
and recovery; distinct 30-second WTP inactivity and five-second input/output
mechanisms; actual USB parser/unread-output pressure with independent authority.
Measure live allocation with the stimulus/state identity intact. Elapsed silence
or cumulative allocator peak alone cannot establish the intended mechanism.

## Diagnostic deployment source-impact review

Candidate `4da36726ac6809bdf4e73d281fe13b2393dd3b31`, UF2
`0153107c517b673bfad7850957c8387a7dbfb12ddb0a3b1e90edb94b804b9a9f`,
ELF `8855dd77cb0057ff8f33f91d02a3447cf39ca96cb2782b606c51f2e44e4f7353`.
All 70 current host CTest groups pass, including actual pinned Mbed TLS tests;
WTP contract passes. The optional historical fb0a2eb client-interoperability
checkout is not selected; current native-client evidence is separately retained.
Old host credential expiry and sandbox-blocked loopback were environment failures,
retained in the private build logs. Both standard inhibited and physical images
build and pass linked flash, heap, stack, interception and RAM placement checks.

1. No framing, CRC, JSON, admission limit, codec, service, event, RF renderer or
   timing algorithm changes. Existing functional boundary/lifecycle evidence is
   retained within its exact historical identity; no new whole-image credit.
2. Host failure retention, nested realloc, overflow, input context cleanup,
   concurrency, guards, protocol and network checks passed. The recorded suite contains exactly 70 CTest groups.
3. New target identity, failure-site addresses, INFO cost, heap reserve and
   physical timing require observation. RF functions in the compared RAM region
   are byte-identical (60 matching RAM functions overall), while linker veneers
   and some static addresses change. Measured linked heap capacity decreases from 220348 to 220328 bytes. This is a
   diagnostic candidate only; it cannot close capacity by its build or a reboot.
4. No hour campaign is admitted for this diagnostic. If diagnosis justifies a
   repair, that candidate needs a new source-impact review and a complete
   acceptance schedule fitting the remaining 900-second RF allowance. If broader
   resource/hour evidence cannot be reused defensibly, Group 2 stays open.

F3 cleanup verified with no failures at host monotonic 346755676051449 ns;
installed PID 1957/hash unchanged and namespace list empty. Fresh F4 has 10800 s
execution plus 900 s cleanup. Its timer must never be extended, and the earlier
four-hour attempt checkpoint remains controlling.

### E5 diagnostic deployment packet (reviewed before execution)

Existing admission runner, fresh packet
`e41c50ae3cef279a28082cdb0ae9de639e57e6f940cf1a0fbe6731b8da8da39d`,
root `/home/pi/phase11-5-r3-v2-idle-e5-20260914`. One A BOOTSEL and one
verified flash/start; zero extra reboot, RF, Wi-Fi commands, CONFIG saves or heap
probes. B receives read-only inventory only. R4 first reconciled the known C3
Complete state using one exact-identity CLAIM/RELEASE; historical failures remain.
E5 reuses the seven existing idle admission assertions (65536 full-write,
65537 rejection/recovery, 513 and overduration rejection, 512/exact duration LOAD,
abort/release), a 600-second runner deadline and 150-second supervision reserve.
A fresh boot's success cannot establish a repair of the prior contention failure.

### C4 sole diagnostic RF reproduction: frozen schedule

Packet `3265c16e1a970c79c1beee2bd6a9cf4b9198381ee051a08f5f0dd40d7ed95277`,
root `/home/pi/phase11-5-r3-v2-capacity-c4-20260914`, diagnostic source/image
above, boot `0bd82f1324920c360d796988cf31cb5b`. One 90-second finite Tone at
135500 Hz, full 90-second charge before ARM, 180-second execution plus 150-second
reconciliation allowance. F4 deadline is 357877820026000 host-monotonic ns.
No flash, extra reboot, Wi-Fi command, CONFIG save, probe, HTTP or native TLS load.

USB WTP if02 is the single exclusive owner and stimulus connection; Console if00
independently reads INFO with the existing single-flight policy, and host health
is independent. WTP STATUS/host health offer at five-second cadence. The first
owned Running STATUS, bracketed by fresh matching INFO, triggers the existing
capacity exchange. Send exactly one 65536-byte valid STATUS payload (65552 frame
bytes), then, only if successful while Running, exactly one correctly CRC-encoded
65537-byte payload plus same-connection PING. Transfers use the existing duplex
4096-byte write chunks, no retry, each whole exchange deadline five seconds from
its start; no artificial request flood or extra connections. Full-write evidence
and exact response identity/state are mandatory. Capacity traffic cannot claim
continuous authority if it blocks the owner path and INFO subsequently fails.

The generator is `wtp_capacity_frame` with the packet's exact session/request IDs;
PING token is `after-capacity`. Frozen bytes:

- maximum: 65552 bytes, SHA-256 `3ebdfbfadf630d37c118e98dd8c0da3c16d17ec6a884742d138d43bb303e03e3`.
- oversized plus recovery: 65748 bytes, SHA-256 `9daa8eec31651ed93dc03cc6b7ffefe0f19325bd366958d00f07f0d3e88684ed`.

Any new allocator failure, observer fault or unexpected state stops dependent
operations. Let the bounded local job complete; use the existing final inventory
and, if necessary, a separately bound known-completion reconciliation. Do not
retry the stimulus. The primary diagnostic evidence is retained allocator entry,
request size, caller and input-context caller resolved against the exact ELF,
plus raw transfer count and independent final output/owner state. A failed
capacity attempt remains FAILED even if its diagnostic fields are useful.

This reproduces C3's declared Tone/input/no-native-load schedule after E5's idle
maximum allocation sequence. It cannot recreate C3's complete prior boot history;
a nonfailure leaves that historical mechanism unresolved. E5's idle seven-assertion
audit and ten evidence mutations passed; no new RF acceptance is inferred.
