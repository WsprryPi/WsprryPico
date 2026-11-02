# Consolidated backlog

This is the distinct TODO list for selected unfinished work. Current behavior is documented in the engineering guides. The reusable [cleanup instructions](repository-cleanup-prompt.md) apply to repository and harness cleanup. Item numbers remain stable.

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

## Si5351 Backlog

Item 13 is complete. The current software provides Si5351 synthesis and local execution, bounded input-only loopback capture, no-GPS UTC rate assistance, retained-rate continuity across jobs and capture loss, strict paired Control/1 interfaces, and informational UTC uncertainty. GPS/PPS ingestion and automatic RF calibration remain separate future work in item 14.

The final software pair is Pico `03340049379eeb074583f67dcf520fbd902e016c` and Pi `309db1d85c02ae51e8db1c5cb13583e9ae766b37`. Both required production integration suites and every other job passed in [paired CI run 41511319323](https://github.com/WsprryPi/WsprryPi/actions/runs/41511319323). The ordinary Pico candidate and matched Pi controller/UI are installed on C and wspr5, with saved settings preserved and idle/service state verified. Subsequent Pico changes affect documentation, the CI companion pin and test fixtures, without changing executable firmware sources.

The [continuity validation record](si5351-continuity-validation.md) describes deterministic checks, adversarial corrections, finite bench observations and ordinary-image smoke results. The retained developer bundle contains exact commands, source manifests, logs, installer receipts and image identities. The existing 85/85 engineering matrix and 51/51 WSPR decodes retain their original scope and image identities.

UTC phase uncertainty is displayed for operator judgment, without another configuration item or first-party phase-uncertainty veto. Independent source-validity, authentication, age, leap, disagreement, ownership and hardware safety checks, frequency-estimate quality selection, and explicit external WTP request contracts remain enforced. The ±500 ppb example is illustrative, not a requirement.

Reference hardware, its declared uncertainty allowance and hardware qualification are local operator decisions. Shared results do not certify hardware or guarantee absolute UTC accuracy. Environmental TCXO testing and independent absolute UTC/long-holdover hardware measurements are outside project completion criteria.
