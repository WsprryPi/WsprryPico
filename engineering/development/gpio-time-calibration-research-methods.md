# Clock-rate analysis and RF calibration limits

A device UTC mapping, an NTP packet exchange and an independently measured RF
carrier are different observations. A rate fitted to periodic Console INFO
snapshots is a diagnostic estimate; it is not a complete NTP sample stream or
an RF calibration. Current RF correction uses manual PPM only; NTP-derived RF
calibration is [rejected](clock-discipline.md). The Pico-to-Pi GPIO measurement
path is retired. These methods remain available for offline historical analysis.

## Observation identity and quality

Separate cohorts by full device ID, boot ID, source/firmware hash, system clock,
engine and RF configuration. Compare monotonic timestamps only within a boot.
Bind each observation to its actual time source, peer, receive timestamp,
accepted/rejected query counters, sample age and uncertainty. A hostname or
reported synchronized state alone does not establish an independent UTC source.

Reject malformed JSON, stale/unsynchronized observations, negative ages,
nonmonotonic host/device time, impossible uncertainty and identity mismatch.
Record missing observations and counter resets. Repeated snapshots of the same
mapping anchor are one observation; conflicting values for one anchor are a
quality fault. Counter increases greater than one between snapshots identify
missing packet-level information. A new reported anchor without a corresponding
acceptance counter, or acceptance without an anchor change, requires explanation
rather than invented source attribution.

A reported mapping may contain rate and finite phase slew. Reconstruct it using
the actual firmware model; subtracting sample age from UTC is valid only for a
unit-rate mapping with no slew. Independent controller observations and NTP
source changes must not be pooled into one oscillator fit. The current portable
model and diagnostics are defined by the
[standalone time policy](standalone.md#time-policy) and the exact firmware source.

## Diagnostic rate calculation

For a unit-rate cohort, let monotonic time be `m`, mapped UTC be `u`, and
`b = u - m`. Across two distinct anchors:

```text
dm = m_last - m_first
db = b_last - b_first
du = dm + db
endpoint_correction_ppm = -db * 1,000,000 / du
```

Require positive `dm` and `du`. Use checked integer/rational arithmetic before
converting the final ratio for display. If the two endpoint UTC uncertainties
are `e_first` and `e_last`, their conditional rate-equivalent bound is
`(e_first + e_last) * 1,000,000 / du`. It is not an independent oscillator
confidence interval and does not account for unobserved source changes.

For an ordinary least-squares fit of offset seconds against elapsed monotonic
seconds, let the fitted slope be `s`. The reciprocal correction is
`-s / (1 + s) * 1,000,000` ppm. Center both axes before fitting and require
multiple distinct anchors and nonzero time span. Report span, sample count,
endpoint estimate, regression estimate and residual distribution separately.
A small residual does not prove the reference clock is accurate or independent.

For descriptive percentiles, sort values and interpolate at rank `(n - 1) * p`.
Report count, minimum, median, p95 and maximum; do not replace missing data with
zero. Keep idle/running and per-job distributions separate so sparse polling
cannot conceal contention or steps.

## Qualification boundary

The mapping's rate sign, RF correction sign and reciprocal conversion must be
checked against actual implementation units and a known independent RF
reference. Preserve exact board, firmware, engine, clock, frequency, receiver,
reference model/lock/routing and conducted path. A GPSDO being connected or a
host PPS timestamp does not by itself measure the transmitter's RF clock.
NTP-server changes, asymmetric delay, host clock steps and thermal transients
can mimic oscillator-rate changes.

These calculations are hardware-free diagnostic methods. They neither alter
firmware settings nor qualify target timing, automatic NTP-derived RF
correction, calibrated power or spectral performance. Current behavior and
selected work are defined in the [UTC/RF contract](clock-discipline.md) and
[consolidated backlog](consolidated-backlog.md).
