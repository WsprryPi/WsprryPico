# Phase 12 offline saves and destructive recovery

Selected by the operator on 2026-10-02. Source implementation and acceptance
results are recorded in the associated execution review; target acceptance
remains open. The [execution prompt](phase12-product-decisions-execution-prompt.md)
defines the authorized software-only work.

## Station details without trustworthy time

Station settings may be saved without SNTP. Settings persistence and service
readiness are separate results. The page reports that settings are saved and
readiness is pending when trustworthy time or validated TLS is unavailable.
Existing certificates and authorized clients are preserved exactly; station
edits never silently rotate trust. A first offline save can contain a versioned
TLS-pending profile. Missing TLS may be created only after accepted trustworthy
time, while safe and idle, with a durable journal transition before activation.
Existing invalid or expired trust remains unactivated and requires explicit
engineering replacement. Browser time is not elevated to trusted certificate
time. Existing job/RF time admission is unchanged.

## Reset levels

Provisioning reset clears network credentials, consumer/TLS provisioning,
engineering access and BLE bonds. It preserves the effective saved station
values, schedules and no-repeat watermark. Station values held only in the
consumer profile must be durably copied before that profile is removed. A
station-only retained configuration does not grant scheduling authority.

Full erase additionally clears station settings, schedules and watermark.
Both operations preserve the reserved RP2350-E10 boot-workaround sector; E10 is
platform boot data, not an operator settings record. Existing GP14 gestures
continue to preserve settings and acquire no destructive behavior.

Each destructive operation requires idle/inactive shared JobService authority,
a durable intent and restart-safe completion. Interrupted reset must resume
before superseded credentials, scheduled work or fallback authority can run.
A failed storage step remains fail closed with its intent retained.

## Operator controls

Use separate recovery-page actions, two explicit confirmations and an exact
typed phrase: `reset provisioning` for provisioning reset, `erase` for full
erase. Each page explains its clearing/preservation consequences. No USB
confirmation is required. Requests are bounded and bound to the device, boot,
reset level and one-use challenge. Unknown delivery results do not cause an
automatic destructive resubmission.

The open setup AP does not authenticate the operator. These confirmations
prevent accidental deletion; anyone able to reach the recovery page may
complete them. This is the selected product behavior, not an authentication
claim.

## Acceptance boundary

Host tests, sanitizers and firmware linkage establish software evidence only.
No flashing, network reconfiguration, USB device access, target fault injection,
destructive target reset or RF is authorized by this document. Physical reset,
offline commissioning, interrupted recovery and resource evidence remain in
the [Phase 12 closure matrix](phase12-closure-matrix.md).
