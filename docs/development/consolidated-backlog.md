# Consolidated backlog

Updated 2026-10-19. Finish the current work below before release. Previously
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
4. ✅ **NTP Work — closed.**
   - ✅ Persistent standalone manual PPM.
   - ✅ NTP filtering and UTC rate discipline using the original MIT μChrony engine.
   - ✅ **4.3: RF-calibration investigation closed — rejected for current use.**
     Retain μChrony for UTC discipline and the future GPS/PPS foundation. Internet
     NTP has not demonstrated reliable RF-calibration benefit. RF correction uses
     the saved manual PPM only. The Pico-to-Pi GPIO pulse measurement path is removed.
     [Decision and closeout](ntp-work-closeout.md).
5. ✅ **Impeccable UI review**, including provisioning; accepted and closed.
   VoiceOver testing is closed as not required.
   Installer coverage is deferred.
6. ✅ **Software/build CI and deployment images.** Run checks and produce usable
   UF2 images with version/source identity, checksums and a manifest before
   release efforts. Use the CI image for decode verification and publication.
   [Build and image guide](software-build-ci.md).
7. ✅ **USB installer.** Standalone and WsprryPi access, preserving saved
   settings; default to the latest verified saved main CI image, with explicit
   devel selection.
   [Installer guide](usb-installer.md) and [acceptance record](usb-installer-results.md).
8. ✅ **Repository and work-harness cleanup.** Remove obsolete project artifacts
   and rewrite operator-facing prose around current capabilities. Keep needed
   technical material in engineering documentation; add no documentation
   placeholder or future promise. [Cleanup guidance](repository-cleanup-prompt.md).
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
  - Reuse the original MIT [μChrony engine](../../src/microchrony/README.md):
    bounded source histories, adaptive frequency estimation, source selection
    and combination, uncertainty propagation, and separate phase slewing and
    frequency correction. Add a reference-clock input path; GPS/PPS
    ingestion is not implemented today. Keep one clock-control loop rather than
    adding a second GPS servo or fabricating NTP packets for PPS.
  - Add a portable, timestamped reference-observation interface and a Pico SDK
    adapter that captures PPS against the raw monotonic clock. Pair each edge
    with a GPS message identifying its UTC second; PPS alone does not supply
    the date or second number. Qualify capture latency, cable delay, receiver
    time validity, GPS-to-UTC conversion and leap handling. Preserve the
    portable engine's separation from hardware and transport.
  - Admit reference-clock observations using source-specific validity and error
    bounds, including missing, duplicate, mispaired and implausible pulses.
    Keep network packet/delay filtering specific to NTP. Define GPS/PPS versus
    NTP disagreement, source selection, loss of lock, fallback and reacquisition
    without weakening existing clock, launch or RF quality gates. During
    holdover, propagate increasing uncertainty from the last valid observation;
    status reads and rejected pulses must not refresh its age.
  - Reuse and extend the Pico correction journal with source provenance.
    Restore a learned frequency only as a provisional restart seed, never as
    restored UTC, synchronization or freshness. Keep the operator's persistent
    manual PPM separate from learned UTC and RF corrections.
  - Use qualified PPS frequency estimates as potential RF correction inputs
    only where the measured timer and selected RF engine have a verified common
    clock relationship. Independently qualify actual carrier error before
    claiming RF accuracy; improved UTC timing or narrower statistical bounds
    alone do not establish RF accuracy. Preserve manual correction and existing
    RF qualification requirements. See the [independent measurement
    boundaries](microchrony-independent-measurement.md).
  - Extend known-error tests and the external Chrony 4.9 reference comparison
    to paired GPS/PPS observations, drift, holdover, restart, source conflict
    and reacquisition. Follow its documented [reference-clock
    rules](https://chrony-project.org/doc/4.9/chrony.conf.html#refclock) using
    original MIT code. Validate UTC timing and RF frequency separately against
    independent physical references, with measured path errors and explicit
    acceptance bounds. The retired Pico-to-Pi GPIO measurement path is not a
    prerequisite or input for this future GPS/PPS work; use a qualified reference
    source connected through the proposed input adapter.
- **Advanced Pico scheduling and durable controller/member transfer**, after
  WsprryPi [issue 333](https://github.com/WsprryPi/WsprryPi/issues/333) research.
- **Keying-envelope work.**
- **Native iPhone consumer BLE app**, only for a need Wi-Fi does not meet.
- **Enterprise/WPA3-only provisioning**, if a useful case emerges.
- **Automatic NTP-server discovery and preference.**
- **Additional LAN/page-delivery security**, if deployment needs change.
