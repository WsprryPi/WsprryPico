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
All 54 jobs completed and both boards were returned to the identified 138 MHz
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
