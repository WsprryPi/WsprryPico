# Phase 14 PIO/DMA qualification and release plan

Status: ACTIVE. Authorized 2026-10-08. This plan is frozen before new RF
measurements. The operator subsequently clarified, before acquisition, that
there is specifically no LPF and that LPF development/application is their
responsibility. Qualification therefore covers the existing unfiltered
conducted path; building or qualifying an LPF is not a Phase 14 completion gate. Results and any explicit method amendments are recorded in
[phase14-results.md](phase14-results.md); historical failures remain unchanged.
P13.1 is complete, P13.2 Si5351 and GP14 production enablement remain deferred.

## Source review and intended scope

The starting checkout is devel at `4b42a5d624cc68aa318b6e8d69c84f9460dc1bb4`.
The untracked `tests/hardware/si5351-i2c/` is unrelated and preserved.
Reviewed areas: JobService validation/leases/replay/terminal retention, portable
NCO/sample planning, two-buffer PIO/DMA and zero-tail stop, UTC reprojection,
core-1 execution, standalone journals/watermark, transport/profile admission,
network/browser concurrency, allocation limits and Phase 12/13 launch changes.

Complete immutable jobs reach one JobService. Local RP2350 execution has no
per-symbol transport dependence. A disconnected owner or expired running lease
cannot establish RF inactivity. Failed disable retains failure/unknown output.
Absolute event boundaries are rounded to samples rather than accumulated.
The driver forces GPIO low on stop and drains a zero tail on natural completion.
P13.1 adds a checked indicator launch handshake, which can delay launch within
the admitted UTC second. Consumer profiles deliberately gate USB WTP and use
Plain LAN; engineering profiles retain USB/mTLS. The existing profile is recorded,
not silently replaced to make an unavailable transport pass.

Direct synthesis supports 100 kHz through sample-clock/2 minus 1 Hz, at most
four distinct NCO increments, 512 events and 3,600 seconds per job. Compare
132, 138 and 150 MHz/divider 1/RAM renderer on GP2. The 15 candidate band points
are inherited from the Phase 11.6 plan (2200 m through 2 m). At 132/138 MHz,
4 m and 2 m are unsupported for direct synthesis. At 150 MHz, 4 m is a synthesis
candidate and direct 2 m remains unsupported. Every band through 2 m remains
in the coverage record: a source limit requires an explicit unsupported
disposition, rather than omission or a failed decode. Harmonic output requires
a separately identified output route and does not
establish native direct-frequency support. Representability alone is not release support.
Modes are Tone, WSPR, QRSS, FSKCW and DFCW. DFCW retains dot-high/dash-low.

Positive correction ppb means a fast oscillator and reduces the NCO increment.
It does not calibrate the RP2350 timer or change sample-count duration. Bench
correction is volatile; ordinary standalone firmware currently has no operator
correction setting. Accepted nHz describes nominal NCO quantization, not a
measured calibrated carrier. These limitations must remain in the disposition.

## Bench and identity binding

Each Pico GP2 and the GPSDO passes through its own 20 dB attenuator into the
combiner. Combined signals pass through 40 dB attenuation into the SDR. There
is no antenna. This established setup is accepted, with 60 dB nominal source
path loss; no further operator setup confirmation is required. No assembled
output filter, buffer, matching or coupling network is identified by this
setup. Raw GPIO/attenuator/combiner results cannot qualify an output filter.
Loading and calibrated path loss are reported where measurable. Post-filter
emissions are outside this campaign. Release instructions require the operator
to develop/apply suitable filtering; no antenna-ready emission claim follows.

Automatically bind Pico A `0BF4B4AEC9FFB344` / device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, B `CDDBF8767C506C07` / device
`29f20b7342051ef947aa56cb9d4fab42`, RSP1B `2404058C60` and GPSDO
`0673ED0FA107`. Both boards are USB-connected to wspr5. Capture settings start
at CF32, 250 ksps, 200 kHz, gain 20, AGC/bias off, center carrier minus 25 kHz.
Use the retained Harness exact-count capture helper, existing phase-fit/keyed
analyzers and independent WSJT-X wsprd. Capture helper and decoder hashes,
firmware source/UF2 hash, boot, clock, job/digest, settings and actual capture
count/hash are mandatory bindings. Logs/captures/configuration stay private.

Read GPSDO frequency, enabled outputs, levels, lock and PPS before changing its
measurement output. Preserve unrelated reference/PPS settings and restore only
measurement settings actually changed. Its RF reference does not discipline
the Pico or SDR. A simultaneously recorded reference estimates tuning offset;
it does not by itself establish sampling-time scale. Report this separately.

## Methods and criteria established before acquisition

| Assertion | Method and acceptance source |
| --- | --- |
| Job/control | WTP/1 validation, identity/boot continuity, exact accepted adjustments, one finite local job; same-job terminal Complete and output false; RELEASE/inactive successor when owned. |
| Synthesis | Source range/quantization, all requested states distinct; reject unsupported LOAD without ARM; no fifth distinct frequency. |
| Screening carrier | Complete on/off capture, >=10 dB contrast, no clipping/overflow; existing analysis's 100 Hz acquisition window is a screening locator, not a calibrated carrier specification. |
| Operational keyed RF | Existing analyzer: 20 ms relative envelope, >=10 dB contrast, phase residual <=0.15 rad; two-state separation/residual <=0.2 Hz; frequency-transition fit <=20 ms and <=0.15 Hz. This retains a consistent screen; ambiguity is reported, not relabeled. |
| Human-copy QRSS family, explicit operator amendment on 2026-10-08 | QRSS, FSKCW and DFCW are intended for human copy. Drift and phase/coherence residuals are diagnostics, not automatic mode failures. Assess acquired continuous marks, correct envelope/gaps and transitions, >=10 dB contrast, amplitude ratio >=0.5, independent final silence and distinct locally ordered frequency states. For the requested 5 Hz states, require at least half the accepted separation near each change as a visibility margin. Keep 20 ms relative timing screens and all resource/control gates. Preserve legacy results and publish a separate human-copy assessment; WSPR criteria are unchanged. |
| Original WSPR diagnostic screen | Complete 162-symbol, 110.592 s frame and quiet before/after; 375/256 Hz spacing, historical <=0.05 Hz separation / <=0.1 Hz residual / <=10 ms transition screens. Retain these measurements and original flags as diagnostics. The operator's 2026-10-09 amendment supersedes their use as WSPR pass/fail gates. |
| WSPR acceptance, explicit operator amendment on 2026-10-09 | WSPR passes when the external tool decodes the expected transmission. Require successful external wsprd execution and the exact AA0NT EM18 37 message in retained stdout, bound to the capture and decoder receipt. Drift, frequency residual and transition-fit flags cannot exclude a decoded WSPR row. Control, capture integrity, resource and cleanup assertions are assessed separately. |
| Release timing/frequency | Report error and uncertainty independently. WTP permits launch within the requested UTC second, subject to admitted clock uncertainty. No inferred microsecond UTC claim. Physical symbol/frame precision and calibrated absolute carrier remain unqualified if receiver/reference uncertainty is not bounded. Historical suggested 10 us/100 us/0.1 Hz budgets are not promoted into new contracts. |
| Spectra/filter | Record close-in sidebands, in-window spurs, separately tuned harmonics/images through at least fifth harmonic where receiver coverage permits; exact coverage and receiver attribution. Retain operator's better-than-WsprryPi close-in benchmark. Qualify the recorded unfiltered path only; LPF development/application belongs to the operator. No filtered-output or antenna-ready emission claim. |
| Resources | No new unexpected allocator/TLS/DMA/stack faults; refill-to-ready below actual full-buffer period, no exhausted predecessor; >=32 KiB preserved authority reserve. Compare equivalent idle windows for growth, with the established 1,024-byte return screen and retained raw samples. |
| Endurance | Finite 60-minute complete jobs, maximum 512-event and 32-character workloads, repeated jobs, transport recovery, realistic Wi-Fi/browser load, natural completion/abort/cancel; no output afterward. An eight-hour mixed soak is proposed for final release, distinct from the historical inhibited soak. |
| Reproducibility | Same pinned SDK 2.3.1, Arm GCC 15.3.1 and picotool commit; clean independent build directories; identical UF2 payload/artifact hashes or investigated differences. No generated firmware or secrets committed. |

Separately tuned spectral surveys use a finite 240-second Tone;
each two-second receiver capture requires the same active Running job/boot both
before and after capture so that a job ending during acquisition cannot be
misclassified as an RF-on measurement.
The retained 80 m Pi close-in benchmark is compared using a full 1,048,576-sample
Hann window at 250 ksps (0.238419 Hz bins), measured-carrier centering, searches
within +/-5 Hz of +/-120 Hz and an equal trailing-off window. Require >=10 dB
carrier on/off contrast. Preserve phase/waveform flags separately; this relative
peak-bin comparison does not establish integrated emissions or calibrated power.
The feature search was widened from the prepared +/-2 Hz helper before its first
current-image acquisition to match the retained Pi benchmark's +/-5 Hz search.
This includes more potentially stronger features and leaves the benchmark limits
unchanged; RF windows and measurement dates remain different.

Use short Tone screens across band/clock on both boards before expensive mode
acceptance. Start with Tone and complete WSPR at 80 m/138 MHz on both boards.
Then screen all representable band/clock candidates. For promising release
configurations require three complete WSPR frames and three keyed repetitions,
including disconnect/reconnect, plus both-board consistency. Under the operator's
amendments, attempt each representable band and mode even if a preliminary
Tone diagnostic screen fails. Uncertain output or invalid capture/control
evidence still prevents a dependent RF attempt until resolved.

The operator's human-copy amendment supersedes automatic rejection of QRSS-family
rows for smooth drift or long-mark phase residuals. Retained captures may be
reanalyzed with this separately identified method. Rows previously stopped by
the legacy diagnostic screen require their missing repetitions if the new
human-copy, timing and resource assessment passes. Do not erase or relabel the
original screen. The separate 2026-10-09 WSPR amendment makes external decoding
the WSPR acceptance criterion. Reuse existing exact-message decodes and acquire
only missing repetitions; do not repeat accepted captures to erase diagnostics.

Include three accepted observations for the representable 150 MHz/4 m keyed
and WSPR rows, reusing their first comparison capture when applicable. Verify
the direct 2 m boundary using finite unarmed LOAD requests on both boards at
each supported clock; an unexpected admission must be aborted and released.
This checks the advertised implementation limit and does not declare harmonic
or image output physically impossible.

The operator's 2026-10-09 clarification requires investigation of actual 2 m
output rather than stopping at direct-frequency rejection. Run a finite,
explicit third-harmonic trial: nominal engine base 48.1635 MHz, measured output
144.4905 MHz. Divide WSPR tone spacing and QRSS-family frequency shifts by three
in the submitted complete job; preserve symbol/mark/gap timing. Multiply accepted
engine frequencies by three only for the RF measurement's expected-state axis.
Tune the SDR and simultaneous GPSDO reference to the actual 2 m region. Use
unmodified captured IQ/audio and the same external-decode/human-copy criteria.
Start with a short WSPR pilot: three complete frames on each board at 138 MHz.
Expand to the full five-mode/all-clock trial only after six of six expected
external decodes with valid control/capture/resource evidence. Reuse these
six pilot frames as the 138 MHz WSPR repetitions. For keyed modes acquire
three observations at 138 MHz and one at each comparison clock; Tone uses one.
Preserve unsuccessful observations; a decode failure leaves the pilot unresolved
for diagnosis rather than proving a physical band limitation.
This trial does not change firmware, advertise native 2 m requests, qualify an
operator filter, or establish standalone 2 m mapping. Positive RF results require
an explicit application frequency-routing implementation before native 2 m can
be declared supported; the direct rejection checks remain separate boundary evidence.

The operator's later 2026-10-09 amendment makes frequency placement and drift
informational for every band and mode. Calibration has not been selected.
Record requested/accepted/measured frequency, excursion over the observation,
fitted drift, defined segment edges and available clearance/uncertainty. Annotate
observed movement that could hinder reliable operation without a segment or drift
pass/fail determination or band exclusion. WSPR remains accepted by external
expected-message decode; QRSS/FSKCW/DFCW remain assessed for human copy.

For the 2 m pilot, the conventional WSPR window is derived as
144.489 MHz USB dial plus 1400–1600 Hz, or 144.490400–144.490600 MHz
([WSPRnet dial list](https://www.wsprnet.org/drupal/WSPRnet/map?destination=WSPRnet%2Fmap),
[K1JT's WSPR subband description](https://sourceforge.net/p/wsjt/mailman/wsjt-devel/thread/54E7E4EF.70308%40princeton.edu/)).
Report the union of simultaneous-reference per-symbol frequencies on both
bracketed receiver sample scales, with explicitly stated engineering estimator
and reference allowances. This describes the wanted component, not all unfiltered
RF energy or a regulatory spectral mask. The general WSPR annotation records
the 200 Hz window centered on the requested bench point. QRSS bench jobs have
no assigned operator segment: report their frequency offsets and state-removed
drift with `window_unspecified`, without inventing segment boundaries from a
WSPR frequency. No segment observation gates the 2 m expansion decision.

Retain raw phase/timing/spectral measurements even when a historical analyzer's
composite flag fails. Investigate receiver artifacts with retuning/gain/reference-
only controls; do not weaken frozen limits to obtain PASS. Preserve every failed
attempt and create new results after repairs. Capture failure is acquisition
failure, not a transmitter failure or successful measurement.

## Prior evidence and final applicability

Phase 11.5 closes six resource families only at 138 MHz/divider 1/GP2/RAM on
its identified firmware. Phase 11.6 accepts exactly 13 rows and no WSPR row.
Phase 11.7 reconciles that scope; earlier 80 m/2200 m independent WSPR decodes
are useful historical demonstrations. Phase 12/13 changed the running network,
allocator/layout and launch paths; current RF candidates require fresh affected
resource/launch measurements. Alternative clocks require their own load checks.
Existing LED/button functional evidence is reused; no new LED/polarity/button
campaign is a release prerequisite.

Stage completion is assertion-level, not a runner PASS label. The final review
challenges incomplete IQ, source/boot/job substitutions, nominal-vs-measured
frequency, reference uncertainty, matrix gaps, stale runtime applicability,
filtered-output claims and final cleanup. Finish each bounded batch, verify
actual RF inactivity and disabled schedules, retain useful RF firmware, close
owned connections/processes, and commit/push only intended Phase 14 files.
Phase 14 is complete only after all required qualification and release gates,
final review, commit/push and independently checked remote parity. An unresolved
firmware or required measurement assertion must be reported as open; an LPF
is an operator responsibility, not an unresolved Phase 14 firmware gate.
