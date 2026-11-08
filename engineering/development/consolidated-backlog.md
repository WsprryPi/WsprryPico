# Consolidated backlog

This is the distinct TODO list for selected unfinished work, with completed and closed items marked below. Current behavior is documented in the engineering guides. The reusable [cleanup instructions](repository-cleanup-prompt.md) apply to repository and harness cleanup. Item numbers remain stable.

Status: ✅ complete; ⏳ in progress; ▧ not started. Closed/will-not-do items are labelled separately.

## Selected unfinished work

24. ✅ **Remove the initial time/calibration review link — complete.** Automatic timeout and calibration read errors stay beside their controls without a top-level save-result link. Transmitter status retains current clock and transmission observations; Time and calibration remains available through normal navigation and bookmarks. Explicit failed reads and unconfirmed saves retain their recovery links. See [contextual saved-state review](browser-pages.md#contextual-saved-state-review).

25. ✅ **Hostname editing in the captive portal.** After the first Wi-Fi save, the authenticated Wi-Fi/Host editor can save a hostname before station setup. The saved name survives later setup and activates after an explicit restart. See the [hostname transaction guide](hostname.md).

26. ✅ **Locked-control feedback.** Authentication-locked fields and controls show “Controls are locked” on pointer or touch attempts. The existing lock button provides keyboard feedback. Native locks, values, and request guards are preserved; see [browser interaction guidance](browser-pages.md#authentication-lock-feedback).

27. ✅ **Radio pins and GPS control alignment.** RF engine/GPIO/Button and GPS fields share content-sized caption, control, and help tracks. Si5351 uses two columns, and narrow screens stack naturally. Labels, values, native locks, and save behavior are preserved; see [control-row alignment](browser-pages.md#control-row-alignment).

28. ✅ **Shared documentation and Pico favicon.** Documentation and every Pico station, setup, owner, and recovery page use the unchanged WsprryPi documentation icon. Firmware serves it locally before login under existing Host/interface checks; see [shared site icon](browser-pages.md#shared-site-icon).

29. ✅ **Hardware settings saves while standalone operation is suspended.** Radio pins, Si5351, and GPS/PPS allocation saves preserve standalone suspension, saved schedule preferences, missing dial selection, and unrelated drafts. Complete allocation, access, identity/revision, storage, ownership/output, and restart checks remain mandatory; WSPR enable/apply retains its prerequisites. See [configuration updates](configuration-updates.md).

23. ✅ **CI reliability and efficiency campaign — complete.** The [eleven-phase campaign](ci-reliability-campaign/README.md) and [scorecard](ci-reliability-campaign/acceptance.md) record qualified failure detection, ownership, state-based synchronization, complete coverage, verified source pairs, build reuse, measured scheduling, and final acceptance. Reliability, safety, and efficacy govern speed and reduction targets. Broad 50% reductions were not demonstrated. Changes are on paired feature branches; merge, release, deployment, and physical qualification remain separate.

## Possible future work

21. ⏳ **Si5351 automatic carrier-correction repeatability — follow-up.** The [close-spaced carrier comparison](gps-pps-validation.md#close-spaced-carrier-comparison) is complete with the existing RSP1B; the RSPduo is not a prerequisite. Two off/on repeats at each selected 160 m, 60 m and 10 m point establish GP2 improvement beyond the declared measurement allowances. Si5351 baseline errors are stable, while corrected errors vary between repeats; consistent Si5351 improvement remains unestablished. Investigate the selected calibration estimates, observation spans and engine realization before claiming repeatable improvement for Si5351. Keep this specific question separate from the completed GPS/PPS implementation and accepted launch timing. Further receiver/temperature coverage is not implied by the present bench results. The [saved execution prompt](si5351-correction-repeatability-prompt.md) defines the investigation, fixes, validation, adversarial review loop, and standing execution authority; the initial investigation on `codex/rc.2` fixed the Arm LOAD/policy frequency projection and reproduced the observed estimate-to-carrier shifts. Four balanced repeats per band still do not establish repeatable Si5351 improvement; the physical contributions of PPS/count endpoint noise and oscillator changes remain unresolved. See the [current investigation evidence](gps-pps-validation.md#2026-11-07-repeatability-investigation). Two subsequent five-minute existing-wiring RAM captures reduced estimate spread at longer windows and agreed with independent count brackets; they did not separate physical PPS/source variation or establish RF improvement. The common-source GP9/GP11 wiring is now electrically verified after correcting the bench GPSDO enable configuration. The first common-source trace was refused for missing GPS observations. An instrumented successor identified arrivals beyond the bench receiver-delay profile; the corrected fixture passed two fresh continuous five-minute captures. Common-source learner replay still spans −260 to +185 ppb, and one short-window midpoint comparison remains discrepant. Source/acquisition contributions and repeatable RF improvement remain open. No Pico feature-branch merge was performed.

## Closed — will not do

15. **Advanced Pico scheduling and durable controller/member transfer — closed/will not do.** Handled from WsprryPi.
16. **Keying-envelope work — closed/will not do.** Hardware is the operator's responsibility.

17. **Native iPhone consumer BLE app — closed/will not do.** Wi-Fi is sufficient.

18. **Enterprise/WPA3-only provisioning — closed/will not do.** Not needed for most operators.

19. **Automatic NTP-server discovery and preference — closed/will not do.** Manual NTP configuration is sufficient.

20. **Additional LAN/page-delivery security — closed/will not do.** No additional needs noted.

## Completed work

22. ✅ **RF launch timing — complete and accepted for the agreed operating needs.** Approximately one second early or late is the operator's acceptable comparison scale; better alignment is a goal, not a precision requirement, admission gate or reason to reject otherwise usable transmissions. The [capture-interface assessment](gps-pps-validation.md#practical-launch-timing-and-the-current-capture-interface) identifies wspr5's PPS-disciplined host UTC, the absence of SDR hardware timestamps, and the difference between host read times and sample acquisition times. Retrospective comparison of 12 existing scheduled launches, four Si5351 and eight GP2 tone/WSPR captures, gives approximate host-anchored offsets of +39 to +65 ms, consistent with that practical goal. This is a coarse operational check, not an independently bounded absolute RF timing qualification. Receiver/driver delay remains uncalibrated; no new transmission, configuration change or additional timing hardware was needed for this assessment.

13. ✅ **Si5351 — complete and merged into `devel`.**

Item 13 is complete. The current software provides Si5351 synthesis and local execution, bounded input-only loopback capture, no-GPS UTC rate assistance, retained-rate continuity across jobs and capture loss, strict paired Control/1 interfaces, and informational UTC uncertainty. Optional GPS/PPS ingestion and automatic RF correction are implemented; their independent measurement limits are recorded with completed item 14.

The Si5351 validation pair was Pico `03340049379eeb074583f67dcf520fbd902e016c` and Pi `309db1d85c02ae51e8db1c5cb13583e9ae766b37`. Both required production integration suites and every other job passed in [paired CI run 41511319323](https://github.com/WsprryPi/WsprryPi/actions/runs/41511319323). The ordinary Pico candidate and matched Pi controller/UI were installed on C and wspr5 for that validation, with saved settings preserved and idle/service state verified. The later GPS/PPS implementation and its separately identified installed image are recorded in the [GPS/PPS validation record](gps-pps-validation.md).

The [continuity validation record](si5351-continuity-validation.md) describes deterministic checks, adversarial corrections, finite bench observations and ordinary-image smoke results. The retained developer bundle contains exact commands, source manifests, logs, installer receipts and image identities. The existing 85/85 engineering matrix and 51/51 WSPR decodes retain their original scope and image identities.

UTC phase uncertainty is displayed for operator judgment, without another configuration item or first-party phase-uncertainty veto. Independent source-validity, authentication, age, leap, disagreement, ownership and hardware safety checks, frequency-estimate quality selection, and explicit external WTP request contracts remain enforced. The ±500 ppb example is illustrative, not a requirement.

Reference hardware, its declared uncertainty allowance and hardware qualification are local operator decisions. Shared results do not certify hardware or guarantee absolute UTC accuracy. Environmental TCXO testing and independent absolute UTC/long-holdover hardware measurements are outside project completion criteria.

14. ✅ **GPS UTC + PPS, RF calibration, location and improved holdover — complete and merged into `devel`.** Optional GPS UTC/PPS ingestion, separate oscillator correction, location/day-night policy, retained-rate holdover and coordinated Pi consumers are implemented and merged into `devel`. The [GPS/PPS contract](gps-pps.md) describes current behavior; the [validation record](gps-pps-validation.md) identifies exact source/image pairs, the completed Si5351 and GP2 measurements, restoration and limitations.
    - **Selected GP2 transmission test completed:** manual-zero and GPS-corrected five-second tones on 160 m, 60 m and 10 m, once-only manual residual, delayed ARM/frozen correction, one complete decoded WSPR interval and exact handback passed on the recorded 138 MHz/4 mA conducted setup. Delayed serial labels use the original captured PPS edge. Control-path memory was corrected without reducing safety reserves, and the controller resumed one logical WTP session per boot. Cumulative DUT RF was 170.592 seconds within the finite 200-second budget; no antenna or PPS disconnection was used.
    - Launch timing is complete under the accepted operating scope in item 22; no further precision-timing qualification or additional PPS hardware is required. The later close-spaced comparison establishes GP2 carrier improvement on the three selected bands; item 21 retains the specific Si5351 repeatability follow-up. Source loss/recovery has software evidence as selected; a live PPS cable-disconnection test is outside the selected scope.
