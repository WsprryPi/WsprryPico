# P12.8 consumer profile structural foundation review

Historical checkpoint: the later
[consumer pre-clock boot review](phase12-8-consumer-preclock-review.md)
supersedes this record's statement that runtime loading always faults on
source 5. Structural admission now permits station time and read-only AP
recovery while all consumer authority remains disabled.

Status: **BOUNDED SOURCE FOUNDATION; CONSUMER COMMISSIONING OPEN**
(2026-09-27). This review follows the approved
[P12.7 Safari/SoftAP contract](phase12-7-decision.md) and the
[earlier continuation review](phase12-7-8-continuation-review.md). It records
code and host checks, not a phone, provisioned-button, TLS or RF acceptance.

## Implemented boundary

- [Consumer-Profile/1](../protocol/Consumer-Profile-v1.md) now has a strict
  portable parser/serializer. It enforces exact keys and order by canonical
  round trip, bounded JSON, Wi-Fi/station field rules, unique owners and client
  serials, sorted client-key digests, canonical base64url, CSR digest, TLS
  aggregate size and the 7,168-byte journal payload limit. It does **not**
  establish that owner points are on curve or that CSRs, certificates, keys,
  SAN, purpose, expiry and exact target identity are cryptographically valid.
- Journal source 5 accepts only canonical structural payloads from a blank
  generation-0 device, a network-only profile or another consumer profile.
  Network-only upgrade and consumer replacement must retain the full device
  identity. Consumer replacement cannot lower the owner epoch or change data
  while reusing the previous request digest. Legacy runtime/factory replacement
  from source 5 is refused; the existing two-slot sequence and committed-slot
  failure rules remain in force.
- Runtime loading **rejects** source 5 until the consumer credential validator
  and owner-authority path exist. The firmware suspends autonomous schedules,
  denies legacy BLE and USB WTP job-control entry, and denies console mutation
  when runtime profile loading fails. Diagnostic `INFO`, `ABORT`, `REBOOT` and
  physical USB bootloader recovery remain available. No Owner-HTTP route calls
  the journal writer. This is an inert format, not a consumer setup release.

The installed Candidate A image remains RF-inhibited `fb091f8` / UF2 SHA-256
`d262c9a92a0b7ec3be4739e50e39c8b7ac59a80f25863e4bf840e40b38a18ce2`.
No flash, button press, credential submission or RF action occurred in this
slice. The newer source cross-build in
`build/phase12-captive-pico231/firmware/WsprryPico.uf2` is unflashed,
SHA-256 `d2988dbf3a930b3c60b3f851f13651fa32c0e1812a41c3ae6f3eca0f5121b97f`.
The linked ELF reports 1,496,632 text bytes and 135,680 BSS bytes. Build output
paths are mutable and do not identify the installed image.

## First adversarial pass and repairs

| Finding | Repair |
| --- | --- |
| The initial structural validator allowed two client entries with the same certificate serial. | Rejected duplicate nonzero serials and added a focused regression. |
| The first serializer used short JSON escapes for PEM newlines, contrary to the project's canonical JSON quote rule. | Wrote directly into the output with the project escape spelling and checked against `wtp::json::quote`. |
| A canonical replacement could lower `owner_epoch` or reuse the previous request digest for changed data. | Added monotonic epoch and changed-request checks before any flash write; tested both rejection paths. |
| Journal source 5 could be structurally readable while legacy BLE or USB job control still started after runtime rejection. | Gated those transports, schedule admission and console mutation on successful runtime profile loading; retained read-only diagnostics and physical recovery. |
| The accepted four-owner/four-client profile budget was only a calculation. | Tested four maximum-size 320-byte CSR encodings, escaped maximum Wi-Fi/name fields, long time server, full 2,304-byte TLS object and round trip under the slot limit. |
| Top-level README, contract and architecture still presented the old BLE/password path as the selected consumer design. | Distinguished the running engineering path from the approved Safari-only consumer contract and updated the bounded Wi-Fi-only physical result. |

## Second adversarial assessment and checks

The second pass traced source-5 selection, boot loading, scheduler, GATT,
station TLS, SoftAP and USB WTP admission. No route can create source 5 in
the current image, and the unsupported source cannot activate old trust or
schedule a job. A corrupted newer committed slot still prevents fallback to
an older authority. The source 5 reader and writer remain intentionally
structural: their test PEM and CSR bytes are not valid cryptographic material.
No further actionable issue was found **within this bounded inert-storage
slice** after the repairs.

- Focused parser and storage tests: 2/2 passed. The storage test cuts every
  profile-journal write page before commit and verifies recovery to the prior
  network-only generation; a corrupt committed newest slot fails closed.
- Full host CTest: 94/95 passed in the Xcode SDK environment; the loopback
  TLS test failed because the sandbox denied binding `127.0.0.1:18443`.
  That exact test passed 1/1 with local loopback access. The earlier default
  Command Line Tools run had three SDK `.tbd` linker failures; the exact three
  passed 3/3 with Xcode `DEVELOPER_DIR` and macOS 26.5 `SDKROOT`. These are
  environment failures, not passing behavior inferred from a failed run.
- RF-inhibited Pico 2 W cross-link passed. The linked image still has one
  SRAM BOOTSEL callback and no core-1 launcher/reader. This proves no live
  flash, radio, trust or button behavior.
- `clang-format --dry-run --Werror`, `git diff --check` and changed Markdown
  relative-link resolution passed after final edits.

## Required next gates

P12.8 still needs platform P-256/CSR/certificate validation, checked entropy
and UTC, on-Pico CA/server generation and renewal, Owner-HTTP/1 crypto vectors,
single-claim and encrypted owner-session state machines, legacy-authority
cutover, station-client enrollment, durable reset intent and consumer station
overlay. P12.9 needs the guided Safari page. The prior failed core-1 physical
BOOTSEL press remains failed; a provisioned/core-1-safe gesture is a hard
target gate. P12.10–P12.12 still require separately authorized RF-inhibited
physical acceptance. Phase 12 is active and not closed.
