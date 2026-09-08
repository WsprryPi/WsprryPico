# Phase 10 joint target acceptance and delivery prompt

Continue the authorized Phase 10 work across WsprryPico, WsprryPi and the
separate Wsprry_Pi_Docs operator manual. Review current code and recent changes,
execute the gates below, assess the result adversarially, repair findings, rerun
affected checks and reassess. Commit and push reviewed changes without force.
Do not promote incomplete physical evidence into a Phase 10 completion claim.

## Starting identities and contracts

- Pico source: clean `eb6aa58d6e429218bbfdb824c82a8f5fd7f4e7c9` on `devel`.
- Reviewed host feature: `2819f0b8ccb05f12d7f978a4cee2cac830997bbf` on
  `codex/phase10-wtp-slice1`.
- Host integration candidate: merge the feature into freshly fetched `devel`
  (initially `a523904`) in an isolated checkout. Preserve the original feature
  checkout. Record the resulting exact commit and executable identity.
- Target: Linux `wspr5`, Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344`,
  WTP device `fd6127d11d6aca42a9905fa3fb1bf1d5`. Recheck the attached identity
  and boot each time; never assume a tty number identifies the Pico.

Read each repository's AGENTS.md and relevant current development instructions.
For Pico, read README.md, CONTRACT.md, architecture, WTP/1, standalone/SNTP,
the shared WTP profiles and `phase10-host-acceptance.md`. For the host, review
the client/session, USB adapter, scheduler, application/runtime bridge, status
and recovery routes, installer and production integration documents. Review
the changed paths shared with newer devel for merge regressions.

## Authorization and boundaries

The user authorized the remaining Phase 10 target acceptance, applicable
installation/services, host merge and operator-documentation work. Reversible
preparation, inhibited firmware flashing and exact-device inspection may proceed.
Confirm current physical routing and make every RF run concrete before starting:
frequency, mode/message, duration/repeats, firmware/clock, output route,
receiver/reference state and stopping procedure. A historical wiring description
does not establish current connectivity. Request necessary cable moves as
logistics, without asking again for the already authorized scope.

Keep autonomous scheduling persistently disabled and preserve station/network
configuration and journal history. Preserve wspr5 GPS/PPS/chrony and its RF state.
Do not reboot the Pi, enable unrelated outputs, change RP1 routes, redesign
firmware networking or start phases 11–13 as incidental acceptance work.

## Execute in order

1. Record clean/dirty source state, exact firmware ELF/UF2 hashes, existing pinned
   SDK/toolchain, board/chip identity and source revision embedded in each image.
   Build fresh inhibited and StandaloneRF images from the clean reviewed Pico
   commit. Check flash/journal layout and absence of the physical RF engine from
   the inhibited image. Never relabel an older dirty build as the current commit.
2. Verify persisted scheduling disabled, ownership idle and output inactive.
   Flash the standard inhibited image with exact serial/revision guards and
   verification. Read the new boot identity and SNTP acquisition evidence.
3. Run the merged host's documented Linux hardware-free suites in an isolated
   real Git checkout, recording source identity and failed attempts. Validate
   protocol, USB metadata/failure handling, application, production runtime,
   scheduling and status/recovery. Build production using its documented profile.
4. Connect Pico's USB to wspr5. Record Linux enumeration, by-id aliases, exact
   serial/VID/PID and the dedicated WTP CDC function. Refuse Console and wrong
   identities. Independently record Linux UTC readiness and Pico GET_CLOCK,
   HELLO/STATUS/CAPS. Confirm inhibited engine and five-mode envelope.
5. Use the real host application/encoders for finite inhibited jobs. Confirm the
   default 1 ms budget rejects clock evidence that exceeds it, then explicitly
   use at most 500 ms for bounded functional acceptance. Exercise WSPR and keyed
   jobs within CAPS, repeated jobs, loaded/armed/running cancellation, connection
   loss, reconnect and boot changes. Preserve job/session identities and terminal
   evidence. No reload/rearm, foreign adoption or output-safe inference from a
   lost connection. Record cases requiring unperformed physical actions as open.
6. Only after inhibited acceptance succeeds, bind a small conducted RF campaign
   to the actual setup. The prior setup had separate 60 dB branches from Pico
   GP2, GPSDO Output 1 and wspr5 GPIO4 into one SDR combiner, without external
   filtering. Verify it now and exclude unintended sources. Use the explicit
   StandaloneRF image, finite requests, necessary frequency-rounding consent and
   host unqualified-frequency opt-in. Retain independent decoding/keyed analysis,
   start/end quiet, frequency/timing observations and authoritative shutdown.
   WTP completion alone is insufficient; do not extend results to other modes,
   bands, clocks, firmware or RF paths.
7. Review the installer before deployment. Bind the installed binary, configuration,
   service and HTTP proxy to the validated host commit. Preserve disabled TX and
   startup policy. Use the installer completion marker outside the Git checkout,
   creating it only on success. Validate status/recovery proxy and service
   lifecycle without enabling output. Record any required unperformed reboot.
8. Update the operator manual's CLI backend, INI and Transmitter-tab guidance.
   Preserve the default-off browser-only development toggle and separate persisted
   Pico selection. Explain exact endpoint identity, clock budgets, unsupported
   continuous Tone, observations versus output proof, and explicit reconciliation.
   Use Impeccable and the manual's existing Sphinx environment; render desktop,
   tablet and mobile, repair broken links and misleading wording, and keep the
   established visual design.
9. Assess all changes and evidence adversarially. Focus on merge interactions,
   source/build identity, preserved disabled state, GPIO/clock disturbance,
   stale/unknown observations, ownership/boot changes, cleanup, and unsupported
   qualification claims. Fix actionable findings and rerun affected checks before
   a second assessment. Record unresolved physical gates separately from defects.
10. Commit and push each repository's reviewed slice separately. Refresh remote
    ancestry first and preserve user branches/work. Report exact commits, remote
    parity, installed/device state, validation and remaining gates. Do not mark
    all Phase 10 complete until joint target acceptance and delivery are evidenced.

## Evidence and stopping conditions

Keep logs, captures, builds, private INI files and manifests outside tracked
source. Maintain a committed review with exact commands and evidence locations,
including failed attempts and repairs. Never expose network credentials.

Missing physical connection or unconfirmed routing blocks dependent target work,
not independent documentation/build/review. An unexpected identity, unknown
output, foreign ownership, clock failure or failed cleanup blocks further RF.
Leave the device inhibited and scheduling disabled when physical acceptance
cannot continue; report the remaining user action precisely.

## Current execution checkpoint

Read the latest section of `phase10-target-review.md` before resuming. Host
integration and operator documentation are published, and the exact release is
installed on wspr5. Earlier inhibited USB cases passed. Terminal-off padding,
fractional timestamp admission, leap-boundary checking, first-fault diagnostics,
guarded local recovery and cooperative WTP request servicing are repaired.
Current firmware source is `6c83982aca3a96582347cda770043e20d4f674df`; both
standard and StandaloneRF images are built and staged with their updated
`final-firmware-manifest.json`. The earlier manifest is archived separately.

The real host's five-second Tone now completes with authoritative cleanup.
Independent RF acceptance remains blocked: a strong continuous carrier near
137501 Hz persists even with the Pico flashed to RF-inhibited firmware, GPSDO
outputs reported off and RP1 idle. A receiver-only baseline confirms this.
The user has been asked whether another source remains from the other test.
Keep the wiring unchanged and do not resume RF acceptance until the baseline is
understood and quiet. Do not relax the burst detector to manufacture a pass.

Current Pico source is `6c83982aca3a`, boot
`f16780943aa7cb3a4e5c8294a6b41098`, standard inhibited engine, empty/inactive,
with persisted scheduling disabled. No new power cycle is pending. The installed
host service remains running; the private installed-release acceptance supervisor
has not been started. Recheck all identities, workload ownership and device clock
before any further authorized target work.

When the baseline is resolved, verify and flash the current StandaloneRF image,
repeat the bounded Tone, then run installed-release QRSS/FSKCW/DFCW ETE jobs and
three independently decoded WSPR frames. Restore inhibited firmware afterward.
Retain every `rf-tone` through `rf-tone-5` record and `rf-inhibited-baseline`;
use a fresh suffix `6` or later. The bounded helpers in
`/home/pi/phase10-wtp-acceptance/` are test orchestration, not product code.
Review their identities, engine guards, private daemon lifetime and cleanup
before reuse. Only one owner may open the Pico WTP CDC interface at a time;
only one receiver process may use RSP1B `2404058C60`. Finish adversarial review,
repair any findings, rerun affected checks, update the roadmap truthfully, and
commit/push the authorized changes. Phase 10 remains open until joint acceptance
passes; Phases 11–13 remain planned.
