# μChrony

μChrony is an original MIT-licensed, bounded NTP client and virtual UTC clock for
microcontrollers. Its implementation follows documented Chrony clock-discipline
rules. Chrony source is not copied, translated, vendored or linked into this
library or the Pico firmware. The adjacent [license](LICENSE.md) permits reuse
independently of WsprryPico.

The external Chrony 4.9 comparison covers eight source-statistics streams,
160 phase-steering cases and five source-selection traces. The tested phase
rules, final source choices and named hysteresis switch agree; startup selection,
adaptive history, transient frequency and reported skew can differ. Full
behavioral equivalence has not been demonstrated. This is an original bounded
implementation, not a port or complete replacement for the Unix daemon.

The [clock-loop comparison](../../engineering/development/microchrony-clock-loop.md)
also exercises complete source-to-clock feedback on 28 identical four-hour
physical-event traces with independently known oscillator and UTC error. It
includes changing drift, phase changes, restart seeds, holdover and four sources;
six additional 256-point histories and 274 same-estimate combinations check
adaptation and source combination separately. The record quantifies retained
quantization and variable-delay limits.

The [Internet-source follow-up](../../engineering/development/microchrony-internet-diagnosis.md)
adds variable-delay tests and pooled replays of retained A/B inputs. It records
both closer frequency agreement and worse indicated UTC offsets in the captured
pulse replay; matching a reference controller does not establish absolute accuracy.

The [packet and independent-clock comparison](../../engineering/development/microchrony-conformance-results.md)
also exercises Chrony's actual packet admission before its statistics API. It
separates packet filtering, fixed raw-coordinate regression and coupled clock
trajectories, and compares learned-rate control with phase damping alone against
known error. The selected tests establish bounded behavior, not complete daemon
equivalence.

The [lead-layout captured-input comparison](../../engineering/development/microchrony-lead-replay-results.md)
separates conditional controller weights from conservative public bounds and
ages each candidate path from its own exchange. It substantially closes the
Chrony frequency/phase replay difference while retaining the Internet inputs'
adverse bias and every existing quality gate. Software agreement does not
establish improved physical UTC or RF accuracy.

## Integration

Use `add_subdirectory(path/to/microchrony)` and link the `microchrony` target, or
compile `microchrony.cpp` with its adjacent header. C++20 is required. No Pico
SDK, operating system, socket, filesystem, heap allocation or other project
module is required. All state has fixed capacity: four sources with up to 64
original measurements each. One application thread owns an engine; its raw
nanosecond clock must remain monotonic. Construct a fresh engine after a raw
clock reset. `reset()` clears source cohorts while retaining the virtual clock
and learned frequency for an ordinary network change.

Configure distinct nonzero endpoint identities. Call `request()` when polling
is possible, send its 48 bytes, and deliver replies through `receive()` with the
original receive timestamp. The caller supplies an unpredictable 64-bit token
and validates source address/port. `cancel()` retires an unsent request. A late
callback is included in measured delay; no timestamp is backdated to hide it.
Repeated reads of `tracking()` never create a sample or refresh source age.

`tracking()` returns the virtual UTC, actual mapping rate, frequency correction,
remaining phase correction, skew, root metrics, source timestamp and synchronization.
The frequency sign is UTC seconds per raw second minus one: a raw clock running
fast needs a negative correction. Phase is slewed after the initial UTC epoch
is established. A saved frequency is only a provisional seed; it cannot restore
UTC, synchronization, source history or freshness after a cold boot.

`readiness()` separates synchronization, remaining correction, frequency skew
and a caller-selected error limit. Its default checks mirror the intent of
`chronyc waitsync`: normal synchronization, at most 10 ms remaining correction
and at most 1 ppm skew. Such statistical confidence is conditional on the
source and network. It is not an independent measurement of absolute UTC or an
RF-clock calibration.

## Rules and profile

The engine correlates NTPv3/v4 basic server replies, unfolds the NTP era, handles
RATE backoff and source denial, rejects unusable sources, filters excessive
network delay, fits weighted clock frequency, checks residual runs, and combines
agreeing sources. Frequency-fit weights use local peer-delay variation rather
than upstream root distance. A separate partial regression learns delay
asymmetry only after ten strong same-sign observations; weak correlation alone
cannot immediately alter the point estimate. Regression covariance includes
the delay coefficient, and public bounds cover the identifiable alternative
when its correction is withheld. Combined uncertainty covers
the actual combined center without assuming source independence. Phase and
frequency corrections are separate. Loss and rejection never rejuvenate a
retained fit. Source loss can leave a projected UTC while synchronization is
withdrawn. Source changes use accumulated quality scores and reselect distance;
repeated status reads do not vote or steer the clock. Only a new selected-source
fit or a changed reference updates clock discipline.

Delay-deviation classification uses the preceding fit and becomes available
with six retained observations; three observations can still establish the
initial UTC fit. Half the extra round-trip delay is compared with ten times
the normalized weighted residual deviation plus elapsed frequency/stability
uncertainty. An innovation too large to be explained by that queue reaches
the estimator and its existing uncertainty gates. Public joint covariance and
identifiable path-bias coverage remain separate from the conditional statistics
used by this classifier. A repeated server transmit timestamp is not a new
observation, even with a new request nonce.

Original timestamp/wire observations remain in the bounded 64-record history
when the active regression shortens. A compact predecessor horizon extends the
balanced-sign residual-runs test with the same learned path term. The horizon
ages before each new observation and never exceeds 127 tested points. Only
quantization-limited fits treat residuals below timestamp precision as ties.
The runs critical count is calculated from the two-decimal 1.65 lower-tail
normal quantile. This preserves the reference's discrete rounding, including
the 54-observation boundary, without including an upstream table.
Phase combines by inverse source distance; frequency combines by inverse
frequency variance. Disagreement and estimate age enter phase-controller error.
Controller statistical error remains separate from conservative public bounds.
Conditional regression errors weight the controller; full joint covariance and
path ambiguity still govern qualification. Each retained candidate path ages
from its own measurement timestamp before ranking and combination weighting.
The engine stays within its existing 32 KiB limit.
Frequency combination gives a new equally precise fit three times the previous
estimate's weight and expands tracking error on disagreement. The controller's
error state is separate from the conservative reported bound, which still
covers the new fit and displacement of the applied frequency from its center.

The portable defaults follow the documented Chrony defaults for the implemented
options. WsprryPico selects the explicit profile equivalent to `minpoll 6
maxpoll 6`, `maxdrift 100` and `maxclockerror 50`. This retains its existing
90-second job-age contract, ±100 ppm oscillator range and conservative 50 ppm
holdover allowance. A rejected selected-source response can still cross that
90-second limit before the next normal poll; an unrelated combined-peer reply
does not refresh the evidence used for the last clock update. Other engine
settings retain their defaults, including
`iburst`, maximum delay/distance 3 seconds, delay-deviation ratio 10,
`polltarget 8`, `minsamples 6`, `maxsamples 64`, `maxupdateskew 1000`,
`maxslewrate 83333.333`, and `corrtimeratio 3`. These are configuration choices,
not alternate NTP estimators. The bounded profile withdraws a source after
eight consecutive unanswered requests, rather than retaining an unreachable
association for the Unix daemon default lifetime. Pico RF carrier correction uses only the independent, persistent manual PPM
value within its existing ±100 ppm range. NTP-derived RF calibration is rejected;
legacy candidate diagnostics never grant RF authority. The Pico-to-Pi GPIO pulse
measurement path is retired. The [closeout](../../engineering/development/ntp-work-closeout.md)
records that disposition; future GPS/PPS input remains in the backlog.

Supported scope is a bounded IPv4 basic client with a virtual UTC clock. It does
not implement NTS/MAC authentication, NTP server/peer modes, interleaved or
extension-field modes, Unix kernel control, reference clocks, GPS/PPS or RTC
tracking. Pending leap indicators are exposed to the application; leap-second
execution is not yet a demonstrated Chrony-equivalent behavior. The Pico job
policy excludes jobs near announced leap transitions. The [target results](../../engineering/development/microchrony-results.md) record
measured callback latency, applied-clock checks and their finite scope. Exhaustive
worst-case latency, long-term clock behavior and physical RF accuracy remain
unqualified.

## Validation

The deterministic engine tests are in `tests/microchrony_tests.cpp`; integration,
manual correction, persistence, source age, clock arbitration and alarm mapping
are in `tests/ntp_work_tests.cpp`. The causal replay compares phase damping alone
with frequency correction using only preceding observations. Future truth is
used solely to score holdouts. Exact rational arithmetic checks both segments
of a finite slew, including inverse alarm rounding.

The separate [reference harness](../../tests/reference/README.md) links only to
a privately built, unmodified Chrony 4.9 tree. Its GPL reference executable is
never linked into firmware or included in an MIT deliverable. Differential
output records disagreement as well as agreement; passing a selected numerical
check is not a certificate for the whole Chrony daemon.

The WsprryPico transport adapter additionally exposes `NTP PACKETS <cursor>`
over USB Console. This is outside the portable engine and compact UI status.
Its 32-record ring retains accepted and rejected known-association deliveries,
original request/receive timing, source identity/epoch, request token, actual
datagram length and the first 48 offered bytes. Overwrite and truncation are
explicit. Unknown-address/port datagrams discarded by transport are outside
this log's scope. The [reference guide](../../tests/reference/README.md#offered-packet-diagnostics)
defines collection and visibility; this diagnostic never supplies time or
changes a clock/RF gate.

The governing references are the official [Chrony 4.9 configuration
manual](https://chrony-project.org/doc/4.9/chrony.conf.html), [chronyc
manual](https://chrony-project.org/doc/4.9/chronyc.html), and the
[NTPv4 specification](https://www.rfc-editor.org/rfc/rfc5905.html).
