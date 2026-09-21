# Phase 12.3 hardware-free platform integration execution prompt

Status: execution brief. This prompt is intentionally bounded to source,
deterministic host validation and target cross-build/layout evidence. It does
not authorize hardware, radios, service changes, host trust changes, physical
endpoints, certificate installation, RF, release publication or Phase 13 work.

## Objective

Continue Phase 12 from the reviewed P12.1/P12.2 portable baseline and implement
the hardware-free portion of P12.3 on `devel`: a separate Pico profile-flash
adapter and linked-image reservation, fail-closed boot selection of provisioned
Wi-Fi/TLS material, a runtime TLS credential source with Mbed TLS validation,
and a repository-owned Web Bluetooth client intended for Bluefy on iPhone.
Preserve every existing job, RF, storage, identity and browser-API authority.

Do not imply that this closes the BLE or SoftAP product. The user selected
Bluefy as the iPhone Web Bluetooth client, but did not select BLE proof of
possession/bonding/CA-rotation authority, SoftAP activation/WPA/recovery,
private-key-at-rest protection, factory reset semantics, page distribution or
desktop trust enrollment. Transport adapters that would turn proximity or AP
association into authorization must therefore remain disabled and open.

## Starting state and authority

1. Work only in `/Users/lbussy/GitHub/WsprryPico` on the existing `devel`
   checkout. Preserve all current Phase 12 changes. Do not reset, stash, switch
   branches, discard or rewrite history.
2. The reviewed base is
   `c3ecc303db9dbcf68214e20c9b93f6889851aa6b`, initially equal to the local
   `origin/devel` reference. Recheck branch, status, HEAD and upstream before
   editing and before publication.
3. This execution authorizes source/document/test changes, deterministic local
   builds, one attributable commit and a push to `origin/devel`. It does not
   authorize target access, flashing, USB device control, Wi-Fi/Bluetooth
   control, service/trust-store changes, host reconfiguration or physical RF.
4. Use only the repository's retained pinned dependencies and documented build
   commands. Do not install tools or substitute a newer SDK.

## Maintained inputs

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/implementation-plan.md`, `docs/development/README.md`,
`docs/development/phase12-plan.md`, `docs/development/phase12-review.md`,
`docs/development/phase12-physical-acceptance.md`,
`docs/development/network-control.md`, `docs/development/phase11-7-review.md`,
`docs/development/phase11-7-result.json`,
`docs/development/phase11-3-identity.md`, `docs/browser-api.md`,
`docs/protocol/WTP.md`, `docs/development/standalone.md` and
`docs/development/phase11-5-extended-job-design.md`. Prefer the current Phase
11 closure and completion matrix over historical then-open paragraphs.

Inspect the actual code and dependency seams before designing: the two existing
standalone journals, Pico flash mapping/linker override, `PicoNetwork`,
`PicoServer`, generated credentials, device identity, `JobService` activity,
browser mutation semantics, the portable provisioning core and the exact Pico
SDK 2.3.1 tree. Record missing pinned BTstack source as a build/input fact, not
as Bluetooth acceptance evidence.

## Frozen safety and compatibility rules

1. Provisioning is not a job-control protocol. It may replace Wi-Fi and the
   complete TLS bundle only. Station, schedules, no-repeat watermark, job
   ownership, RF authority, WTP/1 and browser semantics remain unchanged.
2. The existing standalone flash region remains byte-for-byte at its current
   address. Add a disjoint 16 KiB profile region below it and keep the final
   RP2350-E10 sector untouched. Every maintained linked image must reserve all
   three regions.
3. Profile selection is fail closed. No stored profile means the current
   build-time configuration remains available. Once a committed profile exists,
   corruption, schema/identity failure or credential failure must not revive
   build-time or older superseded trust.
4. A provisioned Wi-Fi overlay changes only SSID, password and time server in a
   runtime copy. It must never persist through or mutate the standalone config
   journal and must not change station, locator, power, schedules, expiry or
   watermark.
5. Runtime TLS owns stable views for the complete listener lifetime. Validate
   parse, key pair, chain, exact DNS SAN, server EKU, validity, actual device
   binding and the accepted P-256/SHA-256 algorithm profile before listening.
   Do not log or expose credential content.
6. Listener activation is gated by synchronized UTC and exact deployment
   identity. A bad committed runtime bundle disables network control rather
   than falling back to build-time trust. No live credential reload is claimed
   until an authenticated transport and an idle-only network restart path are
   implemented and physically accepted.
7. Bluefy is only a Web Bluetooth user agent. The checked-in client may build,
   validate and fragment the canonical profile, bind a request/session/device
   identity, cancel, time out and scrub displayed secrets. It must not fabricate
   adapter authorization. Until proof-of-possession policy exists, the target
   GATT service is not enabled and no end-to-end provisioning claim is made.
8. SoftAP remains an independent Safari fallback, but target AP/captive-portal
   code is not enabled until activation, WPA, recovery, timeout and
   post-success policy are selected.

## Implementation work

### A. Flash and boot integration

- Centralize the 4 MiB physical layout constants and static assertions.
- Add a `provisioning::Media` Pico adapter whose erase operation covers an
  entire 8 KiB profile slot and whose program/read bounds cannot reach either
  the existing 16 KiB journals or the E10 sector.
- Reduce linked FLASH length by exactly 16 KiB while leaving the old journal
  base unchanged. Add deterministic source/layout checks for non-overlap and
  every maintained image.
- Load `ProfileStore` separately at boot. Resolve either no-profile factory
  material, a valid provisioned profile, or a fail-closed fault. Keep owned
  profile buffers alive while Wi-Fi and TLS use them and scrub them on teardown.

### B. Runtime credential bridge

- Replace `PicoServer`'s direct compile-time credential reads with an explicit
  immutable credential view supplied by boot selection.
- Add an Mbed TLS validator implementing the portable `CredentialValidator`
  contract. Accept only the repository's P-256/SHA-256 server profile, verify
  keypair, issuing CA, exact hostname and server authentication purpose, and
  require the profile device ID to match the physical device identity.
- Start the listener only after UTC is synchronized; keep the existing TLS 1.3,
  mutual-authentication, connection limits, memory budget and RF/job admission
  behavior unchanged.
- Add nonsensitive source/generation/fault state to diagnostics only if it does
  not disclose SSID, password, certificate, key or CA material.

### C. Bluefy Web Bluetooth client

- Add a standalone repository-owned HTTPS page/client, not embedded as an
  already-authorized management page. Use fixed project UUIDs and a bounded
  request envelope that maps to portable open/write/apply/cancel operations.
- Validate the 32-lowercase-hex device ID, `.local` hostname, Wi-Fi fields,
  listener port, PEM boundaries and 7,168-byte canonical payload before asking
  for Bluetooth access. Fragment in order with explicit offsets and final flag.
- Do not log secrets, retain them in local storage or silently retry an apply.
  Scrub the form after success/cancel and expose precise, nonsensitive errors.
- Provide deterministic JavaScript tests with a mocked Web Bluetooth/GATT
  surface for unsupported browser, wrong device, malformed/oversize data,
  ordered fragmentation, duplicate/replay response, timeout, cancel and secret
  reclamation. Do not open a browser or contact Bluefy during validation.

### D. Documentation and evidence

- Update the Phase 12 plan/review, architecture, implementation roadmap,
  development baseline and physical acceptance plan to distinguish completed
  hardware-free P12.3 infrastructure from unimplemented transports and
  unexecuted physical acceptance.
- Assess Phase 11 evidence at assertion level. Runtime TLS/flash/linker changes
  invalidate reuse of current-image layout/resource/identity evidence for a
  future target candidate; historical Phase 11 results remain immutable.
- Record exact source identity, dependency identity, tests, cross-builds,
  layouts, review findings, repairs and remaining physical/security gates.

## Deterministic validation

Run the documented host configure/build/CTest suite, excluding only the
intentional immutable Phase 11.7 no-later-drift guard from the aggregate pass
and running it separately to record its expected failure. Run the focused
provisioning and Web Bluetooth tests, credential lifecycle checks, WTP contract
check, sanitizer build when supported and all maintained firmware link targets
with the retained SDK/toolchain. Inspect ELF/map size and the linker-script
reservation. A cross-build is build evidence only, never BLE, Wi-Fi, timing,
storage-wear, coexistence or RF evidence.

## Adversarial review loop

After implementation, review the complete diff as an attacker and failure
analyst. At minimum challenge flash boundary/erase math, downgrade/fallback,
wrong-device activation, invalid time, SAN/CN confusion, EKU/algorithm drift,
secret copies/status leakage, lifetime/dangling views, committed corruption,
station/schedule/watermark mutation, manager replay/concurrency, GATT response
spoofing, fragment ordering, timeout/cancel cleanup, Bluefy capability errors,
resource growth and preserved RF/job ownership. Repair every actionable finding,
rerun affected checks and perform a second adversarial assessment. Record both
passes and any consciously retained limitation.

## Completion and publication

Stage only the attributable Phase 12 changes. Check staged diff and whitespace,
commit once on `devel`, push to `origin/devel`, then verify local HEAD, local
`origin/devel` and the remote `refs/heads/devel` agree. Report:

- code-review orientation and the rendered prompt path;
- exact implemented and deliberately disabled behavior;
- tests, sanitizer, target cross-build and layout results;
- adversarial findings, repairs and reassessment;
