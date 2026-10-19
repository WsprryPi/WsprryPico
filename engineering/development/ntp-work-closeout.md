# NTP work closeout

Punchlist item **4.3 is closed by rejection of NTP-derived RF calibration**.
The complete NTP Work group is closed: persistent manual PPM and μChrony UTC
discipline are retained. GPS/PPS is a selected future foundation, not a current
input or a promise of qualified RF calibration.

## Current product behavior

- The original MIT μChrony engine filters NTP observations, selects sources,
  controls UTC phase/rate and propagates uncertainty. The last learned UTC rate
  persists as a provisional restart seed. It never restores UTC, synchronization
  or freshness by itself.
- RF carrier correction uses the persistent manual PPM value only. It remains
  independent of UTC control and retains its existing range, sign, adjustment
  consent, preparation/pair freeze and storage behavior.
- Live NTP estimates and saved NTP RF priors cannot select an RF correction.
  The former automatic-selection code and production RF-prior staging are
  removed. This is a product decision, not a weakened qualification threshold.
- The Pico-to-Pi GPIO pulse measurement implementation, Console command, live
  host reader and input-audit tooling are removed. Normal firmware has no
  `CLOCKPROBE` command or GP22 metrology role. No Pico-to-Pi GPIO timing link is
  required. Existing measurement signal leads can be disconnected.
- The Pi's GPS HAT/PPS input, chrony/gpsd services, and USB/network time paths
  are independent and unchanged. No RF, clock freshness, uncertainty, ownership,
  launch or physical-output gate is relaxed.

## Decision basis

The [Chrony 4.9 captured-input comparison](microchrony-lead-replay-results.md)
substantially closes the bounded software disagreement. It also shows why
reference agreement is insufficient: the same Internet measurements can give
both controllers a biased frequency estimate.

The [completed physical comparison](microchrony-lead-layout-results.md) retained
mixed/adverse rate results. The [subsequent firmware rerun](microchrony-control-fixes-results.md)
loaded the fixes on both boards but stopped after repeated uncommanded events
on both Pi measurement inputs. Only four pulses per board were retained.
A's indicated UTC error grew during a transient positive rate estimate; B's
phase reduction came mainly from slewing. Initial RF observations found one
useful and one adverse inferred rate correction, with no automatic RF correction
actually applied. Reliable carrier improvement was not demonstrated.

These results do not reject μChrony as a UTC discipline engine, prove that all
NTP oscillator estimates are harmful, or qualify an electrical/kernel cause
for the GPIO fault. They support ending the current Internet-NTP RF-calibration
work and retiring its unreliable Pico-to-Pi measurement path. Historical raw
evidence, numerical reports and frozen private helpers are retained; no old
campaign is resumed or repeated as part of this closeout.

## Compatibility and persistence

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

## GPS/PPS foundation

The [GPS/PPS backlog](consolidated-backlog.md#remain-in-backlog-for-future)
reuses μChrony's bounded histories, adaptive estimation, source selection,
uncertainty and separate phase/frequency control. It calls for a timestamped
reference-observation adapter and UTC-second pairing, rather than a second
servo or fabricated NTP packets. GPS/PPS ingestion is not implemented now.

Future input latency, cable/reference errors, source disagreement, loss/recovery
and holdover require their own validation. Any future GPS/PPS-derived RF
correction also requires a verified common-clock relationship and independent
physical carrier qualification. The retired Pico-to-Pi pulse link is not a
prerequisite for that work.

## Validation and deployment

All 119 host tests passed. Five affected checks passed again after the final
legacy-mode assertion: NTP work/replay, RF-calibration browser, local USB
management and Console INFO formatting. Coverage includes refusal of NTP RF mode
without a manual-value write, legacy flags/priors without RF authority, retained
manual preparation/pair freezing, UTC persistence and unchanged source/launch
limits. The normal firmware cross-build passed its linked RF, flash-layout,
stack, heap and adapter checks. Its application bytes and link map contain no
`CLOCKPROBE` command or `ClockProbe` component.

Both identified Pico 2 W boards were loaded with that normal developer image on
2026-10-19. Its source identity is `650ead37e161-dirty`, based on the preceding
commit with this retirement change applied; it is not a clean CI/release image.
UF2 SHA-256:
`3ff3fa321289b59a21aef2dcc63ada2b841f519e8265ac5148d47a56720fff57`.

| Board | USB serial | New boot ID | Restored UTC rate seed |
|---|---|---|---:|
| A | `0BF4B4AEC9FFB344` | `4d82269d508e4350eebc3bfa5a53d161` | −280 ppb |
| B | `CDDBF8767C506C07` | `b56c1e2521121b0247d206e4bab9184f` | +1484 ppb |

Serial/physical-parent checks, full-flash backups, programmed-image verification
and byte-for-byte reserved-region comparisons passed. Final readbacks confirmed
unchanged Bohica/`pool.ntp.org` settings, manual `0.000` ppm, disabled schedules
and both boards inactive/unowned. Fresh SNTP observations were 21.802 seconds
old on A and 14.182 seconds old on B. Each board refused an identity/revision-bound
NTP RF-mode request with HTTP 400 `ntp_rf_rejected`; saved manual correction and
revision remained unchanged. UTC seeds restored independently of RF selection.

Read-only Pi line inspection found GPIO22/GPIO23 unused with no pull or assigned
function; GPIO17 remained owned by `pps@11`. No GPIO request, pulse, RF job,
source-setting write or Pi-service change was performed. Signal leads were not
physically removed by software and can be disconnected. These are removal and
preservation checks, not new UTC-accuracy, RF-accuracy or electrical measurements.

The adversarial review found obsolete candidate/fallback wording in current
guides. Those passages were corrected; reassessment found no remaining actionable
issue. All 305 local documentation paths/anchors checked at closeout resolved.
Private deployment receipts, hashes and backups are retained under
`build/microchrony-retirement-20261019/` and the matching
`/home/pi/microchrony-retirement-20261019` directory on wspr5, outside Git.

The paused pulse-test monitor remains retired. Preserved historical captures
and backups are private and are not active harnesses or current operating
instructions. This decision makes no claim that the historical GPIO measurement
fault was repaired.
