# GPIO timekeeping and calibration: executed evidence review

Recorded: 2026-10-09. Scope: research and documentation on `devel`.
Executed under the [retained prompt](gpio-time-calibration-research-prompt.md).
The [selected plan](gpio-time-calibration-plan.md) records the three stages and
conditional Si5351 deferral.
The later [review closure](gpio-time-calibration-review-closure.md) rechecks and
publishes the documentation; the original acquisition and findings below retain
their original evidence scope.

## Findings and decisions

Existing closed Phase 14 files are sufficient to observe UTC-anchor updates
without adding requests, RF jobs or duration to the running campaign. The
selected records show occasional roughly 200 ms clock-offset updates, even
with a local NTP server. They justify evaluating a bounded filtering prototype.
They do not demonstrate a scheduling failure, prove that filtering improves
absolute UTC accuracy, or qualify an automatic Pico frequency correction.

| Decision | Research disposition |
| --- | --- |
| Stage 1: NTP filtering | Prioritize an offline prototype using explicit accepted observations; compare jitter, uncertainty, freshness and launch availability before firmware implementation. |
| Stage 1: UTC rate discipline | Consider after filtering. This dataset cannot establish a stable rate or a benefit over the present offset-only mapping. |
| Stage 2: NTP-derived GPIO calibration | Retain as the next investigation. Do not apply the apparent PPM figures below; source provenance, uncertainty and independent RF agreement are insufficient. |
| Stage 3: GPS UTC + PPS | Retain as optional, inexpensive future input to the same estimator. Capture, UTC labelling and source transitions need separate evidence. |
| Si5351 | Conditional future addition depending on ongoing GPIO qualification; transmission and CLK2 feedback remain deferred. |

No firmware, product scripts, tests, configuration or hardware settings were
changed by this research. No Pico, SDR, GPSDO, serial port or control API was
accessed. Remote work comprised read-only evidence-file inspection and copying;
all calculations ran locally. The campaign retains its original dispositions.

## Dataset, identity and cutoff

The cohort is the original completed eight-hour soak, not the later browser
repeat. Its root on `wspr5` is:

```text
/home/pi/phase14-qualification-20261008/build/resume-tools-dbf1f3e/build/follow-on-eight-hour-soak
```

The summary has schema `phase14-soak/1`, `result=CONTROL_COMPLETE`, eight jobs,
eight post-release idle windows and `release_qualified=false`. All eight
physical records report control completion and an inactive terminal output.
CONTROL_COMPLETE describes acquisition/control completion; it is not release,
RF, browser-load or time-accuracy acceptance.

| Identity | Recorded value |
| --- | --- |
| Acquisition firmware source | `bd45bc1bb638839610f28ae529c97d51ec345f6d` |
| Acquisition UF2 SHA-256 | `5034a3fc2140deb7e5475ba0ff7043ada52c340c556401f8a24f6b11d264fa30` |
| Host tool source reference | `dbf1f3e52d553676629fc61b9a7082e77169f0d5`; selected snapshot path and campaign context, not executed-script hash attestation |
| Target/image | Pico 2 W / RP2350; `0.1.0-rc.1`; `pio-dma-gp2` |
| RF clock/output | 138,000,000 Hz nominal; divider 1; GP2; 80 m |
| Board A device / boot | `fd6127d11d6aca42a9905fa3fb1bf1d5` / `340bb6e9548571b196528c07286e1d44` |
| Board B device / boot | `29f20b7342051ef947aa56cb9d4fab42` / `ac148eba9e05ea4afa5a7ebc46cb0302` |
| RF compensation | Engine correction 0 ppb and requested frequency compensation 0 ppb throughout |
| Acquisition interval | 2026-10-09 03:01:16.593428 to 11:27:13.041703 UTC, from host summary |
| File-copy interval | 2026-10-09 12:27:34.021827 to 12:28:01.715461 UTC, from file-export manifest |
| Input size | 25 regular files; 187,925,869 bytes, approximately 179.22 MiB |

The acquisition spans 8.4323 hours including gaps. Each board has four one-hour
RF jobs; neither board has eight continuous RF hours. The files copied were the
summary and each job's `physical.json`, parent `events.jsonl` and
`idle-window.json`. Raw IQ, credentials and active/growing repeat logs were
excluded. Resolved paths were checked for substitution; size, modification
time and inode stayed unchanged during each read. All 25 copied SHA-256 values
were verified locally and again during independent validation.

The firmware revision, image hash and target identity are recorded by the
original acquisition chain and corroborated across its INFO/physical records.
This research did not read the UF2 itself or independently rehash deployed
flash. The host source reference is consistent with the event schema and soak
structure, but these 25 files do not record hashes of every executed host script.
Those provenance limits prevent claiming an independent binary/tool audit.

The copy took 27.69 seconds. It added no campaign step or RF duration and did
not change any campaign file. Ordinary file I/O consumes host resources;
these records do not certify literal zero interference with concurrent tests.
No ongoing-test completion gate depends on finishing this research.

| Job | Board | Mode / workload | Job ID | Existing INFO rows for target | Browser requests |
| --- | --- | --- | --- | ---: | ---: |
| 0 | A | TONE / normal | `bee9f9950362ac719664603e8625df4f` | 341 | None |
| 1 | B | TONE / browser | `e1632fa38042ee9cc8c60035721f8fe7` | 297 | 291 |
| 2 | A | FSKCW / maximum events | `99599da98a8356f6d3609081ddfb9bbd` | 344 | None |
| 3 | B | FSKCW / maximum events + browser | `17b727b989dc3ec285f34ddc518f104d` | 297 | 290 |
| 4 | A | TONE / normal | `b7c8b15856a6a5687cc5c7aba97cb2f0` | 343 | None |
| 5 | B | TONE / browser | `41bc86aef198c65efb10bab8f81c43b2` | 297 | 291 |
| 6 | A | FSKCW / maximum events | `b40c21074faf6778789d83b0d29562ad` | 345 | None |
| 7 | B | FSKCW / maximum events + browser | `572bd100a248e3746904c5579762066c` | 299 | 292 |

Each TONE job contains one accepted event, each FSKCW job 512, with a
3,600-second total duration. All four original B windows remain below their
original 300-browser-request threshold. Their subsequent repeats are outside
this intake. Timing diagnostics remain usable without converting those failures
into passes.

## What the acquisition firmware implements

This is a project-owned restricted unicast SNTP v4 client using lwIP UDP/DNS.
It validates peer IPv4/UDP 123, packet structure, originate nonce, timing,
stratum, leap indication, precision and root-distance fields. It uses one peer
at a time. The configured time server may be a literal IPv4 address or hostname;
the default is `pool.ntp.org`. After network initialization, enabled station
operation, an up link and a usable resolved peer, the next due poll sends the
first request. Failed connection/lookup/exchange paths retry or back off.

An accepted observation normally schedules the next poll 64 seconds later.
Unsuccessful attempts use two 2-second retries followed by a 64-second backoff.
A DNS peer change cancels an outstanding request and resets the poll schedule;
64 seconds is therefore not an invariant spacing across peer changes. A
correlated response must arrive within one second to be accepted. KoD stops
that server for the boot; unsupported leap indications invalidate the SNTP
source. Queries include attempts, and reject counters do not count every lost,
unsent or uncorrelated request.

The receive-time UTC estimate is server transmit UTC plus half the local RTT
after subtracting server processing time. Uncertainty includes the **full**
local RTT, half root delay, root dispersion and 1.050999 ms of margin. The UTC
offset is floored to the timer's microsecond grid. The 500 ms ceiling rejects
over-budget observations. Source arbitration additionally checks overlapping
uncertainty intervals and handles source disagreement/recovery. These guards
are implemented; a multi-sample delay/jitter filter and rate estimator are not.

`UtcDiscipline` stores an accepted UTC/monotonic anchor and projects UTC by raw
elapsed monotonic time. Despite its name it implements offset replacement,
not a fitted rate, oscillator trimming or clock slewing. The adapter uses
`time_us_64()*1000`. Snapshot uncertainty grows at an assumed 50 ppm. The
standalone profile stays synchronized through 90 seconds and in holdover
through 180 seconds, but new launches have a 90-second source-age limit and
500 ms uncertainty ceiling. Neither the assumed drift allowance nor a saved
manual frequency estimate supplies UTC after boot.

The scheduler consumes the shared clock through JobService. Alarm conversion
uses the current UTC-to-monotonic offset, and the local RF engine validates
launch conditions. Clock updates before launch may affect the alarm mapping.
A running job advances its locally prepared waveform using PIO/DMA; a new UTC
anchor does not change its carrier increments or symbol sample counts. Other
stop/failure protections continue to apply. Source inspection and these
snapshots do not independently measure RF onset relative to UTC.

No NTP-derived RF correction exists. The bench correction is volatile,
bounded to ±100 ppm and affects carrier NCO increments. Duration/sample-count
conversion still uses the nominal sample rate. Persistent standalone manual
correction remains proposed. No GPS/PPS observation source or allocated timing
input role is implemented. GPIO eligibility alone does not establish a working
PPS capture path. Si5351 transmission remains unimplemented and deferred.

## Reconstruction and data quality

The event envelope is `kind, utc_ns, monotonic_ns, value`. A canonical INFO
record has `kind=info` and `value={board, info}`. The 365,335 events include
2,579 canonical INFO records. Sixteen observe the inactive counterpart at
preflight; 2,563 observe the target board. INFO's device clock fields are used
for reconstruction; host event clocks describe collection timing only.

For each valid coherent snapshot, with raw monotonic `m`, projected UTC `u`
and sync age `a`, integer nanosecond arithmetic gives:

```text
anchor_m = m - a
anchor_u = u - a
offset   = u - m
base_uncertainty = reported_uncertainty - ceil(a * 50,000 / 1,000,000,000)
```

The last expression removes the firmware's assumed growth; it does not
estimate actual oscillator stability. Anchors are deduplicated by board,
boot, image, nominal clock and anchor monotonic timestamp. All observed
identities match the summary; no malformed JSON, backward host event clocks,
counter reset, invalid clock fields or conflicting UTC at one anchor were
found. All target snapshots report synchronized state.

**Time-source labels are missing from this INFO schema.** Its NTP counters and
server diagnostics support an SNTP-related interpretation, but cannot prove
that every anchor was supplied by SNTP. Source partitioning is consequently
unresolved; the pooled apparent-rate fits below are not SNTP-only calibration.
Source disagreement/recovery is not measured by these records.

INFO assembles network diagnostics before the scheduler clock snapshot. Two
A responses show a new anchor without an advanced accepted counter, followed
by a response advancing the counter without another anchor. Their extracted
base uncertainty also differs from the earlier network field. This is consistent
with the acquisition ordering; those responses cannot be treated as atomic
per-exchange records. An additional four transitions per board span more than
one accepted exchange. Intermediate observations are unavailable.

Latest RTT/sample uncertainty can also describe a rejected response. Only
238 A and 226 B within-job transitions have one accepted-count increment,
no reject increment, a changed anchor and matching base/latest uncertainty.
The clock-update statistics below use that restricted set. It provides a
consistent association, not proof of exclusive time-source provenance.

The 24 entries in the eight idle JSON lists exactly duplicate existing INFO
events. They were verified, not added as independent observations. Each list
contains three samples collected after the runner's original 45-second
post-release wait. Idle coverage is sparse and unsuitable for estimating a
load-caused change in clock quality. The board's server, provisioning profile,
browser workload and observation cadence differ; A-versus-B is not a controlled
comparison of network type or board performance.

## Observed timing diagnostics

Percentiles use linear interpolation at index `(n-1)*p`. Age, uncertainty and
RTT distributions are weighted by INFO snapshots, which repeat observations;
they are not per-NTP-exchange distributions. None is measured absolute UTC
error. Counter deltas below sum first-to-last snapshots within the four jobs,
excluding unobserved inter-job intervals.

| Quantity | Board A | Board B |
| --- | ---: | ---: |
| Target INFO / Running INFO | 1,373 / 1,342 | 1,190 / 1,158 |
| Distinct reconstructed anchors | 249 | 234 |
| Running collection cadence: median / maximum | 10.682 / 11.503 s | 12.371 / 14.759 s |
| Source age: median / p95 / maximum | 29.915 / 58.778 / 64.118 s | 31.792 / 60.472 / 63.821 s |
| Reported uncertainty: median / p95 / maximum | 111.790 / 265.910 / 485.511 ms | 18.368 / 164.031 / 494.285 ms |
| Latest RTT: median / p95 / maximum | 87.925 / 227.812 / 470.778 ms | 15.683 / 160.576 / 490.364 ms |
| Within-job accepted / rejected / queries deltas | 252 / 1 / 253 | 236 / 0 / 236 |
| Largest arm-record uncertainty | 170.246 ms | 56.257 ms |
| Restricted single-accept clock updates | 238 | 226 |
| Absolute restricted offset update: median / p95 | 9.427 / 65.030 ms | 8.268 / 83.944 ms |
| Largest absolute restricted offset update | 201.404 ms | 205.551 ms |
| Distinct reported NTP peer addresses | 93 | 1 |

A was configured to use `pool.ntp.org`; B used one local IPv4 time server.
The server's upstream state and absolute accuracy were not read or independently
qualified. All observed age/uncertainty snapshots stayed within 90 seconds and
500 ms. That shows reported availability at those snapshots, not continuous
availability or accuracy between them. Sampling can miss short failures.

The roughly 200 ms changes show that accepted offset replacement can introduce
substantial UTC jitter. Existing guards still admitted these observations.
They support investigating observation selection; they do not prove RF
frequency drift or require changing the existing launch limits. Even the local
server path had a large RTT tail. Assigning that tail to RF load, temperature,
Wi-Fi, server behavior or a specific firmware defect requires further evidence.

## Apparent rate: diagnostic only

For raw monotonic delta `dm` and reference UTC delta `du`, the apparent Pico
rate error is `(dm/du - 1)*1e6`. Positive values mean the raw timer appears fast.
The independent validation uses exact rational arithmetic for direct UTC-on-
monotonic regression; the primary method regresses offset after subtracting
the first anchor. No epoch-scale floating-point regression is used.

| Cohort | Anchors / span | Apparent OLS error | Apparent endpoint error |
| --- | --- | ---: | ---: |
| A across its four windows | 249 / 26,532.329 s | +0.908 ppm | +0.737 ppm |
| B across its four windows | 234 / 26,514.952 s | -0.735 ppm | -0.421 ppm |
| A job 0 / 2 / 4 / 6 | Individual windows | -2.945 / +2.162 / +0.252 / +0.201 ppm | -2.578 / +0.964 / +2.743 / +3.076 ppm |
| B job 1 / 3 / 5 / 7 | Individual windows | -1.697 / +0.617 / -3.852 / +2.645 ppm | -1.536 / -0.297 / -3.226 / +1.150 ppm |

Each individual fit covers approximately 3,778-3,786 seconds including
preflight and post-release observations. The long fits bridge inter-job gaps,
during which clocks continued updating without this board being regularly
observed. Their span is about 7.37 hours; neither is a continuous observation
or a homogeneous-source controlled calibration. Peer changes can change
reference bias, and no temperature history is available.

Signs and magnitudes vary between windows and endpoints. Absolute OLS residuals
reach 187.852 ms for A and 208.317 ms for B; their p95 values are 28.240 and
47.358 ms. A good long-span slope does not eliminate delay/asymmetry error.

An endpoint timing-error budget illustrates the limitation. First/last extracted
base uncertainties total 261.299 ms for A and 20.887 ms for B. Dividing these
sums by reference elapsed time gives uncertainty-equivalent scales of 9.848 ppm
and 0.788 ppm, respectively. These use the firmware's reported bounds, assume
they bound actual endpoint UTC error, and are **not** independently established
oscillator uncertainty, OLS confidence intervals or transferable RF bounds.
Using exact `dm/(du±E)-1`, where `E` is the summed endpoint budget, gives
model-conditioned endpoint ranges of **[-9.112, +10.585] ppm** for A and
**[-1.209, +0.367] ppm** for B. Both include zero. They apply to the endpoint
estimator only and cease to be bounds if the reported UTC budgets are not valid.
Even 100 ms of endpoint error over eight hours produces about 3.47 ppm of
apparent rate error.

No matching independently calibrated RF analysis was imported. Physical records
identify the conducted receiver/reference path and hashes of retained captures,
but this research neither copied IQ nor validated those capture bytes or
measured carrier/symbol error. A recorded GPSDO reference with PPS disabled
does not supply Pico PPS observations. The apparent fits must not be entered
as a correction or used to qualify a band or WSPR decoding.

## Prioritized follow-up design

1. **Stage 1, observation quality:** Preserve packet/nonce/leap/source guards.
   Evaluate a small bounded delay-aware observation window, outlier handling
   and propagated uncertainty. Compare the current mapping against filtering
   and then filtering plus rate discipline. Metrics must include absolute UTC
   error when a qualified reference is available, offset jitter, rejection/
   recovery, startup time and launch availability. A smoother trace alone is
   insufficient. Selecting an older sample must preserve its actual age and
   grow its uncertainty; do not renew source freshness by re-emitting it.
2. **Stage 1, clock mapping:** If evidence supports rate discipline, retain the
   raw monotonic timer and implement a bounded mapping `UTC=U0+r*(m-m0)` with
   the corresponding inverse for alarm conversion. Update arbitration's
   propagated intervals and launch uncertainty consistently. Cover source
   disagreement, stale data, backward offset changes, bootstrap, outage,
   reacquisition, leap handling and representable timer rounding. Retain the
   500 ms/90-second launch policy until separately justified.
3. **Stage 2, estimator and RF application:** Fit from raw accepted reference
   observations before software UTC discipline to avoid circular calibration.
   Require explicit source/peer/boot/clock provenance, timer-to-PIO clock-path
   verification, stable disjoint-window results, a defensible uncertainty bound
   and independent conducted RF agreement on the exact image. Select one
   calibration authority to avoid double correction. Preserve manual fallback
   and freeze the selected correction for each prepared/running job. Correcting
   carrier increments and correcting symbol sample counts require separate
   design/acceptance decisions. Saved estimates need identity, age and validity;
   they cannot establish UTC or authorize longer holdover on their own.
4. **Stage 3, optional GPS/PPS:** A low-cost GNSS module supplying UTC messages
   plus a 3.3 V-compatible PPS input is the proposed hardware addition. Reserve
   UART/input pins and capture peripherals through exclusive allocation; do
   not choose pins merely because they are exposed. Establish which UTC second
   each pulse labels, GNSS validity/leap state, capture latency/quantization,
   missing/extra pulses and source disagreement. Use the same estimator and
   bounded holdover policy. No GPSDO, external counter IC or precision oscillator
   is required by this plan. Module choice and expected accuracy remain open.

Future telemetry should retain accepted receive-monotonic and reference UTC,
raw RTT/server fields, observation ID/source/peer, acceptance reason, boot and
clock configuration. A separate bounded implementation/test slice is needed
to obtain that richer evidence. This research adds none of those requests or
fields to the ongoing campaign. Si5351/CLK2 work is outside all four follow-ups.

## Reproduction and source references

The private, ignored local companion is
`build/gpio-time-research-20261009/`. It contains the exact inputs, transfer
manifest, acquisition-source extracts, `analysis.json`, sanitized validation
summary, per-snapshot calculations and executable analysis/validation methods.
The notebook is a convenience runner over the same retained methods.

```sh
python3 build/gpio-time-research-20261009/analyze.py build/gpio-time-research-20261009
python3 build/gpio-time-research-20261009/validate.py build/gpio-time-research-20261009
```

These run locally and require only Python's standard library. They do not
access the bench. The companion is retained on this workstation, not committed
or portable with a fresh clone; the intake manifest below identifies the
original files and byte hashes for recovery. Do not replace input files with
later campaign results. Recover source through the recorded Git revisions.
The later [method appendix](gpio-time-calibration-research-methods.md) preserves
the exact method text in Git, with a
[sanitized analysis-input manifest](gpio-time-calibration-intake-manifest.json).
Private raw files are still required; they are not supplied by the repository.

Retained method hashes identify the calculations reviewed in this execution:

| Method | SHA-256 |
| --- | --- |
| `analyze.py` | `5ad0812cdcf599a9332fccb7ed1f8752ad03ab38489319500f849b2d10ff937d` |
| `validate.py` | `da62e9876f288085e79b3303ea07c217f23b8c5eb0d964146c9dbb9ea9b3186e` |
| Executed `reproduce.ipynb` | `d574b121581dde47e55d7e8adea4f66bd5a703dcb630ec222dc7a3c78c897443` |

Relevant acquisition firmware source references (line numbers checked against
`bd45bc1bb638`; the reviewed time/adapter/scheduler source matches the current
checkout at review):

- `src/time/sntp.cpp:20-79`: request/receive validation, UTC estimate and uncertainty.
- `src/time/sntp.hpp:12-47`: polling/retry schedule.
- `src/time/utc_discipline.cpp:23-92` and `.hpp:8-14`: offset mapping and assumed drift growth.
- `src/time/controller_time.cpp:214-270`: source precedence, overlap, disagreement/recovery.
- `src/standalone/pico/adapters.cpp:491-527, 565-629`: peer resolution, counters and polling.
- `src/standalone/pico/main.cpp:216-218, 812-827, 1249-1257`: monotonic timer and INFO acquisition order.
- `src/standalone/wtp_profile.hpp:7-18`: 90/180-second clock profile and 500 ms/90-second launch gates.
- `src/standalone/scheduler.cpp:70-139, 143-169`: occurrence admission and coherent clock fields.
- `src/wtp/job_service.cpp:572-708, 812-863`: local job lifecycle and launch conversion.
- `src/rf/stream_engine.cpp:36-90, 92-100`: armed-clock reprojection and bench correction.
- `src/rf/waveform.cpp:9-24, 87-115`: nominal sample counts versus corrected carrier increments.
- `src/rf/waveform.hpp:58`: correction limit of 100,000 ppb.
- `src/time/observation.hpp:10` and [pin contract](../pin-assignment-contract.md): implemented sources/roles lack GPS/PPS.

Host source at `dbf1f3e`: `src/phase14/live.py:28-60, 155-171` records INFO and
physical identity; `scripts/phase14_soak.py:26-53` selects jobs and existing idle
sampling. The analysis never invokes these hardware-control modules.
[RFC 5905, sections 10-12](https://www.rfc-editor.org/rfc/rfc5905.html) supplies
filter/discipline design context, without implying that full NTP is implemented.

## Adversarial assessment

The first assessment challenged the draft against raw files, source and an
independent calculation, rather than accepting a plausible clock narrative.

| Finding | Repair / disposition |
| --- | --- |
| A host snapshot path does not attest executed script bytes; recorded UF2 identity is not a fresh flash hash. | Relabelled tool provenance and explicitly bounded the firmware/image association. No binary/tool qualification claimed. Closed. |
| Timing uncertainty expressed as PPM could be mistaken for an OLS confidence interval or a calibrated oscillator bound. | Added exact model-conditioned endpoint ranges, both including zero, and identified the estimator and assumptions. Closed. |
| The prompt's general script/build prohibition could conflict with the authorized ignored analysis companion. | Restricted the prohibition to maintained product scripts/build definitions and retained local methods as research evidence. Closed. |
| An armed-clock source reference pointed to later engine progress handling rather than its reprojection function. | Corrected the reference to `StreamEngine::project_clock`, lines 36-90; added the carrier-correction limit reference. Closed. |

Preparation checks also identified and accounted for duplicated idle records,
non-atomic INFO diagnostics, missing source labels, inter-job gaps, different
server/workload cohorts and ordinary transfer I/O. None is repaired by inventing
samples or upgrading an original failed assessment.

The second assessment passed the numerical and documentation checks, then found
one remaining scope ambiguity: the Si5351 backlog still assigned its eventual
qualification to Phase 14 without distinguishing the active PIO campaign.
That sentence was corrected to retain its historical assignment and require a
separately selected future Si5351 scope. Closed.

The final assessment reran the affected checks after repair. No actionable
research/documentation defect remained within this scope. Validation confirmed:

- 25 input hashes and byte sizes; 365,335 raw events; identities, job durations,
  event counts, terminal output state and the 24 duplicated idle entries.
- Independent exact-rational endpoint and OLS rates, uncertainty/age/RTT
  percentiles, offset-update statistics and long-fit residuals; the notebook
  rerun completed locally.
- 255 local documentation links, seven anchors, 14 source-line references and
  all 25 published intake rows; reviewed firmware sources match the recorded
  Git revision across 14 retained files.
- No private SSID values in the six documents, no staged files, ignored local
  companion storage and clean documentation whitespace.

The unresolved measurement/provenance limitations above remain explicit;
they do not justify automatic calibration, longer holdover or release acceptance.
No source unit tests, firmware builds or new hardware qualification were run.

Historical repository state at the original research closure, before the later
[publication follow-up](gpio-time-calibration-review-closure.md): `devel`, HEAD
`42d1c80874de65755dccf54025a3fe1ff26ee64d`, 51 commits ahead of the locally
recorded `origin/devel`. The shared checkout advanced concurrently from the
research-start snapshot `8141cca627bab2c5632bd43848b5a6689703d30a`; this task
created no commit. Its three new documents and three existing-document edits
are unstaged/uncommitted. The pre-existing untracked `tests/hardware/si5351-i2c/`
directory is preserved. Concurrent Phase 14 source/helper commits are outside
this research; the current tracked working diff contains documentation only.

## Exact input inventory

Paths below are relative to the remote cohort root. This is a byte-preservation
inventory, not evidence that IQ or absolute timing was qualified.

| Relative file | Bytes | SHA-256 |
| --- | ---: | --- |
| `result.json` | 7447 | `121fa02ca9ea3cb6fe019fb85dbba1f038540b8d861dd03ca0a1713445054501` |
| `0/0-A-138000000-80m-TONE/physical.json` | 4989838 | `064174da8905585fafd9ad38abebbb7800a8e1a205f0836429f06cf1d159ef75` |
| `0/events.jsonl` | 23598804 | `a89dd9c984d81275871c8bb5d4cb8612a0cf4f4901c68259b7f16df895fe6ca4` |
| `0/idle-window.json` | 35664 | `4491a812ca8bcdf9439954594a4a80c56f98925b4698e638af1b8a8287ec83ae` |
| `1/1-B-138000000-80m-TONE/physical.json` | 3016685 | `888b0720385b7b6bf91345fbf1649be1fedd3c675c9092917177c5492486ed36` |
| `1/events.jsonl` | 19166892 | `acae11c9e0cf974adb4ddc3b5f9fb769dff80e68ee8b74a9db9a37b8dc9d4b50` |
| `1/idle-window.json` | 34197 | `1117bf40d8d5a5df026cca400b85e6cd196473ce72513729ecbad4dc37fcd057` |
| `2/2-A-138000000-80m-FSKCW/physical.json` | 2509990 | `4c227374f71b73ef4051f497c5f07334bda9851fbef4bcc52a5b534b2750c3ba` |
| `2/events.jsonl` | 20753299 | `6bc718432d62728f54eaa943e2a5e2ccf16a98ece389b707aa74669657d6a081` |
| `2/idle-window.json` | 35667 | `988b676c5684b38a9d912eb772c33b8ba84a4a0f0847c2035a865f93ba81fd5f` |
| `3/3-B-138000000-80m-FSKCW/physical.json` | 3246344 | `369da6008772de7def76252ca1d405c0fe739c0650c6486507346d00869ddbbd` |
| `3/events.jsonl` | 19417796 | `e3dda64b92e85a6d9284b1baa247962480d458e32ef5a07f2e6c3c3809a5341c` |
| `3/idle-window.json` | 34203 | `cc83665e3aa92f38cb05b1cfa2ad9308c4c454cbcebf7b5ad4886d787d183d34` |
| `4/4-A-138000000-80m-TONE/physical.json` | 2270653 | `6d0cebfebc42b9e5188a2c7a7bcc95c9629088ac1ebe5db06b512825a576c095` |
| `4/events.jsonl` | 20474699 | `7ce7b43f43c07520021bb72b29f2a47575a3bfdd42062a3e87fc2851f78f0161` |
| `4/idle-window.json` | 35671 | `b5e489f8b2ae591a5c8e53a7b0ec298f19f192b481339ae222bf2726890d40ea` |
| `5/5-B-138000000-80m-TONE/physical.json` | 3013400 | `6a9c9a7056e9108af4c9de50a84d81a389ba81240404663629212bb2cce8279a` |
| `5/events.jsonl` | 19155291 | `30575b2236aed7bce28f69077bce9a8345fbb407d701e161b83dc4834811718a` |
| `5/idle-window.json` | 34218 | `e4ca5c4fcaf8595012a6675c1ba9360b93b6e12ce78a41f8ad40decc73043c18` |
| `6/6-A-138000000-80m-FSKCW/physical.json` | 2492605 | `e165fad685f02e1e350167929e68ec02531525fe56c8820ce14710de4a4d09a9` |
| `6/events.jsonl` | 20723291 | `756b9f0f322f0d5ce831e942cd6da80969c9954bc2d643b43b969aeeec8d7b55` |
| `6/idle-window.json` | 35667 | `c94280e1670f1b965c520734cf5c597be1d8a041d1daa72aacf489a0646e0442` |
| `7/7-B-138000000-80m-FSKCW/physical.json` | 3266976 | `56640c6e4d122052ecf6d6d46f658ea8a107f1461e7b333319eb2a3984486643` |
| `7/events.jsonl` | 19542348 | `bbf985cb2ac82cacc24a85999998a1f334f6ecc0c975c896e7bf9c79d585d0ef` |
| `7/idle-window.json` | 34224 | `c89fcd6455d780f35cdb1db15fa76479d9aeb062807348e017e7c4f74e758b5a` |
