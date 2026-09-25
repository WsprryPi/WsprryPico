# Phase 12 Field-GATT conformance and freeze execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Starting state and authority

Start from clean commit `805e022ec0e230d69fb158dc059f3ff8b84ee9c9`, which
matched `origin/devel` at preflight. Inspect the branch, working tree, HEAD and
upstream before editing and before publication. Preserve unrelated work if the
state changes; do not reset, stash or discard it.

This tranche authorizes the source, deterministic tests, protocol vectors and
documentation needed to finish and freeze the Field-GATT/1 source contract,
followed by adversarial review, repair, reassessment, a commit and a push to
`origin/devel`. It authorizes hardware-free host builds and an existing pinned
Pico cross-build. It does not authorize dependency installation, target access,
BLE or Wi-Fi radio operation, flashing, credential use, host trust mutation, RF
output or changes to another WsprryPi-family repository.

The freeze is a source/host conformance freeze. It is not physical iPhone,
Bluefy, Raspberry Pi, SoftAP, RF or Phase 12 acceptance. Phase 12 remains active
and `OPEN_PARTIAL` after this tranche.

## Required reading and controlling boundaries

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/development/README.md`, `docs/development/phase12-plan.md`,
`docs/development/phase12-field-access-contract.md`,
`docs/development/raspberry-pi-ble-client.md` and
`docs/protocol/Field-GATT.md` before implementation.

Preserve these product boundaries:

- USB CDC is canonical/reference WTP;
- authenticated TLS 1.3/TCP is first-class WTP job transfer/control;
- BLE/Bluefy is primary local provisioning/management/control;
- SoftAP/Safari is an independent fallback;
- WTP/1 remains unchanged and device-neutral over GATT;
- every job-control transport feeds the one `JobService`;
- RF timing remains local to RP2350; and
- no source or host result is physical or RF evidence.

## Required implementation

### 1. Repair native Raspberry Pi profile step-up

Make `scripts/wsprrypico_ble.py provision` conform to the same transaction used
by firmware and Bluefy:

1. authorize the field session;
2. open one profile session;
3. transfer the complete canonical profile in ordered fragments;
4. obtain a fresh current local password specifically for profile application;
5. create the future apply request ID before step-up;
6. send `profile_step_up` on the field session, binding the profile session,
   apply request, expected generation and fresh password;
7. validate both returned booleans;
8. when exact-device USB confirmation is required, show a nonsensitive console
   instruction and poll `profile_step_up_status` on a bounded cadence for no
   more than the selected 25-second confirmation window;
9. send `apply` with the exact request ID and profile session bound by step-up;
   and
10. retain best-effort cancellation and secret/profile scrubbing on every
    post-open failure.

Do not treat the retained-bond `authorize` password member as fresh proof. The
CLI must re-prompt before profile step-up. Do not log or return credentials.
Reject malformed step-up replies, including an impossible not-required/not-ready
combination. Keep all output machine-readable except the explicit confirmation
instruction on stderr.

### 2. Resolve the profile fragment ceiling

Keep the selected 7,168-byte profile limit and 1-through-64-byte decoded
fragment contract. Remove the accidental 64-fragment/4,096-byte ceiling.

The manager must admit every ordered nonempty fragmentation of a profile up to
7,168 bytes, including one-byte fragmentation, while remaining bounded by:

- the 7,168-byte staged-byte ceiling;
- the fact that every accepted fragment contains at least one byte;
- the existing 30-second no-progress timeout; and
- the fixed replay and session capacities.

Derive the maximum possible fragment count from the byte limit rather than
duplicating the client-preferred 64-byte fragment size. Test the 4,096,
4,097 and 7,168-byte boundaries and deterministic rejection beyond 7,168.

### 3. Close the remaining provisional-bond conformance defect

The selected field-access contract already requires timeout and abandoned
enrollment paths to erase provisional bonds. When an enrollment window expires
while a provisional BLE link remains open:

- erase the provisional target bond;
- invalidate the application session and queued logical authority;
- request closure of the physical BLE connection;
- fail closed if bond erasure cannot be confirmed; and
- leave retained authorized bonds unaffected.

Add portable policy tests and source/cross-link assertions for the target
disconnect request. Do not weaken the enrollment window or retained-bond rules.

## Frozen conformance artifact

Add a checked-in machine-readable Field-GATT/1 vector artifact under
`docs/protocol/`. It must define at least:

- protocol/version and frozen status;
- service and characteristic UUIDs;
- command/status/profile/fragment and timeout limits;
- the required profile-apply operation order and step-up bindings;
- accepted profile transfer boundaries and the first rejected byte count; and
- provisional-bond expiry behavior.

Make deterministic checks consume or validate this artifact against firmware
constants and operation vocabulary, Bluefy, the native-Pi client and the
normative documentation. Do not create a drift check that merely searches for
unrelated words; check exact values and required behaviors.

The browser and native-Pi behavioral fixtures must reject direct `apply`
without successful bound step-up. Both must cover confirmation-ready polling,
wrong-password/failure cleanup and the exact apply request binding. Firmware
tests must retain direct state-machine coverage.

## Documentation freeze

Update `docs/protocol/Field-GATT.md` from a working contract to the frozen
Field-GATT/1 source contract. State that incompatible wire changes require a
new protocol version. Link the vector artifact and remove the three repaired
conformance exceptions.

Reconcile the Raspberry Pi guide, roadmap, project contract, architecture,
implementation plan, development index and production review. Preserve
historical evidence as historical. Clearly separate:

- source/host conformance freeze achieved here;
- still-open physical provisioning and interoperability acceptance;
- still-open Bluefy offline reuse, broader job-control/time/LED/reset/fault/
  coexistence/soak work; and
- separately authorized Stage B/RF work.

Do not call Phase 12 closed and do not convert earlier RF-inhibited observations
into full provisioning, deployment or release evidence.

## Validation

Run without installing tools:

- formatting and syntax checks for changed Python, JavaScript, JSON, C/C++ and
  Markdown files;
- the native-Pi client, Bluefy, provisioning-contract and WTP contract tests;
- focused provisioning, field-access, network-transport and endpoint CTests;
- the full already-configured host test suite;
- the relevant already-configured sanitizer suite;
- an existing pinned Pico 2 W cross-build so target-only GATT changes compile;
- a local-link check for every changed Markdown file; and
- `git diff --check`, including the staged diff before commit.

Report exact outcomes and evidence boundaries. A cross-build is not target
execution.

## Mandatory adversarial review and repair loop

After the first implementation pass, inspect the complete diff as a hostile
protocol implementer and security reviewer. Challenge at least:

- accidental reuse of ordinary authorization as fresh step-up;
- apply ID, session, generation or staged-digest misbinding;
- confirmation polling that can outlive the profile session;
- passwords or profile material retained in logs, exceptions or fixtures;
- cancellation that accidentally runs after a successful commit;
- partial success at 4,097 or 7,168 bytes;
- a fragment-count bound that still depends on preferred 64-byte chunks;
- integer, timeout or replay exhaustion;
- provisional-bond expiry that erases storage but leaves live authority or a
  connected target link;
- retained-bond regression;
- vectors that validate only text presence rather than behavior;
- Bluefy/source copy drift;
- documentation claiming physical or Phase 12 closure; and
- target-only compile failures hidden by host tests.

Fix every actionable finding in scope, rerun affected checks, and perform a new
adversarial assessment of the repaired complete diff. Repeat until no actionable
finding remains. Record physical gates as open rather than treating them as
source defects.

## Commit, push and report

Before commit, recheck branch, status, complete diff, validation output and
exact staged paths. Commit only this Field-GATT freeze tranche on `devel`, push
to `origin/devel`, and independently verify local HEAD, upstream and the remote
branch agree.

Report the prompt path, implementation and documentation changes, review
findings and repairs, final reassessment, exact checks, remaining physical
gates, commit ID, push result and remote parity.
