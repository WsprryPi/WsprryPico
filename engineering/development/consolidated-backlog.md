# Consolidated backlog

This is the distinct TODO list for selected unfinished work, with completed and closed items marked below. Current behavior is documented in the engineering guides. The reusable [cleanup instructions](repository-cleanup-prompt.md) apply to repository and harness cleanup. Item numbers remain stable.

## Possible future work

No remaining TODO items.

## Closed — will not do

15. **Advanced Pico scheduling and durable controller/member transfer — closed/will not do.** Handled from WsprryPi.
16. **Keying-envelope work — closed/will not do.** Hardware is the operator's responsibility.

17. **Native iPhone consumer BLE app — closed/will not do.** Wi-Fi is sufficient.

18. **Enterprise/WPA3-only provisioning — closed/will not do.** Not needed for most operators.

19. **Automatic NTP-server discovery and preference — closed/will not do.** Manual NTP configuration is sufficient.

20. **Additional LAN/page-delivery security — closed/will not do.** No additional needs noted.

## Completed work

13. ✅ **Si5351 — complete and merged into `devel`.**

Item 13 is complete. The current software provides Si5351 synthesis and local execution, bounded input-only loopback capture, no-GPS UTC rate assistance, retained-rate continuity across jobs and capture loss, strict paired Control/1 interfaces, and informational UTC uncertainty. Optional GPS/PPS ingestion and automatic RF correction are implemented; their independent measurement limits are recorded with completed item 14.

The Si5351 validation pair was Pico `03340049379eeb074583f67dcf520fbd902e016c` and Pi `309db1d85c02ae51e8db1c5cb13583e9ae766b37`. Both required production integration suites and every other job passed in [paired CI run 41511319323](https://github.com/WsprryPi/WsprryPi/actions/runs/41511319323). The ordinary Pico candidate and matched Pi controller/UI were installed on C and wspr5 for that validation, with saved settings preserved and idle/service state verified. The later GPS/PPS implementation and its separately identified installed image are recorded in the [GPS/PPS validation record](gps-pps-validation.md).

The [continuity validation record](si5351-continuity-validation.md) describes deterministic checks, adversarial corrections, finite bench observations and ordinary-image smoke results. The retained developer bundle contains exact commands, source manifests, logs, installer receipts and image identities. The existing 85/85 engineering matrix and 51/51 WSPR decodes retain their original scope and image identities.

UTC phase uncertainty is displayed for operator judgment, without another configuration item or first-party phase-uncertainty veto. Independent source-validity, authentication, age, leap, disagreement, ownership and hardware safety checks, frequency-estimate quality selection, and explicit external WTP request contracts remain enforced. The ±500 ppb example is illustrative, not a requirement.

Reference hardware, its declared uncertainty allowance and hardware qualification are local operator decisions. Shared results do not certify hardware or guarantee absolute UTC accuracy. Environmental TCXO testing and independent absolute UTC/long-holdover hardware measurements are outside project completion criteria.

14. ✅ **GPS UTC + PPS, RF calibration, location and improved holdover — complete and merged into `devel`.** Optional GPS UTC/PPS ingestion, separate oscillator correction, location/day-night policy, retained-rate holdover and coordinated Pi consumers are implemented and merged into `devel`. The [GPS/PPS contract](gps-pps.md) describes current behavior; the [validation record](gps-pps-validation.md) identifies exact source/image pairs, the completed Si5351 and GP2 measurements, restoration and limitations.
    - **Selected GP2 transmission test completed:** manual-zero and GPS-corrected five-second tones on 160 m, 60 m and 10 m, once-only manual residual, delayed ARM/frozen correction, one complete decoded WSPR interval and exact handback passed on the recorded 138 MHz/4 mA conducted setup. Delayed serial labels use the original captured PPS edge. Control-path memory was corrected without reducing safety reserves, and the controller resumed one logical WTP session per boot. Cumulative DUT RF was 170.592 seconds within the finite 200-second budget; no antenna or PPS disconnection was used.
    - Independently bounded absolute RF launch UTC and consistently improved absolute carrier accuracy remain unestablished. Retain those limits until supporting measurements exist. Source loss/recovery has software evidence only; a live PPS cable-disconnection test is outside the selected scope.
