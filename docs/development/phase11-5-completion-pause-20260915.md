# Phase 11.5 pause for app update

Execution is paused at the user's request. Resume only after the user returns.
The standing completion authorization remains in
`phase11-5-completion-authorization-20260915.md`. Do not start an automation.

## Acceptance and repository

- Phase 11.5 OPEN. Package 0 complete. R1 closed 5/5 and R2 closed 7/7
  in their recorded applicability. R3–R6 remain open.
- Package 1 components 2.1a, 2.1d and 2.1e have accepted evidence on e64ebb9.
  No additional acceptance family closed during the latest work.
- Latest published HEAD on devel:
  `6b7a1b848e2b5192acaa0fa08fb778613457ad8b`.
  Push and independent remote parity were verified at that checkpoint.
- HTTP request bodies now use bounded pages. Seven affected CTest groups,
  TLS integration and altered failure-evidence checks passed. Both target images
  built with the existing SDK/toolchain; the physical image was deployed to A.
  Target maximum HTTP acceptance remains pending.
- Six tooling/test files remain modified and uncommitted: the native-idle
  runner and auditor, completion deploy helper, R3 RF runner, RF reservation
  tests and R3 RF tests. Preserve these edits. They are not a completed checkpoint.
- WsprryPi remains read-only and its working tree was verified clean at pause.

## Retained hardware and accounting

A: USB `0BF4B4AEC9FFB344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`,
source 6b7a1b8, boot `1739cc4f28304080ec97e2b228ab2683`.
Physical ELF SHA-256:
`230148e95ded1bfb8ad05f75dedf0283d3efb3eac85d4356b5a2684c7b666aed`.
UF2 SHA-256:
`b4bca5320dcad489a8dcf1f471003c3cc0c33c2a819dc59257f4a9b9b00b9423`.

B: USB `CDDBF8767C506C07`, device `29f20b7342051ef947aa56cb9d4fab42`,
source `8921a70081839f168edef5926e92445f251d8e1d`,
boot `6684b4b197d80cfa0ce83b3aaf205cb0`.

Cumulative charges: 5 RF jobs / 640 planned RF seconds; 7 A flashes and
7 BOOTSEL transitions; 2 idle Wi-Fi OFF/ON cycles; 0 additional controlled
reboots; 0 configuration writes. One historical unplanned watchdog reboot is
recorded separately. Pause cleanup adds no RF, flash or configuration write.

## Pause restoration evidence

The host fixture at
`/home/pi/phase11-5-completion-http-pages-capacity-fixture-20260915`
was explicitly cleaned up with the existing ownership-aware cleanup helper.
The cleanup command exited successfully. Its deadline must never be extended
or reused for another packet.

Final verification is recorded locally, outside Git, in
`build/phase11-5-completion-20260915/pause-result.json` and on wspr5 in
`/home/pi/phase11-5-completion-native-idleh-20260915/pause-result.json`.
Consult that result for actual verified board, configuration, schedule and
host restoration state. Raw inventories remain on wspr5 as `pause-a.stdout`
and `pause-b.stdout`; the local result contains sanitized identities and hashes.

## Exact next work after resume

1. Refresh working trees, identities, reservation and host baseline. Create a
   fresh finite fixture session with independent cleanup; the paused fixture
   is finished. Do not flash A again for a harness-only repair.
2. Repair native-idle failure cleanup before another run. Its current finally
   block sends cleanup ABORT/CLAIM/RELEASE even when admission failed before
   acquiring the reservation. Only perform owned mutation cleanup when held;
   for preflight failure, read final inventories without taking ownership or
   releasing a reservation never acquired. Preserve the original failure.
   Add an offline regression proving no control/acquire/release on rejected
   preflight, including foreign active authority.
3. Verify the uncommitted LoadedObservationGate: scope v8 requires two fresh
   matching Loaded publications at least one second apart before ABORT, with
   the original three-second minimum dwell and six-second freshness limit.
   Do not relax native response/freshness deadlines.
4. Test the native auditor's newly refactored explicit expected-packet-SHA
   parameter. Its default retains the old native-idlef positive audit. Use the
   private old evidence plus mutation tests before a new physical run.
5. Prepare native-idlej in a fresh root and packet, after the repaired harness
   passes offline review. Native-idlei never froze a packet: staging refused
   because the previous fixture's full execution/cleanup budget no longer fit.
   Use a fresh inventory for initial terminal IDs and their actual newest-first
   order; records can expire while paused. Never assume creation order.
6. Audit nativej on wspr5 independently from raw records. Only after a pass and
   fresh inactive reconciliation, prepare the affected maximum HTTP/RF packet.
   The uncommitted RF policy pins source/image/boot and exact retained IDs;
   review its allowed retained counts against actual inventory before execution.
7. Audit and preserve nativeg/h failures, update current progress/matrix and
   checkpoint tested tooling with the authorized commit/push/parity sequence.
   Then continue Packages 1–9 under the original finite authorization.

## Failed attempts to preserve

- Native-idleg packet
  `25721d44850d980aec375ab336b338a95e82451481b1c89cadeede062223db22`:
  two maximum idle LOADs, zero RF; native monitor freshness failure. Firmware
  stayed healthy. Raw native STATUS responses support a sampling-gap diagnosis,
  not proof of an exact historical application branch. Fixed dwell allowed
  ABORT before the monitor observed the second Loaded state.
- Native-idleh packet
  `8821bc47bc83f4448c2469dd0301ba60a4fb790d2261c4e7d24785e08134e7cd`:
  initial terminal order mismatch; no main LOAD/RF. The unowned cleanup issue
  above means zero main counters do not prove zero cleanup commands. Audit raw
  records before publishing exact cleanup counts. Reservation was never acquired.
- Native-idlei: staging refusal only; no packet.json and no runner/device access.
- Earlier P1h maximum HTTP request was fully written but produced an allocation
  failure and watchdog recovery. Its committed immutable failure audit remains
  valid. The paging repair has not yet earned target HTTP acceptance.

Host raw evidence roots use
`/home/pi/phase11-5-completion-native-idle{f,g,h,i}-20260915`.
Local preparation/evidence lives under
`build/phase11-5-completion-20260915/native-idle{f,g,h,i}`.
Prefer independent audits on wspr5 and retrieve sanitized results/hashes.
Use only the declared authenticated lab paths; do not collect credentials,
unrelated traffic/files or transfer lab payloads to external services.

Historical accepted native-idlef packet:
`ac6623b5ab72ed98ae0ee4230a054f75c00afc0a8fe1e7c37f4517da2d30dab1`.
It remains a bounded idle regression pass on b0254c5, with 32,800-byte observed
headroom against the unchanged 32,768-byte reserve. The new candidate's static
heap changed by 16 bytes, which is the source-impact reason for the affected
retest. Preserve earlier evidence; do not promote it to full combined capacity.
