# Consolidated backlog

This is the distinct TODO list for selected unfinished work. Current behavior is documented in the engineering guides. The reusable [cleanup instructions](repository-cleanup-prompt.md) apply to repository and harness cleanup. Item numbers remain stable.

## In progress

13. **Si5351, including TCXO-assisted UTC continuity without GPS.**
    - ✅ Synthesis, local execution, bounded loopback capture, shared controls, trusted-local μChrony rate input, retained-rate continuity and informational UTC uncertainty are implemented.
    - ✅ Retained bench observations include 85/85 band/mode cells and 51/51 WSPR decodes under their original image identities, plus the recorded ordinary-image continuity smoke check. These are shared results, not certification of operator hardware.
    - ⏳ Finish the current paired software CI and matching Pi controller/UI delivery described in the [Si5351 Backlog](#si5351-backlog). Feature-branch delivery is separate from `devel` or `main`.
    - Reference hardware, its uncertainty allowance and hardware qualification are local operator decisions. Environmental oscillator qualification and absolute UTC/long-holdover hardware measurements are not project completion gates. GPS/PPS ingestion and automatic RF calibration remain in item 14.

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

This slice completes software support for no-GPS TCXO-assisted UTC continuity. NTP or authenticated phone time supplies UTC phase observations; Si5351 loopback supplies frequency observations under the operator's declared reference allowance. Hardware selection and qualification belong to the local operator. Shared bench results describe measured conditions and do not certify hardware or guarantee absolute UTC accuracy. Environmental TCXO testing and independent ordinary-firmware absolute UTC/long-holdover measurements are not completion gates for this project.

UTC phase uncertainty is displayed for operator judgment. It does not add a first-party transmission veto or another configuration setting. Preserve independent source-validity, authentication, leap, ownership and hardware safety checks, frequency-estimate quality selection, and explicit external WTP request contracts. The ±500 ppb example is illustrative, not a requirement.

1. ✅ **Reconcile the candidate and retained evidence.** Review the existing Pico/Pi feature branches, architecture, consumers and retained results; preserve unrelated checkout work. Keep the 85/85 engineering matrix and 51/51 WSPR decodes bound to their actual images and conditions.

2. ✅ **Represent reference assumptions honestly.** Keep measurement-only operation available. Trusted-local operation accepts an explicit operator-supplied reference allowance; count quantization, endpoint capture, divider and numerical effects are added conservatively. Do not substitute a temperature-stability figure for total reference error or assume a universal ±500 ppb specification. Document the software model and measured examples without requiring project hardware qualification.

3. ✅ **Complete frequency assistance in the existing time architecture.** Use timestamped frequency-only observations, uncertainty-based quality selection and independent-source disagreement handling. Preserve continuous virtual UTC, original epoch age, authentication, expiry, leap policy, immutable accepted jobs and manual RF correction. Reference observations must not manufacture UTC, refresh phase evidence, erase accumulated uncertainty or create independent agreement from correlated estimates.

4. ✅ **Retain useful rate information through jobs and capture loss.** Pause acquisition from accepted-job preparation through cleanup, including the loaded interval before ARM. Retain the learned center with explicit timer-drift uncertainty growth; distinguish sample freshness, learned-rate age and epoch-source age. Test loss, reacquisition, plan/clock changes and policy removal without time steps or stale-confidence resets. State the model's assumptions rather than claiming certified hardware performance.

5. ✅ **Demonstrate behavior and share scoped observations.** Deterministic known-error checks cover both timer-error signs, intermittent/jittery NTP, accepted phone time, source/reference loss, drift, reacquisition, full WSPR intervals, repeated gaps, invalid/duplicated/stale/future/generation-mismatched observations, disagreement and restart seeds. Retain physical bench measurements and ordinary-image smoke results with their truth-source assumptions, finite durations and image identities. Do not treat synthetic checks as physical evidence or introduce production GPS ingestion.

6. ⏳ **Complete coordinated interfaces and software integration.** Update current Control/1 schemas, descriptors, strict consumers, runtime use, serialization, generated assets, paired adapters, shared UI and Read the Docs sources together. Render applicable desktop/mobile states with the Impeccable workflow. Both actual production network and USB suites must succeed for the intended source pair under the checked-in Pi workflow recipes; failed, cancelled, skipped or timed-out required checks remain unresolved.

7. ✅ **Validate and deploy the ordinary software candidate.** Cross-build the normal image with pinned inputs and linked memory/flash/stack checks. Use the preserving shared installer and retain the exact developer bundle, same-board references and recovery assets. Verify installed identity, saved settings, finite ordinary-image smoke behavior and restored idle/service state. Additional boards are not prerequisites; excluded boards invalidate no retained results.

8. ⏳ **Finish adversarial review and delivery.** Correct actionable findings, rerun affected checks, commit/push the existing feature branches, bind companion provenance to the tested Pico software revision and verify remote heads. Report tested revisions, commands/results, CI links, documentation, installed images/configuration and actual repository/service state. Remove hardware-qualification assumptions from project completion criteria while preserving honest evidence scope.

The implementation, software model and shared finite measurements are described in [Si5351 continuity validation](si5351-continuity-validation.md). Hardware qualification remains an operator responsibility, not selected unfinished project work.
