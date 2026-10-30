# UTC discipline and RF correction

The original MIT μChrony engine disciplines the virtual UTC clock from NTP.
A persisted learned rate is a provisional restart seed; it restores neither
UTC, synchronization, source history nor freshness. Manual PPM is the sole RF
carrier correction. Internet NTP is not qualified as an RF calibration source.

The Pico-to-Pi GPIO pulse path and CLOCKPROBE commands are unavailable. No GPIO
timing connection is required. Pi GPS HAT services remain independent of Pico
UTC discipline. GPS/PPS ingestion is selected future work in the
[consolidated backlog](consolidated-backlog.md#possible-future-work).

## Compatibility and persistence

The current [NTP timeout resource](../protocol/control-1.schema.json) at
`/api/control/v1/ntp-timeout` defaults to 3600 seconds and accepts zero or
whole-minute values from 60 through 86400 seconds. Zero retains the last
accepted NTP clock without the Pico's NTP age or uncertainty admission cutoff.
Actual uncertainty continues to grow and remains reported. Initial
synchronization, explicit invalidation, range checks, cross-source disagreement,
leap handling and callers' stricter uncertainty budgets remain enforced.
Controller/browser source expiry remains 90 seconds. A finite timeout retains
the 500 ms admission limit.

Positive timeout settings retain internal Config version 1. Zero is serialized as
Config version 2 with an explicit canonical `ntp_timeout_s:0`; storage version 1
rejects zero and version 2 requires that exact field/value. Old readers reject the
record without falling back to an older configuration. Current control config and
progress projections omit the independently owned timeout and internal storage
version. Ordinary merges and scoped saves preserve it. Firmware must understand
Config version 2 to read a stored zero selection.

Saved and boot-active values remain distinct, target/revision-bound and idle-only.
Changes require restart and preserve station/network/pin/frequency/STOP settings.
The stable `ntp-timeout` resource belongs to `Wsprry-Control/1`; mutations require
the root contract, current target and revision. Public discovery's aggregate
`public-read` catalog includes `ntp-timeout` through `/api/consumer/v1/read/`.
Unlimited timeout advertises `UINT64_MAX` for the existing WTP source-age and server
uncertainty limits; WTP semantics and an ARM request's own uncertainty limit remain
independent. No WTP downgrade or zero-age reinterpretation is introduced.

The existing `rf-calibration` resource remains available for manual
PPM. Its GET response reports `saved.mode: "manual"`; PUT accepts manual mode
and rejects `mode: "ntp"` with HTTP 400 `ntp_rf_rejected`, without changing the
manual value. The browser exposes manual carrier correction only.

The legacy `ntp_rf_calibration` configuration field remains readable and
round-trippable for saved-data and closed-view compatibility. It has no RF
effect, including when an older saved configuration contains `true`. A manual
calibration save clears it. RF selection reports no NTP availability and an
unqualified `ntp_rf_rejected` candidate; older candidate-shaped fields are inert
compatibility diagnostics. The separate NTP observation resource can still
expose clock-fit diagnostics under its legacy field names; those grant no RF
authority.

The existing NTP journal layout and device/topology bindings are preserved.
Old RF-prior payloads can still be read so an upgrade does not invalidate the
retained UTC seed; they are never applied to RF or newly learned by production.
Console RF-prior availability is false. UTC rate/skew persistence and the
operator's manual PPM remain separate. No settings erase, journal migration or
manual-correction reset is required.

## Measurement boundaries

Statistical skew and indicated NTP offsets do not establish absolute UTC phase
or physical carrier accuracy. [Independent clock measurements](microchrony-independent-measurement.md)
define the reference and common-clock requirements. The portable engine's
[integration and profile](../../src/microchrony/README.md) and the
[external reference harness](../../tests/reference/README.md) describe software
behavior and reproducible comparisons. Neither qualifies physical timing or RF.
