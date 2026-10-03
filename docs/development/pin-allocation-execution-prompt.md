# Pin allocation execution prompt

## Objective and isolation

Implement the selected Pico 2 W pin-assignment contract as a bounded pin
allocation feature. Preserve WTP/1, one JobService/ownership authority, the
inhibited standard image, and existing reset/stop/setup gestures. Keep Si5351
unavailable, as explicitly selected by the operator on 2026-10-03.

Use an isolated feature worktree/branch based on committed devel. Do not import
unrelated uncommitted Phase 12 work or change its checkout, build directories,
fixtures, evidence or hardware. If target access becomes necessary, use only
Pico A, with separate explicit RF authority for any RF activity. No target
access is needed to establish software allocation correctness.

## Review orientation

At baseline `1dab547e17cd01e0562bab5b6b2ee4d652fd7b3a`, standalone Config v1
is a closed 1,800-byte station/Wi-Fi/schedule schema persisted through CRC
journals. BrowserApi applies authentication, Host/Origin checks, ETag/If-Match
and Scheduler's idle gate. PIO RF uses a fixed GP2 output; GP14 is used by both
PIO/DMA button capture and the worker-side safety probe. IndicatorController
owns the onboard LED for Identify/SoftAP cues. Amp/LPF and Si5351 execution
adapters do not exist. Recent commits address quiet session expiry and
inhibited timing/controller-credit diagnostics.

## Required implementation

1. Add a portable resource model with the exact external GPIO set, distinct
   onboard LED resource and stable IDs for the 12 fixed I²C pairs. Require
   exactly one direct RF GPIO or one I²C pair. Validate pin ownership across RF,
   switch, amplifier, every LPF selector, indicator and both I²C lines. Reject
   reserved pins, duplicate selectors and all overlaps, including GP0.
2. Parse a bounded closed JSON plan. Reject duplicate/unknown keys, wrong types,
   negative/fractional/overflow numbers, unknown engines/pairs and array entries
   beyond the limit. Return structured conflict role/owner/pin information.
3. Keep hardware eligibility separate from implemented adapter support. Expose
   all contract choices and candidate validation through authenticated member
   management routes. Candidate validation must not mutate Store, revisions,
   RF state or GPIO. Do not add pin fields to WTP/1.
4. Persist supported assignments in the existing configuration journal. Read
   legacy configs with the selected defaults. Preserve canonical legacy output
   for default pins; serialize nondefault assignments explicitly. Validate
   Console, browser, Store save and boot reload consistently. Reject operational
   amplifier/LPF/I²C selections while their adapters remain unavailable.
5. Apply supported direct RF, active-low/pull-up button and indicator assignments
   together at boot. Preserve GP2/GP14 defaults. Both button capture and worker
   safety must use the same selected input; disabled input claims no GPIO/PIO.
   Protect RF admission when stored configuration is invalid. Never silently
   drive default RF after a failed stored-pin load.
6. A pin save requires idle, unowned, inactive, nonfaulted state and the browser
   revision gate. Latch RF admission inhibited until reboot after a pin change.
   Later station edits or restoring the original pins must not conceal that
   restart requirement. Report saved versus active pin plans separately.
7. Use one indicator controller for TX and provisioning cues. TX takes priority;
   preserve the existing Field-GATT pattern vocabulary. Support onboard default,
   external GPIO with polarity, and disabled selection. Initialize external
   outputs inactive before enabling their direction. Disabled means no GPIO
   allocation and no active indicator indication.
8. Extend the existing settings form with supported pin selectors and ownership
   lockouts; retain incumbent layout/identity and old-firmware compatibility.
   Show unavailable amp/LPF/Si5351 adapters honestly and list their future fixed
   pair choices without activating them. Preserve unsaved edits and revision
   behavior. Include restart messaging for pin changes.

## Validation and adversarial assessment

Use wspr5 for C++ host builds/tests. Do not retry the known-broken Mac native
compiler. Use the already pinned SDK/Arm compiler and prebuilt host helpers for
cross-link checks; do not incidentally rebuild a native helper or download tools.
Run JavaScript, Python and Git-history checks locally when they need existing
local dependencies/history. No hardware operation is implied by these checks.

Test every eligible/reserved GPIO, all pairs and both I²C lines, every role
collision, engine exclusivity, disabled resources, malformed JSON and late array
failures. Verify persistence/reload, invalid CRC-valid saved assignments, atomic
rejection, auth/revision gates, saved/active separation, restart latching and
post-save WTP admission denial. Test indicator priority and disabled state, and
browser lockouts including external GP0 and freed pins.

Run affected and broader host checks, standard inhibited and standalone RF
cross-links, linked-image gates, formatting and documentation links. Attribute
unrelated failures through an unchanged-baseline comparison rather than changing
historical acceptance to make this feature pass. Record commands and results.

Perform an adversarial source/behavior review, fix actionable findings, rerun
affected checks and reassess. Commit only this feature's files and push the
feature branch. Do not merge or claim production/RF qualification. Report the
remaining adapter/physical limits, actual repository state and remote parity.
