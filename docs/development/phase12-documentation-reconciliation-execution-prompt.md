# Phase 12 documentation reconciliation execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Starting state and authority

Begin at `c889ffce5714cdc6bce3129572903a743240dcac`, which was equal to
`origin/devel` when this documentation tranche started. Inspect the branch,
working tree, HEAD, upstream and current remote-tracking reference before
editing and again before publication.

The working tree already contains an in-progress documentation reconciliation.
Treat those edits as input to review, not as disposable changes. Preserve their
intent, inspect every changed and untracked file, and integrate or correct them
without resetting, stashing, discarding or rewriting history.

This prompt authorizes documentation and documentation-index changes in this
repository, hardware-free read-only source inspection, relevant deterministic
tests, adversarial review, repairs, a documentation commit and a push to
`origin/devel`. It does not authorize firmware or client implementation changes,
dependency installation, target access, BLE/Wi-Fi operation, flashing, reboot,
credential use, trust-store mutation, RF output or changes to another
WsprryPi-family repository.

## Controlling evidence boundary

Keep the evidence hierarchy explicit:

- proposals and intended contracts are not implementations;
- source inspection and host tests are not target execution;
- native Raspberry Pi results are not iPhone/Bluefy results;
- an online Bluefy release is not an accepted offline cache;
- one retained-bond authorization is not fresh pairing/password acceptance;
- one phone-time exchange is not clock-accuracy or disagreement/recovery
  qualification;
- one Identify observation is not the complete LED timing/priority/fault matrix;
- Bluefy WTP `HELLO` plus read-only `STATUS` is not arbitrary job transfer,
  job control, coexistence or soak acceptance; and
- an RF-inhibited run is not RF output, conducted-RF or release qualification.

Phase 12 remains active and `OPEN_PARTIAL`. Stage B and all RF work remain
separate and unauthorized.

## Required reading and source cross-check

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/implementation-plan.md`, `docs/development/README.md`,
`docs/development/phase12-plan.md`,
`docs/development/phase12-field-access-contract.md`,
`docs/development/phase12-ble-local-control-review.md`,
`docs/development/phase12-pi-ble-tcp-review.md`,
`docs/development/phase12-physical-acceptance.md`,
`docs/development/phase12-production-acceptance-review.md`,
`docs/development/raspberry-pi-ble-client.md`, `docs/browser-api.md` and
`docs/protocol/WTP.md` before finalizing the documentation.

Cross-check the custom BLE wire description against the current implementation,
including at least:

- `src/provisioning/pico/field_access.gatt`;
- `src/provisioning/gatt_framing.*`;
- `src/provisioning/command.*`;
- `src/provisioning/ble_session.*`;
- `src/provisioning/manager.*` and `src/provisioning/profile.*`;
- `src/provisioning/local_access.*`;
- `src/provisioning/pico/gatt_transport.*`;
- `src/time/controller_time.*`;
- `src/provisioning/web/bluefy.js`; and
- `scripts/wsprrypico_ble.py`.

Do not make an implementation accident normative merely because it is present
in source. Where the selected contract and implementation disagree, document
the mismatch as an open Phase 12 gate unless this documentation-only tranche can
correct the prose without changing product behavior.

## Current accepted evidence to reconcile

Preserve the earlier failed attempts and their diagnostic value. Add the later
successful bounded evidence without rewriting history:

- target: Candidate A, Pico 2 W, full device ID
  `fd6127d11d6aca42a9905fa3fb1bf1d5`;
- phone/client: iPhone 17 Pro Max, iOS 27.0, Bluefy 3.9.3;
- final firmware identity: `4377d2ded8e3`;
- final UF2 SHA-256:
  `048c3feef2536b7e17c74edc153d4f25a4fa1980e4910566d7d7aaba677ef22a`;
- boot ID: `331e555683a5d6c6122735a07883e0a8`;
- verified online Bluefy release:
  `e1e6caa574a0e5c75cfd8c0a168c3ec8c2b896322ec7a7acc20d555f357f0625`;
- accepted phone subset: retained-bond authorization, one authenticated
  controller-time exchange, Identify LED plus field status, and Bluefy WTP
  `HELLO` plus read-only `STATUS`;
- WTP corroboration: 420 accepted bytes in seven writes and 675 delivered bytes
  in thirteen confirmed indications, with no queue, CCCD, request, indication
  or completion error; and
- final state after `Cancel`: disconnected, both CCCDs clear, no admission or
  pending output, carrier selector clear, access generation 3, healthy
  configuration/watermark journal sequences 72/12, preserved settings,
  RF-inhibited `empty`, unowned and output inactive.

Offline cache reuse, fresh-password/new-pairing behavior, profile provisioning
and activation, arbitrary BLE job control, the broad controller-time and LED
matrices, blank generic SoftAP HTTP, stable-station AP withdrawal, reset and
recovery controls, trust/fault/resource/coexistence/soak work and Stage B remain
open.

## Documentation deliverables

### 1. Authoritative roadmap and current position

Reconcile `docs/development/phase12-plan.md` as the authoritative roadmap:

- keep P12.1-P12.5 scoped acceptance unchanged;
- mark P12.6 partial, not closed;
- record the exact bounded native-Pi, SoftAP and iPhone/Bluefy evidence without
  conflating them;
- show Physical Stage A as partial and Stage B as not authorized/performed;
- add the Field-GATT documentation/conformance/freeze work as an explicit P12.6
  gate; and
- list the remaining completion gates in concrete, testable terms.

Update the top-level and development indexes so a reader can find the current
roadmap, evidence review, field policy, physical plan, Field-GATT contract and
Raspberry Pi client guide without following stale status prose.

### 2. Field-GATT protocol and super-user guide

Create `docs/protocol/Field-GATT.md` as a working Phase 12 protocol contract,
not yet a released compatibility promise. It must be independently usable by a
competent client author and must define or explicitly bound:

- safety, RF and one-`JobService` ownership boundaries;
- supported client roles and current unsupported operations;
- discovery, advertising-name limitations and full-device identity checking;
- Just Works bonding, enrollment, retained-bond and application-authorization
  behavior;
- service and characteristic UUIDs, properties, encryption/key-size rules,
  CCCDs, ATT MTU and write-mode constraints;
- byte-exact field framing, sequence/reset/reassembly rules and direction limits;
- closed JSON envelopes, identifier/integer rules, response families and replay;
- authorization, Identify, field status, controller time and Bluefy WTP-carrier
  operations;
- atomic profile schema, transaction, step-up, confirmation, apply, delivery and
  cancellation behavior;
- unchanged WTP/1 mapping for both dedicated and Bluefy carriers, flow control
  and close semantics;
- actual application and ATT failure behavior;
- troubleshooting and currently absent administrative operations; and
- implementation/evidence references and protocol-freeze criteria.

Keep two known conformance defects prominent rather than concealing them:

1. the native Raspberry Pi `provision` path omits the required fresh
   `profile_step_up` before `apply`; and
2. the manager's 64-fragment counter caps 64-byte writes at 4,096 bytes while
   the declared profile limit is 7,168 bytes.

Until repaired in a later implementation tranche, document native-Pi profile
application as unsupported and prohibit attempts above the effective 4,096-byte
command-path ceiling. Do not weaken the fresh-step-up security contract or
silently redefine the intended 7,168-byte boundary.

### 3. Historical-review preservation

Do not rewrite historical checkpoints to pretend later evidence existed at the
time. Where a historical review now reads as a current claim, add a concise
supersession note pointing to the current production review or current client
guide. In particular, preserve the then-current result of the BLE continuation
and Pi-client tranche while making clear that later phone evidence exists and
that the later fresh-step-up hardening superseded native-Pi profile-apply
support.

### 4. Consistency across maintained documents

Reconcile at least `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/implementation-plan.md`, `docs/development/README.md`, the Phase 12 field
contract, physical plan, production review and Raspberry Pi client guide.
Remove current-status contradictions while keeping exact evidence limits.

Use consistent language:

- USB CDC is canonical/reference;
- authenticated TLS 1.3/TCP is first-class WTP job transfer/control;
- BLE/Bluefy is primary local provisioning/management/control;
- SoftAP/Safari is an independent fallback;
- WTP remains device-neutral and unchanged over GATT;
- Phase 12 is active/`OPEN_PARTIAL`; and
- Phase 13 owns broad hardware, RF and release qualification.

## Validation

Run documentation-appropriate and affected contract checks without installing
new tools:

- `git diff --check`;
- a repository-local Markdown-link existence check for every changed Markdown
  file;
- `python3 tests/provisioning_contract_tests.py`;
- `python3 tests/raspberry_pi_ble_client_tests.py`;
- `node tests/provisioning_web_tests.js`;
- `python3 scripts/validate_wtp_contract.py`; and
- any focused existing CTest target needed to validate field framing/session
  claims if an already configured host build is available.

Test output proves only its own source/host boundary. Do not run hardware,
network-radio or RF tests for this documentation tranche.

## Mandatory adversarial review and repair loop

After the first documentation pass, review the complete diff as a hostile
maintainer and independent client author. At minimum challenge:

- stale current-status statements in indexes, architecture and plans;
- historical evidence rewritten as if it were contemporaneous;
- implementation behavior stated as a selected contract without qualification;
- client workflow that would fail against the current target;
- incorrect UUID, frame, size, timeout, replay, authorization, indication,
  controller-time, profile or WTP behavior;
- errors listed as wire-visible when the target actually maps or suppresses
  them;
- ambiguous retained-bond password behavior;
- conflation of exact phone evidence with offline, broad BLE or RF acceptance;
- links to absent documents and orphaned protocol records; and
- any wording that could lead an operator to expose credentials or enable RF.

Fix every actionable finding in scope, rerun the affected checks, then perform a
second adversarial assessment of the repaired complete diff. Repeat until no
actionable documentation issue remains. Record remaining implementation and
physical gates; do not call them documentation failures or claim Phase 12
closure.

## Commit, push and report

Before commit, recheck branch, status, diff, diff-check, validation results and
the exact files to stage. Commit only this reconciled documentation tranche on
`devel` with a concise message, push to `origin/devel`, and verify local HEAD,
upstream and the remote branch agree.

Report:

- the rendered prompt path;
- documents added or changed and their purpose;
- the exact Phase 12 position after reconciliation;
- first adversarial findings and repairs;
- second assessment result;
- checks and their actual outcomes;
- implementation and physical gates deliberately left open;
- commit ID; and
- push and remote-parity result.
