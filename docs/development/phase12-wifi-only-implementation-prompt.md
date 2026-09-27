# Phase 12 Wi-Fi-only network bootstrap: implementation prompt

Status: **APPROVED DESIGN; EXECUTION IN PROGRESS; TARGET GATES OPEN**.
The operator approved the bounded [product design](phase12-wifi-only-bootstrap-proposal.md)
and [WiFi-Bootstrap/1 wire contract](../protocol/WiFi-Bootstrap-v1-proposal.md)
on 2026-09-26. Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Scope

Implement first station-network setup from a truly blank Pico 2 W through its
open, AP-local captive page. The browser creates a fresh X25519 key, starts one
slot, prompts a runtime BOOTSEL press and release, encrypts the entered SSID and
password, and submits them. The Pico trials association and DHCP while the AP
remains available, commits a device-bound network-only generation 1 record,
and reports **Network connected** only after durable commit and live address
readback. Keep Safari at `http://192.168.4.1/` as the fallback. No code,
certificate installation, Bluefy, BLE requirement, owner claim, station API,
new job/RF authority or legacy factory-bundle credential use belongs to this
slice. Preserve existing USB-local engineering authority and all unrelated
stores. Stage B and Phase 13 are separate.

## Execution order

1. Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`, the
   Phase 12 roadmap, field-access contract, approved design, wire contract,
   vectors, design review and latest blank-AP physical result. Inspect the
   current checkout, target SDK, storage, access journal, flash coordination,
   RF worker, SoftAP, DNS, HTTP, station state and tests. Preserve user edits.
2. Prove a bounded runtime BOOTSEL sampler on the exact RF-inhibited target
   before enabling credential submission. It must run from SRAM in an SDK
   flash-safe zone, stop or coordinate the other core, tolerate CYW43 load,
   preserve QSPI control state, reject a held/stale level and fail closed on
   coordination error or timing overrun. The diagnostic image may expose only
   a USB-local probe. Obtain explicit authority for the exact flash, device,
   BOOTSEL operation, AP use, duration and restoration before target action.
   If this gate fails, keep every mutating HTTP route disabled.
3. Implement one slot and the exact version-1 request/response schema. Admit
   only AP-interface requests with the specified Host, Origin, content type,
   header, length and canonical encodings. Reject duplicate/unknown JSON
   fields, replay, wrong device/boot/slot, competing clients, expiration,
   unsafe activity and damaged access/profile records. The physical edge
   grants only one matching slot. Initialize an exactly erased access journal
   after that edge and before accepting credentials.
4. Bundle pinned, license-attributed browser crypto locally; feature-detect
   secure randomness and actual X25519/HKDF/ChaCha20-Poly1305 operation before
   showing any password field. Match the synthetic vector independently on
   browser and Pico. Encrypt the exact binary plaintext with the specified
   transcript, wipe ephemeral/private/plaintext buffers on every terminal
   path, and keep credentials and keys out of logs, URL, persistent browser
   storage, status and errors. The accepted active page-relay risk remains
   accurately disclosed.
5. Trial AP/STA association and DHCP in RAM before a single transactional
   network-only journal commit. On failure, disable the transient station
   link, retain the AP and allow a new physically granted attempt. On commit
   failure, report failure and do not claim a connected state. Prevent legacy
   Wi-Fi resurrection, malformed journal fallback, schedules, station
   TLS/WTP/HTTPS listeners, browser job API and RF authority in network-only
   mode. A later full profile upgrades generation 1 to generation 2.
6. Keep the AP through the terminal response and authenticated browser
   acknowledgement. Withdraw it only with stable station service or after the
   bounded stable-service timer. A later station failure may bring back a
   read-only AP; credential replacement needs another physical grant.
7. Add deterministic host tests for the vector and tampering, malformed HTTP,
   physical slot lifecycle, competing clients, access initialization,
   association/DHCP timeout, commit interruption, response loss, reboot,
   wrong-device storage, no credential resurrection and authority isolation.
   Cross-build the RF-inhibited image and inspect its resource bounds. Keep
   hardware tests opt-in and record exact image, device and result.
8. Perform an adversarial review against the approved contract and existing
   field-access/RF boundaries. Fix actionable findings, rerun affected checks,
   and perform another adversarial assessment. Reconcile roadmap, protocol,
   security and acceptance documents without calling source tests physical
   acceptance. Commit and push reviewed work on `devel`; verify remote parity.

## Target acceptance after explicit authority

On the exact blank Pico and selected iPhone, separately record automatic
captive launch, captive-sheet crypto/form completion, Safari fallback, one
encrypted join, journal generation/readback after reboot, failed join/retry,
AP withdrawal/fallback and final RF-inhibited, output-inactive restoration.
An isolated Raspberry Pi can exercise the AP protocol and network path but
cannot qualify the selected iPhone behavior. Do not close Phase 12, Stage B or
any RF row from this network-only result.
