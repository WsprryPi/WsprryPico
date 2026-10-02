# Phase 12 GP14 reset and AP continuation prompt

Status: **EXECUTION AUTHORIZED; SOURCE PREPARATION PASSED; PAUSED FOR FRESH READY**
(2026-10-02).

Complete only the two remaining P12.7 conducted GP14 rows: quick-release reset
and long-held RF-to-AP availability. Four of six rows are accepted. Phase 12
remains `OPEN_PARTIAL`; this packet cannot close commissioning, recovery,
Stage A robustness or Phase 13 release/RF qualification.
The [preparation review](phase12-gp14-continuation-preparation-review.md) records
the repaired findings, checks and exact waiting checkpoint.

## Execution authority and Ready boundary

The operator answered **Execute** on 2026-10-02 after discussing orchestration,
the two hands-on sessions and the requirement to pause for acknowledgement.
That authorizes this continuation, including the following bounded scope:

> Authorize the Candidate B GP14 reset/AP continuation on the existing closed
> conducted path, including reviewed image loading, USB preparation/readback,
> receiver captures, physical GP14 gestures, read-only AP checks and final
> inhibited restoration. Extend the cumulative campaign limits to 17 acquisition
> attempts and 12 RF jobs, with each additional job limited to 20 seconds.
> Preserve all 15 previous attempts and ten charged jobs. Require my fresh Ready
> reply before each acquisition. Perform the scoped repairs, adversarial review,
> reassessment, conditional default enablement and commit/push described below.

The extension is now authorized; a fresh Ready has not been supplied. The
previous 15 attempts and ten jobs remain charged. The extension permits at most
**two additional attempts and two additional jobs**, not two passes plus free
retries. A failed acquisition
still counts. Charge every possibly transmitted ARM before sending it; never
replay an ambiguous ARM. Rejected LOAD without ARM consumes an attempt only.
Stop on the first unexpected result, even if budget remains. Further retries or
additional affected RF rows require a new reviewed packet and explicit budget.

## Execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Start with code and tooling
review, respect the Ready boundary above, repair actionable findings,
perform an adversarial reassessment, and commit/push only this slice. Keep the
operator informed with short result-first updates and request only the named
physical interactions. Do not rerun the four accepted rows for duplication.

### Read the current boundary and preserve existing work

Read AGENTS.md, README.md, CONTRACT.md, [architecture](../architecture.md),
[development checks](README.md), the [Phase 12 ledger](phase12-plan.md),
[original RF brief](phase12-gp14-rf-execution.md),
[latest RF review](phase12-gp14-rf-review.md) and
[inhibited integrated closeout](phase12-gp14-integrated-acceptance.md).
Inspect branch, HEAD, working changes and current evidence before editing.

At preparation, `devel` HEAD is `1963431836bd`. Existing modified README.md,
CONTRACT.md, architecture and browser API files, plus untracked pin-assignment
and transmitter-application contracts, belong to separate work. Preserve them
and do not stage them. Recheck at execution; never reset, stash or overwrite
concurrent work. This is not a code freeze or a release drift-sentinel task.
Resolve actual overlaps with the operator before editing them.

The four accepted cases are `active_stop`, `armed_stop`, `active_busy` and
`armed_busy`. Trial 15 recorded no GP14 input after a cue started without a
fresh Ready reply. It remains counted and unaccepted, not a device finding or
permission for an automatic retry. Use the latest review rather than older
historical paragraphs as the current boundary.

### Bind the exact board, image and conducted path

Use Candidate B only: USB serial `CDDBF8767C506C07`, full device ID
`29f20b7342051ef947aa56cb9d4fab42`. Do not operate A or contact/change wspr4.
Use the retained wspr5 campaign and independently captured RSP1B
`2404058C60`; confirm the physical closed path and its 60 dB attenuation with
the operator before deployment. GP2 remains RF output, GP14 physical pin 19
is the existing active-low input to ground, and the onboard LED supplies the
local cue. Do not drive GP14, change wiring, add an external stimulus rig or
use BOOTSEL as a runtime button.

The reviewed acceptance image is source
`3e1337074003616c23d9b8749e728c99c71738c6`, revision `3e1337074003`, UF2
SHA-256 `658605e4bc66094849be71ee6bb59c91d335d6e1fb7fe99ad54d96b27cf09aa5`
(3,212,800 bytes). It uses `pio-dma-gp2`, 138 MHz/divider 1, opt-in GP14 and
acceptance-only telemetry. Source gates are not deployment evidence.

B was last verified restored to inhibited revision `615888e5364b`, UF2
SHA-256 `81361b105def84231c23853507bad81f992426260b9c935061fab82081d5239f`.
The latest retained backup has SHA-256
`70ffde9bd6e873ca2dd43ee25bbe19db01481ab2552a75e277d93f566f6244dd`.
That is historical evidence, not a substitute for a fresh backup and readback.
Confirm current B identity, healthy storage, inactive output, empty/unowned
authority and disabled autonomous scheduling. Retain and verify a fresh full
backup locally before each authorized image load. Compare all 57,344 reserved
bytes and exact saved settings before/after; expected saved profile/access
generations are 5/1, but investigate any drift instead of overwriting it.

The job is one complete 20-second tone requesting 3,570,100 Hz, with reviewed
frequency realization. Receiver settings are CF32, 250,000 samples/s,
200,000 Hz bandwidth, 3,550,000 Hz center, gain 20 dB, channel 0, AGC and bias
tee off. Preserve the 40-second, ten-million-sample capture and finite receiver
cleanup deadline. Require exact receiver settings/identity, complete IQ/hash,
zero overflow/timeout/clipping and verified receiver cleanup.

### Review and repair the continuation tooling before deployment

Review [the acquisition runner](../../scripts/phase12_gp14_rf.py), preparation,
capture, independent analysis, backup and restoration helpers against the
actual INFO/WTP schemas and reset behavior. Use existing pinned dependencies;
do not download tools or an SDK. Keep RF-owning worker safety independent of
core 0 and keep the single JobService/scheduler/ownership authority.

Reconcile the original private campaign under
`build/phase12-gp14-rf-b-20260930/` and its matching wspr5 directory. Its retained
`ledger-after-quick-reset-15.json` records 15 attempts/ten jobs. The local
top-level `packet.json` still names older `62ae4c2c2567` firmware; the newer
`packet-release-3e13370.json` and matching manifests must be verified against
the actual controller packet and image. Do not use whichever file happens to
be named `packet.json`, or reset accounting by creating an empty campaign.
Bind each run to the selected packet, committed image, boot, job and receiver.
Run the physical acquisition on wspr5, not the Mac: the runner uses Linux USB
paths and the retained wspr5 capture helper. Verify any deployed helper against
the reviewed source. Do not change another repository or unrelated Pi services.

The continuation runner now enforces the authorized 17/12 cumulative ceilings,
anchored to the original fifteen-attempt checkpoint. Its offline `--prepare`
mode creates neither a Ready record nor an acquisition, accesses no hardware,
and requires complete historical evidence. The explicit `--packet-file` selects
the reviewed retained image without overwriting earlier packet files.
Preserve inert defaults, explicit physical opt-in and one acquisition per
invocation. Never remove assessment barriers to get a run started. Review a
hash-bound nonqualifying resolution for trial 15: no physical input, exact
finite completion, inactive cleanup, healthy state and unchanged settings.
Keep `independent_rf_pass=false`, the original artifacts and all charges.
The original no-input retry helper remains restricted to `active_stop`; do not
mislabel this `quick_reset` attempt to fit it. The separate historical trial-15
resolution validates its actual INFO schema, WTP admission/completion and
capture bindings without changing the original false qualification. Resolution handling
must reject observed gestures, faults, ambiguous completion/cleanup, altered
artifacts and unrelated cases.

Make the fresh human Ready gate explicit and one-use. A previous Done, old
Ready or standing execution approval is not readiness for the next job.
Only after the actual human Ready may `--acknowledge-ready` create a record
bound to the row, packet, controller path, runner and cumulative counts.
`--run --led-cue --ready-file ...` consumes it once before hardware access.
The acknowledgement must be consumed within five minutes; a stale record
requires a new Ready, never an automatic refresh. Exclusive campaign locking
prevents concurrent acquisitions from racing accounting or launching together.
Test cumulative exhaustion, ambiguous ARM charging, missing/stale Ready,
wrong identity/image, failed prior assessment, expected USB disappearance on
quick reset, same-boot failure, receiver finalization and fail-closed cleanup.
Use deterministic fixtures; no physical test is an incidental unit check.
If repairs change shared gesture/RF safety behavior, identify affected accepted
rows and stop for revised authority rather than silently reusing their results.

### Prepare and obtain Ready separately for each row

After authorized deployment, verify exact programmed-image readback and
settings preservation. Prepare each acquisition with one acknowledged USB
REBOOT only after inactive/healthy/empty/unowned verification. Require a
distinct healthy boot, released GP14, synchronized clock and fresh empty/unowned
USB/LAN readback within the retained 180-second preparation allowance. Do not
replay REBOOT after an uncertain reply or timeout. Verify the identity-bound
non-output cue readiness before CLAIM. Use `--led-cue`, not a physical readiness
tap.

Explain the gesture, confirm the operator is watching B, then wait for a new
explicit Ready reply for that row. Submit only that row's finite job. Flash
the identity-bound triple LED cue locally only after positive active output
for the exact boot/job. Do not rely on chat delivery as the action cue. The
operator's Done reports completion; assess the row before preparing the next.
Park for the operator without a response deadline, background acquisition or
assumption that they remain at the screen. Readiness is not created while
waiting. Refresh device preflight when they return; the finite preparation,
job and receiver deadlines apply only to the corresponding active steps.
Readiness timeout without an acquisition submits no RF job; any acquisition
already started remains charged even if it fails before ARM.

### Accept quick-release reset only with physical and independent RF evidence

At the LED cue, ask the operator for one quick GP14 contact and release,
measured under 400 ms. The existing 10 ms press debounce and 100 ms stable
release filter remain unchanged; the release filter does not add to measured
hold duration. A 912 ms contact is shutdown, not reset acceptance.

Require positive active carrier before the gesture, the exact normal-reset
marker and physical duration, decision time relative to that job's RF launch,
one distinct healthy boot and inactive output with preserved settings. Account
for the expected CDC/WTP disconnect without replaying LOAD/ARM or counting
unrelated boots as success. Retain complete independent capture across reset.
Reject capture or clock uncertainty that cannot resolve the 50 ms decision-to-
inactive operational bound. Worker acknowledgement alone is not RF evidence.
Confirm no carrier restart during the remaining capture and no resumed old job.
The safety latch is cleared by a normal reboot; do not require the new boot to
retain the previous boot's latch. Scheduling must remain disabled.

### Accept long-held AP only after verified RF shutdown

On a separately prepared boot and a new Ready reply, cue one physical hold of
12 to 15 seconds, then release. Require one stop at the selected 0.9-second
held threshold, independently measured RF cutoff within the same 50 ms bound,
and one AP request at 9 seconds only after shutdown is confirmed. Require
same-boot health, no reset, no repeated stop/AP actions while held beyond
10 seconds, persistent output inhibition and no later carrier return.

Record AP and service readiness while still held and after release. Prove
actual AP association and a read-only HTTP response through the AP interface,
not just firmware telemetry or a station-address page. If phone participation
is needed, have the operator join B's AP and manually open
`http://192.168.4.1/`; never ask them to Save or replace credentials. Complete
the AP association/HTTP check within 90 seconds after release and record the
actual observation duration. Inability to do so leaves the row open, not an
invitation to repeat RF. The RF variant has a read-only bootstrap: this row
accepts AP/listener availability, not editable commissioning or a new
ten-minute lease/soak claim. Confirm the
same-boot latch rejects later output admission and reconcile empty/unowned
authority without starting another RF job.

### Assess, restore and close only the established scope

After each row, perform independent IQ analysis bound to packet, boot, job,
events, capture metadata and hashes. State the observed RF edges, thresholds,
clock/edge allowances and resulting cutoff bound. Existing engineering clock
allowances are not calibrated absolute timing. Firmware success flags or
worker acknowledgement alone cannot close an RF row. Record every failure
and stop; cleanup/restoration remains required even if acceptance fails.

On success, failure, cancellation or exhausted limits, verify receiver cleanup
and inactive output, reconcile only this packet's identified owner/job, retain
a fresh full backup, and restore B to the retained inhibited baseline. Verify
exact programmed image, all reserved bytes, saved profile/access/settings,
healthy storage, disabled scheduling and empty/unowned/inactive readback.
If safe restoration cannot be established, stop and report that blocker; never
claim restoration from a load command alone or flash over ambiguous output.
Keep captures, credentials, backups and generated firmware private and ignored.

Perform an adversarial review of authorization/accounting, fresh Ready/cue
ordering, image/identity binding, physical classification, reset reconnection,
launch/cutoff uncertainty, AP-interface proof, assessment barriers, worker
safety, settings preservation, cleanup and restoration. Fix actionable
findings, rerun affected checks and conduct another assessment. Remain open
where independent evidence is missing.

Only if both remaining rows pass and adversarial review closes actionable
findings may GP14 be enabled by default. Keep the standard image RF-inhibited,
acceptance controls off in ordinary builds and BOOTSEL runtime handling absent.
Run `bash scripts/check_host.sh`, `python3 scripts/validate_wtp_contract.py`,
affected helper tests, formatting checks, documented pinned inhibited/RF/
acceptance cross-builds and linked-image/resource checks. Do not deploy an
additional default-on image under this two-acquisition packet; any later
deployment needs separately named authority. Distinguish source default
enablement from physical acceptance of a newly built default image.

Update the RF review, original brief and roadmap only to the established
P12.7 scope. Keep exact flash erase/program coincidence and broader Phase 12
gates open. Do not reopen the closed nonqualifying disconnect test as a device
finding, claim Phase 12 complete or broaden into fleet/configuration work.
Commit only scoped reviewed changes and redacted evidence on `devel`, push,
independently verify remote parity, and report commits, checks, attempt/job
totals, accepted/open rows, B's actual restoration state and unrelated changes
left untouched. While the operator Ready is absent, stop at the prepared
checkpoint and report preparation rather than claiming physical acceptance.
