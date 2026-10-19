# Retired Pico-to-Pi clock pulse measurement

The Pico-to-Pi GPIO pulse measurement path is removed. Normal firmware does
not implement the USB Console `CLOCKPROBE` command, reserve GP22 for metrology,
or generate timing pulses. The live Linux GPIO reader and input-audit helper
are removed from the maintained host tools. There is no required Pico-to-Pi
GPIO timing connection; existing measurement signal leads can be disconnected.
The Pi's own GPS HAT/PPS and services are independent and are unchanged.

This was an output measurement path, not a PPS input that synchronized either
Pico. Repeated unexpected dual-input events prevented a reliable measurement
campaign. No electrical or kernel root cause was established. Historical raw
captures and frozen private helpers remain evidence of their recorded images;
they are not active tools or instructions to repeat the retired experiment.

μChrony remains the original MIT UTC discipline engine. NTP-derived RF
calibration is rejected for current use; RF correction uses persistent manual
PPM. The [NTP closeout](ntp-work-closeout.md) closes punchlist item 4.3.
The [last hardware attempt](microchrony-control-fixes-results.md) retains the
fault and adverse measurements. Future direct GPS/PPS input belongs to the
[backlog](consolidated-backlog.md#remain-in-backlog-for-future), with a qualified
reference input adapter rather than a Pico-to-Pi pulse loop.
