# Phase 11.5 Package 9 execution and adversarial review

## Outcome

Package 9 is **OPEN** and R6 is **OPEN**. Phase 11.5 remains **5 of 6
families closed**, with no accepted complete configuration. The final v44 packet
completed the entire frozen workload but failed the unchanged matched
resource-return gate. This is a measured product/resource result, not an RF
timing or WsprryPi scheduling failure.

The [execution prompt](phase11-5-package9-prompt.md) defines the bounded work.
The [sanitized failure result](phase11-5-package9-failure-result.json) binds the
completed workload, failed gate, final state and evidence hashes. The
[attempt history](phase11-5-package9-attempt-history.json) conservatively charges
every retained attempt, and the
[failure adversarial result](phase11-5-package9-failure-adversarial-result.json)
records the final mutation assessment. Credentials, captures and authenticated
payloads remain private on `wspr5` under the retained attempt roots.

## Candidate and timing ownership

The exercised Pico A is source
`91933c00970939e366d1bfcf3c1956b59be8f6c5`, UF2 SHA-256
`5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446`,
device `fd6127d11d6aca42a9905fa3fb1bf1d5` and boot
`ff719d304f1ba4ac23fddd93561b26f0`: Pico 2 W / RP2350 Arm, 138 MHz,
divider 1, GP2 PIO/DMA and RAM rendering. Pico B remained on revision
`8921a7008183` and boot `6684b4b197d80cfa0ce83b3aaf205cb0`.

The production owner is WsprryPi source
`21ae75ab9e38bd6237b1ae73f3e7ab8527324067`. WsprryPi resolves, connects,
claims, loads and arms each complete job before its deadline. Its timing
obligation ends when ARM is accepted. The Pico then owns the UTC launch, RF
generation, symbol timing and completion locally; no per-symbol host or network
delivery occurs. The v44 evidence shows three complete production lifecycles,
so the failed resource gate does not imply a WsprryPi timing failure.

## Repairs and completed workload

Six zero-RF flash/BOOTSEL attempts produced the accepted physical candidate.
They added static-page streaming and bounded Console priority during HTTP
transfers. The 100 ms candidate missed Console cadence by 29 ms; the 200 ms
candidate produced a 2.262-second Console response at the first N+150 reload;
the accepted 500 ms budget passed every critical reload. One wrong inhibited
150 MHz build was rejected and the accepted 138 MHz standalone-RF configuration
was restored. The aggregate attempt auditor corrects a frozen deployment-local
count that omitted the separately named first flash.

v44 completed all frozen physical work:

- eight one-second, 512-event normalizers;
- three 600-second normal-load intervals, for 1,800 normal seconds;
- three 114.6-second FSKCW production jobs with full independent USB
  Loaded/Armed/Running/Complete evidence;
- 48 browser actions and 84 authenticated GETs, including all six full-page
  reloads and all three RF-overlap reloads;
- a 360-second matched baseline, three 306-second post-N quiet intervals and a
  separate 360-second final equivalent quiet interval; and
- final read-only inventories of both Picos.

The production harness originally required its five-second WsprryPi sampler to
catch brief Loaded and Complete states. Earlier v37 and v41 attempts proved that
those states can occur between host samples while the one-second USB observer
captures the full lifecycle and WsprryPi retains an authoritative matching
completion report. The repaired rule requires host Armed/Running handoff plus
that report, and independently requires USB Loaded/Armed/Running/Complete.
All three v44 cycles passed the repaired rule.

## Failed resource gate

The matched post-warm-up baseline was 44,392 allocated heap bytes. The three
post-N windows were 56,824, 56,824 and 56,336 bytes: deltas of 12,432, 12,432
and 11,944 bytes, all beyond the unchanged 1,024-byte limit. Their 488-byte span
and non-increasing sequence show bounded retention rather than monotonic growth,
but that does not satisfy return to the matched baseline. Final-Q fell to 51,608
bytes and still exceeded baseline by 7,216 bytes.

The run also exposed an invalid harness expectation that exactly eight terminal
records would remain at final inventory. Warm-up records have a one-hour
lifetime, while the complete schedule ends about 67 minutes after the first
warm-up. Natural expiry left four complete, inactive terminal records. That
late harness check stopped result creation, but changing the count rule would
not close R6 because the independently measured 1,024-byte resource gate also
failed.

The closure auditor correctly rejects v44 with `Campaign failure record`. A
separate failure auditor verifies the entire completed workload, the exact
failed measurements, both final inventories, reservation release, fixture
restoration and cumulative budget without treating the run as acceptance.

## Retained attempts and finite budget

The retained chronology includes preflight failures, observer and harness
repairs, the 100/200/500 ms firmware comparisons, v38/v39 memory-readiness
rejections, v40/v43 aged-deadline rejections, v42's zero-RF retained-memory
rejection and v44's complete failed campaign. v41's interrupted campaign left
the shared reservation Held as designed; fresh two-board inactive inventories
and the evidence-checked reconciliation path released it before v44.

Across 45 attempt roots, conservative accounting charges 142 RF jobs and
1,164.4 seconds of planned RF, with six flashes and six BOOTSEL transitions.
Configuration writes, controlled reboots and intentional Wi-Fi cycles remain
zero. Only 35.6 seconds remain under the frozen 1,200-second ceiling; another
complete 351.8-second packet cannot run under this allowance. A product repair
and new finite physical authorization are required before a full R6 retry.

## Adversarial review

Review before v44 found and repaired three evidence defects:

1. the adversarial set removed USB Complete but did not separately remove USB
   Loaded after the host-sampling repair;
2. the raw auditor prefiltered three record sets and then filtered them again
   under display labels, making an intact success fail; and
3. the raw auditor trusted the harness's summarized host state set instead of
   reconstructing states, owner, job, session and completion report from raw
   WsprryPi samples.

The repaired closure adversarial set now contains 40 mutations. Because v44 is
not intact closure evidence, it is not passed through that success-only
assessment. The failure publication instead rejects all 16 altered cases,
including false closure, changed candidate/workload/lifecycle, a widened
resource limit, falsified baseline or terminal count, budget inflation,
restoration changes and evidence corruption. The intact failure publication
passes again after the mutation set.

A stale `/tmp/phase11_5_package9.py` initially shadowed v44's staged module and
caused an irrelevant identity rejection. Rerunning the auditor as a module from
the frozen v44 scripts directory produced the authoritative `Campaign failure
record` rejection. No raw payload was published to work around that import
error.

## Validation and final state

Before v44, the complete host build and all 79 registered tests passed. The
Package 9 suite now contains 13 focused tests covering the repaired lifecycle,
raw-auditor selection, 40 closure mutations, failure publication, cumulative
budget and 16 failure mutations. Python syntax, JSON parsing and repository
whitespace checks pass. A final complete host run is recorded with this commit.

Final independent inventories show both Picos Empty, unowned and output
inactive. Pico A retains four complete inactive terminal records; Pico B is
unchanged. The shared RF reservation is Released. Fixture cleanup restored the
host network state, installed WsprryPi service and Wi-Fi recovery timer.

## Remaining boundary

R6.normal-load, R6.rf-budget, R6.windows and R6.quiet retain scoped v44 credit.
R6.gates remains failed. The next bounded package must first identify and repair
the retained heap that keeps post-N and final-Q states above baseline. Any
repair needs source-impact review and a new finite physical allowance large
enough for the complete 351.8-second RF workload. Phase 11.5 remains OPEN at
5/6 families and `accepted_configuration` remains null.
