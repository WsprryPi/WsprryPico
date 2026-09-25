# Phase 12 Raspberry Pi BLE and first-class TCP/WTP review

Status: **OPEN_PARTIAL**. The focused implementation and review slice is
complete. The second assessment's peer-binding finding was repaired, and the
final assessment found no actionable issue. Phase 12 is not complete: the open
gates at the end of this record remain open.

This is a historical slice record. It implemented profile transfer against the
then-current target contract. Later fresh-password `profile_step_up` hardening
temporarily made the native client's `provision` command nonconforming. The
subsequent Field-GATT/1 freeze repaired that source path with exact
session/request/generation binding, bounded confirmation polling and complete
7,168-byte capacity. Use the current
[Raspberry Pi client guide](raspberry-pi-ble-client.md), frozen
[Field-GATT/1 contract](../protocol/Field-GATT.md) and
[vectors](../protocol/Field-GATT-v1-vectors.json) for the operative boundary.
This historical live record still does not prove physical native-Pi profile
activation.

## Authority and source boundary

The executed contract is the
[Raspberry Pi BLE and first-class TCP/WTP prompt](phase12-pi-ble-tcp-execution-prompt.md).
Work began from clean `devel` at
`47ba73b3a44851aff0582bbf378cdb840007d430`, equal to `origin/devel`, on
2026-09-22. Changes were confined to this repository. No WsprryPi-family peer
repository was modified.

The implemented boundary is:

- a native Raspberry Pi/Linux BlueZ D-Bus client for the existing encrypted
  Phase 12 GATT service;
- at that checkpoint, authenticated field status, Identify, controller-time,
  WTP `HELLO`/`STATUS` and atomic profile-transfer support without an RF-start
  shortcut; later step-up hardening superseded the historical profile-apply
  claim until the current source repair, which has no new physical evidence;
- an explicit, tested contract that TLS 1.3/TCP is a first-class carrier of the
  same WTP/1 stream and the same `JobService` used by canonical/reference USB
  CDC; and
- no second scheduler, job store, protocol, RF engine or authorization model.

The TCP implementation already met that contract. The change therefore adds a
deterministic contract test and corrects documentation instead of replacing the
working network adapter. TCP remains default-off and product-gated; production
use requires TLS 1.3, ALPN `wtp/1`, mutual device-specific authentication and a
certificate-derived transport principal. Plaintext, TLS 1.2, PSK, early data,
silent downgrade and a hard-coded default port remain nonconforming.

## Implementation result

`scripts/wsprrypico_ble.py` uses the native BlueZ D-Bus API and requires both an
exact BLE address and the complete 128-bit device identity. Pairing uses a
transient NoInputNoOutput agent only for an unpaired peer, preserves the bond,
and never sets BlueZ `Trusted`. `inspect` requires an existing bond. The
application password is read only through a non-echoing prompt.

The client implements the existing UUIDs and fragmentation contract, exact
request/operation matching, stale-response rejection, CRC32C WTP framing,
bounded waits and allocations, exact WTP status semantics and identifier-only
remote errors. Atomic profile input must be absolute, nonsymlinked,
invoking-user-owned, regular, no larger than 7168 bytes and inaccessible to
group/other users. It is canonically validated before the target transaction,
and failure attempts cancellation without printing secrets.

The live controller-time exercise exposed a real timing defect. The repaired
firmware starts the target's delay measurement when the final challenge
response indication is successfully queued, retains the nonce so disconnect
can cancel the pending challenge, and clears it after submission. The Linux
client sends the ordered `time_submit` fragments with encrypted GATT
write-without-response and still waits for the target's application response.
The existing 250 ms fixed clock allowance and 500 ms maximum were not relaxed.

## Deterministic verification

The final source was checked with the repository's documented pinned toolchain
and dependencies. The target build used Pico SDK 2.3.1 at clean revision
`079c6f39023649b154152db30f1d781e884879bc` and its clean BTstack submodule at
`eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`.

| Check | Result |
| --- | --- |
| Full host suite, `ctest --preset host-debug --output-on-failure` | PASS, 86/86 |
| WTP contract validator, `python3 scripts/validate_wtp_contract.py` | PASS, 23 schema + 7 raw JSON + 1 framing + 8 transition cases |
| Raspberry Pi BLE client unit suite | PASS, 12/12 |
| Focused sanitizer suite: provisioning, field access, Pi BLE, network transport and endpoint | PASS, 5/5 |
| Pico 2 W standard image plus RF-driver, provisioning and field-access target link checks | PASS, 4/4 |
| Standard-image layout, shutdown, inhibited-sync, heap-hook, stack-guard and endpoint checks | PASS, 6/6 |
| Python compilation and `git diff --check` | PASS |

The standard RF-inhibited image exercised below was built from
`d52a2fa6a3a314704841be00897e36681037b791`. Its UF2 SHA-256 is
`cdad4d238bb4f0411bdef4f6402136d3494bdefbf82976564f66082f95717b0c`; ELF
size was 1,311,792 text, 0 data and 133,732 BSS bytes.

These results prove deterministic behavior and build/link integrity. They do
not prove RF timing, spectral behavior or unexecuted physical transports.

## Bounded RF-inhibited live evidence

The authorized live subset used only Candidate A and `wspr5`:

| Item | Exact identity/result |
| --- | --- |
| Host | `wspr5`, Linux 6.18.34 aarch64 |
| BlueZ controller | `2C:CF:67:62:76:68` |
| Target | Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344` |
| Device identity | `fd6127d11d6aca42a9905fa3fb1bf1d5` |
| BLE peer | `88:A2:9E:0A:60:E0`, `WsprryPico-0a60df` |
| Firmware | `d52a2fa6a3a3`; boot `8523e76c5040d8e71cd8f4f402a99def` |
| Live client SHA-256 on wspr5 | `8e22b4da7ef40aba2608fab3bbc50a81eb06f931c1fd0791079fb2e33fad3c9c` |
| Bond after exercise | paired yes, bonded yes, trusted no |
| Access state after exercise | healthy, generation 3, BLE running, enrollment closed |

The exact Candidate A serial was selected for each verified load; Candidate B
serial `CDDBF8767C506C07` was not flashed or operated. The final client run
verified identity inspection, accepted authenticated controller time, returned
field status, negotiated WTP/1 and returned an exact empty WTP status with the
same device/boot identity. Immediately after controller-time acceptance the
field status reported source `controller`, age 31,670,395,000 ns, uncertainty
450,156,519 ns, no clock disagreement, indicator off and no fault.

The final peer-bound pairing callback repair followed that live run. Its final
local client SHA-256 is
`fb4fd65bb5de475c58fb464dd9145cf67e2440d42a411f944ad4dd69fdfc991d`; it has
deterministic source/host coverage, not a destructive unpair/re-pair retest.
That distinction does not rewrite the live GATT operation evidence above.

The final authenticated inventory proved factory profile generation 0, healthy
access generation 3, network control unconfigured/not listening, the
RF-inhibited simulator, station `AA0NT`/`EM18`/20, schedule 120/0, watermark
`1789607761000000000`, healthy storage, no owner, no job and
`output_active=false`. No profile, Wi-Fi/TLS, station, schedule, watermark, RF
path or job was changed. No RF was enabled and no finite RF campaign allowance
was consumed.

Failed attempts are retained rather than hidden. The original image and the
first timing repair rejected controller time as `invalid_request`. Moving the
target measurement to confirmed indication delivery remained racy; measuring
from response queueing then showed that five ATT write-response round trips
could not fit the remaining bound. The final encrypted, ordered
write-without-response submission passed without relaxing either clock limit.

This is physical evidence only for the named Pi, controller, target, firmware,
commands and RF-inhibited state. It is not BLE job execution, profile
activation, Bluefy/iOS, SoftAP, network TCP interoperability, coexistence, RF
or release qualification.

## Adversarial assessment 1 and repairs

The first assessment found and repaired the following actionable issues:

1. Notifications were not bound tightly enough to one pending request and
   operation. The client now ignores stale replies and rejects duplicate or
   mismatched in-flight responses.
2. `inspect` could create and then abandon a provisional bond, and returning
   peers unnecessarily registered the pairing agent. Inspection now requires
   an existing pair; the agent is installed only for an unpaired peer.
3. Nonfinite timeouts, uncleared consumed WTP bytes, a failed-HELLO cleanup
   path and the wrong D-Bus exception class were corrected.
4. BlueZ signals are now restricted to sender `org.bluez`; target error text is
   accepted only as a stable identifier so it cannot inject output or payloads.
5. WTP `STATUS` receives exact semantic validation, not merely valid JSON.
6. Stale network documentation that described production GATT/activation as
   unimplemented was corrected.
7. Live controller time exposed the timing/cancellation defects described
   above. Response-start anchoring, disconnect cancellation and ordered
   encrypted write-without-response submission closed them, with focused tests.

## Adversarial assessment 2 and repair

The second assessment rechecked exact address plus full device-ID binding,
Just Works limitations, transient/no-trust pairing, password and profile-secret
handling, file ownership/mode/symlink/size controls, bounded memory and waits,
stale/duplicate response behavior, WTP CRC/session/operation/status binding and
the absence of an RF shortcut. It found that the transient agent was installed
only while pairing the exact peer, but its BlueZ authorization callbacks did
not themselves reject another device path during that short default-agent
interval. Both `RequestAuthorization` and `AuthorizeService` are now bound to
the exact peer path; the latter also remains bound to the WsprryPico service
UUID. A contract regression assertion covers both checks.

## Adversarial assessment 3

The final assessment repeated the client checks above after that repair.

It also rechecked that the controller-time hook runs only for a successfully
queued final indication, disconnect cancels a pending challenge, submission
clears it, encrypted ordered writes fail closed and neither timing threshold
changed. The TCP review rechecked default-off startup, TLS 1.3, mTLS, ALPN,
certificate-derived principal, no plaintext/downgrade/default port and the
shared USB/BLE/TCP `JobService`. Documentation claims were compared against the
actual source, host, target-build and named live evidence boundaries.

Result: **no actionable finding remains within this focused slice**.

## Remaining gates

- Bluefy/iOS offline acceptance and broader phone-time/Identify behavior;
- SoftAP/HTTPS provisioning, fallback and reset/gesture controls;
- physical profile transfer/activation and recovery;
- BLE WTP job execution and the broader local-management/coexistence matrix;
- a new physical TCP/TLS interoperability and concurrency exercise for this
  source (the implementation remains first-class and host-tested now);
- the remainder of the Phase 12 RF-inhibited physical matrix; and
- all RF, spectral, timing, reliability and release qualification assigned to
  later acceptance work.

This focused closure does not convert any of those gates into accepted
evidence and does not close Phase 12.
