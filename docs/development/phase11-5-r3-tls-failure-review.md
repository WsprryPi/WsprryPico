# R3 A1 pre-job failure and observer repair — September 12, 2026

The approved A1 attempt **failed in the test tooling before any RF job was
submitted**. This was an implementation and review error, not a target or WTP
protocol failure. The pressure driver treated Console INFO's nested scheduler
status as a WTP STATUS body and accessed `job_id`, which Console INFO does not
supply. The same assumption appeared in the synthetic tests and offline pressure
audit. The earlier preparation assessment was therefore insufficient.

The documentation lacked a direct INFO/STATUS field comparison, which is now
added, but the source and existing raw captures already showed the difference.
That documentation gap does not excuse the implementation error. The repair uses
recorded responses and tests the actual pre-job wait, not just a synthetic shared
status object. No firmware or WTP wire contract change is needed.

## Executed scope and result

The user explicitly approved the [exact packet](phase11-5-r3-tls-execution.md)
and reconfirmed the documented 60 dB conducted wiring. Packet SHA-256:
`cab1abf2afffa27d79992b1d84bf393a2f1059ad3a4615829407485d695ca7a4`.
All 69 staged files were verified in the new private root
`/home/pi/phase11-5-r3-tls-a1-20260912`. The original packet, staged helper bytes,
raw logs and failed results remain unchanged. The approved packet is consumed
and must not be replayed. Its [prepared result](phase11-5-r3-tls-prepared.json)
remains a historical preparation snapshot.

The isolated host fixture started, both original board identities were admitted,
and A was flashed to the pinned inhibited image. CONFIG write 35 installed the
isolated network; the explicit configuration reboot and switch to the pinned
physical 2e43110/138 MHz/divider 1/RAM/listener-on image completed. Physical boot:
`57893aeefa99a6a3f19bcc5b4cabf773`.

The pressure driver failed with `KeyError: 'job_id'` during its first idle wait,
13.343 ms after its start record. The supervisor stopped the RF-off production
load and prevented dependent USB mutations. The independent observer finished
its original 360-second window and recorded the expected incomplete-job failure.
No retry, ABORT, replacement job or extra fault injection occurred.

| Evidence | Verified result |
| --- | --- |
| USB requests | HELLO and 72 STATUS requests only; no CLAIM, LOAD, ARM, RENEW, RELEASE or ABORT |
| RF counters | `launch_epoch`, DMA, alarm and tail counters remain zero throughout |
| Job/output state | All 72 WTP STATUS samples Empty, inactive, unowned, no job and empty terminal history; all 360 INFO samples Empty/inactive |
| Pressure trace | Start followed by the recorded KeyError; no case or TCP connection |
| Observation | 360 INFO, 72 STATUS, 72 host-health samples; maximum start gaps 1.000086669 / 5.000071370 / 5.000091127 seconds |
| Accepted R3 assertions / completed jobs | **0 / 0**; no physical contention acceptance credit |

The production client made its initial RF-off connection before termination.
Zero **pressure** connections does not mean zero network connections overall.
The run did not exercise the proposed TLS failure, timeout, slot or duplicate-WTP
cases. Idle-only resource observations do not establish those assertions.

## Restoration

Guarded restoration established authoritative idle before restoring CONFIG and
the original inhibited image. Final A revision `802c91a7b86e-dirty`, boot
`7a772a4eb283b23afdd1e25acbc449cd`; B remains revision `dbf1d86f0885-dirty`, boot
`feffcd075ab6cb0b74e7e0c2fde6c87f`. Both final raw-audited inventories are Empty,
inactive and unowned. Visible original configuration fields match. The existing
management helper verified the original CONFIG write against its pinned input;
this report does not invent a new post-restoration full-flash measurement.

Cumulative CONFIG is **36/36**, including setup and restoration. Heap probes
remain **six**, with no Wi-Fi fault cycles. Host cleanup passed, with identical
interfaces/routes and installed WsprryPi PID **1957**. Permanent time.local,
chrony/GPS-PPS/Avahi preservation checks passed. A's original inhibited image,
not the physical candidate, is left running. No additional hardware read or
operation was used to retry the failed pressure test.

## Repair and evidence checks

The pressure driver now treats each interface according to its actual fields:
WTP STATUS binds current job and owner; Console INFO binds boot, Running/output
state and the nonzero launch epoch. The epoch must advance for each job and stay
fixed across its pressure cases. The offline audit matches those epochs to the
raw-ARM per-job timing audit. It does not substitute standalone `last_job` for
the external USB/network job ID.

A checked-in fixture contains verbatim selected Console status/launch-epoch and
WTP STATUS fields from the previously raw-audited R2 2e43110 capture. It includes
Empty, Running and Complete states without invented Console job/owner fields.
Tests now run the pressure wait through idle, a previous job and both new launch
epochs, and reject stale/foreign observations and changed epochs.

The separate failure auditor reconstructs the original USB bytes and reported
samples, verifies zero RF counters, the exact pre-job failure, board inventories,
counters and host restoration. Its opt-in read-only failure classification
accepts only this expected incomplete-job observer termination and prohibits all
WTP mutations. The ordinary idle and physical acceptance paths still reject the
failed run. No raw evidence is edited to make an acceptance audit pass.

Checks performed:

- `PHASE115_R3_FAILURE_EVIDENCE=build/phase11-5-r3-tls-a1/evidence python3 -m unittest discover -s tests -p '*phase11_5*tests.py' -v`:
  **172 discovered; 170 passed; two unrelated private-fixture tests skipped**.
- The retained failure passes its failure-classification audit. Eleven mutations
  of raw observations, failure identity, output/counters, restoration and host
  cleanup are rejected; intact evidence passes again. The normal idle success
  audit rejects this failed trace.
- Fourteen R3 tooling tests pass, including the actual-shape pre-job wait and
  recorded Empty/Running/Complete response regression. Existing corrupted
  pressure and observer-identity cases remain covered.
- Documentation links, JSON and whitespace checks passed. No C++ or Pi runtime
  source changed, so those build suites were not repeated.

The [machine-readable failure result](phase11-5-r3-tls-failure-result.json)
records the raw archive hash and exact state. Private evidence is also retained
locally under `build/phase11-5-r3-tls-a1/evidence/`, with credentials and flash
images/backups excluded from that local archive.

## Impact and remaining work

| Change | Acceptance impact |
| --- | --- |
| Driver and pressure-audit observation binding | Repairs unexecuted R3 tooling; no firmware change and no invalidation of R1/R2 measurements |
| Recorded-response regression and failure audit | Verifies the tooling defect and preserved failed outcome; adds zero physical acceptance assertions |
| INFO/STATUS documentation | Clarifies existing implementation fields without changing WTP/1 |

Phase 11.5 remains **OPEN, 2/6 families closed**; R1 5/5 and R2 7/7 retain their
existing applicability. R3 physical assertions remain unrun, R4–R6 remain open,
and the accepted-configuration list is empty. Longer QRSS duration support is
still unresolved. The corrected pressure code has not been run on hardware.
A further physical attempt requires a freshly frozen packet and cumulative
allowance beyond 36, rather than replaying this failed packet or silently using
its unused RF seconds.

## Documentation Impact

Updated: this failure report/result, the current ledger/index, execution and
preparation-history notices, the INFO/WTP field reference, a cross-link from WTP,
and the Pi companion report. Historical packet bytes, prepared JSON and prior
results are preserved. Firmware, WTP schema, UI and separate operator manuals
are unchanged; no UI workflow or Impeccable review applies.
