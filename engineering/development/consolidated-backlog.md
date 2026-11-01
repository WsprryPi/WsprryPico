# Consolidated backlog

This is the distinct TODO list for selected unfinished work. Current behavior is documented in the engineering guides. The reusable [cleanup instructions](repository-cleanup-prompt.md) apply to repository and harness cleanup. Item numbers remain stable.

## In progress

13. **Si5351**
    - ✅ Portable synthesis, local JobService/worker execution, bounded capture, atomic persisted allocations, current shared schemas and strict companion consumers, conditional Pico/Pi controls, and trusted-local μChrony rate input are implemented.
    - ⏳ Physical qualification and production enablement remain unfinished. Keep ordinary Si5351 output gated; require both production integration suites and adversarial review for coordinated candidates before delivery.
    - ▧ Qualify the actual Si5351/reference, I²C pull-ups/speed, physical transitions, shutdown/reset containment and mode waveforms. Ordinary firmware keeps Si5351 output activation disabled; engineering builds are explicit and physically unqualified.
    - GPS/PPS ingestion and automatic RF calibration remain outside this task.

## Possible future work

14. **Optional GPS UTC + PPS and improved holdover.**
    - Reuse the original MIT [μChrony engine](../../src/microchrony/README.md): bounded source histories, adaptive frequency estimation, source selection and combination, uncertainty propagation, and separate phase slewing and frequency correction. Add a reference-clock input path; GPS/PPS ingestion is not implemented today. Keep one clock-control loop rather than adding a second GPS servo or fabricating NTP packets for PPS.
    - Add a portable, timestamped reference-observation interface and a Pico SDK adapter that captures PPS against the raw monotonic clock. Pair each edge with a GPS message identifying its UTC second; PPS alone does not supply the date or second number. Qualify capture latency, cable delay, receiver time validity, GPS-to-UTC conversion, and leap handling. Preserve the portable engine's separation from hardware and transport.
    - Admit reference-clock observations using source-specific validity and error bounds, including missing, duplicate, mispaired, and implausible pulses. Keep network packet/delay filtering specific to NTP. Define GPS/PPS versus NTP disagreement, source selection, loss of lock, fallback, and reacquisition without weakening existing clock, launch, or RF quality gates. During holdover, propagate increasing uncertainty from the last valid observation; status reads and rejected pulses must not refresh its age.
    - Reuse and extend the Pico correction journal with source provenance. Restore a learned frequency only as a provisional restart seed, never as restored UTC, synchronization, or freshness. Keep the operator's persistent manual PPM separate from learned UTC and RF corrections.
    - Use qualified PPS frequency estimates as potential RF correction inputs only where the measured timer and selected RF engine have a verified common clock relationship. Independently qualify actual carrier error before claiming RF accuracy; improved UTC timing or narrower statistical bounds alone do not establish RF accuracy. Preserve manual correction and existing RF qualification requirements. See the [independent measurement boundaries](microchrony-independent-measurement.md).
    - Extend known-error tests and the external Chrony 4.9 reference comparison to paired GPS/PPS observations, drift, holdover, restart, source conflict, and reacquisition. Follow its documented [reference-clock rules](https://chrony-project.org/doc/4.9/chrony.conf.html#refclock) using original MIT code. Validate UTC timing and RF frequency separately against independent physical references, with measured path errors and explicit acceptance bounds. The retired Pico-to-Pi GPIO measurement path is not a prerequisite or input for this future GPS/PPS work; use a qualified reference source connected through the proposed input adapter.
15. **Advanced Pico scheduling and durable controller/member transfer**, after WsprryPi [issue 333](https://github.com/WsprryPi/WsprryPi/issues/333) research.
    - Define durable schedule identity, revisions, recovery, and duplicate prevention before expanding transfer. Pause the source authority, reconcile in-flight work, confirm inactive output, install the destination disabled, and enable only after saved-state readback. Interrupted cross-device writes must not duplicate dispatch; automatic offline fallback is not selected.
    - Design and validate Pico takeover/revocation before advertising parity with Pi. Preserve station data, schedules, credentials, watermarks, and takeover history during migration.
16. **Keying-envelope work.**
17. **Native iPhone consumer BLE app**, only for a need Wi-Fi does not meet.
18. **Enterprise/WPA3-only provisioning**, if a useful case emerges.
19. **Automatic NTP-server discovery and preference.**
20. **Additional LAN/page-delivery security**, if deployment needs change.
