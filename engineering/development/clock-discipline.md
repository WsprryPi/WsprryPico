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

The NTP update timeout defaults to 3600 seconds. The historical [transmitter-ntp-timeout/1 resource](../protocol/transmitter-ntp-timeout-1.schema.json) retains whole-minute values from 60 through 86400 seconds. The independent [version-2 resource](../protocol/transmitter-ntp-timeout-2.schema.json), at `/api/v1/ntp-timeout/2`, additionally accepts zero: retain the last accepted NTP clock indefinitely without the Pico's NTP age or uncertainty admission cutoff. Actual uncertainty continues to grow and remains reported. Initial synchronization, explicit clock invalidation, arithmetic/range checks, cross-source disagreement, leap handling, and external callers' stricter requested uncertainty budgets remain enforced. Controller/browser source expiry remains 90 seconds. A finite setting retains the 500 ms admission limit.

Positive timeout settings retain Config version 1. Zero is serialized as Config version 2 with an explicit canonical `ntp_timeout_s:0`; version 1 still rejects zero, and version 2 requires that exact field/value. Old readers reject the new record without falling back to an older configuration. Public closed Config/progress views stay unchanged, omit the independent timeout field and preserve it on saves and replacements. Historical public Config writes still require version 1; internal candidates preserve the saved timeout and select their stored version accordingly. Firmware must understand Config version 2 to read a stored zero selection.

Saved and boot-active values remain distinct, target/revision-bound and idle-only. Changes require restart and preserve station/network/pin/frequency/STOP settings. Version 1 refuses reads or mutations whose response cannot represent the boot-active zero value. Unlimited timeout advertises `UINT64_MAX` for the existing WTP source-age and server uncertainty limits; WTP's existing semantics and an ARM request's own uncertainty limit are unchanged. No WTP downgrade or zero-age reinterpretation is introduced. Public timeout reads use the independent closed `pico-public-read/3` descriptor containing only `ntp-timeout/2`; historical /1 and amplifier /2 descriptors remain frozen.

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
