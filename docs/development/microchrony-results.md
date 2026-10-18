# μChrony replacement results

Updated 2026-10-18. The original MIT [μChrony](../../src/microchrony/README.md)
engine replaces the previous NTP estimators. Its original validation was isolated
from concurrent installer and cleanup work. The normal
`WsprryPico.uf2` was loaded on B and subsequently authorized A; both receive NTP
and remain unowned, inactive and disabled for autonomous schedules. The finite
NTP-only comparison is complete. [Backlog item 4](consolidated-backlog.md#finish-now)
remains open for independent RF acceptance and the documented qualification limits.

The subsequent [normal-image A/B crossover](microchrony-live-comparison.md)
records the current deployed source, local-versus-pool convergence, verified
application of the clock rates and identical-input Chrony 4.9 replays. Its
evidence remains separate from the earlier image described below.

The [evidence manifest](microchrony-evidence.json) binds the exact sources,
reference executables, normal image and private originals. The original validation
used an isolated worktree detached from
`692e2d821b9aee195c969969cdbc1015338b00e2`. The operator authorized integration
into the primary `devel` checkout on 2026-10-18, retaining the USB installer and
documentation cleanup. Historical device evidence still applies only to its
recorded image and sources. A fresh Linux portable build, 13 focused CTest suites
and normal/inhibited firmware cross-builds pass for the combined source. The
[installer record](usb-installer-results.md#validation-so-far) lists the remaining
consolidation checks and their limits. Those integration checks did not load a
combined image; the subsequent crossover record covers the new deployment.

## Implementation and unchanged authority

The reusable C++20 module has fixed capacity: four sources, 64 original
measurements per source, no OS, Pico SDK, network, filesystem or heap dependency.
Its tested host engine occupies 30,400 bytes. Chrony source is neither copied,
translated nor linked into the firmware; unmodified Chrony 4.9 objects are used
only by private external reference executables.

One model handles packet correlation, source delay admission, weighted
regression, identifiable delay asymmetry with full joint covariance, residual
runs, source agreement, combination and separate frequency/phase correction.
Source preference accumulates quality scores with reselect distance. Only a
new selected-source fit or a changed reference steers the clock; repeated reads
never vote, create observations or refresh source age. Clock copies carry the
finite slew endpoint and subsequent pure frequency for local alarm conversion.

The tested phase rule uses correction time proportional to typical offset
error, update interval and `corrtimeratio`, with magnitude-dependent slew and
a one-second minimum correction duration. Noisy acquisition does not reject a
source merely because its unconstrained slope exceeds `maxdrift`; applied
frequency is clamped and its uncertainty includes the displacement. Rejected
packets cannot revive a withdrawn source or make a stale fit fresh.

The explicit Pico profile uses 64-second normal polls, ±100 ppm `maxdrift`,
50 ppm `maxclockerror`, `maxupdateskew 1000`, `maxslewrate 83333.333` and
`corrtimeratio 3`. A four-reply initial burst takes at most eight attempts.
There is no two-hour, 32-observation or half-window-center qualification gate.
The existing 500 ms/90-second timing admission and launch limits, controller
arbitration, manual PPM storage and independent physical RF gate remain intact.
A statistical rate candidate is not physical RF qualification. Neither board
was asked to transmit, claim an owner or execute a job.

Manual PPM and mode remain separate from the learning journal. Its 192-byte
version-2 record stores pure UTC frequency and skew, never transient phase slew;
version 1 loads with broad unknown skew. Restart seeds restore neither UTC nor
freshness. Host checks cover cold reconstruction, migration, torn updates and
write cooldown. B restored its saved −0.752 ppm UTC seed during the new image
boot before learning a new frequency. This replacement has not undergone a
physical USB power-removal cold-start test; the earlier image's cold test does
not qualify it. Complete histories use [bounded USB pages](ntp-usb-diagnostics.md).

## Software and external reference checks

The current [complete clock-loop comparison](microchrony-clock-loop.md)
adds known-truth source-to-clock feedback tests and records the subsequent
frequency-combination and history corrections. The isolated checks below
describe the earlier deployed image and retain their original scope.

The isolated host suite covered 193 checks: 192 passed initially; the recovery
web test passed after reusing already installed dependencies with an identical
lockfile. The original environment failure remains in the receipt. No package or
SDK was installed. The independent module build, normal Pico cross-link,
reserved-flash, RF engine, primary/core-1 stack and guard checks passed.

The final causal software receipt contains 307 exact rational
mapping cases and 14 traces. At a constant −20 ppm, median held-out error was
640 µs with offset-only updates, approximately 640 µs with phase damping alone,
and 1 ns with the learned-rate model. This is mathematical test evidence,
not achievable hardware accuracy. All admitted synthetic holdouts except the
deliberately lying-server case were covered by their reported bounds.

The official Chrony 4.9 release archive SHA-256 is
`4924c6f530105bcd5b9e9e33c48a2ae1bfd889222c8480bc41601110efc864d0`.
The [reproduction instructions](../../tests/reference/README.md) describe three
original drivers and their separate external executables. Reports bind the
current host engine binary; there is no stale pre-final-binary comparison claim.

Eight 64-point source-statistics streams passed the selected independent
criteria. Stationary frequency differences are below 1 ppb and skew differences
below 2 ppb; queue frequency differences are below 5 ppb. Both implementations
recover from the injected 40 ppm drift change within eight admitted points.
For correlated delay the maximum frequency difference is about 925 ppb, while
μChrony's complete joint covariance remains conservative. Adaptive history,
transient frequency and skew still differ, including approximately 10.48 ppm
maximum transient frequency difference in the drift-change case. No gate or
covariance bound was loosened to force a match.

All 160 tested phase-steering cases agree with the reference correction-time
rule and actual generic-driver clipping to within 0.000334 ppm. Five source
traces agree on final selected choices and the tested exact hysteresis switch;
two numerical scores agree within the documented 1% tolerance. Startup selected
choices differ at rows 5 in disagreement/hysteresis/withdrawal, rows 7–8 in
majority and rows 5–8 in stratum. These are not all-row selection equality or a
complete differential test of the daemon frequency-combination servo. The
reference loss trace uses the bounded reach-loss profile rather than the Unix
default association lifetime. The historical upstream unit run passed 16,
skipped nine and failed the Mac socket test; it was not a clean upstream suite.

## Normal firmware and finite target comparison

Both boards run `0.0.0-microchrony-r2`, revision `692e2d821b9a-dirty`, normal
`pio-dma-gp2` at 138 MHz. The single loaded UF2 SHA-256 is
`269b137c9d8e16a8c0fa29e1c776a578188222bc442f2ce5400d053e0d378d13`.
B serial is `CDDBF8767C506C07`; A serial is `0BF4B4AEC9FFB344`.
The manifest records their exact device and new boot identities.

Each serial-bound load saved a complete 4 MiB flash backup, verified the normal
image, and byte-compared all 72 KiB of reserved saved data before rebooting.
Both rejoined saved Bohica credentials. Full saved configuration, Wi-Fi value
and generation, manual PPM/mode, healthy storage and absence of pending restart
were checked after testing. Both manual settings remain `0.000`/`manual`.

The observer ran 886.3 seconds within its 900-second
plan and 930-second independent timeout. Query-delta ceilings were 96 for A and
32 for B, with a 32 MiB evidence cap. Actual collection used
20203063 bytes before final verification. Both observer and
timeout exited before the separate management verification took the USB locks.
The old overnight observer was not restarted. Raw evidence remains private on
wspr5 under `/home/pi/microchrony-validation-20261018` and in this worktree's
ignored `build/microchrony-validation-20261018/live` directory.

| Board | Configured source | Total queries / accepted | Final pure frequency | Final rate uncertainty | Synchronized INFO reads |
| --- | --- | ---: | ---: | ---: | ---: |
| A | `pool.ntp.org` | 68 / 68 | 0.411 ppm | 41.135 ppm | 66/67 |
| B | `time.local` | 18 / 18 | -4.042 ppm | 8.374 ppm | 67/67 |

These are results at the final observer read, not absolute oscillator-error
measurements. Uncertainty is not the applied correction. Initial acquisition
reads precede synchronization. Packet counts include the initial burst; normal
requests are 64 seconds apart plus bounded jitter. The manifest separates
whole-boot counts from the observer's query deltas. At the last observer read,
both RF candidates remained unqualified: B's 8.374 ppm and A's 41.135 ppm rate
bounds exceeded the 5 ppm statistical candidate threshold. UTC timing readiness
is assessed separately from that frequency threshold.

All accepted originals in the observer window are visible per source. The
analyzer verifies exact device/boot/image/revision, reconstructs each token SHA,
checks page cursor coverage, rejects changed originals and compares unique
records with per-slot accepted counters. Its next-observation holdouts use only
preceding input. Errors below are NTP consistency proxies and include future
network asymmetry, not independent UTC truth. Every row uses the same common
available holdouts across the three modes; each pool source is replayed alone,
so this does not recreate the target's combined pool model.

| Board/slot | Endpoint | Common holdouts | Offset-only median | Phase-only median | Learned-rate median | Rate wins / losses vs phase |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A/0 | `66.175.236.237` | 14 | 5.348 ms | 5.614 ms | 5.054 ms | 1 / 10 |
| A/1 | `23.139.196.53` | 14 | 7.748 ms | 5.438 ms | 5.466 ms | 5 / 6 |
| A/2 | `99.28.14.242` | 13 | 5.635 ms | 3.781 ms | 4.035 ms | 3 / 8 |
| A/3 | `199.180.255.17` | 14 | 11.283 ms | 7.234 ms | 10.146 ms | 4 / 6 |
| B/0 | `192.168.1.54` | 15 | 6.324 ms | 3.874 ms | 3.547 ms | 6 / 7 |

On B, learned rate reduced median proxy error from 3.874 to 3.547 ms, about
8.4%, across 15 common holdouts, with six individual wins and seven losses
(two ties). Pool medians improved on one source and worsened on three. This
short sample does not establish a repeatable benefit. Phase damping and
frequency learning must be assessed separately. Full per-source error, coverage, win/loss and availability
receipts are retained, including cases where learning performs worse.

The observer's INFO-only mapping pairs remain explicitly unbound numerical
consistency. After it exited, separate API → INFO → API reads required active
`sntp` authority, no disagreement, the observer's exact boots/images/revisions,
stable application generation, stable μChrony generation and matching applied
rates at both bracket endpoints. `sntp` is the retained API authority label for
μChrony, not another estimator. The application and μChrony counters have
separate domains. Each board supplied at least two bound points and a constant
segment whose actual UTC progression matched its applied rate within 3 µs.
These new receipts prove application only for their new bracketed intervals;
they do not retroactively certify earlier INFO reads.

Observed callback latency, stack, heap and timing readiness are in the manifest.
Every observed state retained the same boot, healthy allocation/storage and
stack guards, no owner, disabled schedules and inactive output. The test issued
no RF or job request. These finite observations
do not establish maximum-capacity regression latency or RF timing under load.

## Review and remaining limits

Independent read-only review found no firmware blocker for the finite test.
It identified source-acquisition reporting limits and offline-analysis gaps in
clock attribution, page bindings, signed root delay, exact post-observer boot
identity and final Wi-Fi metadata. Those findings were repaired and affected
checks rerun. The reviewer did not perform hardware operations.

Full Chrony daemon equivalence, all-row packet/selection/servo equivalence,
Chrony-equivalent leap execution, long-term thermal/network behavior, exhaustive
target latency, physical cold restoration of this replacement, independent
absolute UTC and physical RF calibration remain unqualified. GPS/PPS is outside
this NTP implementation. The boards continue ordinary background NTP with their
saved sources; finite evidence collection has ended, with both boards unowned
and schedules disabled.


## Direct Chrony comparison using captured observations

The offline follow-up feeds the same normalized timestamp, offset, delay and
root-dispersion streams from all saved originals through the external Chrony
4.9 SST API and the existing μChrony host statistics driver. A has four cohorts
of 17 originals; B has 18. Input hashes, executable hashes, scalar inputs and
every output row are in the private
`build/microchrony-validation-20261018/captured-source-comparison.json` receipt.
No board access, clock change or live collection was performed for this
comparison. The original MIT replay driver is
`tests/reference/replay_chrony49_capture.py`.

This is a source-estimator comparison. The μChrony host driver uses portable
defaults with packet delay admission disabled, reconstructs basic NTP packets
and applies its existing wire quantization. Chrony's SST driver takes scalar
measurements directly. Both receive the same normalized input rows, but this
is not identical full-packet processing or the complete Pico clock profile.
Remote positive root delay is charged to dispersion in both drivers. An
arbitrary common epoch removes irrelevant absolute epoch magnitude; elapsed
raw time and measured offset variation remain unchanged.

B's reported source-frequency uncertainty narrows as follows. These are
statistical source-fit bounds, not measured RF error or the board's applied
model bound. The first two observations have no frequency fit.

| Elapsed since first observation | Chrony 4.9 skew | μChrony skew |
| --- | ---: | ---: |
| 2.30 min | 508.813 ppm | 521.898 ppm |
| 4.45 min | 57.808 ppm | 58.222 ppm |
| 8.75 min | 28.101 ppm | 28.252 ppm |
| 15.23 min | 7.904 ppm | 7.836 ppm |

At the end of this trace, both remain above 5 ppm. This particular data does
not show that μChrony's estimator uniquely prevents reaching that target.
Startup raw fits differ much more: at three observations their reported skews
are approximately 29,302 ppm and 358,129 ppm. Those poorly constrained source
fits are not applied frequency corrections. Broad startup values must remain
visible rather than being hidden by a late-only comparison.

| Source | Chrony final frequency | μChrony final frequency | Chrony skew | μChrony skew |
| --- | ---: | ---: | ---: | ---: |
| A/0 | -0.767 ppm | -1.464 ppm | 20.783 ppm | 31.288 ppm |
| A/1 | -1.946 ppm | -1.466 ppm | 15.943 ppm | 16.339 ppm |
| A/2 | 2.138 ppm | 8.881 ppm | 23.244 ppm | 28.882 ppm |
| A/3 | -7.622 ppm | -7.042 ppm | 33.823 ppm | 33.493 ppm |
| B/0 | 2.662 ppm | 3.498 ppm | 7.904 ppm | 7.836 ppm |

Frequency uses Chrony's positive-fast convention. UTC rate correction has the
opposite sign. These source-fit values do not reproduce the separately blended
on-device applied frequency. A/2 is a material difference: 2.138 versus
8.881 ppm. Without independent frequency truth in this capture, neither result
can be declared more accurate. Weighting, asymmetry/covariance and history
selection differ; this follow-up does not isolate each contributor.

The controlled 40 ppm drift-change stream does have known truth. Chrony
recovers within 1 ppm and remains there after five changed observations;
μChrony needs seven. At 64-second spacing those are 320 and 448 seconds from
the last observation before the change. This exposes slower adaptation in
μChrony, rather than proving equivalence from a common final answer. The
correlated-delay fixture shows the reverse ranking at the final observation:
absolute frequency error is approximately 0.934 ppm for Chrony and 0.017 ppm
for μChrony. A single constructed fixture does not establish general superiority.

The reproducible gnuplot chart and scalar TSV inputs are private under
`build/microchrony-validation-20261018/comparison/`. The top-left panel contains
all available B source-fit skews; the top-right panel starts after one minute
to show later frequency estimates clearly. The bottom panels use known injected
truth. Their logarithmic error display floors values at 0.000001 ppm solely
for plotting. It is a mathematical fixture, not physical resolution.

### Boundaries that prevent a full equivalence claim

- These earlier SST and steering receipts do not compare closed-loop UTC
  convergence. The subsequent [known-truth clock-loop comparison](microchrony-clock-loop.md)
  exercises source-to-clock feedback in software; it does not qualify the
  earlier deployed image or a physical board's UTC or RF accuracy.
- History selection, sample weighting, learned asymmetry and covariance are
  separate implementations. The drift-change and pool replay reveal real
  differences. They are engineering gaps that can be tested and improved, not
  fundamental reasons a microcontroller cannot estimate frequency well.
- The source comparison bypasses Chrony's full packet-admission path and
  μChrony's delay admission. It does not establish identical rejection, polling,
  source-combination or recovery behavior. Five source traces establish final
  choices and a named hysteresis switch; startup choices still differ.
- Linux Chrony can use kernel or supported NIC hardware timestamps, avoiding
  processing and queue delays. Pico currently timestamps the UDP software
  callback after its Wi-Fi stack. Scalar replay cannot compare those acquisition
  paths, and filtering cannot identify every persistent path asymmetry.
- μChrony has four sources and 64 originals per source, a virtual UTC mapping
  and a small MCU integration. NTS, reference clocks/GPS/PPS, interleaved modes,
  Unix kernel control and demonstrated Chrony-equivalent leap execution are
  outside the implemented scope.
- The Pico's 5 ppm candidate/new-UTC-save checks and hard-coded independent RF
  inhibit are application policy outside the progressive UTC estimator. They
  are not evidence that Chrony itself requires 5 ppm before adjusting time.
  The comparison does not validate physical RF or cold-boot restoration.

The governing references are the official
[Chrony 4.9 configuration manual](https://chrony-project.org/doc/4.9/chrony.conf.html)
and [chronyc manual](https://chrony-project.org/doc/4.9/chronyc.html). The clock
process separates offset estimation, oscillator-frequency estimation, source
agreement and gradual phase removal; statistical readiness is assessed
separately from applying useful corrections.
