# Consolidated backlog

Updated 2026-10-18. Finish the current work below before release. Previously
completed work remains complete. Retain handoffs needed for selected unfinished
work; retire obsolete execution prompts under the cleanup guidance.

## Finish now

Status: ✅ finished; ⏳ in flight; ▧ not started.

1. ✅ **Current contract reconciliation.** Align current API, carrier, GPIO-drive
   and build descriptions with the accepted implementation.
2. ✅ **Short WSPR Type 2/3 decode.** Test one Type 2 → Type 3 pair at
   3.570100 MHz (80 m), selected by the operator during execution, on one Pico
   with `wsprd`; record the result and associated
   evidence closeout. [Result](short-wspr-type23-decode-results.md).
3. ✅ **Amplifier-enable GPIO during transmissions.** Assert the configured enable
   pin before RF starts and return it inactive after completion, stop, abort
   or fault. See [amplifier enable](amplifier-enable.md).
4. ⏳ **NTP Work** [Saved prompt](ntp-work-execution-prompt.md).
   - ✅ Persistent standalone manual PPM.
   - ✅ NTP filtering and UTC rate discipline.
   - ⏳ **Implement μChrony for NTP-derived RF calculation.** Replace prior
     estimators with an original MIT implementation; complete Chrony 4.9
     conformance and target/RF qualification while preserving independent
     manual PPM and launch limits.
5. ✅ **Impeccable UI review**, including provisioning; accepted and closed.
   VoiceOver testing is closed as not required.
   Installer coverage is deferred.
6. ✅ **Software/build CI and deployment images.** Run checks and produce usable
   UF2 images with version/source identity, checksums and a manifest before
   release efforts. Use the CI image for decode verification and publication.
   [Build and image guide](software-build-ci.md).
7. ▧ **USB installer.** Standalone and WsprryPi access, preserving saved
   settings; default to the latest verified saved main CI image, with explicit
   devel selection.
   [Saved prompt](phase15-18-execution-prompt.md).
8. ⏳ **Repository and work-harness cleanup.** Remove obsolete project artifacts
   and rewrite operator-facing prose around current capabilities. Keep needed
   technical material in engineering documentation; add no documentation
   placeholder or future promise. [Cleanup guidance](repository-cleanup-prompt.md).
   [Saved prompt](repository-cleanup-execution-prompt.md).
9. ▧ **Operator documentation.** Final instructions, screenshots and
   Read the Docs Community publication.
   [Saved prompt](operator-documentation-execution-prompt.md).
10. ▧ **Testing prerelease.** Publish the verified CI image, manifest and
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
