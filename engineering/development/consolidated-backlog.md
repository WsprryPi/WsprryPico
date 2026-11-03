# Consolidated backlog

This is the distinct TODO list for selected unfinished work, with completed items marked below. Current behavior is documented in the engineering guides. The reusable [cleanup instructions](repository-cleanup-prompt.md) apply to repository and harness cleanup. Item numbers remain stable.

## Possible future work

14. ⏳ **GPS/PPS qualification and GP2 direct-output calibration test.** Optional GPS UTC/PPS ingestion, separate oscillator correction, location/day-night policy, retained-rate holdover and coordinated Pi consumers are implemented on the feature branches. The [GPS/PPS contract](gps-pps.md) describes current behavior; the [validation record](gps-pps-validation.md) identifies the tested implementation pair, installed image, completed checks and measurement limits.
    - **Selected GP2 transmission test:** validate GPS-derived correction on the direct GPIO RF engine. Establish a separately verified GP2 conducted path with appropriate filtering/attenuation into the SDR and no antenna; the tested Si5351 CLK0 path does not qualify GP2. Record board, exact firmware/developer bundle, active system-clock profile, GPIO drive, reference identity and receiver settings before transmission.
    - Verify the raw timer and direct RF engine's common clock relationship. Compare finite manual-zero baseline and GPS-corrected transmissions against an independently identified frequency reference on representative frequencies within the active clock profile's supported range. Exercise manual residual trim once, delayed ARM/frozen correction and a complete WSPR interval; record original observation age, uncertainty, raw capture hashes and an explicit finite RF budget. Evaluate carrier accuracy separately from UTC phase and receiver-relative timing.
    - Restore and verify the original Si5351 CLK0/CLK2 loopback configuration, GPS settings, manual correction, schedules, ownership, service state and valid same-board installer reference after the GP2 campaign. Preserve legitimate schedule-watermark advances and retain the exact recovery/developer bundle.
    - Independently bounded absolute RF launch UTC and consistently improved absolute carrier accuracy remain unestablished by the current conducted measurements. Retain those limits until supporting measurements exist. Source loss/recovery currently has software evidence only; a live PPS cable-disconnection test is outside the selected test scope.
15. **Advanced Pico scheduling and durable controller/member transfer**, after WsprryPi [issue 333](https://github.com/WsprryPi/WsprryPi/issues/333) research.
    - Define durable schedule identity, revisions, recovery, and duplicate prevention before expanding transfer. Pause the source authority, reconcile in-flight work, confirm inactive output, install the destination disabled, and enable only after saved-state readback. Interrupted cross-device writes must not duplicate dispatch; automatic offline fallback is not selected.
    - Design and validate Pico takeover/revocation before advertising parity with Pi. Preserve station data, schedules, credentials, watermarks, and takeover history during migration.
16. **Keying-envelope work.**
17. **Native iPhone consumer BLE app**, only for a need Wi-Fi does not meet.
18. **Enterprise/WPA3-only provisioning**, if a useful case emerges.
19. **Automatic NTP-server discovery and preference.**
20. **Additional LAN/page-delivery security**, if deployment needs change.

## Completed work

13. ✅ **Si5351 — complete and merged into `devel`.**

Item 13 is complete. The current software provides Si5351 synthesis and local execution, bounded input-only loopback capture, no-GPS UTC rate assistance, retained-rate continuity across jobs and capture loss, strict paired Control/1 interfaces, and informational UTC uncertainty. Optional GPS/PPS ingestion and automatic RF correction are implemented; their remaining qualification and selected GP2 test are tracked in item 14.

The Si5351 validation pair was Pico `03340049379eeb074583f67dcf520fbd902e016c` and Pi `309db1d85c02ae51e8db1c5cb13583e9ae766b37`. Both required production integration suites and every other job passed in [paired CI run 41511319323](https://github.com/WsprryPi/WsprryPi/actions/runs/41511319323). The ordinary Pico candidate and matched Pi controller/UI were installed on C and wspr5 for that validation, with saved settings preserved and idle/service state verified. The later GPS/PPS implementation and its separately identified installed image are recorded in the [GPS/PPS validation record](gps-pps-validation.md).

The [continuity validation record](si5351-continuity-validation.md) describes deterministic checks, adversarial corrections, finite bench observations and ordinary-image smoke results. The retained developer bundle contains exact commands, source manifests, logs, installer receipts and image identities. The existing 85/85 engineering matrix and 51/51 WSPR decodes retain their original scope and image identities.

UTC phase uncertainty is displayed for operator judgment, without another configuration item or first-party phase-uncertainty veto. Independent source-validity, authentication, age, leap, disagreement, ownership and hardware safety checks, frequency-estimate quality selection, and explicit external WTP request contracts remain enforced. The ±500 ppb example is illustrative, not a requirement.

Reference hardware, its declared uncertainty allowance and hardware qualification are local operator decisions. Shared results do not certify hardware or guarantee absolute UTC accuracy. Environmental TCXO testing and independent absolute UTC/long-holdover hardware measurements are outside project completion criteria.
