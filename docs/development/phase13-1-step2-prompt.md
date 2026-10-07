# LED closeout step 2 execution prompt

Work on `devel` in `/Users/lbussy/GitHub/WsprryPico`. Execute step 2 of the
fixed six-step LED closeout: complete one untimed operator setup so steps 3–6
can subsequently run without rewiring, button presses or continuous attention.
Both Pico A and Pico B are connected to the SDR and authorized for the tests,
including routine device controls, firmware loads and restoration. Do not ask
for another RF or per-job authorization. Step 2 does not run the RF matrix.

## Objective and boundaries

Prepare and verify board/receiver identity, conducted RF path, external LED
fixtures for both polarities, independent recording and the automatic GP14
stop stimulus. Preserve the external TX-only contract: AP/Identify stay on the
onboard LED; onboard TX is the default; disabled indication remains supported.
Keep the fixed step numbers. Restoration follows every actual device mutation,
even when the final evidence review belongs to step 6.

Read project instructions, README, CONTRACT, architecture, development guide,
runner guide and the step-1 review. Inspect branch/tree and preserve user work.
Do not alter other repositories, credentials, conducted attenuation or receiver
reference settings. Reuse retained tools and dependencies; do not install a
camera stack or SDK incidentally. Use `wspr5` as the existing control/capture
host. Record exact command/source/tool hashes for any deployed preparation
payload; tool approval restrictions remain distinct from hardware authority.

## Execute all independent preparation first

1. Verify named USB serial/device identities and installed revision/boot/engine,
   inactive output, disabled schedules and actual owner authority where exposed.
   Record missing authority as unknown. Never treat an unsynchronized consumer
   LAN refusal as successful WTP inspection or bypass its access policy.
2. Identify the RSP1B by serial, inspect existing capture users and verify retained
   picotool/capture-helper/FFmpeg hashes. Confirm persistent storage for the
   entire retained matrix, video and flash backups, not only one capture.
   Inventory actual camera capture capabilities; Pi codec/video nodes
   are not evidence that an optical camera exists. Record absent equipment.
3. Select a proposed DUT and stimulus board, preserving the existing RF wiring.
   Verify physical header numbers against the official Pico 2 W pinout. Write
   a single plain-language wiring sheet with LED polarity, current limiting,
   inactive bias, 3.3 V supply/ground and the separate stop line. Account for
   fixture reset/high-impedance states and avoid connecting two driven outputs.
4. Prepare the private setup/evidence packet, tool bindings, finite camera/SDR
   smoke checks and readiness criteria. Do not fabricate camera paths, modes,
   regions, wiring confirmations or measurements. No example packet is ready
   until real equipment and physical connections are verified.
5. Ask early about equipment availability. Once the wiring sheet is concrete,
   gather the remaining operator actions together. The operator may take as
   long as needed. No expiring approval token, countdown, timed release, active
   RF waiting for a reply or required reaction to a transient LED cue.

## One operator setup session

Confirm physical A/B identity and the unchanged conducted path to receiver
`2404058C60`. Connect both external polarity fixtures on the DUT, the inhibited
stimulus board's automatic stop connection and a shared logic ground. Use
current limiting and appropriate inactive bias. Wiring changes happen with
board power removed; record any existing accessories or conflicting pin use
before specifying connections. Restore power only after the wiring is checked.

Connect and position the available recording equipment to see the onboard and
both external LEDs without saturation or obstructions. Provide actual camera
identity/capture mode and regions of interest; verify focus/exposure and short
recording playback. Optical regions must distinguish the three LEDs. Resolve
any material camera limitations before requiring the operator to leave.

Ordinary video can support visible plateau and cue observations. It does not
prove microsecond RF/LED edge ordering without independent synchronization and
sufficient resolution. Record the attainable scope and any remaining timing
qualification explicitly; do not silently substitute firmware telemetry for
independent optical evidence or turn a proposed exclusion into acceptance.

## Bounded preparation checks

Use no RF admission for ordinary setup smoke checks. Verify a short retained
SDR capture, camera frame progress/playback and clean process exit. Firmware/GPIO
preparation, if needed, requires actual quiescent authority, exact image/board
binding, full-flash/settings preservation and verified cleanup/restoration.
Use inhibited preparation images only; do not leave a fault or stop input active.
Automatic stop stimulus must release locally within its finite bound and after
reset; preserve wiring and physical measurement evidence for that assertion.
Never infer successful electrical release solely from a USB response.

After operator wiring, record real fixture roles, pin continuity/released logic
level, receiver/camera identities, exact tool hashes, recording mode/regions,
evidence paths and timestamps in private ignored `build/` storage. Keep a
sanitized result/review in the repository. Distinguish operator-confirmed wiring,
automatically verified recording and unresolved automation prerequisites such
as time/transport availability. Step 2 may be marked complete only when its
required physical inputs are confirmed and checked; missing hardware remains
an explicit pending item, not a software pass.

## Adversarial review, completion and publication

Review wrong-board/physical-pin confusion, LED direction and resistor values,
GPIO collisions, floating/reset states, back-power/output contention, actual
camera capability, saturated/overlapping regions, private data handling,
finite process cleanup, source/tool binding, false readiness, clock/owner gaps,
restoration and any hidden operator dependencies in steps 3–6. Fix actionable
findings, rerun affected checks and perform another assessment until no
actionable issue remains. Do not close unperformed physical checks by editing
their status or invent new RF budget/admission retries.

Maintain the step record and development links. Commit and push the reviewed
slice without force; independently verify remote parity and report actual
repository state. Refresh candidate bindings if a changed source commit makes
the live manifest stale. Report the executed prompt, concrete operator setup,
checks/evidence, actual hardware changes/restoration and remaining limitations.
If equipment or a user response is still required, preserve the useful completed
work and the pending request; do not claim step 2 or LED qualification complete.
