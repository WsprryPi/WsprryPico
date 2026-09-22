# Phase 12 BLE local-control continuation review

Status: **OPEN_PARTIAL**. This source tranche advances P12.6 but does not close
Phase 12 and supplies no new physical acceptance.

## Authority and starting point

Execution began on clean `devel` at
`22069831915384500b5128990ce479fe79a7a0f4`, equal to the local
`origin/devel` reference. The controlling execution brief is the
[Phase 12 remaining-production prompt](phase12-completion-execution-prompt.md).
It authorizes the RF-inhibited work named there and keeps Stage B and RF output
outside scope.

The initial code review confirmed one production `JobService`, the existing USB
WTP endpoint, provisioning-only BLE GATT, the network-only profile activator,
the controller/SNTP arbiter, the indicator controller and cross-linked but
unstarted SoftAP primitives. The production graph had no BLE WTP transport and
no BLE command route to controller time, Identify or their nonsensitive status.
SoftAP still lacked a production DHCP and HTTP/HTTPS service.

## Implemented boundary

- The authorized BLE command session now exposes strict, closed-object
  `identify`, `field_status`, `time_challenge` and `time_submit` operations.
  Requests require the full device ID, current retained-bond principal,
  confidential/local authorization and the field session established by the
  page's authorization exchange. Controller-time challenge and submission keep
  their existing principal/session/device/nonce binding and conservative
  uncertainty rules.
- GATT adds separate encrypted write and indicate characteristics carrying the
  unchanged WTP/1 byte stream. A second `wtp::Endpoint` shares the production
  `JobService`; the transport does not translate WTP or create another job,
  scheduler, timing or RF authority. WTP admission requires application
  authorization and indication subscription. Input and output use bounded
  64-byte ATT segments, one confirmed indication at a time, and ordinary
  endpoint disconnect/lease semantics.
- Provisioning indications retain priority and their existing delivery-confirmed
  activation boundary. WTP and provisioning CCCDs, buffers and diagnostics are
  separate. The standard image reports bounded WTP segment and byte counters.
- The repository-owned Bluefy client implements the same controller-time,
  Identify and status commands plus WTP/1 framing, CRC-32C, fragmented and
  combined receive, HELLO/device/boot verification, one outstanding request and
  fail-closed disconnect on a corrupt stream. The page offers explicit
  authenticated controls for Identify, phone time, field status and read-only
  WTP STATUS; its client API can carry all unchanged WTP operations.
- The deterministic `docs/bluefy` release was regenerated as
  `037b80144b7eb8079aca78be42635408530e2752d46fb8112e10f34d41f7916d`.
  The page explicitly warns that a retained authorized bond resumes ordinary
  local access without making the entered text a fresh password proof.

This tranche does **not** production-enable SoftAP, DHCP, captive/read-only
bootstrap HTTP, SoftAP HTTPS/cookie control, password/reset administration or a
physical gesture. It does not establish Bluefy compatibility, phone-time
accuracy, LED timing, BLE WTP interoperability, resource coexistence or profile
activation on a device.

## Deterministic validation

| Check | Result |
| --- | --- |
| Host build | passed |
| Aggregate CTest | 83/83 passed with explicit Xcode 26.5 compiler/SDK paths and loopback permission |
| Phase 11.7 closure/adversarial audit | passed; all 33 mutations rejected |
| Focused ASan/UBSan provisioning, field-access and endpoint checks | 3/3 passed |
| WTP/1 validator | 23 schema, 7 raw JSON, 1 framing and 8 transition cases passed |
| Bluefy client, release and C++/web contract checks | passed |
| Pico 2 W standard image plus field/provisioning/RF-driver linkchecks | passed with pinned SDK 2.3.1 / BTstack |
| Image end/layout, shutdown, heap-hook, stack-guard and inhibited-sync checks | passed |
| Standard image size | text 1,310,288; BSS 133,708 bytes |
| Working-tree UF2 SHA-256 | `8d825ec151c0c018e5b0581b4366e8e7b0f625539170eeae3f931f2223367558` |
| `git diff --check` and JavaScript syntax | passed |

The initial sandboxed aggregate run exposed a defective Phase 11.7 assumption: its closure
audit compared the current production tree with the Phase 11 tested revision,
thereby making every authorized later-phase runtime change a permanent test
failure. The audit now validates the fixed candidate-to-tested interval and
retained immutable artifacts without freezing future source. A regression test
prevents reintroducing a current-tree comparison. That run also exposed the
macOS 27 Command Line Tools `.tbd` incompatibility and sandbox denial of the
loopback-only TLS listener. The final aggregate run pinned the installed Xcode
26.5 compiler/SDK and permitted only the test's local listener; all 83 tests
passed. No assertion was hidden or relaxed.

The target build used the already retained clean SDK at
`079c6f39023649b154152db30f1d781e884879bc` and BTstack at
`eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`. CMake reused its existing local
picotool source/build; no dependency fetch was used as acceptance evidence.

## Adversarial review and repair

The first review found five actionable issues:

1. Field commands checked live BLE authorization but accepted an arbitrary
   request session. They now require the session established by the successful
   page authorization and scrub it on disconnect; wrong-session coverage was
   added.
2. The browser could pipeline WTP requests although the bounded endpoint applies
   response backpressure. The client now admits one outstanding WTP request and
   reports `wtp_busy` before sending another.
3. Identify, field-status, controller-time and HELLO replies were insufficiently
   validated before presentation. The client now validates their exact security-
   relevant shapes, including boolean output authority before displaying WTP
   STATUS.
4. A corrupt WTP indication rejected a pending request but left the logical BLE
   session reusable. CRC/framing failure now disconnects the complete BLE
   session; a failed HELLO does the same.
5. The page's password wording could imply that the already-authorized retained-
   bond path proves a fresh password. The UI now states the distinction.

A second review found that an open WTP endpoint could outlive expiry of
application authorization, and that a late indication completion after such a
release or CCCD close could still touch the closed endpoint. The transport now
releases WTP ownership as soon as authorization lapses and safely ignores that
late completion. It also forbids reopening a new logical WTP endpoint while
that old generation's indication completion remains outstanding. The suspected
response-buffer replacement path was already
closed by the existing `outbound_.empty()` admission check and required no
change.

After that repair, a third review rechecked GATT serialization, CCCD reset,
indication completion, provisioning-response priority, endpoint principal and
lease ownership, authorization expiry, time nonce/session binding, response
bounds, disconnect paths, release determinism, image layout and secret/candidate
leakage. No further actionable source finding remained. Target runtime behavior
and the additional endpoint's peak-resource coexistence remain physical
acceptance gates, not source conclusions.

## Physical disposition and remaining gates

No device was flashed or operated in this tranche. The exact iPhone model, iOS
release, Bluefy identity/version, offline cache state, private provisioning
credentials and required operator interactions were not available to this
execution environment. Those rows are `NOT_EXECUTED`; the earlier retained-bond
online exchange remains the latest physical Bluefy evidence and is not rebound
to this source.

Phase 12 remains open for a clean committed-image reflash; exact client/page
identity and offline reuse; fresh-password/new-pairing and full profile
activation; live controller-time, Identify and BLE WTP behavior; production
SoftAP DHCP/HTTP/HTTPS and independent cookie-authorized control; password,
bond and reset/recovery administration; fault/resource/reclamation/soak rows;
and final RF-inhibited restoration. Stage B and Phase 13 remain separate.
