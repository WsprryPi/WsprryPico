# Phase 14 qualification results

Status: IN PROGRESS. See the pre-acquisition [plan](phase14-plan.md).
No Phase 14 release support is claimed at this checkpoint.

## Numeric progress checkpoint

Three of the nine original workstreams are complete (33.3% by workstream count,
not an estimate of elapsed effort). The finite `2fdfdf8` continuation is active
after the original eight-hour soak closed and its browser-load assessment
failed. The independent WSPR evidence reduction is complete. Its original
waiting upper-band queue was replaced before any RF work by `6443197`, which
starts with a 2 m WSPR pilot and conditionally expands to the full harmonic trial;
closed cases remain closed.

| Workstream | Completed count | Percentage |
| --- | --- | --- |
| 1. Initial source and historical-evidence review | 1/1 | 100% |
| 2. Established plan and acceptance record | 1/1 | 100% |
| 3. Bench identity and tooling preparation | 1/1 | 100% |
| 4. Main 138 MHz WSPR/keyed matrix attempts | 104/104 rows, 174 finite jobs | 100% of attempts |
| 4. WSPR external decode acceptance | 42/42 captures; 26/26 tested board/band rows | 100% |
| 4. WSPR rows with three frames | 8/26; 36 additional frames required | 30.8% |
| 4. Three-observation human-copy rows | 78/78, all passing, 234 observations | 100% |
| 4. Refreshed alternative-clock campaigns | 0/2 | 0% |
| 4. Required post-comparison 138 MHz Tone sweep | 0/26 | 0% |
| 4. 150 MHz/4 m repeated mode rows | 0/10; follow-up prepared | 0% |
| 4. Direct 2 m boundary checks | 0/30; unarmed checks prepared | 0% |
| 4. Actual 2 m WSPR pilot | 0/6 frames; pilot prepared | 0% |
| 4. Actual 2 m third-harmonic mode/clock rows | 0/30; conditional on reliable pilot decoding | 0% |
| 5. Main timing/capture analyses | 174/174 | 100% |
| 5. Paired Tone/QRSS diagnostic captures | 6/6, plus all separate analyses | 100% |
| 5. Requested frequency-compensation trials | 6/6 | 100% |
| 5. Dedicated wideband spectral surveys | 0/4 | 0% |
| 6. Refreshed ordinary native-controller jobs | 12/12 complete and analyzed | 100% of attempts |
| 6. Additional native WSPR at accepted 160 m point | 3/3, all full-screen passing | 100% |
| 6. Maximum-message cases including alternating DFCW | 4/4 complete and analyzed | 100% of attempts |
| 6. USB-unavailable standalone WSPR | 3/3 externally decoded | 100% |
| 6. Clock-loss/cancel/abort/disconnect/maximum-event scenarios | 9/9 assessed | 100% |
| 6. Eight finite one-hour soak jobs | 8/8 closed; original browser-load failure retained | 100% of jobs |
| 6. Repaired browser-load hour jobs | 4/4 closed and analyzed; idle-growth failure retained | 100% of jobs |
| 7. Candidate clock images built | 3/3 | 100% |
| 7. Independent selected-image rebuild | 1/1, complete bytes identical | 100% |
| 7. Final both-board installation/smokes | 0/2 | 0% |
| 8. Final adversarial assessment | 0/1 | 0% |
| 9. Final push, remote parity and closeout | 0/1 | 0% |

All 165 deterministic host groups pass. The independent main integrity audit
passes 174/174 captures and 104/104 rows. These are completed checks rather than
release promotion. Intermediate repairs and initial controller/standalone tests
are retained; remaining reliability/failure workloads and final applicability
still have to finish. At the reviewed `1464d26` tool snapshot, devel had 43 local commits beyond the
verified starting remote, no push has been made, and the unrelated untracked
Si5351 directory remains preserved.

The operator explicitly amended WSPR acceptance on 2026-10-09: a correct
external decode passes WSPR. All 42 main-matrix captures decode AA0NT EM18 37,
so all 26 tested board/band rows pass this criterion, from 2200 m through 6 m.
The previous 19 exclusions arose from the selected 0.1 Hz symbol-residual
screen, rather than failed decodes. Preserve its original seven passing and
19 excluded row flags as diagnostics; they no longer determine WSPR acceptance.
Eight rows already have three decoded frames, while 18 need two more frames
each. Ordinary native 80 m and 160 m WSPR and the USB-unavailable standalone
triplet each have 3/3 correct decodes under the same criterion. The separate
human-copy family has 78/78 passing rows.

The acceptance/workload repair is committed as `2fdfdf87fc25a7c677391598b5af5b0e1ceff37a`.
Its immutable source archive SHA-256 is
`300e6790575994f018ba50c89302608d4790e61c2e70469173b442a227835d6a`;
all 1,798 extracted files were verified. Finite continuation script SHA-256
`d1a29ec4ee8033f71a0b73ee5e8e5a0852417e23759fecd372c65218a1f0d3ac`
waits for the exact predecessor process/start identity and its expected closed
browser-load failure. It then collects the 42 actual external decode receipts,
repeats four B hour cases, separately assesses the retained original soak,
acquires 36 missing WSPR frames, and continues spectra/alternative clocks/Tone
checks. No firmware build input changed in this repair.
The final supported/failed/unresolved release dispositions await the remaining
reference, spectral, producer, reliability and final-image assertions.

All 15 candidate bands, 2200 m through 2 m, remain required coverage entries.
Current direct synthesis ends below half the sample clock: 4 m is representable
at 150 MHz, while 2 m is outside the direct-frequency contract at 132, 138 and
150 MHz. These source limits are distinct from failed transmissions or decoding.
The refreshed comparison must attempt every representable mode and retain
explicit unsupported entries for the others.

The finite upper-band follow-up retains the first 150 MHz/4 m mode screens and
acquires only missing accepted repetitions. It also checks all five direct
2 m LOAD requests on both boards at 132, 138 and 150 MHz: 30 explicit negative
configuration checks with no ARM attempt. An unexpectedly admitted LOAD is
aborted and released. These checks establish the current firmware boundary,
rather than a physical impossibility of generating a harmonic/image at 2 m.

The operator subsequently challenged treating this direct limitation as
exclusion of 2 m. Actual 2 m output is an open engineering/qualification item,
rather than completed coverage through rejection alone. The prepared host-only
third-harmonic trial submits a 48.1635 MHz complete job and receives at
144.4905 MHz. Frequency-state spacing is divided by three before LOAD; accepted
frequencies are multiplied by three in the measurement expectation. Timings and
captured IQ/audio remain unchanged. WSPR is decoded at the actual 2 m receiver
tune. Both boards/all three clocks are covered, with missing repetitions of
passing 138 MHz rows acquired in the same finite batch. Existing firmware and
its direct-frequency API are unchanged; native standalone/controller 2 m
frequency routing remains unimplemented and cannot be claimed from this trial.
No 2 m RF transmission has been performed yet.

The later operator amendment requires a quick WSPR pilot before expanding this
trial: three complete frames per board at 138 MHz. All six must decode the exact
expected message with valid control/capture/resource evidence before the full
five-mode/all-clock batch runs. The full batch reuses those six captures.
Frequency placement and drift are informational only, with an explicit null
pass/fail determination and no band exclusion; calibration remains undecided.
The 2 m pilot adds bracketed GPSDO/sample-scale frequency-envelope, edge-clearance
and drift estimates against the conventional WSPR window defined in the plan.
General mode reports retain state-removed frequency excursion and fitted drift.
The QRSS bench workloads do not specify an operator operating segment, so they
report `window_unspecified` rather than inventing boundaries or a confinement
verdict. An outside-window estimate can coexist with a successful decode and
does not prevent expansion. No final support or release claim follows from a
pilot alone.

The initial time estimate at 2026-10-09 12:34 UTC is 18–26 hours remaining,
including analysis, conditional full 2 m testing, final both-board smokes,
adversarial review and commit/push/closeout. Three of nine workstreams are closed
(33.3% by count). The estimate uses about 3.4 hours of browser repetition remaining,
6.42 hours of alternative-clock captures and 1.57 hours of missing WSPR captures,
plus remaining analysis/control/finalization work. New defects or implementation
needed for native 2 m routing may extend it. An hourly heartbeat refreshes the
private `build/phase14-progress-estimate.json` from actual progress and reports
one line in the operator-selected count/percent/time-remaining format. This
schedule does not stop an active test.

The original harmonic adapter and meaningful waveform/identity/index rejection checks
are committed as `f0d5434e3158541e0bfe7dccdc90cb43e7dd2d7f`; all 31 affected
deterministic tests pass. Its source archive SHA-256 is
`636a7a81e1c8540193515b03e4f3c008d971e425ef219925287d30921e6a7f53`,
with all 1,801 extracted files verified. Finite coordinator SHA-256 is
`a732cf0ce14e5dcc49d518b92900d1476682fd4fb6f0b449e748ebe068a4406f`.
That earlier queue waited on the exact active `2fdfdf8` PID/start identity, then planned
2 m reference brackets, the actual harmonic mode/clock trials, and the retained
4 m repetitions/direct-limit checks. It does not alter the active browser job.
The former `1464d26` queue was stopped only while waiting, with its single
completed offline audit preserved and zero RF steps started. Queue replacement
receipt SHA-256 is
`ed74a90ef37567b6156a5c6b51c8226589ce7accc0034186f7dbd370fa9d73b4`.
Positive harmonic reception also needs source-attribution assessment before a
transmitter-support claim; on/off reception alone does not exclude a
receiver-generated harmonic. Native 2 m mapping and that attribution remain open.

The pilot-first and informational-frequency tools are committed as
`c5f0e579d68720743502ee5a60468b2c73ec4bc0`. All 35 affected deterministic tests
pass on both the Mac and wspr5. The source archive SHA-256 is
`2505ba3f63264f710e1ba395eec457de24114c42ae811c78da237800eb486c77`;
all 1,803 extracted files were verified. Private coordinator SHA-256 is
`cc73b7badbdf523f33ae4225d21fdb1d825d6542820618a6407d7bf817dbd4b4`.
That first pilot queue was verified waiting as PID 2333498/start ticks 46742547, with zero steps
started, for the unchanged active PID 2312716/start ticks 46309764 and its
71-step successful boundary. It runs the pilot first, verifies/reuses successful
pilot decode evidence for conditional full expansion, then continues the
independent 4 m repetitions/direct-frequency API boundary checks. A pilot decode
problem leaves full expansion pending diagnosis; frequency annotations never
make that decision. The replaced `f0d5434` coordinator had no started steps;
its preserved stopped boundary SHA-256 is
`8b217cbeec0b0a2183b97380a32036230118cf746b96dc5cd47a1befe99db74a`
and replacement receipt SHA-256 is
`21a0dd8ac5b1e4b72f31fc6ea3afd76c1ef2a7fcd55e12262472b73f300049ac`.
No active test was stopped or changed. No firmware build input changed and no
push has been made at this checkpoint.

Retained-IQ integration then found that the new WSPR annotation rejected NumPy
real scalar interval values. Repair `6443197` accepts finite real scalars while
still rejecting booleans/nonfinite data. All 35 deterministic tests pass on both
hosts. A fresh immutable archive has SHA-256
`951c727f9fca4c4a0a292b6754201149749e8658e84c3ebc5f4db18eca7f93ef`,
with 1,803 verified files. The repaired coordinator has SHA-256
`0dcb0518b729539e1c4c4bc042890a9fd5f3c7090feead28e473b51b9ef2b71f`
and is verified waiting with zero steps as PID 2335036/start ticks 46766222.
It preserves the same active predecessor and pilot-first finite sequence.
The stopped, never-started pilot queue boundary has SHA-256
`8ccef399f0f5359bc76d2814a5c2fc617c9996a79ad22e7fa94568dea9496a6a`;
replacement receipt SHA-256 is
`8ade43b594f46fa3cfb70696fb7fed6fcd1ec3004e2d7154f19e26865f1a5141`.
No active test was stopped. New immutable retained-IQ analyses confirm that
the WSPR result still externally decodes and QRSS still passes human copy while
its legacy composite screen fails. QRSS reports a 0.03499 Hz state-removed
frequency excursion and -0.000878 Hz/s fitted drift, `window_unspecified` and a
null pass/fail determination. The initial incomplete WSPR annotation output
is preserved; repaired analysis uses a new label. These are offline analysis
verification observations, not additional RF repetitions.

The original soak's four B jobs made 290-292 successful browser requests
per hour, below the frozen 300-request minimum despite spanning the full hour.
The host timer measured ten seconds from request completion, adding latency
to each interval. The repaired timer measures from request start. Preserve the
original eight-hour evidence and its browser-load failure, and repeat only
the four B one-hour browser cases; resource and RF results remain separately
assessed. This is a workload-generation defect, not an observed transmitter fault.

At the 2026-10-09 16:46 UTC checkpoint, all four browser repeats have completed
and their RF/browser assessments are finished. They made 341/339/338/338
successful requests; all meet the frozen count/span requirements. Both Tone
jobs pass the operational screen and both FSKCW jobs pass human copy. Every
per-job resource assessment passes, but the equivalent FSKCW idle-window median
grew by 2,696 bytes, above the frozen 1,024-byte limit. Tone idle median growth
is 480 bytes. The batch therefore fails its idle-growth/resource aggregate;
do not relabel that failure or infer an RF/drift failure. Assessment SHA-256 is
`7bc2b0a0fc7f3c0bd5da2618057f2989a6d1f545ee355e69d3f8a78274018d49`.
Four-job offline analysis took 2,892.23 seconds (48.20 minutes). The unchanged
finite coordinator is now analyzing the original soak and continues independent
work; full qualification remains open.

A finite read-only B observation, made only after confirming the predecessor
was doing offline analysis and acquiring the normal board lock, preserved its
boot/source/138 MHz clock and inactive output. After the existing replay-cache
expiry interval, heap samples are 36,628/36,620/36,628 bytes, below the failed
45-second FSKCW samples of 42,004/42,004/42,012 bytes. TLS allocation remains
4,397 bytes. Private receipt
`build/resume-tools-6443197/build/heap-post-expiry-20261009T1649/samples.json`
has SHA-256
`cd706e6a7584899209e1135bfdc801f917cc5ad776268065bec54107dfb48d32`.
Source retains responses/sessions for 300 seconds, while the repeat sampler
waited 45 seconds. Cached state is therefore a possible contributor, not a
proved cause or a passing replacement assessment. The original four B soak
idle windows had only 296 bytes of equivalent FSKCW median growth. Diagnose
the retained-state contribution and obtain comparable evidence before closure;
no firmware repair is claimed. No active test was interrupted or duplicated.

At the next hourly checkpoint, a second same-boot/source/clock locked INFO-only
observation after the one-hour terminal-history lifetime records stable
23,084-byte idle allocation, 31,284 allocator-live bytes and unchanged 4,397-byte
TLS allocation. Output is inactive throughout. Private receipt
`build/resume-tools-6443197/build/heap-post-terminal-expiry-20261009T1754/samples.json`
has SHA-256
`1f20c06f8c4fcfc2366a0edbab5b447e7906d9c23caea16f3302199ad7c2fbcd`.
This shows bounded memory return; it does not identify the original pair's
2,696-byte difference or replace its failed assessment.

The prepared host-only `phase14_idle_growth.py` follow-up acquires exactly two
additional B/138 MHz/80 m one-hour, 512-event FSKCW/browser jobs on unchanged
`bd45bc1bb638` firmware. Each preserves the existing 45-second idle window and
adds three INFO-only observations at least 350 seconds after owned transport
closure, beyond the contract's 300-second replay/session lifetime. Source,
boot, settings, inactive output and complete capture/resource/browser/RF evidence
must bind both observations. Compare both policies separately using the unchanged
1,024-byte growth/spread limit; no automatic release promotion follows. The
original failure remains immutable. This follow-up must wait for the active
batch and existing 2 m/4 m continuation; it must not interrupt an active test.
All 36 affected deterministic tests pass on the Mac, including malformed-window
rejection and preservation of the original 2,696-byte failure. No firmware build
input changes in this diagnostic/validation preparation.

The completed independent external-decode reduction rehashes all 42 original
IQ/metadata pairs, checks source/device/job/analysis identities, verifies each
actual decoder invocation and unchanged wsprd binary, and hashes decoder
receipt/stdout/audio files. It confirms 26/26 accepted rows, 42 correct decodes,
all resource assessments passing and exactly 36 missing repetitions. Private
receipt `build/resume-tools-1464d26/build/main-wspr-external-evidence-verified.json`
has SHA-256 `994aa84adc175a0c911455bea4633bc27817d237510b84997683f121c9be8e1e`;
the reducer script SHA-256 is
`28e1224034a2850b480f6060af57857fda7b5f4725efc1ea25b0d532ace40b28`.
The separate upper-band continuation archive SHA-256 is
`87d3bf7283057c131bf8aeea3d2b19bb7a2faedf04778891ce80c4679d73876c`,
with all 1,799 files verified; coordinator SHA-256 is
`434ed4449a850b6b0afaed782194aefe0c508ba2926a40f378f00d3319cfb83e`.
It requires the exact active predecessor and all 71 remaining steps to close
successfully before any upper-band RF work. All 30 affected deterministic
tests pass. Neither continuation installs the final release candidate or
claims Phase 14 complete.

The original coordinator stopped at its expected browser-count assertion after
14 completed steps. Closed boundary SHA-256 is
`7c90f03dd8314141102508b686d16c20bd15bb86a3e34170aff600bd5dc694d2`.
The repaired continuation passed inventory, its separate 42-capture acceptance
reduction and reference preflight, and began the first B one-hour browser job.
Live recorded INFO shows source `bd45bc1bb638`, 138 MHz, the preserved B boot
`ac148eba9e05ea4afa5a7ebc46cb0302`, Running and output active. Six observed HTTPS
requests returned 200, and the receiver file grew 3,999,744 bytes in two seconds.
This confirms actual execution; it is not yet a completed browser workload or
final soak acceptance. The wsprrypi service remains active.

A later live checkpoint confirms the same B job remains Running/output active,
with 129 browser requests observed and 2,706,020,352 of 7,290,000,000 capture
bytes retained (37.1%). Completed browser-repeat jobs remain 0/4; count-based
progress uses closed jobs, rather than promoting a partially captured hour.

## Retained execution checkpoints

The following entries retain the evidence and knowledge at each earlier
checkpoint. The current counts and operator amendments above supersede older
active/queued descriptions and older composite-screen acceptance statements.

The human-copy repetition stage has completed all 78 rows: three modes at all
13 representable points on both boards. All 234 observations pass the separate
human-copy/resource method. The stage supplied 102 additional finite jobs,
reusing 132 retained observations without changing their original machine flags.
Its closed receipt permits an independent raw-evidence audit, pipelined with
the next paired Tone/QRSS diagnostic. This completes the repetition subtask;
other clock, spectral, reliability and release gates remain open.

A separate immutable `afaeb70` host-tool snapshot has queued the additional
32-character alternating E/T DFCW controller case. Coordinator SHA-256
`38f83fe98c70a1d7037fbd137ac9f1b754d94b1bd37ca1e19ebb75862fda6512` and
source archive SHA-256
`6e77bea81e5fb47760b890713f05ddcfef43d15a5b97b0cf9bd015c5c39f6f3f`
were verified, along with all 1,794 extracted files. It waits on the exact active
predecessor PID/start identity and requires every continuation step to complete
successfully before RF begins. It has performed zero RF steps at this checkpoint.

The independent human-copy audit passes all 234 observations and 78 rows. It
rehashes actual IQ/metadata, binds all three unique jobs per row, checks accepted
event continuity, same-boot natural completion/inactive boundaries and GPSDO
readback, verifies analysis/tool hashes, and independently checks requested
envelopes, mark continuity/contrast, local frequency-state ordering and raw INFO
resource counters. Private receipt
`build/human-triplet-independent-audit-afaeb70-retry/result.json` has SHA-256
`8d2832aacb4435db48faba2ba9db622ec09cda097c4f05bb90a6544907ef6f76`;
independent script SHA-256 is
`bdff6890eb215e638736fa8a60d4619f7951ce6e8c062f19e57f80043eabc726`.
The original audit rejection is retained: its strict Boolean assumption did not
recognize the Console's numeric stack-guard value `1`. The separate retry accepts
only Boolean true or integer 1; no resource criterion or RF record changed.
This audit does not promote release qualification. The paired Tone/QRSS stage
has completed all six planned finite captures and their separate diagnostics.

Three balanced Tone/QRSS pairs use identical 45-second pre-job idle and the same
nine-second interior at event offset 13 s, with 20 ms excluded at each edge.
QRSS fitted drift across that interval is -0.08648/-0.08675/-0.08806 Hz; Tone is
-0.03949/-0.03704/-0.03582 Hz. Linear phase RMS is 0.1835-0.1870 rad for QRSS
and 0.0752-0.0829 rad for Tone. Independent 25 Hz FIR results agree closely.
Reference pairing retains the difference; quadratic phase fits reduce QRSS
residuals to 0.0269-0.0287 rad. This supports smooth mark curvature as the origin
of the legacy phase flag. It does not establish a thermal cause or exclude
every possible in-band contaminant. Three-second dots/nine-second dashes and
human-copy assertions pass, with original machine flags retained.

All three matched 80 m Tone close-in comparisons meet the retained Pi peak-bin
benchmark. Receiver-visible search-region peaks are about -89.4 to -91.7 dBc;
some on/off differences are below 10 dB, so those particular weak features are
not independently attributed to the Pico. The measured region bounds remain
well below the historical -21.66/-21.49 dBc benchmark. Different dates/windows
and uncalibrated path/receiver response remain explicit limitations. The next
finite step compares zero and +/-1,500 ppb requested compensation on both boards;
Pico engine correction stays zero.

All six requested-compensation trials are complete and pass waveform/resource
screens. For A, mean reference-compared carriers at zero/+1,500/-1,500 ppb are
3,570,102.3207 / 3,570,096.9516 / 3,570,107.7179 Hz; for B they are
3,570,094.8527 / 3,570,089.4490 / 3,570,100.1915 Hz. Positive request compensation
lowers the carrier, negative raises it, consistent with the roughly 5.36 Hz
request change at 3.5701 MHz and quantization/settling differences. These values
use nominal sampling axes with simultaneous GPSDO subtraction; they are not an
absolute traceable calibration or a persisted Pico setting. Engine correction
remains zero, and later baseline jobs request zero compensation.
Private closed-analysis checkpoint `build/keying-compensation-closed-checkpoint.json`
under the immutable continuation snapshot has SHA-256
`64ef6009ad480fc0f974bde76d66605d4a43c42a6b781b7f633a29bed8dab09f`.
It binds the six paired and six compensation analyses by hash, retaining original
flags and separate human/resource outcomes. Refreshed native-controller
repetitions have started; final release gates remain open.

The first three refreshed native WSPR control runs have completed with captured
inactive successors. The first frame decodes correctly and passes resources,
spacing, 110.592-second duration and 1.1 ms maximum transition error, but its
0.102417 Hz symbol residual exceeds the frozen 0.1 Hz screen. The second frame
fully passes at 0.095782 Hz residual and decodes correctly. The first failure
is retained; no native three-frame RF pass is inferred. Third-frame analysis
also decodes and passes resources, but fails at 0.104659 Hz residual. Thus the
original native 80 m triplet is 3/3 decoded and 1/3 full-screen passing.
The remaining ordinary and maximum-message
controller cases continue independently through the shared JobService.

Before further native WSPR acquisition, the host controller helper now accepts
an explicit low-band point, sets the matching INI dial frequency, receiver tune
and GPSDO reference, records the band and checks the actual submitted RF states
against that point. Existing calls still default to 80 m. Three additional
finite native WSPR frames at 160 m are required to bind the controller path to
a both-board accepted WSPR candidate point. The failed original 80 m triplet is
retained, and criteria are unchanged. This is an additional qualification case,
not a restart of independent work. Installed CLI help and local deserialization
source confirm the frequency interface; syntax/help/diff checks pass. Active
immutable campaign files and Pico firmware remain unchanged.

The isolated `85e8906` native-low-band snapshot is verified (1,794 archived files),
source archive SHA-256
`6ef1beb255d9ab7ff12385b58c70d557137356ea1deb56512c1d34422ed37b2a`,
coordinator SHA-256
`cfe6cd930a05607fadbb08588a6689f2bfdb571a1e8c29fbc56bd8312c19dccb`.
It waits on the exact DFCW supplement PID/start identity and requires its complete
success receipt before taking board/receiver ownership. At verification it had
zero RF steps. The active original sequence has completed eight of twelve
ordinary native jobs; all three QRSS and the first two FSKCW analyses pass human
copy and resources. Devel now has 37 local commits beyond the starting remote;
no push has been made and no firmware source changed.

All twelve original ordinary native-controller jobs are now complete and
analyzed. QRSS, FSKCW and DFCW each have three passing human-copy/resource
observations (9/9 total). WSPR retains three correct decodes and one full-screen
pass; its two residual-screen failures are not promoted. The 32-character QRSS
workload is active. The added 160 m WSPR and alternating 32-character DFCW queues
remain guarded and unstarted; remaining reliability and release gates stay open.

The first maximum-length QRSS job completed its 567.000001-second local waveform,
but receiver finalization failed. All 162,500,000 requested samples were retained
with zero overflows/clipping; the helper's complete-file hash and cleanup took
its elapsed time to 664.93 s, beyond the configured 662 s limit. The existing
capture helper checks its deadline after SHA-256 and cleanup and removes failed
output, so no complete IQ artifact remains for qualification. The original
failure metadata and controller record remain unchanged. This is acquisition
failure, not a Pico timing/engine failure or an accepted maximum-message result.
The coordinator stopped at step 56 after 55 complete steps. Both dependent
queues stopped with zero RF steps. Original host service is active; both named
boards report disabled schedules, no owner and inactive output.

An independent fresh five-second quiet capture with healthy simultaneous GPSDO
reference is 54.926/54.763 dB below the same-setting, current-boot A/B on baselines.
It verifies receiver-visible inactivity before resumption. New host budgets
separate RF job duration from sampling and file finalization: nominal sample
duration plus at least 30 s margin, or CF32 hashing at 32 MiB/s plus 15 s,
whichever margin is larger. This conservative rate is below the observed roughly
99 MB/s. Parent waits cover the same helper deadline with 20 s startup margin.
The 650 s capture budget is now 704 s; a 3,645 s hour-job capture has a 3,878 s
budget. RF duration, exact sample counts, overflow/clipping and cleanup gates
are unchanged. All 23 affected portable checks and the configured CTest group
pass. Only unfinished cases will resume in a fresh immutable tool snapshot.

Unfinished work has resumed from immutable `c126bc5` in
`build/resume-tools-c126bc5`, archive SHA-256
`b3c9bcf78041dc23e8798380490c29168e4b4744ab1243eb4e5c24987684970f`,
coordinator SHA-256
`82e17d4228b2a8a34bf4d292f17e69cc0b2ff88c2f17766ed20ff23b224c70cc`.
All 1,794 extracted files were verified. The coordinator requires exact hashes
of the previous 55-complete/one-failed boundary, failure metadata and new physical
quiet receipt before taking ownership. It retries the failed maximum QRSS
capture, runs the three other maximum-message cases and added native 160 m WSPR
triplet, then continues the previously unfinished standalone/failure/soak/
spectral/clock/Tone/reference work. Earlier successful batches are not restarted.
The eight RF jobs remain exactly one hour each; their finite host-step ceiling
is ten hours to include capture tails, hashes and identical idle windows.
Devel has 38 local commits beyond the starting remote, no push, and no firmware
implementation change from the identified runtime.

The resumed maximum-message cases are now 4/4 acquired and analyzed. QRSS,
FSKCW and alternating E/T DFCW pass human-copy/resource assertions. The 32-T DFCW
case passes waveform/resources but cannot assess two frequency roles because
its requested content contains only dashes; the separate alternating case
covers that requirement. Original strict machine flags remain unchanged.
The added native 160 m WSPR triplet is 3/3 full-screen passing. USB-unavailable
standalone reproduces and analyzes all three 80 m frames; two full screens pass
and the first retained failure remains. B clock-loss/recovery and A cancellation,
abort and disconnect control cases are complete. A cancellation resolves no RF
above its off criterion, 54.734 dB below its matched live baseline. Clock-loss
and disconnect operational analyses pass. The generic full-Tone analyzer flags
the deliberately shortened abort as a duration/missing-segment failure; a
separate action-aware abort assessment is required before qualification.

The continuation stopped at step 26 after 25 complete steps: A's 512-event LOAD
connection reset. The submitted JSON payload is 52,601 bytes, below the fixed
65,536-byte framing limit. No LOAD reply or ARM was recorded; Console cleanup
shows the predecessor complete and output inactive. RELEASE on the broken socket
also fails, so ownership expiry is explicitly checked rather than assumed.
Both boards subsequently have no owner, disabled recurrence and inactive output.
A fresh five-second physical quiet capture with healthy simultaneous GPSDO is
55.970/55.807 dB below the same-setting/current-boot A/B live baselines. Original
failed submission and receiver records remain. Source-bound transport/resource
diagnosis is underway; the eight-hour soak and later spectral/clock cases have
not started. No firmware replacement or campaign-wide restart has occurred.

A separate finite unarmed diagnostic accepted the identical 512-event workload
on the unchanged source/boot after available heap recovered from 107,488 to
131,216 bytes. It never called ARM, reconciled the loaded job through Console
ABORT, and verified ownership expiry/disabled recurrence/output inactivity.
Private diagnostic receipt SHA-256 is
`917dd9ddb350531c7442fc94fd6179b564a633858ede8bcb67d47e4520059cfc`.
The failed transport close reason is 4 (endpoint closure); source retains a
complete frame for at most five seconds when its existing 32 KiB decoder work
plus separate 32 KiB authority reserve cannot be admitted. Recovery after
retained control history ages is consistent with resource pressure, without
proving which individual allocations occupied every byte.

The host maximum-event path now waits up to 360 seconds before capture/CLAIM/LOAD
for the serialized request bytes plus those unchanged target reserves and 8 KiB
of connection/management margin. It continuously requires the same source,
boot and clock, no owner, disabled schedule and inactive output. The transport
is closed during the wait and negotiated afresh afterward; uncertain mutations
are never retried. Failure to recover stops the case before RF. This does not
change firmware, retention TTLs, event count, RF duration or acceptance screens.
All 24 affected portable checks pass, including actual failure/recovery heap
values and unchanged 512-event duration; syntax/diff checks pass. The first
sandboxed CTest attempt could not bind its localhost relay socket; the same
configured check passes with the required local-socket access.

The host-preflight repair is committed as `a11686b`; devel is 39 commits beyond
the starting remote with no push. Fresh immutable continuation
`build/resume-tools-a11686b-retry` has archive SHA-256
`e61c96d69efd0d25f8e8ff208030fbdd294a51b5d2a90c92e1d8e76a5cd34ae5`,
coordinator SHA-256
`419479ee555031f605c70d45a5edc1956e0d85ecd4f549723ad5c7757385d9ae`
and 1,794 verified extracted files. It requires the exact 25-complete/one-failed
predecessor, failed LOAD, physical quiet and unarmed diagnostic receipts, releases
only the identified unarmed diagnostic job with ordinary CLAIM/RELEASE, refreshes
the reference and resumes A's 512-event case followed by B's remaining cases,
soak, spectra and clocks. Its first private coordinator attempt stopped after
read-only inventory because setting child PYTHONPATH did not update its own
import path; it performed no RF. That failed startup remains retained, and the
separate retry explicitly initializes the current process path.

The separate action-aware A abort assessment passes. It binds one actual same-job
ABORT request between Running and Aborted observations, rehashes the complete IQ
and metadata, checks a single deliberately shortened burst and every captured
off sample beyond 20 ms edge exclusions, requires a healthy post-stop reference
and checks resources. Observed RF lasts 2.874 s rather than the requested 10 s;
the remaining 47.757 s of capture is quiet at least 54.546 dB below on. Detector
cadence is 1 ms; no absolute request-to-GPIO 100 ms latency claim is made.
The original full-duration duration/missing-segment failure is unchanged.
Receipt SHA-256 is
`6f35d88d0285e4d0ef003fddc9785e2b961e0b5cd04620d2986ef645b387c798`;
independent analysis script SHA-256 is
`722e2aa39e7c074802c6cb138d173ef53c49deb410cf1eef60d7d160b5a9fd5a`.
All 25 affected portable checks pass, including rejection of natural full
completion, extra bursts, two-millisecond RF tails, pre-launch RF, missing RF
and invalid samples. The first standalone invocation omitted the established
external Harness library path and stopped before analysis; its log is retained.
The retry with that path produces the bound assessment above. Firmware and
active campaign modules remain unchanged.

The first maximum-load preflight stopped after its finite 360-second wait,
without opening a receiver capture or submitting CLAIM/LOAD/ARM. Available heap
recovered to 125,400 bytes, below the initial 126,345-byte host estimate. That
preparation failure remains retained. Source accounting shows the parser's
8 KiB INFO allowance and the 32 KiB decode workspace are serialized; adding an
extra 8 KiB to both unchanged 32 KiB reserves was unnecessarily restrictive.
The host estimate retains the full request/header plus both 32 KiB reserves
and uses 4 KiB for connection/paged-allocation overhead (122,249 bytes for this
workload). Target admission remains authoritative; failure there still stops
without replaying LOAD. Firmware, frame capacity, cache TTLs and RF/resource
acceptance criteria are unchanged. All 25 affected tests pass, including the
observed failed, diagnostic-success and recovered-preflight heap states.

Fresh `dbf1f3e` continuation has resumed the unfinished cases from verified
archive SHA-256
`392a0df02dc6b753c6c4a51eebfa7e9b91b18467cfab39bfed31b05cf368e159`,
coordinator SHA-256
`6c70859cade85ca88673af045c86bc22d1f17eaf877b26a579a4ca56620230dd`
and 1,795 verified extracted files. It additionally binds the exact preflight-only
stop and previous diagnostic RELEASE, without repeating diagnostic mutations.
A's 512-event case now completes and passes the separate human-aware/resource
assessment. Its original strict machine screen fails and remains unchanged.
Receipt SHA-256 is
`89d4412cd39c40a2f2ac2768d8e1ae5a4d45281e6ace6bd2665a13a99c55dcaa`.
B cancellation also passes (54.691 dB below its matched live baseline, with
resources passing). B abort/disconnect/maximum-event cases are next; the soak remains
0/8 at this checkpoint. There is no firmware change and no push.

An independent source/raw/control/resource integrity audit passes all eight
closed producer captures (the four maximum-message cases, three native 160 m
WSPR captures and one three-frame USB-unavailable standalone capture). It
rehashes actual IQ and metadata, binds board/source/boot/image/reference, compares
resource reducers with raw INFO observations, and independently parses retained
relay headers/CRC and actual LOAD/ARM/completion messages. It keeps the original
waveform flags and does not promote release qualification. Private receipt
`build/producer-integrity-audit-dbf1f3e-retry/result.json` under the `c126bc5`
snapshot has SHA-256
`d7f3747c4d871b65b1676c8fb7a784d81be93933996ae382d4ed144657f4970b`;
independent audit script SHA-256 is
`393de03cb5f8d837a8d5e6926d74c7841e1782f5ab995c77458f94a013a9cbf7`.
The initial audit assumed nonexistent top-level relay digest fields and rejected
that schema. A separate corrected audit checks the actual transaction records
against framed raw wire bytes. An intermediate private-script indentation error
stopped before evidence access; its log is retained. The passing script is
syntax checked and separately identified above; source/captures did not change.

Current acceptance amendment, 2026-10-08: the operator explicitly stated that
QRSS, FSKCW and DFCW are intended for human copy and that having drift is not
an immediate failure. Earlier `OPERATIONAL_SCREEN_FAIL` labels in this record
are retained machine/phase diagnostics, not automatic human-mode rejections.
The plan now separates a human-copy assessment of marks, spaces, timing, locally
distinct frequency states and shutdown from phase/drift diagnostics. Resource,
identity/control and WSPR machine-decoding gates remain unchanged. Fresh
source-bound assessments and missing keyed repetitions are still required.

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
settings afterward. Later restoration review narrows the write to the original
16 KiB profile plus 8 KiB configuration, preserving the current 8 KiB no-repeat
cursor; see the checkpoint below. This does not reopen GP14 or LED/button qualification.
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

The repeated A 80 m WSPR triplet under that bound completes and passes all three
operational waveform/decoder screens. The band/keyed matrix continues; this is
one repeated screen row and remains release-unqualified pending the other gates.

Prepared power-only transport variant: deauthorize only the exact B USB device
at its live serial-bound sysfs path, keep USB power present, close owned CDC
handles, and run finite standalone slots using Wi-Fi NTP. Restore that same
device's host authorization and verify source/boot/final reservation/last job/
inactive output before restoring the disabled schedule. During deauthorization,
there are no fabricated running Console samples: control records use
`END_STATE_VERIFIED`, with complete independent IQ required to establish frame
count and behavior. This tests powered operation without host USB endpoints,
not an electrically disconnected cable or a hard power cycle. The existing hub
reports ganged power switching; no power switch or unrelated USB device is
changed by this variant. Fourteen rejection/relay/axis/USB restoration tests pass.

## QRSS failure investigation

The current A 80 m QRSS waveform has exact 3/9/3-second RF marks, 9-second
gaps, about 66.6 dB on/off contrast and minimum mark amplitude ratios above
0.998. Timing, continuity and quiet pass. Only the 9-second dash exceeds the
retained 0.15 rad constant-frequency/linear-phase screen: 0.165819 rad versus
0.038725 and 0.034114 rad for the dots. This is not a demonstrated CW keying
failure. Comparing this screen directly with WSPR's much shorter symbol-fit
windows or DFCW's three-second marks is not a like-for-like stability comparison.
FSKCW also retains RF through its low-frequency spaces, unlike QRSS's quiet gaps.

Independent 4,097-tap Kaiser-windowed sinc FIRs at 25 and 100 Hz, centered on the
observed carrier, reproduce the dash residual at 0.165838 rad. The simultaneous
GPSDO residual over that mark is only 0.006702 rad; paired common-reference phase
removal still leaves 0.159252 rad. Thus distant harmonic/reference leakage or
the original wider decimator does not explain this result. A quadratic phase
diagnostic estimates -0.008687 Hz/s, approximately -0.078 Hz over the mark, and
reduces unexplained phase RMS to 0.028775 rad. Increasing edge exclusions from
20 ms to 100 ms leaves 0.159477 rad; half/one-second exclusions give 0.129583/
0.096554 rad as the remaining interval shortens. These diagnostics support slow
carrier drift. Its physical cause remains an inference pending controlled Tone/
keying comparisons; no thermal attribution or new PASS is asserted.

The original screen is unchanged. The complete hashed IQ, diagnostic JSON and
exact diagnostic tool snapshot remain private. Its first launch needed SciPy,
which was unavailable; that failed analysis log is retained. The successful
independent FIR uses existing NumPy and installs nothing. An offline fixture
rejects a distant interfering carrier while retaining a known slow drift;
seven RF-analysis fixtures and fifteen portable Phase 14 checks pass. The wider
batch has also produced passing 2200 m QRSS screens, consistent with the need
to distinguish keying functionality from the chosen long-mark stability metric.

Prepared frequency-correction comparison: complete ordinary jobs at zero and
plus/minus 1,500 ppb requested compensation, using explicit per-job frequency
adjustment and simultaneous GPSDO reference. Positive means a fast oscillator
and lowers requested frequencies; event offsets/durations remain unchanged.
Ordinary engine correction remains zero, no persistent setting is introduced,
and no automatic Pico discipline is claimed. Original uncorrected qualification
rows stay separate from this finite correction experiment. Fifteen portable
checks verify compensation sign, changed job identity, bounded inputs and
unchanged elapsed-time requests. This physical comparison has not run yet.

Matched current-image A 80 m FSKCW captures contain a nine-second mark at the
same carrier and job offset (13 seconds) as the failed QRSS dash. Three marks
have linear-phase residuals of 0.075572, 0.071680 and 0.079716 rad. The preceding
nine seconds contain RF at the space frequency in FSKCW and RF off in QRSS.
This strengthens the evidence for a preceding-state effect; it does not prove
a thermal mechanism. A continuous-Tone comparison remains pending while the
shared receiver is occupied by the finite matrix batch.

Evidence-index review now requires matching analysis/physical board, band, mode,
clock, firmware/source, boot and job identities. Its baseline matrix excludes
intentional aborts, special workloads and nonzero engine/request compensation,
while retaining those observations separately. An optional exact firmware-source
selection prevents historical images from entering a current-candidate matrix.
A rejection fixture proves a substituted board cannot be indexed and that
compensation/abort experiments cannot promote baseline acceptance. Sixteen
portable Phase 14 checks and all 165 host groups pass (84.45 seconds for the
full host run). Release qualification remains false.

Further analysis review found that the coarse in-band spectral mask excluded
the nominal GPSDO frequency only. Receiver tuning offset can place its actual
peak outside that mask and falsely list the reference as the strongest other
component. New analysis records and masks the measured simultaneous reference
positions as well as the nominal position. A synthetic offset reference/known
spur fixture rejects that misattribution. This does not alter waveform acceptance
limits; original spectra remain retained, with corrected analysis saved separately.
The active batch's loaded tools remain untouched until it ends.

The CF32 reader already uses a memory map and the carrier mixer processes
bounded blocks. Its finite-sample check now also scans bounded blocks, avoiding
a roughly 900 MB temporary boolean array for a one-hour capture at 250 ksps.
An invalid sample just beyond a chunk boundary is rejected. This is preparation
for long-capture assessment; no endurance result follows from host tests.

The prepared keying comparison fixes three pairs of 35-second Tone/QRSS jobs
on A at 80 m/138 MHz, alternating pair order with 45 seconds of verified idle
before each job. It compares the same nine-second interval at job offset 13,
with 20 ms edge exclusions, common-reference phase removal and an independent
25 Hz FIR. No compensation is applied; original full-job flags are retained.
Temperature is unmeasured, so this comparison cannot by itself prove heating.

Endurance assessment is prepared before execution: require eight complete
3,600-second jobs, exact Tone/512-event FSKCW alternation, unchanged per-board
boots/source/image, independent full-capture analysis and inactive idle windows.
Each B job must have at least 300 successful browser requests spanning at least
3,500 seconds. Equivalent idle allocation compares the median of three samples
after the same 45-second wait; either sample spread or positive median growth
above 1,024 bytes fails the resource screen. RF screening and resource results
are separate fields and neither can promote release qualification. A leak and
an unstable idle fixture both fail; malformed sample counts/counters reject.
The prepared soak has not executed yet.

The corrected reference mask has now been applied independently to the retained
A 80 m QRSS capture using isolated tool snapshot `4003ce0`; the running batch's
files were not replaced. The reference-edge comparison bin at 3,530,123.499 Hz,
-35.633 dBc, is removed from the coarse spectral comparison. The strongest
remaining comparison bin is 3,570,132.043 Hz at -41.124 dBc with 7.629 Hz FFT
bin width. This is a relative peak-bin observation, not a resolved spur or
calibrated emission claim. The QRSS waveform disposition remains
`OPERATIONAL_SCREEN_FAIL`; the phase measurements and limits are unchanged.
The corrected analysis is a new immutable result beside the original.

Clock-loss preparation review moved NTP suppression from immediately after ARM
to the first observed same-job Running/active state. Suppressing during the
four-second arm lead could instead age an already nearly-stale observation
before launch, exercising launch refusal rather than running-job independence.
The finite running job is followed by the retained aged-clock ARM refusal,
owned-rule removal and recovery checks. The probe uses the same five-second
administration response bound. This workload remains unexecuted.

The operator's human-copy amendment now has a separate analyzer result. RF-on
interior continuity is recorded explicitly, and short frequency fits near
adjacent distinct marks assess state ordering without fitting all message drift
to a single offset. Original phase, state residual and transition-fit diagnostics
are retained. Eleven RF fixtures include smooth-drift examples that pass the
human-copy assessment while retaining their legacy failures; dropouts, extra RF,
collapsed states and substituted expected jumps still reject. Eighteen portable
checks and all ten affected host groups pass.

Native-producer analysis also requires same-job, same-boot natural completion
after the exact ARM response in the retained WTP byte stream. An empty successor
and process exit code alone cannot establish completion. Pre-ARM terminal
records, foreign jobs/boots, aborted/active terminals and contradictory later
terminals reject. The currently running legacy batch and waiting continuation
retain their exact old tool snapshots; new assessments are stored separately.

Isolated snapshot `14ee874` has now assessed the retained current-image A 80 m
QRSS capture and exact native FSKCW capture. Both pass human-copy timing/marks/
states and resources; the native stream independently contains same-job natural
Complete/inactive terminal evidence after ARM. Their original machine-screen
flags remain false. These are source-bound human-copy observations, not final
three-repetition release qualification. A finite adapter will assess retained
keyed captures and complete missing repetitions after the legacy matrix ends.

Prepared alternative-clock comparison uses the current repaired candidate on
both boards at 132 and 150 MHz. At each representable band point, a complete
Tone screen precedes one full WSPR/QRSS/FSKCW/DFCW screen. Failed or unresolved
Tone acquisition leaves dependent mode rows explicitly unresolved. Each clock/
board also runs a finite 128-second, 512-event workload, with HTTPS activity on
B, to repeat affected contention checks. Unsupported points receive no ARM.
The selected 138 MHz candidate is returned to both boards after successful
completion. These are comparison screens, not alternative-clock release
qualification; this prepared batch has not executed.

The endurance assessment now also records a separate human-aware FSKCW result
when the amended analyzer is used. Its legacy RF flags and resource/growth
assertions remain separate and unchanged. Alternate immutable assessment names
permit later method/source-bound review without overwriting the original result.

Prepared pending-cancellation workload first establishes one complete five-second
Tone/on baseline, then cancels a second same-source/clock/boot job while Armed
and observed inactive. Any Running/active observation rejects pending-cancel
classification. The complete receiver capture must remain at least 10 dB below
the live baseline through the 1 ms Hann detector, with a healthy simultaneous
GPSDO reference; shorter-transient and calibrated-UTC claims are excluded.
This supplements the separate active-job abort workload and has not run yet.

Execution checkpoint at 18:15 UTC: all 165 host groups pass after the amended
human-copy and cancellation changes (84.19 seconds). The original bounded
138 MHz matrix remains active; it has completed 49 of 104 board/band/mode rows.
Its legacy flags remain diagnostic inputs for keyed modes. An isolated finite
continuation using tool snapshot `b153d46` is waiting for the exact predecessor
process to exit. No continuation RF step has started at this checkpoint.
It is bounded to retained-capture human assessment/missing repetitions, matched
keying and compensation comparisons, repeated installed-controller and maximum
message jobs, standalone operation without host USB endpoints, clock loss,
pending cancellation/active abort/disconnect, maximum-event load, eight finite
one-hour jobs, spectral surveys and alternative-clock comparison. Each adapter
reverifies board availability and retains failed/partial results. The queue
stops on an unhandled failure; it does not imply qualification or completion.
Final candidate applicability/build/smoke, adversarial closeout, original B
profile restoration, commit/push and remote parity remain separate outstanding
work. Temporary queued versions were stopped while still waiting, without RF
steps or interruption of the active matrix; their records remain preserved.

Fresh candidate source `ffcb1bd3aeee70d8ba4047211f56578d858c9300` is built locally
with the same pinned SDK/toolchain/picotool inputs, version 0.1.0-rc.1 and RF
configuration. Its 132/138/150 MHz UF2 hashes are respectively
`6f66aaabd7d76cae27d0b829817979a8e3e2a2b6d39d51f2073d6f5f34958e0f`,
`aecf5d7da924f33b18a26737f27c27869741ec20838977930e2d844b16c2b81b` and
`914c60bfc3e994edeb91532125433e0317715bb483d13c8807f637f6104d78d6`.
A clean independent 138 MHz rebuild is byte-identical. Exact full-UF2 comparison
against the deployed `bd45bc1bb638` image at each clock finds only two copies of
the 12-character Git revision changed: 24 bytes in each complete UF2, with all
other bytes identical. The private comparison JSON records both artifact hashes.
This supports runtime evidence applicability beyond source-file assumptions;
it does not substitute for final both-board installation/smoke/cleanup. Current
physical batches retain their original deployed image and exact tool identities.

Further independent assessment of current-image Pico B 80 m QRSS and FSKCW also
passes human-copy marks/timing/states and resource screens while preserving the
original drift-related failures. FSKCW local changes measure approximately
5.01–5.02 Hz in the correct order. Neither observation supplies its still-missing
three-repetition release evidence.

Pre-execution spectral review found an attribution gap: Running was checked
before each separately tuned capture, but a job could finish during that capture.
The survey now requires the same active Running job/boot both before and after
every complete 500,000-sample capture. A stop, inactive state, foreign job or
restart rejects the attribution. The finite Tone window is increased from 120
to 240 seconds because 22 receiver initializations plus two-second captures leave
little margin at the observed helper overhead. This changes acquisition budget,
not spectral acceptance thresholds; no survey has run yet. Nineteen affected
portable rejection/relay tests pass, including both sides of the stop/restart
boundary. The active matrix's files and deployed firmware remain unchanged.

Additional preparation review tightened receiver integrity: a successful,
complete file must contain the exact positive integer requested sample count,
not just a size consistent with its retained count. Shortened requested-count
substitutions reject. Human-mode repetition analysis now retains a separately
hashed unresolved result and any partial analysis without retrying over it;
that row cannot pass, while independently verified inactive rows can continue.
A changed physical/capture binding rejects reuse of that unresolved result.
Twenty affected portable checks pass. The new tools are prepared locally; the
active matrix and waiting snapshot remain unchanged until a separate snapshot
is staged. Review also confirmed that long Tone measurements already fit
roughly half-second interior segments rather than one linear phase across the
whole hour. No Tone stability criterion was changed.

The isolated offline A reassessment is complete: all 69 retained current-image
QRSS/FSKCW/DFCW captures pass the human-copy and resource checks across the 13
representable band points. Their original flags remain retained. Missing
repetitions still have to run. The finite continuation now waits with reviewed
tool snapshot `f22a115`; its coordinator hash is
`2ad1e833e6b3d32a5532bd2f01789a432cfebd57c454b7dd1c752db773fea913`.
It includes the existing finite workloads plus one current-image Tone sweep on
both boards after the alternative-clock comparison/restarts. This directly
binds Tone/spectral observations to the repaired runtime; earlier sweeps predate
the launch repair. No continuation hardware step has started at this checkpoint.

Prepared matched close-in assessment uses the retained Pi benchmark's
0.238419 Hz Hann bins, measured-carrier centering, +/-120 Hz searches and an equal
trailing-off window. Source/boot/job/capture/analysis hashes are bound, >=10 dB
carrier on/off attribution is required, and the original waveform disposition
remains unchanged. Known -26.02/-30 dBc synthetic sidebands are recovered;
incomplete or reversed windows reject. All twelve RF-analysis fixtures pass.
The current-image Tone comparison has not executed yet. The inspectable private
80 m/6 m QRSS figure under `build/phase14-qrss-human-copy.png` and its hash manifest
show the requested three-second dots/nine-second dash; they retain nominal
receiver axes and do not substitute for repetition or absolute-frequency evidence.

Standard-environment review found that the new unresolved-analysis fixture
imported the optional Harness/scientific package at module load. The earlier
venv check masked this dependency. Moving that import to the actual IQ call
restores hardware-free independence; all 21 portable checks now pass with plain
Python, and both affected CTest groups pass under their configured interpreters.
The queued Linux snapshot already has its required analysis dependencies and
does not need this import-timing change to execute its RF measurements.

Pre-execution restart/restoration review also found two host-helper defects.
`Scheduler::last_job_` is an in-memory display and becomes empty after reboot;
the durable-settings comparison now excludes that display while still requiring
the persisted watermark and all other operator settings to match. Final B
restoration writes only the original 16 KiB profile and 8 KiB configuration at
`0x103f7000..0x103fcfff`. It preserves the current 8 KiB cursor at
`0x103fd000..0x103fefff`, rejects a cursor older than the original snapshot and
keeps recurrence disabled. A source-backed fixture accepts display reset but
rejects watermark rollback and proves the payload cannot include cursor bytes.
The saved 32 KiB original remains private evidence; it will not be loaded in
full for final restoration. Application/access/bond/E10 regions remain untouched.
These helper fixes are prepared locally; no device setting or active RF job was
changed by this review. A new isolated continuation snapshot is required before
the later clock-comparison restarts; the live matrix remains on its original tools.

The `efb545c` isolated continuation was staged with every archived file verified,
and its waiting coordinator hash is
`35eff91dd6a731b3a1d9d5b6ef3ed36550fba4e15f1ff9cc6b491a4aeebb4025`.
The predecessor remains unchanged. At the following live checkpoint, 76 of its
104 rows and 147 complete jobs were recorded. All 52 A rows were finished; B had
recorded 24 rows through 40 m. No continuation RF step had begun.

Further pre-execution review found an unrenewed final wait in the separately
tuned spectral survey. WTP preserves a running job after lease expiry, but then
releases ownership at its terminal state, making the subsequent owned RELEASE
fail. The survey now renews while awaiting natural completion and rejects wrong
boot/job identities, unexpected terminals and active completion. A virtual
120-second tail exceeds the original 60-second lease and verifies retained
ownership; bad-terminal and deadline cases reject. All 22 portable checks and
the affected configured CTest group pass. This changes only the host survey
helper. It requires a fresh waiting tool snapshot before that survey runs; no
active matrix tool or Pico firmware changed.

The full documented host check after that repair passes all 165 groups in
95.59 seconds. The repaired finite continuation waits on snapshot `e535ee2`,
coordinator SHA-256
`291c9bcc51dd4e9701d0e0248b74aeadcad33f19c0db4b84bef9c6e6685acf23`.
Its staged archive and every extracted source file were verified; all replaced
coordinators stopped while waiting with zero RF steps.

The retained Pi benchmark source specifies +/-5 Hz feature searches, whereas
the prepared new helper used +/-2 Hz. Before the first current-image matched
Tone acquisition, the new helper's feature searches were widened to +/-5 Hz;
this prevents a stronger displaced feature from being omitted. The FFT size,
benchmark ratios and on/off requirements stay unchanged. A stronger synthetic
-124 Hz feature is recovered at -20 dBc and therefore fails the retained lower
sideband benchmark; the existing -120/+120 Hz fixture remains applicable. The
comparison now explicitly distinguishes matched bins/search widths from its
different RF windows and dates. No earlier RF result or original flag changed.
All twelve affected RF-analysis fixtures pass after the search-width repair.

The unstarted separately tuned spectral survey now records GPSDO identity,
frequency/output/level settings and readiness before and after its on/off batch,
requiring unchanged readback. It does not tune or otherwise change the reference.
This supplies the per-result reference binding requested for those surveys;
ordinary IQ jobs already retain their simultaneous reference settings. Syntax
and diff checks pass; the live matrix and its tools remain unchanged.

Numeric progress checkpoint: the main current-image 138 MHz matrix has recorded
92/104 rows (88.5%); all 52 A rows are finished and B is through 15 m. These are
completed attempts, including original failures, rather than qualified support.
Three of the nine original workstreams are established: initial review, plan/
acceptance record and bench preparation. The other six remain open. All 165 host
groups pass, with the affected twelve RF-analysis fixtures subsequently passing
after the more conservative sideband search. Final board installation/smokes,
soak, surveys, alternative-clock mode comparison, final review and push remain.

The reviewed continuation uses immutable source snapshot `bd6c2c1` in private
`build/follow-on-tools-bd6c2c1-bracketed`, coordinator SHA-256
`c04d2c1b0428625016e872ab504e549e6621cef38f065a6f09769331cbddb7fa`.
The source archive SHA-256 is
`2e368c34feea968cbc475e2bad081e4d0cfad2ce9d86e62fc3c08d4056031d3a`;
every extracted source file was verified. Its zero-step waiting predecessor was
stopped by exact process identity without changing the active matrix. Three
additional finite GPSDO-only ABBA comparisons are queued before follow-on work
and immediately before/after the eight-hour soak, in addition to the final
post-comparison reference check. These bracket receiver sampling drift over the
actual long acquisition windows; they neither discipline the Pico nor alter
the frozen mode screens. No continuation RF step has begun at this checkpoint.

The primary 138 MHz batch is now complete: 104/104 rows and 174 finite complete
jobs (90 A, 84 B). Original dispositions remain 34 repeated legacy-screen passes
and 70 excluded legacy-screen rows. QRSS-family drift flags are subsequently
assessed separately under the operator amendment; these totals do not declare
release qualification. The guarded continuation completed inventory and its
preflight reference comparison, then began missing human-copy repetitions.

An independent standard-library audit rehashed every actual IQ file and capture
metadata, verified exact requested/retained counts, receiver identity/integrity,
board/source/clock/pin/engine bindings, submitted/accepted finite event sequences,
same-job/boot natural completion and inactive boundaries, analysis/tool hashes
and each matrix row's underlying results. All 174 captures and 104 rows pass
integrity binding. Private receipt `build/matrix-audit-9303d17/result.json` has
SHA-256 `dc5ad5857e501a0074a9863b3fd5b715a124e9fb7c554b145b785531e7b42a4d`;
its independent script SHA-256 is
`1ca86ee5f42d2567d916adf63c0b63411b9c550416e7491f9ff8d9efc724f859`.
Separate deployment comparison confirms all A/B captures share the respective
verified current-image boot (`340bb6e9548571b196528c07286e1d44` /
`ac148eba9e05ea4afa5a7ebc46cb0302`) and identified 138 MHz UF2 hash.

The post-matrix ABBA result estimates nominal-to-true sampling scale
`1.000001039854018`, actual rate `249999.7400367658` Hz and engineering
repeatability bound `0.3158151020136663` ppm. Its comparison SHA-256 is
`0defc22fae5910406b7a878fc510051c914dae20a481e15198a28ed4cebd5026`.
The center differs by about 0.062 ppm from the pre-RC1 comparison; the explicit
1 ppb reference assumption remains uncertified. Both reference comparisons were
applied separately to all 42 original WSPR reports, retaining 84 supplementary
derived-axis files beside immutable original analyses. Original waveform screens
and Pico correction remain unchanged. At the next repetition checkpoint,
13/78 human-copy rows (16.7%) have three passing observations, including A's
80 m QRSS/FSKCW/DFCW; four additional finite jobs have completed. Other release
gates remain open.

The independent audit's explicit declared-mode/submitted-job check exposed a
missing equivalent rejection in the shared physical-record validator. The host
validator now rejects a changed mode label even when the accepted job remains
unchanged. Existing lifecycle substitution tests include that case. This is a
metadata validation repair: every original capture already passed the stricter
independent mode binding, and the active immutable continuation is not modified.
Later evidence is subject to the same independent audit before release.

Review of the queued maximum-message cases found that 32 T characters in DFCW
exercise only its dash-frequency state. That is a valid length/resource workload,
but cannot establish the separate two-state human-copy assertion. The existing
queued case remains unchanged and its flags will be retained. The controller
helper now also accepts a 32-character alternating E/T message; an additional
finite DFCW case using that message is required before final closeout to exercise
both glyph-frequency roles at the maximum message length. The same three-second
dot, 32-character limit and finite capture bound apply. Syntax/help/diff checks
pass. No running or queued source file was overwritten by this local repair.

Offline B reassessment was pipelined with A's new RF repetitions after the
predecessor files were closed. All 63 retained B QRSS/FSKCW/DFCW captures pass
human-copy/resource checks, including the 6 m captures. Combined with A's 69,
132/132 retained family captures pass the amended assessment across both boards
and all 13 representable points. Their original legacy flags remain unchanged.
Private `build/offline-human-B/result.json` under the `bd6c2c1-bracketed` snapshot
has SHA-256 `9fd24fe8040bef446c738d3fb1000106c6e08d0052828793748b89e266917914`;
the offline script hash is
`8a4305cb2838da719796cb0107d977085bf9eb6e78905d41d683e43d39a637d3`.
The RF repetition stage reuses these immutable analyses; it has reached 31/78
three-observation rows (39.7%), all passing, while missing repetitions continue.
This is waveform/resource evidence under the human-copy method, not final
release qualification or a formal human listening study.
