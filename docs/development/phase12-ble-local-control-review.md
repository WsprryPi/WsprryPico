# Phase 12 BLE local-control continuation review

Status: **OPEN_PARTIAL**. This source tranche advances P12.6 but does not close
Phase 12. Its clean committed-image boot/preservation baseline passed on
Candidate A; at this tranche checkpoint none of the new BLE operations had
physical acceptance. Later page/transport repairs and bounded iPhone/Bluefy
evidence are recorded in the current
[production acceptance review](phase12-production-acceptance-review.md); they do
not retroactively change this historical candidate or its validation record.

## Authority and starting point

Execution began on clean `devel` at
`22069839837afdbf5e5799d8834bd65cd66a3526`, equal to the local
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
- A later Bluefy interoperability repair adds the authenticated,
  connection-scoped `select_wtp_status_carrier` field command. It lets the
  browser carry those same WTP/1 bytes on the already-active field command and
  status characteristics when Bluefy cannot activate or move to the dedicated
  WTP characteristics. The selector reply binds both directions before the
  local parser changes. The mode is cleared on authorization and disconnect,
  requires the current field session and never changes the Raspberry Pi/BlueZ
  client's dedicated WTP characteristic path.
- Provisioning indications retain priority and their existing delivery-confirmed
  activation boundary. WTP and provisioning CCCDs, buffers and diagnostics are
  separate. The standard image reports bounded WTP segment and byte counters.
- The repository-owned Bluefy client implements the same controller-time,
  Identify and status commands plus WTP/1 framing, CRC-32C, fragmented and
  combined receive, HELLO/device/boot verification, one outstanding request and
  fail-closed disconnect on a corrupt stream. The page offers explicit
  authenticated controls for Identify, phone time, field status and read-only
  WTP STATUS; its client API can carry all unchanged WTP operations.
- Bluefy enters local WTP control without a disconnect, a second
  `startNotifications()` call, event-listener replacement, characteristic
  change or CCCD transition. It first selects the field transport through the
  authenticated command/reply path, then changes only its parser on the
  existing indication. Returning to field control deliberately reconnects and
  renews the retained-bond field session.
- The deterministic `docs/bluefy` release was regenerated as
  `35bd0b872dd19ff50f9d467a1437729c77d384917dae7982639ef4ca6b8d1778`.
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
| Aggregate CTest | initial 83/83; final repaired clean-config run 75/75 with explicit Xcode compiler/SDK paths |
| Phase 11.7 closure/adversarial audit | passed; all 33 mutations rejected |
| Focused ASan/UBSan provisioning, field-access and endpoint checks | 3/3 passed |
| WTP/1 validator | 23 schema, 7 raw JSON, 1 framing and 8 transition cases passed |
| Bluefy client, release and C++/web contract checks | passed |
| Pico 2 W standard image plus field/provisioning/RF-driver linkchecks | passed with pinned SDK 2.3.1 / BTstack |
| Image end/layout, shutdown, heap-hook, stack-guard and inhibited-sync checks | passed |
| Final clean committed standard image | source `5afe7576f0016ef3e927090c15232ac5c8daeb4f`; firmware `5afe7576f001` |
| Standard image size | text 1,310,520; BSS 133,708 bytes |
| Committed-image UF2 SHA-256 | `112f798233e12f2e9b7b049412ab428346b9fb1fc734915e823d1cb84feb7c12` |
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
passed. After the final encryption-loss repair, a fresh clean configuration
using the then-current Xcode 26.6 compiler/SDK passed all 75 currently
registered tests. No assertion was hidden or relaxed.

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

A fresh post-evidence adversarial pass then found that an HCI encryption-loss
event could leave application authority and queued server output alive until
the later disconnect callback. Attribute permissions rejected new writes, but
that was not a sufficient fail-closed boundary for already queued indications.
The transport now immediately disconnects the application session and WTP
endpoint, scrubs provisioning output, clears both CCCDs and abandons any active
indication's completion ownership before requesting link disconnect. The
wire-contract regression and fresh 75/75 host run, focused 3/3 ASan/UBSan run,
all target linkchecks and all five image checks passed. A final reassessment
found no further actionable source issue within the implemented boundary.

## Physical disposition and remaining gates

Candidate A, and no other Pico, was reflashed with the clean committed standard
image above by serial-targeted `picotool load -v -x`; verify completed `OK`.
Preflight established the exact device ID, station MAC, RF-inhibited simulator,
empty/unowned state, authoritative inactive output and healthy journals. The
first clean reflash changed boot ID from `a4083142c199d0bb3cfabfd69cedb90b`
to `bb9ab0b52c02b3ddde46b5150cadd449`. The post-adversarial repaired reflash
changed it again to `e7e8854f51789fb1aef53281c817d588`. Final postflight
preserved access generation 2,
factory profile generation 0, station `AA0NT/EM18/20`, the 120/0 schedule,
watermark `1789607761000000000`, configuration journal sequence 72 and
watermark journal sequence 12. It again reported the RF-inhibited simulator,
healthy storage, `empty`, unowned and `output_active:false`. BLE was running,
disconnected, and all new WTP counters were zero. The bounded private packet and
UF2 remain off-repository on `wspr5`; no secret or raw access record entered Git.

This passes only the clean committed-image reflash, identity/preservation boot
and final RF-inhibited restoration baseline. It does not exercise the new BLE
command or WTP paths. The exact iPhone model, iOS release, Bluefy identity/
version, offline cache state, private provisioning credentials and required
operator interactions were unavailable. Those rows are `NOT_EXECUTED`; the
earlier retained-bond online exchange is not rebound to this source.

Phase 12 remains open for exact client/page identity and offline reuse;
fresh-password/new-pairing and full profile
activation; live controller-time, Identify and BLE WTP behavior; production
SoftAP DHCP/HTTP/HTTPS and independent cookie-authorized control; password,
bond and reset/recovery administration; fault/resource/reclamation/soak rows;
and restoration again after any future physical mutation. Stage B and Phase 13
remain separate.
