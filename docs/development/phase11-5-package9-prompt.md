# Phase 11.5 Package 9 — bounded sustained mixed operation

Execute this packet only after refreshing the current repository, physical
identities, shared RF reservation, fixture restoration, installed service and
authoritative inactive state. Package 9 addresses only R6. Preserve every prior
failure and all R1–R5 accepted evidence. Do not repeat an already accepted
family, broaden this into release reliability, sweep bands or clocks, or claim
demodulated RF quality.

## Bound target and prerequisites

- Repository: `/Users/lbussy/GitHub/WsprryPico`, branch `devel`.
- Candidate source: `91933c00970939e366d1bfcf3c1956b59be8f6c5`;
  image SHA-256 `5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446`.
- Pico A: USB serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, boot
  `ff719d304f1ba4ac23fddd93561b26f0`, RP2350/Pico 2 W, 138 MHz,
  `pio-dma-gp2`, RAM renderer, GP2 RF output.
- Comparator Pico B remains read-only: serial `CDDBF8767C506C07`, device
  `29f20b7342051ef947aa56cb9d4fab42`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- Host boot: `220e53ca-ca95-4206-9581-dbe28aa1eeb8`.
- Actual WsprryPi policy source: `21ae75ab9e38bd6237b1ae73f3e7ab8527324067`;
  use the installed production binary with SHA-256
  `ab1989097cc87b54f76f5fcf776d7d16a166e1edca29ed2c71a2f396fdd22a90`,
  whose production policy provides a 12-second preparation allowance, a
  one-second ARM-submission reserve and the negotiated Pico minimum lead.
  Use the previously validated TLS observer only after hashing it in the packet.
- Require R1–R5 to be accepted/applicable in the current completion matrix and
  require no Pico runtime-source difference between the deployed candidate and
  current `devel`.
- Acquire the shared RF reservation only after fresh A/B inventory proves A is
  inactive/unowned and B is unchanged/inactive. Release it only after final A/B
  inventory proves authoritative inactivity.
- Before taking the reservation, use Console INFO only for up to 360 seconds to
  require at least 165,000 bytes of available heap. After the small readiness
  session closes, use Console INFO for at most 45 seconds to observe TLS return
  to its idle allocation before inventory. After the readiness and inventory
  sessions, require at least 150,000 bytes. This lets retained WTP
  response/session state reach its specified expiry without adding more WTP
  sessions. After the normalizer TLS session is connected and before CLAIM,
  require at least 125,000 bytes available. These bounds cover the approximately
  50 KiB maximum warm-up request, decode/preparation workspace, the independent
  32 KiB authority/RF reserve and the active TLS connection.

## Finite packet

- One fresh retained isolated fixture, native `time.local`, exact retained Wi-Fi
  input by hash, 5,400 seconds runtime and 900 seconds restoration. No external
  route or forwarding.
- No flash, BOOTSEL, controlled reboot, configuration write, Wi-Fi cycle,
  allocation probe, clock change, output-pin change or frequency change.
  The preceding zero-RF repair deployment sequence is separately recorded. The
  first flash deployed static page streaming, the second was rejected for a
  build-configuration mismatch, the third restored the accepted network
  identity and base frequency with a bounded 100 ms Console grace, and the
  fourth deployed a bounded 200 ms grace after the 100 ms candidate missed
  cadence by 29 ms. That 200 ms candidate still produced a 2.262-second Console
  response during the first N+150 reload and stopped before a second cycle. The
  fifth flash rejected an accidentally selected inhibited 150 MHz build, and
  the sixth restored the accepted 138 MHz standalone-RF target with a bounded
  500 ms Console grace. A pre-flash inventory packet that omitted the
  WTP schema stopped before mutation and is retained with zero flash charge.
  These six flashes are not part of this Package 9 execution budget. The final
  v36 deployment packet's local cumulative field says five because it omitted
  the earlier separately named static-page deployment; the attempt-history
  auditor corrects the aggregate without rewriting that frozen record.
- Retain later execution amendments without rewriting their evidence. v37
  completed all eight warm-ups and one production job, all sixteen browser
  actions and the critical N+150 reload, then stopped on a harness rule that
  required a sampled live `Complete` state after WsprryPi had already recorded
  a matching completed `last_report` and released ownership. v41 later completed
  the same workload through all sixteen browser actions but exposed a second
  sampling error: the five-second WsprryPi observer saw Armed/Running and the
  authoritative completion report while missing the brief Loaded state that the
  independent one-second USB observer captured. The repaired rule requires
  WsprryPi Armed/Running handoff, a matching authoritative completed report and
  independent USB Loaded/Armed/Running/Complete evidence. v38 and v39 stopped before the
  reservation and RF: v38 exposed an installed-client session during the
  nominally Console-only readiness window; v39 paused that client first and
  confirmed the remaining sub-threshold memory was ordinary one-hour terminal
  retention. Keep the 165,000-byte gate unchanged and start another fresh
  packet only after natural expiry. Count every attempt with the aggregate
  auditor before accepting the final 1,200-second RF ceiling. v40 stopped before
  fixture mutation because its frozen restoration deadline had aged out. v42
  stopped before reservation or RF because v41's one-hour terminal records had
  not yet expired; keep that zero-RF rejection and wait for natural expiry.
  The v41 exception deliberately left the shared RF reservation Held. Fresh
  read-only A/B inventories proved both boards Empty, unowned and output inactive,
  then the evidence-checked reconciliation path released that exact reservation.
  v43 stopped before fixture mutation because its aged absolute deadline no
  longer covered the full declared runtime and restoration reserve. Fresh v44
  completed the entire workload, all five quiet windows and final inventories,
  then failed: natural one-hour expiry left four final terminal records, and the
  independently measured post-N/final-Q heaps exceeded the unchanged 1,024-byte
  matched-baseline gate. Preserve that failure; the remaining 35.6 seconds under
  the cumulative RF ceiling cannot fund another complete 351.8-second retry.
- At most eleven RF jobs and exactly the frozen workload below. Planned RF is
  eight one-second normalizers plus three 114.6-second production jobs:
  351.8 seconds total, under the R6 1,200-second limit.
- Total measured R6 schedule is at least 3,438 seconds: a 360-second matched
  post-warm-up baseline; three 600-second N intervals; a 306-second quiet period
  after each N interval; and a final separate 360-second Q. Setup, normalization
  and restoration are additional.
- On any unexpected output/ownership, boot/source/clock change, observer death,
  missed bound, loss of authoritative evidence or gate failure: stop new
  mutations, preserve evidence, prove output inactive if possible, restore the
  host fixture, release the reservation only from authoritative final state, and
  report the package open.
- Require a synchronized clock sample no older than ten seconds before each
  maximum warm-up LOAD. Recheck the clock after LOAD before ARM. This prevents
  the periodic NTP refresh from changing the guarded UTC mapping inside the
  ten-second local launch window.

## Warm-up and matched state

Submit exactly eight one-second, 512-event FSKCW jobs through one authenticated
network WTP owner. Alternate 135500 and 135495 Hz events at 1,953,125 ns each.
For every job require Loaded, Armed, Running, Complete, terminal completion,
inactive output and release before the next job. Do not overlap these maximum
LOADs with Console INFO construction; start the long-cadence Console and host
observers only after all eight warm-ups complete. Poll warm-up STATUS no faster
than 1 Hz and retain the lifecycle events delivered on that same connection, so
observation cannot starve a scheduled one-second launch. Require the first
successful Console sample before starting the measured baseline. The eight completions normalize
terminal cardinality and content. Then close all application sessions and run a
360-second Console-only Q before recording the matched post-cache baseline.
Give each normalizer request one 20-second completion deadline. Do not resend a
timed-out request; preserve the packet and reconcile authority. The bound covers
the retained Wi-Fi path's exponential TCP retransmission backoff while remaining
inside the 60-second ownership lease. Record one matched response and elapsed
time for every request, and require the offline auditor to reject missing,

## Each of three N intervals

Run the existing actual WsprryPi binary with the network WTP backend and one
persistent logical session. Use FSKCW message `????????????????????????????????`,
135500 Hz base, 5 Hz shift, 0.2-second dot, timing multiples 1/3/7, no fade,
60-minute repeat, and an occurrence 90 seconds after the N interval begins.
Source compilation yields 383 events and 114.6 seconds. Require its wire sequence
to contain one successful CLAIM, LOAD, ARM and RELEASE; the LOAD must match the
frozen mode, event count and duration. Require the actual scheduler job to cover
Loaded/Armed/Running/Complete with the same job/owner/session and final release.
WsprryPi's deadline ends when ARM is accepted: after that handoff the Pico owns
the UTC launch, symbol timing and RF completion locally, without per-symbol host
or network delivery.
Start the production process 25 seconds before the occurrence, at N+65 seconds.
Its TLS session must therefore reach readiness after N begins and remain idle for
less than the firmware's 30-second connection-progress deadline before dispatch.
Record the expected not-started process state at 0.2 Hz before N+65 and the live
process state at 0.2 Hz afterward; process absence before N+65 is part of the
frozen schedule.

The N interval lasts 600 seconds and contains two consecutive frozen N300 browser
intervals. At offsets 0 and 300, initialize with sequential GETs for `/`,
`/api/v1/capabilities`, `/api/v1/status` and `/api/v1/config`. Within each N300,
perform explicit Refresh at +30/+70/+110/+190/+230/+270 seconds and reload the
same four resources at +150 seconds. This is exactly 16 actions and 28 GETs per
N interval. Do not fetch separate CSS or JavaScript assets or add background
polling. Keep action-start lateness at most 15 seconds, each fresh authenticated
HTTPS request including handshake at most 15 seconds, and each four-request page
action at most 60 seconds. The +150 reload must occur while the long job is
Running.

During N, independently sample Console INFO at 1 Hz with start gaps no greater
than two seconds, USB WTP STATUS at 0.2 Hz with request completion within five
seconds and start gaps no greater than six seconds, and host/process health at
0.2 Hz. Record measurement cost and use one observer session per N interval; do
not create hidden polling/session churn.

After each N interval, stop the production process cleanly, close all WTP and
HTTPS sessions and run 306 seconds of Console INFO plus host health only. Record
one comparable resource window at its end. After the third such window, run an
additional 360-second equivalent Q and record the final comparison. Do not open
WTP/HTTPS during any quiet period.

## Gates and evidence

- Require zero unexplained reset, corruption, deadlock, owner error, allocator
  failure, TLS allocation failure, stack fault, DMA error, unpaired refill,
  invalid reserve, TXSTALL/engine diagnostic or safety fault.
- Both 16 KiB stacks retain valid MSPLIM guards and at least 4,096 bytes reserve.
  Heap capacity minus the observed allocator peak remains at least 32,768 bytes.
- At 138 MHz, `rf_max_service_gap_ns` and `max_refill_irq_to_ready_ns` remain at
  most 2,849,391 ns. Full and short predecessor observations remain measured and
  retain at least 25% of their respective block sizes. Require distinct launch,
  sustained refill, short predecessor, tail and inactive shutdown evidence.
- Baseline, all three post-N windows and final Q must have eight completed
  terminal records, the same boot/source/clock/network/cache class and no active
  owner/output. Each post window must be within 1,024 live heap bytes of the
  matched baseline; the three post-N values must not be strictly increasing and
  their span must be at most 1,024 bytes.
- Bind raw journals, production plaintext observer logs, packet captures, exact
  INIs, packet/helper hashes, reservation transitions, fixture state and final
  inventories. Keep credentials and raw authenticated payloads private. Publish
  only sanitized hashes and aggregate measurements.

## Review, repair and publication

Run a separate offline raw-evidence auditor. Then adversarially mutate every
closure-critical identity, count, duration, schedule, browser cadence, observer
gap/deadline, production wire relation, lifecycle state, resource/timing/fault
gate, matched-window relation, budget and restoration claim; every mutation must
be rejected while the intact result still passes. Fix actionable findings and
repeat affected checks and the adversarial assessment until no in-scope finding
remains.

Only then publish the sanitized Package 9 result, raw-audit result, adversarial
result, review, completion matrix/ledger and development index. Close R6 and
Phase 11.5 only if every mandatory R1–R6 row remains applicable on the accepted
exact configuration. Commit the complete evidence-bound change, push `devel`,
and verify local HEAD, upstream and remote branch parity.
