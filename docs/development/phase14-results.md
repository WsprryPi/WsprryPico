# Phase 14 qualification results

Status: IN PROGRESS. See the pre-acquisition [plan](phase14-plan.md).
No Phase 14 release support is claimed at this checkpoint.

The initial host baseline passed 155/157 CTest groups. Two known test-harness
failures were reproduced: the extracted capacity-pressure fixture omitted the
production HTTPS authority helper; explicit admission-budget tests mixed their
injected byte boundary with host-ABI allocation occupancy. Repairs preserve
normal allocation-model checks and adjacent-byte refusal cases. Both affected
groups pass after repair. Firmware runtime is unchanged by these repairs.

Initial live inspection matches both Pico USB serials and receiver/GPSDO
identities on wspr5. A runs inhibited source `6c7b14321003`, B runs inhibited
`72d38d505ba2`; both clocks are 150 MHz, schedules disabled and output false.
B retains no owner/job. The older USB-only inventory cannot finish WTP HELLO
on these consumer profiles, because current source deliberately disables USB
WTP for consumer profiles. These timeouts remain private failed inventory
records; ordinary Plain LAN inventory is used next.

Detailed physical results, release-candidate artifact bindings, final board
state, adversarial findings and publication outcome will be appended here.

Before RF acquisition, the operator explicitly clarified that there is no LPF
and that LPF development/application remains their responsibility. The plan
records this scope amendment; no filter development or post-filter qualification
is required to close the firmware campaign. The complete repaired host suite
passes 158/158 groups.


## Receiver method and candidate checkpoint, 2026-10-08

The first independent rebuild differed because MbedTLS diagnostics embedded
absolute build paths via `__FILE__`. Source `144e8e83e598615a3fb98d2646fc64488a36eedb`
normalizes compiler source/build path prefixes. Two fresh 138 MHz builds now
produce identical complete UF2 bytes, SHA-256
`5c0d80c8dd8cef5fcb02d70e8becdb2a677045d31e8fc50db96e96edcab188f6`.
Both boards retain this ordinary RF-capable candidate, consumer Plain LAN,
GP2, divider 1, RAM renderer, GP14 disabled, fixture code disabled and preserved
settings. These are candidates; no release qualification follows from deployment.

The initial complete 80 m WSPR frames decoded on both boards but failed the
historical 0.1 Hz residual screen (A 0.10543 Hz, B 0.14159 Hz). Three consecutive
settling frames on A passed that screen. Those settling captures bind the
preceding candidate source `fecd531`; the subsequent path-normalization change
alters addresses/layout, so current-image affected launch/resource checks remain
required. Initial tones passed. Current-image B has three DFCW3 passes; QRSS3
and FSKCW3 each have three retained screen failures. QRSS envelopes and quiet
tails agree, but the nine-second dash has 0.291-0.325 rad linear phase residual.
FSKCW has 5.028-5.033 Hz separation, 0.3-0.6 ms transition errors and smooth
state drift that exceeds the frozen composite screen. The screen limits remain
unchanged; diagnosis and final dispositions are pending.

A finite GPSDO-only receiver comparison used four eight-second, fixed-tuning
captures at carrier minus/plus 20 kHz in ABBA order, with six one-second phase
fits per capture. It estimates nominal-to-true time scale 1.000001110233
(1.110233 ppm), observed repeatability bound 0.288629 ppm. The separately stated
1 ppb reference accuracy is an engineering assumption, not a certificate.
GPSDO identity/locks were checked; output 1 was returned to its original 10 MHz,
with output 2, output enable, PPS and output levels unchanged. First execution
failed before analysis because the Harness Python import path was omitted;
its capture and restored settings remain retained. The retry passed acquisition.

Method extension recorded before wider acquisition: an optional simultaneous
GPSDO tone at the tested band point minus 40 kHz permits common tuner-offset
subtraction. It does not discipline the Pico. Apply the separately measured
sampling scale to the frequency difference and relative time only, retaining
raw values, bracket checks and uncertainty. This extends measurement context;
it does not change existing operational screening criteria. Absolute UTC onset
and calibrated power/path insertion loss remain outside the demonstrated claim.

Host-only ownership repair locks only the selected board for deployment and
locks the shared receiver for RF/reference batches. All RF jobs still verify
the other board is inactive. Constructor failure and reference restoration
failure release owned handles. The rejected overlapping deployment changed
no board. No firmware runtime change was needed for these automation repairs.


## Evidence-validation and resource checkpoint

All 26 reference-attributed Tone jobs at the 13 representable 138 MHz band
points completed, with disabled schedules and inactive successors. Immutable
reanalysis passes 25 operational screens; Pico A's 6 m capture fails the raw
100 Hz acquisition screen. The calibrated-reference comparison is retained
separately; that original failure is not replaced. Wider 132/150 MHz screening
is in progress. All 158 deterministic host groups pass again after the stronger
evidence/source/job/boot checks and spectral reference-exclusion repair.

Per-job resource assessment now includes both stack guards, observed authority
reserve, allocator/TLS/flash/DMA fault counters, predecessor exhaustion and
refill-to-ready versus the clock-specific 16,384-word buffer period. Idle memory
deltas are retained without treating unmatched replay-history windows as leak
proof. Long-job and normalized-soak assertions remain pending.

The current consumer profile intentionally suspends standalone recurrence and
USB WTP and has no station browser API. Those disabled policy surfaces cannot
be claimed as failed transports. A temporary B engineering profile is prepared
for the existing USB, mTLS browser and standalone paths. Changing that profile
creates a concrete settings-preservation need: preserve only its 16 KiB profile
plus 16 KiB standalone configuration/watermark region, verify CRC/SHA journals,
leave application/access/bond/E10 bytes untouched, and restore those specific
settings afterward. This does not reopen GP14 or LED/button qualification.
New test credentials remain private under ignored `config/local/` and the
private authorized-host evidence root. Journal corruption tests reject torn
newer records rather than resurrecting older authority.


Mode acceptance follows the plan's economical screening rule: for each 138 MHz
board/band/mode, acquire one complete waveform, then perform the remaining two
repetitions when that screen passes. A failed screen excludes that row from
expensive repetition; its raw result remains. Both boards' initial 80 m WSPR
settling triplets are always completed to diagnose cold/warm behavior. All
results remain release-unqualified until resources, lifecycle, spectra,
endurance, final-image applicability and adversarial review are finished.
Optional simultaneous-reference WSPR comparison uses the existing analyzer's
reference subtraction, retaining the same timing, separation and residual
limits. Keyed jobs retain their existing screen and add independent reference
phase diagnostics over the same intervals to distinguish common receiver drift.

Prepared finite reliability workloads include a 512-event FSKCW job (128 to
3,600 seconds), a one-hour Tone and native-controller ETE/32-character messages.
The native controller uses a private temporary INI, the already installed
binary, disabled ancillary GPIO and a finite iteration/request. No shared
operational INI or sibling source is modified. Receiver captures and independent
Console observation bind its actual job and boot; process exit alone cannot
establish completed RF or shutdown.


Both complete alternative-clock Tone sweeps finished: 13 band points per board
at 132 MHz and 14 per board at 150 MHz, including the representable 4 m point.
Of 54 jobs, 53 completed and A's 132 MHz/80 m job safely returned `MISSED_START` without running. Both boards were returned to the identified 138 MHz
candidate, with settings preserved. Analysis initially mishandled decimal-string
uint64 counters; the repaired reducer validates canonical unsigned values and
rejects booleans, negatives, non-finite spellings and overflow. Original captures
are reused under new immutable analysis labels; no firmware repair was needed.
The first current-image 80 m full WSPR frame also completed and decoded, retaining
its cold-frame screen failure. The acceptance batch resumes after this host repair.

The first temporary B engineering-profile attempt selected the correct profile,
accepted GPS-PPS-backed NTP from wspr5 and started its TLS server, but its host
readiness check incorrectly required the consumer-only `lan_wtp_ready` flag.
It rolled back the preserved settings and verified the original consumer state.
The repaired readiness check uses `network.control_listening` for engineering
profiles; the retry verifies activation, identity, source/clock, inactive output
and USB WTP inventory. The original failure and rollback remain retained.
The configured time server is wspr5's existing GPS-PPS chrony service, which was
already admitting this LAN; no NTP/service configuration was changed.


The repaired B profile has successful, certificate-pinned HTTPS page/status/
capabilities/jobs preflight. During acceptance, offline IQ analysis outlived
an idle Plain LAN connection; the next CLAIM hit a reset socket before any
RF job was submitted. The failure and incomplete receiver attempt remain.
The host now closes its inactive released transport before offline analysis
and negotiates a fresh connection for the next job. It does not replay an
uncertain mutation or reinterpret that failed attempt as RF qualification.


## Launch retry repair

The original 132 MHz/80 m missed job remains excluded. It terminated about
301 microseconds after the admitted monotonic start, with synchronized clock,
normal leap state, 118 ms uncertainty below the 500 ms admission ceiling, and
no allocator/DMA fault. Original diagnostics do not identify its precise rejection
branch, so the causal attribution remains an inference.

Source review found an actionable early-alarm race: when the UTC target is only
a few microseconds ahead, the sink rescheduled exactly that instant; SDK/timer
work could consume the remaining lead and reject the retry inside the otherwise
valid one-second launch window. A deterministic 25-microsecond early entry with
50 microseconds of timer-programming work reproduces `Missed` on the original
code. The repair always retains the existing 100-microsecond retry margin,
bounded by the original UTC deadline. A second case still refuses a retry beyond
that deadline, with no RF. Checked indicator acknowledgement and stale-ticket
handling are unchanged. New static diagnostics distinguish clock guard, retry
alarm and driver launch rejection, retaining WTP `MISSED_START` semantics.
Affected host, firmware, both-board launch/resource and acceptance checks are
required on the new candidate. Old waveform/frequency/spectral captures remain
identified historical observations; they do not close the repaired launch gate.

All 158 host groups pass after the launch repair. Nine Phase 14 rejection tests
also pass, including candidate artifact substitution/reserved-flash writes and
NTP-rule removal when counter observation times out. The initial low-band WSPR
LOAD timed out under the host's three-second response deadline; its outcome is
retained as a control failure. The repaired host waits up to 30 seconds for that
single LOAD and never retries an uncertain mutation. Verified Console cleanup
is recorded before any RELEASE attempt that may itself encounter a reset socket.
The next candidate uses version `0.1.0-rc.1`; host workloads now bind its generated
manifest rather than a historical hard-coded source revision.

## Repaired release-candidate checkpoint

Committed runtime source `bd45bc1bb638839610f28ae529c97d51ec345f6d` builds the
ordinary `0.1.0-rc.1` candidate at all three clocks. The first build hit the
known Command Line Tools linker/SDK mismatch while building host pioasm;
the documented full-Xcode environment repaired this build prerequisite without
changing source or dependencies. Both build logs remain. The clean independent
138 MHz rebuild is byte-identical. Local artifacts are under
`build/phase14-rc1-launch-repaired-xcode/`, with the independent build under
`build/phase14-rc1-independent/`. UF2 SHA-256 values:

- 132 MHz: `361e88297619253bbdd00bfc3fc73e9f11158b54747ee445b5c8f9191a173850`.
- 138 MHz: `5034a3fc2140deb7e5475ba0ff7043ada52c340c556401f8a24f6b11d264fa30`.
- 150 MHz: `562c47d81ad7779501f572e154e3739666394989527634aac91638df38a1c3c8`.

Both named boards have verified 138 MHz deployment with preserved settings.
The fresh receiver ABBA bracket measures a 1.1018203105 ppm nominal-to-true-time
scale offset, with 0.1755081261 ppm repeatability bound. It agrees with the earlier
bracket within those bounds. It is an engineering comparison with the previously
declared reference assumption, not a calibration certificate. Pico frequency
correction remains zero; NTP supplies UTC, not RF frequency discipline.

Pico B completed three ordinary standalone WSPR reservations, with local
ownership, durable watermark, no scheduler error, and disabled configuration
restored afterward. Independent decoding succeeds on all three. The first
frame fails the retained tone-spacing/order residual screen; the next two pass.
Resources pass. This establishes three actual frames and two operational screen
passes, not three passing release repetitions. The original result is retained
under private `build/rc1-standalone-three/`. Its analyzer additionally binds the
actual deployment record because this original producer record omitted the UF2
hash. Future records include that hash directly.

The installed native WsprryPi controller completed FSKCW on A and released
ownership. Initial attempts exposed its fixed singleton port and the temporary
INI's startup gate policy. The verified active `wsprrypi.service` is paused only
for a finite native test and restored on exit; the shared operational INI is
unchanged. A private loopback byte relay now retains the exact submitted LOAD
and ARM exchange and verifies device, boot, job, schema and CRC. Its first attempt
misclassified a native client's reset after completed RELEASE; complete valid
critical transactions were retained, but that receiver attempt stayed incomplete.
The repaired retry has complete control and receiver evidence under private
`build/rc1-controller-FSKCW-relay-repaired/`. Original failures remain.

Method amendment before wider producer analysis: a producer's terminal off
event can be one microsecond, too short for an interior phase fit. The keyed
analyzer skips that final off-event interior only and still requires the captured
half-second final quiet tail, correct envelope, no extra RF and unchanged mark/
transition/coherence criteria. Synthetic truncated tails and extra RF still fail.
Six independent RF fixture checks pass in the retained Harness environment;
the normal 158 host groups do not include these optional analyzer groups.
Twelve Phase 14 rejection/relay checks pass, including fragmented-byte drain
at half-close, corrupt/truncated envelopes and cleanup after unexpected ARM
admission in the clock-loss probe. Loopback validation requires network-enabled
execution on this Mac; no hardware is used by that test.

Prepared endurance automation fixes the proposed soak to eight finite one-hour
jobs, alternating both boards and Tone/512-event FSKCW, with ten-second HTTPS
activity on B and equivalent post-release idle sampling. Raw IQ and resource
observations are retained for separate assessment. Preparation is not execution.

The expanded current host run enables the seven retained Harness analyzer
groups and passes 165/165 groups. The subsequent pure receiver-axis regression
also passes: the reference anchor stays fixed, frequency differences/spacing
divide by the measured scale, durations multiply by it, original measurements
stay unchanged and Pico correction stays zero. Derived quantities are saved
separately with hashes of the original analysis and reference comparison;
they never rewrite original screening flags. Absolute UTC, certified reference
accuracy and phase-fit bias remain separate limits.

The exact native FSKCW retry independently passes timing, phase coherence and
resources, but fails the retained 0.2 Hz state-frequency residual screen.
Its measured separation is 5.0238063443 Hz, phase residuals 0.0088--0.1404 rad,
and all four transition errors are approximately -0.3 ms. This is a retained
RF screen failure, not a successful release repetition. The repaired candidate's
first two new 80 m WSPR repetitions on A pass; the adaptive batch remains active.

Spectral acquisition method fixed before its new survey: both boards at 138 MHz,
80 m and 6 m, harmonic orders one through five, sample-clock and twice-clock
lines and their plus/minus-carrier images. Each target has two-second RF-off and
RF-on acquisitions at gain 12 and 20, exact receiver metadata/hash validation,
and a final fundamental RF-off capture requiring at least 10 dB on/off contrast.
The source uses one finite 120-second Tone per survey and natural completion.
Report per-tune dBFS and on/off contrast; cross-frequency receiver/path response
is uncalibrated, and these controls do not exclude every receiver-generated
product. This evaluates the recorded unfiltered path; operator LPF work remains
outside Phase 14. The new survey is prepared and has not run yet.

The third A WSPR attempt in `rc1-mode-acceptance-138` exceeded the host's
three-second STATUS response deadline. It was safely aborted, released and
verified inactive, retaining the incomplete capture. That triplet is not three
consecutive complete frames. Phase 14 now uses the previously accepted
five-second single-flight administration bound (LOAD remains bounded at 30 s).
Other historical runners keep their default. The adaptive batch records an
isolated failed control row and continues independent rows only after verified
inactive/unowned readback; uncertain output still stops the batch. A new triplet
and remaining rows are running under a new evidence root. All 165 host groups
pass after this repair; the original failure remains.
