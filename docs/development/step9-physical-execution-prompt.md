# Step 9 physical standalone validation execution prompt

Work directly in `devel`. The user's initial reference to Phase 8 was clarified
as Phase 9 physical standalone validation. Preserve unrelated work and other
repositories. Read the project instructions, architecture, contracts, standalone
guide and existing conducted records. Refresh remote state before changes.

## User-selected closeout for this turn

After the inhibited bench tests, the user narrowed this turn to Wi-Fi validation
and deferred the remaining conducted RF and separate-power checks. Complete
Wi-Fi joining, autonomous SNTP, outage/aging/reconnection, retained disabled
configuration and watchdog recovery validation. Leave the RF-inhibited image
installed, scheduling disabled, and report the remaining Phase 9 physical work
as deferred. The broader sequence below remains the future physical checklist;
it is not authority to continue RF work in this turn.

## Objective and scope

Demonstrate, on the identified Pico 2 W / RP2350, that persisted station identity
and schedules survive reboot, Wi-Fi acquires device UTC independently, complete
locally encoded WSPR jobs run without per-job USB commands, network loss inhibits
new jobs, reconnection restores readiness, and restart handling prevents repeats.
Record repeated conducted captures and independent decodes. Keep general RF,
filter, band and calibrated GPIO-edge qualification in Step 13.

The user has requested physical standalone validation, including the described
flashing, provisioning, reboot, Wi-Fi, bounded conducted RF and SDR observations.
Confirm current wiring and the intended network configuration before live work.
Do not treat historical device paths, firmware hashes or source states as current.
Do not operate other transmitters or alter unrelated testing/services.

## Preparation and necessary repairs

1. Verify clean/current `devel`, existing Pico serial/interface mapping and
   current installed firmware. Confirm the GP2/GND attenuation/receiver path and
   acquire the specified Wi-Fi and numeric NTP settings. Read credentials from
   a private ignored file; never print, commit or include them in evidence.
2. Review the application for practical testability before loading an RF image.
   Implement a Console stop action that suspends standalone admission and aborts
   only its locally owned job through the shared service. Preserve external
   WTP ownership. Provide output-checked reboot/BOOTSEL recovery and sufficient
   firmware, boot, clock, network and terminal diagnostics.
3. Add an optional persisted UTC expiry for a bounded autonomous campaign.
   Reject an occurrence whose full frame would exceed that expiry. Preserve
   existing version-1 configuration compatibility and the no-repeat watermark.
   No testing may leave an indefinite enabled RF schedule behind.
4. Provide explicit, bounded Console tooling for configuration and diagnostics,
   with device identity checks and opt-in device I/O. Support an inhibited-only
   network disconnect/reconnect test without interrupting another host's network.
   Verify controls and failure paths on the host first. Do not weaken clock or
   uncertainty admission merely to obtain a successful capture. The user
   subsequently selected a 500 ms UTC uncertainty budget; enforce it at
   observation, admission and launch, including age growth, and test boundaries.
5. Run relevant deterministic tests, sanitizers, protocol validation and pinned
   target builds. Check reserved flash, UF2 extent and primary stack/heap layout.
   Retain exact source revision/diff identity and SHA-256 of tested images.

## Physical sequence

1. Begin with the RF-inhibited standalone image. Verify board/firmware/boot
   identity and inactive output. Provision the actual station/network settings
   with scheduling disabled, reboot, and verify retained non-secret settings.
   Confirm autonomous SNTP acquisition and reported uncertainty/age without USB
   time-setting commands. Verify the configured server's current UTC quality.
2. Exercise inhibited persistent schedules and terminal records. Reboot before
   a reserved start and confirm it is not submitted twice. Disconnect and
   reconnect device Wi-Fi, observe aging into unusable time and skipped slots,
   then reacquisition and resumption. Use a real power cycle for persistence
   evidence when the operator can perform it; software reboot is separate evidence.
3. Prepare an explicitly finite RF campaign on the verified conducted path.
   Recheck other signal sources and receiver ownership. Do not disturb an
   unrelated running WsprryPi campaign. Verify the SDR helper/receiver/settings,
   storage capacity and cleanup behavior before enabling the local schedule.
4. Load only the identified standalone RF image and confirm the persisted test
   window, station identity, engine, frequency, clock and initial inactive state.
   Capture complete scheduled frames with bounded receiver runs and adequate
   pre/post margins. Close USB control ports before jobs; do not send LOAD/ARM
   or timing observations. If the operator supplies power-only operation,
   explicitly distinguish that evidence from USB-attached but command-free runs.
5. Observe repeated autonomous jobs, retained terminal results, network recovery
   and no-repeat behavior across restart. Independently decode the exact station
   message from verified complete IQ captures. Record requested UTC slots,
   device launch observations and receiver timing limits. Do not treat an SDR
   wall-clock label as a calibrated absolute RF onset measurement.
6. Stop standalone execution, persist `enabled:false`, verify inactive output,
   and leave an RF-inhibited image when practical. Verify receiver/helper cleanup
   and other reference outputs' final states. Retain all failed attempts as
   diagnostic evidence; do not silently promote an earlier-image result.

## Acceptance, review and completion

A pass needs identified-device evidence for retained configuration, autonomous
UTC, scheduled execution without per-job host control, independent conducted
message decode, repeated operation and relevant recovery/no-repeat behavior.
Any unavailable physical action is a real remaining item, not a software pass.
Power-interruption flash fault injection is destructive testing and is not to be
improvised; distinguish normal power cycling from brownout/erase interruption.

Perform an adversarial assessment of source, actual artifacts and every claimed
result. Repair actionable findings, rerun affected host and target checks, then
repeat the assessment until clean. Hardware findings that cannot be resolved
within the authorized setup remain explicit blockers. Do not mark the physical
phase complete with unmet acceptance items.

Maintain a sanitized execution/validation record and update the roadmap only to
match observed evidence. Commit only attributable changes, push `devel`, and
verify clean status and HEAD/upstream/remote equality. Report changes, commands,
exact identities, pass/fail results, repairs, remaining limits and final device
state. Do not create another feature branch or scheduled RF automation.
