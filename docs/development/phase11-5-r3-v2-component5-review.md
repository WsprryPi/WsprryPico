# Component 5: bounded target attempt and observer correction

The repaired firmware was built from clean source `e256633304e03ab85998fde947360ccbaab6c68e`
and installed on Pico A. The E6 preparation LOAD returned all 512 adjustments,
and its Aborted terminal record survived the required 310-second aging period.
The attempt then stopped on a defect in the host INFO observer, before the exact
C7 primary LOAD. **No new Group 2 acceptance assertion closed.**

The [authorized scope](phase11-5-r3-v2-component5-scope.md) and
[result with evidence hashes](phase11-5-r3-v2-component5-result.json) preserve
this attempt. No second physical attempt was made after repairing the observer.
The remaining primary/replay and sustained-pressure checks need a separately
bounded continuation; the consumed flash allowance must not be silently reused.

## Observed result

One BOOTSEL and one flash installed the existing shared-adjustment repair.
The candidate used Pico SDK 2.3.1, GCC 15.3.1, Pico 2 W / RP2350 Arm,
138 MHz GP2 PIO/DMA and RAM rendering. Heap hooks, stack guards and the
660-byte RAM renderer passed their linked-image checks. Linked heap capacity
is 219,712 bytes. UF2 SHA-256:
`b2983da197de0462f3ef4288355dc4b5ce5fe349b0b98d526dce0d6e526a9288`.
ELF SHA-256:
`1381fd45d2d79d1415963e70f368794c479b34110cc6fa4f6ea160ae8874489b`.

The preparation request wrote all 53,413 framed bytes. Its successful response
payload contained 54,916 bytes and completed in 2.458091 seconds, including the
request write. ABORT/RELEASE succeeded. After more than 310 seconds, raw STATUS
confirmed Empty/inactive/unowned and exactly the retained E6 Aborted job.
This preparation reply is useful evidence, but it precedes the TLS observer
and is not the exact C7 primary request under combined pressure.

The first INFO sample reported `launch_epoch` as the decimal string `"0"`.
The runner incorrectly compared that field with integer `0`, making its
`Idle counters/faults` check fail. The raw sample shows:

| Measurement | Observed value |
| --- | ---: |
| Allocator failures / TLS allocation failures | 0 / 0 |
| Launch epoch / DMA / alarm / tail IRQs | 0 / 0 / 0 / 0 |
| Fault stage / hash / PC / status | 0 / 0 / 0 / 0 |
| TLS allocated / peak bytes | 31,384 / 34,884 |
| Sampled heap allocated / available bytes | 55,776 / 163,936 |
| Allocator live / peak bytes | 59,128 / 112,920 |
| Core 0 / core 1 stack usage | 8,700 / 940 bytes |

A mutually authenticated TLS 1.3 WTP connection completed HELLO. Its first STATUS
was interrupted by cleanup after receiving its response header; this does not
establish a TLS STATUS timeout or firmware refusal. No HTTPS request, primary
LOAD or replay was sent. The single TLS allocation sample matches the historical
31,384-byte value, but there is no primary LOAD pressure bracket or sustained
combined-load acceptance. No target allocator failure was captured.

The original `run-result.json` remains FAILED, including its original observer
and final-authority errors. The frozen runner and auditor are retained with hashes
beside the raw private evidence. Offline analysis reconstructs the complete raw
INFO that the original runner rejected before emitting its decoded summary.
The corrected checker accepts that sample; it does not rewrite the run as PASS.

## Review findings and repairs

1. **Console counter type mismatch:** handle the documented decimal-string
   representation of the two uint64 counters. Tests accept the captured zero
   representation and reject nonzero counters, faults, inadequate reserve,
   invalid guards and excessive stack use. The same health check now runs on
   the post-flash inventory before retained-state preparation.
2. **Lost decoded failure sample:** emit the decoded INFO record before health
   validation. The auditor can reconstruct this historical complete raw sample
   without pretending the original observer accepted it.
3. **Final inventory coupling:** a failed A health check previously prevented
   B's final inventory. Separate the two checks and preserve each result. A
   hardware-free failure-path test proves B and fixture cleanup still execute.
   The actual attempt received separate post-restoration read-only A/B checks.
4. **Cleanup exception handling:** retain network-termination errors and continue
   restoration; a fixture cleanup error now makes the result FAILED. These
   changes were not deployed into the already completed physical attempt.
5. **Audit completeness:** reconstruct inventory bytes with the existing strict
   inventory auditor, bind reply labels and write counts, validate preparation,
   preserve operation counts, check the successful schedule and Loaded identity,
   and require a recorded clean fixture teardown. Supplemental inventories are
   explicitly named and do not replace failed original records.

Reassessment reproduced the original failure with the frozen runner against the
actual raw sample, then passed the corrected health check. Fifteen altered-evidence
cases were rejected: false success, primary count, reply summary, write count,
USB bytes, hidden operation, truncated journal, sequence, packet binding, extra
flash, final A authority, B identity, TLS identity, TLS bytes and fixture cleanup.
The unmodified capture remains `LOAD_REPLY_TARGET_FAILED` with zero primary,
replay and RF counts. No remaining actionable finding was identified in the
stopped-run diagnosis and cleanup evidence. The corrected runner's full physical
success path remains unperformed; offline tests do not qualify it.

## Validation and source impact

Eight affected CTest targets pass: inventory, network fixture, device fixture,
fixture audit, time.local, LOAD reply, LOAD target and core tests. The new runner
suite has seven cases. The evidence-dependent suite has two cases, including
15 alteration subcases. Raw audits and their tests use private evidence and
require no device or network access:

```sh
python3 tests/phase11_5_load_reply_target_tests.py
python3 tests/phase11_5_load_reply_target_audit_tests.py \
  --evidence build/phase11-5-r3-group2-component5/evidence
python3 scripts/audit_phase11_5_load_reply_target.py \
  build/phase11-5-r3-group2-component5/evidence \
  --output build/phase11-5-r3-group2-component5/audited.json
```

Only host tooling, tests, CTest registration and records changed after deployment.
Production firmware source, protocol, RF code and memory reserves remain at
`e256633`. No broader physical family was rerun or credited from this result.
Generated images, credentials and raw captures remain outside source control.

## Final state and remaining work

Independent verification completed 1,294.449 seconds after the original period
start, within its unchanged 3,600-second bound. The fixture was restored before
the separate final inventories. Temporary units/namespace/subnet are absent,
radio power-save settings and the recovery timer are restored, and protected
host files, management addresses and services are preserved. The installed
WsprryPi PID remains 1957 with its original executable hash.

Pico A remains source `e256633304e0`, boot
`11dac3985326cb81c49022efcdceb5d4`. Pico B remains source `8921a7008183`, boot
`6684b4b197d80cfa0ce83b3aaf205cb0`. Both independently report Empty, inactive,
unowned and scheduling disabled; saved configuration is preserved. A retains
the E6 Aborted record. No ARM, RF output, extra reset, Pico configuration write
or Pico Wi-Fi command occurred.

Next is one newly bounded continuation using the corrected observer and the
already installed exact candidate, after fresh admission and retained-state
verification. It must explicitly account for recreating the terminal baseline,
cache aging, fixture duration, primary LOAD and conditional replay limits; the
stopped attempt cannot simply be restarted. C7's historical failure, broader
capacity/pressure, timeout, USB-pressure, RF and reclamation gates stay open.
