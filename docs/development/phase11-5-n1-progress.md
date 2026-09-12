# Phase 11.5 N1 execution

Historical N1 series. For current prospective scope, use the
[six-family plan](phase11-5-plan.md) and [readiness ledger](phase11-5-acceptance-ledger.md).
The 2/20 counts and runtime identities below belong to their named attempts;
they are not current-image acceptance or active authorization windows.

Status: **OPEN; no accepted physical clock.** This September 11, 2026 record
supersedes the original packet's pending-authorization and live-state wording.
The user authorized N1 and directed continuation. The original six-hour host
deadline remains unchanged; continuation carries prior management-write counts.

The N1/N1r candidate firmware was clean `6e2ddc9e476986046de74d18cbcc3a2f6b64d142`.
Pico A's inhibited baseline runs at 150 MHz, with UF2 SHA-256
`822a7c28617592c28f4f03996b009a66ee32199816a467756b314abf63e41a71`.
The selected physical configuration remains 138 MHz, PIO divider 1, SRAM
renderer, UF2 `ba74b33ec7fd7530a56cc679799d9f452f08d896d22930903ef8bba132387a4d`.
That physical image failed nominal A2 USB delivery on boot
`28f0c1f98b19c6e2a8752e9f3fd881a3`. A 2.964660695-second INFO reply exceeded
the sampling bound; raw chunks show intervening TLS steps. Quiet and controller-only
physical intervals passed. No RF job followed. Pico A was restored to its original
inhibited image, boot `e5a4bc355fe7898a1e0b6d06be36fe9f`, with output inactive.
Host restoration completed without failures, B was unchanged, and packet captures
reported zero kernel drops. The complete private N1r archive SHA-256 is
`b5c7e93eabae8e0149d7ee227fc540b2c1bf3e59d5830afd8e987296c7b3d82a`.
The [USB reply repair](phase11-5-usb-priority.md) at `4ca4494` requires both
new-image target baselines. Physical 132 and 150 MHz are untested.
Selecting another clock during 11.6 requires repeating the affected 11.5 checks.

## Preserved attempts

1. Original N1 passed its 360-second inhibited quiet observation. The private
   production INI had lowercase keys, which the actual application's exact-case
   parser ignored. The executable exited before readiness. A and the host fixture
   were restored; B remained unchanged. The private archive SHA-256 is
   `2ebc508c1489b2f6350d7ee4023e6e864077137d4da0e596a67b73d54418aa59`.
   See [the first-attempt result](phase11-5-device-fixture-result.json).
2. N1r used canonical INI keys and passed a fresh quiet observation. Its actual
   `fb0a2eb` controller achieved only 175 nominal STATUS reads in 180 seconds.
   The rate audit failed. No browser or RF case followed that failure.
3. The corrected controller, clean WsprryPi
   `6f65d5c7d202569102459ab68d7c9ea079b96f35`, passed the controller-only interval:
   **179 nominal STATUS reads in 180 seconds**, one connection/session,
   maximum native-write-entry-to-response time **0.638055880 seconds**.
   Executable SHA-256:
   `122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`.
   The independent 240-second observer reconstructed 240 INFO and 48 USB STATUS
   samples, with unchanged boot `c2c2aa975f5d7d03c0c4cca5dea5154c`, zero observed
   faults and allocator peak 63,156 bytes. This is an inhibited result only.
4. That attempt's browser interval failed its five-second sampling schedule.
   The initial serial status/page/style/script requests took approximately
   1.430, 2.022, 1.497 and 1.488 seconds. Their 6.437-second total delayed the
   next status request beyond the frozen one-second scheduling tolerance.
   The coordinator stopped dependent work. The USB observer's subsequent SIGTERM
   is coordinator cleanup, not evidence of a device fault.

## Current bounded continuation

The `browser-priority` workload preserves the controller executable and firmware.
It services status first and fetches one page asset in each of the next three
five-second slots. All declared request counts and deadline thresholds remain:
36 status requests and six requests each for page, style and script per 180 s.
Regression tests use the observed reply costs and still reject overload.

Its manifest SHA-256 is
`fc789d562dfb1621c8eedc725a50b862f00b91f1fd771eaf5bf83be670abc23c`.
The continuation re-audits the previous passing quiet/controller raw evidence,
requires the same boot and executable, preserves the failed browser attempt,
and repeats the affected nominal interval followed by the 360-second quiet
comparison. The repeated combined interval passed: 179 controller STATUS reads, 36 browser
status reads and six requests each for page/style/script. Its maximum measured
controller write-to-response interval was 1.311965149 seconds; the independent
observer reconstructed 240 INFO and 48 USB STATUS samples. Allocator peak was
125,428 bytes on the inhibited image. The final quiet comparison passed: 360 INFO and 72 USB STATUS samples, with
17,228 allocated bytes versus 16,660 at the preceding quiet baseline, a 568-byte
difference within the frozen 1,024-byte limit. The inhibited A2 baseline passed.
The authorized physical switch completed successfully; A2 remains partial until
the physical baseline passes.

The private root is `/home/pi/phase11-5-n1r-6e2ddc9`; original frozen restoration
helpers and packet are preserved. No RF job has been submitted by N1. The
installed WsprryPi executable/service, comparator B and GPSDO settings are
unchanged. The fixture radios and temporary DNS/chrony access have been restored.

## Validation and remaining work

The current hardware-free Pico suite passed 54 tests. The host cadence repair
passed 39,834 application checks and 6,853 production checks. Five load-driver
tests cover exact INI keys, no-run behavior, failed process evidence and browser
scheduling. The opt-in TLS observer passed eight concurrent loopback streams,
including 65,552-byte writes, six corrupted-log cases, version-1 compatibility,
and write-entry/result lifecycle checks. These checks do not qualify physical RF.

A3 finite-job observers/coordinators are prepared and require their final review
and execution after both A2 baselines. B through G remain unrun. The systematic
RF band/mode/clock comparison and spectral/filter qualification remain Phase 13;
per-band/mode conducted RF acceptance at selected clocks remains Phase 11.6.

Documentation Impact: this record, the joint plan/register and frozen-packet
status pointers. The companion Pi development review records the controller
repair. WTP, browser API and operator contracts are unchanged; published operating
limits still require acceptance. The separate operator-manual repository remains
unchanged.

## Revised-image continuation N1s

The [frozen packet](phase11-5-usb-priority-packet.json), SHA-256
`7985786b1796c7a36ba510d39ee08df6c06222a11e1e36795ae40b29cff755c7`,
binds clean firmware `4ca44943e844465e6109719ad91b900159f9d84f` and the
[new linked image list](phase11-5-usb-priority-images.json). Both standalone
images include the reply-priority change, so both A2 baselines are repeated.
The previous failures and passing old-image evidence are retained.

The private root is `/home/pi/phase11-5-n1s-4ca4494`. The inherited original
absolute host deadline is unchanged. Device runtime is bounded to 9,000 seconds,
with 600 seconds reserved for restoration; the host fixture is bounded to
10,500 seconds plus 600 seconds for cleanup. These are supervisor ceilings,
not required test durations. Four prior configuration writes were carried into
the packet; candidate configuration is the fifth. No RF jobs are in this packet.
Pico A's inhibited admission boot is `62e9ec13007db1d3e619a31cb6d33e5b`,
at 150 MHz, synchronized through the isolated DNS/chrony fixture. B, the installed
service and GPSDO settings remain unchanged. A2 is running; zero of the twenty
full acceptance cases is closed at this checkpoint.

Adversarial review of the prepared A3 actor found that calculating an ARM time
before waiting for a browser slot could consume the intended launch lead. The
actor now chooses the finite start from a fresh device clock snapshot after
acquiring the slot, then verifies and records the returned exact start. This
prepared path has not executed on a target; it does not close A3.

A1 is now **PASS**, within its original compile-only definition: network control
off/on and inhibited/physical layouts, all four exact 4ca4494 images. The image
record includes linked heap/stack/section limits, archive hashes, compiler hash
and pinned dependency revisions. Runtime gates remain open. The case count is
**1 of 20**, with no accepted physical configuration.

N1s retained a staging failure after its passed quiet interval: the actual Pi
controller refused the copied TLS key's file ownership before readiness. No TLS
connection or RF job resulted. Credential contents were unchanged; ownership
was corrected to the executing root account with owner-only permissions, and
prior metadata was recorded privately. Future root extraction uses
`tar --no-same-owner` and checks credential ownership before any timed case.
The `file-owner` continuation re-audits the same-boot quiet trace, retains its
observer session and the failed process record, and repeats only affected
stages. Its manifest SHA-256 is
`e5f25409b4090ab5c891b394ba142e36bc6b833c3cdb97d36eb7e0658cdfe3d4`.
The corrected controller interval passed 180 nominal STATUS reads in 180 seconds,
with a 1.173683358-second maximum native write-entry-to-response interval;
240 INFO and 48 USB STATUS observations passed. Combined browser load is running.

The A3 gate now takes explicit reviewed A2 case names and result digests and
checks the exact prerequisite firmware/clock. This permits preserving a failed
attempt beside its corrected continuation without relabeling or overwriting it.

The first revised-image quiet comparison failed: 16,916 bytes after load versus
15,492 at startup, a 1,424-byte retained difference. Every controller, browser,
USB and quiet interval completed and passed its wire/timing checks. The failure
is retained; it is not evidence of repeated growth or a proven leak by itself.
The same-boot `warm` continuation uses the measured post-load quiet window,
re-audits the earlier controller/nominal evidence, and repeats identical N180
plus Q360 at the unchanged 1,024-byte comparison limit. Its manifest SHA-256 is
`2657ac4956fa2d1364a0b5930e894bf978578ec76aaab061c33f0ca2edcee70b`.
No flash, configuration change, fault clearing or deadline extension occurs.

Before the fresh physical A2 baseline, execute at most one explicitly recorded
N180 conditioning interval with the existing 240-second USB observer. This
preserves initial allocations separately and exercises the previously failed
USB/TLS path before the matched Q/controller/N/Q comparison. It submits no RF
jobs. It must pass the same wire, rate, memory-reserve and USB limits; failure
stops dependent work. Do not repeatedly condition until a result passes. Initial
retained allocations and later equal-state comparisons remain separately visible.

The repeated nominal interval passed 179 controller STATUS reads, 36 browser
status requests, all 18 asset requests, and all 240 INFO/48 USB STATUS samples.
Maximum controller write-to-response time was 0.660180073 seconds. The final
Q360 passed with 16,916 allocated bytes, **zero growth** from its measured
post-load reference. The initial 1,424-byte startup difference remains retained;
this bounded repeat does not prove absence of every leak or close the broader
allocator/sustained-load gates. Inhibited A2 on 4ca4494 is reviewed as passed.
Result SHA-256:
`c0004144d4310f3c9353ab27a0a4c6ca7d71ba12304a13de0c2ddd4676708c5a`.
The guarded switch to the selected 138 MHz physical image completed. Physical
boot is `8a415fd18156fd20abfc2c7dadcbb973`; the UF2 is the published
`7235bcd8ea1e54c09c894a23558232d83c538d8cc2c1ffc78dd6b4a809c81ef5`.

The single predeclared physical conditioning interval passed independent raw
USB/TLS audit: 180 nominal controller STATUS requests, 36 browser status
requests, six each for page/style/script, 240 INFO and 48 USB STATUS samples.
Maximum INFO sampling gap was 1.000090468 seconds; maximum native TLS
write-entry-to-response interval was 0.849392831 seconds. Allocator peak was
118,544 bytes against 218,392 bytes of heap capacity. It submitted no RF jobs.
The subsequent full physical A2 quiet-before window passed with 16,928 bytes
retained, 360 INFO samples and 72 USB STATUS samples. Controller, nominal and
final quiet comparison remain required before closing A2.

Pre-execution adversarial review of A3 found that its audit checked terminal
states and matched refill counters but did not require the complete expected
DMA/launch/tail totals. The audit now compares counter deltas against all three
ten-second jobs: 7,902 DMA IRQs, three launches, three tails and 7,896 running
successor links. Missing or extra counts are rejected by hardware-free tests.
This strengthens the audit without changing the image or the finite jobs.

B1 execution support is prepared for the original Q360 / three N300 / Q360
workload. It reuses the existing load driver, preserves one USB observer session,
checks reviewed A2/A3 hashes and current boot, and compares equal terminal
history. The load helper rejects a duration or workload that differs from the
frozen packet. B1 has not run; no case count or clock acceptance follows from
this preparation. The original independent restoration deadlines were unchanged.

Physical A2 subsequently failed in nominal browser load after the controller
interval passed all 180 nominal STATUS reads and 240 INFO/48 USB STATUS samples.
The first browser status request took 6.013358513 seconds and the following
page fetch took 2.103315077 seconds; the next five-second browser sampling slot
was missed. The observer was then stopped by the coordinator; its signal-15
finish is a consequence of the load failure, not the original USB timing fault.
No RF job was submitted. Passive captures preserve TCP retransmissions and
multi-second gaps; these do not by themselves attribute the delay to a specific
firmware routine or to the radio link. Status reported a 4,454,740-microsecond
maximum handshake and an 811,423-microsecond maximum server poll.

The failed interval spent 3.414361 of 13.285770064 seconds in allocator sampling
(25.7%). The proposed repair eliminates free-only heap walks while preserving
all allocation/reallocation post-state peaks and refreshed public snapshots. It
also avoids materializing a full status when active-job connections are already
permitted. All 54 hardware-free tests and the pinned native TLS regression passed
(11.50 seconds). This is a measured source of overhead, not proof that the repair
resolves the physical browser failure. New exact-image baselines remain required.

Authoritative reconciliation found A empty, unowned, inactive and fault-free on
the same physical boot. Guarded original-image restoration then passed; A is
inhibited on boot `495e4183764e31261d631d957d49f3a1`, B retains its original boot,
and cumulative configuration writes are six including restoration. Host cleanup
passed, leaving the installed `wsprrypi.service` active at unchanged PID 1957,
wlan1 unchanged and the Wi-Fi recovery timer active. AP/client captures contain
8,806/8,199 packets respectively, with zero kernel drops on both. A2 remains
failed; A3 through G1 remain unrun. Only compile-only A1 is closed.

## N1t inhibited reference passed; physical baseline pending

Clean allocator-cost candidate `8fb3894253ef45adc3aad28f25a684168487490f`
completed the one declared N180 conditioning interval and the full inhibited
Q360/controller180/N180/Q360 family on boot
`e66f436249fefe24d2c1d15131f65b33`, clock 150 MHz. Both load intervals passed
independent raw TLS and USB audits. Each had all 180 production STATUS requests;
the browser interval also had all 36 STATUS requests and six copies of each of
its three assets. Its maximum measured native TLS write-to-response delay was
1.063045669 seconds. The quiet heap was 17,004 bytes before and after (delta 0).
The maximum observed allocator peak was 123,596 bytes; allocation-failure and
stack-guard checks passed. This is inhibited reference evidence only.

The complete family result was independently re-audited against raw logs before
physical admission. Its SHA-256 is
`60fa790be6f257c578ec9a468876bf4b9a60d4a5be457446a762afefad68eaeb`;
private remote path is
`/home/pi/phase11-5-n1t-8fb3894/a2-inhibited-browser-priority-family-result.json`.
The local result copy is `build/phase11-5-closure/n1t-inhibited-a2-reviewed.json`.
A2 is not closed until the exact 138 MHz physical candidate passes its family.
No RF job was submitted in this reference run; prior failures remain retained.


## A2 closed on N1t; 2 of 20 cases closed

The exact 138 MHz physical candidate completed its declared conditioning interval
and Q360/controller180/N180/Q360 family on boot
`c282a09bdc59600f588a7abe5675e633`. Independent raw USB/TLS re-audit passed every
interval. Both load intervals contained all 180 scheduled production requests;
the nominal interval contained all 36 browser status requests and 18 assets.
Maximum measured native TLS write-to-response delays were 0.688488665 seconds
(controller) and 0.678320638 seconds (nominal). The quiet heap was 16,928 bytes
before and after, delta zero. The allocator peak reached 123,512 bytes with
unchanged zero allocation-failure counts and valid stack guards.

Together with the reviewed inhibited reference, this closes A2. The sanitized
[exact-image result](phase11-5-a2-result.json) retains both full family summaries
and their hashes. A1 and A2 are PASS: 2 of 20 cases. No clock configuration is
accepted and the prior failed attempts remain retained. A3 was then admitted
under the continuing explicit RF authorization, using the separately reviewed
`3a39cc2` helper supplement; its frozen manifest SHA-256 is
`b44481ec398036b8052df27e3556ddacebda8c15212fae0cd1f5cdf45d00f58c`.
It submits exactly three ten-second 135.5 kHz Tone jobs under N180.


## First A3 attempt: observer freshness guard failure

A3 is FAIL for its first attempt, while A1/A2 remain PASS (2 of 20). Only job
`926a539c60a48ccda6960d7b3781d707` was armed; the other two jobs were not
submitted. The actor stopped at host monotonic 112632597786459 ns because the
previous completed INFO was 2.008 seconds old. A read had started on schedule at
112631498791352 ns and completed at 112632981002224 ns: 1.482210872 seconds,
within its five-second response deadline. Its predecessor began at
112630498783800 ns. No INFO start-to-start sampling limit had been exceeded.
The later observer/driver failures followed the coordinator's termination.

Authoritative reconciliation found the same physical boot, completed job, no
owner, output false and no firmware fault. Counters were 2,634 DMA IRQs, one
launch, one tail and 2,632 successor links. Full/short predecessor reserves were
7,485/16,384 and 2,155/2,312 words; maximum worker service gap was 2,004,000 ns.
These are one-job observations, not an A3 pass. A guarded CLAIM/RELEASE returned
the completed current job to Empty and preserved its exact terminal record.
No flash, journal erasure, configuration change or additional RF occurred.

The archive `phase115-n1t-a2-a3-first-preserved.tar.gz`, SHA-256
`e5a16cb262baa649ef23bea691dfae4643b2964f46cdb8459f09a3341cdcbb0f`, is retained
under both `/home/pi/` and local `build/phase11-5-closure/`. It includes A2,
the failed A3, reconciliation, cleanup and their helper/manifest records.

The harness repair recognizes a same-process, same-packet read already in
flight within its five-second response deadline. The ordinary actor does not
mistake that read for an abandoned completed snapshot. Sampling limits remain
unchanged: INFO start gaps at most two seconds, STATUS gaps at most six, and
five-second request bounds. ARM still requires a completed INFO no older than
two seconds. The independent observer publishes the pending read's identity;
expired reads, wrong operations, changed process identity and stale pre-ARM
INFO are rejected by regression, including the exact measured failure timing.

A separately named corrected A3 attempt may retain the prior completed record.
It must perform three new finite jobs with complete state and hardware-counter
coverage, and its audit must preserve the prior terminal record unchanged.
A2 is not repeated because neither firmware nor its idle workload changed.
The follow-up source review checked strict ARM freshness, bounded in-flight
reads, default no-access entry points, retained-history admission and unchanged
sampling/RF thresholds. The affected tests and both scheduling models pass.


The first corrected coordinator invocation stopped before its admission inventory
or any RF job: a prerequisite-loop variable replaced the new case name with the
A2 name, and exclusive file creation rejected the existing A2 evidence path.
No evidence was overwritten. The original supervisor log is preserved. A new
regression exercises actual A3 and F1 prerequisite admission and reproduces both
wrong labels before the repair; both pass with distinct prerequisite/case names.
The corrected attempt uses a fresh supervisor/manifest. Firmware, boot, retained
history and A2 evidence remain unchanged.


The `observer-progress-v2` A3 attempt reached Running, then stopped because the
browser load exceeded its existing one-second status lateness bound. At 48.861
seconds into N, it started a 2.508-second asset request with 1.139 seconds before
the next poll. Earlier requests had already demonstrated asset costs up to
2.934 seconds. This is a load-scheduler failure, distinct from the prior INFO
freshness guard. One new job, `414173f362488c61a76db612847f4ff6`, completed;
authoritative reads confirmed inactive output, no owner and no firmware fault.
Maximum worker service gap was 2,060,000 ns, full reserve 7,485/16,384 and short
reserve 2,103/2,312. The exact completed job was released after reconciliation,
retaining both terminal records. The original failure logs remain preserved.

Pi source `6703818` repairs asset admission using measured cost and the unchanged
one-second scheduling allowance. Its measured-sequence regression fails the old
runner and passes the repair with every required status/asset request retained.
All eight Pi driver tests and both finite-job scheduling models pass. The
production binary, firmware, clock and A2 request mix/thresholds are unchanged;
the next case records its new driver hash rather than relabeling the old A2
trace. No failed A3 attempt is promoted to PASS.

## N1t final disposition and restored state

The `asset-slack` attempt also failed browser cadence. Its last stylesheet
request began at N+42.899 s and took 3.260 s; the next status poll, due at
N+45 s, therefore exceeded the unchanged one-second allowance. The measured
previous asset maximum did not bound the next response. This remains an open
contention failure; further scheduling guesses are not acceptance evidence.
The third job, `271b9b4489e43bebf1f87e8ac5acaa03`, completed. Authoritative
reconciliation confirmed inactive output, no owner and no firmware fault.
Only one of the three planned jobs was armed in each failed attempt.

[The final machine-readable result](phase11-5-n1t-result.json) binds all three
attempts to physical image `75b26e3f…`, source `8fb3894253ef`, 138 MHz, divider 1
and SRAM rendering. The count remains **2/20 closed: A1 and A2; A3 FAIL; the
other 17 cases NOT_RUN**. Three separately completed jobs from failed attempts
cannot be combined into an A3 pass. No clock configuration is accepted.

After exact completed-job reconciliation, guarded CLAIM/RELEASE retained all
three terminal records. The original inhibited image and configuration were
then restored to Pico A, boot `5b336cccde0e8ce1389a333755cb84f3`. Pico B retained
boot `4e2fb851c08b278dd4b977104d2c2aaa` and its configuration. Both authoritative
inventories report Empty, inactive and unowned. The test namespace/AP and chrony
ACL were removed, wlan0/wlan2 returned down, wlan1 retained its ordinary address,
the Wi-Fi recovery timer is active, and installed `wsprrypi.service` retained
PID 1957. The cumulative configuration-write count is eight.

The full private archive `phase115-n1t-preserved-final.tar.gz`, SHA-256
`e13a5388017d2a2065e1028c823abd509a0f7028b07ed5192014c660a50b8cb6`,
is retained on wspr5 and hash-verified in the ignored local evidence directory.
It includes both A2 families, all three A3 failures, the coordinator admission
failure, guarded cleanup and restoration evidence. Original failures remain
unchanged. This closes the temporary fixture, not Phase 11.5.

## Activity snapshot repair and adversarial review

Source review found repeated full `JobService::status()` construction in the
physical main loop merely to read its state. Every construction copies the
boot ID and any owner/job IDs and retained terminal history. The cost therefore
grows as completed jobs accumulate. This is a concrete source inefficiency;
the traces alone do not establish that it accounts for all browser delay.

`JobService::activity()` now supplies state, live engine output and ownership
presence without copying identities/history. The main loop, connection busy
check and scheduler idle/reset checks use it. Full external STATUS still copies
and returns its complete history. Both paths share the existing local-launch
race handling and query current engine output; no output result is cached.
Allocator peak measurement and all acceptance thresholds remain unchanged.

The new regression proves allocation-free observations across Empty, Loaded,
Armed, Running, Complete and Failed, owner expiry and up to eight retained
records. A full status read in the same test demonstrates the previous allocation
cost. Further checks preserve unexpected output and distinguish a local IRQ
launch from an inconsistent nonlocal Armed/active report.

Adversarial review checked output freshness, owner expiry, failed-state reset
exclusion, terminal-history preservation and unchanged wire serialization.
The review added explicit failed-state/expired-owner coverage; those affected
tests passed. A second review found no further actionable issue in this bounded
source change. All 55 host tests passed, the final affected core/scheduler tests
passed, and native TLS passed in 11.14 s. Target performance is still unmeasured:
new linked images and affected A2/A3 checks are required before accepting the
repair. Earlier A1/A2 results remain bound to `8fb3894`.

## N1u: activity candidate conditioning failed; setup restored

The user approved the separate two-hour activity-candidate network window.
The exact inhibited `4058d3a4a951` image ran one N180 conditioning interval with
USB240. [The unchanged audit failed](phase11-5-n1u-result.json): 179 production
STATUS requests fell within N, with one 2,696,718,780 ns gap exceeding the frozen
2,000,000,000 ns bound. The slowest native TLS write-entry-to-response interval
was 2,592,628,676 ns. There was one production connection and one logical session;
its complete replies retained the expected boot and inactive/unowned state.

The independent raw USB audit passed all 240 INFO, 48 STATUS and 48 health
samples. Maximum INFO request-start gap was 1.000108 s; allocator peak was
118,572 bytes, with no nominal allocation failure. The browser completed all
36 status requests and six requests for each of root/style/script, with HTTP
200, correct boot and a maximum observed request duration of 1.702419 s.
These passing diagnostics do not waive the failed production cadence gate.

Dependent testing stopped: neither full A2 family nor A3 ran, the physical image
was not flashed, and no RF jobs were submitted. Pico A returned to original
inhibited revision `802c91a7b86e-dirty`, boot
`340fe3681621d5c9f112890160e3a826`, with its original configuration and inactive
output. Pico B retained its boot/configuration and inactive state. Normal host
interfaces/routes, installed service PID 1957 and the active recovery timer were
verified restored. The cumulative configuration-write count is ten.

The complete private archive `phase115-n1u-preserved-final.tar.gz` has SHA-256
`636cf62e56264d3856bfe0202772b907e793ba5c28453c7f1800b4e409624d69`.
Its copy was hash-verified locally, then the unchanged USB and production
auditors independently reproduced PASS and FAIL respectively. The production
auditor was not modified. Remaining browser checks were evaluated separately;
the aggregate result remains FAIL. Restoration review compared both original
configurations, comparator boot and exact pre/post host state.

There is no demonstrated root cause yet. Native TLS and USB timing show the
stall, but the run contains no packet-level capture to distinguish retransmission
from firmware/network servicing delay. A diagnostic follow-up needs correlated
packet evidence before selecting another repair; an unchanged acceptance retry
would not close that finding. No further live test ran after this failure.

Adversarial evidence review found and corrected stale documentation saying the
new window was unapproved/unexecuted. It also kept the older `8fb3894` A1/A2
passes separate from this candidate's failed conditioning. The follow-up review
found no further reporting inconsistency. The unresolved timing failure remains
open, rather than being described as repaired. **Zero cases closed in N1u;
the historical count remains 2/20 and no configuration is accepted.**

## N1v–N1y: corrected audits and packet-delivery diagnostics

The [execution prompt and review](phase11-5-status-stall-review.md) record three
closed tooling defects: STATUS cadence used TLS write-return timestamps, Console
trace hashes were subjected to WTP integer limits, and the diagnostic trace
reader could consume INFO's sampling time while draining a burst.

N1v completed N300/USB360 with dual captures. N1w failed before load startup on
the Console integer mismatch; N1x collected a continuous trace but stopped on
INFO cadence after an unbudgeted trace burst. Both failures and restorations
are retained. The repaired N1y diagnostic completed N300/USB360 and 3846
continuous trace events; independent load and USB audits passed. The
[final result](phase11-5-status-trace-result.json) binds exact identities and
hashes. These diagnostics used inhibited source `4058d3a4a951` at 150 MHz and
submitted no RF jobs; they do not close A2/A3 or qualify a physical clock.

Three captured browser delays across N1x/N1y include response segments absent
from both host captures after successful device submission, then delivered on
retransmission. This identifies delivery gaps between observed boundaries.
It does not establish the precise driver/radio/AP cause or retroactively
attribute N1u's uncaptured STATUS stall. No firmware repair is claimed.

Final A boot is `bbabf4bdffb92c6bb0f04f11929c2262`, original inhibited image and
configuration restored, Empty/inactive/unowned. B is unchanged; normal host
networking and the recovery timer are restored, installed service PID 1957 is
unchanged, and cumulative configuration writes are eighteen. All diagnostic
fixtures respected N1u's original absolute cleanup deadline.

The 57-test host suite and affected follow-up tests pass. Corrected auditing
preserves all six historical N1t load passes and N1u's failure. **Zero new
acceptance cases closed; historical A1/A2 remain 2/20 and no configuration is
accepted.** Full affected A2/A3 and the remaining Phase 11.5 cases stay open.


## N1z: single acceptance attempt after diagnostics

The [single-attempt result](phase11-5-single-attempt.md) records the fresh bounded
fixture and first-failure stop. On unchanged `4058d3a`, all four inhibited A2
intervals passed with +16 bytes retained heap. The 138 MHz conditioning interval
then failed production STATUS cadence: 177 nominal requests and a 2.685-second
maximum request-start gap. USB and browser checks passed. Physical A2 and A3
were not run; no RF jobs were submitted. Packet captures include the failing
production exchanges and are consistent with delayed TCP retransmission recovery,
with the exact loss/submission boundary still unproven.

A, B and normal host networking were verified restored. Zero new full acceptance
cases closed; historical 2/20 remains, with no accepted physical clock. This
reproduction does not establish the cause of the older N1u event. The next work
must address the identified STATUS delivery blocker before another acceptance
attempt; no retry or speculative firmware repair was performed here.
