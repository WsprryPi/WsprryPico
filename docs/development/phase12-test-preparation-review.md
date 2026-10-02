# Phase 12 test preparation: execution and adversarial review

Status: **PREPARED / HARDWARE NOT EXECUTED / PHASE12 OPEN_PARTIAL**.
The [comprehensive prompt](phase12-test-preparation-prompt.md) was written and
executed on `devel`, starting at `945a1cd57b2e6ea43b22065e3d1fb41638675611`.
Source preparation is committed as `62fbe96df47d18e35c756c278e8cc087b47123e0`.
Later packet/manifest documentation and offline verifier repairs do not change
embedded firmware source identity.

## Implemented preparation

- INFO reports nonsensitive resource use: lwIP pools, TLS/allocator failures,
  stack/guards, bootstrap/GATT/TCP buffers, retained sessions, flash adapter
  operation attempts/failures/bytes, and five configured BTstack host API pools.
  Linker wrappers use bounded pointer ledgers and fail closed on ownership
  corruption. An offline linked-image checker rejects missing/bypassed wrappers
  and reports actual pinned SDK callers. Unused paths can validly remain zero.
  Controller-owned buffers, largest contiguous allocation and physical durability
  are explicitly outside these measurements.
- Ten isolated inhibited images interrupt real durable reset phases or actual
  profile-program pages once per watchdog marker; no remotely writable fault
  command. Reset host evidence reconstructs all seven phases at both levels.
  Cold power can rearm the marker. Stage8–10 entry requires no boot-triggered
  deferred TLS save; unexpected consumption stops the case.
- A separate inhibited session fixture selects 15 s inactivity/60 s absolute
  deadlines for the ordinary engineering admission policy. Defaults remain
  15 min/12 h. Tests cover absolute expiry despite activity, protected-owner
  status grace, blocked mutation, reclamation and invalid policies.
- Composition capture is opt-in INFO-only, identity/mode/health bound, private
  and finite. Expiring approval binds plan/source/image/console and the whole
  capture deadline; campaign and short USB locks prevent declared collisions.
  A cadence overrun stops before another device read. Capture was never run
  against hardware. Offline normalization verifies retained exact serial bytes,
  actual artifact hashes and raw INFO-derived metrics, then emits
  `RESOURCE_EVIDENCE_REVIEW_REQUIRED`; independent wire/phone/pressure credibility
  remains pending. Separate consumer/engineering templates reject placeholder IDs.
- The [manifest](phase12-test-preparation-candidates.json) binds fifteen clean
  candidate roles to ELF/UF2/map/identity/compile evidence. The offline verifier
  derives symbols/disassembly from ELF, compares UF2 load bytes and E10 layout,
  checks options/stage/linkage and refuses changed artifacts. The builder checks
  clean source/SDK/submodules and unchanged revisions before/after compilation.
  These are unsigned local build records, not cryptographic build provenance.
- The [proposed hardware packet](phase12-test-preparation-packet.md) names B-only
  prerequisites, fresh backup, second-phone and offline evidence, finite ordinary
  soaks, fourteen reset and three profile interruption cases, separate time/LED/
  engineering assertions, one remaining RF/AP acquisition/job and exact restoration.
  It grants no hardware authority. Exact in-pulse flash cuts, GP14 flash-edge
  coincidence and every applicable physical closure assertion remain explicit.

## Adversarial findings, repairs and reassessment

Independent reviewers examined different authors' changes. Actionable findings
were repaired and affected checks repeated:

| Finding | Repair and evidence |
| --- | --- |
| Profile stages8–10 hook lost during flash counter integration | Restored actual adapter hook after physical program/IRQ restore; linked disassembly checks call inside `PicoProfileMedia::program`. |
| Audit trusted normalized booleans/hash strings; carrier artifacts could overclaim completion | Verify confined files and hashes, exact raw serial bytes/decoded object/timestamps; derive resources/final cleanup. Keep independent coverage review pending rather than claiming physical completeness. |
| Real lwIP schema contained metadata/null pools; optional values treated as numeric pools | Validate statistics flag and explicit required numeric pools; retain optional unavailable values honestly. Real-schema and missing/null pool refusal tests. |
| BTstack private occupancy was unavailable | Observe five pinned public get/free API pairs through retained project wrappers; audit exclusive routing and report reachable callers. Controller buffers remain unmeasured. |
| Ordinary soak could accept accelerated session fixture | Require actual15 min/12 h INFO limits; accelerated fixture has separate identity and cases. |
| Observer lacked whole-run exclusion and approval binding | Hold declared campaign lock, retain short USB lock; require approved operation, exact source/image/plan/console and full-run expiry. Files alone do not grant human approval. |
| Delayed cadence and near-term approval expiry permitted further USB observation | Refuse >45 s gap before another read and require expiry covering duration+45 s; refusal regressions prove one read only after pause. |
| Source HEAD or dirty SDK could invalidate clean candidate claim | Check source/SDK revision and full source/SDK/submodule cleanliness before/after build; exact ELF identity and payload verifier. |
| Pressure instructions implied repetition and flash fixture substitution inside unchanged soak | Cases1–5 occur once within the window; case6 is associated prior fixture evidence, never same-composition serialization acceptance. A separate ordinary one-save concurrency case has its own finite operations, boot chain, overlap proof and restoration; acceptance remains pending. |

| Ordinary engineering pressure case incorrectly used consumer portal | Differentiate consumer encrypted profile save from authenticated engineering config PUT/operational journal, with exact selected-journal readback and unrelated records preserved. |
| Actual disassembly and compile database exceeded initial16 MiB limits | Retained all fifteen builds, increased bounded read-only tool output to64 MiB and compile database cap to32 MiB for the large linked images and repeated actual verification; no firmware code changed. |
| Time/LED categories lacked concrete stimuli/paths; wire error and RELEASE wording drifted | Added verified concrete case definitions, actual Field-GATT `conflict` mapping and supported WTP RELEASE cleanup; unsupported LED output-fault injection remains explicitly gated. |

Final independent source reassessment found no remaining actionable issue in
its reviewed fixture, telemetry, session, harness, manifest and clean-builder
scope. Exact final artifact verification and packet reassessment are recorded
below; this does not establish hardware behavior.

## Validation and exact candidates

- Final full retained-Mbed-TLS/lwIP host suite: **117/117 passed**, serially
  after firmware compilation (`build/phase12-prep-host-final-117.log`). Initial
  restricted-sandbox localhost checks failed; the approved localhost run passed
  116/116 before the new manifest registration. One later concurrent-build run
  timed out waiting for a Plain LAN HTTP rejection; its failure is retained in
  `build/phase12-prep-host-117.log`, and the final complete run passed without
  compilation. No timeout was relabeled a successful rejection.
- Focused ASan/UBSan field access, reset storage and pool metrics: **3/3 passed**.
  Final affected host checks: **7/7 passed**. New Python behavioral cases:
  candidate manifest9, composition audit8 and capture6; normal and optimized
  Python pass. BTstack bypass/missing-wrapper regressions also pass.
- WTP validator: **23 schema,7 raw JSON,1 framing,8 transition cases passed**.
  C++ formatting, Python compilation, whitespace and local documentation links
  pass. Six preserved documents match their starting hashes.
- **15 clean committed candidates built** using retained Pico SDK2.3.1 commit
  `079c6f39023649b154152db30f1d781e884879bc`, GNU Arm15.3.1 and picotool2.3.0;
  no dependency download or device operation. All per-image linked allocator,
  BTstack wrapper, stack guard, BOOTSEL/topology and relevant RF-worker checks
  passed. Actual manifests verify source/version, ELF↔UF2 payloads, reserved E10
  boundary, target options and fault stage/hook separation. Private per-role
  logs retain complete commands/results. Initial offline verifier caps were
  smaller than real24 MiB disassembly/17 MiB compile records; repaired caps and
  repeated actual verification pass. Firmware was not changed or reflashed.
- Exact candidate verification returns `VERIFIED_PREPARATION_ONLY`,15 candidates,
  `hardware_accessed=false`, `physical_acceptance=false`. Source is
  `62fbe96df47d18e35c756c278e8cc087b47123e0`; the later documentation/offline
  verifier commit must not be mistaken for the embedded firmware revision.
- Final independent reassessment of packet repairs, concrete time/LED cases,
  actual error/cleanup protocol mapping and verifier limits found no remaining
  actionable issue in the prepared scope. Missing LED adapter-error and in-pulse
  torn-write fixtures, exact GP14/flash coincidence and all physical rows remain
  explicitly open, with no invented fault command or acceptance waiver.
Private logs and firmware are under ignored `build/phase12-prep-*` and
`build/phase12-preparation-candidates`. No credentials, private backups or RF
captures were created or committed.

The six concurrent user documents remain byte-for-byte unchanged against
`build/phase12-prep-preserved.json` and are excluded from both commits:
README.md, CONTRACT.md, docs/architecture.md, docs/browser-api.md,
docs/pin-assignment-contract.md and docs/transmitter-application-contract.md.
No USB, SSH, fixture network, debugger, flash or RF operation was performed.
RF ledger remains16 acquisitions/11 jobs; the17/12 stopped packet is not authority.
