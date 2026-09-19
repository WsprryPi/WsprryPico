# Phase 11.6 conducted RF acceptance

Status: **CLOSED — explicitly reduced acceptance scope.**

The authoritative row ledger is
[`phase11-6-matrix.json`](phase11-6-matrix.json). The immutable authorization
input remains [`phase11-6-closure-plan.json`](phase11-6-closure-plan.json), and
the executed v24 plan is
[`phase11-6-closure-execution-plan.json`](phase11-6-closure-execution-plan.json).
The independent packet audit and exact private-evidence hashes are retained in
[`phase11-6-closure-execution-results.json`](phase11-6-closure-execution-results.json).

Execution began from `origin/devel`
`f817fb79ddee50c690089b9964e39bcf0663a65f`. Fresh zero-RF admission matched
the required Pico A, Pico B, WsprryPi, receiver, helper, fixture, RF-path and
reservation identities. Sequence 176 then completed and passed independent
analysis. Sequence 177 failed the unchanged 10 ms pre-ARM settled-clock gate
after 95 seconds; it performed no CLAIM, LOAD or ARM, started no capture and
emitted no RF. The stop-on-first-failure runner reconciled both boards to
authoritative inactive state and released the shared reservation. There was
no retry. Both fixtures were restored to their recorded pre-run states.

## Authoritative matrix through sequence 177

The 75 rows contain 13 `PASS`, 9 `FAIL`, 12 `BLOCKED`, 31 `NOT TESTED` and
10 `UNSUPPORTED_CONFIGURATION` dispositions.

| Band | TONE | WSPR | QRSS | FSKCW | DFCW |
| --- | --- | --- | --- | --- | --- |
| 2200 m | PASS | FAIL | PASS | FAIL — sequence 177 timing admission | BLOCKED — replacement not reached |
| 630 m | PASS | BLOCKED — WSPR timing | PASS | PASS | PASS |
| 160 m | PASS | BLOCKED — WSPR timing | PASS | FAIL — coherence | PASS |
| 80 m | PASS | BLOCKED — WSPR timing | FAIL — coherence | FAIL — coherence | PASS |
| 60 m | PASS | BLOCKED — WSPR timing | FAIL — coherence | FAIL — coherence | FAIL — observer/resource gate |
| 40 m | PASS | FAIL — control path | NOT TESTED | NOT TESTED | NOT TESTED |
| 30 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 20 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 17 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 15 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 12 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 10 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 6 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 4 m | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| 2 m | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |

`PASS` means an explicit accepted row disposition backed by exact physical and
analysis evidence. `FAIL` is retained and is not a retry request. `BLOCKED`
means the frozen control-path or execution boundary prevents acceptance.
`NOT TESTED` means the stopped batch did not reach that row. At 138 MHz and
divider 1, 4 m and 2 m remain outside direct synthesis range.

The campaign DFCW convention remains **dot-high/dash-low**. The auditor checks
that the `ET E` DFCW measurements are high, low, high; it does not substitute
the more common external dot-low/dash-high convention.

## Evidence and zero-RF repair

The executed candidate remained source
`0e85ff90571c800450073f7b0bfafd70266f1f44`, UF2
`9ac5a40fe6d9a44a3a0156621b82801488efecafb9f472ba601dbcbb3e138398`
and boot `cab95d7eecad05047fcb1d6806cf9e86`. It used the 138 MHz,
divider-1, `pio-dma-gp2`, RAM-rendered GP2 configuration. The companion
WsprryPi source was `c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf` and its
binary SHA-256 was
`b8e63947e2e9780f43dc4247869db138f81cc6e2245c99c1fd02ad9de4b33ff6`.
The receiver remained SDRplay RSP1B `2404058C60`, 250 ksample/s, 200 kHz,
20 dB, AGC off, bias tee off and zero frequency correction.

The first audit correctly rejected the older 630 m production analysis files:
their recorded WTP job IDs did not match the corresponding immutable physical
run results. The originals remain unchanged. The permitted host-only repair
created three new zero-RF analyses from the already bound raw captures,
metadata, historical plans and physical run results. Each new analysis names
the actual WTP job, includes the physical-result SHA-256 and passed the same
unrelaxed signal checks. A fresh full audit then accepted all three paths for
630 m QRSS, FSKCW and DFCW, as well as the retained 160 m QRSS/DFCW and 80 m
DFCW blocks. This is new analysis, not a mutation or rebinding of an old
analysis artifact.

Sequence 176 (`2200m:FSKCW:1:browser_compact:nominal`) has a passing packet,
execution, capture, metadata and analysis chain and consumed 45.000001 RF
seconds. Sequence 177
(`2200m:FSKCW:2:controller_disconnect:nominal`) is a retained zero-RF failure.
The 2200 m FSKCW row therefore fails even though its browser-compact replacement
passed.

## Authorization accounting and closure

The authorization listed 82 jobs and at most 3260.000075 RF seconds. One job
completed, one fresh packet failed before ARM with zero RF, and sequences 178
through 257 were not executed. Actual campaign expenditure under this
authorization was **one RF job and 45.000001 RF seconds**. Eighty listed jobs
remain unexecuted, but the stop-on-first-failure authorization is consumed and
does not permit resumption.

The explicit scope disposition is recorded in
[`phase11-6-scope-disposition.json`](phase11-6-scope-disposition.json). Phase
11.6 accepts only the 13 `PASS` rows. All 52 other supported rows are removed
from Phase 11.6 acceptance: 9 retained `FAIL`, 12 `BLOCKED`, and 31 `NOT
TESTED`. The 10 unsupported 4 m/2 m rows remain explicit configuration
boundaries. Every original row disposition and its evidence remain in the
matrix; scoped closure does not turn a failure, block or untested row into a
pass.

This disposition closes Phase 11.6 without further RF. It performed no flash,
BOOTSEL transition, reboot, configuration write, GPIO change or RF operation,
and it authorizes none. The consumed execution authorization remains stopped
at sequence 177 with 80 jobs unexecuted.
