# Consolidated backlog

Selected work is listed below, with completed items marked explicitly. Current product behavior is documented in the maintained guides. The reusable [cleanup instructions](repository-cleanup-prompt.md) govern explicit repository and harness cleanup requests.

## Operator validation

1. [x] ✅ **Windows browser recovery and setup-Wi-Fi association.** See the [USB Console walkthrough](../../docs/usb.md). Windows command-line installation remains unsupported.

## Backlog TODO

### Combined UI / backend

2. [x] ✅ **Syslog over USB.** Independent Logging channel, Pico export, Pi collection and both management UIs; see the [contract and applicability](usb-logging.md).
3. [x] ✅ **Syslog over UDP.** Independent Pico/Pi export, selected USB forwarding, collector and both UIs; see the [contract and applicability](udp-logging.md). Policies default off; local submission does not confirm receipt.
4. [x] ✅ **LPF/band-selector control.** Named GPIO selection, complete-job coverage, release/settling and amplifier ordering; see the [contract and applicability](lpf-band-selector.md).

### Backend

5. [x] ✅ **Optional amplifier settling and lead/tail timing.** Independent 0–1000 ms intervals with 200 ms defaults; see the [contract and applicability](amplifier-enable.md#lead-and-tail-timing). Amplifier enable remains disabled by default.

### UI

6. [x] ✅ **WsprryPi-style contextual status console with Reset Pico.** See the [status-console contract](status-console.md). Character-level progression remains unimplemented.
7. [x] ✅ **Furl sections by default.** See [browser sections](browser-pages.md#sections-and-navigation).
8. [x] ✅ **Hostname lock control and password modal.** See [browser access](browser-pages.md#browser-access).
9. [x] ✅ **Grouped links to furled sections.** See [sections and navigation](browser-pages.md#sections-and-navigation).
10. [x] ✅ **Top links.** Close settings disclosures and return to status while preserving drafts; see [browser sections](browser-pages.md#sections-and-navigation).

## Possible future work

11. **Si5351**
    - Optional external-engine enhancement.
    - CLK2 calibration only if that engine is selected.
12. **Optional GPS UTC + PPS and improved holdover.**
    - Reuse the original MIT [μChrony engine](../../src/microchrony/README.md): bounded source histories, adaptive frequency estimation, source selection and combination, uncertainty propagation, and separate phase slewing and frequency correction. Add a reference-clock input path; GPS/PPS ingestion is not implemented today. Keep one clock-control loop rather than adding a second GPS servo or fabricating NTP packets for PPS.
    - Add a portable, timestamped reference-observation interface and a Pico SDK adapter that captures PPS against the raw monotonic clock. Pair each edge with a GPS message identifying its UTC second; PPS alone does not supply the date or second number. Qualify capture latency, cable delay, receiver time validity, GPS-to-UTC conversion and leap handling. Preserve the portable engine's separation from hardware and transport.
    - Admit reference-clock observations using source-specific validity and error bounds, including missing, duplicate, mispaired and implausible pulses. Keep network packet/delay filtering specific to NTP. Define GPS/PPS versus NTP disagreement, source selection, loss of lock, fallback and reacquisition without weakening existing clock, launch or RF quality gates. During holdover, propagate increasing uncertainty from the last valid observation; status reads and rejected pulses must not refresh its age.
    - Reuse and extend the Pico correction journal with source provenance. Restore a learned frequency only as a provisional restart seed, never as restored UTC, synchronization or freshness. Keep the operator's persistent manual PPM separate from learned UTC and RF corrections.
    - Use qualified PPS frequency estimates as potential RF correction inputs only where the measured timer and selected RF engine have a verified common clock relationship. Independently qualify actual carrier error before claiming RF accuracy; improved UTC timing or narrower statistical bounds alone do not establish RF accuracy. Preserve manual correction and existing RF qualification requirements. See the [independent measurement boundaries](microchrony-independent-measurement.md).
    - Extend known-error tests and the external Chrony 4.9 reference comparison to paired GPS/PPS observations, drift, holdover, restart, source conflict and reacquisition. Follow its documented [reference-clock rules](https://chrony-project.org/doc/4.9/chrony.conf.html#refclock) using original MIT code. Validate UTC timing and RF frequency separately against independent physical references, with measured path errors and explicit acceptance bounds. The retired Pico-to-Pi GPIO measurement path is not a prerequisite or input for this future GPS/PPS work; use a qualified reference source connected through the proposed input adapter.
13. **Advanced Pico scheduling and durable controller/member transfer**, after WsprryPi [issue 333](https://github.com/WsprryPi/WsprryPi/issues/333) research.
14. **Keying-envelope work.**
15. **Native iPhone consumer BLE app**, only for a need Wi-Fi does not meet.
16. **Enterprise/WPA3-only provisioning**, if a useful case emerges.
17. **Automatic NTP-server discovery and preference.**
18. **Additional LAN/page-delivery security**, if deployment needs change.
