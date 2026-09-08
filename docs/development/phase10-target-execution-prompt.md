# Phase 10 acceptance closeout execution prompt

Complete the remaining WsprryPi-to-WsprryPico acceptance, review the evidence
adversarially, repair actionable findings, rerun affected checks and reassess.
Commit and push the reviewed outcome to the existing devel branch without force.
Mark Phase 10 complete only if the bounded joint acceptance below passes.

## Current source and delivered work

Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md, the WTP/1 contract,
phase10-host-acceptance.md and the complete phase10-target-review.md first.
Inspect Git state and preserve unrelated changes. Current Pico repository tip
before this closeout is 08eef16871699d1f6d1503818fd9ebd25dd8eb91. The tested
firmware source is 6c83982aca3a96582347cda770043e20d4f674df; subsequent changes
are evidence documentation. The clean standard and StandaloneRF pair is staged
with final-firmware-manifest.json in /home/pi/phase10-wtp-acceptance/ on wspr5.
Keep exact source and artifact identity; rebuild only if source changes require it.

WsprryPi devel e95932feebc44d84988c96df969c8f8203ed8c1c is installed on wspr5.
Its isolated real checkout is /home/pi/phase10-wtp-acceptance/host-git. The
operator manual is delivered at 5bbce2d8c46243cc910f663f56397a8f32fdd2fb.
Host installation, Linux suites, UI/manual validation and earlier inhibited
acceptance are already recorded; do not redo unrelated completed work.

Physical findings already repaired: terminal RF-off sample padding, fractional
host timestamp admission, leap-boundary accounting, first-fault diagnostics,
guarded local recovery and RF servicing between WTP request-processing stages.
The last real host Tone completed with authoritative cleanup. Its RF measurement
was obscured by a continuous carrier near 137501 Hz that persisted with inhibited
firmware and did not follow SDR tuning. Treat this as interference in the chosen
measurement channel; identifying its source is not a Phase 10 gate.

## Authorized setup and boundaries

The user explicitly authorized execution, bounded conducted RF, firmware loading,
applicable host services, final review, repair, commit and push. The user also
accepted choosing a nearby clear test frequency. Keep the confirmed physical
wiring unchanged: Pico GP2, GPSDO Output 1 and wspr5 GPIO4 each have their own
60 dB attenuation into the common SDR combiner, with no external filter/antenna.
Keep the GPSDO outputs and RP1 output inactive. Do not reboot wspr5, change its
GPS/PPS/chrony configuration, alter RP1 routes, or modify unrelated repositories.

Use Pico 2 W/RP2350A2, USB serial 0BF4B4AEC9FFB344, WTP device
fd6127d11d6aca42a9905fa3fb1bf1d5. Console is its if00 by-id node; WTP is if02.
Verify exact device/boot/revision, disabled persisted scheduling and inactive
output before each firmware change or campaign. Preserve station/network
configuration and the no-repeat watermark. Only one process may own WTP CDC.

Use RSP1B 2404058C60 at center 112500 Hz, 250 ksps CF32, 200 kHz bandwidth,
gain 20, AGC/bias tee off. Only one receiver process may own it. Screen the
existing IQ and confirm the selected channel in a fresh inhibited baseline.
Use 135500 Hz as the candidate conducted-only base, 2 kHz below the QRM; record
any necessary alternative before transmitting. This is a finite integration
experiment with explicit unqualified-frequency consent, not an on-air band claim.
Retain the existing detector thresholds and original failed captures.

## Execute

1. Record current source, installed executable/configuration hashes, firmware
   hashes, device identity/state, receiver availability, RP1 idle predicate and
   GPSDO disabled observations. Save a fresh receiver-only baseline. Verify the
   selected channel has adequate quiet evidence for the unchanged analyzer.
2. Adapt only private acceptance orchestration to the chosen frequency. The
   host must still compile its real canonical jobs. Bind helper source/binary,
   exact requests, mode/message, duration/count, receiver settings and firmware
   into evidence. Preserve old helpers/captures or use distinct closeout names.
   Do not change product protocol or weaken acceptance checks to obtain a pass.
3. On the final inhibited build, repeat affected installed-release cancellation,
   clock-budget and disconnect/reconciliation checks. Run through the private
   acceptance INI and bounded supervisor, preserving the installed configuration.
   Always restore the original service afterward. Recheck unknown output is
   never treated as safe and failed jobs remain retained rather than auto-rearmed.
4. Flash and verify the exact StandaloneRF image. Require usable device SNTP;
   explicitly allow frequency adjustment and at most 500 ms start uncertainty
   for this bounded functional test. Keep autonomous scheduling disabled.
5. Complete a five-second Tone using the real host application/client and a
   finite receiver capture with leading/trailing quiet. Require complete WTP
   lifecycle, authoritative inactive cleanup, and independent burst/carrier
   acceptance at the new base frequency before longer RF jobs.
6. Through the installed release and private configuration, send one ETE job
   each in QRSS, FSKCW and DFCW with three-second dots, canonical character gaps,
   no fades and 5 Hz FSK/DFCW shift. Confirm exact canonical event semantics,
   expected marks/spaces, duration, frequency separation and final silence.
   Preserve readability as the operational criterion; diagnostic timing limits
   are engineering checks, not published QRSS standards.
7. Send exactly three finite WSPR frames through the installed release, using
   AA0NT EM18 37 and no random frequency offset. Bind the host's actual RF base
   semantics to the analyzer/decoder. Capture all frames with quiet intervals;
   independently decode each with wsprd. Require unique completed job identities,
   expected content, coherent frame timing and confirmed cleanup. Do not let a
   fourth frame start. Use finite capture/process deadlines and a bounded daemon.
8. Restore the standard inhibited image, confirm exact new boot/source, empty
   inactive state, persisted schedule disabled, retained configuration/watermark,
   original installed host service and unchanged installed/boot configuration.
   Receiver cleanup must be verified; no acceptance worker may remain active.
9. Perform an adversarial source/evidence review: frequency mapping, source and
   binary identity, final-image coverage, actual installed-release path, canonical
   jobs, SDR hash/size/settings and cleanup, leading/trailing silence, independent
   decode, failure retention, ownership/recovery, and bounded-output enforcement.
   Repair each actionable finding, rerun affected checks and assess again.
10. Update the target review, execution checkpoint and roadmap with exact passed
    scope and remaining limitations. Commit and push after checking ancestry;
    verify clean state and origin parity. Report the actual result plainly.

## Completion and limits

Success requires all five mode-specific conducted acceptance results plus the
applicable final-build recovery checks and delivered host/manual work. A build,
simulator result or WTP completion alone does not establish RF acceptance.
Logs, IQ, private INIs, firmware binaries and credentials remain untracked;
commit the concise evidence record and commands/identities needed to reproduce it.

Unexpected device identity, foreign ownership, active unrelated work, uncertain
output, unacceptable clock state or failed cleanup blocks further RF. Resolve
what can be resolved within existing authority, retain failures, and restore
inhibited operation before reporting an external blocker. Ordinary QRM at the
old frequency is addressed by the selected clear conducted-test channel.

Phase 11 Wi-Fi/TCP/shared browser API, Phase 12 provisioning, and Phase 13
calibrated timing/RF/reliability, output filters, supported mode/band coverage
and reproducible production UF2 remain separate. Do not expand this closeout
into those phases or claim general RF qualification.
