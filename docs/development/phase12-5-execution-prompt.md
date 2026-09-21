# Phase 12.5 hardware-free activation-safety execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Starting state and authority

Begin from the clean reviewed baseline
`2bc90b1fe59b7f2470ddda031fd666af76d91e87` (`Add Phase 12 provisioning
command contract`), equal to `origin/devel` at the start of this tranche. Inspect
the actual branch, status, HEAD and remote-tracking reference before editing and
preserve any later user work. Do not reset, stash, switch branches or discard
changes.

This prompt authorizes source, tests, documentation, hardware-free builds,
adversarial review, repair, commit and push to `origin/devel`. It does not
authorize flashing, USB/device access, BLE or Wi-Fi radio operation, SoftAP
creation, RF output, physical endpoints, trust-store/certificate installation,
host service or radio changes, dependency downloads, or publication outside the
requested Git push.

## Read and orient first

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/implementation-plan.md`, `docs/development/README.md`,
`docs/development/phase12-plan.md`, `docs/development/phase12-4-review.md`,
`docs/development/network-control.md`,
`docs/development/phase12-physical-acceptance.md`, `docs/browser-api.md`,
`docs/protocol/WTP.md` and `docs/development/standalone.md`. Review the current
provisioning manager/command/runtime/storage sources, Pico credential validator,
TLS server, Pico network lifecycle, flash layout, build graph and affected tests.
Prefer current Phase 11 closure records over historical open-work prose.

Record the exact retained SDK, Mbed TLS, lwIP, CYW43, BTstack and toolchain state.
Do not download or initialize missing submodules. The reviewed authoritative
project-local SDK is 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`; its BTstack revision is recorded as
`eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`, but that SDK's BTstack source is
absent. A second pre-existing cache contains a clean standalone checkout at the
recorded revision while its parent still reports the submodule uninitialized;
do not mistake that cache for a pinned adapter dependency or target evidence.

## Code-review findings that define this tranche

1. P12.4 invokes `ProfileActivator` synchronously after commit and before
   `CommandAdapter` can return the apply notification. A future disruptive
   network activation could therefore destroy its own BLE indication or SoftAP
   HTTPS response. Reuse the repository's existing principle that a destructive
   mutation is released only after the response reaches a terminal delivery
   boundary; a lost response must not leave superseded trust active forever.
2. `MbedTlsCredentialValidator` creates and globally frees PSA state. Calling it
   from `Manager::apply` while `PicoServer` owns live TLS would invalidate the
   listener. Give validator and server explicit shared PSA lifetime ownership so
   transient validation cannot free an active owner's crypto state.
3. `CredentialMaterial` contains borrowed views. Any deferred activation must
   own its staged profile and scrub superseded/staged secrets on every terminal
   path; it must not retain a callback's `Profile` references.
4. The Pico SDK's RP2350 BTstack flash-bank default is 8 KiB at
   `0x3fd000`-`0x3fefff`, which overlaps the existing standalone watermark
   banks. Reserve a disjoint project-owned 8 KiB bank before the Phase 12 profile
   journal, pin the future BTstack offset/size with compile-time definitions and
   tests, and reduce the linked application region accordingly. Do not move or
   reinterpret the existing profile, configuration, schedule, watermark or E10
   records.
5. `Manager` and `CommandAdapter` are present in the core archive but are not
   retained by current firmware ELFs. Add a dedicated target link-check that
   strongly references the P12.5 activation, manager and command boundary. A
   static-library build alone is not target link evidence.
6. Bluefy commands and status notifications can exceed a default 20-byte ATT
   value. Preserve the 512-byte command, 256-byte notification and 64-byte
   decoded-profile-fragment limits. Add drift evidence that target BLE integration
   must negotiate sufficient payloads or support bounded bidirectional
   framing/reassembly, and do not pretend atomic mock values establish ATT
   interoperability.

## Objective

Implement P12.5 as a deterministic, hardware-free, delivery-safe live-activation
boundary. It must advance the already selected credential replacement policy
without enabling BLE, SoftAP or a production runtime reload path.

### Deferred activation contract

- Committing a genuinely new profile stages one activation action and returns a
  complete nonsensitive apply reply before destructive platform work is released.
- Bind the pending action to the apply request and committed generation. Reject
  new provisioning sessions while activation is pending. Exact apply replay must
  not stage or execute twice.
- Expose one bounded terminal-delivery release operation for a future GATT
  indication-confirmation, SoftAP/TCP acknowledgement, disconnect or equivalent
  terminal callback. Reject stale, wrong-request and wrong-generation callbacks
  without mutation.
- A bounded timeout must release the committed action even if the response never
  reaches a terminal callback. The new committed generation is authoritative;
  response loss cannot preserve the old CA or Wi-Fi credentials indefinitely.
- Recheck job/RF activity immediately before the destructive step. Never abort,
  release or clear a job/fault and never infer inactive output. If activity is no
  longer idle, fail closed rather than restoring old trust.
- Model ordered quiesce, owned-runtime replacement and restart through a small
  platform interface with deterministic failure injection. The coordinator must
  own the staged profile, expose only nonsensitive state/fault/generation data,
  and scrub secrets after success, failure, timeout and destruction.
- Any quiesce/install/restart or late activity failure latches an activation
  fault, calls the platform fail-closed hook, leaves the committed generation
  authoritative and prevents implicit factory/superseded trust revival.
- Do not connect this boundary to a radio or claim actual Pico network reload.
  The target link-check proves compile/link retention only.

### PSA/TLS lifetime contract

- Add one core-0 serialized shared PSA lifetime owner used by both
  `PicoServer` and `MbedTlsCredentialValidator`.
- Initialize PSA on the first owner and free it only after the last owner has
  released it. Balance every failure, repeated start/stop and destructor path.
- Keep all Mbed TLS certificate/key contexts independently owned and freed.
  Sharing the PSA lifetime must not share TLS sessions or weaken validation.
- Add a real pinned-Mbed-TLS host regression that validates a candidate while a
  listener remains usable before and after validation, including invalid
  credentials and repeated start/stop/resource return.

### Flash and target-link contract

- Preserve profile journal `0x3f7000`-`0x3fafff`, standalone records
  `0x3fb000`-`0x3fefff` and E10 sector `0x3ff000`-`0x3fffff` byte-for-byte.
- Reserve BTstack storage at `0x3f5000`-`0x3f6fff`; linked application FLASH must
  end at `0x3f5000`. Define the SDK bank offset/total size from the project layout
  and add static/source/image checks proving no overlap.
- Update every maintained linker/image check. Do not rewrite historical Phase 11
  evidence files that describe their exact earlier images.
- Add a `provisioning_pico_linkcheck` (or equivalently explicit target) that
  retains and links the manager, command adapter, activation coordinator and Pico
  credential-validation/shared-PSA boundary using only existing pinned sources.

## Deterministic acceptance

Cover at least:

- successful commit -> reply-pending -> correct terminal release -> exactly one
  ordered quiesce/install/restart;
- lost reply/disconnect and timeout release; no indefinite old-trust state;
- duplicate/replayed apply, duplicate release, stale request/generation release,
  new open while pending and concurrent pending attempts;
- activity becoming owned, armed, running, failed, output-active or
  output-unknown after commit but before release, with no abort/release side
  effect;
- prepare/quiesce/install/restart/fail-closed failures and repeated fail-closed
  calls, preserving the committed generation and latching nonsensitive fault;
- secret-free replies/status/replay state plus staged and superseded secret
  scrubbing/reclamation;
- unchanged station, schedules and watermark through success and every failure;
- shared PSA nested ownership, invalid validation, server start failure,
  repeated server start/stop and zero retained TLS allocation;
- BTstack/profile/standalone/E10 disjointness, UF2 rejection at the new
  application boundary and fixed future bank definitions;
- Bluefy/C++ command and notification limits plus explicit non-atomic,
  bidirectional framing/reassembly target requirement;
- strong Arm link retention and unchanged WTP/browser/job ownership semantics.

## Validation and review

Use only existing pinned dependencies and documented commands. Run a clean host
configure/build and full affected CTest suite, the immutable Phase 11.7 guard
separately with its expected current-source drift, focused ASan/UBSan checks,
`scripts/validate_wtp_contract.py`, and all maintained firmware/link-check targets.
Inspect maps, UF2/layout, sizes, provisioning symbols and RAM/flash impact. A
cross-build is not BLE, Wi-Fi, timing, RF or physical evidence.

Perform an adversarial review after implementation. Inspect authorization and
activity races, response-loss semantics, replay, timeout arithmetic, lifetime
balance, dangling views, secret copies, allocation/failure cleanup, layout
overlap and dead-code link evidence. Repair every actionable finding, rerun the
affected checks and perform a fresh adversarial reassessment.

Create `docs/development/phase12-5-review.md` with source/dependency identity,
implemented and absent behavior, exact validation, findings/repairs, Phase 11
assertion impact, open decisions and remaining physical gates. Update maintained
status documents without claiming BLE/SoftAP/live-device acceptance.

## Explicitly out of scope

Do not select BLE proof of possession, bonding/recovery/CA-rotation authority,
BLE management permissions, SoftAP trigger/timeout/SSID/WPA/disable policy,
Bluefy origin/integrity/cache policy or accepted versions, CA/private-key
generation/storage policy, reset/bond-erasure semantics, desktop trust UX or a
BTstack acquisition rule. Do not add GATT, SoftAP/captive DHCP/DNS/HTTPS or
hardware operations. Record these as remaining decisions.

Finish by committing the reviewed finite tranche to `devel`, pushing
`origin/devel`, independently verifying remote parity and reporting changes,
validation, adversarial findings/repairs, limitations, remaining gates and the
exact clean repository state.
