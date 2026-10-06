# P12.7 GP14 RF integration review

Status: **source gates passed; five RF rows accepted; long-held AP open;
continuation stopped; B restored inhibited** (2026-10-02).
Executes the [authorized brief](phase12-gp14-rf-execution.md). GP14 remains
opt-in pending the required target rows. Phase 12 remains active.

## Changes

The RF target now shares the common main's provisioning/BTstack/crypto and
shutdown dependencies, uses a guarded 32 KiB primary stack and retains its
independent 16 KiB worker stack. The existing RF bootstrap remains read-only.
The standard image remains the inhibited simulator.

`ButtonSafety` applies the selected GP14 debounce/gesture policy on the
RF-owning core. A recognized stop/reset or policy fault latches inhibition;
that worker disables and verifies its engine before further polling or RPC
completion. Preparation, arming and frequency correction refuse after the
latch. The launch driver checks the same immutable atomic latch before output
enable. Core 0 reconciles JobService/scheduler before further foreground
admissions, then its existing PIO/DMA gesture path handles reset or setup AP.
No input ISR calls the engine, reset, flash or network adapters.

`WSPRRY_PICO_GP14_RF_ACCEPTANCE` is off by default and requires GP14 enabled.
It adds one identity-bound five-second busy operation per boot, accepted only
with an armed/running job and healthy input. It reconciles the worker latch
before returning. Acceptance-only quick-reset telemetry retains the decision
time relative to RF launch in unused normal-reset scratch slot 3; SDK reboot
slots 4..7 and recovery fault records remain separate. Normal RF images have
neither the command nor this marker, verified by the linked-image checker.

`phase12_gp14_rf.py` acquires one identified B-only finite 20-second tone and
40-second receiver capture per invocation. It charges ambiguous ARM attempts,
limits the initial campaign to eight RF jobs and ten acquisition attempts, stops on failed evidence and
requires a bound, passing independent RF analysis before the next attempt.
It does not flash, save station settings, inject input or set the clock.

## Adversarial assessment and repairs

1. **RF target build failure:** previously omitted common-main dependencies,
   and an unguarded mutable-bootstrap cancellation branch. Share dependencies
   and restore the RF read-only guard; inhibited and RF links now succeed.
2. **Busy core 0:** captured input alone could not stop RF. The independent
   worker latch now stops active output or cancels a future launch without
   producer RPC. Portable tests exercise active/armed cases, concurrent worker
   ownership, producer inactivity and requests arriving during prepare/arm.
3. **False safety acknowledgement/restart:** a failed disable or output still
   active invokes the non-returning recovery hook. Tests cover both cases.
   The latch remains set after release and explicit disable; later prepare/arm
   cannot call the underlying engine. A future physical launch is interlocked.
4. **Test contamination:** busy control, quick-reset relative telemetry and
   acceptance marker are confined to the explicit test variant. Normal-image
   linked checks assert their absence. No automatic RF job is introduced.
5. **Host gate drift:** the old GCC/libstdc++ build differs from the documented
   Xcode/libc++ allocation model. The documented toolchain passes that gate.
   Current Python TLS verification also exposed missing SKI/AKI in ephemeral
   host certificates. Repair those test-only extensions and use a new fixture
   directory; retain strict certificate verification. Fix two signed bounds
   in the host mDNS observer exposed by GCC's warnings.
6. **Measurement/retry ambiguity:** target ACK timing alone cannot qualify RF.
   The acquisition preserves IQ, exact settings/identity, timestamps and
   capture hash, rejects overflow/timeouts/clipping, and blocks later runs
   until independent assessment is attached. An ambiguous ARM is charged and
   never replayed; failure cleanup only aborts the same identified owned job.
7. **Acquisition field mismatch:** review against the actual retained INFO
   schema removed an assumed runtime-enable field. The explicit acceptance
   marker and advancing GP14 samples bind the acquisition to this image.

Reassessment found no remaining actionable source finding in this slice.
Physical cutoff, armed cancellation, busy-core behavior, quick reset, AP
availability and default enablement remain gates; source tests do not close
them. The extended flash-safe capture evidence does not establish exact
coincidence with the short erase/program operation.

## Checks before clean candidate deployment

- Full documented Xcode host build with pinned retained Mbed TLS/lwIP:
  **107/107 passed**. The earlier GCC/toolchain/fixture failures are retained
  privately, not counted as passes.
- Added prepare/arm race and actual threaded worker safety cases; affected
  worker/failure/button/UF2 checks: **4/4 passed** after review additions.
- Inhibited and RF/acceptance targets build with retained SDK 2.3.1
  `079c6f39023649b154152db30f1d781e884879bc`, pinned BTstack
  `eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec` and Arm GNU 15.3.1.
- Linked checks pass for 32 KiB primary/16 KiB RF worker separation, allocator
  interception, stack guard installation, RAM renderer, shutdown interception,
  journal/UF2 boundaries and the explicit acceptance control.
- Unrelated README/CONTRACT/architecture/browser API/new application contract
  changes retain their original hashes and are excluded from the commit.

Private development logs are under ignored `build/phase12-gp14-rf-*`.
These dirty development builds are not deployable evidence. A fresh clean
committed build, B's preflight/backup, verified application load and reserved
storage comparison are required before the physical packet.

## Clean candidate and B deployment

Clean firmware source is `62ae4c2c25675631c6094f669cc0f74722987bdd`;
the RF acceptance UF2 is 3,210,752 bytes, SHA-256
`3d2d336e0136be5078ac9ef3377487dce9d3b82ef76dab4fe3c366f18308462f`.
Both clean normal variants passed; the normal RF image contains no busy
control. The separate acceptance image passed memory/flash, renderer,
allocator/guard and shutdown checks and the test-control presence check.

B's fresh 4 MiB backup SHA-256 is
`e77aa61396cda525c1ad2d437e69ac30ed4f52cec7cc302261839e816c8b7d99`.
It was retained and independently verified on the Mac before loading.
Serial-targeted load/verify and normal boot succeeded; all 57,344 reserved
bytes matched, and consumer generation 5 / AA1NT / EM18 / 20 dBm, access
generation 1 and standalone configuration were preserved. Boot ID
`26a72ec6e80cf4cd25c3ca4ff6e5ee7f` reports the physical engine at 138 MHz,
guarded primary/worker stacks, zero allocator/capture faults and inactive
output. Later USB and Plain LAN HELLO/CAPS/STATUS/GET_CLOCK confirm the same
boot, empty/unowned authority, `192.168.1.53` and synchronized time.

One receiver-only three-second baseline verified RSP1B `2404058C60`, CF32 at
250 kS/s, 200 kHz bandwidth, 3.55 MHz center, gain 20 dB, channel 0, AGC/bias
off. All 750,000 samples were retained without overflow, timeout or clipping;
cleanup passed. IQ SHA-256 is
`b98ac0600009b75c1765400247caeacb7f80ba668a2302ffd97de450f3b3befd`.
No physical cutoff is claimed from inactive capture.

The first active-stop acquisition failed at LOAD with `FREQUENCY_REJECTED`:
the helper incorrectly disallowed NCO frequency rounding. Retained requests
prove no ARM was sent. Fresh WTP confirms empty/unowned/inactive output.
The attempt is retained and counts toward the eight-attempt limit; it is not
RF acceptance. Permit the normal bounded frequency realization, validate its
returned adjustment within 50 Hz of the conducted tone, and repair claim-only
failure cleanup. Adversarial reassessment also repaired the ABORT body and
terminal cleanup. Schema-valid claim-only, loaded, running, terminal and
foreign-owner refusal checks plus the existing real stream-planner rounding
tests pass (**2/2 affected groups**). The firmware image remains unchanged;
only the acquisition helper is revised for the retest.

## Physical continuation and restoration

The second attempt launched one finite 20-second tone, but no GP14 gesture
was recorded before finite completion. Cleanup verified empty/unowned/inactive
output. The operator subsequently requested another attempt. An inhibited
contact check then recorded a 2,526,000 us hold and one verified stop request.
That establishes the contact in the inhibited check; it does not qualify RF
cutoff. B was restored to `615888e5364b` with all 57,344 reserved bytes identical
before the check.

The explicitly requested retry preserves the initial campaign's attempt count.
The helper permits this reviewed no-input timeout only with a positive launch,
no recorded input/safety fault, exact job/boot completion and verified inactive
cleanup. It binds both attempt and event hashes, retains
`independent_rf_pass: false`, and cannot waive an observed gesture, fault or
ambiguous cleanup. Boundary/refusal tests and the affected stream/client groups
pass (**2/2**). This is an operational retry
authorization, not a passing RF assessment.

The third attempt used the unchanged clean RF image and a new boot
`b9ee1bb6343c67f66f1080cb74ae0b2b`. The operator supplied the hold/release cue;
USB closed unexpectedly during acquisition. Fresh readback identified a normal
GP14 reset, a **27 ms** recorded release and a worker decision 12,637,844 us
after RF launch. The new boot was empty/inactive, with no recovery or stack/
capture fault and consumer generation 5 preserved. The selected quick-release
reset path is therefore observed, but the requested active-stop row is
unaccepted. A partial 52,448,256-byte receiver file remains; receiver completion,
integrity metadata and independent cutoff analysis are absent. It does not
close the quick-reset RF row. The cause of the short recorded contact is not
established by this evidence.

B was restored again to inhibited `615888e5364b`, boot
`4c8a0398698188bf5f593c2a565dccf1`, with all 57,344 reserved bytes identical,
consumer generation 5, access generation 1 and exact saved station/profile
preserved. It reports healthy storage and inactive output. A remains on
inhibited `615888e5364b`; wspr4 was not contacted. **Three attempts and two
finite RF jobs are charged; no physical cutoff row has passed.** GP14 default
enablement remains off. Further RF acquisition requires review of the failed
row and a verified physical hold; no automatic retry is authorized by the
runner.

Private image/backup/capture/readback evidence is under
`build/phase12-gp14-rf-b-20260930/` and its matching wspr5 directory.

Reassessment of the retry guard rejects observed input, a latched stop, input
faults, missing final status and a foreign terminal job. The unexpected reset
remains a failed acquisition and its partial IQ is excluded from acceptance.
Fresh identity-bound LAN readback after restoration confirms empty/unowned/
inactive authority. No further actionable source finding was identified;
physical hold, cutoff measurement and default enablement remain open.

## Physical readiness and retained receiver completion

The subsequent inhibited hold check recorded **5,707,000 us**, one verified
stop and no reset/capture fault. B's exact RF acceptance application was then
reloaded with a fresh retained full backup and all 57,344 reserved bytes
identical. Firmware source/image remain `62ae4c2c2567` and the same UF2 hash.
The fourth acquisition, boot `1e378e6b7b6ce2d0d29cdbd25dc190bc`, completed its
20-second tone before any recorded input. Its later physical hold was
**6,356,000 us**; the worker requested stop **108.211701 seconds after launch**
and acknowledged inactive output in **77 us**, with no input fault. That
acknowledgement occurred with the tone already ended and does not qualify
live RF cutoff.

The repaired finalizer retained all ten million CF32 samples after the target
timeout, with exact receiver/settings, no overflow/timeout/clipping, verified
cleanup and SHA-256
`c5337d9ffcfe10dcbeef01832b971e6cac39b57235fdb6f6e3bef8d08a83a013`.
An independent 1 ms Fourier-window observation finds a continuous carrier
from nominal receiver sample times 5.373 to 25.374 seconds, 64.59 dB above the
inactive baseline. This is a finite-tone observation, not cutoff acceptance;
no calibrated receiver-time bound is claimed. **Four acquisition attempts and
three RF jobs are charged; all required cutoff rows remain open.**

The host helper now retains finite receiver completion even if a target action
fails. A bounded reviewed resolution of the earlier normal quick-reset mismatch
requires positive prior launch, the same image/device, a distinct normal-reset
boot, under-400 ms marker, positive relative worker decision, empty/inactive
output and fault/resource health. It remains `independent_rf_pass: false` and
cannot waive a recovery/fault boot or an unbound readback. Reviewed no-input
timeouts are likewise bound to exact finite completion/cleanup and remain
unaccepted. Initial RF authority stays bounded at eight charged jobs; rejected
LOAD attempts are recorded separately under a ten-attempt ceiling.

To remove chat timing from the short acquisition window, an explicit
`--wait-button-reset` flow waits empty/inactive for the operator's local quick
tap, admits only a new released healthy synchronized boot, and sends B's
existing triple-flash identify cue after active/armed confirmation. It submits
one finite job. The unsignaled ten-minute wait submits no job. Adversarial
checks reject premature/held/faulted ready signals, foreign image/reset
readback and missing decision evidence; real subprocess checks cover receiver
completion and forced reaping at its deadline. Affected stream/client groups
pass **2/2**. Reassessment found no additional source finding; physical cutoff,
busy-core behavior, reset/AP acceptance and default enablement remain open.

The first physical-ready wait stopped before any receiver, CLAIM, LOAD or ARM
because the exclusive USB ownership preflight raced CDC disappearance during
a real reset. Fresh readback records a 57 ms GP14 reset and exact-device
empty/unowned/inactive USB/LAN authority. It charges one acquisition attempt
and **zero RF jobs**. The repaired console wrapper treats that ownership
error as reconnectable only when the exact CDC path is demonstrably absent;
occupied or unverifiable existing endpoints and unrelated parse errors remain
fatal. Refusal tests prove no console request is written without exclusive
access; affected groups pass **2/2**. Reassessment retains the fail-closed
ownership gate and the unchanged eight-RF-job bound.

The next local-ready attempt observed the operator's 395 ms normal reset and
admitted a finite tone, but the legacy `IDENTIFY` command was denied by the
consumer-profile guard. The runner aborted the same owned job and verified
inactive/empty/unowned cleanup; the completed receiver evidence is retained.
This is a failed acquisition, not cutoff acceptance. **Six attempts and four
RF jobs are charged.** B was restored to inhibited `615888e5364b`, boot
`41c8399cebe99a162604f7cf69611f77`, with all 57,344 reserved bytes identical and
exact settings/profile preserved.

The repair adds `GP14 RF CUE` only inside the explicit acceptance build.
Its identity-bound `READY` probe is allowed only with empty/inactive authority
and does not blink or change output. A fresh hexadecimal nonce may start the
existing ten-second triple-flash identify pattern only with armed/running
authority and healthy input/network/indicator state. Recovery, pending reboot,
latched safety and malformed/foreign requests are refused. Consumer legacy
controls retain their existing guard. The host requires the new capability
marker and a positive readiness probe before any CLAIM/LOAD/ARM, then verifies
the action-cue acknowledgement. The linked-image checker requires the new cue
markers in the acceptance image and forbids them in normal images. Affected
worker/failure/field/button/stream/client groups pass **6/6**. Clean SDK rebuild,
image checks and target readiness verification are the remaining deployment
gates for this revised test image; no additional RF has been authorized by
the software repair itself.

The cue repair's clean source is `5d951b2b7caa37249b0e2aad75bf613000b6860c`;
UF2 SHA-256 is
`319a550c41341812ce6037494cb737e6b4d40521f5a257e07ec962b8f1b38889`
(3,212,288 bytes). Clean inhibited/normal RF builds pass, with cue/busy markers
absent; the separate acceptance build passes their presence checks. Guard,
heap, RAM renderer, 32 KiB primary/16 KiB worker, flash/UF2 reservation and
shutdown interception checks pass using the retained pinned dependencies.

B's fresh full backup was retained/hash-verified on the Mac before load;
all 57,344 reserved bytes matched and exact saved profile/access settings
were preserved. Boot `c388b7a417190312774049f485058677` reports inactive output,
healthy guards/storage and synchronized time at `192.168.1.53`. Its actual
saved-profile USB path returns a positive `GP14 RF CUE ... READY` response;
subsequent readback confirms the probe did not activate LED identification or
RF. No new RF job was submitted by this readiness verification.

The old cue-denial receipt remains explicitly unaccepted and is reusable only
after verifying its historical image/profile, same-job ABORT, inactive aborted
terminal record and empty/unowned release. Refusal tests cover foreign jobs,
uncleared ownership, another image and any recorded physical action. Every
new attempt stores its exact packet bytes/hash before device actions; old
packets are retained unchanged when selecting the new image. Affected groups
pass **6/6** after these additions. Reassessment found no remaining actionable
source finding in the revised cue/admission path; all physical cutoff rows and
default enablement remain open.

## October 1 contact discrepancy and release filtering

The first acquisition on clean cue image `5d951b2b7caa` successfully observed
the ready reset, launched the identified finite tone and acknowledged the
triple-flash cue. Run `run-a0a57edd9fa9449fabb83c4ff9354ad1` then lost USB.
The operator reports a five-second hold. Fresh exact-device readback instead
retains a **42 ms normal GP14 reset**, with a worker decision 3,531,210 us
after launch, a new empty/unowned/inactive boot and no recovery, capture,
guard or allocator fault. This discrepancy remains a physical input finding;
the reset marker cannot establish the raw electrical contact history.

The complete receiver capture contains ten million samples, no overflow,
timeout or clipping, and verified cleanup. Its SHA-256 is
`32f59a6fb96d444abadc3db7df8ca2aa423bad632188ec0c2a69679bf3294222`.
Independent 1 ms Fourier windows observe the carrier from nominal sample
times 5.320 to 8.851 seconds, 60.49 dB above baseline. The tone ended during
the reset; this observation does not establish a calibrated decision-to-RF
latency or accept the selected active-stop row. The reviewed failed receipt
remains `independent_rf_pass: false`. **Seven attempts and five RF jobs are
charged; all six required rows remain open.** The initial eight-job cap remains.

B was restored to inhibited `615888e5364b`, boot
`04334065322060a787ff838e4757fb5a`, after retaining and hash-verifying its
fresh full backup on the Mac. Backup SHA-256 is
`2d85d7753f9be1f958472f369c247cd2c49cfc994a380bf34c649ab066b35242`.
All 57,344 reserved bytes and the exact saved profile/access settings match.

Source inspection found that a high interval of only 10 ms confirmed release,
which can split a held contact and schedule reset before later contact resumes.
The revised policy requires **100 ms of stable release**, while retaining the
10 ms stable press, original raw-edge duration measurement, under-400 ms reset,
900 ms held stop and 9 s held AP thresholds. The same portable policy is used
by worker sampling and PIO/DMA replay. Interruptions shorter than 100 ms keep
one gesture; longer interruptions can still confirm release. The physical
cause of the October 1 discrepancy is not yet established, and this change
requires an RF-inhibited contact check before another RF acquisition.

A new regression reproduces premature worker inhibition under the old filter:
a 42 ms initial contact, 50 ms open gap, continued five-second hold and later
99 ms gap must remain one shutdown gesture. It also checks packed replay,
unchanged worker stop time, genuine quick-release confirmation, boot-held
behavior and a ten-second AP gesture with interruptions. Tests retain exact
raw-edge duration and gesture boundary assertions; a confirmed release is
delayed rather than added to the measured hold duration.

Adversarial reassessment checked both shared-policy consumers, the exact
100 ms release boundary, raw-edge duration classification, startup with a
held jumper, interruption handling, sticky worker inhibition and one-shot
stop/AP dispatch. All six affected worker/failure/field/button/stream/client
groups pass, as do formatting and whitespace checks. Press/hold thresholds
and source default-off selection remain unchanged. The stronger filter is a
bounded mitigation, not proof that contact bounce caused this target result;
RF-inhibited and subsequent active/armed target checks remain required.

The release-filter repair's clean source is
`3e1337074003616c23d9b8749e728c99c71738c6`. Both normal inhibited and RF images
build with the retained pinned SDK/toolchain and pass their linked memory,
guard, renderer and shutdown checks; normal RF contains no acceptance controls.
B now runs the revised **inhibited** image `3e1337074003`, UF2 SHA-256
`fbbd2b7b945c0bc334ddd091adb94267504fa848508129bfdc26b4ec4e9c9692`
(3,368,448 bytes), boot `f11d0242b6e9315e1cb94b3badf38d1c`. Its fresh full
backup was retained and verified on the Mac before load, all 57,344 reserved
bytes match, and exact profile/access/settings and empty/inactive authority
are verified. A finite read-only contact observer is prepared; no further
RF job is admitted until that contact check and the next acceptance-image
preflight pass. Physical release-filter acceptance remains pending.

The subsequent RF-inhibited physical hold on B recorded **6,188,000 us**,
one verified stop, zero reset/AP requests, released input and the same boot
`f11d0242b6e9315e1cb94b3badf38d1c`. Guard/capture/storage health and exact
saved profile/access state pass; read-only LAN STATUS is empty/unowned/inactive
before and after the gesture. This accepts the revised filter for that
inhibited contact check. It does not qualify RF cutoff or establish the raw
electrical cause of the earlier 42 ms observation. A clean acceptance-variant
build and verified B deployment precede the next single active-stop RF row;
the initial eight-RF-job/ten-acquisition bounds remain unchanged.

The clean RF acceptance variant of the same source passes the acceptance
control, guard/heap, worker stack and RAM renderer checks. Its UF2 is
3,212,800 bytes, SHA-256
`658605e4bc66094849be71ee6bb59c91d335d6e1fb7fe99ad54d96b27cf09aa5`.
B's fresh inhibited full backup SHA-256 is
`75083a4007733f41028c1fed99ecc6652802224d477a31f507d146f6b2ca02b3`,
retained and verified locally before load. All 57,344 reserved bytes and exact
saved station/profile/access settings match after programming. RF boot
`24a9557a4389a982d57e8259237ad17c` is healthy, released, inactive and synchronized;
the non-output cue readiness probe passes on the saved consumer profile.
The previous exact `5d951b2b7caa` packet is retained unchanged when selecting
the new image packet. Deployment/readiness submits no RF job; five charged
RF jobs remain the current count before the next physical-ready invocation.

## First accepted RF row: active stop

Run `run-629ab099557a4540b05c0f305dc2289c` passes the bounded conducted
**active-stop** row on clean `3e1337074003`, boot
`56109ffc82f5b6aff4c81f445c0c7595`. The 6,732,000 us hold produces one
verified stop, zero resets, a sticky healthy worker latch and a rejected later
CLAIM. Worker acknowledgement is 94 us; this is reported separately from RF.

The complete ten-million-sample capture has exact receiver/settings, no
overflow/timeout/clipping, verified cleanup and SHA-256
`3d8b1f2bab3716b89d360d4ed6ebc012b83a4a264af54a025ff2b93854c94db6`.
Independent 1 ms Fourier windows observe one carrier from nominal sample
times 5.441 to 8.158 seconds, 60.30 dB above baseline. Thresholds 20, 30 and
40 dB below the on level give identical edges. The 2.717 s carrier interval
exceeds the recorded decision-after-launch interval by 0.878 ms. No carrier
reactivation occurs during the remaining 31.842 nominal seconds.

For this operational row, the assessment includes an explicit conservative
1% clock-scale allowance (27.170 ms), 2 ms for both Fourier edges and the
191 us observed maximum launch-alarm interval. The total engineering allowance
is 29.361 ms, giving an upper relative cutoff estimate of **30.239 ms**, within
the selected 50 ms bound. Campaign clock agreement includes the retained
20.001 s finite-tone reference against a requested 20 s, this capture's
40.030 s delivery interval for 40 nominal sample seconds, and a nominal
3,570,101 Hz carrier against the realized 3,570,100 Hz job. These support the
generous engineering allowance; they do not establish certified receiver or
absolute timebase calibration. The pinned SDK derives the timer tick and
system PLL from XOSC. SDRplay's [RSP1B datasheet](https://www.sdrplay.com/docs/RSP1BdatasheetV1.0.pdf)
lists a high temperature stability TCXO; that specification is not substituted
for measured absolute calibration.

Adversarial assessment verified immutable attempt/packet/IQ bindings, positive
RF onset, threshold stability, separate worker/RF timestamps, same-boot
inactive authority, future-admission rejection, receiver integrity and the
declared timing margin. This closes only the recorded active-stop operational
row. Calibrated timing/general RF qualification remains outside this scope.
**Eight attempts and six RF jobs are charged.** Armed stop, active/armed busy,
quick reset and long-held AP remain open; GP14 default enablement remains off.

The next armed-stop preflight (`run-8d7702ca07104ae08b7e03cdfdfadc73`)
rejected the safely aborted job retained after the accepted stop. It reached
no cue, connection, CLAIM, receiver capture, LOAD or ARM; zero jobs are charged
and the event log is empty. The bound assessment resolves this host-only
failure without RF acceptance. The readiness wait now permits a same-boot
aborted job only with both GP14/worker inhibition latches and output inactive;
the physical quick tap must still produce a healthy released, synchronized,
empty new boot before admission. Regression checks reject either missing
latch and every nonempty new boot. The client suite and whitespace checks
pass; adversarial reassessment retains fresh-boot admission and finite bounds.
The campaign now has **nine attempts and six RF jobs**, leaving one attempt
under the original ten-attempt cap.

The repaired armed-stop wait (`run-e7ae625de53945468ea452759dd42445`)
expired before the required quick-reset boot. Zero jobs are charged; no cue,
connection, CLAIM, receiver capture, LOAD or ARM occurred. The event log is
empty and the bound nonqualifying resolution includes a hashed post-wait
INFO readback. B remains healthy, released, RF inactive and worker inhibited
in the accepted active-stop boot. It records three stop events, zero reset
events and a last contact duration of **912,000 us**: that contact selects
shutdown rather than the under-400 ms reset gesture. The cause of the duration
difference from the operator's intended tap is not established. Subsequent
trials will use USB reset for preparation and require only the local LED-cued
test gesture. **Ten attempts and six RF jobs** exhaust the original acquisition
cap; no further acquisition begins without an explicit budget extension.

The operator then explicitly authorized **15 attempts / 11 finite RF jobs**
to finish the five outstanding rows. The runner retains all historical counts,
20-second jobs and reviewed-assessment admission. Its optional LED cue can
now operate after verified USB preparation without a physical readiness tap;
cue readiness remains before CLAIM and cue activation remains after positive
armed/active state. The already-selected press debounce is 10 ms; no firmware
change or image replacement is required for that requested value.

The operator proposed an external digital-output rig connected to GP14.
That can provide actual pad-level low/release stimuli with repeatable timing
while retaining independent RF measurement. Rig identity, available output,
grounding and wiring must be established before controlling it; no rig pin
has been selected or operated. Remaining RF acquisitions are held while that
setup is chosen. This proposal changes neither the production debounce nor
the firmware's selected gesture boundaries.

## Accepted RF row: armed cancellation

The operator requested one more manual trial, with a stop if it failed.
USB preparation checked B's identity, inactive/unowned state and released
input, issued one REBOOT and verified a distinct empty, healthy, synchronized
boot. No readiness tap was needed. Run
`run-75b7f6417ddb4ac99aaa57cd1e16c49c` passes **armed cancellation** on
unchanged clean `3e1337074003`, boot `ca611516a4b04f0ec2a6e997ca00774d`,
job `6b6fb7cdd17b412795616f9433e56525`. Positive ARM precedes the local LED
cue; the recorded 7,517,000 us hold produces one verified stop, zero resets/AP
requests, a sticky worker latch and `launch_epoch=0`. Later CLAIM is rejected
BUSY. Worker acknowledgement is 126 us; this row measures prevention of launch,
not physical RF cutoff latency.

The complete ten-million-sample capture has exact receiver/settings, zero
overflow/timeout/clipping and verified cleanup. IQ SHA-256 is
`d95bc31c10e4e624e9ead982513e99c81d61a80157d10de3eb3dba3f14adb405`.
Independent 1 ms Fourier windows search 19–22 kHz above the 3.55 MHz receiver
center, covering the realized conducted tone. The maximum is 51.68 dB below
the previously observed active carrier. Thresholds 20, 30 and 40 dB below
that reference detect zero carrier windows across all 40 nominal seconds.
The scheduled launch is bracketed 19.803–20.889 s after capture start using
same-host clock request/reply timestamps and a 500 ms admission allowance;
the capture extends another 19.142 s beyond its latest bound.

The hashed assessment binds attempt, packet, events, IQ, capture metadata,
USB preparation, active reference and quiet reference. Adversarial reassessment
checked positive job-specific ARM, launch coverage, whole-capture absence,
receiver integrity, same-boot inhibition/admission refusal and exact saved
profile/access preservation across preparation and shutdown. This accepts the
conducted armed-cancellation row; calibrated timebase/general RF qualification
remains open. **Eleven attempts and seven RF jobs are charged.** Active busy,
armed busy, quick reset and long-held AP remain; GP14 default is still off.

## Accepted RF row: active shutdown during core-0 busy interval

Run `run-ac942570c12d4a36a858a4877c30941f` passes **active busy** on clean
`3e1337074003`, boot `389d894921b51ef32d84565210f44fcb`, job
`f89f294442a1473f8cfe5a9e857a5cb0`, after verified inactive/unowned USB
preparation. The 6,653,000 us physical hold produces one stop, zero reset/AP
requests and a healthy sticky worker latch. The core-0 busy interval is
22.629482–27.629482 s from boot; worker request/stop are
23.126283/23.126373 s, both strictly inside that five-second interval.
Worker acknowledgement is 90 us, separate from measured physical cutoff.

The complete receiver capture has exact settings, zero overflow/timeout/
clipping and verified cleanup. IQ SHA-256 is
`79c2f7b4fdef80b61ea077cf7ccc92d04f30ae9f15bdd5e1b7c7f8d67cc36ff3`.
Independent 1 ms Fourier windows observe one carrier at nominal sample times
5.338–8.478 s, 63.62 dB above baseline. Thresholds 20/30/40 dB below the on
level give identical edges. Its 3.140 s interval exceeds the recorded
decision-after-launch interval by 0.248 ms. The same declared 1% engineering
clock allowance, 2 ms edge allowance and 202 us launch-alarm allowance total
33.602 ms, yielding an upper relative cutoff estimate of **33.850 ms**, below
the 50 ms operational bound. No carrier returns during the remaining
31.522 nominal seconds. This capture spans 40 nominal seconds and agrees
with host delivery timestamps within the declared clock allowance.

Adversarial reassessment verified the job/boot/packet/IQ bindings, positive
physical launch, actual worker cutoff inside the busy interval, stable RF
edges, independent timing allowance, complete healthy receiver capture,
same-boot inactive/unowned authority, rejected later CLAIM and exact saved
profile/access preservation across preparation and shutdown. Calibrated
timing/general RF qualification remains open. **Twelve attempts and eight RF
jobs are charged.** Armed busy, quick reset and long-held AP remain;
production GP14 default stays off until those gates pass.

## Operator pause and verified inhibited restoration

Preparation for the armed-busy row issued one acknowledged USB REBOOT but
missed the 60-second readiness deadline before starting the acquisition.
Post-timeout INFO confirms a healthy released, empty, inactive new boot
`57b38e1b58d554a28a64fe0e6952e397`, with standalone scheduling disabled and
the saved station network/time now ready. The exact readiness condition that
missed the deadline was not recorded and remains unidentified. No LED cue,
receiver capture, CLAIM, LOAD or ARM occurred. The failed preparation is
retained as counted attempt `run-e761760476184fefb91f8e8f0df5221b`, charged
zero jobs, with a bound nonqualifying resolution. **Thirteen attempts and
eight RF jobs are charged.** No retry follows the operator's requested pause
for fleet testing; the remaining three rows need a future resumed packet.

B is restored to the retained inhibited baseline `615888e5364b`, UF2 SHA-256
`81361b105def84231c23853507bad81f992426260b9c935061fab82081d5239f`.
Fresh full backup SHA-256
`1181e02c15d8ebda4d853cdcf19113841be4b67f30cc66689a2cf94146b98646`
was retained and verified locally before load. All 57,344 reserved bytes match
before/after restoration, as do saved consumer profile generation 5 and
access generation 1. Readback boot `a6daf58691953440e1dab6d8af329157` is
healthy and RF inhibited.
Read-only LAN HELLO/STATUS additionally verifies the same B boot is empty,
unowned, has no job and no output; standalone scheduling remains disabled.
Private evidence is under
`build/phase12-gp14-rf-b-20260930/restoration-release-pause-13/` and the matching
wspr5 directory. A was not operated by this GP14 campaign; wspr4 was not
contacted. Adversarial closeout preserves the failed attempt, separates the
three passing RF rows from this no-RF timeout, verifies the backup barrier,
exact reserved storage and inhibited readback, and leaves default enablement
off. Armed busy, quick-release reset and long-held RF-to-AP availability remain
open. Exact coincidence with the short flash erase/program operation remains
the previously recorded evidence limitation.

## Resumed preparation with the SDR reconnected

The operator reported B reattached to the SDR and requested test preparation.
Fresh USB readback already showed the reviewed RF acceptance revision
`3e1337074003`, rather than the earlier inhibited restoration. B was empty,
inactive, released and synchronized, with scheduling disabled and saved
profile/access generations 5/1. No image was overwritten. Fresh unowned LAN
authority was verified before reading flash in BOOTSEL; all **6,274 ARM UF2
payload blocks** match the retained acceptance image exactly. The readback
parser initially rejected the additional RP2350 absolute compatibility block;
it was repaired against the retained SDK/picotool definition, requiring its
exact ignored-block tag/header/payload before excluding that one nonprogram
block. No flash write occurred. The fresh full readback and comparison evidence
were retained locally, then the same verified application was rebooted.

New boot `0076a61b72868ea959213d8126d79334` is healthy, released, empty and
RF inactive. Passive readiness observations record network/clock transitions
through synchronization, using a finite 180-second preparation allowance;
the identity-bound non-output cue readiness probe passes. Exact saved
profile/access state is unchanged. This does not establish the cause of the
earlier unrecorded readiness timeout.

The reconnected RSP1B `2404058C60` completes a separate three-second,
750,000-sample quiet capture with exact retained settings, zero overflow/
timeout/clipping and verified cleanup. IQ SHA-256 is
`ffa756c846f2c7f314bf03f51ec26843c0861d175b9d3947cc2762f0b306e6db`.
The 1 ms Fourier check detects no carrier at thresholds 20/30/40 dB below
the retained active reference; its maximum is 54.97 dB below that reference.
Private evidence is under
`build/phase12-gp14-rf-b-20260930/preflight-resume-armed-busy-14/` and the matching
wspr5 directory. Preparation submits no RF job; counters remain **13 attempts
and eight charged jobs**. Armed busy is prepared for the next operator cue;
all three outstanding RF rows and default enablement remain open.

## Accepted RF row: armed cancellation during core-0 busy interval

Run `run-242cf6742a2942b98e40fc05b10d93fa` passes **armed busy** on the
verified `3e1337074003` image, boot `0076a61b72868ea959213d8126d79334`,
job `22efe9ecdfcf473d800762b134e8080a`. Positive job-specific ARM precedes
the local cue. The 7,855,000 us physical hold produces one stop, zero reset/AP
requests and no launch (`launch_epoch=0`). Core 0 is busy from
749.663179 to 754.663179 s from boot. Worker request/stop at
750.296838/750.296929 s are strictly inside that interval; acknowledgement
is 91 us, separate from any RF cutoff latency claim. Healthy same-boot
inhibition persists and a later CLAIM is rejected BUSY.

The complete ten-million-sample receiver capture has exact retained settings,
zero overflow/timeout/clipping and verified cleanup. IQ SHA-256 is
`f6b852c73bf90c631c4119ecfb7fc895b328ca57a3afaa96cd29349fab96844a`.
Independent 1 ms Fourier windows covering the realized tone detect zero carrier
at 20/30/40 dB below the retained active reference throughout 40 nominal
seconds. The maximum is 55.25 dB below that reference. The newly reconnected
quiet capture is bound separately. Scheduled launch is bracketed at
19.800–20.921 s from capture start using same-host clock request/reply times
and a 500 ms admission allowance; another 19.118 s is captured beyond the
latest launch bound.

Adversarial reassessment checked positive ARM, job/boot/packet/image/IQ
bindings, actual worker stop inside the busy interval, whole-capture carrier
absence, planned launch coverage, healthy receiver/worker state, rejected
future admission and exact saved profile/access preservation. This accepts
conducted armed cancellation while core 0 is blocked, not calibrated timing
or general RF qualification. **Four of six rows pass; fourteen attempts and
nine RF jobs are charged.** Quick-release reset and long-held RF-to-AP
availability remain open. At that checkpoint, the 15-attempt ceiling left one
attempt; an explicit extension to 16 was requested for both remaining rows,
while keeping the 11-job limit. No limit was raised without an operator answer.

## Nonqualifying quick-reset trial and inhibited restoration

Preparation for trial 15 issued one acknowledged USB REBOOT into healthy,
released, empty boot `49deed0b0b9b7663139e176ff54f059b`. The new preparation
helper incorrectly looked for a nonexistent top-level `station_ipv4` field.
Its inactive poll was stopped and the lookup repaired to `network.ipv4`;
continued readiness verification used the same acknowledged reset and new
boot, with no mutation replay or extra job. Private records bind the interrupted
poll to its continuation. Synchronized station readiness, exact saved
profile/access equality and the non-output cue readiness check passed.

Run `run-986b41d58b2e46569d7aa24ae2dd84e4` then attempted **quick-release
reset**, job `d37081f6dca242a58da83239e3b779c4`. The controller started this
cue without obtaining a fresh operator Ready reply after the preceding Done.
No held input, stop, reset or AP event was recorded during its 100 observations.
The tone completed at its finite 20-second limit on the same healthy boot;
terminal history binds completion to the exact job, and cleanup verifies
empty/unowned/inactive authority. This does not establish a button failure or
accept the reset row. The workflow is corrected to require a new explicit
Ready reply before each acquisition.

The complete receiver capture has exact retained settings, zero overflow,
timeout or clipping and verified cleanup. IQ SHA-256 is
`608b3645b791cf2fcb80b971b1f3bb26f310aa1ecc0e806994c14f55f8088e48`.
The 1 ms Fourier check sees one carrier interval: 5,396–25,396 ms at 20 dB
below its on level, and 5,395–25,396 ms at 30/40 dB. Thus the finite carrier
lasts 20.000–20.001 nominal seconds, with another 14.604 seconds free of
carrier at those thresholds. The analysis binds attempt/events/packet/IQ and
metadata, records no physical events, and explicitly retains
`independent_rf_pass=false`. Saved profile/access state is unchanged. This
nonqualifying review does not admit an automatic retry.

B is restored to inhibited revision `615888e5364b`, UF2 SHA-256
`81361b105def84231c23853507bad81f992426260b9c935061fab82081d5239f`.
Fresh full backup SHA-256
`70ffde9bd6e873ca2dd43ee25bbe19db01481ab2552a75e277d93f566f6244dd`
was retained and verified locally before load. All 57,344 reserved bytes match
before/after restoration; saved profile/access generations 5/1 and contents
also match. USB readback confirms healthy inhibited boot
`7d92a0a4a8e6efbcc6ff094b225fc442`, empty and inactive, with scheduling disabled.
Read-only LAN HELLO/STATUS confirms the same boot, empty/unowned state,
no job and no output. Private evidence is under
`build/phase12-gp14-rf-b-20260930/` and the matching wspr5 directory. A and
wspr4 were not operated.

Adversarial reassessment separates the four accepted rows from this failed
readiness sequence, retains both host findings and repairs, verifies finite
completion/cleanup, the backup retention barrier, exact reserved state and
restored inhibited identity, and keeps default enablement off. **Fifteen
attempts and ten jobs are charged.** Quick-release reset and long-held
RF-to-AP availability remain open. A new extension to 17 attempts and 12 jobs
has been requested to cover both rows; the original limits remain enforced
until an explicit answer. Each further job remains limited to 20 seconds.

## Authorized orchestration preparation and Ready pause

On 2026-10-02 the operator answered **Execute** to the
[reset/AP continuation](phase12-gp14-reset-ap-continuation-prompt.md), authorizing
17 cumulative attempts and 12 jobs while requiring a fresh Ready for each row.
The [preparation review](phase12-gp14-continuation-preparation-review.md) records
the repaired accounting/image/Ready gates, concurrent-run interlock, unchanged
nonqualifying trial-15 resolution, 108/108 host checks, 15 orchestration tests
and pinned cross-builds. Both rows park without hardware access or a Ready
record; there is no response deadline or automatic acquisition while waiting.
Counters remain 15/10. Neither physical row nor default enablement is closed,
and B's inhibited restoration remains the last recorded physical state rather
than a new preflight claim.

### Live preparation checkpoint 2026-10-02

The [live preparation record](phase12-gp14-continuation-preparation-review.md#live-preparation-completed-after-premature-ready)
supersedes that waiting device state. The initial Ready was premature;
failed read-only baseline handshakes started no acquisition. A fresh full
backup was retained locally before serial-targeted loading of the reviewed
acceptance image. Exact programmed readback, all 57,344 reserved bytes, saved
settings, one preparation reset and synchronized empty/unowned/inactive
readback passed. B is now idle on `3e1337074003`, boot
`13f36788c9f2670f1e2dd5c197653c48`, with no Ready record or background acquisition.
The next fresh Ready begins quick-reset without repeating deployment.
Counts remain 15 attempts/ten jobs; both physical rows and final inhibited
restoration remain open. No RF pass or default enablement is added.

## Quick-release RF reset accepted 2026-10-02

After a fresh human **Ready**, run
`run-85db06e513bc47df8678603ee95da255` submitted one complete 20-second tone,
job `9127ff3215f540daab50fbb6e39a212e`, on prepared boot
`13f36788c9f2670f1e2dd5c197653c48`. The identity-bound local LED cue followed
positive active output; the operator subsequently answered **Done**. The
one-use Ready record, packet, runner, boot, successful LOAD and single ARM are
bound in the retained evidence. No ambiguous mutation was replayed.

Candidate B remains serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`, acceptance revision `3e1337074003`, engine
`pio-dma-gp2`, 138 MHz/divider 1 and GP2 RF output. The operator confirmed the
unchanged closed conducted 60 dB path on wspr5. The requested tone is
3,570,100 Hz; target realization is `3570100004319102` nHz. Independent RSP1B
`2404058C60` capture used CF32, 250,000 samples/s, 200,000 Hz bandwidth,
3,550,000 Hz center, gain 20 dB, channel 0, with AGC and bias tee off.

The exact normal-reset marker records a **328 ms** physical contact and a
decision **3,664,197 us after RF launch**. Distinct healthy normal boot
`ac1c5c761775b0b85ba92ca396de8795` is empty and inactive, with no resumed job,
disabled scheduling and unchanged saved profile/access contents and generations
5/1. Fresh post-reset USB INFO verifies synchronized time and released input;
Plain LAN HELLO/STATUS verifies the same boot, empty/unowned authority and no
job or output. No old-boot
worker acknowledgement timestamp was captured for this row; the relative reset
marker, independently observed RF edge and normal boot provide its evidence.

The complete 40-second receiver record has ten million complex samples,
80,000,000 IQ bytes, finite IQ throughout, zero overflow, timeout or clipping,
and verified stream/device cleanup. IQ SHA-256 is
`0ecf01873acf43d69ffa4eeb998927acd37f1aa6607fc2a3d59c3ae95f73b260`;
metadata SHA-256 is
`6233603ad23a946136e1941dbe1765039274c07d2e7bd48ecdb8d666d390fa7e`.
The retained wall span is 40.03 seconds for 40 nominal sample seconds.

Independent 1 ms Hanning Fourier windows, searched 19–22 kHz above receiver
center, find a 77.033 dB carrier/background contrast. At 20/30 dB below on-level,
the single carrier interval is nominally 5,328–8,992 ms; at 40 dB it is
5,327–8,992 ms. The 1 ms onset difference is retained, not reported as identical
edges. The longest 3.665-second interval is used conservatively. Its relative
cutoff delay is 0.803 ms beyond the target decision interval. The inherited
**uncalibrated engineering** 1% clock-scale allowance contributes 36.650 ms;
two Fourier edges add 2 ms, launch-observation offset adds 0.009 ms and reset
marker quantization adds 0.001 ms. Total uncertainty is 38.660 ms and the
conservative upper delay is **39.463 ms**, below the 50 ms operational bound.
No carrier returns during the remaining 31.008 nominal seconds. This is the
bounded conducted reset check, not calibrated timing or general RF qualification.

The separate hash-bound assessment sets `independent_rf_pass=true`; the
acquisition's original pending-assessment record is unchanged. Its attempt,
events and packet hashes are respectively
`f87057f57e12ad37e114fb1585802c8896b70f49bdc74755227fbca165e38b7d`,
`4a592630bad30c25d8d99519a53b6cfb496f2feea0921b8eb33a2a08b51ce57c`
and `0a52d238dc5bdf175a2fea499a504a8bc969fc0bba411eba3e52b4f8d6977213`.
Private capture, assessment and `post-quick-reset-16` readback are retained
locally under `build/phase12-gp14-rf-b-20260930/` and in the matching wspr5
campaign. All fifteen prior attempts and their charges remain intact.

Adversarial review checked Ready consumption, single complete job/ARM,
identity/image/boot binding, physical classification, expected disconnect,
reset marker versus launch, swept thresholds and conservative uncertainty,
absence of RF restart, preserved settings and fresh post-reset unowned
authority. **Five of six RF rows are accepted; sixteen attempts and eleven RF
jobs are charged.** Long-held RF-to-AP availability and default enablement
remain open. Broader Phase 12 remains `OPEN_PARTIAL`.

## Final-row preparation stopped before acquisition

The next-row helper stopped at its initial released/inactive readiness guard,
before its preparation REBOOT, a Ready record, receiver capture or RF job.
Read-only diagnosis subsequently found boot
`51c960c0b6d8686a8177773620631dd2`, not the accepted row's final boot, with
GP14 held, both output inhibition latches asserted, one stop and one AP event,
empty/inactive output, unsynchronized time and unavailable LAN WTP. Storage,
stack/allocator/capture health and saved profile/access checks pass. No cause
is inferred from the held-input telemetry, and this is neither acceptance of
the long-held RF row nor proof of a device defect.

The continuation stopped under its first-unexpected-result rule, despite
one attempt/job remaining inside the authorized 17/12 ceiling. The operator
was asked to release GP14 solely for safe restoration and answered **Released**.
No further RF
acquisition is authorized by a previous Ready or Done. A new reviewed
continuation packet and explicit operator approval are required before
resuming the remaining row. The failed `prepare-long-ap-17` and read-only
`long-ap-preparation-stopped-16` evidence remain retained; counters are 16/11.
B was then the acceptance image with RF inhibited by the input/worker latches,
not the inhibited firmware baseline. The restoration recorded below completes
that cleanup without a further acquisition.
Default GP14 remains off; no firmware source safety behavior or default build
option is changed. The authorized installed-image restoration is below.

## Inhibited restoration verified 2026-10-02

After the operator's Released reply, USB readback confirms released GP14,
empty inactive output and the known stopped boot. One guarded BOOTSEL command
entered ROM. The exact acceptance source checks unowned/inactive authority and
verified engine disable before acknowledgement and again before ROM entry;
no unready LAN handshake, forced reset or mutation replay was used.

The fresh 4 MiB RF flash backup, SHA-256
`70ffde9bd6e873ca2dd43ee25bbe19db01481ab2552a75e277d93f566f6244dd`,
matches all 6,274 acceptance payload blocks and the prior deployment's 57,344
reserved bytes. It was retained and independently hashed on the Mac before
the inhibited image write. A second ROM readback matched that exact backup
before loading the baseline. All 6,578 inhibited payload blocks subsequently
match UF2 SHA-256
`81361b105def84231c23853507bad81f992426260b9c935061fab82081d5239f`;
all reserved bytes remain identical. Independent local verification of the
full restored readback also passes, with full-flash SHA-256
`e77aa61396cda525c1ad2d437e69ac30ed4f52cec7cc302261839e816c8b7d99`.

USB INFO verifies revision `615888e5364b`, inhibited simulator engine, healthy
storage/stack/allocator/input, exact saved profile/access/scheduler settings
and disabled scheduling. One guarded baseline reset provides a second
unowned/inactive reset check and distinct healthy final boot
`acc79f7a70b9f8a966a0fd76c15e622b`. Fresh USB INFO and read-only Plain LAN
HELLO/STATUS/GET_CLOCK verify that same boot/device, empty/unowned authority,
no job or active output and synchronized usable time. Saved profile/access
generations remain 5/1. Receiver cleanup from the completed acquisition is
verified, and restoration submits no job or Ready record.

Private `restoration-stopped-continuation-16` backup, full readbacks and
prepare/complete/final-authority records are retained on wspr5 and the Mac.
A, wspr4 and unrelated Pi services were not operated. **B is restored inhibited;
five of six RF rows pass; counts remain 16 attempts/11 jobs.** The remaining
long-held RF-to-AP row and default enablement are open. No further RF is
admitted by this stopped continuation; broader Phase 12 remains `OPEN_PARTIAL`.

Documentation adversarial review corrected stale prepared/current wording and
an overstatement of the post-reset operations: that record contains USB INFO
and LAN HELLO/STATUS, not a GET_CLOCK exchange. The independent assessment was
revalidated offline against the retained IQ, complete LOAD/ARM, cue/Ready,
released reset boot, capture format and exact existing assessment; it changes
no original artifact. Restoration review verified the release boundary,
single guarded ROM entry, exact images, local backup barrier, invariant reserved
bytes/settings, guarded baseline reset and direct final unowned readback.
Reassessment retains the five accepted rows and verified restoration without
claiming long-held AP acceptance. Fifteen orchestration tests pass normally and
with Python optimization; WTP contract, changed-file whitespace and 84 local
Markdown links/anchors pass. These are current affected checks, not new full
host-suite or firmware cross-build claims. All six unrelated files retain their
pre-turn content hashes and are excluded from this commit.

## Final long-ap attempt failed — 2026-10-06

The operator confirmed the established connected setup and answered Ready.
The final named `long_ap` run,
`run-380467fbc52d47ef9ebb4ec53bd3c063`, used Pico B
`CDDBF8767C506C07` / `29f20b7342051ef947aa56cb9d4fab42`, source
`c0d2bd53e4bde67af64d9528e3ee89efce51b87a`, RF UF2 SHA-256
`5b4774af6bfe507b098cb8ff86ffd67040fab718240ab0bf4834ac10496c03c8`
and boot `99396fc326f6bd51e5b49bab033842c3`. The engine was `pio-dma-gp2`,
GP2 output, GP14 button, 138 MHz, with one 20-second Tone at 3.5701 MHz and
the retained RSP1B `2404058C60` capture settings/metric. No path inventory or
further path questions were required.

One acquisition and one successfully armed job were charged. At launch the
Console INFO grew beyond its 8,192-byte queue and returned
`console_response_capacity`. The run sent **no physical LED action cue** and
stopped. Owned ABORT/RELEASE passed; final original WTP STATUS showed the
same boot, empty/unowned/inactive authority and the aborted job's terminal
record. The receiver retained 10,000,000 CF32 samples/80,000,000 bytes without
overflow and verified stream/device cleanup. Its successful capture is not
a qualifying physical-button cutoff.

The operator's subsequent visit showed the identity-only recovery page, with
Wi-Fi setup explicitly unavailable. Its device ID matches B. The private
screenshot corroborates the reported unusable portal and is not repository
content. There is no qualified 12–15-second hold/release bracket, independent
cutoff assessment, same-boot AP/HTTP proof within 90 seconds, or usable-portal
pass. Preserve `FAILED_STOP_CAMPAIGN`; do not relabel the later hold as a pass.

Original attempt SHA-256:
`4e4825694624e550363a851ad85e841e4c98d4d245febadc911ac3dab4872907`.
Original events SHA-256:
`a9cda9c35242b46f7c386f967400ed7060472d42cae8e8c9c547f18029c1d19f`.
Capture SHA-256:
`4848bf199909023fc9a4556683b6cf8371d0309afecb7dc9f9c0e7094a54b8ee`.
The failed originals and capture remain private on wspr5 and the Mac.

**Five of six RF rows remain accepted; accounting is now 17 acquisitions / 12
charged jobs. The authorized ceiling is exhausted.** No automatic retry or
GP14 default enablement follows. The demonstrated Console/portal repairs and
their source/target validation are recorded in the
[four-group results](phase12-orchestratable-closeout-results.md#final-four-group-continuation-2026-10-06).
They do not grant physical G7 acceptance. Actual recovery is authorized for
the broken Console/portal path; another acquisition needs explicit additional
budget for this same row or an explicit scope disposition.
