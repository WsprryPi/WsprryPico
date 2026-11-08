# Pico RF qualification

The Qualification Harness provides a distinct Pico USB `complete-test` route.
It submits complete finite WTP jobs to RP2350 and uses separate USB management
for discovery, current-control validation, configuration observations, and
output readback. It uses the selected Pico's production encoders, exact-count
SoapySDR captures, independent Morse references, carrier analysis, and WSJT-X
`wsprd`. Pico is not represented as a Pi process or Pi GPIO/I²C backend.

The maintained [Harness campaign guide](https://github.com/WsprryPi/WsprryPi-Qualification-Harness/blob/codex/pico-rf-harness/docs/development/pico-rf-campaign.md)
contains configuration fields, the source-bound compiler build, CLI commands,
evidence validation, platform limits, and software acceptance. The implementation
is on the Harness `codex/pico-rf-harness` branch until its normal review/merge;
select the intended actual ref rather than assuming availability on `devel`.

## Campaign coverage

| Pico RF engine | GPS/PPS use | Correction subcases |
| --- | --- | --- |
| Direct GP2 / PIO-DMA | Disabled | Manual; explicit supported non-GPS UTC source |
| Direct GP2 / PIO-DMA | Enabled | Automatic correction off and on |
| Supported Si5351 / CLK0 | Disabled | Manual; explicit supported non-GPS UTC source |
| Supported Si5351 / CLK0 | Enabled | Automatic correction off and on |

Every configuration covers TONE, WSPR, QRSS, FSKCW, and DFCW. Each selected
mode requires three independent complete job/capture transactions. Three
on/off cycles inside a Tone job remain one observation. Each WSPR observation
has an additional finite carrier gate. Live WSPR qualification currently uses
ordinary Type 1 station messages; paired Type 2/3 plans are refused before
USB access because the maintained decode identity classifier is Type 1.

GPS disablement is observed in firmware; physical cable removal is unnecessary.
GPS-enabled rows require usable paired serial/PPS/time observations. Manual
trim, automatic RF correction, UTC discipline, and receiver-only calibration
are separate dimensions. Automatic correction requires the product's qualified
observations and matching frozen job provenance, with no manual fallback.
Si5351 correction uses the existing CLK2/input-only GP7 feedback and supported
hardware profile.

## Setup and execution boundaries

Campaign setup is read-only. Select and verify the engine, pins, time source,
GPS/PPS, correction, and disabled schedules through ordinary product setup
before running. The Harness does not silently install firmware, restart the
board, change settings, set UTC, or take over another owner's job. Install
firmware separately using the [shared installer](usb-installer.md), retain the
exact bundle, and preserve its same-board reference.

Portable composition, rehearsal, analysis, and result validation support
macOS, Linux, and native Windows. Live USB requires native macOS or Linux
on the host that physically owns both Pico USB and the SDR. Remote USB/SDR
delegation and Windows/WSL live USB are refused before device access. A
controller may invoke the installed command on the bench host through its
separately authorized management connection.

Use current conducted-path evidence for the selected output, termination,
attenuation, combiner/filter routing, antenna disconnection, SDR identity,
and safe input basis. Historical wiring records and example configurations
are not physical evidence. Identify the intended board and both USB CDC roles
before opening them.

The Harness admits idle state before opening WTP, bounds capture and job
lifetimes, verifies RF-off preamble before ARM, renews only its own lease,
never replays an uncertain mutation, and reconciles/aborts/releases only its
owned job. Cleanup checks boot-bound output inactivity and Si5351 register
disablement where applicable. Final settings readback must match the original
state. A reset, disconnect, changed owner, or unverified receiver/transmitter
cleanup prevents qualification. Existing schedules are not resumed implicitly.

## Evidence and claims

Keep private run bundles outside Git. They retain the requested/frozen plan,
compiler/encoder and separate Harness analyzer identities, observed firmware
and boot, actual USB topology, settings and correction snapshots, complete
WTP transactions and management ACK/byte audit, exact-count IQ metadata,
full decoder output, analysis, and final cleanup/settings state. Validate them
with the maintained `validate-complete-test` route before interpreting results.
A compiler source revision does not establish the installed firmware bytes;
exact-artifact qualification must bind the retained installer bundle separately.

Software fixture success, rehearsal, and synthetic IQ establish no physical
USB, RP2350 timing, installed-image, or RF acceptance. Live results are specific
to the recorded board, engine, band, modes, clock/correction state, receiver,
and conducted path. Decode success is not spectral compliance or calibrated
power. The [RC.2 checklist](rc2-release-checklist.md) separates Harness delivery,
exact-artifact physical qualification, and publication.

The [Si5351 investigation disposition](gps-pps-validation.md#bounded-investigation-closure-2026-11-08)
is finally closed as inconclusive and resolution-limited. Automatic correction
remains available for experimentation. Campaigns verify its selected operation
without requiring it to improve accuracy or expanding acquisition windows.
