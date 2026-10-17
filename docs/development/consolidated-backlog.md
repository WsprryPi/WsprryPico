# Consolidated backlog

Updated 2026-10-17. Finish the current work below before release. Previously
completed work remains complete; saved execution prompts are retained.

## Finish now

Status: ✅ finished; ⏳ in flight; ▧ not started.

1. ✅ **Current contract reconciliation.** Align current API, carrier, GPIO-drive
   and build descriptions with the accepted implementation.
2. ▧ **Short WSPR Type 2/3 decode.** Test one Type 2 → Type 3 pair at
   14.097100 MHz (20 m) on one Pico with `wsprd`; record the result and associated
   evidence closeout. [Saved prompt](short-wspr-type23-decode-execution-prompt.md).
3. ▧ **Amplifier-enable GPIO during transmissions.** Assert the configured enable
   pin before RF starts and return it inactive after completion, stop, abort
   or fault. [Saved prompt](amplifier-enable-execution-prompt.md).
4. ▧ **NTP Work** [Saved prompt](ntp-work-execution-prompt.md).
   - ▧ Persistent standalone manual PPM.
   - ▧ NTP filtering and UTC rate discipline.
   - ▧ NTP-derived RF calibration.
5. ▧ **Impeccable UI review**, including provisioning.
   [Saved prompt](phase15-19-execution-prompt.md).
6. ▧ **USB installer.** Standalone and WsprryPi access, preserving saved
   settings. [Saved prompt](phase15-18-execution-prompt.md).
7. ▧ **Software/build CI and deployment images.** Run checks and produce usable
   UF2 images with version/source identity, checksums and a manifest before
   release efforts. Use the CI image for decode verification and publication.
8. ▧ **Operator documentation.** Final instructions, screenshots and
   Read the Docs Community publication.
9. ▧ **Testing prerelease.** Publish the verified CI image, manifest and
   checksums. [Saved prompt](phase15-17-execution-prompt.md).

## Remain in backlog for future

- **Si5351**
  - Optional external-engine enhancement.
  - CLK2 calibration only if that engine is selected.
- **Optional amplifier settling and lead/tail timing.**
- **LPF/band-selector control**, if economically useful.
- **Optional GPS UTC + PPS and improved holdover.**
- **Advanced Pico scheduling and durable controller/member transfer**, after
  WsprryPi [issue 333](https://github.com/WsprryPi/WsprryPi/issues/333) research.
- **Keying-envelope work.**
- **Native iPhone consumer BLE app**, only for a need Wi-Fi does not meet.
- **Enterprise/WPA3-only provisioning**, if a useful case emerges.
- **Automatic NTP-server discovery and preference.**
- **Additional LAN/page-delivery security**, if deployment needs change.
