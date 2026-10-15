# Phase 14 original closeout ledger — October 14, 2026

## October 14: Phase 14 completed within the declared scope

**9 of 9 original workstreams are closed (100%).** The operator explicitly
requested the 56 reviewed Phase14 files committed on devel, pushed to
origin/devel, independently checked for parity and closed out. Code/evidence
commit **74c73d548e2e05cf6f61978817d7de264da961ff** contains exactly those 56
files. Its push succeeded and a separate `git ls-remote` read matched that SHA.
This final documentation update changes no runtime or installed image bytes.
The final documentation commit and its independent parity proof are retained
in the private closeout receipt and reported in the chat; no self-referential
commit hash is fabricated here.

All 1,039 runtime/build/test blobs in the source commit match the frozen,
independently rebuilt and installed C96 candidate. The compiled identity remains
`dda8a6eb1e69-dirty`; it is preserved as build provenance rather than relabelled
with the later commit. Runtime SHA-256:
`c96eeeeb4871bdcec40aa5b8fbc1dce42507b5fac6b00ee3a8b41838d5836d64`.
Selected release artifact: consumer-radio-c96eeeeb4871, PIO/DMA GP2, 138 MHz,
divider1/RAM renderer. UF2 SHA-256:
`17065bc7945a91d210bf3e48aedf1c6f5772f4386e7b26c04f364553afc6adad`.
ELF SHA-256:
`0fa99101a76735ac1a319e951fd14774ee6f4ce1ba44015ffde38f8d023449f9`.
Independent 138 MHz ELF and UF2 builds are byte-identical.
The private UF2 is retained under local
`build/phase14-consumer-radio-arm-plain-admission-20261014/build-138/firmware/WsprryPico-StandaloneRF.uf2`;
its closeout manifest is local
`build/phase14-final-consumer-c96-closeout-manifest-20261014.json`.
No generated firmware, raw capture, credential or private profile is in Git.
No GitHub release or additional public artifact publication was performed.

The accepted matrix covers Tone, WSPR, QRSS, FSKCW and DFCW on both boards:
2200m,630m,160m,80m,60m,40m,30m,20m,17m,15m,12m,10m and6m, with historical
132/138/150 MHz comparisons and the selected138 candidate. All390 cells and602
accepted observations are bound to actual source/firmware/boot/job/capture
identities. Original nominal failures, receiver-only acceptance and keyed
human-copy amendments remain separate. The current [band/mode catalog](phase14-band-mode-qualification.md)
uses WsprryPi terminology: 4 m is Unqualified under the all-mode gate; native
direct 2 m is Unavailable. Failed manually mapped 2 m harmonic pilots remain
Unqualified evidence. 8 m/5 m remain Untested. This terminology update changes
no original observation, flag, receipt or release-scope decision.

The timing, spectra, reference, lifecycle, native/standalone, eight-hour mixed
and separate two-hour memory gates retain their actual reviewed scopes and
measurement uncertainties. Their full/closed source/control/raw/resource proofs
and both original retention scopes are accepted. Final source/coverage/
adversarial proof **912ea1c254067a193d0489707660510c9682a3ef082e5f6ccf019f3d388a9735**
retains every failed original. Consumer radio access, settings/persistence/
original restoration and all four smoke screens are independently accepted on
both boards, with narrow R189/C96 applicability preserved.

Final separately admitted readback verified both Picos C96/138, empty, unowned,
output-inactive, schedules disabled, synchronized clocks, ready consumer AP and
Plain LAN listeners, original settings and unchanged current cursors:
A **1791199541540946076**, B **1791705481000000000**.
Recorded boots remain A `4ac25bc51decbde2e1eb3f6cce6f75fa`,
B `67e58db2fc1a86d2f3f4add83e3cf146`. Subsequent Git-only closeout performs no
Device, flash, profile, config, cursor, RF or GPSDO mutation. Fresh process/
receipt checks show no active owned programme. Reference state is restored,
wsprrypi.service is active and wlan2 disconnected; management is preserved.
All four locks and exact source/durable presence histories remain bound.
Exactly164 CLOCK and three MIXED source absences remain separate, with all
retained copies, nonraw controls and failed evidence preserved.

The unfiltered conducted scope establishes no LPF, calibrated watts or antenna-
ready emissions. Absolute RF/timing calibration, consumer-image long endurance,
general leak freedom, hostile HTTP-page delivery and authenticated Plain LAN
remain unqualified. These are explicit retained limits, not new completion
claims. P13.1 stays complete; P13.2 Si5351 and GP14 default enablement stay deferred.
The unrelated implementation-plan bytes and Si5351 work are preserved.
Hourly reports remain ACTIVE until the final documentation push, independent
remote parity and closeout receipt are verified, then are stopped because this
Phase14 task is complete.

Earlier dated sections below are immutable historical boundaries; their old
pending/count/estimate/repository descriptions are superseded by this closeout.

## October 14: final source, coverage and adversarial audits independently closed

**8 of 9 original workstreams are closed within the recorded scope (88.9%).**
| Original workstream | Current disposition |
| --- | --- |
| 1 Initial source review | Closed |
| 2 Plan/acceptance record | Closed |
| 3 Bench/tooling | Closed |
| 4 Clock/band/mode coverage | Closed within retained operator-amended scope |
| 5 Timing/spectra/unfiltered path | Closed within recorded methods and uncertainty limits |
| 6 Reliability/failure handling | Closed under original engineering evidence identities |
| 7 Identified reproducible candidate/settings/smokes | Closed for selected consumer138 candidate |
| 8 Final source/coverage/adversarial review | Closed within the declared scope |
| 9 Git/remote parity/final report | Open; explicit Git request required |

The remaining workstream is the explicit Git request, intended-file commit/push,
independent remote parity and final closeout report. Allow **15–60 minutes of
execution after that request**; this is a planning allowance, excludes waiting
for authorization and subtracts no elapsed time. Phase 14 is not complete.

Final closed acceptance:
`912ea1c254067a193d0489707660510c9682a3ef082e5f6ccf019f3d388a9735`.
Original-workstream reconciliation:
`3732a330f0f2cebc2133e59f1b9fe40096b8063e3e6657ca6a7405417b0b14e6`.
The closure parent was 93689/start93303008; the reconciliation parent was
94270/start93315189. Fresh exact checks find both gone and no active owned work.
Both proofs have identical internal and durable bytes.

The new review verified 1,955 immutable metadata bindings, 1,039 current
runtime/build/test files, all **390** retained board/band/mode/clock cells and
**602** accepted observations. The required 138 MHz repeated-mode screens have
at least three observations. Separate A/138 MHz 6 m receiver-only acceptance
and repetitions are bound; their nominal failed flags remain false. Twelve new
adversarial cases reject source/boot/raw substitutions, missing coverage,
incomplete/overflowed captures, resource failure and bad Tone quality/reference.
The initial reviewer incorrectly used two legacy Tone placement flags; its
refusal/log/source remain preserved. The successor uses the frozen numerical
quality criteria and preserves every original flag, with no RF/DSP/decoder replay.

Fresh source/archive tuples were checked for 520 recordings across the current
and original closed scopes. Exactly 164 CLOCK and three MIXED source absences
remain separate. Existing full raw proofs were reused; no IQ was read again.
Twenty own programme/admission/source/result controls, 520,152,825 bytes, were
full-hashed source/durable and fsynced under:
`/mnt/phase14-testing/phase14-closed-internal-first/final-source-coverage-adversarial-controls-20261014`.
The closure proof and reconciliation are also durable there. All source evidence
is retained and no profile/configuration/cursor or service write occurred.

A separately admitted final boundary performed exactly two named Console INFO
reads and one read-only GPSDO query. Both C96/138 MHz Picos were empty, unowned,
output-inactive, schedules disabled, clocks synchronized, with false experimental
opt-ins and unchanged flash-write counters. Current watermarks remain
A **1791199541540946076**, B **1791705481000000000**; boots remain
A `4ac25bc51decbde2e1eb3f6cce6f75fa`, B `67e58db2fc1a86d2f3f4add83e3cf146`.
Reference state is restored, wlan2 is disconnected and wsprrypi.service active.
All four locks were held/available at the respective review/closure boundaries.

The first final-state reviewer missed its PID because it compared CPU-changing
whole `/proc/stat` records. That missing field is preserved honestly. The new
metadata-only closure uses stable PID/start/argv checks and confirms no instance
of the predecessor's exact programme remains; it makes no repeated Device reads.

The accepted scope is the operator-amended, unfiltered conducted matrix and
recorded engineering-profile reliability, plus the identified reproducible
consumer138 candidate and bounded both-board settings/control/four-smoke checks.
Older RF is never relabelled C96. Consumer-image long endurance, general leak
freedom, hostile HTTP page delivery, authenticated Plain LAN, LPF/emissions,
calibrated watts/absolute RF precision, 8 m/5 m and 4 m/2 m support are not claimed.
These documented limits remain; the current audit found no unresolved actionable
finding inside that declared scope. P13.1 remains complete; P13.2 and GP14 default
enablement remain deferred. Current source/docs/tests are uncommitted on devel,
ahead74, index empty. No staging, commit, push or publication is authorized yet.

Hourly reporting remains ACTIVE, with its original schedule and notification
policy. Earlier dated counts, estimates and pending boundaries below are historical.

## Earlier retention-only ledger boundary (historical)

Mixed and memory are separately independently accepted. Phase 14 release
closeout remains open. The original nine task headings are retained below;
accepted component evidence alone does not promote an original workstream.
The current estimate is 3–24 hours of remaining effort, with 3 of 9 original
workstreams closed (33.3%). Historical estimates, flags and receipts remain
unchanged in the results record.

The consumer radio access repair adds remaining work and may extend that range.
The user now permits private restoration evidence on the Pi or this Mac; keep
profiles, credentials and generated evidence private and out of Git. Current
flash backups and cursor comparisons remain on the Pi for this installation.

## October 14: remaining original finite retention independently accepted

The new original-other scope is exactly237 existing recordings /19,288,000,000
bytes: native19, spectra/compensation, lifecycle, standalone and preserved
excluded-band repetition/idle/connection records. No scientific workload was
repeated or promoted. The catalogue/admitter ran before IQ/Device access.
Copy parent33758/start91968401 closed3,207 files /19,593,384,927 bytes,
with all sources retained and no profile/config/cursor/service writes or removals.
Copy result067183249615f6b621f35aef92d87954590abf89ed26b2e2cb4f56693e4903bf.
Independent reviewer41803/start92142657 FULL hashed both source and archive
for every pair, including all237 raws /19.288GB on each filesystem.
Full reviewc081df4f75ae49e23c86ee9be9cf13a884bd08ab69f297a9f058575a47e90768.
Closed acceptance48657/start92284685 reused only exact unchanged just-closed
raw proofs and full-hashed all2,970 nonraw pairs /305,384,927 bytes plus controls.
Closed proof6c818feb8d0f0bf1a3b70e092f1d8cd179cb158469eda2e5b8637c0844d6ec64.
Fresh exact checks confirm these three parents and their admitters gone.
Copy/full/closed proofs are internal/durable BYTE-IDENTICAL, and fixed metadata
copies are preserved privately on this Mac. No raw/native profile bytes were
exported. All original success/failure/legacy flags and separate164 CLOCK /
three MIXED source absences remain unchanged.

Archive: /mnt/phase14-testing/phase14-closed-internal-first/final-other-finite-source-controls-20261014.
Original source/runtime/control and recursive evidence companions are retained.
The copier's four separately admitted INFO reads verified the current C96 boots,
settings and advanced cursors unchanged. Reference/capture/tool identities and
source/image scopes remain historical in their original records. These bytes
stay inside the existing original other allowance: no new scientific, capture,
core-memory-transfer or elapsed credit is invented.

The original core and original finite evidence retention scopes are now closed.
Final consolidated assertion/source applicability, adversarial and release/Git
closeout remain open. Counts stay3 of9 /33.3%, conservative estimate3–24hours.
The local adversarial audit corrected stale consumer USB/smoke documentation
and missing Noble browser dependency notices. Exact retained upstream licenses
and pinned versions are recorded; runtime/library/bundle bytes are unchanged.
Current runtime/build/test files still match the frozen installed C96 snapshot.
See the [final assertion audit](phase14-final-audit.md).

## October 14, 12:59 CT: final memory/consumer core retention accepted

The separately admitted copy closed as 20585/start91684592 with result
515c4286cccf1028fd14056929698c0ee10632766e020154cb61f7bcb068f735.
A distinct full source AND durable review, 25370/start91788757, independently
full-hashed all 6,086 pairs / 15,829,335,463 bytes, including all 14 raws /
15,532,000,000 bytes on both filesystems. Review proof:
1110d05936f9016d17a744363ab2d635325a9d6a436c67b89c4058308b437dd0.
The finite closed acceptance, 28356/start91853556, reused those just-closed
full raw proofs only at exact unchanged source/destination tuples and full-hashed
all 6,072 nonraw pairs / 297,335,463 bytes plus programme/closure controls.
Closed acceptance:
4e4c2e9c45274a14f800a2eb4c30d6f77520cb6648fafa2f09f292500d5de97a.
Fresh exact PID/start checks verify all three parents and their separate
admitters gone. Internal and durable copy/full-review/closure proofs are
BYTE-IDENTICAL; three fixed proofs were privately mirrored on this Mac.

Durable archive:
/mnt/phase14-testing/phase14-closed-internal-first/final-memory-consumer-source-controls-20261014.
The scope retains the two accepted memory hours and eight references, the four
final consumer smoke recordings, frozen DDA/R189/C96 source snapshots, native
restoration evidence, programme/admission/dispatch/execution controls and
preserved failed consumer/reviewer controls. Every source in this scope remains.
No raw/profile bytes were exported to the Mac, no sample was removed, and no
RF/DSP/decoder work or profile/config/cursor/service write occurred. The copier's
four separately admitted INFO reads preserved both current C96 boots, settings
and advanced cursors. Exactly 164 CLOCK and three selected MIXED source absences
remain separate; historical source-retained flags are unchanged.

Original memory core transfer receives 14,580,000,000 bytes credit ONCE;
128 MB references and 824 MB smoke raws remain inside the existing other allowance.
Together with the accepted mixed archive this closes all 72.9 GB original core
transfer. The fixed 37,546-second science credit is unchanged and no elapsed
credit is added. Original workstream counts remain 3 of 9 (33.3%). Remaining
inclusive other work, receiver contingency and review total
2.938081–23.688081 hours, rounded up to 3–24 hours. Consumer repairs and awaiting
explicit Git authorization can extend calendar completion.

Other finite evidence retention, consolidated assertion/source applicability,
adversarial review and final release/Git closeout remain open. A local audit
matched 1,039 runtime/build/test files to the installed C96 snapshot and all
51 reviewed RF/WTP/encoding/time files to DDA HEAD. It does not promote an
original workstream or relabel older RF as C96. The hourly automation remains
ACTIVE, hourly, with healthy notifications required and its schedule/policy
unchanged. Its short reporting prompt now returns status promptly. Missing
past notification delivery could not be verified.

Earlier dated sections below preserve historical boundaries. Their old active,
pending, source/boot and ETA descriptions are superseded by later evidence;
failed records, original flags, limits and immutable receipts are unchanged.

## October 14: corrected consumer access and final smoke screens accepted

Both Picos now have the independently reviewed consumer-radio-c96eeeeb4871
138 MHz application, honest uncommitted revision dda8a6eb1e69-dirty.
Independent application-only installation receipt 7467f413... verifies the
mapped application and the entire protected tail, including CURRENT 8 KiB
cursors. Recorded boots are A 4ac25bc51decbde2e1eb3f6cce6f75fa and
B 67e58db2fc1a86d2f3f4add83e3cf146. Current cursor watermarks remain
A 1791199541540946076, B 1791705481000000000.
UF2 SHA-256:
17065bc7945a91d210bf3e48aedf1c6f5772f4386e7b26c04f364553afc6adad.
The independent 138 MHz ELF and UF2 are byte-identical.

The transport repair changes two pending-connection predicates so Plain LAN
WTP can activate during an independent TLS handshake. The exact old-gate host
control blocked HELLO at the original five-second deadline; the corrected
real TCP regression passed. TLS/HTTP/idle/WTP deadlines, slot/owner limits and
RF algorithms remain unchanged. Independent host review de02a9b0... preserves
the TLS-rejection fixture failure and its corrected closure fixture.
The upstream TLS delivery-delay origin remains unisolated.

A's controlled unfinished TLS handshake coexisted with HELLO/PING in 0.444 s,
and 16 complete authenticated page/API responses passed. The whole target
receipt 5c1db64b... remains FAILED because an added B pre-traffic guard refused
an already occupied connection slot. A's distinct review 4c3d1a4b... accepts
A only. A separate B check preserved the existing connection and completed
HELLO/PING in 0.221 s plus 16 complete authenticated page/API responses.
Independent B review 8a0d060f... verifies no settings/flash/cursor writes,
owned Wi-Fi removal, unchanged management and active service.
Both genuine delivered radio pages are 90,429 bytes. Prior R189 settings writes,
persistence and native restoration at b259382e... remain separately accepted:
the API, cryptography, profile/store/cursor and main source bytes are unchanged
in C96. HTTP page delivery retains the documented open-AP substitution risk.

The first smoke parent stopped after A/B Tone and A WSPR, before B RF.
Its e2fe622e... failure and 512 MB remain unchanged. The B-only pre-repair
refusal 13bc15f2... also started no RF. Corrected-image parent
9527/start91427889 captured B WSPR job 9efa30a808bc42b3f641031001613347,
completed external AA0NT EM18 37 decode and restored the service/reference.
Result 7fd02e17... closed with all registered native/analysis processes gone.

Separate full review
f7915a808a8a372b07df40b783e49d97e9883410e18fcf61c521b0373c1c3c40,
reviewer 10839/start91464960 now gone, independently hashes all four raws /
824,000,000 bytes and verifies AGC/bias-T false, zero clipping/overflow,
original resource/quality/close-in screens, both actual expected WSPR stdout
records, tools, controls, source, boots and final restoration.
The three R189 screens retain their actual old firmware identity; the B WSPR
screen is actual C96. Narrow source applicability verifies every other target
runtime source byte and normalizes only the two Plain predicates/comment.
Older measurements are not relabelled as new C96 captures.
Two separately admitted final INFO reads and one reference read verify both
current C96 boots, false opt-ins, inactive/unowned outputs, unchanged cursors,
synchronized clocks, ready AP/Plain listeners and original GPSDO state.
No DSP/decoder/RF replay or profile/config/cursor write occurred in the review.

Memory and mixed science remain separately accepted under their actual original
identities. Original memory 14.58 GB core plus 128 MB references still needs
durable retention, alongside final consumer/smoke/source/control evidence.
Consolidated coverage, adversarial audits and Git closeout remain open.
Progress stays 3 of 9 (33.3%) and estimated 4–25 hours pending actual original
workstream gates. Hourly healthy reports remain ACTIVE. No staging, commit,
push or publication is authorized by the current request.


## Earlier R189 consumer and first-smoke boundary (historical)

Latest accepted consumer boundary: both Picos have the uncommitted
`consumer-radio-18997499747b` / 138 MHz image. The independent application-only
installation review `356e2650...` verifies full native application/protected-tail
identity and CURRENT 8 KiB cursor preservation. B's original consumer 24 KiB
still matches. Both station clocks are synchronized and their setup/radio APs
are ready while idle.

Authenticated settings, persistence and original restoration are independently
accepted at `b259382ea28ed6cf6a7ed4046d83605bb9b048d5f40d1130548c8e2dd9e2e0df`.
Parent `4174699/start90801639`, admitter `4174517/start90799698`, reviewer
`4175951/start90831552` and all recorded Node/native/NM/service children are gone.
The actual result is `cd0912cac64341d10637b032d5ddb3fcef1af891c3a25b9e5b9e8bf49873ba0e`.
There are 86 complete authenticated HTTP responses, 43 per Pico. Default and
single-opt-in non-amateur LOADs refused; both opt-ins admitted an unarmed plan.
Revision and profile-identity refusals passed. Both flags persisted across
reboot, then ONLY original configuration 8 KiB was restored on each board.
Full native 4 MiB images are byte-equal to their pre-test baselines:
A `c4057a48...`, B `9cbd732a...`. CURRENT cursors remain
A `1791199541540946076`, B `1791705481000000000`; profiles, application and
credentials are unchanged. Final recorded boots are A `c772cca9...`,
B `c9f20b1f...`, subject to a fresh read before further hardware work.
Both flags are false, schedules/outputs disabled, owners empty, wlan2 test
profiles removed, management unchanged and the owned service active.

Four separately admitted final consumer-image smokes are actually dispatched
once as `4179238/start90904373`: A/B 80 m Tone 5 s and one normal WSPR frame each,
412 capture seconds / 824 MB. The parent owns all four locks through captures,
gaps and analysis; same-image/boot/settings/current-cursor, explicit AGC/bias-T
false, original signal/resource criteria and external decoder output remain
required. The host metadata adapter changes only the source spelling from a
clean 12-hex revision to the actual `dda8a6eb1e69-dirty`, with the full runtime
and linked image pinned. No old RF evidence is relabelled. This is an active
stage until refreshed, not final acceptance. It requires a new independent full
raw/control/source/restoration/process review after actual closure.

Preserved failures explain the scoped correction. The R260 settings run stopped
on its first CLAIM because the commissioning predicate withdrew the AP on
ownership; actual timeout `3b885d69...` and eight responses remain failed.
A separate two-INFO check verified zero settings writes, unchanged current
cursors and idle restoration. The new ownership distinction then passed seven
host cases and both physical settings runs. The first new fixture `83ee6e72...`
incorrectly classified 40,000,100 Hz as non-amateur; the existing source catalog
correctly permits this unqualified amateur frequency with the first opt-in.
Its one owned A configuration change and 18 responses remain recorded.
A config-only restoration first refused before native LOAD on an omitted
false-valued journal key (`5d61e3d...`). A distinct exact-ROM continuation
`6cc61b09...` restored the original 8 KiB; independent `be309a4b...` verified
entire native flash/cursor equality and owned-service restoration. The admitted
successor uses actual non-amateur 46,000,100 Hz, records parsed inner responses
immediately, and keeps every deadline/security/scientific limit unchanged.
The earlier 32-response read/page acceptance `505c129d...` at R260 also remains
separate historical evidence.

At the preceding installation boundary, both Picos had the uncommitted
consumer-radio `a0284281bba7` image.
Independent full native comparison verifies each new application payload,
A's unchanged protected flash, B's restored original 24 KiB consumer
profile/configuration, and both CURRENT 8 KiB cursors. The idle-only closeout
receipt is `6109b07e...`; the separate closure checker verifies its exact parent
and service child gone, all four locks available and the owned service active.
Both setup APs are ready. The original 90-second station-clock/readiness check
failed and remains failed: both station clocks were unsynchronized. No RF smoke
or physical authenticated consumer API acceptance is claimed from installation.

The pinned CYW43 driver makes a newly enabled AP the default network interface.
The consumer portal now remains available with station Wi-Fi, exposing this
interaction. A source correction restores the connected station as default
inside `PicoNetwork::poll`; AP subnet routing remains intact. A new real-lwIP
packet regression verifies external NTP packets use the station and local AP
packets use the AP. The exact old-route control fails that assertion. Independent
host review `b0154023...` verifies 2,569 source/dependency files and closed
processes. Two unchanged MAC checks are reused from their actual prior passes.
The first new fixture stopped before its intended packet observation because
its virtual interval did not include the existing 64-second SNTP backoff; that
failure remains preserved. Only the fixture observation window changed.
That historical routing candidate subsequently passed Arm build/review,
installation and physical validation before the accepted ownership successor. The original mixed/memory acceptance is not relabelled as this
new consumer image's target evidence.

| Original workstream | Current status | Remaining acceptance gate |
| --- | --- | --- |
| 1. Initial code/evidence review | Closed | Preserve its original scope and limitations. |
| 2. Plan and acceptance record | Closed | Preserve frozen criteria and operator amendments. |
| 3. Existing bench and automation | Closed | Refresh exact identity/state before every later action. |
| 4. Clock/band/mode behavior | Open | Consolidate assertion-level retained-band coverage and final-source applicability from actual accepted controls and decoder/human-copy proofs. |
| 5. Timing/spectra/output path | Open | Consolidate accepted timing, spectra and compensation proofs with source, receiver and unfiltered-path limits. |
| 6. Reliability/failure handling | Open | Consolidate native, standalone, lifecycle, eight-hour mixed and separate two-hour memory acceptance, their exact source applicability and preserved failure history. |
| 7. Release candidate/configuration/smokes | Open | Both consumer settings/persistence/restoration and all four source-bound smokes passed; finish consolidated final-source/release artifact and fresh quiet restoration audit. |
| 8. Adversarial review/repair | Open | Final independent assertion-level review; fix actionable findings and rerun affected checks only. |
| 9. Commit/push/report | Open | Obtain the required explicit Git request after a concrete reviewable result, then authorized commit/push and independently verify remote parity and final closeout. |

Workstreams 4–6 remain conservatively open until their final consolidated audit
checks each original assertion against applicable evidence. No extra RF matrix,
accepted-job repetition, decoder sweep, frequency/drift pass/fail gate or 4 m /
2 m qualification is introduced. All-mode 4 m / 2 m release exclusions remain.
No general leak-freedom, calibrated power or production RF/LPF claim follows.

## Actual component reconciliation

New helper `bf0c8fc496f49d79d787e3233160c48fd1567c5bdf5b35c0c17fed403d0dfce0`
ran once under all four locks / 900-second bound as `4095365/start89086803`.
Nine new arithmetic/refusal cases passed. The actual reconciliation receipt is
`0c5be5cc7f3b5c199384f0cbee25bfb6f7b57be258002827427c7bc675d6c10d`,
under the current private Pi ROOT at
`build/original-components-reconciliation-20261014/result.json`.
Distinct closed identity/decimal-arithmetic verification is
`b96fa60205ce55c420ccd45acc4e8998bc0deada002a0fcc3497a169343891d5`.
The reconciliation parent is gone. The distinct checker completed; a fresh
monitor verified no campaign work and all four locks available. The check reused
just-closed raw proofs with unchanged identities and read no IQ. Fresh source/control and nonraw verification does not
constitute a new full application-flash proof. Exact-byte local copies are in
ignored `build/phase14-original-components-accepted-20261014/`.
The first attempted local reserialization failed exact-byte comparison and
wrote no proof; the distinct fixed-byte export matched the original receipts.

| Original remaining component | Actual acceptance credited once | Remaining |
| --- | --- | --- |
| Mixed settled workload | 29,544 seconds; full `014b4438...`, closed `77c6b727...` | 0 fixed seconds |
| Memory settled workload | 8,002 seconds; full `3c5c5539...`, closed `a42de550...` | 0 fixed seconds |
| Core closed transfer | Mixed 58,320,000,000 bytes; full copy `f7418de2...`, closed `bfb7b432...`, post `b6739a96...`, closed post `46e22bde...` | 0 core bytes after full 1110d059... / closed 4e4c2e9c... |
| Reference/other retention | Original inclusive allowance; no new core credit | Fresh final source/raw/result scope inventory still required |

The historical fixed baseline is 37,546 seconds and original core transfer is
72,900,000,000 bytes. Their credits are acceptance based; elapsed time is never
subtracted. Original 128 MB reference companions receive no second credit.
Every failed capture and original legacy false flag remains retained.

Remaining core transfer uses the existing optimistic 32.188098877 seconds /
936,191,802 bytes and conservative twice 2,604.051136275 seconds /
38,720,000,000 bytes large-copy benchmark, including verification overhead.
For 14.58 GB this is 0.139247–0.544752 hours. The unchanged inclusive other-work
range is 1.818081–15.818081 hours, receiver/final-validation contingency
0.87–5.87 hours and control/review 0.25–2 hours. Total 3.077328–24.232833 hours
rounds up to 4–25. Repairs and waiting for explicit Git authorization may extend
calendar completion. Transfer is not treated as closed before actual durable
copy and independent acceptance.

## Next finite admissions

1. Inventory the original remaining source/raw/result scope and original
   coverage assertions at a freshly quiet boundary. Bind every accepted proof
   to its real source, RF boot, image, settings, receiver and applicability chain.
   Reuse independently full-hashed raw proofs only for exact unchanged tuples;
   do not invoke old whole-source closures after the recorded source unlinks.
   Identify absent source samples from the separate immutable CLOCK/MIXED
   release histories. Restore an archived raw internally and full-hash it before
   any future reanalysis. New retention needs its own fresh scope and ready-stage
   need before storage operations; retain originals until its actual acceptance.
2. Preserve the independently accepted both-consumer page/API/settings,
   unarmed admission and reboot-persistence evidence. The original configuration
   journals are restored; no consumer settings run is queued or to be repeated.
   The consumer transport, profile identity, cursor and threat boundaries are
   recorded in [Consumer-Radio/1](../protocol/Consumer-Radio-v1.md).
3. Preserve B's completed original consumer 24 KiB restoration and full native
   current-cursor proofs. No further profile write is needed. A future native
   check must use CURRENT cursor bytes and must never restore the old saved
   cursor. All previous refusal/failure/result records stay immutable.
4. Admit applicable final smokes, consolidated source/coverage audit and final
   adversarial review separately. Preserve useful candidate images and all
   worktrees. Recheck source/image/boot/current settings/cursor, no unintended
   schedule, GPSDO/reference restoration, process closure, locks and UUIDs.
   Commit/push only after the human's explicit Git request.

The original mixed/memory evidence root remains
`/home/pi/phase14-qualification-20261008/build/resume-tools-dda8a6e-browser-deadline-async-internal-first-20261013`.
At that historical boundary ordinary firmware was clean
`dda8a6eb1e69539b7399cdd899d8830a2d199769` / 138 MHz;
UF2 `091a647aeecd845ba35de036a82f0f24d7880ca4dbace202d8c3367556995a5b`.
Those historical restored boots were A `bc63566fd9201be27577db13ed22e5bf` and
B `d52057776b5048d0c9912e92cd3e2d65`; refresh these before hardware work.
The historical memory AP boot is not current ordinary B identity.

Private artifacts may be stored on the Pi or Mac under the user's October 14
storage amendment. Live samples remain on internal Pi NVMe and closed raw
retention follows the existing archive rules. Exactly
164 CLOCK and three selected MIXED source absences remain separate; historical
copy/full-review source-retained flags remain pre-unlink observations. Every
durable raw/nonraw, failed sample, maximum/useful image and immutable control
is preserved. No only-copy/nonraw deletion, external transfer overlapping
acquisition/analysis, old helper replay or automatic future RF/storage queue.
No incidental SDK/tool installation, native Mac C++ build or publication.
Hourly automation stays active at its existing schedule and notification policy.

## October 14: bounded final sample-location inventory closed

A separately admitted 300-second stat-only inventory closed at
`fd62335bf2d7004cf00e8bf0674d9fe1a5709d3501f3f12d6b041c4c52579a9e`.
Exact parent `4100801/start89209761` and admitter
`4100628/start89205300` are gone. Helper `15aef4a8...` / admission
`cfe441b3...` inventoried 1,627 sample containers / 362,766,106,624 bytes under
`/home/pi/phase14-qualification-20261008` and 288 / 159,280,000,000 bytes under
`/mnt/phase14-testing/phase14-closed-internal-first`. These are bounded location
and stat counts, including `.cf32`, incomplete and gzip containers; they are
not unique scientific workload, logical decompressed totals or new full-hash
archive acceptance. Exact accepted memory/mixed tuples and separate 164 CLOCK /
three MIXED absences matched. No sample/private contents, Device, RF, transfer
or removal occurred. The full location inventory remains private on the Pi.

The first admission refused before traversal because its static guard treated
`dirs.remove(name)` list filtering as a filesystem deletion. That source and
actual trace remain preserved. The distinct successor changes only programme /
output namespaces and permits that exact in-memory call; filesystem deletion
still refuses. Six new AST call cases passed; the actual eight prior scope
cases were retained by exact unchanged source/trace proof without replay.
The first admitter PID was not recorded; no exact PID is invented for it.
Fresh host checks verified no active work, all four locks, UUIDs, AP absent and
service active. Counts stay 3 of 9 / 33.3%, estimate 4–25 hours. Final coverage /
companion mapping, actual remaining retention and consumer settings/restoration /
smokes/adversarial/Git closeout remain. No retention or RF stage is queued.
