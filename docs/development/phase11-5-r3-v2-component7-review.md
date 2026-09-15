# Component 7: primary LOAD reply verified; replay reserve gate remains open

The authorized Wi-Fi recovery succeeded. The exact C7 primary LOAD now returns
its complete successful reply on the repaired firmware under measured TLS
pressure. The overall bounded validation remains **FAILED**: during the first
identical replay, allocator peak headroom fell below the unchanged 32-KiB reserve.
The replay response and fresh-ID replay are not qualified. No RF ran.

The [scope](phase11-5-r3-v2-component7-scope.md) records the user's authorization
and report of an unrelated external router reset. The
[result](phase11-5-r3-v2-component7-result.json) contains exact identities,
measurements and private-evidence hashes. Prior failures remain preserved.

## Physical result

A remains on clean source `e256633304e03ab85998fde947360ccbaab6c68e`, boot
`11dac3985326cb81c49022efcdceb5d4`, Pico 2 W / RP2350 Arm, 138 MHz GP2 PIO/DMA
with RAM rendering. There was no new build, flash, BOOTSEL, reset or CONFIG write.

The old E6 terminal record had expired. Fresh admission verified the same
firmware/boot and empty terminal history. One Console WIFI OFF/ON cycle completed
with raw acknowledgments and restored network enablement. One replacement
512-event E6 LOAD completed; ABORT/RELEASE and at least 310 seconds of request-cache
aging established the required retained state. Two fresh INFO samples confirmed
link up and address 10.77.15.10 before the authenticated TLS observer started.

| Check | Observed outcome |
| --- | --- |
| Exact primary request | All 52,105 framed bytes written; original C7 SHA-256 matches |
| Primary response | Valid framing, CRC, schema, identity and all 512 expected adjustments; 54,916-byte payload |
| Total primary exchange | 2.175230900 seconds, including the request write |
| TLS allocation around primary | Four nearby samples, all 31,384 bytes; matches the historical comparison value |
| First identical replay | All 52,105 request bytes written; observer stopped before the response completed |
| Fresh-request-ID replay | Not sent |
| Network observations | Persistent authenticated TLS/WTP; one successful HTTPS status GET before stop |
| Independent INFO observations | 35 complete samples; remaining observation period stopped on the reserve gate |
| Allocation failures / TLS allocation failures | 0 / 0 |
| RF, firmware writes and Pico configuration writes | 0 |

The first replay was interrupted before its five-second deadline. This is not a
measured reply timeout or proof that the endpoint closed. The primary response
is directly verified; the shortened post-LOAD observation and incomplete replay
checks prevent full regression acceptance.

## Memory evidence

Linked heap capacity is 219,712 bytes. The captured allocator peak is 190,424,
leaving **29,288 bytes**, **3,480 bytes below** the required 32,768-byte reserve.
The failing INFO sample's current sampled heap availability was 55,600 bytes;
current availability and historical allocator peak are different metrics. A
later decrease in live allocation does not erase the recorded peak excursion.

| Seconds from primary start | Sampled heap allocated | Allocator live | Allocator peak | TLS allocated |
| ---: | ---: | ---: | ---: | ---: |
| -0.324 | 67,848 | 71,208 | 116,976 | 31,384 |
| 0.699 | 120,256 | 123,616 | 125,304 | 31,384 |
| 1.698 | 164,896 | 168,256 | 169,944 | 31,384 |
| 2.706 | 161,288 | 164,648 | 174,976 | 31,384 |
| 3.745 | 164,112 | 167,472 | 190,424 | 31,384 |

The primary reply finished at +2.175 seconds. The replay started at +2.260 seconds
and finished writing at +3.101 seconds. The reserve failure was observed at
+3.745 seconds. These samples locate the excursion in the replay stage; they do
not identify an exact allocation call or measure every transient allocation.
No allocator NULL, fault PC or allocation-failure record was produced.

A concrete source lead is `codec.cpp`: decoding LOAD materializes a vector of
512 `json::Value` views while input pages and the decoded Job's event vector
coexist. The active job is also retained during replay. Investigate this lifetime
with a complete replay-stage allocation model; the captured peak site is not yet
proven. No speculative firmware repair or extra physical attempt was made.

## Review and reassessment

The recovery runner binds one OFF/ON cycle into a new explicit scope, charges
commands before writing, and attempts ON in a finally path if OFF's acknowledgment
is lost. Admission allows one replacement preparation only when selected from
fresh empty-history evidence. The original hour and cleanup reserve remain fixed.

Independent auditing reconstructs Wi-Fi commands/replies, retained preparation,
USB writes and responses, TLS/HTTPS observations and final inventories. Review
added explicit USB event-boot, STATUS-authority, CLAIM-owner and label/operation
checks. Those additions do not change captured firmware or alter the failed run.

The original auditor raised on the recorded reserve failure and could not finish
reporting authoritative cleanup. It now records that specific health finding only
when the run is FAILED and the original observer recorded the matching reason.
It still rejects unexplained failures and cannot award PASS with a reserve finding.
Stack validation now precedes the reserve check, so acknowledging a known reserve
failure cannot hide a stack fault. The original raw result remains unchanged.

Eight affected CTest targets pass, including 12 runner cases. The original C8
and C9 evidence suites still reject their 15 and eight altered cases. The new
recovery suite has three cases: it verifies the complete primary and preserved
reserve stop, keeps a lower-pressure altered trace FAILED, and rejects 18 evidence
alterations. These include validly reframed wrong adjustments, request/job identity,
active STATUS, wrong owner, allocation/stack faults, premature aging, extra Wi-Fi
or flash counts, altered final authority, TLS/HTTP corruption, cleanup failure,
removed failure reason and attempted promotion of the failed result.

Reassessment found no remaining actionable defect in the recovery tooling or this
stopped-run audit. The real replay-stage reserve excursion remains an open product
finding. Firmware source, protocol, RF implementation and reserve thresholds remain
unchanged. Raw captures, credentials and generated firmware remain private.

```sh
python3 tests/phase11_5_load_reply_recovery_audit_tests.py \
  --evidence build/phase11-5-r3-group2-component7/evidence
```

## Final state and next work

Independent final verification completed 749.496 seconds after the original
period start. The host fixture is restored; protected files/services, management
addresses and radios match the baseline. Installed WsprryPi PID 1957 and its
executable hash are unchanged. Both Picos independently report Empty, inactive,
unowned and scheduling disabled, with unchanged configuration. A retains the
new E6 and C7 Aborted records. B remains source `8921a7008183`, boot
`6684b4b197d80cfa0ce83b3aaf205cb0`.

The next software step is to reproduce the fully written replay's peak through
the production parser/decoder/service/encoder and reduce the demonstrated lifetime
cost while preserving the reserve. A subsequent authorized target check must
complete both replay replies and the full observation period. The exact primary
response has new physical evidence; full LOAD-regression and broader Group 2
RF/capacity/timeout/USB-pressure/reclamation closure remain open.
