# Implementation acceptance record

This record preserves completed implementation and its source-bound acceptance.
The sole current work list is [Consolidated backlog](development/consolidated-backlog.md).

## Accepted implementation history


1. **Complete:** architecture and protocol boundaries.
2. **Complete:** WTP/1 contract and validation fixtures.
3. **Complete:** portable job service and RF lifecycle.
4. **Complete:** Pico 2 W firmware foundation.
5. **Complete:** dual USB CDC transport.
6. **Complete:** strict USB WTP endpoint.
7. **Complete:** RF feasibility study and PIO/DMA selection.
8. **Complete:** physical RF engine and UTC-scheduled WTP integration, including
   GP2 output, encoded WSPR, comparative spectrum work, USB UTC synchronization,
   scheduled local execution, conducted SDR capture and independent decoding.
9. **Complete:** persistent station/schedules, device SNTP, retained watermark,
   Wi-Fi loss/reconnection and recovery controls, plus recurring standalone RF
   frames independently decoded after a wall-power boot without a USB host.
   This is bounded functional acceptance; later RF/reliability acceptance is
   recorded in the [Phase 14 closeout](development/phase14-closeout-ledger.md).
10. **Complete:** WsprryPi client/backend integration, published operator manual,
    installed Linux release and bounded joint USB/conducted acceptance. Repaired
    physical timing, streaming, clock-refresh and launch-status findings were
    regression-tested and reassessed. Final source a3ec67d passed Tone, QRSS,
    FSKCW, DFCW and three consecutive independently decoded WSPR frames at the
    recorded 135500 Hz conducted setup. Final inhibited clock-loss, cancellation
    and USB reconciliation checks passed; inhibited firmware and original host
    services are restored. This is functional integration acceptance, with
    later conducted qualification recorded in Phase 14. See the
    [target review](development/phase10-target-review.md) and
    [host acceptance guide](development/phase10-host-acceptance.md).
11. **Complete within documented scope:** optional mutually authenticated
    TLS WTP/TCP, browser API v1, embedded UI, network management and local
    certificate lifecycle. Host tests and firmware cross-linking are recorded in
    the [Phase 11 review](development/phase11-review.md). WsprryPi 11.1 host
    software is implemented independently. [11.2 concurrent management](development/phase11-2-review.md)
    supplies software isolation and instrumentation, with later bounded physical
    applicability recorded by 11.5/11.6 rather than an unrestricted timing claim.
    [11.3 DHCP/mDNS/hostname certificates](development/phase11-3-plan.md) is closed
    within its joint software/integration scope. [11.4 inhibited physical acceptance](development/phase11-4-plan.md)
    is closed within its bounded matrix, including the reviewed eight-hour soak.
    [11.5 target resource/contention acceptance](development/phase11-5-plan.md)
    is closed 6/6 for 138 MHz/divider 1. 11.6 is `CLOSED_SCOPED` at exactly
    13 accepted conducted rows, with no WSPR row accepted and all failures,
    blocked/untested work and 4 m/2 m configuration boundaries retained. The
    [11.7 joint review](development/phase11-7-review.md) reconciles current source,
    evidence applicability, regressions and documentation and closes Phase 11
    within those boundaries.
    The [selected QRSS-group limits](#planned-qrss-group-message-and-duration-limits)
    are implemented; affected 11.5 resource and extended-job physical acceptance
    are complete for the recorded 138 MHz/divider-1 configuration before 11.6
    acceptance of those jobs. Package 9 completed the R6 workload but failed its
    1,024-byte matched resource-return gate. Package 11 preserved that failure,
    qualified a separate two-host fixture and repaired the clock-poll,
    credential-owner, retained-terminal/memory and event-reducer harness paths
    exposed by four stopped attempts. Retry 4 then completed the exact fresh
    campaign. Its five matched windows pass the unchanged limit with a 520-byte
    post-N span and no monotonic growth; heap, stack, timing, fault, capture and
    restoration gates also pass. The independent
    [result](development/phase11-5-package11-retry4-result.json) and
    [review](development/phase11-5-package11-retry4-review.md) close R6 and
    Phase 11.5 at 6/6 families for that configuration.
    An alternative clock selected during 11.6 must repeat affected 11.5 checks.
    The systematic band x mode x clock comparison, supported configurations,
    unfiltered spectra and reproducible artifact are recorded in the closed
    Phase 14 scope. Filter development/application is the operator's responsibility.
12. **Closed within selected scope:** Phase 12 provisioning/local control and consumer commissioning.
    The [Phase 12 plan](development/phase12-plan.md), operator-selected
    [field contract](development/phase12-field-access-contract.md) and
    [production review](development/phase12-production-acceptance-review.md)
    define the current boundary. The frozen
    [Field-GATT/1 contract](protocol/Field-GATT.md) and
    [conformance vectors](protocol/Field-GATT-v1-vectors.json) bind the custom
    BLE wire surface across firmware, Bluefy, the native-Pi client and host
    tests. Bounded profile activation and the later
    [automatic closeout](development/phase12-orchestratable-closeout-results.md)
    are accepted within their recorded scopes. All four declared automatic
    workstreams are complete. The operator accepted the final frozen scope
    dispositions on 2026-10-06; the phase is **CLOSED_SCOPED**. Broader
    interoperability is outside that acceptance. Later conducted RF/release
    acceptance is recorded separately in Phase 14.

    P12.1/P12.2 provide the portable profile journal and provisioning state
    machine. P12.4/P12.5 provide strict command decoding, delivery-safe
    activation coordination and shared PSA ownership. P12.6 enables the
    provisioning-only GATT service, network-only activator and indicator in the
    standard RF-inhibited image and builds an integrity-inventoried offline
    Bluefy release. Candidate adoption, preserved operational state and BLE
    advertising have partial physical evidence. The subsequent
    [BLE local-control continuation](development/phase12-ble-local-control-review.md)
    production-connects controller time, Identify/status and a separate
    unchanged WTP/1 stream to the same authorized GATT session and one
    `JobService`. Its clean committed standard image has verified Candidate A
    load/boot, preserved state and final RF-inhibited restoration. Later bounded
    iPhone 17 Pro Max/iOS 27.0/Bluefy 3.9.3 evidence accepts retained-bond
    authorization, one controller-time exchange, Identify LED/field status and
    WTP `HELLO` plus read-only `STATUS`. The native-Pi BLE subset and provisioned
    SoftAP control subset have separate bounded Candidate A evidence.

    The separate blank-device Wi-Fi-only encrypted SoftAP transaction is
    implemented at `fb091f8`; its RF-inhibited Candidate A open-AP preflight
    and selected-iPhone network-only generation-one reboot readback passed;
    final phone-page and AP-return rows were open at that checkpoint in the
    [target record](development/phase12-wifi-only-physical-result.md).
    The 2026-09-27 Safari/SoftAP selection and
    [P12.7 physical-owner decision](development/phase12-7-decision.md) are
    historical. The [revised open setup contract](development/phase12-safari-open-setup-revision.md)
    selects Wi-Fi first and optional station details without a retained phone
    owner or button ceremony. P12.9 is closed under its selected manual
    fixed-address portal gate; final consumer acceptance is in the current
    matrix. The earlier
    BLE/Bluefy evidence remains bounded engineering evidence. The later
    automatic closeout accepts credential-journal recovery, reset/old-peer
    refusal, engineering carrier/API composition, the two-hour resource capture
    and consumer Save/STATUS overlap. The later selected commissioning, LED,
    physical-cut and member results are retained in the
    [current matrix](development/phase12-closure-matrix.md), together with the
    operator's explicit timing/peer/fleet exclusions. Final RF accounting is
    19 acquisition attempts/13 charged jobs. G7 retains a measured cutoff and
    later same-boot usable portal; strict 50 ms/90 s assertions remain unqualified
    and GP14 production default enablement is deferred. Stage B and Phases 13
    and 14 remain separate; this closeout starts no new feature work.

13. **LED complete:** P13.1 transmit LED addressability and external TX-only
    operation are accepted. The former P13.3 manual bias-enable request was
    withdrawn on 2026-10-17.
14. **Closed within declared scope — 9/9 workstreams (100%)**, 2026-10-14.
    The [closeout ledger](development/phase14-closeout-ledger.md) supersedes older
    active/pending descriptions in the [qualification plan](development/phase14-plan.md)
    and [result record](development/phase14-results.md). Accepted conducted scope
    covers PIO/DMA GP2 on both Picos, Tone/WSPR/QRSS/FSKCW/DFCW and 13 retained
    bands, with recorded 132/138/150 MHz comparisons. The selected reproducible
    release artifact is C96/138 MHz. Timing/frequency, unfiltered spectra,
    lifecycle/reliability and consumer settings/smoke results retain their exact
    source/image applicability and measurement limits. Code/evidence commit
    `74c73d5` and final closeout commit `e501c0d` were pushed with independent
    remote parity verification. The [band/mode catalog](development/phase14-band-mode-qualification.md)
    records 4 m as Unqualified under the all-mode gate and native direct 2 m
    as Unavailable; 8 m/5 m were outside that historical matrix. Their later
    [P15.13 point-scoped qualification](development/phase15-13-results.md) is separate.
    Filtering, calibrated power/absolute RF timing,
    consumer-image long endurance and documented security limits remain outside
    acceptance. These are retained scope limits, not unfinished workstreams.
15. **Accepted implementation:** P15.1–P15.16 are complete within their
    recorded scopes. Their evidence is retained below. Current work is selected
    only in [Consolidated backlog](development/consolidated-backlog.md).

## Selected consumer LAN access slice

Selected 2026-10-14 after Phase 14 closure. The
[implementation/acceptance plan](development/consumer-lan-access-plan.md) and
[consumer contract](development/consumer-lan-access.md) cover normal LAN
IP/hostname browser access, authenticated radio and transactional setup,
temporary button AP, automatic unavailable-network fallback/recovery, default
configured-button delivery and preserved local RF/ownership authority.
Implementation, bounded target acceptance and final review are complete; see
the [acceptance record](development/consumer-lan-access.md#acceptance-record--2026-10-14). This is separate
from closed Phase 14 and LED work; it selects no Si5351, amplifier, filter or
new-band implementation.

## Phase 13 acceptance

P13.1 transmit LED work is complete (`CLOSED_SCOPED`), including the checked
launch handshake, LED addressability, external TX-only operation, fourteen
accepted target cases and verified restoration. See the
[LED requirements and acceptance](development/transmit-led-requirements.md)
and [final review](development/phase13-1-step4-review.md).
The manual bias-enable request was withdrawn on 2026-10-17. Existing button
operation is recorded in the [Phase 12 closeout](development/phase12-closure-matrix.md).

## Phase 15 acceptance record

P15.1–P15.16 are complete. Historical item numbers, executed prompts, exact
source identities, observations and acceptance limits retain their meanings.
Current work and the remaining saved execution prompts are selected only in
[Consolidated backlog](development/consolidated-backlog.md).

- ✅ **P15.1 — Preserve Pico configuration across legacy and partial updates.**
  Track [WsprryPi #447](https://github.com/WsprryPi/WsprryPi/issues/447):
  Pico-owned preservation of unchanged configuration, explicit resets,
  validation and persistence. Established update semantics, capabilities,
  revision/conflict handling and profile-owned field boundaries for later
  settings work, with legacy PUT protection independent of new partial-edit
  support. The [configuration-update contract](development/configuration-updates.md)
  and [review record](development/issue447-review.md) deliver the Pico-owned
  implementation, merged at
  [`87144d1`](https://github.com/WsprryPi/WsprryPico/commit/87144d1364f36d04bfe0a714bd1c2f6deb974302).
  Paired Pi adoption and supported-version evidence are accepted under P15.2;
  #447 is closed. Status: complete within the recorded software scope.
- ✅ **P15.2 — Use compatible Pico configuration updates and verify supported
  version pairs.** Track
  [WsprryPi #448](https://github.com/WsprryPi/WsprryPi/issues/448): Pi
  client/adapter/UI changes, safe fallback and interoperability coverage.
  Uses the P15.1 / #447 contract and Pico implementation. Pi implementation is
  merged at
  [`6a39398`](https://github.com/WsprryPi/WsprryPi/commit/6a39398bb23d69ba0628e1b82171717040115ec8).
  All four supported source-pair rows passed actual Pi-generated requests
  through the adapters and Pico handlers with authoritative journal reload;
  focused regressions, sanitizers and UI checks passed, and final CI passed
  seven jobs. The [paired review record](https://github.com/WsprryPi/WsprryPi/blob/6a39398bb23d69ba0628e1b82171717040115ec8/docs/development/issue448-review.md)
  retains exact source pairs, adversarial repairs and validation limits.
  The operator-documentation gate is accepted as complete for this roadmap
  by the operator on 2026-10-15. Status: complete. This acceptance does not
  establish firmware, physical/RF or installed-service qualification.
- ✅ **P15.3 — Define and implement supported management carriers.** Publish
  a per-profile/per-carrier matrix separating WTP job control from JSON
  configuration management. Review engineering HTTPS, consumer station/AP
  [Consumer-Radio/1](protocol/Consumer-Radio-v1.md) and USB availability against
  the [browser API](browser-api.md); select the required Pi-to-Pico management
  paths and implement their supported adapters. Decide explicitly whether USB
  JSON management is needed; a working WTP carrier must not imply management
  support. Advertise actual management capabilities and reject unsupported
  paths without automatic fallback or an authentication downgrade. Preserve profile
  authority, device/boot identity, revisions, credential redaction and the one
  JobService/configuration authority. Use P15.1/P15.2 compatibility rules and
  verify authorized access, refusal, busy state and uncertain writes across
  the selected profiles/carriers. Keep resource/session budgets bounded and
  document access-policy and security limits. Status: complete within the
  [recorded software acceptance](development/phase15-3-management-carriers.md).
  Station mTLS is preserved; explicit Consumer-Radio/1 station/AP Pi clients and
  versioned discovery are implemented. USB JSON was unsupported at that
  closure; P15.14 adds the separately versioned USB adapter. Required
  paired/compatibility, sanitizer, UI and CI checks passed after independent
  review and repair. Physical, installed-service and unrestricted security
  qualification remain outside this closure; final operator documentation is
  P15.20.
- ✅ **P15.4 — Adopt shared application, station and hardware resources.**
  Pi now consumes the existing application, station, hardware and pin resources
  through protected member routes, its runtime coordinator and P15.3 engineering
  mTLS/consumer station/AP management. Explicit complete station/hardware saves
  and nonpersistent pin validation preserve target, profile and revision
  authority, saved versus active/null state, restart inhibition, STOP and cursors.
  Consumer setup-owned station fields and unavailable adapters remain explicit.
  Existing Pico schemas and the closed P15.3 discovery contract are unchanged.
  All five source-pair rows, actual carrier/journal checks, runtime, sanitizers,
  desktop/mobile light/dark UI and nine pushed-head CI jobs passed after
  independent review and repair. Status: complete within the
  [recorded software acceptance](development/phase15-4-shared-resources.md).
  Physical, installed-service and unrestricted security qualification remain
  separate; operator documentation is P15.20. No later roadmap work is included.
- ✅ **P15.5 — Add multi-threaded web service.** Support concurrent web
  requests from the operator's phone and Mac without one client's connection
  blocking or locking out the other. Coordinate with P15.6 so both clients can
  remain authenticated and usable simultaneously. Define bounded thread/task
  resources and synchronization while preserving local RF timing and shared
  transmitter ownership. Retain serialized configuration commits and revision
  checks from P15.1. Validate overlapping requests and slow or disconnected
  clients. Delivered two bounded cooperative port-80 tasks on core 0 with
  isolated transaction/delivery state; application commits remain serialized
  and RF servicing stays on core 1. Status: complete within the
  [recorded software acceptance](development/phase15-5-concurrent-web-service.md)
  after adversarial repair, 189/189 host groups, affected sanitizers and both
  RP2350 cross-links. The operator accepted later ad hoc phone/Mac contention
  testing on 2026-10-17; no further physical campaign is queued. Simultaneous
  authenticated sessions are covered by P15.6. See the
  [executed prompt](development/phase15-5-execution-prompt.md). Published
  implementation: `9cf5ba2`; acceptance/checklist closure: `62b33d9`.
- ✅ **P15.6 — Support multiple simultaneous login sessions (software scope).**
  Three independent consumer sessions support phone, Mac and native Pi, with at
  most one pending login among those three. Logout, expiry, context invalidation,
  keys and delivery completion are isolated; one scheduler, transmitter owner
  and configuration authority remain. Management/2 advertises exact limits;
  updated Pi also retains frozen management/1 support. Genuine crypto/HTTP,
  mixed native/browser contexts, conflicting settings, quota/expiry/failure,
  historical source pairs, sanitizer, cross-link and scoped UI checks are in the
  [acceptance and review record](development/phase15-6-sessions.md). On
  2026-10-17 the operator reported ad hoc phone/Mac, recovery and resource
  testing complete and accepted it without another qualification campaign.
  This records operator acceptance while preserving the original measurements.
  The [executed prompt](development/phase15-6-execution-prompt.md) and the
  [completed separate post-execution review](development/phase15-6-sessions.md#separate-post-execution-review)
  retain distinct evidence boundaries.
- ✅ **P15.7 — Recover login cleanly after a failed save or lost session (software scope).**
  After the callsign-only save was blocked, the operator could no longer log in
  to Pico B and saw "Radio request rejected. Status remains unknown." A live
  check against the earlier single-session firmware returned HTTP 409
  `radio_session_busy`; that firmware retained its session until logout or
  expiry, while the browser hid the specific rejection. P15.6 now provides
  three sessions; P15.7 adds fresh password-authenticated retirement at full
  capacity, without a device restart or ordinary idle expiry. One fixed
  five-second proof workspace retires only an explicitly selected login; it
  creates no replacement and never repeats a save. Both Pico and Pi preserve
  drafts and require fresh saved-state readback and review before a new save.
  The precise original physical failed-save-to-session-loss sequence is not
  claimed reproduced and is no longer a separate release task. The implementation
  builds on P15.6's genuine software
  refusal/lost-reply cases and the delivered multi-session service.
  A settings-preserving restart of B restored encrypted login and private
  status access; the verification session was logged out afterward.
  Status: complete within the [recorded software acceptance](development/phase15-7-recovery.md).
  The [execution handoff](development/phase15-7-execution-prompt.md) preserves the
  authorized scope. Exact source pairs, genuine crypto/bootstrap tests,
  independent review repairs, all seven compatibility rows, firmware links,
  sanitizers and browser evidence are recorded there. The operator accepted
  later ad hoc phone/Mac/recovery/resource testing on 2026-10-17; no additional
  target or consumer-grade qualification campaign is queued.
- ✅ **P15.8 — Add WSPR Type 2/3 to WsprryPico.** Automatic Type 1/2/3 planning,
  adjacent-window Type 2/3 pairs, versioned resources and browser/commissioning
  support are delivered. Ordinary calls retain saved-six/on-air-four Type 1
  behavior. `/00`–`/09` remain supported with ambiguity warnings; paired Type 3
  hashes the requested full callsign. Overall status: complete within the
  documented software scope. The operator confirmed WsprryPi integration and
  acceptance under its release checklist step 14 on 2026-10-16.
  The Pico implementation is complete within the
  [recorded software acceptance](development/phase15-8-wspr-type23.md), accepted
  for scoped software closure by the operator on 2026-10-16. P15.8's published
  Pico head is `4e96f0e`; its tested implementation pin is `804e8a0`. The originally
  accepted Pi companion was `6d5e734` on `codex/p15-8-wspr-type23`, before the
  subsequently accepted Pi integration. Recorded validation
  passed 196 host tests, 27 sanitizer-build checks, both firmware links and all
  12 companion CI jobs after executor adversarial review and repairs. Official
  wsprd-code payload/symbol/hash/receiver compatibility is recorded. The separately
  requested originating review note is handled with the selected short
  one-frequency, one-Pico Type 2/3 decode follow-up and its evidence closeout.
  Earlier software evidence is not relabeled as captured-RF decoding.
  The
  [execution handoff](development/phase15-8-execution-prompt.md) retains its
  historical baseline and release-coordination boundary. Related Pi integration
  is closed under WsprryPi release checklist step 14 by operator acceptance.
- ✅ **P15.9 — Save valid fields independently of transmit readiness.** The
  operator wanted to update a callsign without completing unrelated station or
  message controls. The genuine-page software reproduction found native required
  locator validation blocking the station form; QRSS controls were separate.
  This does not diagnose the original physical incident.
  Allow valid editable fields to be saved without completing unrelated station
  or message inputs. Validate submitted fields and their relevant dependencies;
  preserve unchanged saved values and leave invalid entries unsaved with clear
  feedback. Explicitly identify what was saved and what still needs attention.
  Preserve incomplete work as distinct saved draft state where the existing
  runnable configuration cannot represent it safely; do not invent placeholder
  values or weaken execution validation to permit saving progress.

  Show saved state separately from readiness for the selected transmission mode,
  for example, "Callsign saved; not ready to transmit: locator missing." Saving
  fields must not itself grant transmit authorization or create, queue or arm
  a message job. Keep explicit enable/start controls and existing runtime guards;
  enforce completeness and validity before execution in both UI and backend.
  Reuse P15.1 update semantics, P15.7 readback/review and P15.8 station-planning
  rules, preserving profile/configuration authority and transaction boundaries.
  Status: complete, including WsprryPi item 15, confirmed by the operator on
  2026-10-17.
  WsprryPi coordinates; WsprryPico owns firmware, persistence and standalone UI
  implementation. Product `56821ac`, evidence `29542e4` and subsequent P15.12
  integration `227e73c` are included in published Pico `devel` at `156dfa1`.
  Software validation, exact unchanged-Pi compatibility pairs and independent
  reassessment passed. Pages checks passed; no firmware/software-test CI pass
  is claimed. The [Pico execution record](development/phase15-9-valid-field-saves.md)
  retains the exact sources, results and limits. P15.13 qualification and
  P15.20 operator documentation remain separate checklist items. The
  [originating post-execution assessment](development/phase15-9-post-execution-review.md)
  closes four repaired findings after fresh independent reassessment; Pi adoption
  remains a separate decision.
- ✅ **P15.10 — Allow hostname changes and use the hostname in the page title.**
  Provide a browser setting to edit and save the hostname, retain it across
  restarts and use it for LAN/mDNS discovery and access. The saved hostname must
  also drive the HTML page title shown in the browser tab, with the hostname
  first, for example `<hostname> - Station control`, instead of the generic
  `WsprryPico - Station control`. Verify distinct titles with two Pico tabs open
  and correct titles after a hostname change, page reload and restart. Reuse
  the established update rules and P15.7 recovery behavior for hostname/authority
  changes before P15.12 exposes the saved name as the main-page identity.
  A restart is an accepted application boundary; provide operator instructions
  and bounded countdown/reconnect assistance, confirming the same device, a new
  boot and the applied name before claiming success. Status: complete within
  the [recorded supported software acceptance](development/phase15-10-hostname.md).
  Consumer station/AP management, preserved CA/client trust, both firmware
  links, exact unchanged Pi compatibility, browser evidence and independent
  review repairs passed. Engineering names remain credential-bound; physical
  LAN/restart/RF and P15.20 operator publication remain separate.
  The [P15.10 execution handoff](development/phase15-10-execution-prompt.md)
  retains the source review and original implementation/review prompt.
- ✅ **P15.11 — Consolidate or split Station/Transmission and Wi-Fi/Host setup.**
  Remove duplicated settings between "Station and Network" and "Wi-Fi and
  station setup". Either consolidate them into one page with clear
  Station/Transmission and Wi-Fi/Host sections, or place those areas on separate
  pages. Wi-Fi/Host setup must be the default landing area for captive-portal
  access; Station/Transmission must be the default for an infrastructure Wi-Fi
  connection. Provide clear links in both directions so either area is reachable
  from the other. In a consolidated layout, entry points and links may target
  the corresponding sections of the page.

  Reorganize after P15.8-P15.10 settle station validation, saving independently
  of transmit readiness and hostname behavior, while preserving the existing
  profile/configuration authority boundaries. Verify both connection-specific
  defaults and navigation in both directions. The one-page versus two-page
  layout is implemented as one shared document with reloadable task-area links.
  Status: complete within supported software acceptance; see the
  [organization record](development/phase15-11-page-organization.md) and original
  [execution handoff](development/phase15-11-execution-prompt.md).
- ✅ **P15.12 — Show the hostname as the main-page identity.**
  Replace the prominent `Pico <full device ID>` text with the Pico's hostname.
  Make the full stable device ID available under About or Diagnostics for
  identification and troubleshooting. Use P15.10's persisted hostname and
  hostname-driven browser-tab title with the resulting P15.11 page layout.
  Verify the main-page identity stays consistent with the tab title after a
  hostname change, page reload and restart.
  The [reviewed execution handoff](development/phase15-12-execution-prompt.md)
  records current identity/title sources and the implementation/review prompt.
  Status: complete within supported software acceptance; see the
  [identity record](development/phase15-12-main-page-identity.md) for final checks,
  review repairs, transient host-test failures/skips and qualification limits.
  The operator accepted this P15.12 closure. Its P15.20 documentation handoff
  does not close operator-document publication. The original handoff preparation
  did not execute the work.
- ✅ **P15.13 — Complete untested-band qualification and resolve clock-dependent support.**
  Revisit the [band/mode chart](development/phase14-band-mode-qualification.md)
  and [machine-readable catalog](development/phase14-band-support.json). Test
  the originally Untested 8 m and 5 m entries across Tone, WSPR, QRSS, FSKCW and
  DFCW. The selected campaign uses Pico A for fourteen nominal transmission
  windows: one Tone, three Type 1 WSPR frames, one QRSS, one FSKCW and one DFCW
  per band. Pico B is used only for failure diagnosis; WSPR Type 2/3 testing is
  excluded. Build fresh uninhibited firmware from current project devel tips
  and flash A before testing; flash B with the same artifact only if needed.
  Additional clock acquisitions must address a specific finding rather than
  form a blanket clock sweep. Define finite
  conducted tests and acceptance criteria against identified current firmware,
  boards, engine, pins, clock and receiver/RF setup; record failures and
  unavailable configurations as well as passes. Run after the preceding
  firmware/interface changes to avoid repeating qualification for those changes.

  Identify and resolve each historical case whose result depended on another
  clock. Determine explicitly whether the delivered firmware provides the
  capability itself, needs a separate clock-specific build/reflash, or requires
  receiver adjustment. Current source uses build-time
  `WSPRRY_PICO_RF_SAMPLE_RATE_HZ` (138 MHz default; 132/150 MHz alternatives)
  and sets that clock at boot; automatic per-band clock selection is not
  implemented. Preserve the distinctions that 4 m is directly representable
  only at 150 MHz but remains Unqualified under the reliable-WSPR gate, while
  the 6 m WSPR exception is a receiver-only +125 Hz retune at 138 MHz.
  Neither establishes automatic firmware clock handling. If intrinsic support
  is missing, resolve the implementation/support policy explicitly; qualify any
  selected firmware change, including affected timing/resource/contention and
  regression checks, before claiming that capability.

  Update the chart/catalog with per-mode, per-clock and exact source/image
  applicability, normal-firmware behavior, required operator steps and honest
  Qualified/Unqualified/Unavailable/Untested outcomes. Preserve the closed
  Phase 14 scope and original results; this is a new follow-up. Historical raw
  captures and generated firmware were [disposed of](development/phase14-evidence-retention.md#october-15-operator-directed-test-data-disposal),
  so use the Git records as historical context and acquire fresh evidence.
  Record setup/settings restoration and review the resulting claims before
  P15.20 documents them. **Complete, 2026-10-17:**
  [results](development/phase15-13-results.md),
  [matrix](development/phase15-13-result-matrix.json) and
  [support policy](development/phase15-13-support-policy.md). All five modes are
  Qualified only at 40.001/60.001 MHz on Pico A, fresh source `165303458e49`,
  GP2/138 MHz. WSPR acceptance includes fixed +125/+200 Hz receiver-audio
  translation; the accepted 5 m sequence uses a cold boot and waveform-equivalent
  compact realized-frequency jobs. Actual accounting is 12 nominal RF windows
  plus four diagnostics (16 total); two original WSPR slots were untransmitted,
  and original invalid/partial cases remain explicit. B and alternate clocks
  were unused. Source/image, decoder/capture audit, affected checks, fresh
  self-review and restoration are recorded. This does not promote whole
  frequency intervals, refresh historical bands on current firmware or start
  P15.20's documentation site.
- ✅ **P15.14 — USB control.** Implemented in normal inhibited and StandaloneRF
  firmware and the Pi runtime/UI. Shared configuration, saved progress,
  canonical hostname, Wi-Fi create/replace/delete-last/recreate and qualified
  USB UTC work without Pico networking. Every AP entry has the same finite
  ten-minute maximum. Existing job capacities and other timing guards remain
  unchanged. The
  [execution record](development/usb-control-results.md) and
  [target result](development/usb-control-target-results.json) record 186 Pico
  checks, Pi/runtime/sanitizer/pair/compatibility checks, independent repairs,
  maximum-capacity physical LOAD and observed AP withdrawal under USB traffic.
  Exact original flash is restored. This closure does not renew transmitter
  RF/timing or unrestricted network/TLS coexistence qualification.
  The accepted [100 ms UTC follow-up prompt](development/utc-100ms-execution-prompt.md)
  and [results](development/utc-100ms-results.md) record the new/missing Pi
  settings default of 100 ms while preserving explicit limits, including 1 ms
  (Pi `1dd918b`, Pico `1162e4f`). The follow-up's software validation and
  adversarial self-assessments passed; no physical ARM or RF test was performed.
- ✅ **P15.15 — GPIO drive-strength configuration across Pico and WsprryPi.**
  After P15.14 USB acceptance, add persisted per-RF-pin drive choices of
  **2, 4, 8 and 12 mA**, default **4 mA**, to the Pico firmware, USB management
  and Console configuration, shared API, all applicable device-served settings
  pages and the selected Pico's WsprryPi UI. Apply through existing hardware
  restart/admission rules, preserving unrelated configuration, saved progress,
  legacy-client saves and exact-pair compatibility. Distinguish pad drive from
  reported WSPR power and measured RF power.
  Saved execution prompt: [P15.15 GPIO drive strength](development/phase15-15-execution-prompt.md),
  with its [prompt assessment](development/phase15-15-prompt-review.md).
  Status: **Complete within recorded scope**, 2026-10-17.
  [Software record](development/phase15-15-results.md) and
  [hardware acceptance](development/phase15-15-hardware-results.md) cover all
  four actual pad getter values on both boards, persistence/restart/physical USB
  re-enumeration, target lifecycle, finite conducted comparison and exact
  restoration. Numerical in-span energy findings remain nonblocking under
  explicit operator direction; no calibrated watts or all-band/mode RF claim.
- ✅ **P15.16 — Make the default firmware build uninhibited.** After P15.14 USB
  control and P15.15 GPIO drive strength are accepted, make the normal firmware
  target, `pico2-w` preset, build helpers and release recipe produce the same
  RF-capable normal application. Keep an explicitly selected inhibited variant
  for testing.
  Preserve saved configuration, timing, ownership and output-admission controls;
  RF capability does not enable transmission by itself. Validate both variants,
  affected regressions and build documentation before P15.17.
  Saved execution prompt: [P15.16 uninhibited default build](development/phase15-16-execution-prompt.md),
  executed 2026-10-17. Status: **Complete within recorded software/build scope**.
  [Execution record](development/phase15-16-results.md) and
  [artifact manifest](development/phase15-16-artifacts.json) track exact variants,
  hashes, resources, checks, the repaired LED-builder finding and clean independent
  reassessment. No physical RF/USB/timing qualification is renewed.
P15.1 and P15.2 were coordinated from WsprryPi: #447 delivered the Pico changes
and #448 delivered the Pi changes and paired compatibility evidence. With their
roadmap closure accepted, P15.3 returned to WsprryPico and is complete within
its recorded software scope, with companion Pi changes committed separately.
P15.4 shared-resource adoption is complete within its recorded software scope.
P15.5 concurrent web servicing is complete within its recorded software scope.
P15.6 independent sessions and P15.7 login/save recovery are complete within
their recorded software scopes. P15.8 Type 2/3 software and its WsprryPi step 14
integration are complete by operator acceptance. P15.9 and WsprryPi item 15 are
complete by operator confirmation on 2026-10-17.
Later ad hoc concurrency/recovery/resource testing
is accepted; no additional endurance qualification queue is selected.
P15.10 and P15.11 are complete within their recorded supported software scopes.
P15.12–P15.16 are complete within their recorded scopes.
GPIO drive strength retains
[bounded physical acceptance and RF observations](development/phase15-15-hardware-results.md).
The uninhibited default build (P15.16) has software/build acceptance.

## Current work

[Consolidated backlog](development/consolidated-backlog.md) is the sole current
work list. This acceptance record does not maintain a parallel queue.

<a id="planned-qrss-group-message-and-duration-limits"></a>

## QRSS-group message and duration limits

Decision: selected by the user on 2026-09-13. Implemented in Pico source
`7d183978d08d` and Pi companion `bba4024`. Phase 11.5 later accepted the limits
within its recorded 138 MHz/divider-1 physical scope; later Phase 14 reliability
and configuration results retain the accepted scope in its closeout ledger.

- Apply one uniform maximum message length of **32 characters, including
  spaces**, to QRSS, FSKCW and DFCW. Every supported character counts equally;
  do not expose a different character limit based on Morse complexity or mode.
- Allow complete finite transmission jobs of up to **60 minutes (3,600 seconds)**,
  including any repetitions and gaps within the job. Message length and total
  duration are independent limits; show the calculated transmission duration.
- Preserve WSPR framing and the existing supported Morse alphabet. This decision
  selects neither a new alphabet nor additional punctuation or prosigns.
- Budget internal event capacity for the worst-case supported 32-character
  message in every QRSS-group mode, plus required job-boundary events. Resolve
  repeated-message representation separately within the finite-job, advertised
  event and payload limits; do not assume the character cap bounds expanded
  repetitions or introduce per-symbol transport delivery.
- Retain fixed waveform buffers and local RP2350 execution. Assess peak memory
  across parsing, job copies and RF planning; audit duration/sample arithmetic,
  advertised capabilities and companion client validation. WsprryPi changes
  remain independently scoped in that repository.
- Validate 32/33-character and 60-minute duration boundaries, worst-case Morse
  expansion, completion, cancellation, disconnect handling and sustained resource
  use. Hardware-free checks precede separately authorized physical acceptance;
  later endurance evidence and its image-specific limits are recorded in the
  [Phase 14 closeout](development/phase14-closeout-ledger.md).

The implemented RF profile advertises 512 events and 3,600 seconds. The compact
message compiler expands finite repeats within both bounds; it never streams
symbol timing after ARM. Worst 32-character plans require 383 events, plus one
final off event for compact browser submissions. See the
[extended-job design](development/phase11-5-extended-job-design.md).
E0a has independently verified idle maximum admission and S0 has completed a
32-character, 384-event QRSS plan lasting 143.250001 seconds on the new image.
Actual QRSS, FSKCW and DFCW physical hours are recorded in checkpoints 006/010/012,
with their original observation limits preserved. Later Package 11 Retry 4
closed saturation/reclamation and Phase 11.5 at 6/6 for the recorded
configuration. The [current completion matrix](development/phase11-5-completion-matrix.md)
records source applicability and affected checks. The
[incremental ledger](development/phase11-5-acceptance-ledger.md#incremental-v2-validation)
preserves each applicable passing assertion without resetting unrelated checks.

## Completed baseline

The completed implementation history below retains each checkpoint's original
evidence scope. References to later Phase 14 work in that history are historical;
current closure and deferred items are recorded above and in the closeout ledger.

- Documented the accepted architectural decisions.
- Established draft WTP and browser API boundaries.
- Identified the static PIO divider resolution issue for a representative HF carrier.
- Recorded initial implementation and qualification boundaries; current status
  is detailed below.

## Completed WTP/1 contract

- Defined framing, exact representations, envelopes and operation schemas.
- Defined finite job limits, state transitions, ownership and clock rules.
- Defined retry, replay, reconnect, reset, error and transport behavior.
- Added machine-readable contract data, normative vectors and a dependency-free
  hardware-free validator.

## Completed hardware-free job service

The portable C++20 core now provides bounded frame parsing, SHA-256 replay
identity, typed request dispatch, ownership leases, immutable jobs, clock-aware
arming, lifecycle management, retained results and output-safe cancellation.
Deterministic tests use a virtual clock and mock RF engine.

Host evidence covers partial, malformed and oversized frames, unsupported
versions and modes, duplicate requests and ARM, concurrent owners, late starts,
clock rejection, reconnect/reset behavior, cancellation, output-disable
failure, and local execution without further requests. It is not target or RF
evidence.

## Completed Pico firmware foundation

The Pico SDK, Arm toolchain and picotool inputs are pinned. The Pico 2 W build
links the portable service to an unsynchronized target clock, fresh boot
identity, stable device identity and RF-inhibited engine. Two USB CDC interfaces
separate text diagnostics from bounded WTP framing. CMake presets and VS Code
metadata provide the same repository-root build.

## Completed dual USB CDC transport

Dedicated Console/WTP APIs provide bounded RX/TX, partial-write handling,
connection resets, distinct descriptor identities and deterministic isolation
checks. Hardware USB validation remains separately opt-in.

## Completed strict WTP USB adapter

Strict JSON request decoding, response/event encoding and typed job-service
routing now run on the WTP CDC interface. Connection negotiation, replayed
snapshots, logical closure and bounded ordered transmission are host-tested
against normative fixtures, the independent schema validator and monitor decoder.
An opt-in read-only probe is supplied. Bounded target USB checks pass for the
[recorded board, image and host](development/usb-target-validation.md); general
WTP conformance and RF qualification are not claimed.
See the [endpoint guide](development/wtp-endpoint.md).

## Completed RF feasibility and candidate selection

The [hardware-free comparison](rf-feasibility.md) and
[reproducible calculations](rf-calculations.md) compare static dividers,
PLL retuning, PIO/DMA synthesis and Si5351. PIO/DMA packed-bit GPIO synthesis
is selected for experimental implementation, initially at the 80 m study point,
with generation throughput, job lifecycle behavior and spectra still to assess. Si5351 remains
an alternative. This is candidate selection, not engine implementation or RF
qualification. The [bounded measurement plan](development/rf-measurement-plan.md)
remains broader than the initial bench measurements.

## Completed first Step 8 software slice

The [portable stream](development/rf-stream.md) implements bounded initial-tone
planning, packed waveform generation and a streaming engine behind an abstract
sink. Host tests cover sample accuracy, phase continuity, timing, ownership,
faults and job-service integration; the library also cross-compiles for Arm.
The [output/inhibit design](development/rf-output-design.md) is a proposal,
with electrical/filter details and qualification still pending.

## Completed second Step 8 software slice

The [PIO/DMA driver](development/pio-dma-driver.md) implements GP2 output,
finite buffer handoff, final zero clearing and local timer launch. The job service
can prearm local engines while preserving existing WTP clock and missed-start
semantics. Host fault/sequence tests pass and the actual SDK driver links for
Pico 2 W. No physical transmission was performed for this slice.

## Completed third Step 8 slice: bench integration and initial measurements

The separate [RF bench](development/rf-bench.md) implements finite relative-time
tones, CPU benchmarks, observed IRQ/stack metrics and software BOOTSEL. Exact word
lookup reduced worst measured refill from 22.092 ms to 1.507 ms with the same
checksum. Two preloaded data DMA channels and a dedicated final stop channel
resolved observed underruns. Recorded 100 ms and 1 s tones completed and were
received using the Harness capture helper on wspr5 through 60 dB attenuation.
Coarse carrier analysis remains inconclusive for qualification.

## Completed fourth Step 8 slice: frame and reference measurements

The [frame validation record](development/rf-frame-validation.md) covers two
complete 162-symbol synthetic frames, a ten-second tone against the GPSDO on
the combiner, and intentional abort/rearm. All 161 transitions were located;
maximum estimated timing error was 0.5 ms. The compared carrier was about
+7.85 Hz high, and frame frequency residual exceeded the 0.1 Hz diagnostic
criterion at 0.123 Hz. An in-window feature measured about -32 dBc. These remain
physical engineering findings; no WSPR message was encoded or decoded.

## Completed fifth Step 8 slice: correction and alias diagnosis

The [correction record](development/rf-correction-validation.md) validates
volatile frequency correction: short-run mean error fell from +7.974 Hz to
approximately +0.012 Hz with 2222 ppb correction. Retune, gain and reference-only
controls support an intrinsic sampled-square-wave alias near -33 dBc. The full
frame still fails the linear residual limit; a separate fit describes a roughly
0.40 Hz settling transient. Neither finding is silently promoted to a pass.

## Completed sixth Step 8 slice: clock and comparison experiments

The [clock validation record](development/rf-clock-validation.md) adds tested
132/138/150 MHz profiles and selects 138 MHz for the experimental bench. It
removes the original roughly -33 dBc alias at the recorded frequency. The
stronger +/-120 Hz sidebands follow a translated carrier and also occur on
wspr2 GPIO4. CPU activity before a frame did not materially improve settling
in the tested protocol. Progress arithmetic, completion acknowledgement and
capture storage checks were repaired and tested.

## Completed seventh Step 8 slice: encoded WSPR and RF warmup

The [encoded validation record](development/rf-wspr-validation.md) adds a
portable Type 1 encoder, a complete-message bench command, and independent
WSJT-X decoding of received RF from wspr5. Optional RF warmup improves the
measured frame settling. The final-data/tail acknowledgement path has additional
bounded recovery tests. Retained cold-frame diagnostic failures remain distinct
from successful decodes and repaired-image evidence.

The operator accepts better-than-WsprryPi close-in sidebands as a practical
benchmark. The earlier comparison meets that criterion; eliminating those
sidebands is not a prerequisite for further development. The operator develops
and applies output filtering; Phase 14 measures the established unfiltered path.

## Completed eighth Step 8 slice: USB UTC and RF job integration

The [UTC/WTP integration record](development/utc-rf-job-validation.md) adds a
portable bounded-uncertainty clock, a sampled USB time source and an explicitly
selected RF-capable WTP image. A future UTC job completed locally without
per-symbol USB traffic and independently decoded from a complete wspr5 capture.
The standard firmware remains inhibited. USB host time, receiver wall-clock
onset, the output network and calibrated filter/band behavior are not qualified.

## Step 9: standalone configuration, timing and physical operation

The [standalone guide](development/standalone.md) documents persistent station
identity and recurring schedules, an independent no-repeat watermark, Wi-Fi
SNTP acquisition and one-time Console provisioning. Standalone and USB WTP jobs
share the same job service. The standard image is RF-inhibited; an explicit
standalone RF image retains the experimental GP2 engine.

Deterministic and sanitizer tests cover autonomous simulated completion,
configuration/storage failures, restart/clock-step behavior, SNTP rejection and
host ownership. All firmware targets cross-link. The later
[inhibited bench record](development/standalone-physical-validation.md) adds real
configuration retention, autonomous SNTP, scheduled local simulation, Wi-Fi
outage/reconnection and watchdog recovery. The subsequent
[RF and wall-power record](development/standalone-rf-power-validation.md) adds
independently decoded recurring frames without USB job commands, a physical
separate-power boot, USB-host absence, and retained configuration/watermark.
This closes Phase 9's bounded functional acceptance. Timing/frequency
measurements, unfiltered output performance, wider network compatibility and
endurance remain Phase 14 qualification work. Filter development/application
belongs to the operator.

## Current boundaries

The firmware builds for Pico 2 W. The portable core and WTP USB endpoint are
host-tested, and bounded target USB validation passes on the recorded Pico 2 W
and Mac. Bounded RF bench transmissions, UTC-scheduled WTP integration and CPU
timing measurements are now recorded. Phase 11 adds its bounded inhibited,
resource/contention and scoped conducted-RF acceptance. Phase 14 closes its
declared conducted matrix, reviewed reliability/control results and reproducible
artifact scope. Its explicit measurement, endurance, security and excluded-band
limits remain documented; no Phase 14 workstream is open. WTP/1 schemas are
normative; changes to them require an explicit protocol-contract revision.
