# Phase 12 RF-inhibited SoftAP physical review

Status: **PARTIAL PASS** on 2026-09-23. Phase 12 remains active and Stage B
remains unauthorized.

This review records the finite SoftAP work authorized by
[the completion execution prompt](phase12-completion-execution-prompt.md). The
machine-readable companion is
[the SoftAP physical result](phase12-softap-physical-result.json). No RF output,
`LOAD` or `ARM` operation was used.

## Exact boundary

The work began from clean `devel` at
`c84fa157b93493cf0c28fa2e96c30e0beeabe7e2`. Source was reviewed and allowed to
change before candidate commits were made; no pre-freeze drift sentinel was
installed. Each actionable target finding produced a new commit, exact rebuild
and affected physical repeat.

Only Candidate A was modified:

- Pico 2 W serial `0BF4B4AEC9FFB344`;
- device ID `fd6127d11d6aca42a9905fa3fb1bf1d5`;
- station MAC `88:a2:9e:0a:60:df`, BLE address `88:A2:9E:0A:60:E0`;
- SSID `WsprryPico-0a60df` and hostname `wsprrypico-0a60df.local`.

Comparator serial `CDDBF8767C506C07` was not flashed or otherwise modified.
The controller retained management on `eth0` and `wlan1`; the isolated `wlan2`
interface was used only for the candidate AP. Every temporary NetworkManager
profile was deleted and `wlan2` was left disconnected.

The final candidate is clean source
`0ecf9c170384fd2cc3ba802515e1d2c1396ab9fa`, embedded firmware identity
`0ecf9c170384`, and UF2 SHA-256
`6261e322884a280afcd997537d6248fbbf0033b879fab1b2a661acd3a3575e23`.
It was built with pinned Pico SDK 2.3.1, clean BTstack
`eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec` and picotool
`6f6458d792b93685a11423b244a585eaa99eafcf`. The UF2 is 2,699,776
bytes; the ELF reports 1,367,880 text bytes and 134,560 BSS bytes. The standard
image and provisioning, field-access and RF-driver linkchecks passed.

## Preserved failures and repairs

Three candidate failures were retained rather than replaced by a later pass:

1. `46e21069ac2a` associated to WPA2 but issued no DHCP lease. The pinned SDK
   did not include its optional DHCP utility. Commit `9bd0d7057128` added a
   bounded, AP-netif-bound project-owned DHCP server derived from the MIT
   Raspberry Pi `pico-examples` source, checked startup and packet/pool tests.
2. `9bd0d7057128` then passed DHCP and mDNS, but HTTPS refused connections. The
   provisioned image had started both its TLS listener and blank bootstrap
   listener despite having only one configured listen PCB. Commit
   `45d0a9215e3a` made the plaintext listener exclusive to the truly
   unprovisioned surface.
3. `45d0a9215e3a` passed identity, certificate, fresh password, cookie and
   status checks, but three controller-time attempts were correctly rejected as
   over budget. Separate TLS handshakes made challenge-to-submit round trips
   1.46--1.73 seconds, which could not meet the unchanged 500 ms maximum
   uncertainty. Commit `0ecf9c170384` keeps only that immediate authenticated
   challenge/submit pair on one TLS connection. All other HTTP responses retain
   their one-request/close behavior.

The final repair passed a source-focused adversarial review for mutation
ordering, parser reset, session continuity, response acknowledgement, timeout,
resource release and accidental general keep-alive. A challenge response is
committed only after full TCP acknowledgement; only then is the request parser
securely reset for the paired submit. The existing 15-second connection
deadline remains in force.

## Final physical results

Picotool serial-targeted Candidate A, verified every programmed block and
reported `OK`. The new image preserved factory profile generation 0, healthy
access generation 3, default-password state, station `AA0NT/EM18/20`, the
120/0 schedule, watermark `1789607761000000000`, configuration journal
sequence 72 and watermark journal sequence 12. The engine remained
`inhibited-standalone-simulator`; the job state remained empty and unowned with
`output_active=false`.

The final-candidate SoftAP results were:

| Assertion | Result |
| --- | --- |
| WPA2 association to the exact SSID/BSSID | PASS |
| DHCP address/gateway | PASS: `192.168.4.16/24`, gateway `192.168.4.1` |
| AP-interface mDNS | PASS: the certified hostname resolved to `192.168.4.1` |
| Server identity and trust scope | PASS: TLS 1.3, `http/1.1`, process-local CA file only |
| Wrong password and cross-origin login | PASS: rejected without a session |
| Correct current-password login | PASS |
| Cookie policy | PASS: `Path=/; Secure; HttpOnly; SameSite=Strict` |
| Controller-time pair | PASS on native Pi only: one TLS connection, 277,132,467 ns; repeated at 277,595,784 ns |
| Post-time surface and clock | PASS: normal surface and synchronized clock |
| Existing local API | PASS: identity, status and capabilities |
| Existing `JobService` | PASS: `HELLO`, `CLAIM`, `RELEASE`; no `LOAD` or `ARM` |
| Logout | PASS: server session invalidated and cookie cleared |
| Bounded disconnect/reconnect | PASS: DHCP, mDNS and HTTPS recovered |
| Resource return | PASS: zero allocator/TLS allocation failures; TCP PCB, segment and packet pools returned to zero current use |

The successful controller sample reported 307,049,485 ns uncertainty. It is a
native-Pi control-path check, not iPhone phone-time acceptance. No private key,
cookie token, custom password, raw access sector or authenticated packet was
placed in Git.

## Restoration and its exact limitation

The test session logged out, released WTP ownership, removed every temporary
NetworkManager profile, disconnected `wlan2` and rebooted Candidate A. Final
boot `889776ed08c5da0743cfa62b224062ac` was unsynchronized as expected after
restart, with BLE running but disconnected, both journals healthy, an empty
unowned job and inactive output. The comparator was untouched.

The AP-stop row cannot pass on this preserved factory configuration: the
station network remains unavailable, so the selected contract deliberately
starts automatic SoftAP fallback. Scans after restoration observed that
fallback SSID. This is not evidence that the transient join-grace survived
reboot, and it is not repaired by weakening the required fallback behavior.
The exact row is `NOT_MET_PREREQUISITE_STATION_UNAVAILABLE`; a later run with a
usable committed station profile must prove 30 seconds of station stability and
then AP withdrawal. The candidate is otherwise restored to the standard
RF-inhibited image and preserved persistent state.

## Validation and reassessment

The final source state passed:

- the 87-test aggregate CTest suite with the retained Xcode SDK selected;
- the focused ASan/UBSan network, DHCP, mDNS, field-access, SoftAP and Pico
  adapter tests;
- the WTP validator, browser/release/contract helpers and Console helper tests;
- exact standard-image and three RP2350 cross-links with image, heap-hook and
  stack-guard post-link checks; and
- formatting, JSON parsing, changed-link target and whitespace checks.

A control aggregate run without the required Xcode `SDKROOT` retained the
known Command Line Tools 27 malformed `arm64e.x1` text-stub failures in three
tests. Repeating the same 87 tests with the documented Xcode SDK passed 87/87;
the toolchain failure was not treated as a product failure or hidden.

The final adversarial assessment found no further actionable production defect
in the implemented SoftAP boundary. It found and repaired one stale test
assumption: the real-lwIP mDNS exhaustion test still allocated the old fixed
number of IGMP groups after the AP pool expansion. It now fills the configured
pool dynamically, proves `ERR_MEM`, checks unwind and releases every temporary
membership. The reassessment also found that the original restoration wording
assumed a usable station and therefore could not coexist with mandatory
station-failure fallback on this candidate. The result now records that row as
unmet instead of falsely claiming the AP stopped.

## Remaining Phase 12 gates

Phase 12 remains open for exact iPhone/iOS/Bluefy identity; verified offline
page reuse; a fresh phone password exchange; full credential transfer and
delivery-safe activation; iPhone time and visual LED checks; blank generic HTTP;
BLE simulated-job execution; SoftAP credential/reset administration, which is
not implemented; password/bond/reset recovery; fault, trust-replacement,
concurrency and soak matrices; and AP withdrawal after a usable station profile
is stable. Stage B and every RF-output assertion remain separate.
