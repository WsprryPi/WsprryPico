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
limits the initial campaign to eight attempts, stops on failed evidence and
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
