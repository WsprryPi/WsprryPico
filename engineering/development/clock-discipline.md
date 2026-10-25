# UTC discipline and RF correction

The original MIT μChrony engine disciplines the virtual UTC clock from NTP.
A persisted learned rate is a provisional restart seed; it restores neither
UTC, synchronization, source history nor freshness. Manual PPM is the sole RF
carrier correction. Internet NTP is not qualified as an RF calibration source.

The Pico-to-Pi GPIO pulse path and CLOCKPROBE commands are unavailable. No GPIO
timing connection is required. Pi GPS HAT services remain independent of Pico
UTC discipline. GPS/PPS ingestion is selected future work in the
[consolidated backlog](consolidated-backlog.md#remain-in-backlog-for-future).

## Compatibility and persistence

The standalone NTP update timeout defaults to 3600 seconds and is stored as the optional Config v1 field `ntp_timeout_s`; omitted fields select that default. The independent [transmitter-ntp-timeout/1 resource](../protocol/transmitter-ntp-timeout-1.schema.json) exposes saved and boot-active values. Whole-minute values from 60 through 86400 seconds are accepted with exact target and If-Match binding while idle. Changes require restart, preserve station/network/pin/frequency/STOP settings, and inhibit new standalone jobs until that restart. Legacy closed Config and progress views omit this field and preserve it on ordinary saves and replacements. The service advertises the active maximum source age in its existing WTP capabilities. The 500 ms job uncertainty limit, local launch checks, leap handling and initial synchronization requirement are unchanged.

The existing `transmitter-rf-calibration/1` resource remains available for manual
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
