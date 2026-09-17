# Phase 11.5 Package 10 matched replay-state closure prompt

## Objective

Execute one bounded R6 continuation that tests the unchanged 1,024-byte
resource-return gate with equivalent WTP terminal/replay state at the baseline,
each post-N window and final Q. Preserve Package 9 v44 as a failed result. Close
R6 and Phase 11.5 only if the complete packet and independent raw audit pass.

## Evidence-based diagnosis

Package 9 v44 completed its 1,800-second normal workload, three production RF
jobs and all five quiet windows. Its post-N heap values were stable, but about
12 KB above the baseline. This is consistent with one retained 383-entry
`FrequencyAdjustment` vector introduced by the first production job. WTP/1
requires the exact original LOAD result to remain replayable with a terminal
record for at least one hour. The implementation shares equal immutable
adjustment lists, so later production jobs do not add another vector.

The v44 warm-up contained only one different 512-entry adjustment class. Its
baseline therefore omitted required production replay state. Four early warm-up
records also expired before final Q. The baseline and final-Q terminal histories
were not equivalent to the post-N histories. Treat this as a measurement-design
defect, not evidence of a firmware leak. Do not weaken WTP replay retention,
remove required records, change the resource threshold or erase the failure.

## Exact identities and boundaries

- Repository: `/Users/lbussy/GitHub/WsprryPico`, branch `devel`.
- Pico A: serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, source
  `91933c00970939e366d1bfcf3c1956b59be8f6c5`, UF2 SHA-256
  `5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446`,
  boot `ff719d304f1ba4ac23fddd93561b26f0`.
- Pico B comparator: serial `CDDBF8767C506C07`, device
  `29f20b7342051ef947aa56cb9d4fab42`, source `8921a7008183`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- Pico A configuration: Pico 2 W/RP2350 Arm, 138 MHz, divider 1, GP2 PIO/DMA,
  RAM rendering and configured network listener.
- WsprryPi production source:
  `21ae75ab9e38bd6237b1ae73f3e7ab8527324067`.
- Host boot: `220e53ca-ca95-4206-9581-dbe28aa1eeb8`.
- Use the retained isolated `time.local` fixture, authenticated TLS credentials,
  independent USB/Console observers and shared RF reservation.
- No firmware or protocol change is selected by this diagnosis. Perform source
  impact review and stop if current runtime code differs from the deployed
  source or if evidence reveals a separate product defect.

## Finite authorization and accounting

This package may consume at most:

- 480 additional RF seconds;
- 20 RF jobs and 360.8 planned RF seconds across the preserved stopped attempt
  and one corrected complete attempt;
- two flashes and two BOOTSEL transitions authorized as a ceiling, with zero
  planned or permitted by the frozen packet because no firmware change is
  selected;
- zero CONFIG writes, controlled reboots, intentional Wi-Fi cycles and
  destructive allocation probes.

The first frozen attempt was stopped after four one-second jobs when an
independent retained-TLS comparison proved that its production-class frequencies
were wrong. That attempt remains charged as four jobs/four RF seconds. Its fresh
final inventories, released reservation and restored fixture are mandatory
inputs to the corrected packet. The corrected 16-job workload uses another
356.8 seconds, leaving 119.2 authorized RF seconds unused. Do not use that
remainder for another retry or exploratory work.

## Frozen workload

### Mixed eight-job warm-up

Run exactly eight one-second jobs before the baseline:

1. three 383-event production-class FSKCW normalizers whose requested-frequency
   sequence is exactly the sequence produced for 32 question marks at
   135,505 Hz mark, 135,500 Hz space, one-dot intra-element gap and three-dot
   inter-character gap; and
2. five 512-event alternating-frequency maximum-event normalizers.

Compress only event durations in the production-class normalizer. Distribute
one second contiguously over 383 events using 2,610,966 ns per event plus one ns
for the first 22 events. This changes neither event indexes nor requested
frequencies. Require 383 returned adjustments and record a canonical SHA-256 of
`event_index`, `requested_frequency_nhz` and `realized_frequency_nhz`. Require
512 adjustments and the corresponding hash for every maximum-event job.

Run the three production-class jobs first, followed by the five maximum-event
jobs. After the eighth job, require exactly eight complete, inactive terminal
records, with a 3/5 class cardinality. Each real production completion then
evicts the oldest short production-class record, preserving that same 3/5
cardinality as well as the same two shared adjustment allocations. Start the
360-second matched baseline only after this state exists.

### Normal workload and interleaved windows

Reuse Package 9's frozen normal workload without changing its behavior:

- three 600-second normal-load intervals;
- one native WsprryPi 32-question-mark FSKCW job per interval;
- 383 events, 114.6 seconds per production job;
- the same 48 browser actions and 84 authenticated GETs;
- independent Console, host and USB evidence; and
- one 306-second application-quiet measurement after each interval.

WsprryPi treats the configured 135,500 Hz base as the FSKCW space frequency and
adds the 5 Hz shift for the mark. Retained Package 9 TLS evidence binds the
resulting 192 mark and 191 space events before corrected execution. The
independent TLS audit must reconstruct each production LOAD and its LOAD
response. All three production adjustment hashes must match the short
production-class normalizer hash.

### Five-job terminal-history refresh and final Q

After post-N3, run exactly five new one-second 512-event maximum-class jobs.
Require complete Loaded/Armed/Running/Complete lifecycles, matching adjustment
hashes and inactive output after release. The resulting eight terminal records
must be exactly the three production jobs and five refresh jobs. The original
warm-up records must be evicted. Both adjustment classes must still be
represented.

Then run the separate 360-second final-Q interval. Require the same exact
eight-record terminal set before and after final Q so natural record expiry
cannot make the comparison inequivalent.

## Acceptance gates

Keep every applicable Package 9 identity, workload, observer, service,
restoration, RF timing, stack, heap-reserve, allocator-failure, TLS-failure,
DMA, fault, capture and authority gate. Additionally require:

- baseline, all three post-N values and final Q within 1,024 allocated heap
  bytes of baseline;
- maximum post-N span at most 1,024 bytes;
- no strictly increasing post-N sequence;
- exact equivalent retained adjustment classes and terminal/history cardinality
  for every compared window;
- all three production adjustment hashes equal the production-class warm-up
  hash, and all maximum normalizer/refresh hashes equal one another;
- exactly 16 completed jobs in the corrected attempt and cumulative accounting
  of 20 jobs / 360,800,000,000 RF ns including the stopped attempt;
- at least 16 additional tail IRQs and launch-epoch increments;
- both Picos finally Empty, unowned and output-inactive;
- shared RF reservation Released; and
- fixture, installed WsprryPi service and recovery timer restored.

Any failure, observer loss, identity drift, unexpected reset, resource failure,
diagnostic, authority error, capture loss, incorrect terminal set or restoration
failure keeps R6 and Phase 11.5 open. Never infer inactive RF from a disconnect.

## Implementation and validation

Create a Package 10 runner, staging helper, raw auditor, adversarial assessor and
focused hardware-free tests. Reuse reviewed Package 9 helpers where behavior is
identical. Freeze every helper hash and private input in the packet. Keep
credentials, TLS payloads, captures and generated firmware outside Git.

Before physical execution, run syntax/style checks, focused tests and the full
documented host test suite. Stage a fresh mode-0700 evidence root, verify fresh
A/B inventories, reconcile the shared reservation and start the existing
isolated network/time fixture. Execute exactly one frozen packet. Audit only
after fixture cleanup and independent final inventories.

The raw auditor must rebuild facts from the journal, inventories, TLS logs and
captures rather than trust the harness summary. Publish only credential-free
aggregate results and cryptographic evidence hashes.

## Adversarial review and closeout

After an intact raw audit, mutate every closure-critical class independently,
including packet identity/budget, mixed warm-up composition, adjustment count
and hash, production hash equivalence, lifecycle, workload counts, quiet-state
equivalence, resource threshold, terminal set, timing/resource faults, capture,
reservation and restoration. Require every mutation to fail and rerun the
intact audit. Repair any accepted mutation or ambiguous gate, rerun affected
checks and repeat the adversarial assessment until clean.

Update the acceptance matrix, ledger, plan and a Package 10 review/result only
from audited evidence. If all gates pass, close R6 and Phase 11.5 for the exact
deployed configuration above. If any gate fails, publish the failure without
claiming closure. Commit the durable prompt, helpers, tests and sanitized result,
push `devel`, verify remote parity, and report the exact outcome, finite budget,
checks, restoration, commit and push state.

## Execution record

Execution stopped before the corrected workload could reserve RF. The first
packet remains charged for four one-second warm-up jobs after its production
frequency mismatch was found. Thirteen corrected zero-RF fixture preflights then
tested bounded association/readiness, exact radio resets, both radio-role
assignments and one-packet X25519 TLS handshakes. The final qualified-role
combination still failed the mandatory independent-client association gate.

Package 10 therefore earns no acceptance credit. R6 and Phase 11.5 remain open.
Actual Package 10 RF use is four seconds, with zero flashes, BOOTSEL transitions,
configuration writes, controlled reboots, intentional DUT Wi-Fi cycles or
allocation probes. See the
[execution and adversarial review](phase11-5-package10-review.md) and
[sanitized failure result](phase11-5-package10-failure-result.json).
