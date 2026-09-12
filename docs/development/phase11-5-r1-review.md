# R1 execution and adversarial review

**R1 remains BLOCKED: 1 of 5 assertions passed, 1 blocked, 3 not run.** The
[execution prompt](phase11-5-r1-prompt.md) was implemented and executed within
R1. The [machine-readable result](phase11-5-r1-result.json) preserves both
attempts, exact images, raw evidence hashes and restoration. No RF job ran;
Phase 11.5 remains 0/6 revised families closed, with no accepted configuration.

## What ran and what failed

The first attempt stopped before any device mutation because both Picos had
new boot IDs. The user confirmed rebooting them between campaigns. Read-only
inventories showed their original inhibited firmware/configuration, empty and
unowned state, inactive output and zero reported firmware faults. A fresh
attempt used those exact boots, preserved the first failure, and shared the
existing host fixture without extending its cleanup deadline.

The second attempt backed up A, installed the exact inhibited e20ae8b image,
wrote the isolated Wi-Fi settings and performed the planned configuration
reboot. A associated and obtained `10.77.15.10`, but time-server name resolution
did not complete within the frozen readiness interval. At 64.376732 seconds
uptime it reported two resolution failures, `ntp_address:""`,
`ntp_resolution:"resolving"`, and an unsynchronized clock. The inhibited boot
was `8f7f208c8eaf639c18f78b7e1feedd2d` at 150 MHz. There were no allocator or RF
workload intervals. The physical image and three allocation probes were not run.

The dnsmasq log records A's queries and its configured `10.77.15.1` answer. A
subsequent native Linux client query also timed out after three seconds; that
query had no packet capture. A later bounded capture showed host-local and
native-client queries succeeding, with matching DNS IDs, valid UDP checksums
and the correct answer on AP/client captures. Host filtering had no nftables
rules and the reply route used wlan0. These observations establish an
**intermittent DNS/readiness failure with unresolved cause**. They do not prove
whether the earlier replies left the AP or reached the Pico, or establish a
firmware defect. The later success does not pass the earlier failed attempt.

The host fixture existed approximately 15:19:51–15:34:43 UTC on September 12,
2026. Device work in the second attempt ran approximately 15:25:40–15:27:37 UTC.
The original 80-minute outer cleanup bound was not extended.

## Assertion accounting

| Assertion | Result | Evidence or remaining work |
| --- | --- | --- |
| R1.1: four exact layouts | PASS | Reused and rechecked all four e20ae8b ELF/UF2 pairs; allocator hooks, stack startup/readbacks, heap separation and reserved flash passed. |
| R1.2: changed-path inhibited regression | BLOCKED | Readiness failed before N180/USB240. Source regressions pass, but do not replace the missing target workload. |
| R1.3: necessary allocation/failure recovery | NOT RUN | No heap probe executed. |
| R1.4: matched physical Q/controller/N/Q | NOT RUN | No physical boot or comparison in this attempt. |
| R1.5: observer cost in the matched baseline | NOT RUN | Earlier exact-image stress evidence is contextual; the new baseline did not run. |

"Blocked" describes R1 readiness. Both raw supervisor attempts remain `FAILED`;
their results have not been rewritten as successful tests.

## Artifact and measurement boundaries

The unchanged firmware source is
`e20ae8bea2d5237af017dbd5f73bfe9332ce144e`. Public hashes and map checks are in
[the result](phase11-5-r1-result.json). The four variants are **network control
listener off/on** (`WSPRRY_PICO_NETWORK_PORT=0/18443`), not removal of all Wi-Fi
or SNTP code. Linked general-heap capacities are:

| Image | Listener off | Listener on |
| --- | ---: | ---: |
| Inhibited, 150 MHz | 377,572 bytes | 377,512 bytes |
| Physical, 138 MHz | 218,432 bytes | 218,380 bytes |

Core 0 reserves 16 KiB; the physical worker has its own aligned 16 KiB BSS
stack below the heap. Both physical startup routes enforce a 4,096-byte MSPLIM
reserve. The changed CYW43 common-send frame is 2,120 bytes in the frozen linked
image. Preserve the previously reviewed SDK 2.3.1/Arm GNU 15.3.1 and dependency
identities bound to these exact artifacts; no firmware was rebuilt here.

Physical selection remains 138 MHz, divider 1, RAM renderer. Its full-block
interval is 3,799,188.406 ns and the existing 75% budget is 2,849,391 ns. R1 does
not test refill/launch deadlines. Physical 132/150 MHz remain untested; selecting
another clock during 11.6 requires the affected 11.5 checks.

Re-analysis of the earlier e20ae8b stress diagnostic gives 58.150913 seconds
summed allocator sample time over 359.000921 observed seconds (16.198% of that
elapsed interval), maximum sample/entry times 57/158 microseconds, core-0 scan
136 microseconds and core-1 probe 315 microseconds. These overlapping observer
metrics are reported separately, not summed into an RF timing budget or described
as an exact CPU profile. Its 118,532-byte allocator peak and canary touched
extents of 8,248/544 bytes remain limited to that earlier idle stress run.
They are not new R1 normal-workload results or exact stack-pointer maxima.

## Tooling implemented and review iterations

- Added a distinct N profile in the Pi load driver. For 180 seconds, Refresh
  offsets are 20/40/60/100/130/160 and reload is at 90. For 300 seconds, Refresh
  offsets are 30/70/110/190/230/270 and reload is at 150. Both begin with the
  actual embedded page and capabilities/status/config initialization. Each has
  eight actions and fourteen sequential GETs. Legacy S remains unchanged.
- Recorded action start/finish, constituent responses, per-request deadlines and
  whole-action latency. N permits at most 15 seconds action-start lateness,
  15 seconds per request, and 60 seconds for four-request initialization/reload;
  every action must finish within the declared interval. This is source-matched
  HTTP load, not visual browser-UI qualification.
- Added an explicit closed candidate registry for e20ae8b while preserving the
  old candidate. Original-image/config, boot, guard, endpoint exclusivity,
  operation budgets and restoration checks remain in force. Shared R1 host
  fixtures require their original packet hash and unchanged cleanup deadline.
- Added an explicit reconciliation path for user-confirmed between-campaign
  reboots. It requires hash-bound original idle configurations and zero reported
  faults; an in-run boot change still stops the campaign.
- Added the bounded R1 executor, resource comparisons and offline raw audit.
  The historical 20-case register/validator remain unchanged.

Adversarial iteration 1 caught an INFO/WTP distinction in resource aggregation:
terminal history is available in independent WTP STATUS, not Console INFO.
The aggregator was repaired before device execution, replayed against preserved
raw evidence, and covered by a regression that rejects nonempty history.

Iteration 2 exercised missing/extra/reordered/late actions, wrong firmware and
boot identities, foreign ownership, changed saved configuration, guard admission,
quiet-state differences and retained growth. It also exposed missing validation
of browser initialization response content; the offline auditor now checks page
assets, API initialization, idle authority and browser peer identity. These
post-attempt audit checks do not claim that the blocked workload executed.

Iteration 3 addressed the readiness discovery: future R1 executions now perform
one recorded native-client DNS positive control **before any device mutation**.
Wrong transaction IDs, answers, source addresses, error responses, truncation
and deadline violations are rejected without retry. This closes the missing
preflight check; it does **not** fix or close the intermittent DNS cause, and
has only hardware-free validation in the committed R1 executor. A fresh reviewed
packet is required for another execution; the preserved packet hashes describe
what actually ran.

Final adversarial disposition: no remaining actionable tooling finding was found
in this scoped review. The unresolved live readiness failure is explicitly open,
and the full R1 auditor rejects these failed attempts rather than awarding a pass.

## Validation

- `python3 -m unittest discover -s tests -p 'phase11_5_*tests.py'`: 102 pass.
- Five affected CTest groups, including the registered R1 suite: all pass.
- Pi `python3 src/tests/phase115_production_load_tests.py`: 10 pass.
- Five pinned real-source CYW43 regressions: all pass; original corruption is
  reproduced and the fixed source preserves payloads and error semantics.
- All four unchanged ELF/UF2 pairs match prior hashes and pass linked image,
  allocator-hook and stack-guard checks.
- The complete R1 auditor rejects the actual failed R1 evidence. Public packets
  match archived execution bytes; result counts, JSON, relative links and diff
  whitespace checks pass. A successful end-to-end R1 audit still requires the
  missing target run.

## Restoration and next action

Fresh final USB inventories confirmed:

- A: original inhibited `802c91a7b86e-dirty`, boot
  `36889c374d905eb63896157976503614`, empty/inactive/unowned.
- B: original inhibited `dbf1d86f0885-dirty`, boot
  `feffcd075ab6cb0b74e7e0c2fde6c87f`, empty/inactive/unowned; unchanged during R1.
- Both original configurations were preserved. Cumulative counts are config
  **24/32**, Wi-Fi OFF/ON **0/0**, heap probes **0**. Eight configuration writes
  remain; reserve future schedule/rotation and restoration writes.

Host cleanup restored wlan0/wlan2 to disconnected state, removed the fixture
subnet/namespace and chrony ACL, resumed the recovery timer and preserved Ethernet,
wlan1 and installed WsprryPi PID 1957. GPSDO and RF settings were unchanged.

Next: diagnose the intermittent startup reply failure with simultaneous AP/client
capture and a native DNS positive control before admitting another device packet.
Keep firmware e20ae8b frozen unless target evidence demonstrates a defect. Once
readiness is established, execute the still-missing inhibited and physical R1
intervals/probes. Do not expand into R2-R6 or a band/clock sweep.

Documentation Impact: updated the R1 prompt/packets/result/review, coordinating
plan/ledger/development index and Pi companion review. Operator workflows,
firmware, WTP/browser API contracts and third-party documentation repositories
were not changed. All captures, credential-bearing firmware, keys and private
configuration remain outside Git; archive hashes are in the result.
