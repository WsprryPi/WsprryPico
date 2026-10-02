# GP14 production RF integration and acceptance

Status: **FOUR RF ROWS ACCEPTED; CONTINUATION AUTHORIZED; WAITING FOR READY; DEFAULT OFF** (2026-10-02).

## Authorization and scope

The operator answered "Let's do it" to the proposed RF build repair,
independent worker shutdown, bounded active/armed cutoff measurements,
adversarial repair/reassessment and eventual default enablement/commit/push.
Use `devel`, preserve the existing unrelated changes and all adapter settings.
Use Candidate B (`CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`) for the RF acceptance candidate and the
established closed conducted path on wspr5. A remains inhibited during the
cutoff campaign. wspr4 is offline and must not be contacted or changed.

The current retained inhibited restoration image is `615888e5364b`, UF2
SHA-256 `81361b105def84231c23853507bad81f992426260b9c935061fab82081d5239f`.
Bind each deployment to fresh USB identity/readback, its exact committed image,
a fresh full backup and identical reserved storage before/after loading.
Recheck the receiver identity and existing helper before capture. No incidental
tool/SDK installation, network replacement, station Save or journal erase.

## Implementation packet

1. Repair `WsprryPico-StandaloneRF`: share the provisioning/crypto/BTstack
   dependencies used by its common main, configure a 32 KiB guarded primary
   stack, retain the independent 16 KiB worker stack and verify memory bounds.
2. Keep PIO/DMA GP14 capture for core-0 blackout/replay handling. Add a portable,
   latched safety policy sampled by the RF-owning worker. Recognized stop/reset
   or safety faults inhibit further preparation/arming and synchronously stop
   the engine without a core-0 RPC. Refuse launch after the latch. Never call
   engine, flash, reset or CYW43 operations from the input sampler interrupt.
3. Core 0 reconciles the same JobService/scheduler before other admissions,
   confirms inactive output and then admits AP or normal reset. Preserve the
   selected 10 ms press debounce, 100 ms stable release, under-400 ms reset,
   900 ms held stop, 9 s held AP,
   boot-held ignore and one action per gesture. The latch persists to reboot.
4. Add an explicit RF acceptance build option with an identity-bound, finite
   core-0 busy operation and timing/status readback. Keep that operation absent
   from normal images. No job may start automatically in the test image.
5. Run deterministic boundary, race, failure, busy-producer and latch tests;
   build inhibited, RF and acceptance variants with pinned existing SDK/tools.
   Review PIO/DMA/IRQ ownership, clocks, heap/stack, flash-safe pauses and launch
   races. Repair findings, rerun affected checks and reassess before deployment.

## Bounded target packet

Prepare the exact image/receiver/job settings and finite host runner before
each output action. Use finite tone jobs on the already recorded conducted
frequency path; independent capture must establish actual carrier cutoff.
No broad mode/band or Stage B coexistence campaign is included.
The explicit RF target retains its existing read-only bootstrap surface;
the AP row qualifies network/listener availability after shutdown. It does
not claim station-save functionality on that RF variant. The normal inhibited
image retains the accepted editable portal.

Required rows are active stop, armed cancellation, active and armed stop while
core 0 is deliberately busy, quick-release reset and long-held AP after stop.
The operator supplies real GP14 contact; firmware injection cannot replace
physical input or independent RF evidence. Record input/classification and
worker cutoff timestamps, RF launch/termination, busy interval and the exact
job/boot identity. The proposed acceptance bound is 50 ms from the selected
stop/reset decision to inactive RF; retain measured uncertainty and reject
evidence that cannot resolve that bound. Armed cancellation must prevent later
launch. New output admission after the stop latch must fail.

Use no more than eight finite RF jobs of at most 30 seconds each in the initial
packet, no unattended repetition and stop on the first unexpected result.
Record each attempt, including failed starts. The controller separately caps
acquisition attempts at ten; a rejected LOAD with no ARM consumes an attempt,
and every possibly sent ARM consumes one of the eight RF-job charges.
On 2026-10-01, after ten attempts and six charged jobs, the operator explicitly
authorized extension to **15 total acquisition attempts and 11 total RF jobs**
to finish the five remaining rows. All further jobs are at most **20 seconds**.
No counter is reset and historical failed attempts remain counted.
After the subsequent nonqualifying quick-reset trial, all 15 attempts and
ten jobs are charged. The operator answered **Execute** on 2026-10-02 to the
[reset/AP continuation](phase12-gp14-reset-ap-continuation-prompt.md), authorizing
17 total attempts and 12 total jobs for the two outstanding rows. This grants
no standing Ready: orchestration must park until a fresh acknowledgement for
each row. The earlier pending request for 16 attempts did not cover both rows.
Keep the core-0 busy interval
below the existing 8-second watchdog. A watchdog recovery row may require a
separate reviewed stimulus; do not improvise a destructive fault.

An operator-requested retry of a finite active-stop timeout with no recorded
input may proceed only after reviewing positive launch, exact finite job/boot
completion and inactive cleanup. The explicit retry flag binds those retained
events and keeps the failed attempt counted and unaccepted. It cannot resolve
an observed gesture, safety fault or ambiguous cleanup. An unexpected reset
still stops the campaign for review and restoration.

Chat cue delivery proved too slow for a 20-second tone. The physical-ready
flow waits RF-inactive for one operator quick tap/reset, then requires a new
healthy, released, synchronized boot and fresh empty/unowned WTP admission.
It starts one finite acquisition and uses the existing identity-bound triple
LED identify pattern only after positive active RF (or positive armed state
for armed rows). The operator watches B locally and performs the required
gesture at that cue. An unsignaled wait ends after ten minutes without an RF
job; faults, unqualified resets and early input refuse admission. No firmware
input injection or new automatic output policy is introduced.

The operator's later intended tap was recorded as 912 ms, outside the selected
under-400 ms reset interval. For the authorized continuation, prepare each
trial with one USB REBOOT after verified inactive/healthy state, then require
a distinct released, synchronized, healthy boot and empty/unowned admission.
Use `--led-cue` to verify cue readiness before CLAIM and flash locally only
after positive armed/active admission. This removes the readiness tap from
the operator's trial steps. The physical quick-release reset acceptance row
still requires real GP14 contact and remains a separate gate. Press debounce
is already 10 ms; the 100 ms release filter does not lengthen measured holds.

Require a fresh explicit operator Ready reply for each acquisition before
starting its finite job and local cue. A Done reply for the preceding row is
not readiness for the next row. The first quick-reset cue was started without
that fresh handshake; no GP14 input was recorded, and the finite job completed
without a reset. That trial remains counted and unaccepted. B was restored to
the retained inhibited baseline after verified empty/unowned cleanup and a
fresh, locally retained full backup. Do not replay that trial automatically.

Finish with inactive, empty/unowned, healthy storage and exact settings
comparison, then restore the retained inhibited image. Enable GP14 by default
only after source review and the required target rows pass; the standard image
must remain RF-inhibited. Capture during the extended flash-safe pause remains
accepted in its existing scope; exact coincidence with erase/program remains
unmeasured and is not silently promoted by this packet.

## Closeout

Retain private captures/backups/image manifests under ignored `build/` and
the matching wspr5 packet directory. Publish redacted assertion-level evidence,
source/image identities, timing bounds, restoration and remaining limitations.
Perform adversarial review, repair and reassessment, commit and push, and
independently verify remote parity. Update P12.7's production gate only to the
scope actually established; the broader Phase 12 gates remain separate.
