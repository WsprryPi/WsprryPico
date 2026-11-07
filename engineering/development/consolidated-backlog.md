# Consolidated backlog

This is the distinct TODO list for selected unfinished work, with completed and closed items marked below. Current behavior is documented in the engineering guides. The reusable [cleanup instructions](repository-cleanup-prompt.md) apply to repository and harness cleanup. Item numbers remain stable.

Status: ✅ complete; ⏳ in progress; ▧ not started. Closed/will-not-do items are labelled separately.

## Selected unfinished work

24. ✅ **Remove the initial time/calibration review link — complete.** Automatic timeout and calibration read errors stay beside their controls without a top-level save-result link. Transmitter status retains current clock and transmission observations; Time and calibration remains available through normal navigation and bookmarks. Explicit failed reads and unconfirmed saves retain their recovery links. See [contextual saved-state review](browser-pages.md#contextual-saved-state-review).

25. ⏳ **Hostname editing in the captive portal.** Allow the operator to change the device hostname from the captive portal page. The [saved execution prompt](captive-portal-hostname-prompt.md) defines the implementation, validation, adversarial review loop, and standing execution authority; execution and validation are in progress on `codex/rc.2`.

26. ▧ **Locked-control feedback.** Show a short tooltip, “Controls are locked”, when the operator attempts to click or otherwise interact with a locked control or field. Keep the control locked while providing this feedback. The [saved execution prompt](locked-control-feedback-prompt.md) defines the implementation, validation, adversarial review loop, and standing execution authority; it has not been executed.

27. ▧ **Radio pins control alignment.** Align the RF output engine label and selector with the adjacent RF output GPIO and Button labels and selectors. Correct both the Direct GPIO / PIO layout and the Si5351 layout, where only RF output engine and Button are shown. The RF output engine field currently sits lower than the neighboring fields. In GPS wiring and timing, also align the controls for “Validated UTC/PPS association”, “PPS edge delay from UTC boundary (ns)”, and “Capture timestamp error allowance (µs)” with neighboring controls. Wrapped labels and inline help must not displace individual controls within a row; preserve readable labels and responsive layout. The [saved execution prompt](radio-pins-control-alignment-prompt.md) defines the implementation, validation, adversarial review loop, and standing execution authority; it has not been executed.

28. ▧ **Shared documentation and Pico favicon.** Use the same default page/site icon as the WsprryPi documentation across the WsprryPico documentation pages on Read the Docs and the web pages served by the Pico, including the captive portal. The [saved execution prompt](shared-favicon-prompt.md) defines the implementation, validation, adversarial review loop, and standing execution authority; it has not been executed.

29. ▧ **Hardware settings saves while standalone operation is suspended.** Investigate the reported inability to save Si5351, GPS, PPS, LED, and button pin/configuration settings while Transmitter status says “Standalone operation is suspended. Future WSPR needs a saved dial before schedules can be enabled.” The reported state shows no job, inactive RF output, and an available owner. Determine which save/admission condition actually blocks these edits; the status message alone does not establish the cause. Allow otherwise valid hardware settings to be saved independently of a saved WSPR dial or schedule enablement, while preserving applicable access, ownership, output, and validation checks. Make any actual save refusal specific and actionable. The [saved execution prompt](hardware-settings-save-suspension-prompt.md) defines the implementation, validation, adversarial review loop, and standing execution authority; it has not been executed.

23. ✅ **CI reliability and efficiency campaign — complete.** The [eleven-phase campaign](ci-reliability-campaign/README.md) and [scorecard](ci-reliability-campaign/acceptance.md) record qualified failure detection, ownership, state-based synchronization, complete coverage, verified source pairs, build reuse, measured scheduling, and final acceptance. Reliability, safety, and efficacy govern speed and reduction targets. Broad 50% reductions were not demonstrated. Changes are on paired feature branches; merge, release, deployment, and physical qualification remain separate.

## Possible future work

21. ▧ **Si5351 automatic carrier-correction repeatability — follow-up.** The [close-spaced carrier comparison](gps-pps-validation.md#close-spaced-carrier-comparison) is complete with the existing RSP1B; the RSPduo is not a prerequisite. Two off/on repeats at each selected 160 m, 60 m and 10 m point establish GP2 improvement beyond the declared measurement allowances. Si5351 baseline errors are stable, while corrected errors vary between repeats; consistent Si5351 improvement remains unestablished. Investigate the selected calibration estimates, observation spans and engine realization before claiming repeatable improvement for Si5351. Keep this specific question separate from the completed GPS/PPS implementation and accepted launch timing. Further receiver/temperature coverage is not implied by the present bench results. The [saved execution prompt](si5351-correction-repeatability-prompt.md) defines the investigation, fixes, validation, adversarial review loop, and standing execution authority; it has not been executed.

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
