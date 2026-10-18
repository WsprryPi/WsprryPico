# Compact NTP status and bounded USB histories

The normal `WsprryPico.uf2` image `0.0.0-ntp-pool-usb-r2` resolves the earlier
routine-status memory conflict. A real authenticated Consumer-Radio/1 request
sequence succeeded on B with both 32-record histories full. The pool baseline
ended on the user's request to compare `time.local`; it did not run for two
hours. The [evidence manifest](ntp-pool-usb-evidence.json) binds the source,
image, checks, observations, independent calculations and final pool readbacks.
The [earlier paused run](ntp-pool-quality-results.md) remains separate evidence.

## Implementation and source boundary

Routine `INFO`, browser status and NTP resources retain current model summaries
and bounded peer diagnostics. Full originals use the explicit Console command
`NTP HISTORY <token|-> <cursor>`, with at most four complete records and 4096
encoded bytes per reply. A reconstruction covers at most 64 records in at most
64 pages; the full target histories used 16 pages. Its SHA-256 token binds
device, boot, firmware, source revision, slot,
endpoint, clock epoch, estimator generation, counts and model metadata. New
observations or source changes reject mixed pages. Original measurement values
and uncertainties are unchanged.

Diagnostic model metadata is evaluated at the last original observation.
The current page timestamp never refreshes a sample or model. Current freshness
and actual clock application require separately matched ordinary status.
The [USB diagnostic reference](ntp-usb-diagnostics.md) defines the interface.

The image retains pool quality selection, time-only spread compaction toward
two hours, the separate dense recent RF estimator and every qualification gate.
Admitted active-source phase updates UTC immediately. Qualified UTC rate can
apply before two hours; unqualified estimates supply unit slope. Independent
physical RF acceptance remains false. No provisional servo was added to firmware.

The build uses source base `2914745042ee4f8f2c46d9cdb59b33430d803346` plus the
owned NTP overlay, bound by a 2258-file manifest. Concurrent UI/frequency/CI
changes were preserved and excluded from this image. Only the normal firmware
target was built. The UF2 SHA-256 is
`f6962e1e9769a61c9e92eb3bb94d7a1814dd1acf14de672818503796845fde63`.

## Target and UI results

Only B was flashed: USB `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`, boot
`23084d332d37fa8d62eee868a208c850`, PIO/DMA GP2 at nominal 138 MHz.
The reserved 64 KiB and saved settings were preserved. A retained original
boot `70810de1c28e94df31343e54c74b19f9` and was never claimed or flashed.

With both histories full, encrypted `status`, `ntp-observations`, `status`
responses were 7022, 6309 and 7023 plaintext body bytes. All API requests
returned 200 and logout was confirmed. No browser/controller time or settings
write was used. This exercises the actual encrypted resource path; it does not
claim a new rendered-browser acceptance test.

The largest observed diagnostic page was 2667 bytes. Raw `INFO` reported a
46,584-byte allocator peak, 98,064-byte minimum sampled available heap,
17,608/32,768-byte core-0 stack use and 584/16,384-byte core-1 stack use.
Allocation failures and stack faults were zero; guards remained valid. These
allocator measurements come from raw `allocator_peak_bytes`; the collector's
unused zero-valued peak placeholder is excluded from reported extrema.

## Pool baseline and unchanged gates

B joined saved `Bohica`, retained `162.159.200.123` for configured
`pool.ntp.org`, and recorded 42 query attempts, 40 admitted observations and
33 UTC updates. Seven admitted scouts trained their own associations. No scout
met the healthy-source improvement rule. No source promotion occurred.

The first complete 32-observation window spanned 1988.368334 seconds.
Original active-source uncertainty was 57.041278–121.125949 ms. The exact
training intersection was −84,867 to +93,289 ppb: its 89,079 ppb uncertainty
exceeded the 5000 ppb limit. The endpoint interval was −102,094 to +104,431
ppb, also exceeding the permitted ±100,000 ppb. The disjoint-center difference
was 635 ppb, within its 2000 ppb gate. The next window failed the stability
gate as well. Neither UTC nor recent RF rate qualified in the recorded run.

An independent exact-rational oracle matched all 34 emitted snapshots.
Every one of the 40 admitted originals was independently visible in per-peer
latest records; reconstructed spread and compact fields matched, with no ID
gaps. Thirty-three actual UTC anchors matched their boot/source/generation and
unit-slope model. No contradictory matched clock/model binding was found.

Across 32 later-original comparisons, median absolute residual was 12.1535 ms
for repeated phase updates and 8.192 ms for the initial free-running anchor.
Phase updates improved 11 comparisons, worsened 20 and tied one; all retained
their declared bounds. This compares later NTP estimates, not independent UTC
truth. No applied interim-rate benefit was established in this pool window.

The collector exited cleanly through its verified PID handle after the user
requested the local-server comparison. Exit was independently verified at
2079.916 seconds of process lifetime, with 42 queries at final readback.
Stopping observation did not disable autonomous NTP. A later transition
counter and conservative reboot allowance are charged to the subsequent local
comparison; the original two-hour/128-attempt ceiling is carried across it.

## Interim correction and SPC assessment

Known-truth replay with unchanged gates and 12 ms source uncertainty confirms
that a qualified rate can help before two hours. Steady ±10 ppm traces first
qualify at 83 minutes 12 seconds, reducing matched 32-second projection error
from 320 microseconds to zero. A bounded-jitter trace changes matched median
error from 720 to 591.792 microseconds. A wander counterexample remains.

A separate exploratory, causal shadow replay evaluates phase/rate damping and
EWMA supervision. It is never applied to B and grants no RF eligibility. Its
parameters are bound in the manifest. Each prediction uses only prior data;
source/boot/epoch changes, gaps and original-bound phase discontinuities split
the replay. Full source uncertainty and unapplied phase lag remain. Broad replay
bounds explicitly assume UTC-per-raw slope within ±100,000 ppb; they do not
establish independent physical uncertainty.

For the captured pool originals, phase damping reduces median later-NTP
residual from 12.1535 to 8.090179 ms and cumulative phase adjustment from
401.318 to 35.510800 ms. The shadow supervisor applies no rate in this trace;
the improvement comes from phase damping. This is NTP consistency evidence.
Synthetic results remain mixed: the steady trace's median error increases
from 320 to 609.038 microseconds due to startup lag, bounded jitter changes
520 to 511.619 microseconds, and late wander increases 320 to 3615.975
microseconds. Reduced whipsaw does not establish improved accuracy everywhere.

A provisional UTC controller would be a separate policy from the current
qualified-only rate application. Damping a qualified rate must account for
the difference between fitted and applied rates; phase slewing must account
for unapplied phase error. Statistical stability cannot reduce unknown path
asymmetry or qualify RF. These distinctions follow the feedback discipline in
[RFC 5905 §11.3](https://www.rfc-editor.org/rfc/rfc5905.html#section-11.3).
[NIST's EWMA guidance](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm)
requires representative data and independence assumptions for its standard
control limits; the shadow alarm claims no Gaussian false-alarm probability.
The proposal and pool availability follow-ups are in the consolidated backlog.

## Checks and disposition

All nine affected host checks passed, including NTP/replay, standalone,
network, management, consumer-radio, RF-worker/failure and time-local checks.
Coverage includes 235 exact mapping cases, 15 identical-input replay traces,
44 independent model cross-checks and three analyzer failure regressions.
The normal target build and linked flash/RAM/stack checks passed. Scoped
formatting and whitespace checks passed. Initial fixture/compiler failures
were repaired before these successful checks.

Independent review found no remaining actionable source, diagnostic, oracle
or shadow-analysis finding after repairs. Before the local-server transition,
supported readbacks verified both boards synchronized, inactive and unowned,
with saved settings unchanged, schedules disabled, manual 0.000 ppm and boot
drive 4 mA. The RF gate remained false. No RF job, service or RF-path change
occurred. Local comparison results are a separate source/boot cohort.

The live two-hour pool test and independent physical RF acceptance remain
incomplete. Backlog item 4 retains its in-progress state. Changes are unstaged
and uncommitted; no push or publication occurred.
