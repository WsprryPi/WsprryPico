# Phase 11.4 C2 completion execution prompt

Complete the remaining C2 work in `/Users/lbussy/GitHub/WsprryPico`: deploy the
reviewed browser safeguards and obtain an actual Chrome observation of a
production-owned Loaded job. Execute this prompt, perform adversarial review,
repair actionable findings, rerun affected checks and repeat the assessment.
Commit and push the scoped result to `origin/devel`; report actual outcomes and
remaining broader gates. Do not claim all of Phase 11.4 is closed.

## Starting identity and authority

- Start from clean Pico `devel` at `23ac5b1`. Read project instructions, README,
  CONTRACT, architecture, development checks, browser API, WTP, the joint 11.4
  matrix and `browser-production-coverage.md` before implementation.
- Prior grants authorize tests on this sole inhibited Pico, bounded USB/flash
  operations, Chrome access and bounded production-acceptance service pauses.
  The current request expressly includes completing the remaining deployment
  and observation work. Preserve those boundaries; no RF, GPIO, router, trust
  import or unrelated repository modification is included.
- Pico 2 W/RP2350 on wspr5: serial `0BF4B4AEC9FFB344`, full device ID
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, Console `-if00`, WTP `-if02` under
  `/dev/serial/by-id/usb-WsprryPi_WsprryPico_`. Do not open the adjacent GPSDO.
- Expected starting firmware is `f88fa71eef5e`; verify rather than assume it.
  Build and deploy only standard `WsprryPico`, engine
  `inhibited-standalone-simulator`. Record revision, source inputs, ELF/UF2 SHA-256,
  exact device/boot and public server certificate fingerprint. Preserve journals,
  power20, disabled schedules, time server, credentials and watermark.
- Use existing Chrome and distinct controller/browser credentials at certified
  `wsprrypico-0a60df.local:18443`, with unchanged TLS 1.3/mTLS/SAN/ALPN/HTTP
  authority and independent WTP identity checks. Fresh USB may supply the TCP IP;
  that does not qualify hostname resolution. Execute LAN probes outside the
  sandbox and distinguish OS denial from actual device failure.
- The existing isolated production executable on wspr5 is
  `/home/pi/wsprrypi-browser-coverage-20260909/src/build/bin/wsprrypi-browser-coverage`,
  source `923ab570fe53ef2ccca7d12e519c9dc36adf7e93`, SHA-256
  `993ad62def487e5f03d82a5a7a1f5f82b972b16bd36eaa5b0d9a8c13a7166323`.
  Verify source/binary identity before invoking. Preserve the installed application
  and configuration, and the independent WsprryPi working checkout.

## Execution

1. Save private evidence under a new owner-only ignored `build/phase11-4-c2/`.
   Record baseline USB INFO/HELLO/CAPS/STATUS, healthy storage, exact identity,
   explicit inactive/unowned output and disabled autonomous schedules.
2. Build the reviewed standard inhibited image using the existing pinned SDK,
   toolchain and approved certificate bundle. Run affected browser/API/actual-TLS
   checks sequentially where they share loopback ports; check image inhibition,
   stack/heap and journal layout. Stage under a new hash-specific filename on
   wspr5, verify the hash, flash only the identified serial, and prove a fresh
   normal boot with saved settings preserved. Retain any failed attempt.
3. Reload actual Chrome from the Pico and verify the served safeguards match the
   candidate. Check connected idle controls and separate bounded disconnected
   observations, without inventing unavailable/unknown fields on a live device.
   Local fixture and deterministic tests remain separately labelled.
4. Use the unchanged isolated production application for at most three finite
   inhibited QRSS E jobs, each no longer than 20 seconds, nominal 3,570,100 Hz,
   with fresh synchronized clocks within CAPS limits. Never use continuous tone.
5. For the missing Loaded observation, the existing host gdb may set one temporary
   breakpoint at `TransmissionController::execute_prepared`, after real CLAIM/
   LOAD and before ARM. Bound the stopped interval to at most 20 seconds, below
   the negotiated lease, and automatically resume even if browser observation
   fails. Do not change variables, return values, clock, protocol bytes or code.
   During that interval obtain Chrome's actual Loaded state, exact job/foreign
   owner and inactive output; verify foreign controls disabled. Independently
   correlate USB/HTTPS device/boot/job/owner. Record this as a deliberately paused
   production-client observation, not an unmodified timing measurement.
6. The paused job may miss its fixed ARM deadline. Do not shift its start or
   retry it. Verify the production client rejects late handoff and cleans up
   authoritatively. Run an independent unpaused finite job for normal
   Armed/Running/Complete observations and explicit inactive/unowned cleanup.
7. Any installed-service pause is limited to the bounded test run (at most four
   minutes). Check provider output disabled first. Use an independent finally
   path to stop only the isolated client/debugger, resume a stopped client before
   termination, restore the service and verify original installed binary/INI
   hashes. Never infer cleanup from process exit or socket closure.

## Review and closure

Challenge partial deployment, stale browser assets, wrong owner/device/boot,
synthetic data presented as hardware evidence, debugger timing effects, lease
expiry, late ARM, duplicate jobs, cancellation and cleanup failure. Verify unknown
output never enables submission/release, and failed reconciliation remains
unknown. Prefer existing tests; add behavioral tests only for discovered defects.
Keep real Chrome evidence distinct from fixture screenshots and read-only API
probes. Use bounded desktop/mobile visual passes if UI changes are needed.

Write a sanitized execution/review record with exact identities, original
failures, tests and cleanup. Update C2 and the browser-safeguard deployment limit
in the joint records, preserving earlier failed/unobserved attempts. Leave UTC,
DHCP/link faults, certificate cases, lost-reply/recovery cases, second-board,
watchdog/connectivity reliability, resource and RF gates open unless independently
proven within an explicitly expanded scope. Inspect the full staged diff, commit,
push without force and report repository/remote parity and actual device/service
state. Do not claim remote CI or broader hardware qualification.
