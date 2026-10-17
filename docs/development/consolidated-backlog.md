# Consolidated backlog

Updated 2026-10-17. Finish the current work below before release. P15.1–P15.16
remain complete; P15.17–P15.20 retain their existing numbers and saved prompts.

## Finish now

1. **NTP Work**
   - Persistent standalone manual PPM.
   - NTP filtering and UTC rate discipline.
   - NTP-derived RF calibration.
2. **Amplifier-enable GPIO during transmissions.** Assert the configured enable
   pin before RF starts and return it inactive after completion, stop, abort
   or fault.
3. **Current contract reconciliation.** Align current API, carrier, GPIO-drive
   and build descriptions with the accepted implementation.
4. **Software/build CI and deployment images.** Run checks and produce usable
   UF2 images with version/source identity, checksums and a manifest before
   release efforts. Use the CI image for the following decode and publication.
5. **Short WSPR Type 2/3 decode.** Test one Type 2 → Type 3 pair at one frequency
   on one Pico with `wsprd`; record the result and associated evidence closeout.
6. **P15.17 — Testing prerelease.** Publish the verified CI image, manifest and
   checksums. [Saved prompt](phase15-17-execution-prompt.md).
7. **P15.18 — USB installer.** Standalone and WsprryPi access, preserving saved
   settings. [Saved prompt](phase15-18-execution-prompt.md).
8. **P15.19 — Impeccable UI review**, including provisioning.
   [Saved prompt](phase15-19-execution-prompt.md).
9. **P15.20 — Operator documentation.** Final instructions, screenshots and
   Read the Docs Community publication.

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
