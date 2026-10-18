# Overnight NTP comparison

The user authorized this run after B passed one physical cold start and three
fresh post-cold NTP observations. It extends the completed original experiment's
collection budget. The [retention report](ntp-retained-results.md) records the
cold-start evidence and the limits of the early error comparison.

The overnight run **stopped early** on a diagnostic pagination error. The
observer and its guard exited at 2026-10-18 01:53:49 UTC, after 2089.55 seconds
(34 minutes 49.55 seconds). The planned overnight interval was not completed.
The run was not restarted. Both boards use the same normal
`0.0.0-ntp-retained-r4` image, revision `582b7221b785-dirty`, at 138 MHz with
`pio-dma-gp2`. UF2 SHA-256:
`80ce14d21b1db966acfc9c726cf0dc5d16dfb8fa742bcc4ca613f2858e7f2408`.

| Board | USB serial | Boot | Configured server |
| --- | --- | --- | --- |
| A | `0BF4B4AEC9FFB344` | `209968718134f4efc5a0deacc90bb7ba` | `pool.ntp.org` |
| B | `CDDBF8767C506C07` | `607918f8ee0acde8db20ca5309b33142` | `time.local` |

A's load preserved its final 72 KiB of saved storage. Its saved time-server
setting changed to `pool.ntp.org`; unrelated settings and manual calibration
were verified unchanged. A received pool time before observation began.
B retains its verified cold boot and local server. Both remain unowned and
inactive, with schedules disabled, manual `0.000`/manual mode and 4 mA drive.
No RF jobs are started by this experiment.

The private logger ran on `wspr5` independently of the Mac. Its planned hard deadline
was 2026-10-18 12:00 UTC, **07:00 America/Chicago**, with a two-minute stop margin
for final reads and an independent process guard. The maximum duration is
twelve hours, the allowed query-delta cap was 800 per board, and evidence was
bounded to 256 MiB. Actual final query deltas were 41 for A and 34 for B, with
5,868,937 bytes in 139 complete paired observation rows. The guard verified
exit within the hard deadline without a forced stop. Stopping the logger did
not disable normal firmware NTP polling.

Routine status remains compact; original histories are collected through bounded
USB pages. Identity, ownership and resource checks run each cycle. Saved
configuration, Wi-Fi generation and calibration are checked approximately every five
minutes, independently of NTP progress. A conflicting UI/settings change pauses
the observer. The heartbeat checked on a fifteen-minute schedule. It is now
paused after failure assessment and final review.

The failed reply was `{"ok":false,"error":"ntp_history_cursor"}` while
reading A's history. The firmware checks cursor bounds against the current
history length before checking whether the supplied snapshot token is stale.
Failure INFO still selected slot 3 with 58 records; final INFO approximately
3.53 seconds later selected slot 1 with two records, under the same boot and
image. This strongly supports a peer-switch pagination race: a continuation
cursor from the longer history was rejected against the shorter history, and
the observer handled only `ntp_history_changed` as a recoverable snapshot change.
The failed request cursor and earlier pages of that interrupted read were not
saved, so the exact wire interleaving remains inferred.

This was a diagnostic/observer failure, not a quality-gate rejection or evidence
that firmware NTP stopped. Saved configuration, Wi-Fi generations and manual
calibration comparisons recorded no conflict. A separate bounded post-stop
check at 02:06 UTC verified both original run boots, unchanged saved settings,
synchronized NTP, zero resource faults, unowned/inactive state and the unchanged
independent RF gate. Firmware was not reset or reflashed.

Complete paired rows contain 39 accepted A originals and 38 B originals.
Existing failure and exit INFO recover two additional A originals, yielding
41/41 A and 38/38 B accepted originals through observer exit, with contiguous
IDs within each of five source cohorts. These exit supplements do not reconstruct
the missing interrupted pages. Post-stop NTP samples are excluded from the
comparison below.

The exact-arithmetic oracle matched all 34 A and 33 B complete history snapshots,
with no qualified UTC or RF estimate. B reached a 32-record window but failed
strict stability/range gates; A did not retain enough samples in one active
peer history for qualification. All gates remain unchanged.

| Causal next-NTP comparison | A: pool | B: local |
| --- | ---: | ---: |
| Actual-clock-API-bound holdouts | 32 | 32 |
| Median absolute servo residual | 7.295 ms | 4.011 ms |
| Median immediate-phase-refresh residual | 9.350 ms | 4.013 ms |
| Median free-running residual | 9.202 ms | 11.620 ms |
| Within-cohort damped phase movement | 55.684 ms | 39.717 ms |
| Within-cohort immediate phase movement | 504.390 ms | 374.625 ms |

Damping produced substantially less movement within continuous source cohorts;
these totals exclude source-transition and reset discontinuities. Separating rate from the same
damped phase anchor, A's 18 nonzero-rate holdouts improved seven times and
worsened eleven, with a median error reduction of −53.740 µs. B's 32 improved
twenty times and worsened twelve, with median reduction +7.746 µs. This short
run does not establish a reliable interim-rate accuracy improvement, an
overnight result, or two-hour convergence. These are consistency comparisons
against later NTP estimates, not independent absolute UTC or RF truth.

Allocator/stack fault counters stayed zero in captured rows. Minimum sampled
available heap was 93,232 bytes on A and 98,704 bytes on B. Saved corrections
were updated independently of manual PPM. No RF jobs were started and no RF
calibration was qualified during the captured 35-minute interval.

The [evidence manifest](ntp-overnight-evidence.json) binds setup, process exit,
failure reply, complete originals, offline analyses and final settings readback.
A future repair should check stale tokens before current-history cursor bounds
and preserve interrupted request/page exchanges. No such firmware repair or new
live collection was performed during this closeout.

## Current-state inspection, 2026-10-18

After the user ended logging, one bounded read-only inspection completed at
11:48:50 UTC (06:48:50 America/Chicago). Continuous observation was not resumed.
Both boards retained the image and boots identified above, remained unowned
and inactive, and were synchronized to their configured servers. Saved
configuration, Wi-Fi settings and generation, and manual `0.000`/manual mode
matched their pre-run baselines. Allocator and stack fault counters were zero.
There was no firmware, settings, ownership or RF change.

| Current measurement | A: pool.ntp.org | B: time.local |
| --- | ---: | ---: |
| Queries / accepted / rejected | 647 / 638 / 4 | 597 / 596 / 1 |
| Latest synchronization age | 20.382 s | 19.496 s |
| Reported current clock uncertainty | 164.319 ms | 361.593 ms |
| Applied provisional UTC rate | −0.545 ppm | −1.022 ppm |
| Saved UTC rate | −0.464 ppm | −1.091 ppm |
| Retained spread-history span | 44.934 min | 117.376 min |
| Spread-history median RTT | 104.253 ms | 6.585 ms |
| Latest RTT | 126.736 ms | 242.847 ms |
| Current strict UTC / RF qualification | false / false | false / false |
| Historical saved RF candidate | none retained | available |

A had five other queries unanswered or pending. Its selected peer was
`73.185.182.209`; B used `192.168.1.54`. The table describes this inspection,
not the missing overnight stream. In particular, B's latest delay outlier and
114.713 ms unapplied phase lag increased its reported clock uncertainty despite
its much lower typical network delay. Typical delay alone is insufficient to
establish absolute time accuracy.

B's independent learning cache contains a historical software-qualified RF
candidate from the current boot: UTC slope −1069 ppb, reported slope uncertainty
4831 ppb, 32 observations over 1984.451391 s (33.074 min). Its source reference
time is 08:04:25.776876 UTC (03:04:25 America/Chicago); this is the measurement
window's reference time, not a recorded flash-write timestamp. The reciprocal
oscillator correction is approximately +1.069 ppm. Firmware stages such a record
only from a fresh qualified recent fit. This establishes that B reported a
qualifying software fit later in the night, after observation had stopped.
Its original window has expired, so the fit cannot now be independently
reconstructed and its qualification duty cycle is unknown. The stored record
explicitly reports unknown current age. This newly learned RF candidate has
not had a cold-boot restoration test. The earlier physical cold-start check
established UTC-prior restoration.

Manual PPM remains separate and the selected RF correction remains zero on
both boards. Independent RF acceptance remains false. The historical candidate
does not establish physical carrier accuracy or current RF eligibility.

All currently retained 32 spread and 32 recent records per board were recovered,
with complete USB request/reply exchanges. Full source-admission metadata and
uncertainty reconstruction were verified for the spread originals. Recent
records retain compact original ID, raw time, UTC and reported uncertainty;
full admission metadata is available only where they also occur in the spread
history. Eight A and 22 B recent-only records lack that metadata. Their fit
arithmetic was checked using reported uncertainty. Snapshot-token bindings and
the actual applied clock-rate API were checked. The exact-arithmetic strict-fit
oracle matched both boards with zero mismatches. Its current failures expose a
weakness in software qualification:

- B's extended training interval is [−2.760, +0.789] ppm. Its two half-window
  intervals overlap, but their centers differ by 5.592 ppm, exceeding the fixed
  2 ppm limit. This rejects mutually compatible uncertain estimates; it does
  not demonstrate that the crystal changed rate by 5.592 ppm.
- B's recent half-window center difference is 74.649 ppm. The recent training
  interval is [−6.445, +5.072] ppm, whose half-width already exceeds 5 ppm.
  Removing only the center-difference check would not establish RF eligibility.
- A's extended and recent center differences are 4.303 and 31.230 ppm, with
  much wider uncertainty intervals. Its present pool history supports a weaker
  rate estimate than B's local history.

The [current-state evidence manifest](ntp-current-state-evidence.json) binds the
private originals, oracle outputs and sanitized assessment. These retained
windows cannot recover the missing overnight corrections or establish whether
interim rate adjustment improved actual overnight error. Logging remains ended
and the heartbeat remains paused.

## Proposed statistical qualification

The user's current direction is to replace the brittle software convergence
rule with a Chrony-informed estimator. This proposal is not implemented in the
loaded image. Chrony weights measurements by network delay, rejects excessive
delay, and combines old and new frequency estimates according to estimated
accuracy. Its regression diagnostics use residual-sign runs to detect a poor
linear model and shorten the retained history. See the official
[measurement and update controls](https://chrony-project.org/doc/4.6/chrony.conf.html)
and [source statistics](https://chrony-project.org/doc/4.6/chronyc.html#sourcestats).

The proposed Pico policy is to maintain a bounded delay baseline per source,
downweight ordinary jitter and exclude excess-delay observations from rate
training while retaining their diagnostic records and rejection reasons.
Weighted offset/rate regression would report frequency uncertainty and use
residual structure plus uncertainty-normalized prediction errors to distinguish
network outliers from persistent clock or path changes. History would adapt to
model validity; two hours would remain a storage ceiling rather than a mandatory
wait. Each update would use only data available when issued, account for
correlation between overlapping fits, and avoid repeatedly counting the same
evidence as independent.

Correction updates would depend on estimate quality: good existing estimates
would dominate noisy replacements, bounded phase/rate changes would reduce
whipsaw, and holdover uncertainty would grow through loss and restart. Saved
priors would remain provisional until checked against fresh observations.
Statistical frequency uncertainty and conservative absolute phase uncertainty
must remain distinct; persistent asymmetry and server error cannot be averaged
away. Real source changes need explicit detection and reacquisition.

Packet validity, manual correction independence, launch accuracy requirements,
and independent physical RF acceptance remain requirements. A replacement
software model must demonstrate predictive error and uncertainty coverage on
causal replay and deterministic failure cases before target use. Tests should
cover delay spikes, correlated jitter, asymmetry changes, oscillator drift,
source changes, loss and saved-prior restoration, and compare phase damping
separately from rate correction. Parameter values and the exact statistical
qualification policy remain to be validated offline; no new live collection is
authorized by this proposal.
