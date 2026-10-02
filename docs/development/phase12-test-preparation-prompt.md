# Phase 12 test preparation execution prompt

Work on `devel` in `/Users/lbussy/GitHub/WsprryPico`. Execute this preparation,
perform independent adversarial review, repair actionable findings and repeat
assessment, then commit and push scoped work with independently verified parity.
Prepare the tests; do not execute physical acceptance.

## Inputs and boundaries

Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md, development guide,
Phase12 closure matrix, product-decision review and current historical hardware
records. Preserve the six concurrent user files byte-for-byte. Other repositories
remain independent. No hardware/USB/debugger/SSH/fixture network control, flashing,
target erase/reset/fault injection, phone steps or RF is authorized. Existing
physical evidence remains scoped; do not repeat accepted rows or grant authority
from a successful build. GP14 default stays OFF. RF ledger remains16/11, historical
ceiling17/12; one remaining RF trial needs a new explicit packet and fresh Ready.
No tool/SDK downloads or installs. Keep captures, credentials, images and clean
build worktrees private/ignored. Never contact wspr4 or enroll Candidate A.

## Deliverables

1. Nonsensitive bounded resource telemetry: configured lwIP pools, heap and
   guarded stacks, TLS/server occupancy, GATT/bootstrap/access-session retention,
   flash operation/failure counters with exact semantics and explicit unavailable
   metrics. Do not call observed allocation size the maximum allocatable block;
   static BTstack capacity is not observed occupancy. Observers must not refresh
   leases, expire records, probe largest allocations or mutate store state.
2. Named compile-selected RF-inhibited fault candidates: durable reset checkpoints
   and actual journal/media write boundaries, one-shot finite stimulus and safe
   restart/resume. No arbitrary fault command in production firmware. Identify
   exact coverage and limitations. Prepare a separate accelerated engineering
   session deadline fixture for the12-hour boundary; keep ordinary15-minute/12-hour
   policy and WTP/time admission unchanged. Fixture symbols must be absent from
   standard and RF images; target fixtures cannot enable RF.
3. A finite composition/pressure/soak plan and hardware-free auditable evidence
   contract. Explicitly select consumer Plain LAN versus engineering TLS, bind
   board/source/image/boot/client identities, sample cadence, tolerances, cycle
   counts, expected rejections and final resource return. Provide an opt-in bounded
   INFO-only capture tool with refusal tests; never run it here. Require separate
   wire evidence for USB/BLE/LAN/HTTPS and pressure/phone actions. Do not promote
   telemetry, synthetic records or offline audit passes to physical acceptance.
   Separate two-hour ordinary soak from accelerated deadline evidence.
4. Build exact clean committed candidates using retained pinned SDK/toolchain and
   local picotool. Retain ELF/UF2/map hashes and selected build options; distinguish
   source revision from later documentation-only commits. Validate memory layout,
   inhibited engine and fixture/RF separation. Keep firmware private. Prepare a
   hash-bound machine-readable candidate manifest and offline checker, reject
   changed/missing images or contradictory variants.
5. Write one consolidated proposed hardware packet: B-only identity, fresh backup,
   exact candidates/hashes, named stage/case ordering, second-phone requirement,
   separately explicit destructive resets/network/credential/fault operations,
   noRF inhibited phases and separately bounded remaining RF/AP trial, operator
   Ready and stop rules, private evidence artifacts and exact restoration/readback.
   State all prerequisites and gaps honestly. The packet itself grants no authority.
   Provisional final GP14-default-on candidate cannot be claimed before RF acceptance.

## Validation and closure

Add meaningful deterministic failure/refusal tests for telemetry semantics,
fixture single-use/reboot state and absence from normal images, accelerated
expiry/grace/reclamation, capture authority/identity/bounds, audit missing/forged/
misclassified evidence and candidate hash binding. Run affected checks, full
host suite, meaningful sanitizers, contract/format/whitespace/link checks and
pinned inhibited/normalRF/fixture builds without target access. Review independently
for observer side effects, hidden hardware actions, false acceptance, stale
source/identity, partial cleanup and unsafe image options. Repair and reassess.
Commit scoped source when needed to create clean exact candidates, then commit
review/packet/manifest preparation and push all resulting scoped commits. Report
actual checks, hashes/paths, preserved repository state, any genuine limitation
and remaining physical gates; Phase12 remains OPEN_PARTIAL.
