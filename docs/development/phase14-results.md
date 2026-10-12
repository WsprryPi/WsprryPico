# Phase 14 qualification results

Status: IN PROGRESS. See the pre-acquisition [plan](phase14-plan.md).
Storage follows the operator-amended [evidence retention policy](phase14-evidence-retention.md).
No Phase 14 release support is claimed at this checkpoint.

## October 12 response-body repair and Linux regression

The operator requested that the identified defect be fixed. The source now
releases the dynamic HTTP response body when a connection closes or an
acknowledged keep-alive response finishes. Both paths call the shared
`HttpResponse::reset()` primitive in the existing transport cleanup order.
Response bytes remain available until that boundary. RF algorithms, job timing,
browser content and the original resource acceptance limits are unchanged.

A distinct Linux validation rebuilt the portable core and passed all six
affected test groups: network, response lifetime, bootstrap HTTP, browser,
owner-claim HTTP and transport contracts. The allocation regression checks
30 cases across two slots, including empty/static, small and large bodies,
completed/cancelled responses and acknowledged keep-alive reset. Every repaired
reset returns requested C++ allocations to its construction baseline. A separate
control changes only the reset call back to the previous empty-response
assignment and fails the reclamation assertion with 65 retained requested bytes
in three blocks. This demonstrates that the regression detects the old behavior.

The completed parent receipt is
`build/phase14-response-body-repair-host-closed-20261012/result.json`, SHA-256
`a367788c516ecf882af7a64913692487e07048217cc85700bee55d1a509467ab`.
Offline source/log/order verification is
`build/phase14-response-body-repair-host-offline-review-20261012.json`, SHA-256
`e6f609c2528a337599209baf1a882ba158fa583d529233024a30fc42dc2002ea`.
The finite harness and children are gone; the owned service remained active.
No device, RF, raw sample, external transfer or removal occurred. The useful
installed images still contain the original source. Clean Arm build, artifact
review, installation and target validation remain before any deployed-repair
claim. The original mixed failure remains unchanged and unaccepted.

Hourly reports now include a freshly verified `Harness: RUNNING` or
`Harness: STOPPED` indicator alongside counts, percentage and ETA; unavailable
live state is reported as `UNKNOWN`. Counts remain 3 of 9 workstreams (33.3%);
estimated 15–37 hours remaining, with possible repair extension. Host tests and
elapsed time supply no original-workstream acceptance credit.

## October 12 mixed resource failure and closed workflow

The exactly-once clean-image mixed run is closed with
`FAILED_AMENDED_CLEAN_MIXED_EVIDENCE_PRESERVED`. All eight one-hour acquisitions
and both GPSDO reference batches completed normally. The unchanged science
analyzer returned zero within its 7,200-second bound, then the coordinator
refused qualification because the aggregate resource assessment failed.
The final parent receipt SHA-256 is
`3b0a10cd3687a629473dc61640cac223faa3146f626d4b46b69b52b615e31a32`;
the assessment SHA-256 is
`7d538fee857bbdb7b87ac637922bc4a874b25e35d0bc42e61f0985063a61d9e9`.
These supersede the active-run snapshots below for current process state.

Equivalent three-sample windows after the original 45-second idle show B's
median allocated growth at 1,384 bytes for Tone and 1,704 bytes for FSKCW,
exceeding the unchanged 1,024-byte limit. A's corresponding changes are zero
and minus 16 bytes. Every individual active/idle resource and cumulative fault
screen passes; B's four browser workloads each pass the required request count
and time span. The aggregate human-copy-aware RF screen passes, while all four
original FSKCW legacy screens remain false. No original flag was promoted.
This identifies a resource acceptance failure, without isolating a leak or
its physical or software cause.

A separate finite metadata-only review independently checked all eight actual
job/source/image/boot/control/metadata/analysis bindings, recomputed active and
idle resource checks from the recorded INFO events, recalculated equivalent
idle growth and browser counts/spans, and verified the recorded final settings,
current cursor, inactive/unowned/disabled state and unchanged GPSDO controls.
Its receipt is
`build/phase14-mixed-resource-failure-independent-review-20261012.json`, SHA-256
`f6531bb570f4324fd6318f19893256d58c7ac1c6b283f06327459408add7e8f7`,
identical to clean-root
`build/mixed-resource-failure-review-20261012T0610/result.json`.
Ten isolated idle-window boundary/refusal checks passed. The reviewer held all
four locks, verified all campaign processes gone and independently read the
restored `wsprrypi.service` as active. It made zero raw reads and zero device
requests; current board/reference readbacks are the recorded coordinator
closeout, not new independent live-device measurements.

All 58.32 GB of mixed raw samples remain internal. This review binds their
current stat identities to the completed science hashes, and does not replace
independent full-raw qualification. The failed coordinator reached neither
the later Tone close-in checks nor whole independent acceptance. No mixed
capture credit was applied. The separate memory follow-up is not admitted;
the completed run, analyzer and reservations must never be blindly repeated.
Any causal successor needs a separate bounded plan at a fresh quiet boundary,
preserving source identities and the original workload/acceptance limits.

Progress remains 3 of 9 original workstreams (33.3%); estimated 15–37 hours
remaining. Repairs can extend that range. Final installation, consumer API,
profile/configuration, smokes, evidence retention, review, push and closeout
remain unfinished.

### Closed idle B browser path contrast

The separately admitted six-GET idle target diagnostic completed once in
607.194409293 seconds. Program admission passed 19 static/fixture/refusal checks
and 692 source bindings before device access; live admission verified the
expected clean853/138 boots, idle state, false flags and public durable
settings/current watermarks before traffic. Exactly 26 direct Console INFO
commands and capabilities/root/status/root/capabilities/root GETs executed.
All processes are gone, all four locks are available and the service stayed
active. No WTP, RF, firmware, profile/cursor, receiver or GPSDO action occurred.

B's 45-second heap medians were 19,864 bytes after capabilities/root, 22,416
after status/root, then 19,864 after capabilities/root again. All windows had
zero spread; each root preserved the preceding level and the final at-least-
350-second window remained 19,864. TLS allocated stayed 4,397 bytes; selected
connection/input counts stayed zero. This demonstrates a reversible 2,552-byte
idle path effect, consistent with host response-body retention. It does not
isolate an individual target container or the original active mixed failure,
prove leak freedom, select firmware repair or relax the original resource gate.

Verbatim parent receipt
`build/phase14-idle-browser-path-contrast-closed-20261012/result.json`, SHA-256
`254bbe284a50f46f095789dcf6def69994f12a6a5d7d80aee125953a710220c1`,
and separate `independent-review.json`, SHA-256
`75b235fac04cf28ebb9191003e4d548d73e239a6b15bfcc2c48695c46db5c018`,
retain actual response hashes/lengths/parsed values, Console bytes, all INFO
observations and independent timing/arithmetic/source/settings/process review.
Same-boot/public cursor checks are not fresh full-flash byte proofs. The
[causal plan](phase14-memory-causal-plan.md) records exact admissions, final
quiet proof and a private, unselected response-body release proposal for future
bounded host validation. Production source and installed images remain
unchanged. Qualifying memory follow-up stays blocked; counts remain 3 of 9
(33.3%), estimated 15–37 hours remaining with possible repair extension.

### Closed host memory lifetime control

The separately bounded [causal plan](phase14-memory-causal-plan.md) now records
a completed Linux-only probe of unchanged clean-source WTP HELLO/STATUS
lifetimes. A separate admission program checked source/dependency/binary
bindings, seven static acceptance/refusal cases and allocation controls before
the probe ran. The first admission's ineffective loop-bound guard refusal is
preserved; a distinct corrected successor reused the completed binary and
executed the synthetic probe once. Both coordinators and their children are
gone; no board, RF, decoder, sample, firmware or external-storage action occurred.

The one-session case retains 2,769 requested C++ bytes after expiry across all
four epochs. The twelve-session case changes from 4,809 to 6,089 bytes, then
plateaus for the remaining epochs. Both return all tracked bytes/blocks to zero
on full service destruction. Actual host receipt
`build/phase14-wtp-lifetime-host-result-20261012.json`, SHA-256
`9c20517a50cf2759bf1e84e9c8029d679a6ad2d8f21f8c99315fed9e0474f661`,
and separate offline recomputation
`build/phase14-wtp-lifetime-host-result-review-20261012.json`, SHA-256
`0caf807dd90e2aeea1b7b27314fe64975833d72d94b8fe1a0630e05cf9818181`,
bind these limited findings. They do not identify B's target cause or qualify
its allocator, HTTP/TLS/lwIP or 512-event job lifetime. Browser GET status/jobs
views bypass WTP replay insertion, so this host retention step does not explain
the browser-loaded failure. Both INFO heap counters use the same underlying
newlib `mallinfo().uordblks` at different times; they are not independent leak
measurements. The subsequent HTTP result is recorded below.
No original failure, threshold, source identity, workstream count or credit changed.

### Closed portable HTTP lifetime control

The distinct HTTP/API/parser runner completed 1,600 successful rotating GETs
with two reused slots, four epochs, virtual 10-second spacing and 45/350-second
idle samples. All twelve post-workload/idle samples retain 7,233 requested C++
bytes in 26 blocks; construction retains 3,783 bytes in 24 blocks and full
fixture destruction returns both counters to zero. The parent receipt is
`build/phase14-http-lifetime-capacity-aware-result-20261012.json`, SHA-256
`9c731733b978b0bbb36a2f9d756ea9f04e3c13d85573deb0d40948eafacdd568`.
Separate admission passed 15 static guards plus source/dependency/binary and
allocation/capacity controls before execution. A separate offline result
review verified hashes, execution order and all 14 samples; its SHA-256 is
`cf4ad02dc33f2990d2d8712b5387af539f71d9c34f3f018b8c29429140b95878`.

The first host admission aborted on an incorrect fixture assumption that
production closure releases all response string capacity. A distinct bounded
localization preserved the abort and identified that assertion. The corrected
synthetic control measures 4,097 retained requested bytes for an injected body;
explicit body release restores baseline. That release occurs only in the
control. Production source, firmware and the main workload close path remain
unchanged. All failed/corrected receipts and unique reservations are retained;
none may be blindly repeated.

This demonstrates a plateau in the selected empty-job portable host fixture,
without isolating Pico B's target cause or qualifying newlib/TLS/lwIP and the
active 512-event job lifetime. All processes are gone, all four locks are
available and the service is active. No device, RF, raw read, external archive
or sample release occurred. The subsequent attribution is recorded below.
Progress remains 3 of 9 original
workstreams (33.3%); estimated 15–37 hours remaining, subject to repair extension.

### Closed response-capacity attribution

The distinct twelve-GET host experiment attributes its whole 1,922-byte retained
step to two closed response bodies. Each retains 960 capacity bytes plus a
terminator allocation; releasing them individually reclaims 961 bytes and one
block each, returning to the construction baseline. Static root responses
preserve the previous dynamic body's capacity. Full fixture destruction returns
all tracked C++ bytes/blocks to zero. Thirteen static guards and a separate
source/dependency/binary admission passed before execution; prior completed
controls and the 1,600-GET experiment were not rerun.

Actual receipt `build/phase14-http-response-capacity-attribution-result-20261012.json`
has SHA-256 `89ec7137e28ca2793663f4aa07f9c24892d559ee9865ea809538d7dac7ec8df8`.
Separate offline verification checked all 29 samples, body capacities, path/count
order and individual release arithmetic; its SHA-256 is
`859d62c488b6ce7bd4483284637a114cdc385264a01aa09a482045a0bcf72435`.
The attribution coordinator and all children are gone, the service is active, and no
target, raw sample, RF, archive or removal action occurred.

Metadata-only inspection of the four B browser records shows different final
paths: capabilities, root, status and status. The last FSKCW status response
reports completion and one terminal record. These recorded differences and
the host attribution motivate a separate idle target path contrast, without
isolating B's allocator cause or accepting the failed comparison. Its bounded
six-GET plan is unimplemented and unqueued. Original flags, 1,024-byte limits,
source/image identity and the blocked qualifying memory follow-up are unchanged.

## October 11 amended mixed run started

The clean-image mixed qualification is running exactly once under coordinator
3233082/start 66510419, source `8538564583f1cb67ce9882755d2464e6b2297600`,
138 MHz image `d60985822da465b6840bf921f05eedff558e109beef0568115dda70f35916ab9`.
The actual output is
`/home/pi/phase14-qualification-20261008/build/resume-tools-8538564-clean-internal-first/build/amended-clean-mixed-20261011T193513/result.json`.
The 19:36 UTC snapshot showed the reference-before capture active, successful
parent/child ownership handoff and no error or published mixed observation.
It makes no whole-stage acceptance or capture-time credit claim.

The separate current coordinator review
`build/phase14-amended-mixed-owned-closeout-independent-review-20261011.json`,
SHA-256 `06ae722b410562e184f2db8e0fc8add6aad490582a797abcfa351697875e2f92`,
passed 43 Linux ownership/closeout/socket checks and actual current-image
prerequisite, settings, cursor, reference and browser readbacks. It accepts
the separately identified `4c1e50b0` coordinator for execution. The earlier
`9623fcac` entry remains unexecuted and superseded.

Full independent pre-release verification is closed: 2,014 source/archive
pairs, 41,826,678,767 bytes and 253 raw pairs, receipt
`build/phase14-clock-reserve-full-audit-complete-20261011.json`, SHA-256
`2d27bb6f2fb9bf2e77a50f47008d182f5eb3c1c7a1ae49949093b4d88baff06d`.
The finite duplicate-only release removed 24 eligible internal clock raws,
7.590 GB, with retrieval published on both filesystems and immediate full
hash/stat/user checks before each unlink. An independent review full-hashed
all 24 durable destinations and 1,758 distinct small companion pairs. A separately guarded
state-aware correction released one additional 312 MB duplicate to include
the unchanged eight GPSDO reference recordings in the storage budget. Its
independent final review full-hashed that destination and retained fresh
closeout controls. All durable samples and nonraw companions remain.

The actual cumulative release is 25 internal duplicates/7.902 GB. The final
review is `build/phase14-reference-inclusive-final-reserve-review-20261011.json`,
SHA-256 `4d4dff0dca9e616a6e9fd92e8532f7fa31a11576c4533f326058cf54da5541a8`.
Launch independently rechecked 69,384,732,672 bytes free against
69,185,418,240 bytes required: 58.32 GB mixed raw, 128 MB reference raw and
10 GiB reserve. The correction changes storage accounting, not the workload,
scientific criteria, old results or original copy-only flags.

No archive, release or later queue overlaps the active mixed acquisition.
The workflow owns the whole stage; child handoffs retain the inactive board
and reacquire all bench locks between children and during analysis. The owned
service restoration remains pending while testing runs. All SDR requests
retain bias-T disabled. Eight accepted job results and a separate independent
review are required before a separately identified memory follow-up. No
4 m/2 m RF, decoder or diagnosis is authorized for this release.

Progress remains 3 of 9 original workstreams (33.3%); the conservative estimate
is 15–37 hours, including 10.429444 hours of fixed mixed/memory work. No elapsed,
preparation, verification, duplicate-removal or active-job credit was applied.

## October 11 earlier mixed coordinator and reserve verification

The amended eight-hour mixed coordinator retains the byte-identical
`phase14_soak.py` and `phase14_reference.py` drivers, including all eight
one-hour jobs, B's browser workload and the original 45-second idle sampling.
A private Unix socket hands only the selected board and receiver locks to
the exact child PID/start/UID. The parent retains the inactive board and owns
all three bench locks between children and during analysis; the workflow lock
spans the complete stage. Firmware, WTP and scientific criteria are unchanged.

The separate execution review
`build/phase14-amended-mixed-execution-independent-review-20261011.json`,
SHA-256 `e6e931356b9d788705090e79b3d88c7e02a492318f02e058ac19ea1ecbe423c2`,
passed 40 Linux checks, including real socket/wrapper exchanges, constructor
failure and ordered lock handoffs. It also verified actual clean-image idle
boards, settings/cursors, GPSDO and authenticated B browser status. A later
closeout review found that checking immediately after SIGKILL could report
uncertainty before the child actually exited and omit the final failure receipt.
The separately identified successor
`4c1e50b05f966d6dda6f6d4e46774fbed3832289c718910d3fc5cf815a0e633a`
waits for registered own groups to exit and publishes failed closeout before
skipping device re-entry when cleanup remains uncertain. Its 34 isolated
ownership/cleanup checks pass, including a separate receiver-like child,
signal resistance and stale PID/start refusal. Its separate execution review
remains pending; the first coordinator has never run RF and is superseded.

The independently implemented reserve verifier passed 15 isolated removal
and retrieval failure checks and bound the actual two closed archive catalogs.
It is running only its `--verify` entry at
`build/clock-reserve-full-audit-20261011T184656/result.json` under the clean
internal tool root, PID 3218955/start 66220732, helper SHA-256
`0a9e1d49a1206993b7b2defd18585603cf7db664668b0eec2217afa419b91e2d`.
It independently full-hashes all 2,014 source/archive pairs, 41,826,678,767
bytes, including all 253 raw pairs and every companion. This new verification
is required before releasing duplicates for the demonstrated next-stage
shortage; it repeats no RF, decoder or scientific analysis. At the 18:52 UTC
snapshot it had verified 12.612 GB without error. All four locks remain owned;
no capture, raw transfer, sample removal or later queue is active.

Preserved preflight refusals caught the original copy-only receipt's intentional
zero release count and 49 legitimate zero-byte decoder stderr companions.
Separate successor readers corrected those assumptions without changing the
catalogs, thresholds or original flags. Eligibility is derived from the original
218-record full clock audit, excluding the separately retained A132 maximum job.
After verification closes, the coordinator successor needs its independent
review and a separately bound release-only successor before any removal or
mixed RF launch. Count and conservative ETA remain three of nine workstreams,
33.3%, and 15–37 hours; verification and preparation add no capture/transfer
credit. Final consumer API validation, mixed/memory qualification and release
closeout remain unfinished.

## October 11 clean installation and target admission

The clean experimental-frequency candidate is installed on both boards at
138 MHz, with exact revision `8538564583f1`. A source-bound independent
readback verified the retained settings, profiles, current cursors, inactive
outputs and restored service/GPSDO. Installation receipt
`build/phase14-clean-8538564-target-installation-20261011.json` has SHA-256
`a782880f7561f906974453208dccdcfd3cc566fc1c9eb25e9fc543e358384e58`;
independent review SHA-256 is
`b794756c0ff77383a4a6d01474a1c39924167e1d9730552a1d58fd2ad92a297b`.

The first build from the primary checkout embedded `8538564583f1-dirty`
because an unrelated retained documentation edit was present. Its initial
artifact review missed that exact compiled-identity distinction. The first
installation stopped on the identity guard after loading A; B was not loaded.
Failure receipt `3516fcca38a5d2478dfc84aa3e1c3a67091bab92f888eaf923cfe72db28340fb`
and all earlier artifacts remain unchanged. A separate clean managed checkout
of the exact source produced these replacements with the same pinned inputs:

| Clock | Clean UF2 SHA-256 |
| --- | --- |
| 132 MHz | `7c97b216a87ddf0c89d6705d8c0618b6da9ff0ae64b32983de254123db813071` |
| 138 MHz | `d60985822da465b6840bf921f05eedff558e109beef0568115dda70f35916ab9` |
| 150 MHz | `18af2e50391255d457e92e98ea4f2a6ed02ec444b479705c3b9daaa481256ec0` |

The independent 138 MHz ELF/UF2 rebuild is byte-identical. Build status
`33d2a1345f0c2b9bc67dbe5ced441083a25c1ac307b79d5046ed3a05daf537e0`
and independent review
`132040aa5f595c3b2edf46b7cb0082e8a1c356d76d7d2a1b772c11df4ac5baba`
bind exact generated revision, source and reserved-flash/stack/heap checks.
The new internal tool root is
`/home/pi/phase14-qualification-20261008/build/resume-tools-8538564-clean-internal-first`;
its 1,825 source/artifact files were independently verified. No SDK/tool
installation or native helper rebuild occurred.

Seventeen actual unarmed LOAD checks passed: three default-admission checks
on A, and fourteen combination, numeric-limit, reboot-persistence and restored
default checks on B. Every accepted LOAD was aborted/released without ARM.
B's original configuration was restored and its profile/current 8 KiB cursor
were independently verified byte-identical. Actual result
`dd86f752d012bb7c6369eb14c09289420ec68ab2391bd7d012b87be24ca9717a`
and independent review
`231c0d6c856191279d41d66846f857758b75ba2741cbab7478210911a7c51a8e`
are retained in the new tool root and locally in the corresponding
`build/phase14-frequency-profile-aware-target-*` receipts.

A's consumer Console intentionally rejects CONFIG with
`profile_runtime_unavailable`; the initial target plan stopped before any LOAD
or accepted configuration change. Its full 32 KiB profile/configuration/cursor
snapshot remained byte-identical, independently verified in receipt
`b06deb0753f66ee30a411ed2473342d36898d05005ca37229a01bf07eeec9b55`.
The profile-aware successor used B's engineering CONFIG interface. A's consumer
settings API opt-in path remains unverified; Console refusal is not a failed
frequency-policy test. Original failed receipts and reservations remain intact.

Four separately bounded current-image 80 m baselines are closed and
independently accepted: A/B five-second Tone and one nominal WSPR frame each,
at 138 MHz. Both external decoders returned `AA0NT EM18 37`; Tone/resource
checks pass and receiver overflow/clipping are zero. The full independent
824 MB raw/control/resource/decoder review has SHA-256
`f5c68e209c58b99332c699f5d74db67a50c3044c7aa7a040d32287856f11a4c2`;
actual stage SHA-256 is
`1ed59102a4d9addb234001e9183d4c2014649f069a9345bf0bb6a149f71a7dcc`.
The original WSPR legacy analysis flags remain false; external expected-message
acceptance is recorded separately under the unchanged informational
frequency/drift policy. All four captures explicitly disable SDRplay bias-T,
and their actual metadata confirms `bias_tee:false`. Both boards remain clean
138 MHz, empty/unowned/inactive/disabled, with settings/cursors/GPSDO and owned
service restored. No excluded-band trial or decoder rerun occurred.

A separate amended mixed prerequisite review binds the accepted historical
finite gates under their actual e953 identities, current-image baseline/flag
proofs, source applicability and the operator's all-mode upper-band exclusion.
It replaces the old positive 4 m prerequisite without claiming a 4 m pass.
Receipt `f9e0043ceb909f055892a5c49e9796c7a28d1b2d156bd1475c1d38f37035d568`
measured a 7,571,194,880-byte shortage for the 58.32 GB mixed captures plus
10 GiB reserve. A separately reviewed execution/ownership adapter and guarded
state-aware reserve release are still needed. No long stage or raw release is
queued; the old ed93 entries remain superseded. The accepted additional
412 baseline seconds do not reduce the fixed remaining mixed/memory workload.
Long reliability, final consumer/API checks, retained-band closeout, final
review and push remain. Only three of nine original workstreams are closed.

The [band/clock/mode table](phase14-band-mode-qualification.md) records accepted
historical RF evidence with average A/B received relative carrier power. Those
power values include receiver/path response and are not calibrated transmitter
power; no historical capture is relabeled as this new image.

## October 11 experimental frequency controls

The application source now implements WsprryPi-compatible, persisted,
default-off `allow_unqualified_frequency` and `allow_non_amateur_frequency`
settings. Failed/untested amateur bands require the first; frequencies outside
the recognized correlation catalog require both. Every normal job source uses
the same guarded engine preparation, including RF-on mark/space events and
realized adjustments. Numeric limits and WTP ownership/time/safety remain
authoritative. The existing all-mode 4 m/2 m exclusion is unchanged; opt-in is
experimental permission, not qualification. Configuration details are in the
[standalone guide](standalone.md).

An isolated wspr5 Linux build passed eleven targeted CTest groups covering
frequency policy, standalone/configuration/journals, browser/network/application
resources, provisioning/reset/consumer storage and the portable WTP core.
A second build with autonomous WSPR base `40000100` Hz passed the policy test,
including default refusal, subsequent explicit consent and no repetition of a
reserved rejected occurrence. Browser behavior, WTP contract validation and
the existing standalone image/Console source checks also passed. The original
test-initializer, request-digest and spy-counter failures remain in the private
build logs; they were corrected in the test fixture without changing production
thresholds or RF algorithms. Source hashes and final results are recorded in
`build/phase14-experimental-frequency-validation-20261011.json`.

The initial validation receipt records source/host checks before any firmware
build or installation. Its Linux inventory found SDK 2.3.0 and no Arm compiler;
that inventory does not describe the retained pinned tools on the Mac. The
original Phase 14 task authorizes Pico firmware cross-builds with those inputs.
No SDK or tool installation was needed.

Source `8538564583f1cb67ce9882755d2464e6b2297600` has now built at all three
clocks with retained SDK 2.3.1 and Arm GNU 15.3.1. Existing native pioasm and
picotool binaries were imported without rebuilding them. An independent 138 MHz
build produced byte-identical ELF and UF2 files. These historical first-build
UF2 hashes embed the dirty revision described above and are superseded for
installation by the clean replacements:

| Clock | SHA-256 |
| --- | --- |
| 132 MHz | `8bfb652396b369fcb902bc08bed844b477f9b37c4a05c6c35d7b037906ee3127` |
| 138 MHz | `6fe71e3f51b4c7ce3dccce49fee91299c899fe9f9411886c289b807e23005950` |
| 150 MHz | `c27eb773b794ae97d0f16a6b68785baf3f567d5251f7b791af59ed4c2ab47add` |

The finite build status is
`build/phase14-experimental-frequency-arm-candidates-20261011T1623/status.json`,
SHA-256 `e33e366659616d47833fde0afa2213cecc555784496796bb98c2ada5d3e127a6`.
Independent artifact/source/layout review is
`build/phase14-experimental-frequency-arm-artifact-independent-review-20261011.json`,
SHA-256 `46cc9f4ef436bc66ac93c93d23d23041b5db251d132382d5737db68bd89610bd`.
All four ELF/UF2 sets passed the existing stack, heap, worker and reserved-flash
checks. The source applicability review,
`build/phase14-experimental-frequency-source-applicability-review-20261011.json`,
SHA-256 `06a802583e78c6ff45141ca92e3969affaed8b1760fab8698176cfd3de44da86`,
retains unchanged RF, encoding, clock and WTP evidence under its original
identities. It does not qualify the new admission boundary or linked image.

At that initial build checkpoint, no new RF, receiver/decoder trial, firmware
installation or sample transfer had occurred. Both boards then retained their
actual `e95334a` RC3 images. The later clean installation and target checks are
recorded above; current-image reliability/final installation remain. The old mixed/memory entry remains superseded and must
not run as-is. Builds and reviews add no capture credit or workstream closure.

## October 11 upper-band diagnosis and operator exclusion

The operator amended the release decision: when required WSPR decoding fails
without a fault preventing synthesis, exclude 4 m and 2 m for **all modes**.
Both bands are now `UNSUPPORTED_RELEASE` for Tone, WSPR, QRSS, FSKCW and DFCW,
on A/B and across the three candidate clocks. The authoritative coverage is
[phase14-band-support.json](phase14-band-support.json). This supersedes the
earlier mandatory 4 m repetition and conditional 2 m expansion requirements;
no further upper-band diagnosis or native harmonic mapping is required.
The independent support-scope review is
`build/phase14-upper-band-support-independent-scope-review-20261011.json`,
SHA-256 `0256bc692acdb0b82d993f367a67e266b889d8ae48ecae017d972058d988a946`.
The decision and five small evidence receipts are durably retained at
`build/upper-band-support-amendment-20261011` under the current wspr5 tool root.

A separate check of the two failed 4 m repetitions and both original 2 m
pilots verified complete 162-symbol synthesis, four distinct accepted RF states,
same-job/boot natural completion and inactive output. Stack/fault/allocation/
refill records show no fault preventing synthesis; resources pass and receiver
overflow/clipping are zero. The expected-message decoder outcomes remain false.
Receipt `build/phase14-upper-band-synthesis-fault-review-20261011.json` has
SHA-256 `6dea07c6d5b8a15d853e2a1cb0bbeb3110e941cf1248dea754803842d808d1f8`.
The retained 2 m captures keep their actual `119477a9c8c8` identities and the
existing source-applicability review; they are not relabeled RC3.

The diagnosis found carrier movement rather than collapsed tone states.
Independent fits to received steps give approximately the accepted separation
at both bands. In representative failed B frames, state-removed carrier spans
are 11.447 Hz at 4 m and 19.175 Hz at 2 m; simultaneous-reference spans are
2.083/2.891 Hz, leaving 9.364/16.286 Hz movement relative to the GPSDO. Existing
five-second constant-carrier observations also show relative movement, so it
does not require WSPR tone switching. These remain informational measurements;
they do not select calibration or isolate crystal, PLL or thermal origin.

Exactly four separate ideal-audio decoder controls are closed: at each band,
the steady-carrier version decoded `AA0NT EM18 37`, while the otherwise-identical
version following the measured common-carrier trajectory did not. Thus measured
movement alone suffices to defeat this installed decoder in the model. This is
software diagnostic evidence, not an accepted decode of the failed recordings.
No new RF, IQ read, retained-audio edit or transmitter/receiver/time/drift/sample
correction occurred. The actual terminal receipt has SHA-256
`9447089103621853a3638aeba7e7032fdbd91336bcb8bdd4123eeb2de57608ba`;
its separate independent review is
`build/phase14-upper-band-synthetic-independent-review-v2-20261011.json`,
SHA-256 `59463f0c9a1fff724d0cc5512807791f76d1511b1c5f71e3fe39b54889bdb1e4`.
All children are gone, originals remain unchanged and both boards/settings/
cursors/GPSDO were independently checked at idle RC3/138 MHz. The controls and
their reservation must not run again. The initial independent reviewer refusal
at an alternate floating-point symbol-boundary formula is preserved; the
corrected reader verifies the exact recorded convention without changing audio.

Some retained 4 m frames and keyed observations passed; they retain those
outcomes. The new all-mode release exclusion does not claim synthesis is
mathematically impossible or rewrite any flag. Direct 2 m remains outside the
NCO range, while the observed third-harmonic states remain distinct. The old
mixed/memory entry must not run as-is: prepare separately reviewed admission
that binds this operator exclusion instead of demanding positive 4 m evidence.
Storage reserve, remaining-band criteria, reliability and final audits/install/
review/push still apply. No long queue or redundant raw release is armed, and
the scope disposition alone closes no additional original workstream.

## October 11 14:28 UTC checkpoint

One separately identified decoder diagnostic on the closed normal-connection
A frame is complete and independently verified, with no expected-message
decode. Inspection of the exact installed Debian WSJT-X 2.7.0 package payload
and its source confirmed that `wsprd -w` widens the carrier search from
±110 Hz to ±150 Hz. Existing A estimates motivated this one trial; B received
no additional trial. The diagnostic used A's byte-identical nominal audio and
original 5.07-second start/120-second window, adding only `-w` to the original
command. It read no IQ and acquired no new RF. Transmitter, receiver tuning,
time, drift, samples, waveform and settings remained unchanged.

The helper and decoder have ended. The actual receipt is
`build/phase14-closed-action-A-wide-search-result-20261011.json`, SHA-256
`306ed02adbcb66b5275a734dc7c22ac3502f07cba449ab66dad1f62200194bf4`.
The independent negative review is
`build/phase14-closed-action-A-wide-search-independent-review-20261011.json`,
SHA-256 `d6e86b13aff311cf72f27ce08387865a7c89cddf92e6db7b09d5f8ea6e18c34d`.
It verifies unchanged original audio/control/metadata/resource/receiver and
raw identities, plus restored boards/settings/reference state. Widening this
search alone did not resolve A's decode. No cause, calibration, mode acceptance
or capture credit follows; original failed flags remain unchanged. This trial
must not be repeated or followed by blind decoder-option loops.

The accepted post-clock Tone evidence is now durably archived: 26 Tone raws
(2.6 GB), eight closed GPSDO reference raws (128 MB) and all companions,
288 files/2,739,943,875 bytes in total. The archive also includes the clock
copy's full closeout controls and this copy's own full closeout controls.
Its location is
`/mnt/phase14-testing/phase14-closed-internal-first/post-tone-rc3-1791728421022595521`.
The copy receipt and identical durable retrieval record have SHA-256
`b4f46fe8689731f9dcffe5f9301575ac447e454d11d71885dbb2ca6a2cc3b00d`.
The separate full source-and-destination review is
`build/phase14-closed-tone-copy-independent-review-20261011.json`, SHA-256
`77b7340d1052af48ec0ad86d1bd74211751c95d648a7a53168663c6130f9a6a3`.
All internal originals remain; no source bytes were removed. Copy and review
processes are closed, and their entries must not be repeated.

Fresh process/four-lock/UUID checks found no active campaign or later queue.
Both boards are idle at RC3/138 MHz with settings, current cursors and GPSDO
restored. The actual 2.6 GB Tone transfer receives credit once; the eight
reference companions remain within the existing retention allowance and add
no capture credit. Pending core transfer is now only the unrecorded 72.9 GB.
Three of nine original workstreams remain closed (33.3%); the estimate remains
15–37 hours. Four-metre and physical 2 m decoding still block qualification,
and mixed/memory reliability remains unqueued. No raw release is due while
the required 4 m acceptance remains unresolved.

## October 11 13:27 UTC checkpoint

The connection-action comparison and its independent audit are now closed,
with both expected-message decodes false. The B-only continuation retained
already audited A and acquired only the missing B frame. Both recordings pass
resources and receiver integrity with zero overflow/clipping. The exact
coordinator, acquisition/analysis children and independent auditor have ended;
both boards returned to RC3/138 MHz with settings, current cursors and GPSDO
restored. The actual terminal receipt is
`build/phase14-action-b-prefix-recovery-closed-result-20261011.json`, SHA-256
`035441f921713b5523381665a34350ddf535e0bdc65e2bd9562ad63485063d9f`.

The independent audit full-hashed only B's new 312 MB and reused A's completed
312 MB independent hash with unchanged exact file identities. It verified
624 MB in total, actual source/image/boot/job/control/metadata, decoder stdout/
audio, unchanged 13 resource samples per frame, receiver and restored state.
Its receipt is
`build/phase14-action-prefix-independent-closed-audit-20261011.json`, SHA-256
`650c20dd93ecbdd22b4856afb7864a9238e031577fab3071cda829e9c0b7b90e`.
Original failed stages, nominal flags and earlier diagnostics remain unchanged.
Neither the comparison nor its audit may be repeated.

Keeping the normal connection after minimum 350-second idle did not resolve
either expected decode. A separate read-only summary binds existing symbol
estimates and the unchanged converter/decoder commands; it reads no IQ and
runs no new decoder or RF trial. Its placement/drift estimates remain
informational and establish no transmitter, receiver, thermal or waveform
cause, calibration, correction or band exclusion. Four-metre repetition and
physical 2 m decoding remain unresolved; mixed and memory reliability are
unqueued and still require actual accepted finite prerequisites.

Fresh closure checks found no active campaign process and all four locks
available, with the actual internal/external UUIDs and devices 66306/2049.
All internal samples remain. The two comparison raws add 624 MB to finite
retention once, now 19.288 GB inside the existing allowance; they receive no
capture or mode-acceptance credit. The closed-clock transfer credit remains
unchanged. Three of nine original workstreams remain closed (33.3%); estimated
remaining time is 15–37 hours, with upper-band diagnosis able to extend it.

## October 11 13:11 UTC checkpoint

The connection-action comparison ended after A's acquisition and analysis.
Its host evidence reader required the final job-filtered INFO sample to equal
physical after-INFO. Natural completion had cleared `job_id`, so the unchanged
analyzer appended that final INFO separately. The reader rejected that layout;
its original failed status, zero published observations and every original
flag remain unchanged. The exact coordinator and children ended, and both
boards returned to RC3/138 MHz with settings, current cursors and GPSDO restored.
The saved failure is
`build/phase14-four-metre-connection-action-failed-result-20261011.json`, SHA-256
`011221633e1206b62c60fa05c86da8be1961e54d99f6a3a3e6d488e48f2b3886`.

A separate reader now matches the unchanged analyzer's original sample count,
ordered job/boot/clock-bound INFO prefix and separately appended after-INFO.
Resource and scientific thresholds remain unchanged. An independent closed
boundary audit full-hashed A's unchanged 312 MB and checked its actual control,
metadata, source/image/boot/job, 13 resource samples, receiver, decoder stdout
and audio, plus live restored settings/reference state. A's expected-message
decode is false; resources pass with zero receiver overflow/clipping. The audit
and its process have ended. Its receipt is
`build/phase14-action-a-prefix-independent-audit-20261011.json`, SHA-256
`b0094111e10601e62f91c40331e5d9bf9aaf85c8c509cc2655a1479cc080b520`.
This supplies integrity reuse, with no mode acceptance or capture credit.

After fresh process, four-lock, UUID and reserve checks, the separately
identified B-only continuation `a097f0b0` was dispatched once as
PID 3123957/start ticks 64186195. It retains audited A and acquires only the
missing B comparison: one unchanged 156-second WSPR capture after a fresh
150 MHz boot and at least 350 seconds idle, with the normal connection retained.
At the snapshot B is still settling, no new observation is closed, and the
single published observation is retained A with its false decode. The receipt
is `build/phase14-action-b-prefix-recovery-live-20261011T1311.json`, SHA-256
`07ae760e772ac74dca2b6c748a77376a906f1153c983df00e17f724127c205dd`.
There is no firmware, waveform, calibration or acceptance change, and no
external transfer, raw release or automatic later queue.

Thirty-three prefix guards and 33 continuation guards pass, with five actual
closed layouts checked. A separate recovered-comparison audit is staged with
32 refusal checks; its BUSY probe rejected the active workflow before sample
or device access. Its positive path remains unexecuted. It requires actual
continuation closure, matching hashes, ended processes and restored state;
it reuses A's completed full audit and independently hashes only B's new
312 MB. The earlier `39fa6bbe` audit is superseded and must not be invoked
against the failed original comparison. None of these integrity checks
accepts the 4 m repetition or disconnect-reliability gate.

Three of nine original workstreams remain closed (33.3%); the estimate remains
15–37 hours. A adds 312 MB of closed finite evidence to pending retention once,
inside the existing allowance, with no completion credit. The verified
38.720 GB clock transfer credit is unchanged. The 4 m failures, physical 2 m
decoding, long reliability and final release work remain unresolved; further
repairs can extend the estimate.

## October 11 12:49 UTC checkpoint

The closed-clock archive is now independently verified and its exact copy
process has ended. It retains 219 raw recordings/38.720 GB and their companions,
1,726 files/39,086,734,892 bytes in total, at
`/mnt/phase14-testing/phase14-closed-internal-first/clock-rc3-1791719809192454023`.
The successful status and identical durable retrieval receipt both have SHA-256
`44efa33e035f255ac928afebc9e635ce41dc25fd31a1bd949b0dc17ee4bdf132`.
Every internal original remains; no source bytes were removed.

The separate closure reader verified the retrieval bytes, all retained source
identities and 1,507 small companion hashes/366,734,892 bytes, reusing the actual
copy's full raw hashes. Its receipt is
`build/phase14-clock-copy-independent-closure-review-v3-20261011T1245.json`.
Two preceding read-only reader failures are preserved: the copy receipt uses a
compact inventory summary, and WTP STATUS does not contain the scheduler's
`enabled` field. The corrected reader binds the summary to full stored INFO and
WTP boot/owner/output records, and checks disabled configuration in INFO. The
successful archive and all original qualification flags were unchanged.

Fresh process, lock, UUID and reserve checks then passed. The separately
identified two-slot connection-action comparison was dispatched once as
PID 3117468/start ticks 64055343, helper `e2fbfb31`. A is in its fresh 150 MHz,
minimum 350-second idle period; no observation was closed at the snapshot.
Its receipt is
`build/phase14-four-metre-connection-action-live-20261011T1247.json`, SHA-256
`9e57c3d4a1758c49a8b9466cc8aedd0cb8d7abb42c84696ef3894df9c4ad74e7`.
This comparison changes only the connection action described below and retains
the two original failed slots, waveform, receiver settings and decoder. It
must not be duplicated or automatically promoted to 4 m acceptance. No archive,
source removal or later queue overlaps the active workflow.

An independent closed-comparison audit is separately prepared and unqueued.
Thirty isolated Linux refusal checks pass, including rejection of false decode
promotion; its actual positive path remains unexecuted. The audit requires the
actual comparison terminal/hash, ended processes, full new raw/control/decoder/
resource bindings and restored board/settings/reference state. Neither a
diagnostic terminal nor an audit template accepts the 4 m release gate.

Only three of nine original workstreams are closed (33.3%). Crediting the
actually completed clock transfer once leaves 75.5 GB of core transfer. The
estimate is still 15–37 hours: its optimistic transfer rate uses the earlier
verified small copy, while its conservative rate now uses twice the measured
2,604.05-second large-clock copy per 38.720 GB of raw, including companion and
verification overhead. No failed settling, unaccepted repetition or active
comparison capture receives completion credit; no elapsed time is subtracted.
Physical 2 m decoding, reliability and final release gates remain open.

## October 11 12:18 UTC checkpoint

Three of nine original workstreams remain complete (33.3%); the estimate is
15–37 hours. The two-slot 4 m idle-settling diagnostic closed with complete
recordings, passing resources and zero receiver overflow/clipping, but neither
new frame decoded the expected message. Holding each fresh 150 MHz boot idle
for at least 350 seconds did not resolve those decoding failures. Both boards
returned to RC3/138 MHz with settings, current cursors and GPSDO state restored.
The actual terminal receipt is
`build/phase14-four-metre-idle-settling-closed-result-20261011.json`, SHA-256
`0db0afc909553473fd02fabd97ddae7b074c08cc64f3f77ae107d98ba9df1e40`.

A separate closed-boundary audit independently full-hashed the two recordings,
624,000,000 bytes, and verified their unchanged source, control, metadata,
decoder, audio, resource and receiver bindings. Its receipt is
`build/phase14-idle-settling-closed-audit-20261011.json`, SHA-256
`c35d03b097ee7b210addc6a074c04b1b82359492b873ff117e12b5a0f7c04a52`.
The diagnostic and auditor have ended. Both new mode results remain unaccepted;
the original repetition failures and all earlier retune/OSD results are
unchanged. Neither these 312 diagnostic seconds nor the unaccepted 1,512-second
4 m repetition gate receives completion credit. Physical 2 m decoding also
remains unresolved; no transmitter cause or calibration has been selected.

After that audit and every acquisition/analysis process ended, the copy-only
closed-clock helper `7b0e63a0` was dispatched once. Coordinator PID 3103666,
start ticks 63759990, is copying the 219 closed clock recordings/38.720 GB and
all required companions to the external SSD while retaining every internal
original. At the latest small checkpoint, 192 entries/33.468 GB had independent
destination and unchanged-source verification, with no errors or removals.
Whole-archive verification and durable retrieval remain pending; partial copy
progress receives no transfer credit. The actual active receipt is
`build/phase14-clock-companion-copy-live-20261011T1218.json`, SHA-256
`89068a4f928bdcb6dbe5afc46dc88749a694d9fdc2d1fafef1ba33d7e310f198`.
No RF acquisition or sample analysis overlaps this copy.

A separately identified two-slot connection-action comparison is staged and
unqueued. It keeps the same fresh 150 MHz boot, minimum 350-second idle period,
WSPR job, receiver settings and nominal decoder, while maintaining the normal
connection/lease renewals instead of disconnecting. Thirty-six new refusal
guards pass; its probe refused the active archive lock before device access.
Preparation is recorded in
`build/phase14-four-metre-connection-action-staging-20261011.json`, SHA-256
`3ef38633fab5c9a9db0b837a4d4f28dbad93c4d823fad2802d5f8dd466277ab8`.
Positive execution is unvalidated and requires the actual successful archive
receipt, retrieval hash, ended process and fresh quiet-boundary checks. It is
bounded to two original failed slots, 312 capture seconds and 624 MB. Even a
positive comparison would require separate review before accepting the 4 m
disconnect/reliability gate. No long reliability queue or raw release is armed.

## October 11 11:25 UTC checkpoint

Three of nine original workstreams remain complete (33.3%). The nineteen-job
RC3 native producer/max-message gate is now independently accepted, including
all actual control, raw, decoder, resource and restoration bindings. Its 4,985
capture seconds are credited once within the existing other-work allowance.
The estimate is 15–37 hours; unresolved 4 m and physical 2 m decoding and the
remaining reliability, audit, installation, review and push gates can extend it.

One separately bounded settling diagnostic is active on the two failed 4 m
slots. It holds each freshly loaded 150 MHz board idle for at least 350 seconds,
then takes one unchanged WSPR job per board. No diagnostic observation was
closed at the recorded checkpoint. Original failures remain immutable; this
diagnostic cannot automatically accept the 4 m gate or launch reliability work.
No current clock, Tone or finite-stage raw bytes have been archived or removed.

## INFO allocation repair and closed raw audit

Fresh October 10 USB readback identifies A's stopped contention recovery boot
at source `119477a9c8c8`/132 MHz. Its saved fault record reports stage 5,
allocation panic hash `3833354787`, a null 16,385-byte allocation and disabled
network service. The preserved event log ends with `INFO` immediately after
the 512-event job was armed. B remains empty, unowned and reachable at 138 MHz.
The old timeout, missing terminal receipt, incomplete recording and failed
stage remain unchanged. The private diagnosis is
`build/phase14-info-allocation-diagnosis-20261010.json`.

The old INFO suffix deterministically reproduces a doubled allocation when
its 8 KiB string grows under a constrained host allocator. The source repair
retains complete INFO bytes in checked 4 KiB pages and drains them through the
existing 64-byte USB writes. A page-allocation failure returns
`diagnostic_unavailable` through an allocation-free literal rather than
publishing a partial JSON response. WTP limits, job ownership, the 32 KiB
authority reserve, RF workload and 100-us Worker acknowledgement bound are
unchanged. Tests cover exact bytes across page boundaries, blocked writes,
failed page allocation, reset/release and the unchanged 65,536-byte reply limit.
The saved allocation size and source regression support this diagnosis; the
exact failing caller address was not retained. This finding does not isolate
receiver overflow causation.

Source `e95334aa56d816b31a62255b980b540b849cf6ff` includes the repair and
the subsequently cross-compiled character-field append fix. All 160 configured
Linux test groups pass cumulatively; the original environment failures and
their identified Git-history, temporary-directory and retained-JavaScript
dependency reruns remain recorded. The affected INFO/USB checks pass again
after the character-field fix. No dependency was installed. The candidate
build uses the retained, hash-checked native picotool/pioasm binaries with the
existing pinned Arm toolchain and SDK; the failed default native-tool rebuild
and earlier character-field compile attempt remain historical failures.

The new ordinary RC3 UF2 hashes are:

- 132 MHz: `979bc9c5354a141f7909170d20573afea6194809c01404ce9ad2beb3f687b3ee`
- 138 MHz: `f8b21a53924bb90de0ea00a5b910e487c8f4cc14cf715041bd95c5e29af23f43`
- 150 MHz: `3c876431da087fa8107cf40f8b9afad9af666b339cab1cf1e03fb176c08dda7f`

The independently rebuilt 138 MHz UF2 is byte-identical. Manifest SHA-256 is
`133b3d47dcba2f0dc109cf46314d0a2362192c7ec7778bbc26c2a82d9569afe5`.
The separately staged root
`/home/pi/phase14-qualification-20261008/build/resume-tools-e95334a-internal-first`
has 1813 independently verified source files and all three verified images.
Its build directory is on the internal NVMe UUID
`ed6c7f1b-238b-41a1-b4b6-7bcdef3270fe`, distinct from the external SSD.

The first finite target attempt completed A/132 MHz/80 m/512-event FSKCW,
job `bfab86e1ae7236083b0fe286ac369ea3`, with accepted human-copy and resource
checks and no receiver overflow/clipping. The original legacy screen flag
remains. Both-board WTP inventory then succeeded, but the private helper's
filename construction raised `TypeError` before the four baselines. Its
`FAILED_EVIDENCE_PRESERVED` receipt remains unchanged, SHA-256
`774856500dad7f6b1fb3a71a246e56250e8e97a19df14a757026cdeb87194c9c`.
The GPSDO was restored, the helper ended, and the accepted physical job was
full-hash reverified. A separately identified four-job continuation runs only
the missing both-board Tone/WSPR baselines, preserving that original failure
and the accepted first job. That continuation closed all four jobs: both Tone
screens and both expected-message WSPR decodes meet operator/resource criteria,
with zero overflow/clipping. Both new-image boards are empty/unowned/disabled
at 138 MHz, and independent GPSDO readback matches restoration. All five raw
files, 1,170,000,000 bytes, and actual decoder/control/analysis/inventory bindings
were independently reverified in
`build/phase14-info-repair-target-reconciliation-20261010.json`, SHA-256
`2b76025e3d465709a1c96fb0229e84b9b32adecc2aa7e1f9846db21d11c42bdf`.

At a verified quiet boundary, the separately identified `b9fa1aec` auditor
completed full-stream hashing of all 338 closed repaired main/pre-clock Tone/
supplemental 6 m captures: 61,568,000,000 bytes in 174.98 seconds. Every full raw
hash/size and unchanged metadata, physical and analysis binding matched;
symlinks and unstable source identities were rejected. Its result is
`FULL_CLOSED_RAW_CONTENT_AUDIT_COMPLETE`, local receipt
`build/phase14-closed-main-full-raw-audit-20261010.json`, SHA-256
`875ed168c2b4141c51226c08444eda9d005be82f5fc1f40df5c812dae7ab256e`.
No raw file or original result was changed or removed. This closes that audit
scope; later reliability and final release audits remain.

A separate quiet-boundary audit full-stream hashed the 55 accepted historical
clock recordings, 8,888,000,000 bytes, in 225.80 seconds. Every original
raw/metadata/physical/analysis binding matched. Its local receipt is
`build/phase14-55-clock-full-raw-audit-20261010.json`, SHA-256
`f3097e985b023be511aa0925473dcd3f88791d6a205743ef07426b80d6d32ad0`.
Those observations remain bound to source `119477a9c8c8` and its actual
132 MHz image/boot identities. The review identifies 232 unchanged compiled
inputs; only INFO construction and USB reply retention changed. Reviewed reuse
is limited to unchanged ordinary RF algorithms, with changed diagnostics,
contention, resources, long reliability and final installation requalified on
the new image. Neither the old failed rows nor their source identities are
rewritten. The reviewed applicability receipt is
`build/phase14-info-repair-source-applicability-reviewed-20261010.json`, SHA-256
`60edde42f2fa490a0521529a67d0467b236c3bed08e23b05709bc17517413ab8`.
It does not promote historical long-soak/memory resources to new-image evidence.

The first internal-first recovery fully rebound the 55 retained rows, then
rejected an unnecessary B consumer-to-engineering conversion. B already had
its engineering journal, source 1/generation 4. The profile tool rejected before
writing, retained its exact 32 KiB read and rebooted B; fresh WTP inventory
confirmed both new-image boards healthy, idle and at 138 MHz. That failed
preflight started no new RF and remains `FAILED_INTERNAL_CLOCK_EVIDENCE_PRESERVED`,
status SHA-256 `5104841618f5a104b2522d21f10425e84e27569ed1e9c9553b00eed7a9aaf4ef`.

A separately guarded continuation uses B's existing engineering profile and
rechecks its identity-bound authenticated browser before acquisition. It repeats
only 215 missing ordinary physical slots and three remaining contention jobs,
retaining the accepted new-image A/132 MHz/512-event job separately. All 300
logical rows keep explicit old/new source/image/boot identities; unsupported
labels do not establish negative LOAD checks. It uses the unchanged receiver
and scientific workloads, a 43,200-second bound, preserved settings/current
cursor, and final return to 138 MHz. Its helper SHA-256 is
`6367f622111f64bd392648e85146768ac7c6f1434c165df1742874a9a88a2697`;
PID 2886637/start ticks 58849933 was dispatched once at October 10 22:18:28 UTC.
Status/rows live under the new root's `build/internal-clock-profile-recovered-state/`
and `build/internal-clock-profile-recovered/`. The browser preflight passed and
the first replacement capture completed with verified receiver integrity;
analysis/overall campaign closure remain pending. No later Tone/soak queue is
running. New source-bound reliability, upper-band investigation, remaining
finite checks, final audits/installation/profile restoration/review/push remain
open.

At October 10 22:37 UTC, the unchanged internal clock continuation has 63
closed, accepted ordinary observations: 55 retained with their original
source/image identities and eight new RC3 observations. The eight replacement
captures have valid control, metadata, resource and receiver-integrity records;
the three WSPR jobs also bind actual expected-message decoder stdout and audio.
No new receiver overflow, control error or resource failure is recorded. Their
new full raw-stream audit remains a closure task; this checkpoint checks
finalized size/hash receipts and small records without reading active samples.

The separately prepared internal-storage follow-on helper is staged under
the RC3 root as `build/phase14-internal-followons-5657e98c.py`, SHA-256
`5657e98c5edf939f021f6610018119943fecdbc3b29bf19daf21375801fd67e0`.
It offers three separate finite executions: 26 post-clock Tone/close-in jobs,
eight mixed one-hour jobs, and the two-job memory follow-up. All 34 Linux
closure/evidence rejection checks pass, all twelve pinned tool hashes match,
and each staged probe reports BUSY before device access. Preparation receipt
`build/phase14-internal-followon-preparation-20261010.json` records zero RF
jobs and no queue. The helper requires the actual predecessor to end, internal
NVMe identity/reserve, qualified analyzer runtime and a separately reviewed
reconciliation receipt binding actual control/metadata/analysis/decoder records.
The mixed soak additionally requires the remaining finite gates reconciled.
Memory acquisition explicitly passes source `e95334aa56d816b31a62255b980b540b849cf6ff`;
its original and cache-expired growth assessments remain separate. All live
recordings stay internal; closed transfer remains a separate quiet-boundary
operation. B's existing engineering profile stays available for browser load;
final consumer-profile restoration still preserves its current 8 KiB cursor.
None of these prepared executions has started.

At October 10 23:55 UTC, the same coordinator has 116 closed logical rows,
including 10 unsupported labels and 106 accepted ordinary physical observations:
55 retained and 51 RC3 captures. The 51 new captures have zero overflows or
clipping, accepted mode/resource records, and actual decoder bindings for WSPR.
All ten unusable original A/132 MHz overflow slots now have separate accepted
replacements; their original failures remain unchanged. Three contention jobs,
the remaining ordinary clock slots and final return/inventory remain pending.

Review of the prepared admission helper found that NaN quality values could
evade numeric comparisons. The separately identified successor rejects
nonfinite Tone coherence/amplitude/reference values and a missing expected
reference, retaining the existing thresholds and informational placement/drift
policy. All 41 admission checks pass. Decisions match all 21 closed Tone reports
checked; no original report or running clock criterion changed. Use the staged
successor `build/phase14-internal-followons-ed93f302.py`, SHA-256
`ed93f302dac44d74891ad26347e12a14d2274e78abd54adc747d96045dde4025`.
The earlier `5657e98c` helper remains preserved and superseded for future runs.

Two additional finite helpers are staged and unexecuted. The closure auditor,
`build/phase14-clock-closure-audit-1db6c8c5.py`, SHA-256
`1db6c8c5797862a145685af3b5728792952784b1c7d24348358ce2219696d95f`,
requires successful 300-row clock closure, its process gone and all bench locks.
It full-stream hashes the 218 newly produced captures, 38,374,000,000 bytes,
reuses the completed full-hash receipts for 55 old jobs and the accepted new
maximum-event job, independently recomputes resources from actual INFO events,
and binds all 274 physical jobs. A positive next-stage reconciliation is
published only after decoder/quality/integrity checks and actual final idle
inventory. Closure or planning alone does not establish that result.

The closed-retention helper, `build/phase14-closed-clock-retention-d54a18f6.py`,
SHA-256 `d54a18f63215f22c3ebaf25618a7f490937da4366b30993bff7d1e7d3dec9774`,
separately copies audited closed clock evidence to the external SSD with full
destination and unchanged-source verification and durable retrieval records.
Its optional redundant-raw release is a separate invocation: it requires an
actual successful copy, a demonstrated next-stage reserve shortage, immediate
full archive/source rechecks, unchanged small companions and durable location
records before unlinking only eligible redundant raw files. Partial/unknown
outcomes retain recovery locations and require inspection before retry. Both
helpers pass 18 Linux guard checks; all staged probes stop at the active bench
lock. No current campaign audit, transfer or removal has run. The exact small
preparation receipt is `build/phase14-finite-quality-and-retention-preparation-20261010.json`,
SHA-256 `ccc5d7202a47edbab91f2ca8d88f52d2815f8e341388217a19d5c9cc53bd44fa`.

The separate direct-2 m boundary helper is staged as
`build/phase14-direct-2m-internal-e11f28e2.py`, SHA-256
`e11f28e29986ca945d394a7ab4823ff6256a50dbdeb2f23d386e83404a3bcfbb`.
All 31 Linux closure, coverage and fake-transport checks pass, including
unexpected LOAD admission followed by ABORT/RELEASE, an uncertain exchange
without replay, a different rejection and foreign-owner preservation. Its
live probe stops at the active receiver lock with zero device/ARM requests.
No actual boundary request or new firmware load has run through this helper.

After the accepted RC3 post-clock Tone observations and their processes close,
this finite 3,600-second batch requires exact source/tool/image hashes,
internal NVMe identity, the workflow and all three bench locks, and idle boards.
It submits five direct 2 m LOAD requests per board at each of three clocks,
without ARM, requires `FREQUENCY_REJECTED`, and records actual request/response,
boot, inactive successor, ownership and resource bindings. Each new peer is
negotiated only after proving idle/unowned state. Unexpected admission is
aborted/released and preserved as a failure; the batch returns both boards to
138 MHz while retaining settings and the current scheduler cursor. These
checks establish a direct-request boundary only. They neither exclude physical
third-harmonic 2 m output nor resolve the failed external-decoding pilot.

At October 11 00:41 UTC, the unchanged clock continuation's rows contain 150
closed logical attempts: 130 accepted ordinary physical observations (55
retained and 75 RC3) and 20 unsupported labels. All 75 new ordinary captures
have zero receiver overflow/clipping and accepted mode/resource records with
actual WSPR decoder bindings. B's 132 MHz maximum-event contention job is
active and uncredited. The coordinator counter remains at 140 until its next
publication; the independently checked extra ten entries are unsupported
labels only. The separately identified read-only reducer requires unchanged
state/rows throughout verification and rejects unpublished physical results.
It changes no active script or scientific criterion. The full new raw audit,
remaining clocks/contention, later finite gates and reliability remain pending.

At October 11 01:38 UTC, the same coordinator has 181 closed logical rows:
161 accepted ordinary physical observations (55 retained and 106 RC3) and
20 unsupported labels. Both 132 MHz maximum-event contention jobs are accepted,
including B's authenticated browser load; the two 150 MHz contention jobs
remain. All 106 new ordinary recordings and both accepted contention captures
have zero receiver overflow/clipping and accepted mode/resource bindings.
The source/process identities are unchanged. Full new raw audit and actual
clock closure remain pending. Private checkpoint
`build/phase14-clock-profile-recovered-checkpoint-20261011T0138.json` has SHA-256
`163a8e5a54fb27351c880022e2acb6f9f9263ebdfef8e9626b5ab1fb51e571e8`.

The separately staged 4 m repetition helper is
`build/phase14-4m-internal-repetitions-8d358736.py`, SHA-256
`8d358736480b832c71494f9642682799312c15cca6e2d8db1a8a1d01a5c0f8de`.
It requires the actual accepted clock full audit/reconciliation, accepted
26-job post-clock Tone closure, ended predecessors, all bench/workflow locks,
current RC3 images and internal NVMe reserve. It reuses ten accepted 150 MHz/4 m
first observations, then acquires exactly sixteen missing WSPR/keyed repetitions,
including disconnect/reconnect. The finite workload is 1,512 capture seconds,
3,024,000,000 raw bytes and a 7,200-second stage bound. Each new analysis is
followed by independent full raw hashing; actual decoder, receiver, control,
resource, tool and source/image bindings govern acceptance. Original flags
remain unchanged, and both boards return to 138 MHz with settings/reference
restoration. All 39 Linux guard checks and five finalized record-layout checks
pass. The live probe is BUSY before device access. Preparation receipt
`build/phase14-4m-staging-20261011.json` records zero acquisitions/transfers and
no queue; the actual positive repetition path remains unexecuted.

At October 11 02:43 UTC, the unchanged coordinator has 218 closed logical rows:
197 accepted ordinary physical observations (55 retained and 142 RC3), one
unaccepted RC3 observation and 20 unsupported labels. All 143 new ordinary
recordings have valid receiver/control/resource bindings and zero overflow or
clipping. Two of four contention jobs are accepted. The independent new full
raw audit and actual campaign closure remain pending. Private checkpoint
`build/phase14-clock-profile-recovered-checkpoint-20261011T0243.json` has SHA-256
`9b659091a9f68e3f4ab3b605fa0cb9aeae7b02b9b0224ca0900cee8c4ed09b47`.

The unaccepted observation is A/150 MHz/4 m WSPR, job
`4bab612b59fa47b79decd671a31aa120`. The original decoder exited zero with no
expected-message match; control completed naturally, resources passed and
receiver cleanup was verified. Its retained analysis SHA-256 is
`24abb31c951c61410287b262714f5b2fe89e97b204d5d17e8a615d5a03cc00ef`.
The measured nominal receiver-axis carrier lies above the requested demodulation
center; that observation is informational and does not establish the cause.
No diagnostic retune, new RF repetition or original flag change has run.
This missing acceptance remains inside the ordinary clock workload budget.
The prepared closure/repetition guards require separate accepted evidence;
clock closure alone cannot admit the later Tone or reliability stages.

A separately staged retained-recording diagnostic,
`build/phase14-4m-fixed-receiver-retune-a644ed92.py`, has SHA-256
`a644ed920a711280632ba5a55c9295703665636e43b8bfd7be501ebed07c5c4f`.
Only after actual clock closure and ended predecessors, it takes all bench and
workflow locks, verifies the unchanged 312 MB recording and its original
control/analysis/decoder bindings, and reproduces the nominal audio payload
byte-for-byte. It then permits one fixed +150 Hz receiver demodulation trial
using the same sample window, converter and external decoder. The decoder and
whole-stage bounds are 90 and 600 seconds. No transmitter, time, drift or sample
correction is applied. An actual expected-message decode would require separate
review and reconciliation; it cannot change the original failure or automatically
admit later stages. All 38 Linux guard checks and the actual closed-record layout
check pass. Its live probe is BUSY before device or IQ access. Preparation receipt
`build/phase14-fixed-retune-staging-20261011.json` has SHA-256
`0fd05f48c8170318ac1f59f763133b46d9558b9a56e87de76156cc030a42ba2d`.
No decoder trial, RF job, transfer or removal has run; the positive execution
path remains unvalidated.

At October 11 03:41 UTC, the unchanged clock coordinator has 251 closed
logical rows: 225 accepted ordinary observations (55 retained and 170 RC3),
one unaccepted RC3 WSPR observation and 25 unsupported labels. Three of four
contention jobs are accepted. All 171 new finalized ordinary recordings have
verified control/resource/receiver bindings and zero overflow or clipping;
the same A/150 MHz/4 m decode remains unresolved. Independent full new raw
hashing, final clock closure and the remaining contention job are pending.
Internal NVMe free space is 86.658 GiB. Private checkpoint
`build/phase14-clock-profile-recovered-checkpoint-20261011T0341.json` has SHA-256
`066ac17d3c270cbe631d6dbc5aa58cab28254a55b9d9f99d839ba64d78a44ea0`.
Only three of nine release workstreams are closed; the estimate is 18–40 hours
from verified remaining workloads, with 4 m/2 m decode uncertainty retained.

A separate internal spectrum/compensation helper is staged as
`build/phase14-spectra-compensation-internal-9f5103d9.py`, SHA-256
`9f5103d9689de38ccab96fcd388e82b28836c0d678b50524547537a348471944`.
After accepted post-clock Tone closure and ended predecessors, it requires exact
RC3/runtime/tool/image bindings, internal NVMe reserve and all bench/workflow
locks. It performs four A/B 80 m/6 m surveys with paired 12/20 dB receiver gains,
off/on/final-off captures and same Running job/boot on both sides of each
measurement. Six separate 35-second 80 m Tone trials use zero and +/-1,500 ppb
per-job requests; engine correction and persistent settings remain unchanged.
The workload is 840 capture seconds/1.68 GB, within the existing additional RF
allowance, with a 7,200-second finite bound. Complete recordings receive
independent full hashes, actual INFO resource checks and unchanged quality
checks, with settings/GPSDO restoration. All 53 Linux guard checks and 15 tool
hashes pass. Its live probe is BUSY before device access; no acquisition or
transfer is queued. The small preparation receipt
`build/phase14-spectra-staging-20261011.json` has SHA-256
`37368a320471d97b4e14ee1202327c0799b75184d2553bc1e9f6df95c0e54c45`.
Its positive execution path remains unvalidated; no calibrated power, filtered
output or selected Pico calibration is claimed.

A separate current-image native producer stage is prepared at
`build/phase14-native-producer-internal-fbd408ba.py`, SHA-256
`fbd408baf5a7f0ebfa923231d279265e674c7006c2735722a1b2e66e02e5bf75`.
It retains the existing twelve ordinary 80 m producer repetitions, four
maximum-message cases and three native 160 m WSPR repetitions. Its 4,985
capture seconds/9.97 GB are within the existing additional RF allowance.
After accepted post-clock Tone closure and ended predecessors, it requires
RC3/138 MHz idle boards, the actual internal NVMe, 10 GiB reserve and pinned
controller/template/receiver/tool/runtime hashes. The workflow lock spans
child gaps; the parent holds B's lock while the controller child owns A and
the receiver, then holds all three locks during analysis and full raw hashing.
Actual relay requests, natural-completion responses, metadata, decoder stdout,
resources and quality are independently bound. The 32-dash DFCW case establishes
single-state envelope/capacity only; the separate alternating E/T case supplies
two-state evidence without changing the original flags. Owned service state,
GPSDO settings and both idle boards must be restored at the finite closeout.
The stage bound is 14,400 seconds; acquisition/analysis child bounds are
1,200/900 seconds and do not predict runtime.

All 62 Linux rejection/coverage fixtures, 21 tool hashes and qualified runtime
imports pass. Four retained keyed record layouts were checked without IQ reads;
a historical WSPR report missing the current serialized acceptance field was
rejected and preserved separately. Historical records were not promoted to
RC3 evidence. The live probe returns BUSY before device access. Preparation
receipt `build/phase14-native-producer-staging-20261011.json` has SHA-256
`8aa32c5666b8abe094694dfc83e63bb9d50227d25e356d630fbc4bdb2b9f790d`.
No RF, transfer, source removal or automatic queue has run. The positive
execution path remains unvalidated.

The internal clock continuation closed at October 11 05:02 UTC with 300 logical
rows, 270 ordinary physical observations, 30 unsupported labels and four
accepted contention jobs. Its exact process ended and both RC3 boards returned
empty, disabled and unowned at 138 MHz. Terminal status SHA-256 is
`1dec5400dba52f0710db9092a91d0a13ca6a998979d0b094db4a086181d5baad`.
All 215 new ordinary recordings and three new contention recordings have
zero overflow/clipping; the independently verified A/132 MHz target supplies
the fourth contention observation. Unsupported labels remain labels rather
than actual negative LOAD evidence.

The separate clock raw auditor completed all 218 new files/38,374,000,000 bytes
in 243.919 seconds, with unchanged raw/control/metadata/analysis bindings and
56 completed full-hash receipts reused. Its actual receipt
`build/phase14-new-clock-full-raw-audit-20261011.json` has SHA-256
`e20c96c86d33bb289c594696c0f72230d76dfa4d29eb0be9a81c9bb7a13c18cf`.
That audit honestly retains 273 nominally accepted jobs and the original
unaccepted A/150 MHz/4 m WSPR flag. The auditor ended without changing originals.

At the quiet boundary, the prepared single +150 Hz receiver demodulation trial
decoded `AA0NT EM18 37` from A's unchanged 312 MB recording. Its nominal audio
was first regenerated byte-for-byte using the original 4.322-second/120-second
window. Full raw hashes before and after match. No Pico/GPSDO setting, sample,
transmitter timing or drift correction changed. Actual result SHA-256 is
`2f96154a46654ef11eeee27ec41cdf7a6d839bc1a27a2800a41b01ae6ae660da`;
the original failed nominal analysis, decoder receipt and row remain unchanged.

A separately identified review passes 37 offline rejection checks and then
checks actual audit/source/control/decoder/raw identities and fresh idle boards.
Its accepted reconciliation binds all 274 jobs without changing the original
nominal flags or audit: `build/phase14-accepted-clock-reconciliation-20261011.json`,
SHA-256 `612ba1f6496cde361e194001d1d21123e221da3cf7cf3a86558c68294e4f4ff4`.
The 55 retained waveforms keep their actual older source/image/boot identities.
The prepared `8d358736` repetition entry requires original nominal-positive
flags and cannot admit this separate reconciliation. Preserve its shared
binding utilities and prepare an identified successor before the sixteen
still-required 4 m repetitions; do not rewrite the original failed row.

The separate 26-job post-clock Tone sweep closed on internal NVMe at October 11
05:44 UTC under `ed93f302`; coordinator 3004539/start ticks 61345766 and all
children ended. Its terminal status has SHA-256
`4fb3edebc0cb05628608ad08a98d46a3df63b2de25e8748320b008327e4e69d1`.
The separate audit verified all 26 complete recordings/2,600,000,000 bytes in
6.871 seconds, with actual control/analysis/metadata/INFO resources, finite
coherence/amplitude/reference gates and matched close-in records accepted.
The audit receipt `build/phase14-post-clock-tone-full-raw-audit-20261011.json`
has SHA-256 `13efa68802775a57a59cd03f6d1947065a12d58282187660c77dc62ace4a6c07`.
The original A/6 m nominal placement flag remains false; it does not exclude
the band or select calibration. Both boards returned idle at RC3/138 MHz.
These 26 jobs are separate from the closed 26 pre-clock captures.

All thirty unarmed direct 2 m LOAD boundaries have now actually returned
`FREQUENCY_REJECTED` on two boards, five modes and three clocks. There were no
ARM requests or RF captures. Six resource groups were independently recomputed
from actual INFO events, and both boards returned empty, disabled and unowned
at 138 MHz. The stage status has SHA-256
`97f5aac45e297723e5316ee6a2ae5fd712554d3be54b70f1df10bb13ee9b7060`;
the independent review `build/phase14-direct-2m-verified-result-20261011.json`
has SHA-256 `849fa6ca0bba81cf8d320a8030f14a7da6b0bdc44a6760b9484e8b01ccbaed1e`.
This closes the control gate; physical 2 m decoding remains unresolved.

The 4 m successor `855c05a4` preserves the original A
nominal failure and admits its actual reviewed receiver decode. It checks
all ten retained raw identities before reuse. Its 61 Linux rejection checks,
ten actual closed layouts and fifteen tool hashes pass; the probe refused
at the then-active Tone workflow lock before device or sample access.
It is now running as coordinator 3039713/start ticks 62039003, acquiring only
the sixteen missing repetitions on internal NVMe at 150 MHz. Its initial ten
observations are retained; whole-stage closure is not yet claimed. Preserve
the old shared `8d358736` binding utilities; do not execute its old RF entry
or the superseded `38fa079d` preparation.

The October 11 07:25 UTC snapshot has seven new closed observations, six
meeting mode criteria. All seven have accepted resources and zero receiver
overflow/clipping. New A/150 MHz/4 m WSPR job
`e54aaac9b904c5b0aadba08c4a09eb84` is missing its nominal expected decode;
the following WSPR frame decoded correctly. No transmitter cause is inferred.
The original failed analysis remains unchanged. A distinct receiver-only
diagnostic is staged as `build/phase14-new-4m-fixed-retune-825ee3f6.py`,
SHA-256 `825ee3f61482c8ab0906c2ebc46626127f4c7138b400ab4bd1bc022951593c27`.
Its 38 Linux rejection checks and actual closed-record binding pass; the probe
refuses the active workflow before IQ or device access. After actual sixteen-job
closure, ended processes and restored idle 138 MHz boards, it permits one fixed
+150 Hz receiver-demodulation trial on unchanged IQ, requiring byte-identical
nominal audio and the original 4.669 s/120 s window. It adds no RF or
transmitter/time/drift/sample correction. It is not running or queued; only
actual external stdout and a separate review could accept this recording.

The sixteen missing 4 m repetitions closed at October 11 07:43 UTC with
3,024,000,000 complete, independently hashed sample bytes. Coordinator
3039713/start ticks 62039003 ended, both RC3 boards returned empty at 138 MHz,
settings/current cursors were preserved and the GPSDO was restored. Terminal
status SHA-256 is
`ae2cd42bb105949b7d5889fa26232805d831596ef7678b5224fae16bd03f76d2`.
All sixteen resource and receiver records pass with zero overflow/clipping;
fourteen new observations meet mode criteria. The two first WSPR repetitions,
A job `e54aaac9b904c5b0aadba08c4a09eb84` and B job
`e7cc7bf7f353e2947fc3bf6bc5062e7c`, lack expected nominal decodes. Each following
frame decoded correctly. Those observations do not resolve the first-frame
failures or qualify three-frame reliability.

Separate single +150 Hz receiver-demodulation diagnostics on the two unchanged
312 MB recordings also ended without expected decodes. Each regenerated its
original nominal audio byte-for-byte and retained its original decode window:
A 4.669 s/120 s and B 4.158 s/120 s. Full raw hashes before/after match. Result
SHA-256 values are
`8352acab1dc7b5cb53d7ad23c55ab9a7db30ffb48bca63c8aac14d4f45d717f5`
and `545087a3d99ba6ab16485c1c05ae95ee86385cdda4fc2082bab8160823201606`.
Both diagnostic coordinators/decoders ended; no transmitter, time, drift,
sample or device-setting correction was applied. Preserve these completed
trials and every original nominal flag. The 4 m gate remains unaccepted;
neither repetition nor diagnostic is to be blindly repeated. A prepared
evidence reviewer rejects missing expected-message evidence and has not run.

The first standalone preflight stopped before settings reads, child execution
or RF because its prepared browser credential path lacked `server/deployment.json`.
Coordinator 3050869/start ticks 62256676 ended with no observations or child
steps, restored reference state and both RC3/138 MHz boards empty. The failed
status SHA-256 is
`a57c0378e5e25d0779e0682effa38fefe03bce43a87a69f7e0fec9fb2ebabc89`.
The separately identified `b83ba6b2` standalone/lifecycle recovery binds that
exact closed failure and the existing credential directory already used by
the clock/browser campaign. Its 84 existing guards plus 13 failure-admission
checks pass, and actual identity-bound HTTPS readback returned 200 before RF.
No firmware, scientific workload or threshold changed. Preparation's receipt
parser failure remains recorded; the offline guard's accidental historical
receipt replacement was preserved separately and the independently retained
original bytes restored. The successor guard has its own output.

That recovery has been dispatched once for the existing three USB-unavailable
standalone frames on internal NVMe. Exact coordinator 3052618/start ticks
62288662 and child 3052808/start ticks 62292381 were active at the checkpoint.
The fresh 32 KiB read verified B's existing engineering profile generation 4
and disabled configuration; it wrote no flash profile. Analysis, actual
external decodes, settings/current-watermark restoration and whole-stage
closure remain pending. Lifecycle, controller and long reliability stages are
not queued. The original `fc0e92c7` standalone/lifecycle entry is superseded;
the current standalone execution must not be repeated. Lifecycle remains a
separate guarded execution after the bench becomes quiet.

The separately staged `b53d2482` decoder diagnostic permits one installed
OSD-depth-one trial per new failed 4 m recording, with the original nominal
WAV, receiver frequency and decode window unchanged. Thirty Linux guards pass;
both probes refuse the active standalone workflow before sample/device access.
Each decoder is bounded to 90 seconds and its enclosing trial to 600 seconds.
No RF, retune or transmitter/time/drift/sample correction is added. This is
preparation only; an actual expected-message decode and separate review would
still be required. The completed fixed-retune trials must not be repeated.

Standalone recovery closed at October 11 08:02 UTC. All three adjacent WSPR
frames externally decoded `AA0NT EM18 37` while host USB was unavailable and
USB power stayed unchanged. The 472-second recording contains 944,000,000
complete bytes with zero receiver overflow or clipping. The independent
review full-stream hashed the raw file, checked stable file identity and
bound actual control, metadata, INFO resources, decoder stdout/audio/tool
hashes, the same boot across the three frames and USB disable/restore events.
The original analysis's false legacy flag remains unchanged. Advanced current
watermark, durable settings and the engineering profile were preserved;
the owned service, GPSDO and both idle RC3/138 MHz boards were restored.
Coordinator 3052618/start ticks 62288662 and every child are gone. Actual
status SHA-256 is
`c6d4fe3571455988cb5fefbcba4c94e35d90b19ac2082c34066e5475b74de5b1`;
the separately accepted review
`build/phase14-standalone-independent-review-20261011.json` has SHA-256
`3e877d522fc365d068e13ca8284b99c03c52a507cccb4392ca5248be980214a0`.
Those frames and their full raw audit must not be repeated.

Both separate OSD-depth-one trials on the two failed 4 m nominal WAV files
also closed without expected decodes. Each used the byte-unchanged nominal
audio, original receiver frequency and original decode window with only
the installed decoder's `-o1` option added. A coordinator 3055289/start ticks
62380450 and B coordinator 3055690/start ticks 62388131 and their decoders
are gone. Actual result SHA-256 values are
`b8b2fc51c15a7884255f194f8118c51c5c6c116e15775cda0d72780ec14c0e5b`
and `61e352549a84d9b35f873cad7c58c546699b73de5a280e7b7d80e1526606d7ad`.
No RF, IQ modification, retune or transmitter/time/drift/sample correction
was used. Preserve these negative trials; the complete 4 m repetition gate
remains unaccepted, and its prepared positive reviewer has not run.

The first lifecycle attempt closed at 08:18 UTC after its valid B clock-loss
capture and analysis. Its host assertion mistakenly passed the actual opaque
job ID back as a constructor seed, producing a different expected ID. Every
scientific job field matched; actual LOAD/ARM/terminal identities remain bound.
Coordinator 3056654/start ticks 62405576 and both children ended. Its failed
status, SHA-256
`b2a411303668a4b0827db8b7836c5d28e2709e4892bd6a47f0a7b13e5f4434f2`,
keeps zero published accepted observations and its original error. The owned
NTP rule was removed, fresh synchronization recovered, and the service,
GPSDO and both idle RC3/138 MHz boards were restored.

A separate review independently full-stream hashed that unchanged 570 MB
recording and verified its 285-second receiver record, finite Tone quality,
actual resources and exact clock-loss request/response/events. The aged ARM
request actually returned `CLOCK_UNSYNCHRONIZED`; its own block, refusal,
removal and recovered synchronization occur in the required order. Review
`build/phase14-lifecycle-clock-loss-independent-review-20261011.json`, SHA-256
`ab29dbc053fd5bf3ac0f274d431398cb30619501c400fc73009c38d70a881bda`,
separately accepts that case without rewriting the failed stage. Its raw hash
is `67aa92131d32ab9f8bcd81eca35071ee24cff0e9ed7aa3b7f10e1955fbfcc37b`.
The case must not be repeated. Lifecycle coverage remains incomplete.

The separately identified continuation normalizes only the expected opaque
job ID before comparing the entire unchanged job body; the physical validator
still independently binds the actual ID to accepted LOAD/ARM/terminal records.
Eighty-four existing guards and twelve opaque-ID/body rejection checks pass.
Helper SHA-256 is
`91ac22d4ed086b7d214ffcfe389f4a2a688eb58fc6e57fb5d34e6a29080f3142`.
Coordinator 3062849/start ticks 62561372 was dispatched once at 08:37 UTC,
retaining the separately accepted clock-loss case and acquiring only eight
missing cancel/abort/disconnect/512-event cases on internal NVMe. Their planned
capture is 926 seconds/1,852,000,000 bytes within a 7,200-second whole bound.
The 08:41 small-receipt checkpoint shows the same process and A cancellation
child, with only the retained case published. No new partial case is credited.
No active helper, firmware, scientific workload or threshold was changed.
Later controller and reliability stages remain separate, unqueued work.

A read-only comparison binds the 28 existing ordinary RC3/150 MHz WSPR
reports and four new 4 m repetitions to unchanged physical/metadata/analysis
records and tool hashes. It reads no IQ, runs no decoder and starts no RF.
The two new failed frames have retained monotonic launch observations at
A 25.348 s and B 15.235 s after reboot; the following decoded frames begin
at A 220.330 s and B 216.270 s on their respective same boots. Their first
20 symbol slopes relative to the simultaneous reference are A -0.335 and
B -0.584 Hz/s, versus -0.147 and -0.206 Hz/s in the following frames.
The separately recorded reference slopes are much smaller, but this does not
calibrate the Pico or isolate a transmitter mechanism.

Boot age alone is insufficient: the initial A 4 m frame still missed its
nominal decode at 6,883 s uptime, before its separately accepted fixed receiver
demodulation. Its first-20-symbol relative slope is -0.135 Hz/s. Initial B
decoded at 6,859 s with -0.210 Hz/s. Boot age, controller disconnect, elapsed
time and previous RF workload are confounded. The comparison is informational,
keeps frequency/drift pass/fail null and changes no original acceptance flag.
Private receipt `build/phase14-upper-band-boot-age-reference-cohort-20261011-complete.json`
has SHA-256 `be5b6e0cf5210a7b0c0a2ce64e186a6e554a61e3a23da81cbe4e42ae7716d5a6`.
Earlier read-only layout/count refusals remain recorded; 150 MHz has fourteen
representable bands per board, so this comparison contains 32 physical jobs.

The lifecycle continuation closed all nine cases at October 11 08:59 UTC.
Coordinator 3062849/start ticks 62561372 and every child ended with no error
or unresolved cleanup. Actual terminal status SHA-256 is
`417a56f65b0e5d6b2fb8d3336d25263ca9398a415f218ff6bbe54c967ff11711`.
The independent reviewer then full-stream hashed the ten new recordings/
1,852,000,000 bytes, reusing the existing full audit and unchanged identity
of the 570 MB clock-loss recording. All nine cases and eleven actual jobs
passed source/image/boot/job/control/metadata/event/analysis/tool/resource/
receiver binding, including paired cancellation baselines, deliberately
truncated aborts, disconnect completion and B's browser-loaded 512-event case.
Fresh before/after inventory, settings and GPSDO readback passed at the quiet
boundary; the owned service was restored. The original failed lifecycle stage
and nominal diagnostic flags remain unchanged.

Auditor 3066587/start ticks 62704147 is gone. The accepted private review
`build/phase14-lifecycle-independent-review-20261011.json` has SHA-256
`2305f2203f28fe7f0fbef0b4a62a5429ee9ff3743570a81985f465bd8bf4ffac`.
Its predecessor reviewer was superseded before execution to account explicitly
for the serialized overall human-copy/resource field. That reader change kept
the existing assessment and thresholds; the actual closed 512-event record
matched. These cases and completed audits must not be repeated.

The next native producer/max-message gate was dispatched once at 09:03 UTC
after accepted lifecycle closure and a fresh quiet source/tool/storage probe.
Coordinator 3067306/start ticks 62717429 uses the prepared `d0075b85` helper,
SHA-256 `d0075b85ee9ed9fe6883edee3edcc9a2e2abf705402595149d52b264d8c39990`.
It retains the existing nineteen-job workload: twelve ordinary 80 m producer
repetitions, four maximum-message cases and three native 160 m WSPR frames.
The 32-dash DFCW case supplies capacity evidence; its separate alternating E/T
case supplies two-state evidence. Planned capture is 4,985 seconds/9.97 GB,
with the unchanged finite stage/child bounds and internal-storage ownership.
The 09:06 small-state snapshot shows the coordinator and first controller
child, with no analysis-closed job credited. The service was active before its
owned stop. Actual closure, independent acceptance and restoration remain
pending. No external transfer overlaps this active workflow, and mixed/long
memory work is not queued. The unresolved 4 m and physical 2 m WSPR evidence
remains open. The estimate is 16–38 hours with three of nine original
workstreams closed; the newly accepted 926 lifecycle capture seconds are
credited once in the inclusive other-work allowance.

The native stage closed at 09:26 UTC with a preserved host assertion failure;
coordinator 3067306/start ticks 62717429 and its children ended. Six jobs were
published as accepted, and the seventh FSKCW acquisition and analysis also
completed. Its requested space state was exactly 3,570,095 Hz. The recorded
accepted realization was 3,570,094.991941005 Hz, 0.008058995 Hz below the
wrapper's coarse lower bound. This assertion concerned the accepted event
representation; it was not a failed measured RF-frequency or drift criterion.
The actual FSKCW human-copy, resource and receiver checks passed, with zero
overflow or clipping. Service, GPSDO, settings and both RC3/138 MHz idle boards
were restored. Original failed status SHA-256 is
`a187e32df01aa13d8262f2a9fc20b279bbdf7c9b151e72bc9440ad0bc57f4aa6`.

A separately identified recovery validates the exact requested native frequency
states and retains the recorded accepted adjustments, relay transactions and
existing waveform/resource criteria. It preserves all nineteen original jobs:
seven completed recordings supply 1,150 capture seconds/2.3 GB, leaving twelve
missing jobs/3,835 seconds/7.67 GB. It does not repeat the completed RF jobs or
change firmware, controller, scientific workload or measurement thresholds.
The existing 65 Linux guards and 19 recovery guards pass; seven actual closed
record layouts match. Earlier shell-access refusals, a mistaken centered-WSPR
request assumption and a serialized file-identity comparison refusal are
preserved separately. These were preparation/review failures, not new RF
failures. The corrected reviewer reuses six completed full-hash receipts with
unchanged file identities and independently full-hashes the seventh recording.
Its actual acceptance remains separate from preparation and whole-gate closure.

That seven-job review has now closed with actual acceptance, SHA-256
`2bf8eb7996598238a569612a6839d19e32fa7b487ee9a9cc8205cc90520bb043`,
at private `build/phase14-native-seven-prefix-independent-review-final-20261011.json`.
Reviewer 3079872/start ticks 63042677 is gone. It reused the six existing
full-hash receipts/2.13 GB with unchanged file identities and fully hashed the
seventh 170 MB recording. All actual controls, metadata, INFO resources,
accepted relay events, analysis tools, expected WSPR decoder stdout/audio and
keyed human-copy records matched. Fresh idle inventory, durable settings,
GPSDO and active-service restoration passed. The original stage remains failed;
the separately accepted prefix does not close the full native gate.

The missing-job continuation was dispatched once at 09:59 UTC, coordinator
3080610/start ticks 63057499, using
`build/phase14-native-prefix-reviewed-identity-3c9094cc.py`, SHA-256
`3c9094ccad0f0414cf2c2f3cc6686b42e4e813ae6f00bf232f68bb21aea1d656`.
Its first child is acquiring `ordinary-FSKCW-1`; the seven retained jobs are
already bound to the actual admission receipt. The read-only live checkpoint
`build/phase14-native-prefix-recovery-live-20261011T1000.json`, SHA-256
`64b6e1de71d004b5839ae2f08f9ad6d890777f822029c4bf049ab38f23516282`,
confirms the exact process identities, no error, 67.009 GiB internal free and
distinct internal/external filesystems. This finite twelve-job continuation
must not be duplicated or changed. No external transfer or later queue is
running, and no native capture credit is applied before whole-gate acceptance.
The original three-of-nine workstream count and 16–38-hour estimate remain.

The continuation subsequently closed all nineteen jobs at 11:12 UTC, status
SHA-256 `5c0415b92cefd577772f300cec44f8c2ca24e5dee587fe1bf09db5fa12c6fe8a`.
Coordinator 3080610/start ticks 63057499 and all 24 acquisition/analysis children
are gone. A separate bounded reviewer, helper `5793cc85`, independently hashed
the twelve new recordings/7.67 GB and reused the accepted seven-job prefix/
2.3 GB with unchanged exact file identities. It rebound every actual controller,
private template, relay LOAD/ARM/natural terminal, metadata, analysis, expected
WSPR stdout/audio/decoder, human-copy, INFO resource and receiver record.
Before/after idle inventory, durable settings/current cursor, GPSDO and active
service restoration passed. Reviewer 3091023/start ticks 63498720 is gone.
Its actual accepted receipt is
`build/phase14-native-nineteen-independent-review-20261011.json`, SHA-256
`1d0c21f758a4dc7562d606d66dce2578a5d53d48fad623fba289937c701e4b85`.
This accepts the existing nineteen-job native gate, 4,985 capture seconds/
9.97 GB, while preserving the original failed `d0075b85` stage. These jobs and
completed audits must not be repeated.

A six-record informational comparison used only retained symbol reports and
small source/control/metadata/tool bindings, without IQ reads, new decoding or
device access. The failed new A/B frames show greater within-frame frequency
movement than their following decoded frames. The actual receiver-indicated
offset ranges are 158.02–174.05 Hz versus 155.10–161.95 Hz on A, and
21.82–46.62 Hz versus 18.32–27.30 Hz on B. GPSDO-relative estimates are retained
separately. Neither those correlations nor the fit residuals isolate a
transmitter, receiver, thermal, restart or disconnect cause, select calibration,
or create frequency/drift pass/fail or band exclusions. The private receipt is
`build/phase14-four-metre-carrier-placement-informational-20261011.json`, SHA-256
`4ed4ede393d4976ede95bc2630313f7082bd9eaa6c1fad629dc7c9d76e2fd253`.

The separately identified two-slot diagnostic was dispatched once at 11:23 UTC,
coordinator 3094063/start ticks 63560563, helper `612a4347`, SHA-256
`612a434745f0d475f05cb388158d30bc9ddef8d9c3ae86bd387c8622d196340b`.
It changes only the observed idle settling interval before these two failed
slots: both boards use the same RC3/150 MHz image, original WSPR workload and
disconnect action, receiver settings, nominal decoder and acceptance criteria.
Firmware monotonic boot age must reach 350 seconds while the board remains
empty, unowned and disabled. The two 156-second captures use internal NVMe;
the whole-stage bound is 2,400 seconds. New raw hashes and all control/resource/
receiver/decoder bindings must pass, and both boards/settings/current cursor/
GPSDO must return to their original 138 MHz state. There is no RF warmup,
transmitter/time/drift/sample correction, selected calibration or automatic
4 m reconciliation.

The first preparation refused a resource mismatch before IQ/device/RF access;
its reader had included INFO records appended after the original analysis.
That refusal and unexecuted helper `35790ebe` remain preserved. The successor
checks the exact original INFO prefix, sample count and terminal snapshot with
unchanged thresholds. The 27 original Linux guard checks, ten affected prefix
guards and two actual failed-record layouts passed. Preparation is not RF
qualification. At the read-only checkpoint
`build/phase14-four-metre-idle-settling-live-20261011T1128.json`, SHA-256
`c85bc7b85769b52e19a4c2e843a969983788cd81838aee40650ba131b53d5a3d`,
the same coordinator was waiting on A, with zero closed observations. Do not
duplicate or alter this active work. Mixed reliability and memory follow-up
remain unqueued and require separately reviewed 4 m acceptance.

The revised 15–37-hour estimate credits the accepted native duration once,
leaves 4 m and this new diagnostic uncredited, and includes 346 MB of retained
new A132 max-contention samples previously omitted from the core archive
estimate. Pending core raw transfer is 114.220 GB: 72.9 GB unrecorded mixed/
memory, 38.720 GB closed clock including that retained max job, and 2.6 GB
post-clock Tone. No elapsed-time or archive credit is taken. Other finite raw
retention stays within the existing inclusive other-work allowance.

The original `9f5103d9` spectra attempt closed with a connection reset before
CLAIM, LOAD or ARM; coordinator 3016363/start ticks 61576755 is gone. Its failed
status `b3c3f5e918417fa68ca3b337bf293b34104482ff31505c175c0c2f495b58d2b0`
and partial survey remain unchanged. A separate reconciliation fully hashed
22 receiver-only background recordings/88,000,000 bytes, with zero overflow
or clipping, restored GPSDO settings and both RC3/138 MHz boards idle. Its
receipt has SHA-256
`557c5c125f612f123ccb449b6f6fb908e41f7fc3f99ca15c8636473acf085cc4`.
No transmitter job or accepted survey ran in that attempt.

A separately identified recovery `ec2c44d4`, coordinator 3025774/start ticks
61779527, completed all four paired surveys. It then closed at 06:49 UTC with
a stale connection reset at the first compensation CLAIM, before LOAD or ARM.
Its failed status has SHA-256
`8a712e32f2de5235783617cf8c0af12b60c2a640801c74a7e94ee33744e2ddd6`;
its process is gone, both RC3/138 MHz boards are idle and GPSDO restoration
passed. All four accepted surveys and 180 independent full-raw receipts/
720,000,000 bytes remain unchanged. No compensation RF ran in that attempt.

The separate `fcf105c9` continuation runs only the six missing compensation
trials, refreshing a peer only after proving the board idle and unowned.
Coordinator 3035716/start ticks 61956963 closed all six trials and is gone. Fifty-four
Linux guard checks, all four persisted survey layouts, their original INFO
prefixes and all 180 audited raw identities pass. The earlier read-only
tuple/list, resource-prefix and shared-helper compatibility failures remain
preserved; they changed no source, samples or RF result. No survey is repeated.
Actual status `fceb7197e92df730c8505e98151c7285344dfe28758f9b826c1642521b741bc1`
records successful closure and restoration. Independent review of all ten
jobs, 186 full-raw receipts/1,680,000,000 bytes, actual controls, resources,
receiver and finite Tone quality passed. The separate reviewed receipt has
SHA-256 `f04a870159c12ab4e6e7961e6c5748182302c673a0dd350f309de874c7339a9e`.
Frequency/power/filter qualification and selected calibration are not inferred.
All clock/Tone originals remain; no external transfer or raw release overlaps
capture/analysis, and no later reliability queue is armed.
The remaining standalone scope is the existing three USB-unavailable frames
and nine lifecycle cases. A separate driver is staged as
`build/phase14-standalone-lifecycle-fc0e92c7.py`, SHA-256
`fc0e92c7d90e70c3d35dcd1de5778cfb90f20048e698460124a6f7a178437b89`.
Its 84 Linux rejection checks, 33 source/tool hashes, qualified imports and
52 actual closed INFO identity checks pass. Both stage probes refused the active workflow
before device or sample access. It is not running or queued.

Standalone and lifecycle are separate finite invocations, each with a
7,200-second bound and all bench/workflow ownership. Standalone reads a fresh
disabled configuration, retains B's engineering profile and observes three
frames while host USB is unavailable; configuration restoration preserves the
current scheduler cursor. Lifecycle retains the existing clock-loss, cancel,
abort, disconnect and 512-event cases. Maximum capture is 1,741 seconds/
3,482,000,000 bytes, already in the other-RF allowance. Original nominal flags
remain; independent decoder/control/resource/full-raw checks and actual
restoration are required before acceptance. No positive execution is claimed.

Adversarial preparation review distinguished USB serials from WTP device IDs
in the standalone and native-producer guards. Old `34d5bdff` and `fbd408ba`
helpers remain preserved and superseded. The native successor is
`build/phase14-native-producer-device-identity-d0075b85.py`, SHA-256
`d0075b85ee9ed9fe6883edee3edcc9a2e2abf705402595149d52b264d8c39990`;
65 Linux rejection checks pass. The actual protocol IDs are
A `fd6127d11d6aca42a9905fa3fb1bf1d5` and B
`29f20b7342051ef947aa56cb9d4fab42`; their USB serials remain unchanged.
No RF ran under either superseded guard. The new helpers are prepared only;
their scientific jobs and thresholds are unchanged.

Only three of nine release workstreams are closed; the estimate is 17–39 hours.
It credits actual reviewed clock acceptance once and includes completed clock
recordings awaiting closed-file archival in addition to unrecorded samples.
The remaining fixed core is 37,546 capture/settled seconds; finite gates,
4 m reliability, unresolved 2 m, later audits, installation/review and push
remain unfinished.

## Operator storage correction and stopped clock stage

The operator rejected direct external-SSD writes during acquisition and
required internal recording. The external build bind is retained as historical
evidence; it is superseded for new acquisition. The separate tool root
`resume-tools-1024529-internal-first` records on wspr5's internal NVMe, UUID
`ed6c7f1b-238b-41a1-b4b6-7bcdef3270fe`. Its 1,812 source files and three
candidate images match their pinned hashes. A flushed 4 MiB write/read check
passed with about 117.90 GiB free. Completed, analyzed recordings can be
transferred to the external SSD at a verified quiet boundary, with independent
full source/destination hashes and durable retrieval records before any
redundant internal representation is removed. No transfer overlaps acquisition.
The [retention policy](phase14-evidence-retention.md) records this amendment.

Before that change, the original `64ab8175` clock campaign independently stopped
at October 10 20:37:40 UTC. Its final failed state has SHA-256
`b2c379edbec8ad83368460577148295faf16564aeb7015f182a3edea9413c4db`;
75 logical rows have closed, with 55 accepted physical observations, 10
receiver overflow failures and 10 unsupported labels. The final small-receipt
reduction is `build/progress-evidence-clock-20261010T2050-closed.json`, SHA-256
`ff70aac25ab6bd17876a1c37cf2d7b33fc05f09cdb74193f5414a8e6a1cb2d28`.
It does not replace a full raw-stream audit or establish negative LOAD checks.

The stage stopped during its A/132 MHz/80 m/512-event FSKCW contention check
on `Inventory exchange deadline`, followed by `USB EOF` during cleanup.
That is separate from the ten receiver overflows. Its original terminal/cleanup
state was not obtained. The 26,062,848-byte incomplete recording remains
retained and does not qualify that job. A USB disconnect/re-enumeration and
changed A boot identity were observed; the cause remains unisolated. Separate
fresh USB INFO confirms both boards empty, disabled and unowned at unchanged
source `119477a9c8c8`, A at 132 MHz and B at 138 MHz. Full WTP inventory was
unavailable because A's consumer LAN listener/time was not ready; it is not
claimed as passed. The small reconciliation is
`build/phase14-clock-contention-stop-20261010.json`.

The old external-acquisition clock, receiver, Tone and reliability wrappers are
superseded and must not be run. A separate finite GPSDO-only receiver diagnostic
completed three 156-second internal-NVMe captures with zero overflows/clipping,
the original receiver settings and no Pico jobs. Reference restoration and
same-boot/source/clock USB-idle checks passed. Its result receipt is
`build/phase14-receiver-internal-result-20261010.json`, SHA-256
`96cfcbebef87bc6d701f23a7e2c48beca9e70a0cbb8c2bfc433ae045e14bd766`.
It is closed; do not repeat its completed jobs.

After that process ended, a separate copy-only transfer independently verified
17 files/936,191,802 bytes on the external SSD and unchanged internal sources,
with durable retrieval receipts. It took 32.19 seconds; no capture was active
and no source file was removed. The archive is
`/mnt/phase14-testing/phase14-closed-internal-first/receiver-internal-20261010T2045`.
Its retrieval receipt has SHA-256
`e39db2494e6849e149ad5d0056af5a03eae9af50c7a872f99948f59ad0c2be6b`.
The private local summary is `build/phase14-internal-first-storage-result-20261010.json`.
These observations verify the internal-recording/closed-archive workflow;
they do not isolate the earlier overflows, qualify Pico RF or establish
hour-long reliability. Original failed rows, control receipts and external
recordings remain unchanged. The separate USB/control failure requires
reconciliation before resuming qualification.

The refreshed estimate is 24–47 hours, with only three of nine workstreams
closed. It credits 4,444 accepted clock capture seconds and the 468-second
receiver diagnostic once. Remaining fixed capture/settled observations are
58,206 seconds (16.17 hours); the ten missing overflow slots and all four
contention jobs remain required. The existing 3.90–17.90-hour other-work
allowance remains, and the receiver range becomes 0.87–5.87 hours after its
completed diagnostic. New USB/control diagnosis adds 1–4 hours. Applying the
measured closed-transfer/verification time to remaining raw bytes adds
1.09–2.18 hours for this newly required storage workflow. The resulting
23.03–46.12 hours are rounded upward. Larger source repairs can extend it;
2 m decoding and final audits, installation, review and push remain open.

## Numeric progress checkpoint

Three of the nine original workstreams are complete (33.3% by count).
The repaired 138 MHz matrix has all 312 required observations accepted under
the operator's mode/resource criteria, including separately reconciled 6 m
receiver-retuned decodes. Its 26 pre-clock Tone observations are closed.
The original nominal-decode, frequency-only, completion-fault and cached-peer
closeout failures remain unchanged. Source `119477a9c8c8` repairs the Worker
inspection race without changing the 100-us bound; 12/12 affected DFCW RF
observations and both-board 80 m baselines pass. The 2 m pilot remains 0/2
externally decoded, with full qualification conditional on reliable decoding.

At October 10 18:48:58 UTC, the separate verification-only recovery completed
both archive destinations and unchanged-source rehashes, saved retrieval
locations and released its quiet guard. The immutable final receipt is
`build/phase14-archive-verification-final-1791658138038212000.json`, SHA-256
`05e818ccbd9ed3dc6779bf5e6d90f5fe7af1d1b3b63500200eb0ec4398412058`.
It honestly identifies helper `9770a57e`; the earlier copying and 900-second
whole-directory verification timeouts remain failures. wspr4 has 18 verified
files/14,642,387,882 bytes and wspr2 has 17 files/14,632,036,322 bytes.
All four original source recordings remain. The external SSD makes their
relocation unnecessary; no new bulk archive or compaction is needed.

The pinned system-Python clock handoff then failed before RF because it could
not import the existing qualification harness. Its failed state and logs remain
preserved, with no original RF output. The runtime observer independently
confirmed that exact failure and dispatched corrected helper `64ab8175` once.
Both Mac observers are now closed. The corrected clock coordinator ran
on wspr5 as PID 2821523/start ticks 57594160, child PID 2821541/start ticks
57594346, using the qualified Python 3.13.5 environment and explicit current
Pico source/scripts before the harness source. Its state and rows are under
`resume-tools-1024529/build/repaired-runtime-clock-state` and
`repaired-runtime-clock-comparison`. It has since stopped as recorded above;
do not restart it or invoke its superseded external-acquisition wrapper.

At the independently checked October 10 20:23 UTC snapshot, 57 of 300 clock
row attempts were closed. Forty-eight complete captures have accepted mode and
resource evidence: 8 expected-message WSPR decodes, 10 Tone, 10 QRSS, 9 FSKCW
and 11 DFCW observations. Verification binds actual control, capture metadata,
analysis and firmware/job identities, plus decoder stdout/audio/receipts.
The immutable progress receipt is
`build/progress-evidence-clock-20261010T2030.json`, SHA-256
`d872201945ca3bbf6aa65a4371ca613bbb60084a4cd70bc4f8f6e3d699222b70`.
Full independent raw-stream rehashing remains pending; this checkpoint does
not substitute for that audit or close an original workstream.
Sixteen keyed rows retain legacy frequency/coherence flags. Their separately
serialized human-copy and overall human screens and resource checks pass;
these informational flags do not invalidate those observations or exclude
their bands. The preceding 19:30 checkpoint and every original flag remain
preserved.

Nine attempts have unusable receiver evidence, all on A at 132 MHz:
2200 m Tone/FSKCW, 160 m WSPR, 30 m WSPR, 20 m QRSS,
17 m Tone/WSPR/FSKCW and 15 m WSPR. Every capture helper reports one SDR stream
overflow, zero clipping and verified receiver cleanup. The existing helper
removed incomplete raw files while retaining their sizes/hashes and failure
receipts. Some Pico jobs completed; others were aborted during cleanup after
the receiver ended early. These observations establish capture
failures and missing qualification coverage, without isolating their cause or
establishing transmitter failure. The original row flags stay failed. Their
nine physical slots remain required, and no repetitions have been queued.
The private missing-coverage snapshot is
`build/phase14-missing-clock-coverage-plan-20261010T2024.json`;
it must be reconciled against the final closed campaign before execution.
This partial snapshot is not a final follow-on scope.

Read-only USB inspection places the RSP1B and external SSD on different USB
controllers. The snapshot showed available memory and no corresponding SDR
reset in the kernel log; it does not isolate the overflow cause. A further
39-second read-only host observation retained 40 samples, with at least
3,465,824 KiB available memory, low load and no recent kernel errors.
Source inspection shows synchronous CF32 encoding/writing between receiver
reads. Write or scheduling latency is a hypothesis requiring closed-boundary
measurement, not an established cause or proof of the deployed binary's build
provenance. The inspected source hashes match the existing wspr5 Harness
checkout; no sibling source, active process, settings or storage route changed.
The separate investigation record is
`build/phase14-receiver-overflow-investigation-20261010T2025.json`.
A separate
GPSDO-only diagnostic is staged as `phase14-receiver-overflow-probe-f63b9cda.py`,
SHA-256 `f63b9cda108230562008c3e78cb007c80f6fd946d34dd40132c6eddfaf0d498b`.
Six closure/rejection checks and exact tool hashes pass; its live probe returns
BUSY before acquisition. It is not running or queued. After successful clock
closure and a verified quiet boundary, it can take three finite 156-second
captures using the unchanged 250 ksample/s CF32 receiver settings, no Pico
transmissions, preserved GPSDO settings and final restoration/inventory.
This is receiver-continuity evidence, not a transmitter qualification claim.

The external-acquisition post-clock Tone `ee04ee8d` and reliability `bbd4efbc`
wrappers are now superseded, not queued. Required finite checks and affected receiver coverage must
be reconciled before long reliability testing. All new bulk recordings use the
verified wspr5 SSD; 919.77 GiB was free at this checkpoint. No recording is
copied to the Mac or added to a routine SD-card archive.

The preceding 20:23 estimate was 22–41 hours. It credited 3,950 seconds of accepted
clock captures and retains the 964 seconds represented by failed slots in the
required clock budget. The completed 2.396-hour archive allowance has been
credited once; its verification uncertainty is closed. Remaining core raw
capture is 57,604 seconds (107.30 GiB); including settled observations gives
58,700 seconds (16.31 hours). The remaining other-work allowance is
3.90–17.90 hours. Continuing overflows across six bands replace the previous
0.5–3-hour receiver diagnosis allowance with 1–6 hours for diagnosis and
affected validation. Missing capture durations remain in the fixed budget.
That allowance included the finite diagnostic
and retains 2 m, audits, installation, review, commit/push and closeout.
Measured helper-start-to-analysis-publication medians project about 6.03 hours
for the remaining clock slots; their analysis/control overhead is already
inside the other-work allowance. Timeout bounds are not predicted runtimes.
Larger repairs can extend the estimate. Placement/drift remain informational,
with null pass/fail and no band exclusions because calibration is undecided.

| Workstream | Completed count | Percentage |
| --- | --- | --- |
| 1. Initial source and historical-evidence review | 1/1 | 100% |
| 2. Established plan and acceptance record | 1/1 | 100% |
| 3. Bench identity and tooling preparation | 1/1 | 100% |
| 4. Main 138 MHz WSPR/keyed matrix attempts, preceding firmware | 104/104 rows, 174 finite jobs | 100% of attempts |
| 4. WSPR external decode acceptance, preceding firmware | 78/78 captures; 26/26 tested board/band rows | 100% |
| 4. WSPR rows with three frames, preceding firmware | 26/26; all main repetitions complete | 100% |
| 4. Three-observation human-copy rows, preceding firmware | 78/78, all passing, 234 observations | 100% |
| 4. Repaired-firmware main three-observation rows | 104/104 accepted with separate 6 m reconciliation; original 103-pass/1-failure flags preserved | 100% |
| 4. Repaired-firmware main observations | 312/312 accepted captures, including 3 supplemental external decodes | 100% |
| 4. Pre-clock Tone captures and analyses | 26/26 captured/analyzed/close-in; 26 resource passes, 1 frequency-only legacy flag retained | 100% of observations |
| 4. Repaired-firmware affected DFCW observations | 12/12 human/resource passes | 100% of diagnostics |
| 4. Repaired-firmware 80 m Tone/WSPR baselines | 4/4 pass, including 2/2 external decodes | 100% of baselines |
| 4. Refreshed alternative-clock campaigns | 0/2 successfully closed; preserved stopped campaign | 0% of accepted campaigns |
| 4. Repaired-firmware alternative-clock accepted physical observations | 55/270; 75 logical attempts, 10 receiver overflow failures and 10 unsupported labels | 20.4% accepted |
| 4. Alternative-clock physical rows, preceding firmware | 59/270 complete; two additional failed attempts | 21.9% |
| 4. Required post-comparison 138 MHz Tone sweep | 0/26 | 0% |
| 4. 150 MHz/4 m repeated mode rows | 0/10; follow-up prepared | 0% |
| 4. Direct 2 m boundary checks | 0/30; unarmed checks prepared | 0% |
| 4. Actual 2 m WSPR pilot | 0/2 observed decodes; 2/6 planned frames executed, repetitions stopped for diagnosis | 0% of required decodes |
| 4. Actual 2 m third-harmonic mode/clock rows | 0/30; conditional on reliable pilot decoding | 0% |
| 5. Main timing/capture analyses | 174/174 | 100% |
| 5. Paired Tone/QRSS diagnostic captures | 6/6, plus all separate analyses | 100% |
| 5. Requested frequency-compensation trials | 6/6 | 100% |
| 5. Dedicated wideband spectral surveys | 4/4 complete; interpretation/audit remain | 100% of acquisitions |
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
The October 10 repaired-firmware pilot continuation below is the first actual
2 m acquisition; completed evidence is counted only after capture and analysis.

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

The follow-up is now concretely queued from committed host tools `21ef82e`.
All 36 tests also pass on wspr5. Archive SHA-256 is
`95c659581a9d227b5e51529b4ddc38247fb00b2b3a5d9ddaf081d38520d9c7dc`,
with all 1,811 extracted files verified. Finite coordinator SHA-256 is
`88ab46e03ca640b7637c9a6fd4a6d62be64c684c8a52e4c31e54208a7c432874`.
PID 2418816/start ticks 48657084 is verified waiting with zero started steps
for the exact `6443197` coordinator PID 2335036/start ticks 46766222, its
unchanged script hash and successful conditional five/eight-step boundary.
It then runs pre-inventory, reference brackets, two finite follow-up jobs,
separate assessment and final inventory. Neither earlier queue was stopped or
modified; active PID 2312716/start ticks 46309764 is unchanged. The added
validation allowance is now 2–4 hours, with unresolved cause and original
failure still explicit; the remaining estimate is 15–25 hours at this checkpoint.

At the 2026-10-09 18:50 UTC checkpoint, all eight original one-hour jobs have
separate diagnostic analyses. Their per-job resources, comparable idle-growth
assessment and human-aware RF aggregate pass. The original browser workload
still fails and the original strict RF composite flags remain unchanged.
Private assessment `assessment-original-diagnostic.json` has SHA-256
`7e959f90dcdcb5b5e2a086d78c278c94144f59b2e7b9f4e3e4fb8fce3dff1b24`.
Its offline analysis took 5,411.30 seconds (90.19 minutes).

The active continuation has moved to its 36 missing main WSPR frames. Ten
additional frames are verified against immutable analysis/physical/job identities;
all externally decode and pass their resource assessment. This yields 52/78
required frames (66.7%) and 13/26 complete three-frame rows (50%). A's 60 m,
40 m, 30 m, 20 m and 17 m rows gained their two missing observations. The other
26 additional frames remain queued. Current observed acquisition/analysis throughput
is about 199 seconds per added frame; remaining capture time is about 1.13 hours,
plus analysis/finalization. Neither the 2 m/4 m queue nor the memory follow-up
has started; their verified process identities remain unchanged. No active
test was interrupted or duplicated. Phase 14 remains at three closed workstreams;
the refreshed overall estimate is 14–24 hours, including the pending memory check.

At the 2026-10-09 20:48 UTC checkpoint, all 36 additional main WSPR frames have
completed and externally decoded with passing resource assessments. Combined
coverage is 78/78 frames and 26/26 three-frame board/band rows, from 2200 m
through 6 m at 138 MHz. A separate check rebinds all new immutable analysis
hashes, physical hashes and source/device/boot/job identities; full independent
raw-IQ auditing remains pending. Closed repetition-summary SHA-256 is
`b0c7b3e952c629df715bfc949c39ea08ed909237b7a2f74c0ba4bfe9321ca10e`.
No residual/drift flag excludes any decoded WSPR row.

All four A/B × 80 m/6 m spectral surveys completed. Each contains 44 source
on/off captures at 11 tunes and two gains, plus independent final-off evidence:
180 receiver captures in total. Coverage includes harmonics one through five,
sample-clock and twice-clock images. These qualify recorded acquisition/control
coverage only; uncalibrated cross-frequency response and receiver-product
attribution still limit interpretation, and no output filter was present.
Survey result SHA-256 values are A/80 m
`aeadd4ae5f562e8722f3d3ff63667fefc4a92e6ab6aec3e56cc342f4911d8a4b`,
B/80 m `94185aadf2574a65f7541e5b0fc31027f10ed4ea0ceacd8b1fca6b78c86d32c3`,
A/6 m `cd3ab00ecbf8dc6d59192120d33d20944bdb01fe6a57bd5e52cfb74c7d32886f`
and B/6 m `cc5e4c0722e09ba8a84f61f14f0061016a6abf65165deb7aac3468ec3ac23ee7`.
The same finite coordinator is now running alternate clocks (six initial
132 MHz/A rows complete at inspection). Both dependent queues remain waiting;
memory validation, remaining clock/band coverage and final release work remain
open. The refreshed overall estimate is 12–22 hours; three workstreams are closed.

At the 2026-10-09 22:47 UTC inspection, the clock comparison had stopped after
44 completed A/132 MHz rows: nine Tone screens, nine expected-message WSPR
decodes, 26 human-copy results and all 44 resource assessments pass. Eleven
legacy keyed residual/phase flags remain diagnostics. The next 17 m DFCW job
(`795c72945bea5f8f06450df7e1ad4090`, boot
`ba1515d7709465b1915075fa1b8e7741`) reached `failed` with `DEVICE_FAULT` and
`output_active=false`. RELEASE was correctly rejected in this latched state.
No engine diagnostic or DMA-error increment identifies its cause. Its terminal
timestamp is 109 microseconds after the reported launch plus the requested
17-second duration; this is an observation, not a proved completion-race diagnosis.

The closed coordinator boundary hashes are `2fdfdf8`
`bba41f5080e14c495cbc60830fdb720c2a128c1a6055ec0853229880cde4181f`,
`6443197` `c8c13924f80edeb6a9fcec9f1cfb058f3c9f0393a7f4c451a0198aa92406351c`
and `21ef82e` `2c85e482cbf7cdec15f24b68c45c15690ff7bd4aaac546e4d74450e4fcffeb9a`.
Both dependent coordinators started zero steps. Preserved failed physical
receipt SHA-256 is
`4040ce0b2a9f7de493105a533f446f07ee1304127d648ef3a2429e011e1f79f2`;
its incomplete IQ file is retained with SHA-256
`7617f4d6a281b81e3788a2d71069e5b71a1e31c04e91998301710712fe418b20`.
The 44-row snapshot has SHA-256
`81f8304524bb57d221cf576b94fcf0536a6fcee5fc17fcddd2af114f52ce420e`.

A locked receiver-visible check found 57.38 dB on-to-quiet contrast relative to
the preceding same-boot, same-setting 17 m FSKCW capture. After ownership expired,
ordinary Console REBOOT recovered A without changing its bd45 source, 132 MHz
clock or durable settings. All three finite 17 m DFCW diagnostic jobs complete
and pass human-copy/resources. A repeated
success does not erase the original fault or establish its cause. The first
diagnostic attempt stopped on an offline interval-field lookup before reboot
or RF; that attempt and its quiet capture also remain preserved.

The host adapter now retains a failed terminal and finishes the planned capture
before recovery, instead of masking the fault with an invalid RELEASE. The
clock runner can resume into a new evidence directory: it rehashes raw IQ,
metadata, physical receipts, analyses and their original tools before reusing
closed rows, rejects identity/path/source/workload substitutions and duplicate
entries, and reacquires only missing rows. Existing failed evidence is not
rewritten. All 38 affected deterministic host tests pass. These host changes do
not change firmware inputs or claim that the completion fault is repaired.

The replacement finite continuation is actually running under
`build/resume-tools-ff1cb6c`, PID 2500834/start ticks 50448441. Its source archive
SHA-256 is `a941f49371cd4884ded74d8e338fab184606db3ae95702043bb87fde956cc392`
(1,812 extracted files verified); coordinator SHA-256 is
`037e7deb1d1fba34841fb0d12f2cf9670dca2886cd4aa5a28397ab03c7f048cf`.
The completed three-job diagnostic receipt has SHA-256
`907380dacf7c62fbfc40fd42a3d880860209c78b2bb787aaba9484c8e9460398`.
The new coordinator checks each exact stopped predecessor boundary and this
diagnostic before acquiring RF. Inventory and reference preflight complete;
its third step is the clock comparison, with all 44 original rows rehashed and
reused. The first two source-identical DFCW observations were not confused with
the original failed job; none of the failed receipts were rewritten.

The current queue is a single finite coordinator: remaining clock rows and
four affected maximum-event contention cases; return both boards to 138 MHz;
26 current-image Tone captures and separate analysis/close-in assessments;
reference/inventory; six-frame 2 m WSPR pilot; conditional full harmonic
qualification; 4 m repetitions and direct 2 m boundary checks; then the two
one-hour B memory-follow-up jobs and their assessments. It has 70 steps if the
full 2 m trial does not start, or 73 if it does. A failed pilot remains open for
decode diagnosis and does not exclude the band. Final candidate installation,
completion-fault diagnosis/repair, independent audits and release closeout
remain separate required work. The hourly automation now inspects this actual
coordinator. The estimate is 12–24 hours: 5.37 hours of remaining clock capture,
the existing analysis/final-work and memory allowances, plus 1–3 hours reserved
for the unresolved completion fault. No additional workstream is closed.

At the 2026-10-09 23:49 UTC checkpoint, `ff1cb6c` has stopped after 59 completed
A/132 MHz rows: 12 Tone screens, 12 expected-message WSPR decodes, 35 human-copy
results and all 59 resource assessments pass under the operator's criteria.
Twenty legacy keyed phase/residual flags remain diagnostic. A's next 10 m
DFCW job (`1b0d1d870273786f7d412c90d2b5dec8`, boot
`db9625a325064e1b82786cfac666dfe5`) reaches `DEVICE_FAULT` 102 microseconds
after reported launch plus requested duration, with no engine diagnostic or
DMA-error increment. The host evidence-preservation repair retains its full
124 MB capture and actual terminal error. Its closed coordinator boundary
SHA-256 is `a075eeb62032e9673faa542901666c302c6612f809248bd425316221fc3b1172`;
failed physical receipt SHA-256 is
`919aaf37d77c0bf1e62520f3b437add793f691185f3ee43d0b689358d8945a73`.
A separate offline diagnostic rehashes the raw capture and confirms reproduced
human-copy marks and resource checks while retaining `CONTROL_FAILED`.
Diagnostic SHA-256 is
`f9db188e875d16a6c8a00ad580e33e1e820d4992747e4ed4b0378ef4563c76b0`.

Source review identifies a cross-core completion race: `WorkerEngine::step`
can take its initial Running snapshot before core 0 publishes an inspection,
then acknowledge that later request using the earlier snapshot. `JobService`
can therefore see stale Running just beyond its unchanged 100-microsecond
completion acknowledgement bound, despite the hardware having completed.
A deterministic threaded fixture forces this ordering; the exact stopped
worker source fails the completion assertion. The repair polls again after
accepting the request and staged clock and updates the worker's cached state
from that fresh reply. The fixture passes for both lifecycle and output
inspection, and existing missing-worker/reentrancy/unverified-shutdown tests
still fail closed. This reproduces a concrete source defect consistent with
both hardware timestamps; physical validation of the repair remains required.

All 165 documented host test groups pass, including the repaired RF worker and
stream/PIO/core checks; all 39 affected Phase 14 Python tests pass. The memory
follow-up retains its default bd45 source guard and now requires an explicit,
exact full commit when intentionally testing the repaired candidate. Its
same-boot/settings requirement and both 45-second and cache-expired windows,
1024-byte threshold and original failed assessment remain unchanged.

Because this changes firmware RPC/poll behavior, the preceding candidate is
superseded. Requalification will bind every result to the rebuilt source:
the selected 138 MHz WSPR/keyed three-observation matrix, full 132/150 MHz
comparison and affected contention, current-image Tone/spectral assessments,
producer/failure checks, eight-hour mixed soak and the separate two-job memory
follow-up. Existing raw waveforms and failures remain useful component/history
evidence; their old-source lifecycle/resource acceptance is not silently
promoted to the new firmware. The first finite stage verifies both-board
132 MHz DFCW at the two affected points, returns both to 138 MHz, establishes
80 m Tone/WSPR control/decoding, then runs the requested 2 m pilot and conditional
full harmonic trial. Remaining broad qualification follows that closed stage;
this early pilot avoids postponing the outstanding 2 m decision until another
long qualification run. Frequency placement and drift remain informational.

The repaired candidate source is
`119477a9c8c891db6f50c7a7dab7c9fbd2e16fac`, version `0.1.0-rc.2`.
All three images build from the retained SDK/toolchain. UF2 hashes are
132 MHz `32dbb9ffcc3864c7f3d16804fedb8cacc3b9a0c4cf6568b2f88277b5c1957bdf`,
138 MHz `7a73b0598c037a28edcc5886078a891701f1f76a3b26b1c4fc4c68868ab998a3`,
150 MHz `ebef8cb7ce57e9421a48ae92140e3138b6a540791d0c1ac15852379105cff247`.
An independent clean 138 MHz rebuild is identical across all 3,674,112 UF2
bytes. The primary manifest SHA-256 is
`32ef4de23d2397519bde961b0c56fea136f4ffccc28a67f0ac28124940716804`;
the local candidates and reproducibility receipt remain under
`build/phase14-rc3-worker-repair/`, outside source control.

The finite bootstrap began on wspr5 under
`build/resume-tools-119477a`, coordinator PID 2518696/start ticks 50840921,
SHA-256 `9edfbc962416b375eb775599c9f45478454867dc00fd7500dd87912a4fb8f4f5`.
Its source archive SHA-256 is
`0cfdd0e4ec0fb36cb54322a9bab8f5551ead49541f6c4f10cd4e7e3cc3ff8996`
(1,812 verified files); artifact archive SHA-256 is
`07d764ea9ead7bc0532e94e66e8a506eb0ec7ef8c20e4a8a902f36aa5690eb8f`.
Before recovery, a locked same-setting capture verifies 57.05 dB RF inactivity
relative to the retained failed-job mark. The ordinary unowned Console recovery
and new-image loads preserve durable settings. The first stage is the 12-job
DFCW verification, followed by the 80 m baseline, pilot and conditional full
2 m harmonic trial. No broad requalification coordinator is claimed running
yet; that follow-on is prepared after the closed bootstrap and pilot outcome.

At the October 10 00:54 UTC inspection, that coordinator had stopped after
13 completed steps. All 12 repaired-image DFCW observations pass human-copy
and resource checks, and both 138 MHz 80 m Tone/WSPR baselines pass their
applicable checks, including both external expected-message decodes. Step 14
failed during the GPSDO-only reference acquisition, before any Pico 2 m job.
The closed status SHA-256 is
`3fb50b8e0cd9d43a6ed1ccde91af1c5e08a29d8d30a70d24d2852cd97c44c1ea`;
the original failed pilot receipt SHA-256 is
`ac4a7cb54e6e91b69753555e4e03c03c0a9c4dce0da3c5dcefa9397f66c209be`.

The retained reference IQ is strong and coherent: its measured peak is
144,470,658.71 Hz, about 158.71 Hz from the requested 144,470,500 Hz on the
uncalibrated receiver axis. All six phase residuals are below 0.066 rad.
The nominal +/-100 Hz contrast mask misses the peak and reports 26.15 dB;
centering that same mask at the measured reference reports 99.23 dB. The
reference analyzer now uses the measured peak and saves its fit before
checking the unchanged 30 dB contrast and 0.15 rad coherence limits. A
synthetic displaced-reference/noise regression passes with all 16 RF
measurement fixtures; all 39 portable Phase 14 tests also pass. This host
analysis repair changes neither firmware nor receiver samples, transmitter
frequency correction or the informational-only frequency/drift policy.
Original capture SHA-256 is
`e92f173c6c03dcf49c02ddd45a96c6bff001e44fd074a3d36fc88171169962b6`;
the separate diagnostic receipt under the stopped root has SHA-256
`964f0a9bab9cb5a39fb75db6493add542098bfe0e74202a1891c9647129ed970`.
Both Picos were idle afterward, and the GPSDO readback restored both outputs
to 10 MHz. The stopped receipts remain unchanged; a new finite pilot
continuation will carry only unfinished work.

The unfinished pilot continuation is genuinely running on wspr5 at the
October 10 01:04 UTC checkpoint under `build/resume-tools-26f0e56`, coordinator
PID 2534731/start ticks 51188218, script SHA-256
`dc789cfd1ba4c4c0c671b4201be2895178e0748dd368622237637888e4d8814b`.
Its source archive SHA-256 is
`e82462e1478cdabe0621a38785bb586c1e66fae62f729c154396a62c3884287f`,
with all 1,812 files independently verified. It uses the exact repaired
119477a firmware artifacts; 26f0e56 changes host analysis and documentation.
All 39 portable and 16 RF measurement fixtures pass in the exact Linux
snapshot too. Its guard rehashes the stopped bootstrap boundary and checks the
exact candidate source/image before any new job. The 13 completed predecessor
steps are not repeated. The new four-capture 2 m reference bracket completed
(SHA-256 `4cd25b8f6117a79a2d48d27618ba37fde6d0e790259ba8e59f00f0b33995fd00`),
and the first Pico A WSPR capture is active. No 2 m decode is counted yet.
The finite continuation conditionally runs the full harmonic trial only after
six valid expected-message pilot decodes, then records final reference and
inventory. Native 2 m application routing still requires a separate decision
from these physical results before broad qualification begins.

The refreshed estimate remains 34–48 hours and three of nine workstreams
(33.3%). It credits the closed diagnostics and baseline and uses recent closed
captures: median DFCW helper 64.93 seconds plus 2.29 seconds analysis, and
80 m WSPR helper about 160.6 seconds plus 29–30 seconds analysis/finalization.
The roughly 25 hours of broad matrix/clock/soak/memory capture work remains,
with the separate analysis/audit/storage/final release allowance. Available
overflow storage is verified at 22.57 GiB on wspr4, 20.39 GiB on wspr2 and
18.31 GiB on wspr1; wspr5 has about 177 GiB. The first broad matrix fits current
storage, but the complete remaining campaign needs checked archival capacity.
No archive relocation has yet occurred and no broad coordinator is running.

The pilot continuation subsequently closed four steps with status SHA-256
`8ed7e492b22e9eb35b8d043401c1229881cb0c86f01946a8b237e8730869b02e`;
PID 2534731 no longer exists. Its pilot receipt SHA-256 is
`0bbb6a194a26b48cb20bfa5eb5defd3d4f084588a44144267554d8667242cd45`.
Both first WSPR frames complete control, capture and resource checks, but
neither externally decodes. The finite screen therefore stops repetitions on
each board after its first failed decode: 0/2 observed decodes, with the planned
six-frame reliable pilot unresolved. The aggregate six-frame resource decision
is false because coverage is incomplete; both observed per-job resource checks
pass. Full harmonic qualification is not initiated and native 2 m routing
remains unimplemented. This leaves 2 m open for investigation and does not
exclude a band from candidate coverage.

Pico A's indicated received tones are 144,490,793.06–144,490,816.91 Hz.
Subtracting its simultaneous nominal-axis GPSDO indication gives a fitted
base of 144,490,646.43 Hz, fitted drift -0.1263 Hz/s and 3.67 Hz maximum
state/drift-fit residual. B's fitted reference-compared base is
144,490,349.73 Hz, drift -0.1146 Hz/s and 5.61 Hz residual. These observed
frequency movements may hinder reliable WSPR reception; they carry no
frequency/drift pass/fail judgement because calibration is undecided.
Their nonlinear evolution may explain some decode difficulty, but it has not
been isolated as the cause. A fixed +300 Hz receiver DDC/dial retune on A's
unchanged IQ also fails the expected-message decode. That diagnostic receipt
SHA-256 is `7c3004f4dd8502556f742b876d072d6dc444673d5b627c6e84ab7d4e69388a3e`.
A documented wideband/OSD-depth-five decode on the identical audio exceeds its
90-second finite budget; timeout receipt SHA-256 is
`589ac8ac80720b30d67f2a6e1bb1f04b760474604bc452fa41d31fffaeda304d`.
Neither diagnostic changes the transmitter, sample time, drift or original
nominal failed evidence.

The per-symbol simultaneous reference contrast has the same nominal-mask
defect as the GPSDO-only reference CLI. Its contrast measurement now also
centers on the observed reference frequency. The old absolute-offset diagnostic
remains separate, and no transmitter/receiver samples are corrected. A noisy
synthetic signal/reference test verifies acquired reference contrast and
frequency subtraction despite the displaced receiver axis. New reductions of
the closed 2 m captures will preserve the original analyses while recovering
informational frequency-window annotations where reference quality permits.
The repaired firmware is unchanged. The first broad 138 MHz matrix/Tone stage
can proceed independently with 2 m decoding unresolved; no positive 2 m result
requiring native mapping is being promoted or bypassed.

The first broad repaired-runtime stage is now running under
`build/resume-tools-df16f5e`, coordinator PID 2539333/start ticks 51272956.
Its `matrix-continuation.py` SHA-256 is
`ff94d275727a7c6237fa23e00f192aa31b0349ccf84a6ebc1adab59140c969a7`;
state is in `build/repaired-matrix-state/status.json`. Source archive SHA-256
is `27355ac1bbc942acb297c07282c8ff996a43c1bf3ae9541a016d09ccece6ebaa`,
with all 1,812 files independently verified. The exact Linux snapshot passes
all 39 portable and 17 RF measurement tests. The source snapshot changes host
analysis; deployed firmware remains 119477a. The start guard rehashes the closed
pilot boundary, verifies its unresolved decision and the exact 138 MHz source/
UF2, requires the old coordinator to be gone, and reserves at least 70 GiB for
this first stage. Inventory and the pre-matrix reference are complete; the
first A/80 m WSPR capture is active. This finite stage has 312 planned main
jobs, 26 Tone jobs with analyses/close-in reductions, and final reference/
inventory. No later clock/soak/memory batch is claimed queued or running.

The new separate 2 m informational reduction has SHA-256
`2e0225a23c77af0563d72bff94022fe3031afa0e2c4771bda2e48b73499b9225`
at `build/resume-tools-df16f5e/build/2m-informational-rereduction.json`.
Both unchanged nominal external decodes still fail and resources still pass.
The corrected reference contrast recovers bounded wanted-tone estimates:
A 144,490,634.04–144,490,654.03 Hz, B 144,490,339.09–144,490,359.21 Hz.
Their estimated occupied envelopes extend about 56.35 Hz above the upper
conventional WSPR edge and 63.23 Hz below the lower edge, respectively.
Both annotations explicitly retain null pass/fail and no band exclusion.
This establishes an observed frequency-placement problem without deciding the
future calibration method or proving the cause of the failed decodes.

The estimate remains 34–48 hours, three of nine workstreams (33.3%), with the
2 m decoding investigation still open. Exact remaining core captures total
169.57 GiB: 8.19 hours main matrix, 6.42 hours alternative-clock rows plus
692 seconds contention, 1,300 seconds Tone, 29,160 seconds mixed-soak capture
and 7,290 seconds memory-pair capture. Idle observations, per-job analysis,
other producer/failure/upper-band/spectral work, audits, checked archives and
final installation/review/commit/push remain additional. About 176 GiB is free
on wspr5; first-stage capacity is sufficient, while later stages require
checked evidence archival capacity and reserve. No raw evidence has been
relocated or discarded.

At the October 10 01:58 UTC checkpoint, the exact broad-stage process remains
PID 2539333/start ticks 51272956 with its original script hash. Six of 104
three-observation rows are closed and passing (5.8%); 20 of 312 individual
observations are closed (6.4%). All 20 applicable mode and resource checks pass:
six expected-message WSPR decodes, six QRSS, five FSKCW and three DFCW
observations. The closed rows cover A/80 m in all four modes and A/2200 m WSPR
and QRSS; the partial FSKCW row is still open. Private source/job-bound progress
snapshot `build/progress-evidence-20261010T0158.json` under the active root has
SHA-256 `0b97e5cb6df49c6698cce7e12bba22af3869969c746a6314e7b5492c60b6027d`.
Its row snapshot SHA-256 is
`3cf9cb1da2c02914d2d8dbaa1bb910700a2f626317cfb7274599e7805f785d05`.

The refreshed overall estimate is 33–47 hours. Remaining main capture time is
27,482 seconds (7.63 hours); applying observed closed-job pipeline medians gives
about 8.57 hours for its remaining 292 observations before the Tone/reference
tail. Median WSPR helper/analysis pipeline is 184.22 seconds, QRSS 86.23,
FSKCW 86.58 and DFCW 67.27. The complete remaining work still includes other
clocks, reliability/memory, producer/failure/upper-band/spectral testing, audits,
storage and final release work. Three of nine workstreams remain closed
(33.3%); partial rows do not close a workstream. The 2 m decode investigation
remains unresolved, with all placement/drift findings informational.

Available wspr5 capacity is about 172 GiB. The private archive plan
`build/phase14-evidence-archive-plan.json` identifies four complete historical
A soak captures (indices 0, 2, 4 and 6, 27.16 GiB total), with exact raw/
metadata/physical hashes, for independently verified copies on authorized
wspr4/wspr2. Execution is prepared for a verified acquisition boundary between
finite stages; the active matrix is unchanged. No copy or relocation is claimed
performed. Both independent destination and unchanged source verification,
explicit location/retrieval manifests and preservation of original failed
receipts are required before any source-space relocation.

At October 10 02:51 UTC, the same coordinator is still running with its
original PID/start ticks/script hash. Sixteen of 104 repeated rows are closed
and passing (15.4%), covering A/80 m, 2200 m, 630 m and 160 m in all four
main modes. Forty-nine of 312 observations are closed (15.7%): 13 expected-
message WSPR decodes and 12 observations each of QRSS, FSKCW and DFCW. All 49
mode and resource checks pass. A/60 m WSPR is active. Private progress snapshot
`build/progress-evidence-20261010T0251.json` under the active root has SHA-256
`f963d3f4a6004cdc5d557c353bb5d2496d915ba4823f946cfdfba6e1bf93c833`;
the row snapshot SHA-256 is
`f95589be29e9e5c3ed5770ea77b0f2c1a54ddcddc670ba9904b7fefdd8106288`.

The new overall estimate is 32–46 hours, with three of nine workstreams
(33.3%) closed. Remaining main capture time is 24,792 seconds (6.89 hours);
observed helper/analysis medians project about 7.74 hours for the remaining
263 main observations before the Tone/reference tail. Other clocks, soak/
memory, producer/failure/upper-band/spectral work, 2 m diagnosis, audits,
evidence storage and final installation/review/commit/push remain included.
The estimate credits verified completed jobs and measured runtimes without
closing a partial workstream. Available wspr5 storage is about 167 GiB.

The private copy-only helper is prepared at
`build/phase14-archive-closed-evidence.py`, SHA-256
`0678421c980f05e7bdeff1e195a8262087efcd3af9071815dfcacb65ce7fda48`.
Local plan validation/compilation passes. Its live `--probe` correctly returns
`BUSY` for the exact active coordinator before taking bench locks or creating
archives. It requires a successfully closed main/Tone stage and verified final
idle inventory, holds the existing receiver/board locks only at that quiet
boundary, streams closed evidence to the authorized destinations, independently
hashes destination and unchanged source files, and records explicit locations.
It has no source-removal operation. Real copying and destination verification
have not run; no archives or relocated raw evidence are claimed completed.

At October 10 04:01 UTC, the original coordinator remains running with the
same PID/start ticks/script hash. Twenty-eight of 104 three-observation rows
are closed and passing (26.9%), covering A/80 m, 2200 m, 630 m, 160 m, 60 m,
40 m and 30 m in all four main modes. Eighty-five of 312 observations are
closed (27.2%): 22 expected-message external WSPR decodes and 21 observations
each of QRSS, FSKCW and DFCW. All 85 applicable mode/resource checks pass;
A/20 m WSPR analysis/repetitions are active. The private verified snapshot
`build/progress-evidence-20261010T0404-verified.json` under the active root has
SHA-256 `5f95f0544c0a4a09777feb47522c0ba04761b1a06c1fe798a9e181a8dca00028`;
its rows SHA-256 is
`81a637900753e94a854598650d413f5721c405d25213e0d294a60c3da0337902`.
WSPR acceptance is independently checked against actual decoder stdout and
its serialized receipt. An initial private progress reduction incorrectly
looked for the in-memory summary flag in the persisted report; its false
WSPR flags are superseded by this verified reduction, with no test or original
result changed.

The refreshed estimate is 31–45 hours, with three of nine workstreams (33.3%)
closed. Remaining main capture time is 21,390 seconds (5.94 hours); measured
helper runtimes and analysis publication intervals project 6.69 hours for the
remaining 227 observations, before 26 Tone jobs and final reference/inventory.
Other clocks/contention, mixed soak, memory follow-up, producer/failure/
upper-band/spectral work, 2 m diagnosis, archives/audits and final installation/
review/commit/push remain included. About 160 GiB remains on wspr5; remaining
core captures require 154.50 GiB before other workloads/reserve. Checked archive
execution is still prepared for the quiet boundary, with no copies or source
relocation performed.

A separate offline 2 m symbol reduction is retained under the active root as
`build/2m-symbol-diagnostics-20261010T0406.json`, SHA-256
`ceaf4fe8a062dc9106dd93465001f6ef715fa7d97faf3323c5acecc11bbcd97b`.
The exact reducer binding is saved beside it; the reducer SHA-256 is
`b006d9b95a9deea2c8a402a7704d20e8b143d140cd9dab6fb21aaf75f5840e36`.
It subtracts exact accepted harmonic event frequencies from existing symbol
fits for diagnostics only, preserving original IQ, audio and decoder results.
A's indicated received tones span 144,490,793.06–144,490,816.91 Hz; B's span
144,490,496.19–144,490,519.09 Hz, close to the nominal decoder center. Thus a
constant tuning displacement alone does not explain both failed decodes.
Both boards show a nonlinear transient: reference-compared, state-removed
slopes over the first 20 symbols are about -0.354/-0.490 Hz/s for A/B, reducing
to -0.073/-0.046 Hz/s over the last 40. Whole-frame linear residual RMS is
0.933/1.412 Hz. Symbol phase residuals remain below 0.077 rad, minimum amplitude
ratios exceed 0.928, and fitted transitions are within 3.3/1.6 ms for A/B.
These observations identify a useful next investigation without isolating the
physical cause or proving why decoding fails. No new RF/decoder trial or full
2 m qualification has begun; drift/placement retains null pass/fail and no
band exclusion.

At October 10 04:57 UTC, the original coordinator still has the same
PID/start ticks/script hash and is running the main matrix. Thirty-eight of
104 repeated rows are closed and passing (36.5%); 115 of 312 observations are
closed (36.9%). Actual external decoder stdout/receipts confirm 30 expected-
message WSPR decodes; 30 QRSS, 28 FSKCW and 27 DFCW observations pass human-copy
checks. All 115 resources pass, with no new mode/resource/control failure.
A/15 m FSKCW is active. The private verified progress snapshot under the
active root is `build/progress-evidence-20261010T0457-verified.json`, SHA-256
`037be7f85f6612c9e39cbeaf2e9c811ae48e344303e2aba629dee3c3b2b6af5c`;
its rows SHA-256 is
`95455ba09157dd70dc84ed7f086aa29f7d0f690cdd7c662cc09e4be1ca3b5ad6`.

The refreshed overall estimate is 30–44 hours, still three of nine workstreams
(33.3%) closed. Main remaining capture time is 18,490 seconds (5.14 hours);
measured helper runtimes and analysis publication intervals project 5.79 hours
for the remaining 197 observations before the 26 Tone/reference/inventory tail.
All other clocks/contention, soak/memory, producer/failure/upper-band/spectral
work, 2 m investigation, archives/audits and final installation/review/commit/
push remain included. Available wspr5 capacity is about 155 GiB; remaining
core captures require 149.09 GiB before other work/reserve. The 2 m pilot
remains unresolved; no new RF/decoder trial or native mapping was initiated.

Pre-transfer review repaired the private archive helper's quiet guard lifetime:
the earlier two-hour guard could expire before both hosts' combined bounded
transfer/hash operations. Its finite lifetime is now six hours, with explicit
liveness checks after copying/verification and before final publication.
A failed attempt now preserves a failed-copy receipt and all partial copies.
The copied file inventory also includes the exact closed soak summary,
original assessment (including its browser failure), and historical candidate
source/toolchain/runtime-input manifest, alongside per-index IQ, metadata,
physical/control/idle/events and both original/diagnostic analyses. Independent
destination and unchanged-source verification covers those companions as well.
The original helper is retained privately as
`build/phase14-archive-closed-evidence-0678421c.py`. The prepared current helper
at `build/phase14-archive-closed-evidence.py` has SHA-256
`5962aa5ad62dcca9293119407725ba73f46fb86ccaaaa7dc79f7c10a42ef4606`.
Syntax/plan validation passes, and its live probe still returns `BUSY` before
locks/copies for the exact active coordinator. Actual transfers remain
unvalidated and unexecuted; no source file has been removed or relocated.

At October 10 06:01 UTC, the same original coordinator remains running with
unchanged PID/start ticks/script hash. Fifty of 104 row attempts are closed
(48.1%): 49 have three passing observations and A/6 m WSPR retains one original
nominal-receiver decode failure. There are 150 of 312 physical observations
closed (48.1%). The original analyses have 149 mode passes and 150 resource
passes: 36 nominal expected-message WSPR decodes, 39 QRSS, 38 FSKCW and 36 DFCW
human-copy observations. A/6 m FSKCW analysis was active. Private verified
snapshot `build/progress-evidence-20261010T0559-verified.json` under the active
root has SHA-256
`06fa783b41d0863a3a42fd0187bd8b5f0d96d0fc883096b1ebf6277b5a3c4eeb`;
its rows SHA-256 is
`4bdefa85f64d4919c361ed862f634cbafd927426be0000d1fa05e4de3c6b7ac0`.
The failed first-frame row caused the original runner to omit its remaining
two WSPR repetitions. This does not exclude 6 m from qualification.

The retained A/6 m signal is indicated at 50,294,622.86–50,294,632.23 Hz,
roughly 125 Hz above the decoder's nominal center. One separate fixed +125 Hz
receiver-demodulation trial on the unchanged IQ recovers AA0NT EM18 37 in
2.10 seconds with the same external decoder/options. No transmitter, time or
drift correction was applied. Supplementary receipt
`receiver-retune-125hz-diagnostic/result.json` beside the original case has
SHA-256 `ddd3039fde8d1118050ed13962e6de57ca4fe5ff1dbd035720ec229efa53a22c`;
the exact offline tool SHA-256 is
`79846d76e8f14a022c9eba9242a4ddbb406282625dd4ac51b9ba8c19dacb23d2`.
Independent stdout/audio/decoder verification is saved under the active root
as `build/6m-receiver-retune-verification-20261010T0603.json`, SHA-256
`af513f765b2b12c4ec350f5408f4ce38faba465a3ad8ac77e671bd3d39c3f8aa`.
This accepts that one retained capture under the operator's external-decode
criterion: 37 externally decoded WSPR captures and 150 total accepted mode/
resource observations including the supplement. Original failed decoder,
analysis and matrix row flags remain unchanged; reliable three-frame coverage
still requires two new physical A/6 m WSPR observations. Their finite plan is
private `build/phase14-6m-missing-repetition-plan.json`, prepared for a verified
quiet boundary after the current stage and not queued or running. The 2 m
pilot remains unresolved; frequency/drift annotations do not fail any band.

The refreshed overall estimate is 29–43 hours, still three of nine workstreams
(33.3%) closed. Remaining required main capture is 15,320 seconds (4.26 hours);
observed helper/analysis intervals project 4.81 hours for 162 remaining slots,
including the two missing 6 m frames. Only 160 of those jobs remain in the
actual first-stage queue; the two follow-up frames are already included in
this budget. Other clocks/contention, soak/memory, producer/failure/upper-band/
spectral work, 2 m diagnosis, archives/audits and final installation/review/
commit/push remain included. Storage accounting explicitly includes another
26 Tone captures after the alternative clocks: the current stage's 26 Tone
jobs precede that comparison and cannot close its documented post-comparison
sweep. These 1,300 seconds were already inside the other-work time allowance;
the explicit full core baseline is now 171.99 GiB and remaining core raw data
145.61 GiB before other work/reserve, against about 149 GiB free on wspr5.
No archive transfer, relocation or active-test/firmware change occurred.

At October 10 06:58 UTC, the same original coordinator is running with its
unchanged PID/start ticks/script hash. Sixty of 104 row attempts are closed
(57.7%): 59 have complete passing repetitions, while the original A/6 m nominal
decode failure remains preserved with its accepted supplemental decode and
two physical repetitions still missing. There are 180 of 312 closed captures
(57.7%). Original analyses pass 179 mode checks; the independently reverified
6 m supplement accepts the remaining capture. All 180 resources pass. WSPR has
44 nominal expected-message decodes plus one supplemental decode; QRSS, FSKCW
and DFCW each have 45 human-copy passes. No new failure appeared. B/630 m WSPR
is active. The private progress snapshot under the active root is
`build/progress-evidence-20261010T0658-verified.json`, SHA-256
`f18d7b162c41dba4cabac55758d7fa527e6fd3bc72950a663ea628f90a5ae926`;
its rows SHA-256 is
`31c40b4d853b6cd5a8de8e3a1509bb2f81216b3c98d37a88205d514fd7fc0046`.

The refreshed estimate is 28–42 hours, with three of nine workstreams (33.3%)
closed. Remaining required main capture is 12,474 seconds (3.47 hours); measured
helper/analysis intervals project 3.91 hours for 132 remaining slots, including
the two missing A/6 m frames. The active stage has 130 jobs left; those two
follow-up frames remain separate prepared work. Both Tone sweeps, alternative
clocks/contention, soak/memory, producer/failure/upper-band/spectral work, 2 m
investigation, archives/audits and final installation/review/commit/push remain
included. Remaining core raw data is 140.31 GiB before other work/reserve;
about 144 GiB is free on wspr5. Storage work still waits for the quiet boundary,
with no archive transfers or relocation. The 2 m pilot remains unresolved.

The finite two-frame acquisition helper is prepared privately at
`build/phase14-6m-followup-prepared.py`, SHA-256
`ebea05fe7a6838a737c7f2577e5f0acfd63914ea0493f62e865c6b3e65339d80`.
Syntax checking and its live `--probe` pass: it returns `BUSY` before device
access during the active campaign. Before execution it requires successful
closure of the exact current main/Tone stage, the predecessor process to be
gone, matching final inventory, independently reverified retained first-frame
IQ/metadata/control/audio/decoder evidence, an exact staged helper checksum,
and matching live source/clock/boot on both boards. It takes both board locks
and the receiver lock, admits only two new finite WSPR frames with a 30-minute
script bound, preserves nominal analyses and uses a fixed receiver retune only
when the nominal external decode fails. It verifies natural completion,
resources and final inactive inventory and restores reference settings; failed
cleanup cannot publish a successful stage. This helper has not been staged
for execution or run RF. The active tests and firmware remain unchanged.

At October 10 08:06 UTC, the exact original coordinator, start ticks and
script hash are unchanged and the matrix is still running. There are 72 of
104 closed row attempts (69.2%): 71 full repeated passes and the preserved
original A/6 m nominal-decode failure, whose supplemental decode is accepted
but whose two remaining physical repetitions are prepared separately. The
216 of 312 closed observations (69.2%) have 215 original mode passes plus
that independently reverified supplemental pass; all 216 resources pass.
WSPR has 53 nominal expected-message decodes plus one supplemental decode;
QRSS, FSKCW and DFCW each have 54 human-copy passes. No new failure appeared.
B/40 m WSPR is active at this checkpoint. The private progress receipt is
`build/progress-evidence-20261010T0802-verified.json` under the active root,
SHA-256 `f4bddfba8838ec5bd472cf1f228d94e13a18598825faba13340dd94c1be8614f`;
its rows SHA-256 is
`a80d2a6aa704628eb3fbe3d51fd991cf21afe74ffa147164a9e89372e25e7906`.
This verifies actual expected-message decoder stdout/receipts, physical and
analysis bindings, capture metadata/size and resources. Full independent raw
IQ rehashing remains part of the later audit.

The refreshed estimate is 27–41 hours, with three of nine workstreams (33.3%)
closed. Required main capture is 9,072 seconds (2.52 hours); observed
helper/analysis intervals project 2.84 hours for 96 remaining slots, including
the two prepared A/6 m frames. The active stage itself has 94 jobs left.
Other fixed capture/observation work totals 17.76 hours: alternative clocks,
contention, both 26-Tone sweeps, the eight-hour mixed soak and the memory pair.
An inclusive additional 6.3–20.3-hour allowance covers remaining RF checks,
analysis, 2 m/memory diagnosis, evidence storage/audits and final installation,
review, commit, push and closeout. These diagnosis/analysis subdivisions are
not additional quantities to add again. Remaining core raw data is 133.97 GiB
before other work/reserve, against 137.34 GiB free on wspr5. The current stage
fits; independently verified archives and necessary relocation must precede
later acquisition. The archive and two-frame helpers remain prepared and
unexecuted. Reviewing their guards and the alternative-clock candidate/receiver
handling did not change an active test or firmware. The 2 m decode outcome
remains unresolved, with all placement/drift annotations informational.

At October 10 08:56 UTC, the original coordinator, start ticks, script and
firmware remain unchanged. There are 81 of 104 closed row attempts (77.9%):
80 complete repeated passes and the preserved original A/6 m nominal-decode
failure with its accepted supplement and two prepared missing repetitions.
There are 243 of 312 closed observations (77.9%); 242 original mode passes
plus the independently reverified supplemental decode accept all 243, and
all 243 resources pass. WSPR has 60 nominal expected-message decodes plus
one supplemental decode; QRSS has 62 human-copy passes and FSKCW/DFCW have
60 each. Partial-row observations are counted without calling that row
complete. No new matrix failure appeared. B/20 m QRSS is active at this
checkpoint. The private receipt is
`build/progress-evidence-20261010T0858-verified.json` under the active root,
SHA-256 `b5768fdf2dee4634ca4abb2d70150ad7cc7045355bedd7fc5a8e88bfa1d5e12b`;
its rows SHA-256 is
`833bae1c135eaa3e9728aef98456ec133180fd7d4ed14413172bcdb47d9f308b`.
Actual decoder stdout/receipts, resource results and physical/metadata/analysis
bindings were rechecked; the later full raw-IQ audit remains required.

The refreshed estimate remains 27–41 hours, with three of nine workstreams
(33.3%) closed. Required main capture has fallen to 6,488 seconds (1.80 hours);
observed helper/analysis intervals project 2.03 hours for 69 remaining slots,
including the two separately prepared A/6 m frames. The active stage has
67 jobs left. The unchanged fixed capture/observation workload is 17.76 hours,
plus the inclusive 6.3–20.3-hour allowance described above. The resulting
26.10–40.10-hour range rounds upward to 27–41 hours; this is a calculation
from remaining work, rather than an elapsed-time countdown. Remaining core
raw data is 129.16 GiB before other work/reserve, against 132.55 GiB free on
wspr5. Archive transfer/relocation remains prepared for the successful quiet
boundary and has not been executed. No active test or firmware was changed.

A separate low-priority offline diagnostic at 08:58 UTC ran the installed
external decoder on B's unchanged retained 2 m WAV, using its original
receiver frequency/window and adding only `-o 1`. Installed decoder help
confirms this OSD depth is supported. The 90-second bounded process exited
normally in 5.15 seconds with `<DecodeFinished>` and no expected-message match.
Receipt `build/2m-b-osd1-diagnostic-20261010T0902/result.json` under the active
root has SHA-256
`151070bfe3a743bb3dfd22b64b3b50e028839a5e511fa22d61544cdec36dacbd`.
The private source helper SHA-256 is
`ad15823385acf085c03815e171f507d0252575f1d8dc6a709f8aa480fe471d49`.
Independent verification rehashed actual stdout/stderr, decoder and all bound
original WAV/control/metadata/analysis/decoder receipts. No RF, transmitter,
receiver retune, waveform, time or drift correction was applied. The original
failure is preserved; this additional unsuccessful decode does not establish
its cause or change the unresolved pilot, frequency/drift annotations or
conditional full-qualification state.

At October 10 10:03 UTC, the exact original coordinator, start ticks, script
and firmware remain unchanged and running. There are 93 of 104 closed row
attempts (89.4%): 92 complete repeated passes and the preserved original
A/6 m nominal-decode failure, with its accepted supplement and two prepared
missing physical repetitions. The 279 of 312 closed observations (89.4%)
have 278 original mode passes plus the independently reverified supplement;
all 279 resources pass. WSPR has 69 nominal expected-message decodes plus
one supplemental decode; QRSS has 71 human-copy passes and FSKCW/DFCW have
69 each. Partial-row observations do not close that row. No new matrix
failure appeared; B/12 m QRSS is active at this checkpoint. The private receipt
is `build/progress-evidence-20261010T1005-verified.json` under the active root,
SHA-256 `7c68be047aa6a474d5f3537dd2770f2e5ad079e45c53602227d721ca7fe6a833`;
its rows SHA-256 is
`b9f6e8d687ce99fa33cddf585a24e55ea467bd091ae2f8a89fdf4b0ad0a078ef`.
Actual decoder stdout/receipts, resources and source/job/metadata/analysis
bindings were rechecked. The later full independent raw-IQ audit remains open.

The refreshed estimate is 26–40 hours, with three of nine workstreams (33.3%)
closed. Required main capture is 3,086 seconds (0.86 hours); observed
helper/analysis intervals project 0.97 hours for 33 required slots, including
the two prepared A/6 m frames. The active stage has 31 jobs left, followed
by its 26 Tone jobs, analyses, close-in reductions and final reference/inventory.
Other fixed capture/observation work remains 17.76 hours, with the inclusive
6.3–20.3-hour additional-work allowance. Remaining core raw data is 122.82 GiB
before other work/reserve, against 126.28 GiB free on wspr5. The current stage
fits; storage relocation remains necessary before later acquisition.

A separate private relocation helper is prepared at
`build/phase14-relocate-verified-raw-prepared.py`, SHA-256
`5c10fab4f81152ac5b996c5a0f1d90e6aada68b0cafe8378b7c007689b3d6dc9`.
It pins the existing copy-only helper, exact four-job archive plan and successful
copy receipt/checksum. At the successful current-stage quiet boundary, it
holds both board/receiver locks, independently rehashes every destination file
and unchanged source, publishes explicit location/retrieval records on all
three hosts and locally, then reverifies each destination raw before removing
only its redundant, exact source raw file. It checks the source raw hash,
inode/size/timestamps and unchanged physical/metadata receipts immediately
before removal. All original receipts and retained archive bytes remain.
Separate final or partial-failure records preserve recovery locations and
identify removals without overwriting the copy receipts. Its bounded operations
fit inside the existing six-hour quiet guard. Local/generated-script compilation
passes, and live `--probe` returns `BUSY` before any copy/removal operation.
Actual successful transfer and relocation paths remain unexecuted/unvalidated;
no evidence has been copied or relocated and no active RF test was changed.
The 2 m pilot remains unresolved with informational frequency/drift annotations.

At October 10 11:02 UTC, the main matrix step is complete while the exact
original coordinator continues its pre-clock Tone sweep. All 104 row attempts
are closed: 103 have complete passing repetitions, while the preserved original
A/6 m nominal-decode failure has an independently accepted supplement and
two new physical repetitions still prepared separately. The 310 closed main
observations out of 312 required (99.4%) satisfy operator mode criteria and resource checks:
309 original mode passes plus the reverified supplement. WSPR has 75 nominal
expected-message decodes plus one supplemental decode; QRSS, FSKCW and DFCW
have 78 human-copy passes each. No new matrix failure appeared and no band is
excluded. Three of 26 pre-clock Tone control/captures are complete (11.5%),
with zero completed analyses or close-in reductions; A/80 m Tone is active.
Captures are not promoted to analyzed Tone acceptance. Firmware, PID/start
ticks and script hash remain unchanged. The private receipt is
`build/progress-evidence-20261010T1105-verified.json` under the active root,
SHA-256 `80bba683b1e2a90b6d286e0a83432aa92c34ddcb1314af1cac29566299bed8fd`;
its matrix rows SHA-256 is
`265da12e0085df149d11c482e482f0552e89b9c65debfba77553e426576a9142`.
Actual decoder stdout/receipts and source/job/metadata/analysis/resources were
rechecked; the later full independent raw-IQ audit remains required.

The refreshed estimate is 25–39 hours, with three of nine workstreams (33.3%)
closed. Required main capture is now only the two prepared A/6 m frames,
312 seconds (0.087 hours), with an observed pipeline estimate of 0.103 hours.
The active stage still owes 23 pre-clock Tone captures, all 26 analyses/close-in
reductions and its final reference/inventory. Remaining fixed capture/observation
work totals 17.72 hours after deducting the 150 verified Tone capture seconds;
the inclusive additional-work allowance remains 6.3–20.3 hours. Remaining core
raw data is 117.38 GiB before other work/reserve, against 120.79 GiB free on
wspr5. All follow-ons, archive copies and relocation remain prepared rather
than running. The exact successful main/Tone quiet boundary has not yet been
reached, so neither follow-up acquisition nor evidence relocation was started.
The 2 m pilot remains unresolved and all frequency/drift annotations remain
informational. No active test or firmware was changed.

The finite main/Tone stage closed successfully at October 10 11:28 UTC,
with all 59 steps complete and coordinator PID 2539333 gone. Its immutable
status SHA-256 is
`4130d4fa3eec9aafd58ff706e0814228df54f5855fc85b1b058ce482bcb5a1db`;
final idle inventory SHA-256 is
`14c26ee225b092705652e4e0d3879beaf18c2589e6dfa55ede559ea3cff9ea06`.
All 26 Tone captures, analyses and close-in reductions are closed with valid
resources. The retained A/6 m Tone legacy flag arises solely from nominal
receiver-axis offsets of +136.36 to +137.24 Hz exceeding the old 100 Hz screen.
All ten coherence/amplitude/reference checks pass: maximum phase residual
0.01673 rad, minimum amplitude ratio 0.99783; reference-compared mean is
50,294,579.95 Hz with 0.868 Hz peak-to-peak range. Under the operator amendment
this frequency observation has null pass/fail and excludes no band. Its
original analysis SHA-256 remains
`376907b5bcc61e533a159ab5f696fe2e6913a6d00d76951038eae0b8c36c5a5e`.
The separate closed-stage progress receipt under the original root is
`build/progress-evidence-20261010T1208-verified.json`, SHA-256
`7d31866b99fa060ec208c22602edf92ec34add46522357b65fe97ac2aa7b357c`.

At the verified quiet boundary, the exact two-frame helper was staged and
executed on unchanged 119477a/138 MHz firmware. Both new A/6 m frames completed
control/capture/resources and decoded AA0NT EM18 37 after the same fixed
+125 Hz receiver demodulation retune. No transmitter, waveform, time or drift
correction was applied. All 312 required main observations now meet operator
mode criteria/resources: 75 nominal plus three supplemental WSPR decodes,
and 78 human-copy observations in each keyed mode. The original failed 6 m
row remains unchanged; its third-frame coverage is accepted separately.

The follow-up's final inventory rejected CAPS with `HELLO_REQUIRED` from a
cached WTP peer. The original failed closeout receipt is preserved at
`build/repaired-main-6m-missing-repetitions/result.json`, SHA-256
`2409c1aec9156af380b9fb7c1beb4001343f4920eeb1afed8821a3a3df819621`.
Its two decoded RF frames were not repeated. A separate fresh-session inventory
confirmed both named boards unowned, disabled and empty on the expected
firmware/clock; SHA-256
`7ce17508656e9fe554c1bb4f3908217d8ef5216eda43faa7150bde8a03f6c3c3`.
Independent verification rehashed both actual raw captures, metadata/control,
nominal analyses, supplemental WAVs/decoder/stdout/stderr and the recovery
inventory. Reconciliation receipt
`build/sixmetre-followup-reconciliation-20261010T1222.json`, SHA-256
`5eca42406d8d377c03f9fd1b858ebb2069147732f24b63d12134c88bdc0931e7`,
records three-frame RF acceptance and separately recovered closeout; it does
not relabel the original failed receipt or establish why negotiation was lost.

The inventory tool now reconnects only after validating that the board is
unowned and inactive, so its new peer negotiates HELLO before inventory RPCs.
A deterministic stale-peer fixture rejects the original implementation with
`HELLO_REQUIRED`; all 40 affected tests and 17 measurement fixtures pass on
the isolated Linux snapshot. The fixture also rejects an owned/running board
before disconnecting its peer. A live repaired-tool inventory succeeds on
both boards, SHA-256
`47e06b9d73652d5fbc8b3839e095e7f1df5f306566a545743557e80cea55b4f5`;
tested `live.py` SHA-256 is
`62e58a5718d0009921c94699ee30f1d6d45e46d90b764ab23c89ded66ec4219e`.
Mac Python 3.9 lacks the existing `hashlib.file_digest` API: its new focused
fixture passes, while the complete suite uses the verified Linux runtime.
Firmware and the original closed tool snapshot remain unchanged.

Copy-only evidence archiving is now running at the verified idle boundary,
using frozen private plan SHA-256
`9faa959e3a49a796f4ab6013f0296c38906531c5177c65d6fdba2ceb4be16f19`.
Local helper PID 81492 started October 10 12:20:24 UTC; wspr5 quiet guard
PID 2721842/start ticks 55261620 holds the board/receiver locks. Receipt
`build/phase14-evidence-copy-1791634825243653000.json` records the active copy
and all verification state. Both destination capacity checks pass. No source
raw file has been removed and no archive copy is yet claimed independently
verified. Relocation and the next clock stage remain prepared, not running.
The full repaired matrix and pre-clock Tone capture budget is complete;
the remaining fixed core workload is 17.40 hours plus the inclusive analysis,
diagnosis, storage and final-work allowance. The estimate is 24–38 hours,
three of nine workstreams (33.3%) closed. The 2 m pilot remains unresolved.

The committed inventory repair is `1024529dfe315938bc9c1299fd50d5c232a78222`.
Its separate future tool root is `build/resume-tools-1024529` on wspr5;
all 1,812 staged source files independently match source archive SHA-256
`f169db7c5d6840dee6573dea37496e5ae9ce0e69d015a01a2dc8304c95f2be47`.
Verification receipt `build/tool-source-verification.json` in that new root
has SHA-256
`b6e38a518030596aae34287aa5c29af5d4643513ac35237eb1d4653a55f12042`.
It reuses the unchanged identified 119477a firmware artifact manifest through
a private link. No firmware load or further RF job was started.

The next finite clock-stage helper is prepared privately, SHA-256
`837777737663ef5d955d305babf382271b5e4617e8f3404a889df820f8b5c01e`.
Its read-only probe recognizes the separately recovered RF closeout and
returns `RF_PREDECESSORS_CLOSED_STORAGE_RECEIPT_REQUIRED`. It remains unstaged
for execution and must wait for verified archive copies, successful necessary
relocation, 140 GiB available, exact self/source/image/runner identities and
live idle-board checks. Its 12-hour child bound covers the full clock comparison
and contention; the later post-clock Tone sweep remains separate work.

The copy is still active, with zero independently verified destinations and
all source files retained. Two read-only size samples show approximately
3.38 MB/s raw throughput, projecting 2.40 hours of streaming for all four raw
captures. At that rate the existing 3,600-second per-host copy bound may expire.
The active helper is not changed or restarted. Any failure/unknown outcome
requires inspection of preserved partial copies and source/prefix/full hashes
before bounded recovery. A 0–1-hour recovery uncertainty allowance is added
without adding the projected transfer duration again: it is already inside
the inclusive other-work allowance. The revised estimate is 24–39 hours,
with three of nine workstreams (33.3%) closed. Remaining fixed core raw data
is 114.65 GiB, versus 117.94 GiB free on wspr5 before relocation; all other
work and reserve remain additional. The 2 m decode outcome stays unresolved.

At October 10 13:13 UTC, the original copy remains active under unchanged
PID 81492 and quiet guard 2721842/start ticks 55261620. The first destination
has 10,993,935,488 raw bytes streamed; none is yet claimed independently
verified and every source raw file remains. Recent throughput is about
3.22 MB/s. The failed/partial-copy recovery is now prepared separately at
`build/phase14-resume-archive-prepared.py`, SHA-256
`030b131092a664207dfdfbb0c37271473410594f06e365e7161b85ebc392ff39`.
Seven tiny Linux fixtures pass complete-copy/hash rejection, matching-prefix
append, changed-prefix rejection, truncated-stream preservation, empty partial
handling and symlink rejection. Positive evidence transfer remains unvalidated.

A finite observer, local PID 97384, now waits for the exact original process
to end, leaving it unchanged. Its receipt is
`build/phase14-archive-boundary-supervisor-1791638061972813000.json`,
script SHA-256
`d11a48b3ea41ce3f14aafcf4ea2510b8ba4916527b705a0314b73f219b162e8c`.
It starts recovery only after a preserved failed original receipt; recovery
also checks old guard/tar processes are gone and takes the existing quiet locks.
A success or unknown outcome cannot trigger a fresh duplicate copy. Recovery
rehashes every existing prefix against its source, appends only missing bytes,
then independently verifies full destinations and unchanged sources and saves
separate location receipts. Its 19,800-second lifetime fits within the
21,600-second guard. It never removes source files.

The separate relocation helper that accepts this honestly identified recovery
provenance is prepared as `build/phase14-relocate-after-resume-prepared.py`,
SHA-256 `0319637d0953eec81cae5131224c04cd6bbc852b7f488c52c1b86c85c1dbbbe0`.
It pins the new helper and original failed receipt, while retaining full
source/destination verification and location publication before redundant raw
removal. Both original helpers remain unchanged. Relocation and clock testing
are not running. The estimate remains 24–39 hours, three of nine workstreams
(33.3%) closed, because no archive destination is yet accepted and the remaining
fixed RF/settled-observation work is still 17.40 hours. Transfer progress informs
remaining streaming time without manufacturing completed workstreams. The 2 m
pilot remains unresolved.

The original copy subsequently hit its 3,600-second destination timeout at
13:20:58 UTC. Its closed failed receipt SHA-256 is
`21db39e094984e1938e603eb5fde9413ff096b50ca70579714840a1fd3628036`;
PID 81492 and its guard are gone. The finite observer launched exactly one
recovery child, Mac PID 99470, at 13:21:07 UTC. Its separate mutable receipt is
`build/phase14-evidence-resume-1791638471854100000.json`.
The new wspr5 guard PID 2738054/start ticks 55626280 holds all three expected
lock files; its code retains SHA-256
`8232e20d1cc8f6a3c80da8ec4eef0940d3788b69d3de112f2b8e50e52fb029b1`.
Preserved destination raw sizes are 7,290,000,000 and 5,218,783,744 bytes.
Recovery has entered source/destination verification, without claiming any
accepted archive or removing source files. Relocation and clocks remain
prepared. The estimate remains 24–39 hours, three of nine workstreams closed.

At the earlier repaired-runtime checkpoint, the estimate was 34–48 hours,
with three of nine workstreams closed. That historical estimate included about
25 hours of main-matrix, alternative-clock, mixed-soak
and memory-follow-up capture/observation workloads on the repaired runtime,
plus diagnostic/pilot/upper-band tests, analysis/audits, evidence storage work,
final installations and review/commit/push/closeout. This increase follows a
regression-proven firmware defect and required requalification, rather than
slower elapsed-time subtraction. About 179 GiB remained on wspr5 then; the Mac
had about 4 GiB, wspr4 22 GiB and wspr2 20 GiB. Broad acquisition requires a checked
storage plan and, if necessary, verified relocation of closed raw evidence
between these already-authorized hosts, preserving every original receipt and
the only copy of every capture.

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
