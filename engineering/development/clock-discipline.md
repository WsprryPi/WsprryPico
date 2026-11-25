# UTC discipline and RF correction

The original MIT μChrony engine disciplines the virtual UTC clock from NTP or optional qualified GPS UTC/PPS observations. A persisted learned rate is a provisional restart seed; it restores neither UTC, synchronization, source history nor freshness. Manual PPM is independent from optional PPS-derived RF correction; when automatic correction is selected, manual PPM is a residual trim. Internet NTP is not qualified as an RF calibration source.

The Pico-to-Pi GPIO pulse path and CLOCKPROBE commands are unavailable. No Pico-to-Pi GPIO timing connection is required. Pi GPS HAT services remain independent of Pico UTC discipline. Optional receive-only GPS serial/PPS wiring, UTC association, month-boundary safety, separate oscillator calibration, and restart provenance are defined in the [GPS/PPS contract](gps-pps.md).

## Compatibility and persistence

The current [NTP timeout resource](../protocol/control-1.schema.json) at `/api/control/v1/ntp-timeout` defaults to 3,600 seconds and accepts zero or whole-minute values from 60 through 86,400 seconds. Zero retains the last accepted NTP clock without the Pico's NTP age or uncertainty admission cutoff. Actual uncertainty continues to grow and remains reported. Initial synchronization, explicit invalidation, range checks, cross-source disagreement, and leap handling remain enforced. Engineering controller time expires after 90 seconds. Authenticated consumer browser time has a separate one-hour holdover limit and sample-admission policy. A finite NTP timeout retains the 500 ms NTP admission limit. See [field time](field-time.md).

Positive timeout settings retain internal Config version 1. Zero is serialized as Config version 2 with an explicit canonical `ntp_timeout_s:0`; storage version 1 rejects zero and version 2 requires that exact field/value. Old readers reject the record without falling back to an older configuration. Current control config and progress projections omit the independently owned timeout and internal storage version. Ordinary merges and scoped saves preserve it. Firmware must understand Config version 2 to read a stored zero selection.

Saved and boot-active values remain distinct. Saves bind the target and revision, require idle, and preserve station, network, pin, frequency, and STOP settings. Changes take effect after restart. The `ntp-timeout` resource belongs to `Wsprry-Control/1`. Mutations require the root contract, current target, and revision. Public discovery's aggregate `public-read` catalog includes `ntp-timeout` through `/api/consumer/v1/read/`.

The existing `rf-calibration` resource remains available for manual PPM. Its GET response reports `saved.mode: "manual"`; PUT accepts manual mode and rejects `mode: "ntp"` with HTTP 400 `ntp_rf_rejected`, without changing the manual value. This manual resource remains independent from the GPS and Si5351 automatic-correction selections under Radio pins.

The legacy `ntp_rf_calibration` configuration field remains readable and round-trippable for saved-data and closed-view compatibility. It has no RF effect, including when an older saved configuration contains `true`. A manual calibration save clears it. RF selection reports no NTP availability and an unqualified `ntp_rf_rejected` candidate; older candidate-shaped fields are inert compatibility diagnostics. The separate NTP observation resource can still expose clock-fit diagnostics under its legacy field names; those grant no RF authority.

The correction journal retains its 256-byte framing and device/topology bindings. Its independently versioned GPS cache payload is defined in the [GPS/PPS contract](gps-pps.md). Old RF-prior payloads can still be read so an upgrade does not invalidate the retained UTC seed; they are never applied to RF or newly learned by production. Console RF-prior availability is false. UTC rate/skew persistence and the operator's manual PPM remain separate. No settings erase, journal migration, or manual-correction reset is required.

## Measurement boundaries

Statistical skew and indicated NTP offsets do not establish absolute UTC phase or physical carrier accuracy. [Independent clock measurements](microchrony-independent-measurement.md) define the reference and common-clock requirements. The portable engine's [integration and profile](../../src/microchrony/README.md) and the [external reference harness](../../tests/reference/README.md) describe software behavior and reproducible comparisons. Neither qualifies physical timing or RF.

## Si5351 trusted-local rate input

An engineering-enabled Si5351 allocation can measure a separate loopback against raw Pico time. Measurement only is the default. Trusted-local use requires an explicit oscillator uncertainty; a TCXO label alone does not establish it. Timestamped rate observations feed the existing μChrony engine without inventing NTP packets, UTC epochs or fresh network samples. Both μChrony-derived UTC and authenticated browser UTC receive this rate assistance through their existing mappings. Independent rate disagreement blocks all UTC admission until resolved; missing capture cannot clear it. Expiry retains the last learned rate center with ordinary conservative UTC holdover and the original UTC-source age. Raw hardware clocks and manual RF correction are unchanged. See [Si5351 measurement and execution](si5351.md).

## UTC uncertainty and admission

Control/1 reports UTC phase uncertainty with `utc_uncertainty_policy: informational`. Source age, NTP timeout, authentication, leap safety, source disagreement, ownership, output inhibition, launch-window mapping, and overflow checks retain their independent admission requirements. Frequency-reference quality and disagreement use rate uncertainty, which is distinct from the UTC phase estimate shown to the operator.

Changing the frequency estimate settles accumulated dispersion at the old bound before applying the new slope. A reference observation cannot retrospectively reduce phase uncertainty or refresh the UTC source timestamp.
