# P12.7 GP14 RF integration review

Status: **source gates passed; physical RF acceptance pending** (2026-09-30).
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
