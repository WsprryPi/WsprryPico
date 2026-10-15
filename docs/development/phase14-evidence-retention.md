# Phase 14 evidence retention and storage

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

## October 14: consumer settings/persistence/restoration independently accepted

The requested authenticated consumer radio page/API is implemented and passed
bounded validation on both Picos. The actual `consumer-radio-18997499747b`
138 MHz source snapshot is uncommitted `dda8a6eb1e69-dirty`, runtime
`18997499747b027dcdf85a980c03bcaeb616f5f5684f6a4ab3d80471ee62095a`, UF2
`4ddbfdc8ac7b8c643d396f72f6b794983775ee37fabe9d9b53b4e97f4cfb5b99`.
Two Arm builds are byte-identical. The independent installation review
`356e2650...` and settings review
`b259382ea28ed6cf6a7ed4046d83605bb9b048d5f40d1130548c8e2dd9e2e0df`
bind actual source, full native flash, both CURRENT cursors and closed processes.
Settings result `cd0912ca...` contains 86 complete authenticated responses,
revision/identity refusal, default/single/both frequency opt-ins through UNARMED
LOAD only, reboot persistence and original configuration restoration. Four
successful API writes and two original configuration 8 KiB native restores
left full 4 MiB bytes equal to each pre-test image. No RF or cursor/profile
write occurred in that settings run. Both flags are restored false,
outputs/schedules disabled, owners empty, management unchanged and service active.

The original CLAIM/AP withdrawal timeout `3b885d69...`, incorrect 40 MHz fixture
classification `83ee6e72...`, omitted-false journal parser refusal `5d61e3d...`,
and actual config-only ROM continuation `6cc61b09...` / independent
`be309a4b...` remain preserved. They were resolved with distinct source/state-bound
successors; no closed programme, reservation, scientific workload or helper was
blindly replayed. The correct non-amateur fixture is 46,000,100 Hz and never
ARMed. No original RF flag or scientific/security limit changed.

Four separately admitted final consumer-image 80 m smokes are dispatched once
as `4179238/start90904373`; completion/acceptance requires a fresh receipt and
independent full raw/control/restoration review. Original mixed and memory
remain separately accepted under their real older source identities. Phase 14
release remains open: 3 of 9 original workstreams / 33.3%, estimate 4–25 hours,
with consumer repair work able to extend it. No Git action is authorized.
See the [current closeout ledger](phase14-closeout-ledger.md).

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

## October 14: original components reconciled; estimate 4–25 hours

A new finite metadata reconciliation `bf0c8fc4...`, actual parent
`4095365/start89086803`, closed at receipt
`0c5be5cc7f3b5c199384f0cbee25bfb6f7b57be258002827427c7bc675d6c10d`.
A distinct closed identity/arithmetic check `b96fa602...` verified that parent
and the accepted predecessors gone, all four locks available, actual UUIDs,
owned AP absent and service active. It independently recalculated the estimate
with decimal arithmetic. The new reconciliation checked source bindings,
unchanged full-hash raw tuples, all 1,972 mixed nonraw source/durable pairs /
242,808,776 bytes, memory controls and separate 164 CLOCK / three MIXED
source absences. No IQ/Device/RF/DSP/decoder, transfer or removal occurred.
Only three fixed closed JSON controls were mirrored locally byte-for-byte.
A first local JSON reserialization was refused by exact-byte hash comparison;
no proof was replaced. The subsequent fixed-byte metadata export matched.

Mixed and memory each receive their original component credit once:
29,544 + 8,002 = 37,546 settled seconds. That historical baseline is preserved;
remaining fixed core workload is zero. The separately accepted mixed archive
credits 58.320 GB core transfer once, leaving 14.580 GB memory core retention.
Reference bytes remain inside the existing inclusive allowance. Unchanged
other-work, receiver and control/review ranges produce 3.0773–24.2328 hours,
rounded up to **4–25 hours**. No elapsed, failed, partial, preparation, release
or duplicate transfer credit is applied. Larger repairs or the wait for an
explicit final Git request may extend completion.

Counts remain **3 of 9 original workstreams (33.3%)**. The remaining original
assertion-level source/coverage audits, final A authenticated consumer settings
API validation, final B consumer 24 KiB-only restoration preserving its current
advanced 8 KiB cursor, remaining retention, smokes and adversarial closeout are
listed in [the closeout ledger](phase14-closeout-ledger.md). No combined
long/memory workstream closure is invented. Historical rows below retain their
original meanings. The hourly schedule and notification policy stay unchanged.
No Git mutation occurred; existing unrelated changes and useful images remain.

## October 14: memory independently accepted; final closeout remains

The original two adjacent B 80 m / 138 MHz / 512-event FSKCW browser hours
closed at receipt `2894b75363d1857a79f3e798e99e7feaaeb7ea092b290753b973489d385f86ba`.
A new separately admitted independent full review
`3c5c5539c4b1a3c36061781e8a8632e9eddd5fec61ff46c1aa58672c4415b9b6`
full-hashed all ten original raw files / 14,708,000,000 bytes and checked source,
image, receiver, raw Console/control, timing, resources, browser security,
human-copy/reference and restoration evidence. Its exact parent
`4081086/start88768849` and admitter `4080768/start88762471` are gone.
A distinct 180-second closed acceptance
`a42de5504768639600500cddf893a865b5836a46a59bc4cafd4718c3544edc27`
verified metadata/admission agreement, exact unchanged full-hash identities,
all nonraw/review controls, all 38 registered memory identities gone and the
restored host state. Its exact parent `4082057/start88787638` is gone.
It reused the just-closed full raw proofs without new IQ or Device reads.

Each hour met the original browser gates: 337 and 331 successful responses,
spanning 3,600.616445128 and 3,593.305051494 seconds. Original 45-second
median allocation growth was −392 bytes and expiry-normalized growth was
−480 bytes; both three-INFO window spreads were zero. The 1,024-byte growth
and spread limits, >=350-second expiry boundary, one-second INFO spacing,
30-second client / 10-second handshake / 15-second HTTP server limits and
original authentication/no-retry requirements remain unchanged. Both legacy
FSK analysis flags remain false; the existing human-copy screens pass under
the retained operator amendment. This is bounded memory acceptance, not a
general leak-freedom claim or Phase 14 release completion.

Native saved/restored 32 KiB bytes are equal, including configuration and the
current advanced 8 KiB cursor. Owned AP/profile/service restoration passed:
AP removed, management preserved, service active. A ordinary boot remains
`bc63566fd9201be27577db13ed22e5bf`; actual restored ordinary B boot is
`d52057776b5048d0c9912e92cd3e2d65`. B AP RF boot
`f95e62adf209dff899960e17f245e48d` and pre-memory ordinary boot `f48227c3`
remain historical identities. Firmware remains clean DDA / 138 MHz / UF2
`091a647a`; settings equality does not supply a new full application-flash proof.

The first reviewer admission is preserved at `a4b8f52d...`: it passed thirty
new pure refusal cases and source checks but refused before IQ/Device access
because its reviewer checked receiver AGC/bias arguments at positions 11/12.
The distinct corrected program checks actual positions 10/11, adds three
receiver-flag cases and reuses that actual thirty-case proof through unchanged
function AST without replay. Actual corrected admission is
`836442c134c00b4d2793c583dded272a1fef18b5da6f6d3ccc8e7974b0ee45e7`;
reviewer `f2a55185097958c7e186a05890bf6f5ea9c0b8f701b98a463fd62767c6df853d`,
manifest `19dab5bec86d82a9105cff05ffc9f944a9123409ba9bf7ee07b15ada25d4e66d`.
The earlier metadata-shape refusal is retained separately. No scientific failure
or limit relaxation is inferred from either reviewer refusal.

Fresh historical boundary `1791970202697663508` verified Harness STOPPED,
all exact parents/children gone, four locks available, actual filesystem UUIDs,
AP gone and service active. Only three fixed closed JSON proofs were mirrored
locally byte-for-byte; all samples/profiles/credentials/keys remain on the Pi.
Every failed result, original flag, raw/nonraw, maximum/useful image and the
separate 164 CLOCK plus three MIXED source absences remain preserved. Never
replay the closed programs, reservations, fixtures or whole-source helpers.
Refresh actual state before the next action or report.

The original remaining-component/workstream reconciliation, final A consumer
settings API validation, B consumer 24 KiB-only restoration preserving the
current 8 KiB cursor, source/result retention, final smokes/adversarial closeout
and explicit final Git request remain. No later job is queued. Counts remain
3 of 9 / 33.3% and the 15–37-hour estimate remains the unreconciled original
baseline; no combined workstream closure or elapsed/partial/transfer double
credit is invented. The hourly automation stays active at its existing cadence
and notification policy. No Git mutation occurred.

## October 14: second memory hour active; independent acceptance pending

Historical monitor `1791965371001687427` verified exact parent
`4056459/start87681546`, acquisition `4056909/start87696979` and native
capture `4064443/start88107751` active for the second B 80 m / 138 MHz /
512-event FSKCW browser hour. The capture targets 911,250,000 samples /
3,645 seconds at 250 ksample/s CF32 on internal NVMe, with AGC and bias tee
explicitly false. Receipt
`1b32025eedfd3e43f47d88801ca6d77950c82278f6f8ed0708caabec4f4e0e65`
reported no primary or closeout error and zero whole-review observations.
Reference-before was complete with exit zero. Recorded AP B boot
`f95e62adf209dff899960e17f245e48d` is unchanged between the two jobs.

Advancement to the second capture does not accept the first job or the whole
run. Original workload, timing, resource, browser/security and restoration
limits remain unchanged. Only the active coordinator restores its owned
AP/engineering profile/service after verified own children exit. Continue
monitoring only with the SSH-stdin receipt/process reader; no competing bench
or retention work. Whole closure and a new independent full two-job review
remain required. Refresh this snapshot before each report or action.
Counts remain 3 of 9 / 33.3%; the 15–37-hour estimate may extend. The hourly
schedule and notification policy remain unchanged; no Git mutation occurred.

## October 14: reserve independently accepted; memory qualification running

The full post-release review closed at
`b6739a96a81b9505b6cb369dfee17447f784f9e0cc9cdc074a68fef9c69c5d50`:
all three removed durable raws / 21,870,000,000 bytes and all 1,972 nonraw
source/durable pairs / 242,808,776 bytes verified, with all 27 new closed controls,
retrieval order, exact absences, source bindings, reserve, service and AP checks.
Exact reviewer `4045941/start87447129` and admitter are gone. Separate finite
closed post acceptance
`46e22bde7575a52f3d08d2bd6d99b886f3284493beac9b3e48cd275ba3233078`
verified identical internal/durable proofs and unchanged identities, reused the
just-closed raw full proofs without reading raw bytes, and retained sixteen
additional final post/closure controls. Its exact parent
`4053381/start87613770` is gone. The historical 164 clock absences and the three
selected mixed source absences remain separate; original flags remain unchanged.

A distinct one-time memory dispatcher `ea15cb5642510f3351d4a458e6047787d18affefc1f3733b86b2efdba9320043`
passed 32 new proof/failure/closure refusal cases before Device access, checked
all source and programme bindings, and published its programme guard admission.
Fresh direct Console INFO verified both named ordinary DDA/138 boards,
boots A `bc63566fd9201be27577db13ed22e5bf` and B
`f48227c35ddd7613d5dee13bb784235d`, unchanged public settings/current cursor,
false flags and empty/unowned/disabled outputs. Read-only GPSDO identity/lock /
current settings matched the retained reference. All four locks, actual UUIDs,
service/AP state and strict reserve passed; dispatch free space was
32,739,889,152 bytes, above 25,687,613,010. Its preflight and dispatch controls
were retained on both Pi filesystems before the fork gate released the child.
No raw, credential file or private key was exported to the Mac.

The already admitted memory coordinator
`643ba3a6c9716fee3ae6ad374a7a6b02d04cf0a052266f0f1f425ba6da09ba1b`,
manifest `c6057e2d999f4a7a313f2106be068c43feccac9b01d6ca282254b523dd03bb7a`,
admission `3fb006cc928fcb8164bab598bf6426df5db853d39820d02c0cfc1907adf01169`,
was dispatched once as `4056459/start87681546` to
`build/isolated-ap-memory-20261014T062344/result.json`. Dispatcher receipt
`ecfd717b3c817e9db83420ab3929a498e47deac037aab285cf57d1aa78c45ff8`
and the coordinator's own unique reservation prohibit duplicates. Historical
launch metadata marked live admission pending; subsequent actual live admission
`30df85e1ca902f6cbab8ed3cd7befac9dd481423a1e0fe56ba2199e996a7b23c`
preceded RF and bound new AP B boot `f95e62adf209dff899960e17f245e48d`,
synchronized clock, current settings and authenticated original-security browser
probe. A boot is unchanged. The prior B ordinary boot is historical during RF.
Firmware remains ordinary clean DDA / 138 MHz / UF2 `091a647a`; public settings
equality is not a new full application-flash proof.

At historical monitor `1791959139486960449`, exact PID/start/argv and receipt
`20d0459145ce226d3f1dd7cab45d8dcaca45a3397d631046f2c9e1a1265797ef`
confirmed the reference-before child `4056731/start87689774` active, zero whole
observations and no error. Owned service/AP/profile restoration is pending;
only this coordinator restores after its verified own children are gone.
Refresh each report using only the SSH-stdin receipt/process monitor
`build/phase14-isolated-ap-memory-live-reader-20261014.py`. No competing Device,
raw, archive, copy, deletion, audit, decoder or analysis work may overlap it.

At the later historical monitor `1791959875699772806`, reference-before
`4056731/start87689774` was complete with exit zero. Exact acquisition
`4056909/start87696979` and native capture `4056921/start87697962` were active
for the first B 80 m / 138 MHz / 512-event FSKCW browser hour: 911,250,000
samples / 3,645 seconds / 250 ksample/s CF32, explicit AGC and bias tee false,
internal NVMe only. Exact parent `4056459/start87681546` remained active;
receipt `e162792d7ce51c39b8def367e0afa3c426f878e146b679075a38319c7a0fbbf7`
reported no primary or closeout error and zero whole-review observations.
This is an acquisition snapshot, not acceptance; refresh it before reporting.

The original two adjacent B 80 m / 138 MHz / 512-event/browser hour jobs, same
AP boot/settings, 45 versus >=350-second windows, three INFO one second apart,
1,024-byte growth/spread, >=300 successes spanning >=3,500 seconds and 128 MB
references remain unchanged. Bounds are 14,400 whole / 10,000 acquisition /
3,600 analysis / 600 reference seconds. Security and no-retry limits are
unchanged. The parent owns workflow/inactive A/gaps/analysis, verified own-child
cleanup and only its AP/16 KiB engineering profile/service restoration, with
full 32 KiB native original/restored config/current-cursor proof. Whole closure
is not acceptance: a new independent full two-job raw/control/timing/resources /
browser/human/reference/source/image/boot/cursor/native/AP/service/process
review is still required. No combined workstream closure or release completion
is claimed. Counts remain 3 of 9 / 33.3%; estimated 15–37 hours, possibly longer.
Existing code/test/document edits remain uncommitted; the unrelated plan and
Si5351 paths are preserved. No Git mutation is authorized.

## October 14: three redundant mixed raws released; full post-review active

The guarded release closed at
`aebb36810995d9ae0b917a457aa4ab9a49b5c6cb5b0878c4bfd40855739efe1a`.
Exact parent `4039985/start87320725` is gone. Only the catalogue's three selected
7.29 GB source raws were removed: index 0 A Tone, index 1 B Tone and index 2
A FSKCW, total 21,870,000,000 bytes. Every durable raw and nonraw companion is
retained. Internal and durable release result bytes match. Each of the three
retrieval records was fsynced on both filesystems before immediate independent
full pair hashes, identity/user/source/current-settings/UUID checks and unlink.
Final actual free space was 32,740,282,368 bytes, above the unchanged strict
25,687,613,010-byte memory guard. These three mixed source absences remain
separate from the 164 historical clock absences; old source-retained flags
remain immutable historical observations.

The distinct state-aware post-review passed 49 new refusal cases and bound all
sixteen release-owned closed controls before any raw or Device access. Its
admitter `4045444/start87435546` is gone. New programme:
core `3d636904064b19bdc5970bd911c4b2056afb546b10d7006fe795ab3a24e2984f`,
post `cb9f2d029cca6b78487a6704d4861e2aa2ff312602611bd91fe7dfedc1669f2c`,
manifest `3f3c3c1a2df219ffa38aee4770e9bc4cff7f4e6b752f33fdc5eb33ef59b1edcd`,
admission `024bc254929d81b4122c515a90133560fa1223a9bc45dbd52b2513fa923028bd`.
Exact parent `4045941/start87447129` runs once under all four locks and a
1,800-second bound. It independently full-hashes all three removed durable raws,
all 1,972 nonraw source/durable pairs and all copy/full-review/acceptance controls.
Only unchanged remaining raw tuples reuse the actual preceding full proofs.
It verifies retrieval byte equality and publication/hash/unlink order, exact
absences, current source bindings/reserve/service/AP/UUID and predecessor exit.
It durably retains the release's own programmes/admissions/reservations/log /
final result/live Console events/retrievals and its own new programme controls.
No Device/RF/DSP/decoder/service/profile/config/cursor writes or source removal
are part of this review.

Historical monitor `1791956716823710676`, receipt
`2ae7371236115473b5b67e5376aa05a97b534bfbf1e63c3706d57774435c06fb`, confirmed
fresh exact PID/start/argv, the first durable hash active, no error and no further
removal. Refresh before each report/action. While active, use only the SSH-stdin
monitor `build/phase14-memory-release-post-live-reader-20261014.py`; do not run
competing bench, sample, storage or analysis operations.

Memory RF remains undispatched and unqueued. Actual positive full post-review,
identical durable proof, exact process exit and retention of the post-review's
own final controls precede a separate fresh source/image/ordinary-boot/settings /
current cursor/network/resources/GPSDO/UUID/lock/reserve memory dispatch. The
original two-hour workload, security, scientific limits and owned restoration
are unchanged. Full memory independent acceptance and final closeout remain.
Counts are still 3 of 9 / 33.3%; estimated 15–37 hours with possible extension.
No Git mutation is authorized; existing unrelated edits and all worktrees remain.

## October 14: full copy review accepted; guarded redundant release active

The independent retention review closed at result SHA-256
`f7418de29a5af61e89e6f607c521ad80e8f6be478f4bba36bac0c58def87b566` after full
source and durable hashes of all 1,988 pairs / 58,690,808,776 bytes, including
all sixteen raws / 58,448,000,000 bytes. Exact reviewer
`4021797/start86910468` and its admitter are gone. Separate finite closed
acceptance `bfb7b432a01d1f73450a3a935bcc4a9052c7f349a9f7d43cf8201d29614cf4a5`
verified identical internal/durable review and acceptance proofs, unchanged
pair identities, the 164 historical clock absences, service/AP restoration and
process closure. It retained fifteen additional final review and acceptance
controls on the private SSD; it read no raw bytes. Its exact parent
`4037462/start87267732` is gone. The original mixed RF acceptance is unchanged.

A distinct three-candidate release programme passed 46 new refusal cases before
Device or raw access: release `1c06f541874ec98eb2c52c69d5a71e400d6861c823c732c883d1a68253c0f75a`,
core `991ff9031ca82494b0b3145589bd693f40a6e1afba3a01f34c0a984491820adb`,
manifest `cbc569579db0c827a2c3c984b183eb79f50bc75781ce644e35232599519a74a8`,
admission `597e46f8312735c07bdedc30f68c78caea56a8d0a95c594161107c4c02eb60a4`.
Admitter `4039476/start87309574` is gone. Actual new release
`4039985/start87320725` runs once under all four locks and a 3,600-second bound.
The catalogue permits only indices 0 A Tone, 1 B Tone and 2 A FSKCW, each
7.29 GB, maximum 21.87 GB. It stops at strict actual free space greater than
25,687,613,010 bytes. Both-filesystem retrieval precedes immediate independent
full source/durable hashes, exact stat, active-user, current board settings and
UUID checks before each redundant-only unlink. No durable copy or companion is
removed, and no service/profile/config/cursor write is part of this programme.

At the historical monitor boundary `1791955431614247654`, exact PID/start/argv
and receipt `aa9c2e2e8267ea9d20e9912273794bf28037b478c526b63981bfe55a03643a27`
confirmed the first source hash active, zero removals and no error. Refresh the
actual receipt each report; this launch snapshot is not current-state evidence.
Monitor only `build/phase14-memory-redundant-release-live-reader-20261014.py`
through SSH stdin while active. Preserve every prior failed record and original
flag. Clock absences remain a separate set from any new mixed source absences.

After actual positive release closure and exact parent/descendants gone, a new
separate full post-release review must hash every removed durable raw, validate
all companions/closed controls and both retrievals/order, exact source absences,
current reserve/service/UUID, retain the release's own final controls and publish
an identical durable proof. It is not implemented or queued at this boundary.
Only positive post-review/exit and fresh source/boots/settings/current cursor /
network/resources/GPSDO/locks/UUID/reserve guards permit the separately admitted
memory coordinator to dispatch once. Memory RF remains unqueued.

## October 14: accepted mixed copy closure and new full pair review

The copy-only retention has closed with 1,988 files / 58,690,808,776 bytes and
zero source removals. Result SHA-256
`4056fca2f250bcae6308dda8dc418ef71c223e9a73d6812f250ca6a23f097c81` and retrieval
`3bb3649295f2fd524f697227b397fbfd36b6015e96b716bb0498ed537b819b47` match their
durable counterparts byte for byte. Exact copier, admitter and import probe are
gone. The archive remains private on the established external filesystem:
`/mnt/phase14-testing/phase14-closed-internal-first/accepted-ap-mixed-memory-reserve-20261014`.
All source tuples remain unchanged, including all sixteen raws / 58.448 GB.

The separate new full review `4021797/start86910468` independently hashes source
and durable bytes for all 1,988 pairs. Verifier `676fc2157a54e3daefaa8a5435a1dbb6fb61216cca5f0cb538fb424809a9c721`,
manifest `75fc45b750235dd94927991c1da005afa433aa872d55b43c6ed1fc5143799e58`,
admission `4b00ab979cd7f5cd548ccdff50c8b47344f4910dc50ca4be2417024f4cd5bc08`:
all four locks / 7,200-second bound / exact open-file identity / no active raw
users / unchanged source and destination tuples. Its durable exact file set
includes the original catalogue and the copy's own 24 closed control files,
retained separately under `copy-closure-controls`, plus this review's programme
controls. No Device/RF/GPSDO/decoder/DSP workload, source removal or service write
is part of this review. Monitor only the new live reader while it is active.

Positive full review, identical durable proof and exact process exit are required
before a separate closed-acceptance check and any later release programme.
Only three catalogue-selected accepted mixed 7.29 GB duplicate raws may later
be considered, after a fresh ready-memory shortage and full immediate source /
durable / stat / user / UUID proofs. Retrieval must be published on both
filesystems before unlink. A separate full post-release reserve review remains
required. The current 164 historical clock source absences are a separate set;
no accepted mixed source raw is absent. Every durable raw, nonraw companion,
original flag and failed sample remains. Restore archived samples internally and
full-hash them before reanalysis. No sample, credential file or private key is
exported to the Mac.

## October 14: accepted mixed retention for admitted memory reserve

Independent full mixed review `014b4438` and closed acceptance `77c6b727`
verified all 58.448 GB and controls/restoration/process closure. Separate memory
admission `3fb006cc` established a strict 25,687,613,010-byte reserve and an actual
roughly 14.8 GB shortage. Catalog `ce9624e5` contains 1,988 files/58,690,808,776
bytes: all 16 accepted mixed/reference raws, every run companion and the source,
programme and closed-control bindings. Only three accepted 7.29 GB mixed raws
are possible later redundant-release candidates; none has been removed.

Actual copy-only successor `9bcf1d87`/manifest `4b73af06`/admission `e0526555`
runs once as PID 3997272/start 86360439. Its private durable directory is
`/mnt/phase14-testing/phase14-closed-internal-first/accepted-ap-mixed-memory-reserve-20261014`.
The whole bound is 7,200 seconds. It full-verifies copied sources, destinations
and unchanged sources and preserves all internal originals, flags and nonraws.
The filename-shadowing predecessor failed before transfer/output and is gone;
its exact source/admission/log remain. The actual import-ready successor retains
the whole copy AST after namespace substitution and entry rename.

Copy closure must be followed by a new independent full pair/companion/control
review including the copy's own closed controls and identical durable retrieval.
No release or memory RF is queued. Any later removal needs its own admission,
both retrievals before immediate full hash/stat/no-user/UUID checks, and a separate
full post-review. All failed evidence and 164 clock source absences remain.
Restore archived mixed samples internally and full-hash before any reanalysis.
No Mac raw or credential-file copies, external transfer overlap with RF/analysis,
or Git mutation occurred.

## October 14: closed AP mixed retained internally; full review active

The new mixed acquisition, references, analysis and close-in checks are closed
under receipt `a12fc6bc`. All eight 7.29 GB mixed raws and eight 16 MB reference
raws remain on internal NVMe: 58,448,000,000 bytes, plus every companion,
original flag and control. Full independent reviewer `99448dd1` is running
once under admission `57b3bf66`, all four locks and a 7,200-second bound.
It performs full hashes without copying, removing or reanalyzing samples.

Dispatch measured 10,879,934,464 internal free bytes, with the unchanged
internal/external UUIDs and restored service/AP state. No memory reserve or
new storage release is claimed. After actual positive mixed review and exact
exit, any required memory reserve must use its own ready-stage shortage,
durable full raw/companion proof, both-filesystem retrieval publication and
immediate full hash/stat/no-user/UUID checks before redundant-only unlink.
The 164 known clock source absences, all earlier failed samples and all durable
copies remain unchanged. No raw or credential file was exported to the Mac.

## October 13: new mixed reserve closed and independently reviewed

The new reserve programme independently hashed all 290 source/durable pairs.
The guarded release removed exactly 58 redundant internal clock raws,
8,200,000,000 bytes, after both-filesystem retrieval publication and immediate
full source/durable hashes, exact stat/user and filesystem identity checks.
Release receipt `c16fcaf9` is closed; separate full post-review `cd358a17`
rehashed all 58 durable raws and every companion/control, checked retrieval order,
and published an identical durable proof. Both parents are gone.

Clock source absences are now exactly 164 (prior 106 plus 58). Total new-task
releases are 83.256 GB; the earlier 7.902 GB is separate. Every durable raw,
nonraw companion, original flag, retained maximum and failed capture remains.
The previous mixed reset's six sample files, 8,139,691,648 bytes, remain internal.
All new pre-RF launch refusals and their settings/control evidence are retained.
Never replay a closed helper or assume all source originals exist; restore
archived samples internally and full-hash them before future analysis.

The new `isolated-ap-mixed-20261013T154332` dispatched with 69,544,620,032 free
internal bytes, above the unchanged strict target 69,427,613,010. Live capture
uses only internal NVMe. No further retention/removal is admitted or queued.
No external transfer, raw audit or removal may overlap acquisition/analysis.

## October 13: isolated AP transport validation in progress

The new mixed run failed after 36 successful browser responses when B reset
its next TLS handshake. Its independent failure review is closed; all 20
registered processes are gone. The 8,139,691,648 bytes of failed-run samples
remain internally preserved, including B's incomplete capture. No mixed or
memory acceptance was credited.

A separate single status read found one firmware timeout, zero admission
rejections and zero TLS allocation failures. The saved pre-reset handshake
still had 788 bytes awaiting TCP acknowledgement. This supports closure at the
unchanged ten-second handshake limit; the upstream delivery-delay origin is
still unisolated.

A new, independently admitted validation now uses the already authorized
wlan2 AP on wspr5. It makes 60 authenticated reads at the original ten-second
request cadence with independent one-second INFO polling. The firmware,
certificates, 30-second overall client budget, ten-second server handshake
limit and fifteen-second server HTTP limit remain unchanged. B's temporary
engineering Wi-Fi profile changes only its 16 KiB profile region. The
coordinator owns restoration of that profile, the AP and its stopped service,
and verifies the original configuration and current cursor bytes.

The first AP attempt stopped before any B profile or ROM operation because its
host guard compared naturally decreasing DHCP lifetimes. Its AP was removed;
a separate source-bound closeout verified unchanged board boots/settings and
restored the owned service. The current successor compares stable addresses,
MACs and routes, and retains both failed records.

The AP run must close, restore and pass a separate independent result review
before a new mixed programme is admitted. The original eight-hour science,
45-second idle windows, one-second INFO cadence, 1024-byte growth/spread gates,
300 successful browser responses over at least 3500 seconds, storage reserve
and finite bounds remain unchanged. Memory follows only an independently
accepted mixed run. Hourly reporting remains active at its existing cadence:
3 of 9 workstreams (33.3%), estimated 15–37 hours remaining. No diagnostic,
preparation or elapsed-time credit is applied.


## October 13 mixed run failed at B TLS handshake; independent failure review closed

The current eight-job mixed run ended at 08:41:52 CDT with
`FAILED_REPAIRED_SOURCE_MIXED_EVIDENCE_PRESERVED` (receipt `51397b7d`).
A's first Tone control/capture completed. B's first Tone failed after 36
successful authenticated responses with `ConnectionResetError(104,
'Connection reset by peer')` during the TLS handshake, before the next GET
was sent. This is a peer reset, not a 30-second harness deadline expiration.
The next root path is inferred from the fixed rotation. No network or firmware
root cause has been isolated and no eight-job or memory acceptance is credited.

Separate independent review `ce99ef7d` closed at 08:53:01 CDT. It verified
all 1,829 staged source/artifact hashes, exact program/live admission,
31 saved metadata/control/log hashes, all 36 response bindings, final raw
Console INFO, source/image/boots, public settings/current watermarks,
recorded GPSDO restoration and all 20 registered processes gone. Fresh
host checks verified all four locks, filesystem UUIDs and restored active
service. Recorded A is empty; B is aborted on its exact owned job
`8a8e01f9c1dcd5a092d6bcb9b695237b`; both outputs are inactive, unowned,
disabled with zero recorded faults. This is independent failure integrity,
not a full IQ or RF acceptance review or fresh target/full-flash proof.

All six new sample files remain internal and unchanged in stat identity:
A 7,290,000,000 bytes, B partial `.cf32.incomplete` 785,691,648 bytes, and
four reference raws totaling 64,000,000 bytes; total 8,139,691,648 bytes.
No new IQ reads, transfer, deletion, firmware load, reset or settings write
occurred during the review. Every older failed recording/control/flag remains.
The original limits and the 30-second repaired harness are unchanged.

Memory qualification is blocked because the mixed run did not pass. No retry,
new RF, memory, retention or release stage is admitted or queued. Never replay
the closed run, inventory, review or reservation. Monitor the closed state only
with the new `build/phase14-browser-harness-mixed-reset-closed-state-live-reader-20261013.py`
via SSH stdin; verify fresh identities/receipt every report. Hourly reporting
remains active at its existing cadence/content: Harness RUNNING/STOPPED/UNKNOWN,
3 of 9 (33.3%), estimated 15–37 hours with the new failure and possible extension.
Counts and fixed 37,546 seconds receive no failed/partial/review/elapsed credit.
These facts supersede older running/first-A/first-B activity entries only.

## October 13 repaired harness mixed qualification running at original limits

The new mixed coordinator was dispatched once at 12:30 UTC after the independent reserve post-review closed. Fresh observation `1791894762685573841` verifies parent `3848545/start81241607`, completed reference-before (exit 0), acquisition `3848740/start81249627` and native first-A Tone capture `3848748/start81250614`. Actual live admission `ea9591a3` preceded RF. Result `c52c3dfa` is RUNNING with no errors and zero whole accepted observations; only the coordinator restores its stopped service. Monitoring makes no new device or sample requests, and competing capture/analysis/archive/review work is prohibited.

The repaired harness uses a 30-second absolute HTTPS request budget and one in-flight read worker, allowing STATUS/INFO/RENEW polling during requests. All 47 Linux checks and 24 authenticated reads on the existing mesh passed independent review. Firmware DDA/138, TLS security, original eight hour A/B workload, 45-second idle, one-second idle samples, 1024-byte screens, browser success count/span, scientific drivers, references and original finite bounds remain intact. This is a running qualification, not whole acceptance or leak-freedom evidence.

Reserve admission `22ce5871`, release `865b8c12` and full separate post-review `e394a9ee` are closed/gone. Exactly 75 internal clock duplicates (14.736 GB) were removed through guarded per-file source/durable proof and retrieval-before-unlink; every durable recording, companion, original flag, failed sample and useful image remains. There are 106 known clock source absences. Seven fixed closed metadata receipts (699,214 bytes, no keys/raw samples) are retained under `build/phase14-browser-harness-closed-validation-20261013/`. Source/code/doc edits remain uncommitted; unrelated user changes remain intact.

Hourly reporting stays active. Counts remain 3 of 9 (33.3%), estimated 15–37 hours. Whole eight-job review and exact process closure are required before credit or separately admitted memory follow-up. Historical activity entries below are superseded by this actual running state.


## October 13 repaired harness verified on the mesh; mixed admission closed

All 24 authenticated reads succeeded on the existing Ethernet/Orbi path, taking 1.77–2.57 seconds each. Independent review `16574498` binds all response receipts, 193 raw Console INFO observations, control polling during every request, unchanged source/boots/public settings/current watermarks, restored service and gone processes. The new 30-second total HTTPS budget and single read worker address the harness deadline and blocked polling defects. No isolated Orbi cause or long qualification acceptance is claimed; all prior failures remain immutable.

The new internal toolroot is `resume-tools-dda8a6e-browser-deadline-async-internal-first-20261013`, catalog `ed24fedf` and stage `f38d4bdb`. Firmware DDA/138 remains unchanged; the separately identified Python harness snapshot is uncommitted. New mixed programme admission `4bacdf68` verifies unchanged eight-hour science, ownership/cleanup execution, 45-second idle, one-second idle samples, 1024-byte screens, successful browser count/span and original finite bounds.

Its actual storage shortage is 14.64 GB. A distinct full source/durable review is running on the 78 selected clock duplicates and 534 recursive pairs under all four locks; no removal or RF has started. Per-file publication on both filesystems, immediate full hashes/stat/no-user checks, duplicate-only release and separate full post-review must close before the mixed launch. Counts remain 3 of 9 (33.3%), estimated 15–37 hours. Previous activity entries below are historical.


## October 13 harness deadlines and control polling repaired; Linux checks closed

LATEST HUMAN HARNESS-DELAY AUTHORITY AND CLOSED LINUX VALIDATION — 2026-10-13. Human says real-world delays must be accounted for by harness and authorizes AP on wspr5. This supersedes historical four-second network deadline restrictions ONLY; original RF/science/eight-hour/45s idle/1s idle INFO/1024 growth/browser success-count/span/reference/bounds remain. No RF/mixed/memory/retention/AP stage admitted or queued. Fresh host quiet observed_ns1791891118383990572; verify fresh every action/report, do not carry STOPPED forward.
Actual source Python changes local uncommitted: Browser overall HTTPS deadline30s across TCP/TLS/body, stage/elapsed diagnostics, no retries, one in-flight read worker keeps main STATUS/INFO/RENEW polling independent. TLS1.3/ALPN/mutual cert/fingerprint/hostname/status200/complete length/cap131072/read-only four paths remain. Browser >=300 successful responses and >=3500s span unchanged; no timeout/failure/partial credit. Firmware remains ordinary DDA/138/UF2091a647aeecd845ba35de036a82f0f24d7880ca4dbace202d8c3367556995a5b, Abootbc63566fd9201be27577db13ed22e5bf/Bboot6870c9af19ab3b6016d66ebf009cedc2 recorded. Harness code not live-qualified. Local Browser6d78f062ab3b91e5141a5f3ac752c19a9c4e979d5a750cfc9f02dbe2c077a78f/livee08a627e2c5c224427b440a98a9a1bbdec7bd9284537a2a685e5f75517ee17bb/newtests351cb625a9ce304d25afa822ef5bf966e81ea61733377100a195807f4d3754ce.
Actual Linux host validation D=/home/pi/phase14-qualification-20261008/build/browser-harness-deadline-host-validation-20261013, inputs0855f83e67e75204b6afa839f9b510bf90699e184d164cd12b16da21fdcd42d2, independent closed review9fcf4e653d2026848b3afe9c580f5ff6fb5527e19d3e45285efa3b1e0dc85cd1. Seven new tests + forty existing tests pass; forty split39+1 because first40 invocation lacked standalone_image_tests support. Preserve preflight typo refusal e674c613/zero jobs/no reservation; corrected-input result494ce564 includes7pass/39pass+support error; remaining single support-bound check1a21ac9e passed. All parents/children gone, all4locks/UUIDs/serviceactive verified, zero Device/RF/externalnetwork/CXX/build/install; one local loopback fixture. Never rerun completed helpers/tests/reservations.
All ARP diagnostics actually CLOSED/GONE/REVIEWED: contrast result75e2c437864fef0d58a6780021a0d7e1d2a46db6248f8e91e94af30d2f50d982/independentd2b390309cd322b0926d0f0e6ac46f13b72a6003dfebfba6da7a0b2d4fc70962. Broadcast controls work, unicast first B ingress relative5.807390179s late; B input-to-reply125–142us. Second unicast absent only during recorded window, no permanent-loss claim. Actual two-interface diagnostic784a69c2431ff3c1abaf00bad5686ed044ae5c667af5f8d3523a0b61bd9ccea8 FAILED before any TCP (3directINFO/zero network) because imported guard pinned stale bootd87 vs actual687. Preserve original pendingTRUE receipt/events_sha256ABSENT, independent owned-service-only restoration cbfeec27/closed review8aade0711461a37da615c22ae25194f17b7b84823cef86ac75013ffc37193de7. Serviceactive restored; no changed firmware/profile/cursor/settings/hostroutes. Closed old guard must never execute as-is; new admission must test expected current boot and wrong-boot refusal.
Human Orbi version7.2.8.8/currentmesh Bohica and Bohica-IoT nearby. Host eth0IP54 active/netplan; externalwlan1IP117 active/Bohica-IoT; onboardwlan0disconnected; externalwlan2MACe84e06aed709disconnected. Temporary isolated AP permitted on unused capable radio after source/identity/route/profile/currentsettings/finite/restoration review, no credentials export. No AP created. Existing mesh must be validated with repaired harness. Next prepare NEW finite RF-off 24authenticated read validation of repaired Browser/worker with actual independent programme and fresh named source/boot/publicsettings/watermark/defaultfalse/emptyunowneddisabled/synchronized/network/runtime/source/4locks/UUID/service guards. No duplicate old GET helpers/reservations. New acceptance precedes ready-source mixed admission and actual reserve, never old RF entry as-is. No firmware cause claim from network timeouts.
PrimaryHEADdda8a6eb1e69539b7399cdd899d8830a2d199769/develahead74/indexempty; preserve unrelated implementation-planSHA20dc830b58eb1c08001162b4359e5ddba8e13fee85be6ec57e1bf7ca94a63ca7/untrackedSi5351/allworktrees/usefulimages/failedsamples. No Git mutation unless explicit request; automatic approval rejected stage/commit per current AGENTS. No SDK/tools/nativeMacCXX/publication. All prior retention/known31clockabsences/failedmixedraws/flags unchanged; no raw release admitted until actual new READY RF programme/shortage/full guarded durable proofs. Finalpush/parity/closeout unfinished. Four/two metre all-mode unsupported stays, no upperband RF/decoder/mapping. Final B consumer24KiB only preserve current8KiB cursor; AconsumerAPI pending.
Hourly ACTIVE/existing RRULE/notificationpolicy unchanged; every NOTIFY fresh HarnessRUNNING/STOPPED/UNKNOWN |3of9workstreams(33.3%)complete;estimated15–37hoursremaining; currentstage/mixedmemorypending/possibleextension. Fixed37546s unchanged/no elapsed/host/preparation/partial/diagnostic credit. Historical immutable evidence follows; stale activity/next-actions superseded only.


## October 13 two ARP replies verified; broadcast/unicast contrast active

LATEST ACTUAL BROADCAST/UNICAST ARP CONTRAST ACTIVE — 2026-10-13 04:21 UTC. Leading authority supersedes old two-ARP ACTIVE/EEE/bus/loop activity only. Previous two-ARP diagnostic ACTUALLY CLOSED/GONE: resultce0490e7d9563be372269d5288487e3d06296951325e3f8b1474cba50d8d0b91/independent39b7eff3969f0d08280420cef171e39e18cac173048d4e4351e6f57569584915 at1791865209521244879. Both real broadcast42B requests received identical BARP replies, host455775805/289620288ns; Bnetif input→output127/137us/bus123/133us. 28INFO/11TRACE/6namedPT/all source/control/settings/currentwatermarks/newordinaryBbootd66656e5559432de5dc29bbe500f7754/unchangedAbootbc63566fd9201be27577db13ed22e5bf/serviceactive/4locks/UUIDs/exactgone verified. No TLS fix/cause/qualification credit.

NEW ROOT=/home/pi/phase14-qualification-20261008/build/resume-tools-loop-profile-cd93ab1-internal-first; P/build/arp-delivery-contrast-program-20261013; output ROOT/build/arp-delivery-contrast-diagnostic-20261013/result.json. Coordinator25b466b4b04b9c15fc6b4ccda1e26b22ad3f9b8759485453f7b3ca00cb9fe967/reviewer8b5a72d88f85aafa7daf899f93e44b2ff87e2b1b806d64cb3705e6e63d3cce5f/manifestf0e985079b5e48b93af8c7b0aed07edbf64ee69fc4499e52ef4f106e866ce845/stage38b0623c96eea888b5f4c7beedac716c023f0311b69aa5a3627b571e80665589. Actualadmission3aee5a0133983b03b45f1704b05bdae8a8f90369d663b5f0d9f6697f36532bef passed11guards12newwirefixtures+narrow nine unchanged owned/source/closure function AST and entire finally reuse; oldprogramme/fixtures not repeated.

Actualparent3647791/start78308536 RUNNING observed1791865296924916522/receipta261f2e334d1af8eb2940a1e8d2d0acdcfddc6036efb13485e1e1301a4c579e3. Exactly FOUR fixed42B ARP requests broadcast/unicast/broadcast/unicast to actual BMAC88a29e0a9d89; real PiMAC2ccf67627664/IP54 targetB53/no spoof,4s receive10s cadence. Reviewed private loopimage4a33/cd93 is installed ONLYB; currentdiagnosticboot must be read fresh. Existing ordinary091/DDA and failed evidence preserved. NETTRACE aftereach, no TCP/TLS/HTTP/ICMP/WTP/RF/GPSDO/receiver/raw/hostsetting/profile/config/cursor/copy/removal/laterqueue. 600whole360operational240restoration/PT45/boot90/all4locks/source/UUID/currentsettings/watermarks/falseflags/finite ownchildren and ordinary B+ownedservice restoration mandatory. Never duplicate/change/restart/signal inputs/processes. Monitor ONLY SSHstdin build/phase14-arp-delivery-contrast-live-reader-20261013.py, fresh PID/start/argv/receipts everyreport/action; afteractualwholeclosure/exactgone NEW independent metadata/control/source/packet/restoration review before cause/fix selection.

Original task persists: find/fix B TLS transport then NEW admitted/live source-bound original8jobmixed after positive transport readiness/fullreserve; mixed/memory/release UNADMITTED/UNQUEUED. No automatic chain/oldentry execution/timeout orcadence or1024criteria relaxation. Originalscience/reference128MB/45sidle/1sINFO/8hours/43200whole36000acq7200analysis unchanged. No upperband4m2mRF/decoder/native mapping, SDK/tools/nativeMac C++/publication/Gitmutation/rawMaccopy/removal. All current/old images/worktrees/unrelated implementationplan20dc/untrackedSi5351/indexempty/develahead74 preserved. Counts3of9/33.3%,ETA15–37h/fixed37546s unchanged; no partial/diagnostic/elapsed credit. HourlyACTIVE/existingRRULE/policy unchanged, everyNOTIFY freshHarnessRUNNING/STOPPED/UNKNOWN+countspercentETA/currentstage/unresolvedmixedmemory/mayextend. Leading actual activity supersedes historical stale next-actions only.


## October 13 two-sender failures closed; finite ARP receive diagnosis active

Supersedes older EEE/bus/loop/two-sender-active descriptions. Ordinary DDA source dda8a6eb1e69539b7399cdd899d8830a2d199769/138 UF2 091a647aeecd845ba35de036a82f0f24d7880ca4dbace202d8c3367556995a5b preserved; A boot bc63566fd9201be27577db13ed22e5bf, pre-diagnostic B d87edf97beca9b247d7b6a7da72ff352. Every original failed sample/control/flag/nonraw remains immutable; no new IQ hash/copy/removal/RF/qualification credit.

EEE link-ready continuation CLOSED/GONE: result52239e16bf6b6ba06c3f96e56d40a45f85393728035de487085de704023b9d0a/independentb0454f4d095dfa2beee3c15264a55688996f74f1e674f9073f62895cdeb18897, TCP connect still timed out after five consecutive 1Gbps/full/carrier1/EEEoff readings. Initial dc5/bc0 link-down confound preserved. EEE enabled-active/TxLPI250000us restored; no EEE fix selected.

Two-sender comparison CLOSED/GONE: ORDROOT/build/two-sender-tcp-diagnostic-20261013/result.json SHA370dda1d77a2a6fb208ad2afee2e074546e935247e8d66a9c9b26912f77bacde; independent1d2d7adf3d7649a0835c0ace55ecb2f1496e879bcef1333c43de93d654518fb9 at observed1791864227875845960. Parent3640068/start78138857/local producer+SSH gone. Four Pi54 and four Mac52 bare TCP connects to B53:443 all original4s timeout, no TLS/application bytes. Twelve INFO/source/sameboots/settings/cursors/falseflags/owned-service restored; all4locks/UUIDs verified. Both senders lack usable B ARP (Mac none/PiFAILED); old recorded ARP inspection75021a8d97d28682b01785d5622eb6a651287f55c30af52e8b153a5a8c53e81c contains other ARP but no who-has B53. No sole-host/TLS/EEE/netmask cause selected.

NEW ARP programme ROOT=/home/pi/phase14-qualification-20261008/build/resume-tools-loop-profile-cd93ab1-internal-first; P=ROOT/build/arp-receive-path-program-20261013; output ROOT/build/arp-receive-path-diagnostic-20261013/result.json. Coordinator8c720882b10d3b3aee535fbacd3bc88e66321195fb7c5358d569e1c2ffc2a46e/reviewereb54922ca4871ff889487845fc23afc34dec5a72498edcaf0bedf42b355f4cf1/manifested644a5a07dec4baf4cfe29788d1a59c3b1e6fcfea30514e735e6d543df3fc30/staged680ff38fd85ec4831b3ef83480804581f37befd4984469262b20445d9a362f9. Actual admission27b59422234ef394486d9ae9718819c1b509860e1b2b6cf622cc7d3fb0833b96 passed11checks7new packet refusal fixtures/1833source bindings and narrow old27guard9fixture AST reuse WITHOUT repeating old helpers/fixtures.

Actual parent3646379/start78279864 RUNNING at observed1791865010778038073, receipt792d044d145f7919589048817abc06644826efcac1335c4d018bf8fbd3192297. Private already reviewed loop diagnostic snapshotcd93ab17/UF24a33aaed94420373edca6dd88e202118a07c53cd036bcb1a1cade1fe49fca182, compiled DDA-dirty not ordinary, installed ONLY B. Exactly TWO42-byte fixed ARP requests local real Pi MAC/IP54 to B53 with4s receive/10s spacing; NETTRACE only after each. NO TCP/TLS/HTTP/ICMP/WTP/RF/receiver/GPSDO/profile/config/cursor/hostsetting write/raw/copy/release/laterqueue. 600whole/360operational/240restoration/PT45/boot90/all4locks/source/UUID/finite ownchildren and ordinary B+owned-service restoration mandatory. Do not duplicate/change/signal/restart any active process/input. Monitor ONLY SSHstdin build/phase14-arp-receive-path-live-reader-20261013.py; fresh PID/start/argv/receipt every report. Actual all-closed/exactgone+NEW independent control/ARP/source/image/boot/settings/cursors/restoration review mandatory before cause/fix selection.

User-authorized B TLS diagnosis/fix and original-limits mixed continue. Mixed/memory/release UNADMITTED/UNQUEUED; transport readiness/cause/fix not established. NEW positive source-bound admission/live/currentboots/full reserve+original8job science mandatory before mixed. Keep original45s/1sINFO/1024growthspread/8hour/reference128MB/43200whole36000acq7200analysis; no retries/timeout/cadence/criteria relaxation or autochain. 4m2mALLMODEUNSUPPORTED_RELEASE/no upperband RF/decoder/native mapping. No SDK/tools/nativeMac C++/publication/Gitmutation. Indexempty/develahead74/unrelated implementation-plan20dc830b/untrackedSi5351/all6worktrees/images preserved. Finalpush/parity/closeout unfinished.

Hourly ACTIVE/existing schedule/policy unchanged; every NOTIFY fresh HarnessRUNNING/STOPPED/UNKNOWN |3of9workstreams33.3%;estimated15–37hours; currentstage/unresolvedmixedmemory/mayextend. Fixed37546s unchanged/no elapsed/partial/diagnostic/preparation credit. Older evidence follows; leading current activity and next steps supersede stale descriptions only.


## October 13 EEE link-transition failure closed; link-aware continuation active

The bus-awake contrast failed and is independently closed at result
ef1887f868ceba4a89040de3791a805c8fd140805d20b39816c56400cec106e1,
review179f0964e212026129a16b14fb991594d543d02e5ba0537d14bc0cef6ed81bd7.
No bus-sleep repair is selected. Ordinary DDA/138 B boot is now
d87edf97beca9b247d7b6a7da72ff352; A remains bc63566fd9201be27577db13ed22e5bf.
All images/public settings/current watermarks/false flags and failed evidence remain.

The first host EEE contrast failed at TCP connect. Result
dc5af898cab94ec8156ab9785910e96e2afb6b05503fde3ddf13c2602e911ced
and independent review bc0aecb568c20b3d08becf382a611522a01e11f3529202e4c276e314e69255bb
are closed/gone with EEE and owned service restored. Actual kernel messages
prove eth0 was down from 1791862341.361845 to 1791862344.433845, overlapping
the original four-second connect. The setting readback was admitted, but
post-change carrier readiness was not. Preserve that protocol failure; it
cannot reject EEE as the cause. No Pico firmware change occurred.

The actual macb/6.18.34 host has active EEE/250000us Tx LPI. Primary upstream
[Raspberry Pi issue7511](https://github.com/raspberrypi/linux/issues/7511)
supplies an applicable lead only. A new finite link-aware continuation adds
five consecutive one-second carrier/1Gbps/full-duplex/EEE readbacks within
30 seconds after each EEE change, plus a fresh named B idle/synchronized guard
before TLS. Original browser security, four-second timeout/ten-second cadence,
24 off reads and one separate restored-on control, 600 whole/540 operational
bounds, locks/UUIDs and unconditional owned EEE/service restoration remain.
No firmware, RF, IQ, profile/configuration/cursor writes or later queue.

Admission dda30fd63eb789947df8a4c94bef12937bed31d82dcb117bdb3ae113a6a62811
passed six checks/six new readiness fixtures, narrowly reusing the exact old
16/7 setting proof without repeating old helpers or fixtures. Parent
3636404/start78062897 was active at observed_ns1791862876325414892; receipt
b83d271db170138c9c4a611bf820aa3c0c4ca73267096c45c8fda564a3b36aeb was pre-device.
Never duplicate/change/signal/restart active inputs or processes. Monitor ONLY
the SSH-stdin build/phase14-host-eee-link-ready-live-reader-20261013.py;
verify fresh PID/start/argv/receipt. Whole closure, actual EEE/service/board
restoration and a new independent review precede any repair selection or RF.

Counts3/9/33.3%, ETA15-37h/fixed37546s unchanged; mixed/memory/release are not
admitted or queued. All prior failed IQs/controls/flags/nonraws and only copies
remain. Git/index/user changes/worktrees are preserved; no new Git mutation.
This leading entry supersedes older activity and EEE-negative cause wording.

## October 13 bus-awake causal contrast active

A new private default-off bus-sleep contrast changes only the gated low-level
can_sleep return relative to the closed loop observer. Snapshot
`dc0f6f80bbd9fd001a177d1f681468f2056cb64c011bfa9409126abe68c33dbd`
is reviewed at `b6f863aa36adac67620354461fe4253e495e3b6f745f94cc38ae55c1a598551a`;
two Arm ELF/UF2 builds are byte-identical. Diagnostic UF2 is
`be7ecbb34e25f6d19b04f75699577edb02b60966fef6a8750fd85ddf296375a1`.
Production remains ordinary DDA; the diagnostic is not a selected fix.

Actual admission `a75537c233a7ed78cf58e34382a6bcea1c7795dd3a4abbc08e0a51ac7e6154d3`
passed five new binding refusals and AST-verified unchanged control/restoration
code, narrowly retaining the closed 27 guards/nine fixtures without executing
them again. Source staging verifies all 1,833 files; stage proof
`7b0e7258b0e3428cf84dd108b7f251040734292c07111bf5426acd92f49ae1d4`.
The first artifact review was blocked by sandbox ps before output; a distinct
process-access review completed without any source/build/device rerun.

Parent PID 3630634/start 77943192 was freshly active at observed_ns
1791861661113923264, receipt `a3f77f36b5f0487e07b262a7563bf2ed5a8ca03a4d4c71289c97bedbaf17a7e1`.
The unique programme holds four locks and runs at most 24 original authenticated
TLS reads, four-second timeout/ten-second cadence/900-second whole bound,
with synchronized-time admission and guarded B-only ordinary-image/owned-service
restoration. No RF, IQ, profile/configuration/cursor writes or later queue.
Do not modify, duplicate, signal or restart it. Monitor only the SSH-stdin
`build/phase14-bus-awake-contrast-live-reader-20261013.py`; a saved RUNNING
receipt is not current status. Whole closure and a distinct independent review
are mandatory before selecting a fix or mixed continuation. All previous
failed evidence remains immutable; counts and ETA receive no diagnostic credit.

## October 13 loop-profile connect failure closed; bus-wakeup contrast planned

Result `98cb4d59ea009b5a4398d13f8768107f54d9a722d798e31c56ac8e0db6db105a`
failed before TLS at the first TCP connect under the original four-second
limit. Independent review `0e3863a3576582176af493702bb85ca1ee763b80e884d48e5efcefd9344bec08`
verifies all source/control/packet hashes and ordinary restoration. All exact
parent/collector/tool processes are gone. B's ordinary DDA/138 image is restored
at boot `8642d67072e211ed7dac337b75cb75d1`; A retains
`bc63566fd9201be27577db13ed22e5bf`. Public settings/current watermarks and false
flags are preserved; the owned service is active. The first reviewer refused a
success-only traceback field before output or device access; the distinct
schema-aware review above preserves that refusal.

The complete trace contains all four SYN retries, delivered to B in a 2.1 ms
burst after the timeout. First SYN-ACK at wspr5 is 4.586 seconds after the first
SYN. The after-failure driver snapshot precedes that delivery and records zero
TCP while multicast grows 12 to 82. The earlier snapshot therefore cannot
support complete-trace absence. Header inspection
`c472e9779940d7028e13042e662ed1e6929b1ab9d9329fcfb7f94a0c539c341d`
preserves packet/device timestamps. Both loop-profile snapshots are identical;
no foreground interval reached 100 ms during the failed connect. PM reads off,
RSSI is -28 dBm, and driver/security errors do not increase. Cause remains
unisolated within the AP/radio/firmware/host path.

Wired inspection `32b70a1b6235ce70b14e374baf99b62205d74afc45ea7777cd0b1cb5f32bcbc7`
records a 1 Gb/s full-duplex link, correct B MAC/direct route and zero reported
link/checksum/queue-drop errors, with no network probe. The pinned driver can
sleep its host bus independently of Wi-Fi PM; INFO/radio IOCTL reads wake that
bus. Next is a distinct default-off private contrast suppressing only the
low-level can_sleep transition, with the existing observation hooks retained.
Source/build/program/live admission must precede execution. Original browser
security, 24 read-only requests, four-second timeout/ten-second cadence,
900-second bound, four locks and B-only ordinary restoration remain required.
The AP/context question is optional and pending. This is not a selected fix.

All failed samples, controls and flags remain immutable. Mixed/memory remain
unadmitted/unqueued. Original RF limits/science, 3/9 (33.3%), 15–37 hours and
37,546 fixed seconds remain unchanged; transport may extend the estimate.
Do not repeat completed helpers/fixtures/reviewers/reservations. Verify fresh
PID/start/argv/receipts for every report. This entry supersedes older activity,
current-B-boot and complete-absence descriptions only.

## October 13 client transport contrast failed; loop profile active

The client TCP_NODELAY contrast failed on its first TLS handshake, with zero
responses. Result `29a09f989b08804df39dcd30a0e4a2923e554dda4cfb6946be1fe2fb99e389b1`
and independent negative review `7b401c93310549e5d22e63f24697e03b261ea3fdb5aad45cd2bda15171226e8c`
are closed, with all registered processes gone. B's ordinary DDA/138 image,
boot `771bd72c3483ca6a18c3bb44e6587dad`, public settings/current watermarks and
false flags are preserved. The owned service is active. No client change was
selected or applied to production, and no qualification credit is earned.

Its capture contains 15 TCP packets with no kernel drops. B kept retransmitting
SYN-ACKs; the recorded post-timeout state had zero active/pending connections
and the idle TLS allocation baseline. This failure preceded an established
B TLS session. The 47-byte ClientHello tail was not transmitted even with
TCP_NODELAY set/read back, so the earlier attribution to Nagle alone is
unisolated. Link delivery delay and foreground-service delay remain distinct
possibilities; no AP, radio, driver or host-link cause is selected.

A new default-off timing observer snapshot
`cd93ab17bff09fd2c3ae20c1a3e8748e9e44ef30483bb235e0a58074220ebfe8`
records whole-loop/network/CYW43/BLE/TLS/USB/Console maxima and the last 32
intervals of at least 100 ms. Measurement hooks allocate nothing and change no
underlying control flow. Linux JSON/threshold/ring-order checks and independent
review `2adb46b86f51ba44b448b419c4b622f6eca0821054f605abeb38e68bfe3a37b1`
passed. Two Arm builds are byte-identical; independent source/default-off/layout
review `250755d99cc0f2581c6b72e034102ab16ec9d0664118754b19bb660e52a380ee`
binds diagnostic UF2 `4a33aaed94420373edca6dd88e202118a07c53cd036bcb1a1cade1fe49fca182`.

The separately identified programme passed 27 guards and nine new failure/
restoration fixtures before hardware access. Admission is
`988435a8c65d368921657c266c5f5e373ce98d1ea94c45da6dbe8d88bb153e4d`.
Parent PID 3623659/start 77793338 was freshly verified active at observed_ns
1791860171331152009. It runs the original browser transport at four-second
socket timeout/ten-second cadence, requires synchronized time before TLS and
restores only B's ordinary image and the owned service. Trace reads occur after
the workload/failure; overwritten trace prefixes are recorded explicitly and
cannot support a complete absence claim. All four locks, source/settings/boot
and finite process guards remain in place. No RF/IQ/configuration/profile/cursor
or retention operation is part of this diagnostic.

All original failed evidence and preparer/compile refusals are preserved.
Mixed/memory stages remain unadmitted and unqueued. Counts remain 3 of 9
(33.3%); the recorded 15–37 hour estimate and 37,546 fixed seconds remain
unchanged. Unresolved transport may extend the estimate. This leading entry
supersedes older activity and Nagle-only cause descriptions; every RUNNING
report still requires a fresh exact process/receipt check.

## October 13 closed receive observer; client transport contrast active

The network-ready driver observer failed on its second TLS handshake after one
successful root response. Result `d22b1247bccfe57660d2685253625cbc5eea37625747a87a7c8c88c041c3cd22`
and independent review `e75371938630a980d2178ce3323c6b3c95160ad34c8f090b811473705e1b122d`
are closed, with all registered processes gone. B's ordinary DDA/138 image was
verified and restored to boot `771bd72c3483ca6a18c3bb44e6587dad`; A's boot is
unchanged. Public settings/current watermarks and false flags are preserved;
the service is active. Equality is not a new full-flash proof.

The observer recorded no new SPI/SDPCM or association/security error during
the failed request. Its four multicast-decode events and two parser errors
already existed at baseline and did not increase. All original failed evidence
remains immutable. Saved header inspection `66071d005b3aab837685b0590a43894b49ae43093e48d9e97d8877324f139a6f`
compares 140 Ethernet TCP packets with 128 on-board TCP records. Incoming SYNs
arrived at the board in a burst; the client also withheld the last 47 bytes of
its ClientHello until an ACK. This is evidence of delay, not isolation of a
radio, AP, host-link or foreground-service cause.

A separately identified private client transport contrast is now active. It
sets and verifies TCP_NODELAY before the original TLS wrap. The GET method's
AST is otherwise identical: TLS 1.3, mutual authentication, certificate/server
fingerprint, ALPN, body length/hash, four-second socket timeout, 24 requests
and ten-second cadence remain unchanged. Programme admission
`570a2ab11a318d81c8c55d6662fe615e7e21be4843bb223a8134e771be4d0f17`
passed 16 guards and five new socket/error/security fixtures before real
requests. Parent PID 3615904/start 77621644 was freshly verified active at
observed_ns 1791858453705848650. Only its coordinator restores the owned
service. No firmware, profile/configuration/cursor, RF, GPSDO/receiver or IQ
operation is part of the contrast.

The preceding observer's initial readiness attempt remains failed at
`e064662e848574e058a1f26b619f1792500226dead8bb4566d6b67a195b66bfc`:
no TLS request ran, its clock stayed unsynchronized within 90 seconds, and
closeout reached the 221st INFO attempt before the 220-request cap refused it.
The ordinary image had been verified/reloaded. Separate three-INFO service
restoration `d9a4dfb79ed327eadaace7d5142904a37fdd6503e26675f91fdd1c27ce03bcd4`
was independently reviewed at `61d3c6d365e6b12e20675f6648be59bc1eff889d05697cdd9a3bafa2fcb38c0b`.
The later RF-off observer recorded clock state while requiring TLS network
identity; synchronized time remains mandatory for mixed RF qualification.

No client repair or transport qualification is credited from partial results.
Mixed/memory stages remain unadmitted and unqueued. Original scientific
limits, 3 of 9 workstreams (33.3%), the recorded 15–37 hour estimate and 37,546
fixed seconds are unchanged; unresolved transport may extend the estimate.
This entry supersedes older live activity and current-boot descriptions.

## October 13 low-level receive observer admitted and active

The new private snapshot `899a6046ebf2bc7903698217c23cb71f8e5c1b130b7730520b9633d5748315a0`
adds read-only SPI/SDPCM receive-error counters and association/security event
counts. Its two 138 MHz Arm builds are byte-identical, diagnostic UF2
`42bcebf96a5d5a6372f6bd47e495d5362700e448c55982009ca3ef71c0345948`;
independent source/artifact review is `36155ac3c1878a6adc18c83b3c6f535aaa66b27b7e884d361f2dd6aa3863d3d5`.
The honest compiled identity is `dda8a6eb1e69-dirty`. The counter overlays
retain the original receive and association flow and are disabled by default.

Internal source staging verified all 1,832 files. Separate programme admission
`476ce20c2d14bece14727950353e6b902fa175b3d1b79f6eea33e5b7e2230ac6`
passed 23 checks and nine new failure/restoration fixtures before hardware
access. Coordinator `89170356eb6f17b834c5256ae3c32e5ea9117d4873c3e5798516569128fe35ba`
was dispatched once; parent PID 3610184/start 77488352 was freshly verified
active at observed_ns 1791857178238146700. The stage permits one radio read,
two counter reads, bounded trace pages and 24 authenticated read-only requests
at the original four-second socket timeout and ten-second cadence. Its whole,
operational and restoration limits are 900/660/240 seconds. All four locks and
verified own child cleanup remain required; only this coordinator restores B
and the service. Current installation/restoration is pending; no diagnosis or
qualification is credited from partial results.

The ordinary DDA image must be restored after this diagnostic. A retains boot
`bc63566fd9201be27577db13ed22e5bf`; B's pre-diagnostic ordinary boot was
`6024f7b90d8aec003250df66ef1c5ddb`. Public settings/current watermarks must be
preserved, with no profile/configuration/cursor writes. Earlier failed IQ,
controls, flags and traces remain immutable. No RF/mixed/memory stage, retention
release or later queue is admitted. Counts remain 3 of 9 (33.3%); the recorded
15–37 hour estimate and 37,546 fixed seconds are unchanged. Unresolved
transport can extend the estimate. This is a live checkpoint, not authority
to carry RUNNING forward without a fresh receipt and exact process check.

## October 13 receive-path diagnostic closed; loss precedes lwIP

Both boards currently retain ordinary clean `dda8a6eb1e695` at 138 MHz, UF2
`091a647aeecd845ba35de036a82f0f24d7880ca4dbace202d8c3367556995a5b`.
A boot `bc63566fd9201be27577db13ed22e5bf` is unchanged; B was restored to new
boot `6024f7b90d8aec003250df66ef1c5ddb`. The owned service is active and all
registered diagnostic/collector/tool processes are gone. Public settings and
current watermarks are preserved; equality is not a fresh full-flash proof.
This leading entry supersedes older current-source/activity/boot descriptions.

The separate read-only trace used the honest `dda8a6eb1e69-dirty` diagnostic
snapshot `daea7ec3acf3cd3e51c49f64e036ed8d0fdca7e094a36b1e9c80f1bbebed7f4b`.
Its two Arm rebuilds were byte-identical; source/artifact review and the new
21-check/six-fixture program admission completed before device access. The
first root request timed out in HTTP receive at the original four-second
socket timeout. Result `61e6a8eaad84dc5d9ca4076eb66a15d34bf93e96525c6bfa87de9bb01b495ac3`
remains failed, with 55 INFO attempts, five trace pages and one radio read.
B's ordinary image was verified and restored; restoration/control errors and
pending flags are clear. Independent closed failure/source/control/header and
restoration review `34900461be71b1630bb3735684e87c3d056c319621e62827800e0e7e38b75458`
verified 51 successful raw Console bindings and six named B tool calls.

Hardware readback measured power-save mode 0 (off), RSSI −27 dBm and BSSID
`ce:9e:43:b7:cd:84`. Ethernet capture has 34 packets and zero kernel drops;
its hash is `30ee0270e42ca869e8e1d59eb3d0b5691f44c5768acad67d57c2967c8c0b0e48`.
On-board netif tracing retained 27 events with no ring overflow. Pi TCP ACKs
and the 1,141-byte client-authentication flight/retransmissions are absent at
B's netif input, while multicast and ARP continue to arrive. This narrows loss
to before lwIP/TLS receive; it does not isolate Wi-Fi firmware, driver, AP or
host-link cause. No packet-pool/heap/allocation/stack/DMA fault or transmit-credit
wait was recorded. Saved header inspection is `32978a726cfa09f29edf10c59e761aa3fd0ebb420423d0babcf895b36a63aff3`.
Host queue inspection found no traffic-control drops, backlog or ingress/egress
filters; cumulative NIC counters are not causal evidence.

All failed IQ/control/flags/logs/header traces and previous source identities
remain preserved. No new RF/IQ/retention/removal occurred. A separate private
read-only low-level receive/error/association-event observer snapshot is being
cross-built; no further target diagnostic, RF/mixed/memory stage or retention
release is admitted or queued. The mixed draft is stale and unadmitted.
Original scientific limits, counts 3 of 9 (33.3%), ETA 15–37 hours and fixed
37,546 seconds remain unchanged; unresolved transport may extend the estimate.

The operator requested reduced storage on October 10, 2026. The Mac was down
to about 3.9 GiB free; wspr1, wspr2 and wspr4 use SD cards. This amendment
changes storage and encoding, while retaining the required measurements,
original result records, failed evidence and complete raw sample contents.

## October 13 outgoing TLS repair installed; HTTP receive failure preserved

This leading entry supersedes the current-source and activity descriptions in
older entries below. Both named boards currently run clean `dda8a6eb1e695`
at 138 MHz, UF2 SHA-256
`091a647aeecd845ba35de036a82f0f24d7880ca4dbace202d8c3367556995a5b`.
A's boot is `bc63566fd9201be27577db13ed22e5bf`; B's current restored boot is
`3e7d3e6445138c02e346538cde57b8fc`. The pending-receive repair and TLS
Nagle repair are installed; ordinary image installation and independent review
are closed (`cbbd3b32bd24f529d9a149c9e29680e46fb0a54eb8f2b73cdbd9593df95df19c`
and `2fe0375771716c1c3be3e7b850057dc3da7bd1e82e41cb321774c7b951d2c81f`).
Public settings/current-watermark equality is not a fresh full-flash byte proof.

The new RF-off browser validation remains **failed**:
`tls-flight-browser-packet-validation-20261012/result.json`, SHA-256
`1f35e0d61084fc5a973ac75045aafde6038fed833ff18647baa14f398d09cd94`.
Fourteen HTTP responses completed. Attempt index 14, capabilities, completed
client TLS setup and timed out while reading HTTP at the original four-second
socket timeout. Its TCP-header trace contains 814 packets, zero kernel drops
and 73,956 bytes, SHA-256
`2e185864be328876adc312cc68227a251a1d409b39a855ed30cab2ec00ab56d7`.
The server's TLS records through Finished were ACKed; the client's subsequent
109-byte encrypted HTTP request received no B ACK through retransmissions.
The receive path is still unisolated. No receive-buffer, TLS-allocation or
stack/DMA fault was recorded. All registered processes are gone; both boards
are idle, outputs disabled and unowned, and the owned service is restored.

A distinct idle B ICMP contrast sent 24 unique packets with TLS/HTTP/WTP/RF
absent. All 24 replies arrived, but RTT ranged from 9.859 to 1,188.844 ms
(mean 209.211 ms). Result hash
`97e1b828241cc1ab3088557d60f5a5e101d11c390cb7d2780cf9dfe9312687a2`
and independent metadata/process/settings review
`0119ce289df2a341c4f9d2fa4053c441f0b133f233042a223a9313ba6ef192ee`
are closed. The saved power-save field is false on both boards; it is cached
adapter readback, not a fresh radio measurement. B's BLE service was running;
A's was stopped. Radio coexistence is a hypothesis, not an established cause.

The temporary `fa03a10687031e740b9438518d9d7f95c8b5f771` diagnostic was
built, independently reviewed and used for one B-only idle BLE contrast. Its
actual metadata-closeout result is **failed**, SHA-256
`c945e3a86122ea1af18915cd8f66e2beaca570d1c9d9312a1ec658daaa6f98b1`.
BLE-on sent/received 24/24 packets (mean RTT 46.028 ms); BLE-off sent/received
29/24 (17.2414% loss, mean RTT 233.928 ms). The diagnostic incorrectly assumed
that ping's combined count/deadline options bound transmitted packets to 24;
the extra five packets and assertion failure remain preserved. BLE suspension
is not selected as a repair or isolated cause.

All eight registered steps and the parent are gone. The ordinary `dda8a6e`
application was restored on B, now boot `3e7d3e6445138c02e346538cde57b8fc`.
A's boot remains `bc63566fd9201be27577db13ed22e5bf`. Public settings/current
watermarks, empty/unowned/disabled outputs and the active owned service were
restored; closeout/control errors and restoration-pending flags are clear.
Independent metadata inspection verified the actual logs/counts/control hash
and process closure. Full independent source/artifact/admission/control/log and
ordinary-restoration review is now closed, SHA-256
`4713a4b6d187e77fe44695e1eb0ca2baa344a8afd90ed52e3a42ebbe301ea194`. Existing failed TCP
traces use the expected B/Pi Ethernet MACs. Neither result isolates the receive
path. No new RF/mixed/memory/retention/release stage is admitted or queued.
A new default-off, read-only receive-path trace and actual radio power-save
readback are being prepared in a separate worktree; they are diagnostic only.

All original failed IQ, companions, flags and old source/image identities remain
preserved. No new IQ hashing, transfer or removal occurred. Automatic approval
review rejected copying full new host logs into the Mac workspace; those logs
remain internal on wspr5, and compact verified hashes/outcomes are retained.
Mixed qualification and its later memory follow-up remain unaccepted; the new
mixed draft is unadmitted, unstaged, unexecuted and unqueued. A positive current
transport review, new RF program/live admission and actual full storage reserve
are still required. Progress remains 3 of 9 (33.3%), estimated 15–37 hours with
possible extension; fixed remaining 37,546 seconds is unchanged.

## October 12 corrected repaired mixed closed with B TLS-handshake failure

This is the current state. It supersedes the earlier running snapshots below;
all older results, source identities and failure flags remain immutable.
The corrected run stopped during B's first Tone job after 322 successful
browser responses. The primary error is
`TimeoutError('_ssl.c:1012: The handshake operation timed out')` in
`ssl.do_handshake`, after TCP connection and before HTTP request `sendall`.
The failed next path is inferred as `/api/v1/capabilities` from the fixed
root/status/capabilities/jobs rotation; no HTTP request for that attempt was
sent. The last completed response was status, HTTP 200, 2,881 bytes, SHA-256
`ff2f3c5049679e199d3b911140fbbc2283b9a7e33e06c2bfbd2c3ae12ab6a2e9`.
This boundary does not isolate a firmware, TLS, network or host cause.

Actual failed parent receipt in the repaired source root is
`build/repaired-source-mixed-service-guard-20261012T192001/result.json`, SHA-256
`9de8b772e92c3325b596d3c3357c8c5815e2c9d084e39ee8ea568dc03f1bf993`.
The corrected coordinator preserved the primary child log/exit and two completed
Rig handoffs, reporting `ChildProcessError` without a secondary closeout error.
A's Tone control completed; B aborted with exact job
`455cc28378217a68172801116b89f9f1`. No whole mixed qualification completed,
no independent RF/raw acceptance occurred, and no workstream or capture credit
is added. The original 4-second browser connection/handshake timeout, scientific
limits, 8-job workload, 45-second idle, one-second INFO spacing and 1,024-byte
growth/spread screens were unchanged. No retry, firmware change or later stage
was dispatched.

A distinct saved-metadata inventory and independent metadata-only review are
actually complete. Review SHA-256 is
`23620e6a10bcefa9515661f702510d993d782f42e95e4ca3cded3ffcd2e04861`;
its helper is `f0924c04c266519654ca77eaa99e6fec60685eb3533a2c72a24c8a72cae9ce1a`.
It hash-bound eight explicitly named result/log/live-admission/raw-Console/
browser/physical metadata files, decoded final Console TX/RX, verified all
322 completed browser response records and fixed order, exact source/image/
new boots/public durable settings/current watermarks, cleanup and process
closure. Its scope is failure integrity, not independent IQ or whole RF
acceptance. Local private proof/source files are identically durable in the
repaired root's `build/repaired-mixed-tls-failure-metadata-closed-20261012/`;
fixed four-file size/hash/private-key-marker checks passed, with no credentials
or sample files copied.

Recorded final A is empty; B retains the exact safely aborted job. Both remain
clean repaired `2d67224dbddc` / reviewed 138 MHz image / expected new boots /
RF off / unowned / disabled / default-false flags. Public durable settings,
current watermarks and saved consumer profile equality passed; this is not a
new full-flash byte proof. Selected final connection/pending/RX/TCP counts and
fault/allocator/DMA/stack observations are zero. These are saved target
readbacks, not new device requests. B's last saved INFO is after cleanup and
must not be described as pre-timeout telemetry. GPSDO restoration is recorded
by the coordinator, while this metadata review made no GPSDO request.

Fresh host checks at observed_ns `1791840962174421871` verify all 18 registered
process identities gone, including parent 3519766/start 75059297, acquisition
3519966/start 75067112 and both captures. All campaign processes are gone;
all four locks were simultaneously available; actual internal/external UUIDs
and devices 66306/2049 match; `wsprrypi.service` is active and restoration is
not pending. Internal free is 55,316,123,648 bytes. The new run retains four
16 MB references, A's complete 7,290,000,000-byte raw and B's partial
6,898,074,624-byte raw internally. This review used sample stats only, performed
no new full IQ hash, transfer or removal, and preserved the earlier failed
partial recording, all original durable samples/companions/flags, useful images
and exactly 31 known clock-source absences. Closed retention/diagnostic/cleanup/
RF helpers and their reservations must not be repeated.

Next work is source-bound TLS failure diagnosis. First inspect exact deployed
TLS/connection lifecycle source and the saved B network/resource chronology.
If new measurement is required, prepare a distinct finite RF-off TLS-handshake
contrast with separate actual program/live admission, unchanged timeout,
source/image/new-boot/public-settings/current-watermark/aborted-job/credential/
process/lock/UUID/service safeguards, no HTTP mutations or RF. No diagnostic,
cleanup, new retention/release or RF successor is admitted or queued here.
Do not blindly rerun either failed mixed entry, relax deadlines or repeat the
closed GET/STATUS probes. Qualifying memory remains blocked until an actual
repaired whole mixed result is independently accepted and all processes gone.
Any future storage shortage must bind an actually ready new programme and
fresh reserve; the present free-space figure alone does not admit raw release.

Harness: STOPPED. Progress remains 3 of 9 original workstreams (33.3%);
estimated 15–37 hours remaining, with unresolved mixed/memory failures possibly
extending the estimate. Fixed remaining 37,546 seconds is unchanged. Hourly
reports remain active. Final push/remote parity/Phase 14 closeout are unfinished;
no native Mac C++ build, SDK/tool installation, publication or excluded-band
RF/decoder work occurred.

## October 12 final reserve closed; corrected repaired mixed actually running

This leading state supersedes the earlier failure/diagnostic-active/prepared
snapshots below. The original repaired first-A failure remains immutable
(`cc3140e1...`): header-only Plain LAN STATUS timeout, partial recording and
actual safe aborted cleanup; zero completed jobs or acceptance credit.

The distinct RF-off diagnostic actually closed and was independently reviewed:
1,024 STATUS exchanges / 60 direct INFO, one Plain LAN HELLO, no mutations or
RF. Result SHA-256 is
`e2766646638dcda9ff0fa8609021c56eb1c08718a850b9fdb6f29fa780f260f8`;
independent review is
`5663a7c0744bc3bebf0bff05dc785cfaa89be640fb72d225b69d42c21f3a4a82`.
Maximum STATUS latency was 1.42726568 seconds with the original five-second
deadline. The earlier active-RF timeout cause remains unisolated; this scope
is not long qualification or leak freedom. Exact diagnostic/reviewer processes
are gone. Do not repeat the probe/reviewer or its reservations.

A new mixed child-error candidate passed actual 106 guards and three new real
socket/fake-Rig fixtures (`5056acdb...`). Further review found service ownership
and uncertain-restoration publication flaws in its unexecuted cleanup-only mode;
that candidate/receipt remain preserved and must not execute as-is. A distinct
service-guard successor passed six new service-failure fixtures and fresh source/
artifact/runtime/receipt binding. Narrow AST applicability retains the actual
106/three prior proofs without repeating or relabeling them. Its PROGRAM
admission SHA-256 is
`7e97e79c1c6e75863dcfe3e3e79cadeef8fbaab6280f0ee2d09796ce8e286b67`.
The RF execution/science/handoff/owned-process cleanup and original limits are
unchanged. Primary child exit/log now remains visible instead of being masked
by incomplete-Rig EOF; failure final readbacks preserve exact own job-bound safe
aborted states, while initial/success admission still requires empty.

The successor's separately admitted finite cleanup-only entry actually closed:
only eight direct INFO and A HELLO/own 5,000 ms CLAIM/RELEASE. It cleared the
exact retained aborted job with zero RF/LOAD/ARM/flash/config/profile/cursor
writes. Result SHA-256 is
`d982ab8d2d67f4e9691983ede2e3db4a2db484c3fe87fca957ee0dc057b19799`;
independent raw-control/source/boot/public-settings/current-watermark/empty/
unowned/disabled/RF-off/owned-service/quiet review is
`a27da856fab08db489d9a273e8080e1425ed2faa0d1dfbc08653f8b13ce8bf57`.
Both source/new boots/138 MHz and useful images remain. Public equality is not
a new full-flash byte proof. Cleanup and reviewer are gone; never repeat them.

The failed partial recording remained internal, causing a fresh approximately
1.062 GB deficit against the stricter host reserve. The actual new readiness/
cleanup/shortage bound a distinct four-clock duplicate-only reserve program.
Its selected recursive catalog SHA-256 is
`d8c8b53b0b0f7561867775df685acb99c491851145026d31700262d5218e0712`:
four A150 WSPR raws (30 m/20 m/17 m/15 m), each 312 MB, and 48 recursive
metadata/decoder/audio companions plus clock-closeout controls. The earlier
16-direct-file catalog is unselected; no IQ read/removal occurred from it.
The first staged reserve program's broad private-key phrase check also matched
its own source; it remained unexecuted. A distinct safe-controls successor
uses complete PEM-header checks and fixed source-control inventory.

Actual separate reserve PROGRAM admission passed 17 guards/tiny-owned-file
refusals and full source/durable hashing of all 52 selected pairs/controls:
`d98750bfc6e53c53531b63e9e217f495e8b3eb803b3b9054a9cecaf24cc075a9`.
Actual release removed only those four proved redundant internal raws /
1,248,000,000 bytes after per-file retrieval publication on both filesystems
preceded immediate full hash/stat/user/process/UUID checks and unlink.
Release SHA-256 is
`807b73c891723c2fffce8b2bf9ec60ba923daf4cbbb4e42278c519bdbb5bc944`;
separate independent full durable/raw/recursive-companion/control/retrieval-
order/known-absence/process/service/UUID/reserve post review is
`e5f398e1c5139c336d0be02946c0b0cbeecd01e609b774c8202a2530f52e1744`.
Both release/post-review parents are gone. Every durable recording, nonraw,
original flag, maximum sample and old/new useful image remains. Exactly 31
clock-source absences are known (prior 27 plus these four); do not repeat old
helpers or assume all original sources exist. Restore archived samples internally
and full-hash before reanalysis. No new raw copy or acceptance credit occurred.

Internal free space was 69,613,322,240 bytes at independent closure, above
69,427,613,010 bytes (original 69,185,418,240-byte raw/reference/10 GiB reserve
plus measured companions/32 MiB allowance). All four locks were available;
actual internal/external UUIDs/devices and active service matched. No extra
retention/removal is queued.

The corrected repaired-source mixed qualification was dispatched exactly once
at 19:20 UTC. Exact parent PID 3519766/start 75059297 runs coordinator
`78c491467c3cae2734349af97b91ecc7d0523c8aecb0c8f6214e34f7441d8bdc`;
manifest is
`51b77adecac97dcc429c8e08a338ef134d2c91159999ecd5488d61f81f22ede1`.
Output in the repaired root is
`build/repaired-source-mixed-service-guard-20261012T192001/result.json`.
Actual fresh live admission SHA-256 is
`daa609d0c917453dbc5419523f93b10609fc9bc72c89786be6c19c5d900e772c`:
named A/B clean `2d67224dbddc` / 138 MHz / reviewed UF2 / expected new boots /
public durable settings/current watermarks/default-false flags/empty inactive
unowned disabled/resources/network/GPSDO guards passed before RF. Reference-before completed with return code 0 and balanced AB handoffs.
Acquisition child PID 3519966/start 75067112 and capture PID 3519975/start
75068078 are active for first A 80 m / 138 MHz Tone, 911,250,000 samples /
3,645 seconds, 250,000 samples/s CF32, explicit AGC false and bias-tee false,
internal NVMe only. Capture writes approximately 2 MB/s; the earlier heavy
reads were full copy/hash/reclamation checks, now closed. No raw sample was
transferred to the Mac. Parent holds B/workflow while the child owns A/receiver.
Parent/child identities must be verified fresh before action/report. Only this
coordinator restores its stopped initially active service. Never duplicate,
modify, signal or redirect active inputs or overlap transfer/removal/audit/device
probes with acquisition/analysis. Monitor only the new SSH-stdin live reader.

All eight original one-hour A/B Tone/512-event FSKCW/B-browser jobs, 45-second
idle, one-second INFO spacing, 1,024-byte growth/spread screens, unchanged
science/reference workload and 43,200/36,000/7,200-second bounds remain.
No timeout/threshold/cadence relaxation or later queue. Actual whole eight-job
closure/full raw/control/source/image/boot/resource/browser/human-copy/Tone/
reference/restoration review and exact process closure are required before any
acceptance credit or separately admitted qualifying-memory followup.

Harness: RUNNING; 3 of 9 original workstreams (33.3%) complete; estimated
15–37 hours remaining. Mixed/memory requalification remains open, the prior
active-RF LAN timeout is unisolated, and failures may extend the estimate.
Fixed remaining 37,546 seconds is unchanged; retention/diagnostic/cleanup/
preparation/launch/elapsed time add no capture or workstream credit. Hourly
reports stay active and must verify actual current processes/receipts. Final
push/remote parity/Phase 14 closeout remain unfinished. No native Mac C++ build,
SDK/tool installation, publication or excluded 4 m/2 m work occurred.

## October 12 repaired mixed failure closed; RF-off LAN diagnosis active

This leading checkpoint supersedes the earlier mixed-running snapshot below.
Guarded retention completed and remains independently reviewed: 18 redundant
internal raws / 59,072,000,000 bytes released; all durable samples, companions,
original failures and maximum samples retained. The closed helpers/reservations
must not be repeated. Exactly 27 known clock-source absences include the prior
25 and the two new clock duplicates. No new retention or raw release is admitted.

The repaired-source mixed run stopped during its first A hour job. Exact
parent PID 3495730/start 74484964 and every registered descendant are gone.
The failed result SHA-256 is
`cc3140e1c402ca1f75b7e3cee84189f596326602cb01101dc473d7c0a59d8034`.
Its primary acquisition error is `TimeoutError('Inventory exchange deadline')`
on A's Plain LAN WTP connection `192.168.1.47:31417`, not USB. The failed
STATUS received only a 16-byte header advertising a 363-byte payload before
the unchanged five-second deadline. Preceding Console INFO showed 363 pending
TCP bytes; post-timeout INFO showed 379. This localizes the transaction but
does not isolate the target/network/host cause.

The parent separately reported an unfinished handoff sequence. Its final empty
state assertion also failed because A retained the aborted job
`c0bd4da6ca2ab22d5e88c4025a8d2cbe`. Recorded cleanup/final direct Console bytes
show both boards on clean repaired `2d67224dbddc` / 138 MHz / expected new
boots, both outputs false, owners null, disabled, fault fields zero and selected
network connection/input counts zero. A is aborted; B is empty. Public durable
settings and current watermarks match the pre-run values. Owned service was
restored active. Public equality is not a new full-flash byte proof.

A new metadata-only reader independently checked saved result/log/event/physical
hashes, decoded both actual final Console TX/RX streams, bound the failed header
and cleanup, and verified fresh registered/campaign process closure, all four
locks simultaneously available, both filesystem UUIDs/devices and active
service. Local receipt
`build/phase14-repaired-mixed-failure-pending-aware-readonly-inspection-20261012.json`
has SHA-256
`067155de5e1b9973fd58d3ed4144bc5f25378ca8f6d75930eb1075658274d8d5`.
The earlier metadata reader's incorrect expectation of 363 pending bytes after
the timeout refused with zero device/raw/RF/output; the distinct reader binds
the actual 379 bytes honestly. Host quiet is fresh; these target values are
recorded final readbacks. No original failed flag was rewritten.

Reference-before completed, retaining 64 MB. The first A receiver retained only
1,077,543,936 bytes in `capture.cf32.incomplete`; no complete first hour or later
job exists. That partial recording, controls and raw event bytes remain internal;
no full raw hash or new archive/removal has occurred. Zero jobs or original
workstreams are credited. Fresh internal free space at the reader was
68,370,612,224 bytes, below the new mixed reserve; any later ready stage needs
fresh admission and separately proof-bound redundant-only retention.

A distinct finite RF-off Plain LAN diagnostic passed separate actual program
admission before devices: 48 real-record/refusal/call-inventory checks, all
1,830 source/artifact bindings and pinned dependencies/failure/install proofs.
Admission SHA-256 is
`f668f0a72941aab90fd12be298b73db5a25c20fb1a4b5aecd457a7e4e8822afb`.
Exact parent PID 3505003/start 74717805 is active at this checkpoint, under all
four locks with only its initially active service stopped. Fresh direct Console
live admission preserved the exact A aborted job / B empty state, source, boots,
138 MHz, public settings/current watermarks, default-false flags and RF-off
unowned disabled state. Workload permits only direct INFO (at most 130), one
A Plain LAN HELLO and at most 1,024 sequential STATUS requests, 0.5 seconds
after completed responses, INFO when ten seconds have elapsed, unchanged
five-second WTP deadline. No retry, mutation, RF, receiver, GPSDO, HTTP, flash,
profile/config/cursor write, raw read, transfer or removal is permitted. Operational
bound is 1,200 seconds plus at most 60 seconds of closure; no later queue.
Only this probe restores its owned service. Monitor fresh PID/start/argv and
receipt; never modify, duplicate or signal active work. A separate metadata-only
result review is required after actual closure and exact process exit.

A distinct private mixed child-error/closeout candidate is prepared only. It
records actual child exit/log and partial ownership roles before raising,
preserving full handoff requirements for successful children. Failure final
readbacks are saved before validation; only an exact source/image/boot/board/job-
bound own aborted/unowned/RF-off cleanup can admit that terminal failure state.
It changes no production firmware, science, eight-hour workloads, 45-second idle,
one-second INFO spacing, 1,024-byte limits or 43,200/36,000/7,200-second bounds.
It is unadmitted, unstaged, unexecuted and unqueued. A separate source-bound
finite no-RF CLAIM/RELEASE cleanup could empty the exact own aborted job after
actual diagnostic closure/review, without flash/config/cursor writes; it is not
implemented or admitted at this checkpoint. No RF or qualifying-memory successor
is admitted. Never rerun the closed mixed coordinator/wrapper/reservations.

Harness: RUNNING (RF-off transport diagnostic); 3 of 9 original workstreams
(33.3%) complete; estimated 15–37 hours remaining. Original mixed memory
requalification and the new LAN timeout remain unresolved; diagnosis may extend
the estimate. Fixed remaining work stays 37,546 seconds. No partial, diagnostic,
retention, elapsed or source-preparation acceptance credit. Hourly reports remain
active and must verify current activity afresh. Final push/parity/Phase 14 closeout
remain unfinished; no native Mac C++ build, SDK/tool installation, release
publication or excluded 4 m/2 m work occurred.

## October 12 guarded retention closed; repaired-source mixed running

Guarded retention is complete and independently reviewed. The original failed
853 mixed/reference evidence and all companions remain durable in
`/mnt/phase14-testing/phase14-closed-internal-first/failed-mixed-853-retention-1791816708337667176`.
Copy, separate full source/durable review, separate release program admission,
redundant-only release and separate full post review all actually closed;
every exact registered parent is gone. Their respective SHA-256 receipts are:

- Copy: `28c048f22b3e415006cbb0a3e5ef2a4d7e1c0e0d9d5e4f75c4bef34bed3d34bb`.
- Full retention review: `a50a732d14dbaaf17fdba55499b56e955d245695cd9a48b1c0b14086129f094f`.
- Release program admission: `17bb9ee415f2ffd1382a9e386e29417f0b3975ed9f002a4c13dc65fee330dd66`.
- Actual release: `a690b1c77e67cc612a82e04dc5fb681c58ff07ab84dc4bc7b43a855c2e2af118`.
- Independent post review: `9868c41a05b5f89597ec34a3aa3d5fb382e4ccb4241e1151c1d3dfa0a701426b`.

The copy/full review checked all 105 source/durable pairs / 58,656,640,338
bytes. The 18-guard release admission also freshly verified both additional
clock raw pairs and all 26 companions. Exactly 18 redundant internal raws /
59,072,000,000 bytes were released: 16 failed mixed/reference copies and two
312 MB clock duplicates. Both-filesystem per-file retrieval publication
preceded immediate full source/durable hash/stat/user/UUID rechecks and unlink.
The post reviewer independently full-hashed every removed durable raw, all
companions/controls and retrieval order, verifying only known source absences.
All nonraws, durable samples, original failed flags and retained maximum samples
remain. Prior 25 clock removals are separate; exactly 27 clock-source absences
are now known. Never repeat these closed helpers or reservations. Restore
archived samples internally and full-hash before any later reanalysis.

Post-review internal free space was 69,516,165,120 bytes. Fresh pre-dispatch
free space was 69,516,161,024 bytes, above the stricter 69,427,613,010-byte
host reserve (original raw/reference/10 GiB plus measured companion volume
and 32 MiB allowance). Both actual filesystem UUIDs/devices matched, all four
locks were simultaneously available and service was active. Only five fixed
metadata proof files were mirrored locally, with exact byte/hash/size/private-
key-marker checks: `build/phase14-failed-mixed-retention-release-closed-20261012/`.
No credential file or raw sample was copied to the Mac.

The separately identified repaired-source mixed qualification was actually
dispatched exactly once at 17:44 UTC. Parent PID 3495730/start 74484964 runs
admitted coordinator `e1e07a8a1b2c5b8b44757e5d28494e4dbad534749e5c4a49cee89b9b28456b00`
on installed clean `2d67224dbddc16b320e43c9fce3ccb74f8d102ce` / 138 MHz,
image `6d5ee077e711d008422a0b881f4912e17e7c2fad56abf47c9fc6bcd4ee974787`.
New output is
`build/repaired-source-mixed-20261012T174418/result.json` in the repaired root.
Actual separate live admission SHA-256 is
`dd3d3a53e67440d2880b66259a2c1ba89520c7242a3d044a611100fc27ab4d16`;
named A/B source/new boots/clock/public settings/current watermarks/default-
false flags/empty inactive unowned disabled/input/resource/GPSDO guards passed
before acquisition. Public equality is not a new full-flash byte proof.

At observed_ns 1791827298802549356 the reference-before child had returned 0
and its AB ownership handoffs were balanced. Acquisition child PID
3495930/start 74492792 owns A plus receiver while the parent holds B and the
workflow lock. Exact capture PID 3495938/start 74493758 is active for the
first A 80 m / 138 MHz Tone: 911,250,000 samples / 3,645 seconds, internal
NVMe only, explicit AGC false and bias-tee false. Owned active service was
stopped for qualification; only this coordinator may restore it at closeout.
Do not duplicate, change, stop or redirect active inputs/processes, issue
competing device probes or overlap external retention work with acquisition
or analysis. Monitor only the SSH-stdin private live reader.

All eight original one-hour A/B Tone/512-event FSKCW/B-browser jobs, 45-second
idle windows, one-second INFO spacing, 1,024-byte growth/spread screens,
reference workload and byte-unchanged science remain. Bounds remain 43,200
seconds whole / 36,000 acquisition / 7,200 analysis. Current zero whole-review
observations are not acceptance or capture credit. Whole closure requires
separate independent eight-job/raw/control/source/image/boot/resource/browser/
human-copy/Tone-quality/reference/restoration/process review. Memory followup
remains blocked until that actual whole acceptance and process closure;
no automatic memory chain or new raw release is queued.

Harness: RUNNING; 3 of 9 original workstreams (33.3%) complete; estimated
15–37 hours remaining, with memory requalification pending and possible
extension. Storage, host tests, installation, preparation and elapsed time
add no workstream/capture/acceptance credit. Earlier stopped/partial-retention/
undispatched snapshots below are immutable history. Final push, remote parity
and Phase 14 closeout remain unfinished; no publication, native Mac C++ build,
SDK/tool installation or upper-band RF work occurred.

## October 12 guarded redundant release closed; post review active

The new duplicate-only release actually closed, with result SHA-256
`a690b1c77e67cc612a82e04dc5fb681c58ff07ab84dc4bc7b43a855c2e2af118`.
Exact parent PID 3467127/start 73965462 is gone. It removed only 18 proved
redundant internal raws / 59,072,000,000 bytes: all 16 failed mixed/reference
copies (58,448,000,000 bytes) plus two eligible 312 MB clock duplicates.
Every durable sample, nonraw companion, useful image and original failed flag
remains. Per-file identical retrievals were published on both filesystems
before immediate full source/durable hash/stat/no-active-user/UUID rechecks
and unlink. Source absences are separately recorded; original copy receipts
keep their historical zero-removal flags. Prior 25 clock removals remain
separate; there are now exactly 27 known clock-source absences.

Final measured internal free space was 69,516,210,176 bytes, above the
69,427,613,010-byte dispatch target. This is reserve readiness, not RF
acceptance. No original scientific or acquisition/analysis limit changed.

The actual separate post reviewer is active, PID 3487857/start 74312745,
under all four locks and a 3,600-second bound. Output is new-root
`build/failed-mixed-redundant-release-post-review-20261012/result.json`.
It independently full-hashes every removed durable IQ, all companions and
controls, each both-filesystem retrieval and publication/unlink order,
exactly known source absences, UUIDs, service state and full reserve.
It performs no deletion, device/RF request or transfer. Positive whole post
review and exact process gone remain required before the repaired-source
mixed live/RF admission. Never repeat the closed release, admissions, copy,
full review or reservations; do not change active post-review inputs.

Harness: STOPPED (independent post review running); 3 of 9 original
workstreams (33.3%) complete; estimated 15–37 hours remaining, with
requalification potentially extending the estimate. No new capture or
workstream credit is earned by retention. Earlier partial-release snapshots
below are immutable history, not current source-presence claims.

## October 12 retention copy/full review closed; guarded release active

The actual separate full retention review passed all 105 source/durable
pairs, all 16 IQs and companions, ten copied controls, exact file/stat lists
and identical retrievals. Receipt SHA-256 is
`a50a732d14dbaaf17fdba55499b56e955d245695cd9a48b1c0b14086129f094f`.
Reviewer PID 3457841/start 73780246 is gone; do not repeat the review or copy.

The final new redundant-only program was staged and separately admitted.
Manifest SHA-256 is
`c09b0f86e893b975dfe0d3adc9d9084f0dc9065550404b4ddcc035ddcaf1c3ea`;
release helper `83fe2db93ecc7169ea215143c0ddab14aa5fa5d5432ce243a9e0e8847c20b560`.
Actual program admission
`17bb9ee415f2ffd1382a9e386e29417f0b3975ed9f002a4c13dc65fee330dd66`
passed 18 guards/tiny-owned-fixture cases and freshly full-hashed both
additional eligible clock raw pairs and all 26 companions, excluding the
25 previously removed clock duplicates. Admission PID 3466200/start
73953716 is gone. All earlier release draft bundles remain unexecuted.

Actual release PID 3467127/start 73965462 is active under all four locks,
with a finite 7,200-second bound chosen before program admission from the
observed full-review I/O cost and two required per-file full-pair rechecks.
This changes none of the original RF acquisition/analysis/scientific limits.
Result is new-root
`build/failed-mixed-redundant-release-1791821864373158198/result.json`.
At observed_ns 1791822091829313226, eight redundant reference raws /
128,000,000 bytes had been removed after both-filesystem retrieval publication
and immediate full source/durable hash/stat/no-active-user/UUID checks.
All durable samples, nonraw companions and original failed flags remain.
This partial source state supersedes earlier all-originals-present snapshots.
Never repeat or modify the active helper, admitted inputs or reservations.

Whole release closure, exact parent gone and a separately executed positive
post review remain required before new repaired mixed live/RF admission.
The post reviewer must full-hash every removed durable raw, all companions,
per-file retrieval/order and exactly known source absences, verifying service,
UUIDs and free space above the 69,427,613,010-byte host dispatch target.
No RF job or later stage is queued. Progress remains 3 of 9 (33.3%), estimated
15–37 hours remaining, with requalification potentially extending the range.

## October 12 copy closed and independent full retention review active

The copy actually closed with 105 verified files / 58,656,640,338 bytes and
zero source removals. Actual copy receipt SHA-256 is
`28c048f22b3e415006cbb0a3e5ef2a4d7e1c0e0d9d5e4f75c4bef34bed3d34bb`.
Exact copier PID 3442893/start 73449924 is gone. The external catalog retains
all 16 failed mixed/reference IQs, original flags and all companions, with
identical copy retrieval on both filesystems.

A distinct actual independent full review is active under all four locks,
PID 3457841/start 73780246, bound 7,200 seconds. It rehashes all 105 source
and durable pairs, exact file/stat identities, ten copied controls and
retrievals. Output is new-root
`build/failed-mixed-retention-full-review-20261012/result.json`.
Review progress is not closure or removal permission. Do not repeat or
change either admitted program, its reservations or active inputs.

Only after positive whole review and exact process gone may the new
redundant-only release program be staged and independently admitted.
Its final prepared manifest is
`cb9e3831670ed9c5cddfd1922633e6b34aae432a96b6e1f62a8fcb915c751f25`;
release `84c7ab25be91f527141a5eac2f53b3df04da124a69e35092c25574a201667585`;
post reviewer `0678b3dbc4cb26bc7ca940a823e5916708438db91c8d307d3634c0e06aa23839`.
These remain unexecuted/unadmitted. Actual source/durable clock proof,
per-file retrieval before immediate full rechecks/unlink, separate removed-
durable post review and fresh stricter reserve are still required before
new repaired mixed live/RF admission. Original RF/science limits are unchanged.

Harness: STOPPED (retention full review running); 3 of 9 original
workstreams (33.3%) complete; estimated 15–37 hours remaining, with
requalification potentially extending the estimate. Storage closure adds
no RF qualification credit. Earlier active-copy wording below is history.

## October 12 guarded failed-mixed retention copy active

The operator requested completion of guarded retention followed by repaired-source
mixed qualification with the original limits. A distinct copy-only program is
now active under all four locks, with parent PID 3442893/start 73449924 and a
7,200-second bound. Separate program admission SHA-256
`6fd5602d15c36cf33663f2d395e37f074281b70b26c80ec71d811df1f4e6add8`
passed 24 new catalog/source/alias/hash/tiny-fixture checks, with no actual IQ,
device or RF access. No older completed control/helper was run.

The exact 105-file catalog contains all 16 failed mixed/reference IQs,
58,448,000,000 raw bytes and 58,656,640,338 total bytes, with original expected
hashes, source stat identities and every companion. Catalog SHA-256 is
`6f66bbf25582ca7d7de734857b24df06c6aa252afc8b660ab5bbb77de824fe81`.
Preserve the initial metadata inventory refusal before copy/IQ/reservation: its
small-read limit did not compute hashes for large recorded serial metadata.
The separately identified successor uses their existing immutable f653 hashes;
actual copy and independent review still verify every byte. No original failed
flag, scientific criterion or source/image/job identity is changed.

New copier SHA-256 is
`b58d1451f30194e9424d8c37558ad32b14df8c48b307b1fdf1f8b15aa2d7df53`;
manifest `664dd9add51db7dadc0298f61168cbde3da7139bc2b48fe5dcf4be69a5afdfc4`.
It copies only to a fresh external retention catalog, fsyncs and verifies full
source/durable bytes and unchanged source identities. Every original remains.
Internal result is new-root
`build/failed-mixed-retention-copy-1791816708337667176/result.json`;
external catalog is
`/mnt/phase14-testing/phase14-closed-internal-first/failed-mixed-853-retention-1791816708337667176`.
Dispatch/copy reservations prohibit duplicate launches or blind retries.
Current progress is not whole copy closure or independent acceptance.

After actual copy closure and exact parent gone, a separate already admitted
full reviewer must independently hash all 105 source/durable pairs, exact
file lists/stat tuples, all companions/controls and identical retrievals on
both filesystems. Full reviewer SHA-256 is
`aa66d9763a8ef35b9923ba0bc5eeb4035054a37f34f72072183f796ca717628b`.
No evidence is removed by either program. The following redundant-only release
and its independent post review are separately prepared, unexecuted and
unadmitted. Two still-present eligible 312 MB clock duplicates are identified
from the old full archive proof and all 26 companions, explicitly excluding
all 25 previous removals; they still require fresh full proof before release.
No maximum retained clock job or nonraw file is eligible. Unknown/partial
outcomes require inspection and a distinct state-aware successor.

The original raw/reference/10 GiB minimum remains 69,185,418,240 bytes.
The observed failed-run companion volume is another 208,640,338 bytes; a
32 MiB host allowance gives a stricter dispatch target of 69,427,613,010 bytes.
This keeps room for metadata while preserving the original working margin.
It changes no RF duration, job count, cadence, growth/spread limit, science or
acceptance threshold. The new release program will stop at that target.

No RF stage or later queue is active. Progress remains 3 of 9 original
workstreams (33.3%), estimated 15–37 hours remaining, subject to extension.
Copy/retention/elapsed time adds no qualification acceptance or capture credit.

## October 12 repaired-source mixed program admission closed

A new repaired-source mixed coordinator is implemented and its separate Linux
program admission is actually closed. Program receipt SHA-256 is
`279bde21ec2df3742480f3bb3443840cb9a0cd283658dd01380071a0614cc10b`, in new-root
`build/repaired-source-mixed-program-20261012/program-admission.json`.
The reviewer passed 85 policy/live-record/admission/output refusal cases and
four new relocated-wrapper socket fixtures using fake Rig/science, with zero
device, RF, raw-sample, external-transfer or removal requests. All 1,830
source/artifact catalog files, 27 exact receipts and 68 retained dependency
hashes matched. No completed old helper, control, RF job or admission was run.

New coordinator SHA-256 is
`e1e07a8a1b2c5b8b44757e5d28494e4dbad534749e5c4a49cee89b9b28456b00`;
wrapper `c6dccfff0b71eca057534e3d1ba27df32579b49658669505b36013c69cb45ff4`;
reviewer `3cef0c2f1b79b072f6adfaea297f99836de05b6cf3e9abb1dcb0efdd4b40cd45`;
manifest `1554d658a2183954265170d669b20f4a9094facc6a44ce4fd6e2e4297cf1769c`.
The exact five-file internal staging bundle is 81,920 bytes, SHA-256
`41f01952ea281a511fea1d41207d153325c96f3fccc93bff8f2cc2871f16fb6b`.
Canonical local files and the verbatim admission are in
`build/phase14-repaired-source-mixed-program-20261012/`.

The program retains byte-identical science/reference/analysis commands and
AST-identical peer, ordered handoff, owned-child cleanup and quality checks.
Source review caught the new longer toolroot exceeding the Linux Unix-socket
path limit before execution. Its separately identified private socket now uses
`/tmp/p14-repaired-mixed-<parent-pid>.sock`, with root ownership, mode 0600 and
existing PID/start/UID/request/sequence verification. The new RF entry requires
its exact program admission, source/image/boots, full reference-inclusive
reserve and unique fresh output/reservation before any device access. Its
future live admission uses direct named Console INFO under all four locks,
preserving public durable settings/current watermarks, default-false flags,
empty/inactive/unowned/disabled state, faults and network identity. Public
readback remains distinct from a fresh full-flash byte proof.

All eight original hour jobs, 512-event FSKCW/B-browser load, 45-second idle,
one-second INFO cadence, 1,024-byte growth/spread screens and scientific
criteria remain unchanged. Retained old finite RF evidence keeps its actual
source identities; 4 m/2 m exclusions remain. Actual live admission, RF dispatch,
retention copy/review, redundant-only release and qualifying memory are still
unexecuted/unadmitted; no later queue exists. The closed program review now
establishes ready-stage storage requirements for preparing the separate
retention-only copy/full review of preserved failed mixed evidence.

Fresh quiet receipt `build/phase14-repaired-mixed-program-admission-final-quiet-20261012.json`, SHA-256
`fdc8310c8dce7a9a9a25deca02762c3d10eb0fe287edd47d700f2dfea066d90f`, observed_ns
`1791815244458743757`, confirms the actual reviewer and its four fixture
children gone, every campaign process gone, all four locks simultaneously
available, actual internal/external UUID/device identities and service active.
Internal free is 10,444,759,040 bytes against the unchanged
69,185,418,240-byte full requirement; current planning deficit is
58,740,659,200 bytes. The preserved failed mixed
58.32 GB and 128 MB references remain internal. Copy/release needs its own
reviewed program, complete durable catalog/source/companion proofs and fresh
state checks; no removal follows from this arithmetic.

Progress stays 3 of 9 original workstreams (33.3%), estimated 15–37 hours
remaining. Program/fixture/preparation time earns no acceptance or capture
credit. Repair is installed and scoped idle behavior passed, while the original
memory screen still needs mixed requalification and may extend the estimate.

## October 12 repaired installation and target refusal evidence

Retain the new internal toolroot
`resume-tools-2d67224-http-body-repair-internal-first`, its 1,830-file staging
catalog/source proof, reviewed application artifacts and unique stage/installer
reservations. Source-stage receipt SHA-256 is
`3234720e1e2cf248e73a78a0834edabe22ef5a1a26fed2322cc09bac3112f63b`.
The closed application-only installation under
`build/application-only-repair-install-20261012/` has parent SHA-256
`cf8e7c0dddd6bd0ef3b06354b1d89fd4f289e363306f1facbcc128a7eb2508db`;
adjacent independent installation review SHA-256 is
`a12806c24e630c713ef6c8122c039e723863f63888fb6aa1f0cc9e085a353f15`.
Local `build/phase14-repaired-install-closed-20261012/` preserves actual
program/live admissions, complete serial events, all seven command logs,
source/artifact bindings and the independent review verbatim. No credentials
or RF samples were copied. Both repaired application images are now installed;
older not-installed statements below are historical.

Preserve the new pre-GET IPv4-join refusal at
`build/repaired-image-idle-six-get-validation-20261012/`, parent SHA-256
`27c4a58ab0e0ae26cb7235263b95c4f868b5f5b4189a5eaa8fdfb5884fe9db12`,
and the distinct two-GET TCP timeout at
`build/repaired-image-idle-six-get-address-aware-20261012/`, parent SHA-256
`ec69002d2ed61193804179a299c853bb95c1a8b007caa17e824206f200de6984`.
Their canonical small mirrors are
`build/phase14-repaired-six-get-pretraffic-refusal-closed-20261012/` and
`build/phase14-repaired-address-aware-refusal-closed-20261012/`.
Retain source plans/manifests, actual admissions, original INFO RX/TX, completed
response hashes/lengths/parsed values and the actual failure logs. The separate
metadata-only failure review SHA-256 is
`d5e58cf26404af9e6f50f7ca9c483baa02a6db235c563d2038793f1c77dee323`.
Its initial missing-success-field reader refusal is preserved separately; no
device request or original evidence rewrite occurred during either review.

Never repeat these completed workflows or reservations. Any remaining-path
validation must reuse the two completed GETs, preserve the failed TCP attempt
and ownership gap, and obtain its own finite program/live admission and result
review. That distinct remaining-path stage is now closed and independently
reviewed. Keep new-root `build/repaired-image-remaining-four-get-validation-20261012/`
and its unique reservation, with parent SHA-256
`06b82e3095cd12041b01c9559d60474532379337c747204f6d4a931066c981d5`.
Its adjacent independent split-result review SHA-256 is
`f8fbf96f455d1489060b6b5b25a58efc0736d56daf5d732e29c59441b9445cd3`.
Canonical local `build/phase14-repaired-four-get-closed-20261012/` contains
explicitly named public evidence files and logs; credential files, raw samples
and generated Python caches are excluded. Preserve the refused directory-wide
export; the completed export instead used a fixed evidence-file allowlist,
hash/size checks and private-key marker refusal. No original file was rewritten.

Fresh quiet proof
`build/phase14-repaired-install-and-split-validation-final-quiet-20261012.json`,
SHA-256 `0c848718b4b1f9e2e8c2da81ead547351c48c17112131fe67ddef599f26b9ce6`,
records all campaign and exact registered processes gone, four locks available,
actual UUID/device identities, active service and zero new device/raw requests.
Do not repeat the completed remaining-path program, traffic, review or reservation.
No original mixed raw or companion was transferred or removed. All
58.32 GB plus 128 MB references remain internal under the old853 root, with
immutable failed flags. The earlier 25 redundant clock removals and durable
retrieval proofs remain unchanged; no new raw release is admitted.

## October 12 response-body repair controls

Retain the distinct repair validation directory on internal wspr5 storage:
`resume-tools-8538564-clean-internal-first/build/response-body-repair-host-validation-20261012`.
Its actual parent receipt SHA-256 is
`a367788c516ecf882af7a64913692487e07048217cc85700bee55d1a509467ab`.
The source bundle SHA-256 is
`dc96802b81a47ff74a04e7eadafeb0d7f9b5fb349b214deff1a11da363154021`;
the unique reservation and coordinator identity prohibit blindly repeating
this completed build, tests or negative control. Preserve the source snapshot,
rebuilt core, binaries, commands and all step logs, including the expected
old-assignment assertion failure. No production or historical evidence was
rewritten by that control.

Small canonical receipt/log copies are retained locally in
`build/phase14-response-body-repair-host-closed-20261012/`. Offline hash/source
verification is
`build/phase14-response-body-repair-host-offline-review-20261012.json`, SHA-256
`e6f609c2528a337599209baf1a882ba158fa583d529233024a30fc42dc2002ea`.
There were zero device/raw reads, RF jobs, external transfers or removals.
Useful old images and every mixed failure raw/companion remain intact. The
source repair has host evidence only; no repaired firmware is installed yet.

Retain the completed Arm candidate/rebuild directory
`build/phase14-http-body-repair-arm-process-access-20261012/`, its unique
reservation, build source identity, immutable ELF/UF2 files and four command
logs. Build receipt SHA-256 is
`33a20e76b07234663c66dccd61400d30048fa913b4fd2135fbe21b04bea09cd7`;
independent review
`build/phase14-response-body-repair-arm-independent-artifact-review-20261012.json`
has SHA-256
`8579cff2fd4055860c737201064ccf56a59709b529d982792e8d66a919d2656f`.
Both candidate and independent rebuild share UF2 SHA-256
`6d5ee077e711d008422a0b881f4912e17e7c2fad56abf47c9fc6bcd4ee974787`.
Keep the clean repair worktree at exact source
`2d67224dbddc16b320e43c9fce3ccb74f8d102ce` and the old clean853 worktree.
Preserve both preceding build refusals and the first empty output/reservation;
do not repeat either closed builder or completed checks as-is.

Final quiet receipt `build/phase14-response-body-repair-final-quiet-20261012.json`
has SHA-256
`9f8bbb336bb0499fdab98d058e8a1690a1724243df35a998d7321e26c1b0d6ff`.
It supplies process/lock/filesystem/service state only, with no device request or
new source-image installation claim. Raw evidence, external retention and the
25 historical redundant-clock removals are unchanged.

## October 12 failed mixed stage retained intact

The amended mixed workflow and every child are now gone. All eight acquisitions
and both reference batches completed; the completed assessment rejected B's
1,384-byte Tone and 1,704-byte FSKCW equivalent idle growth against the unchanged
1,024-byte screen. The parent failed with evidence preserved and restored its
owned service. No memory stage, archive transfer, raw release or later queue
was dispatched.

All eight mixed raws/58.32 GB and the eight reference raws/128 MB remain at
their original internal paths under clean-root
`build/amended-clean-mixed-20261011T193513`, with all metadata, INFO events,
browser responses, analyses, idle windows, failure logs and closeout controls.
The parent receipt SHA-256 is
`3b0a10cd3687a629473dc61640cac223faa3146f626d4b46b69b52b615e31a32`;
the completed assessment SHA-256 is
`7d538fee857bbdb7b87ac637922bc4a874b25e35d0bc42e61f0985063a61d9e9`.
The metadata-only independent failure reconciliation is retained locally as
`build/phase14-mixed-resource-failure-independent-review-20261012.json` and
identically at clean-root `build/mixed-resource-failure-review-20261012T0610/result.json`,
SHA-256 `f6531bb570f4324fd6318f19893256d58c7ac1c6b283f06327459408add7e8f7`.
It hashes nonraw companions and independently recomputes the failing resource
screen, while reusing completed science raw hashes with current stat checks.
It performs no new raw read, RF test, device request, external transfer or
sample removal and supplies no full-raw or whole RF acceptance.

This closed failure adds no capture or transfer credit. The earlier 25-file
duplicate-only release and its durable retrieval proofs remain unchanged.
Any future archive or duplicate release still requires a separately identified
state-aware workflow and the established full verification/retrieval rules;
no only-copy sample or nonraw companion may be removed. The active-run wording
below records earlier snapshots, not the current closed state.

The distinct six-GET idle B path contrast is also closed and independently
reviewed. Clean-root `build/idle-browser-path-contrast-20261012` and its adjacent unique
reservation retain the original plan, program/live admissions, source manifest,
Console TX/RX/event bytes, actual response hashes/lengths/parsed values, all
26 INFO samples, timing groups and parent closeout. Local
`build/phase14-idle-browser-path-contrast-closed-20261012` mirrors the small
closed evidence verbatim; no RF samples or private credentials were copied.
Parent SHA-256 is
`254bbe284a50f46f095789dcf6def69994f12a6a5d7d80aee125953a710220c1`;
its separate metadata-only independent review SHA-256 is
`75b235fac04cf28ebb9191003e4d548d73e239a6b15bfcc2c48695c46db5c018`.
Final quiet proof
`build/phase14-idle-browser-path-contrast-final-quiet-20261012.json`, SHA-256
`9eac8b037003ffa6b40cfa40472216624e88884a33ac698bf9405c6afd068f5d`,
verifies exact processes gone, all four locks available, actual UUIDs and active
service with no new device request. The reversible 2,552-byte idle endpoint
heap effect earns no acceptance, capture, transfer or elapsed-time credit.
Never repeat this workflow, admission, traffic or completed review. The private
unselected body-release patch and source comparison are preparation only;
production source, useful images and all failed mixed evidence remain intact.
No target successor, raw release or automatic qualifying memory stage is admitted.

The separate October 12 [causal plan](phase14-memory-causal-plan.md) retains a
new metadata-only eight-window counter comparison and closed Linux-only WTP
lifetime experiment. Internal clean-root `build/wtp-lifetime-host-20261012`
preserves the completed host build and initial admission refusal;
`build/wtp-lifetime-host-admission-recovery-20261012` preserves corrected
admission, unchanged-binary reuse, verbatim probe log, original plan snapshot,
source manifest and full coordinator closeout. Their unique reservations must
not be repeated. Local receipts
`build/phase14-wtp-lifetime-host-first-refusal-20261012.json`,
`build/phase14-wtp-lifetime-host-admission-20261012.json`,
`build/phase14-wtp-lifetime-host-result-20261012.json` and
`build/phase14-wtp-lifetime-host-result-review-20261012.json` preserve the
refusal and scoped host findings. No target cause, acceptance, capture/transfer
credit, firmware change, external archive or raw removal follows from them.
All failed mixed samples and original companions remain intact.

The subsequent portable HTTP experiment is also closed. Clean-root
`build/http-lifetime-host-20261012` retains the original build and failed
fixture admission; `build/http-controls-localization-20261012` retains the
distinct bounded assertion localization and its admission;
`build/http-lifetime-capacity-aware-host-20261012` retains the capacity-aware
successor, immutable-library binding, separate admission, source manifest,
verbatim 1,600-GET log and complete closeout. All unique reservations prohibit
blind repetition. The first failed parent SHA-256 is
`9cc4b4e46ab3cdad637d04a769f840b9d60630e21c14e055b2503f0365df7a8b`;
the completed successor SHA-256 is
`9c731733b978b0bbb36a2f9d756ea9f04e3c13d85573deb0d40948eafacdd568`.
Verbatim local receipts use the `phase14-http-lifetime-*` and
`phase14-http-controls-localization-*` names in private `build/`.
The separate offline result review is
`build/phase14-http-lifetime-host-result-review-20261012.json`, SHA-256
`cf4ad02dc33f2990d2d8712b5387af539f71d9c34f3f018b8c29429140b95878`.
Fresh metadata-only closure is `build/phase14-http-causal-final-quiet-20261012.json`,
SHA-256 `d03f79d487060d701f2e8e737a11f1981293d3dc86e1c536e60432c80d66972e`.
It verifies exact host processes gone, all four locks available, actual internal
and external filesystem identities and service active. No new raw read,
external transfer, removal, firmware change or qualification credit occurred.
The target resource failure and blocked memory follow-up remain unchanged.

The distinct twelve-GET attribution is retained at clean-root
`build/http-response-capacity-attribution-20261012`, including its pinned-library
build, new source/plan/manifest, separate admission, verbatim log, full closeout
and unique reservation. It must not be repeated. The actual parent SHA-256 is
`89ec7137e28ca2793663f4aa07f9c24892d559ee9865ea809538d7dac7ec8df8`;
the admission SHA-256 is
`75ac63cdda4eb8033c48ea4ced6fdc358d0c90957fe4076b7141d825ba6ab40a`.
Local private `phase14-http-response-capacity-attribution-*` receipts preserve
the same result, admission and log bytes. The separate offline review SHA-256 is
`859d62c488b6ce7bd4483284637a114cdc385264a01aa09a482045a0bcf72435`.
Metadata-only inspection of recorded B browser response selections is
`build/phase14-browser-last-response-inspection-20261012.json`, SHA-256
`aabb9eeb1e42e31fbbb0889397829a7653b0a761683b7614a9babcccc135ede4`.
Original physical/body hashes and parsed values remain unchanged; no original
HTTP body is replaced by a JSON reserialization.

Fresh closure `build/phase14-http-attribution-final-quiet-20261012.json`, SHA-256
`7982f977604af18dbb36dad9265fba6b548138f9d4709ea8df7d700507b40147`,
verifies exact attribution processes gone, all four locks available, filesystem
identities and service active. There was no device, RF, new HTTP, IQ, external
transfer or raw removal in the metadata inspection. Host attribution supplies
no target acceptance or new capture/transfer credit. The next target path
contrast is a separately prepared, unimplemented plan only.

## October 11 closed reserve release and active mixed acquisition

The full independent source/destination verification completed for all 2,014
closed clock/Tone pairs, 41,826,678,767 bytes and 253 raw pairs. Its immutable
receipt is `build/phase14-clock-reserve-full-audit-complete-20261011.json`,
SHA-256 `2d27bb6f2fb9bf2e77a50f47008d182f5eb3c1c7a1ae49949093b4d88baff06d`.
Its identical durable retrieval is
`/mnt/phase14-testing/phase14-closed-internal-first/reserve-verification-1791744416866697703/retrieval.json`.

The separately recorded duplicate-only release removed exactly 24 eligible
internal clock raws/7.590 GB, receipt
`build/phase14-clock-reserve-owned-release-result-20261011.json`, SHA-256
`f53b01f2f04bae5e7aad028ca3f609c04206e35d2cc733a962de56534ce69668`.
Its durable retrieval is
`/mnt/phase14-testing/phase14-closed-internal-first/reserve-release-1791746425065388223/retrieval.json`.
Every sample remains in the original clock archive, with its full source and
destination proof, unchanged source identity before unlink, independently
published per-file retrieval on both filesystems and immediate final full
hash/stat/user checks. The independent post-release review full-hashed all
24 destinations/7.590 GB and 1,758 distinct small companion pairs; it reused the exact
unchanged identities of the remaining 229 raw pairs. Its receipt
`build/phase14-clock-reserve-release-independent-post-review-20261011.json`
has SHA-256 `decbfa28da4889a045f2dca430f5522fa0066ee646501257de15f51acd958aaa`.

The unchanged before/after GPSDO references require another 128 MB of raw
storage. A separate state-aware correction, bound to the accepted 24-file
review, released only one additional 312 MB internal duplicate. The original
release was never repeated. The correction receipt is
`build/phase14-clock-reference-reserve-delta-result-20261011.json`, SHA-256
`0113ba95ef30c44a70d08276bcd34183babf066afb56f7ace5753c5d2732a38c`;
its durable retrieval is
`/mnt/phase14-testing/phase14-closed-internal-first/reserve-release-1791747120324807917/retrieval.json`.
An independent final check full-hashed the new destination, reused the accepted
24-file proof, verified retrieval ordering and retained both releases' complete
closeout controls. The final review SHA-256 is
`4d4dff0dca9e616a6e9fd92e8532f7fa31a11576c4533f326058cf54da5541a8`,
identical in the clean internal root and the correction archive as
`independent-final-reserve-review.json`.

Cumulatively, 25 internal duplicates/7.902 GB were removed. No only-copy sample,
nonraw companion, retained A132 max raw or Tone/reference raw was removed.
The old copy-only zero-removal flags remain immutable historical records; the
separate release receipts identify the actual later source absence. Restore
archived samples to their recorded internal paths and full-hash before reanalysis.
Never rerun helpers that assume all original sources exist; any later release
requires a new ready-stage shortage and state-aware verification.

The actual mixed dispatch rechecked internal/external UUIDs and all four locks,
then 69,384,732,672 bytes free against the complete 69,185,418,240-byte requirement
(58.32 GB mixed raw + 128 MB reference raw + 10 GiB). Coordinator
3233082/start 66510419 is active at clean-root
`build/amended-clean-mixed-20261011T193513/result.json`. No further archive,
raw release or audit may overlap its acquisition/analysis. Memory remains
a separate stage after actual independently accepted eight-job results and
gone processes. Verification and duplicate removal add no capture or transfer
credit and close no original qualification workstream.

The earlier wrong self-hash command argument refused before devices, raw reads,
output or reservation; its corrected probe and original refusal are retained
in `build/phase14-release-self-hash-argument-refusal-20261011.json`. Prepared
`7373e15d`, `151e06bd` and `eceb7c54` entries were never executed on campaign
evidence; their distinct successors and actual receipts supply the evidence above.

## October 11 earlier reserve audit snapshot

The actual ready-stage review demonstrated approximately 7.6 GB of additional
space needed for the eight mixed captures plus the 10 GiB reserve. The new
verifier, helper SHA-256
`0a9e1d49a1206993b7b2defd18585603cf7db664668b0eec2217afa419b91e2d`,
was dispatched exactly once with `--verify` and removes zero files. Its private
receipt is `build/clock-reserve-full-audit-20261011T184656/result.json` under
the clean internal root below. It full-hashes both unchanged sources and durable
destinations for the closed clock and Tone catalogs: 2,014 pairs totaling
41,826,678,767 bytes, including all companion logs and all 253 raw pairs.
All four locks exclude acquisition, analysis and other archival workflows.
This audit is a new mandatory prerequisite for duplicate release, not a repeat
of accepted RF work. Existing copy/audit receipts and every source remain intact.

The release candidate derives its 218 eligible clock raws from the actual
original full clock audit. The copy-only catalog's zero release count stays
zero, and its 49 empty decoder stderr companions remain empty and retained.
Both initial reader refusals, with zero raw reads, removals or reservations,
are preserved in the private preparation receipts.

The running verifier and its inputs must remain unchanged. Its release entry
is superseded because the mixed coordinator received an additional closeout
guard repair. Once the verification is complete and all processes are gone,
independently review that coordinator successor, then bind a separately
identified release-only helper to the actual completed full audit and current
ready-stage review. Publish retrieval on both filesystems before each unlink,
full-hash the unchanged source and destination immediately, check exact file
identities and active users, remove only redundant internal raw and stop when
the reserve is met. Keep the retained A132 maximum raw, all nonraw companions,
profiles and current cursors. No release or mixed stage is queued.

## October 11 clean candidate staging

The new clean source/tool root is
`/home/pi/phase14-qualification-20261008/build/resume-tools-8538564-clean-internal-first`.
It is on the existing internal NVMe, UUID
`ed6c7f1b-238b-41a1-b4b6-7bcdef3270fe`, device 66306. The 1,825 source/artifact
files and qualified imports were verified; staging receipt SHA-256 is
`4fecf34cd093851a418e4f055224f49f2fd6f1714fd6ff158ebe7dabe42d0358`.
The fresh root retains clean 132/138/150 MHz candidates and the independent
138 MHz rebuild proof. Existing e953 and first 853 staging roots remain
unchanged, including the earlier dirty-identity installation failure.

Current profile/configuration/cursor ROM snapshots for the unarmed admission
checks remain private on wspr5. They contain credentials and are not copied
to the Mac or committed. Small public source/control/result/review receipts
are retained locally. Both installation and B flag checks preserved the current
8 KiB cursor; the B flag experiment independently verified profile bytes and
restored the original configuration. A's refused consumer Console request
left its full 32 KiB region byte-identical.

The four new-image 80 m baselines closed on this internal root with
SDRplay bias-T disabled. All 824 MB of complete raw samples remain internal,
independently full-hashed with their immutable control/decoder companions. They do not start a later queue or permit raw release.
Existing independently verified clock and Tone external archives remain
unchanged, with every internal original retained. Any future reserve release
still requires actual ready-stage shortage, a separately identified state-aware
helper, full source/destination/companion verification and published retrieval
before immediately rechecking each redundant raw file for unlink.

## Storage placement

- Keep new bulk captures on wspr5. Do not copy additional raw recordings to
  the Mac or use the other Pis as routine bulk capture archives.
- Keep source, selected firmware artifacts, hashes, small status/analysis
  summaries and retrieval receipts on the Mac. Remove rebuildable intermediates
  after the relevant build closes; retain source, pinned inputs and final UF2/
  ELF artifacts.
- The fixed four-recording archive on wspr4/wspr2 has completed independent
  destination and unchanged-source verification. Retain all original source
  recordings and every earlier failed-copy receipt. Do not start another
  routine archive transfer.
- The operator subsequently added a 1 TB external SSD to wspr5, then clarified
  that live captures must use the faster internal SSD. Record on wspr5's
  internal NVMe and transfer closed recordings to the external SSD. The previously prepared
  four-file source relocation is no longer needed to make space for the next
  batch; retain those original recordings. Further storage savings, when needed,
  come from verified lossless compaction on wspr5.

## October 10 external SSD

The operator authorized erasing and repartitioning the newly attached USB
WD Black SN770 1 TB, serial `012345678906`, size `1000204886016` bytes.
Its stable device link is
`/dev/disk/by-id/usb-WD_BLACK_SN770_1TB_012345678906-0:0`.
The external disk now has one GPT Linux data partition, formatted as ext4
with label `phase14-testing` and UUID
`d9df35dd-f27b-45e0-9dff-c74e1bbfabe6`.

The filesystem mounts at `/mnt/phase14-testing`. The future tool root's build
directory,
`/home/pi/phase14-qualification-20261008/build/resume-tools-1024529/build`,
is a bind mount of
`/mnt/phase14-testing/phase14-qualification-20261008/resume-tools-1024529/build`.
This preserves the existing capture paths while storing new bulk bytes on the
external SSD. Its existing tool-source verification record was copied and
independently matched before mounting; the internal copy is retained.

The UUID and bind mount are saved in `/etc/fstab`, with the original file
backed up as `/etc/fstab.phase14-ssd-20261010.bak`. Both entries passed a real
unmount/remount through fstab, and their generated systemd mount units reached
`active/mounted`. A flushed 4 MiB write/read hash check passed through the
actual future capture directory. Available space was about 927.30 GiB.
The system remains booted from `/dev/nvme0n1p2`.

### Internal recording amendment

The initial storage setup bound the future tool root's build directory directly
to the external SSD. The operator subsequently rejected direct external writes
during acquisition because the external disk is slower. That acquisition route
is superseded; its existing mount and evidence remain intact.

New live acquisition uses the separate tool root
`/home/pi/phase14-qualification-20261008/build/resume-tools-1024529-internal-first`.
Its `build` directory resolves to `/dev/nvme0n1p2`, UUID
`ed6c7f1b-238b-41a1-b4b6-7bcdef3270fe`, filesystem device 66306, distinct
from the external device 2049. All 1,812 pinned tool-source files and the three
ordinary firmware candidates were copied and independently hash-verified.
A flushed 4 MiB write/read check passed, with about 117.90 GiB free.
No firmware, sample format, rate, duration or acceptance rule changed.

Use the external SSD for completed evidence at
`/mnt/phase14-testing/phase14-closed-internal-first`. Copy only after acquisition
and analysis have closed and their exact processes have ended. Do not overlap
the external transfer with a live capture. Independently hash the full destination
and unchanged source, retain every metadata/control/decoder/analysis record,
and publish durable retrieval locations. Free internal space only after those
checks by removing a redundant representation; never remove the only retained
sample bytes. Maintain enough internal reserve for the next finite stage and
one largest recording, and restore archived recordings to internal storage
before reanalysis when necessary.

The former external-acquisition clock, Tone and reliability wrappers are
superseded and must not be invoked for new recordings. The old clock campaign
ended independently with preserved failure evidence before this change.
Its historical external files remain untouched. Small preparation receipts are
`build/phase14-internal-workspace-preparation-20261010.json` locally and
`build/internal-workspace.json` under the new host root.

### October 11 upper-band exclusion and diagnostic retention

The latest operator amendment excludes 4 m and 2 m for all five modes after
failed required WSPR decoding without synthesis-preventing faults. See
[phase14-band-support.json](phase14-band-support.json). Preserve every original
successful/failed capture, metadata, control, decoder, analysis and flag; this
support decision removes no evidence and changes no historical result.

Four separate synthetic audio controls have closed, with steady-carrier decodes
and negative observed-trajectory controls at both bands. Their actual result is
retained internally at
`build/synthetic-carrier-controls-20261011T1521/result.json` under the current
tool root, SHA-256
`9447089103621853a3638aeba7e7032fdbd91336bcb8bdd4123eeb2de57608ba`.
Keep all four synthetic WAV/stdout/stderr files and the original small-file/
raw-identity bindings. The byte-identical independent review is
`build/upper-band-synthetic-independent-review-20261011T1534.json`, SHA-256
`59463f0c9a1fff724d0cc5512807791f76d1511b1c5f71e3fe39b54889bdb1e4`.
No retained IQ/audio was edited or copied to the Mac, no new RF ran, and no
qualification/capture credit follows. Do not repeat these decoder controls.

The native nineteen-job archive remains unexecuted and unqueued. Its new
preparation encountered a zero-ended-time guard refusal before copying; retain
that refusal and correct/review a separately identified successor before any
copy. No source bytes were removed. Clock/Tone archive credits remain unchanged.

The former positive 4 m prerequisite is superseded by the operator exclusion.
Mixed reliability still requires reviewed amended admission and enough internal
reserve before launch. Any redundant raw release needs its own guarded helper,
actual next-stage shortage, independent durable/source/companion verification
and retrieval publication; no release is currently armed. The checkpoint below
records the earlier support boundary and is preserved as history.

### October 11 14:28 UTC closed Tone and reference archive

The accepted post-clock Tone archive and its independent full review are
closed. All acquisition, analysis, decoder and audit predecessors had ended
before copying. Workflow and all three bench locks covered the copy; actual
internal/external UUIDs and distinct devices 66306/2049 were checked. No
external transfer overlapped acquisition or analysis.

The durable location is
`/mnt/phase14-testing/phase14-closed-internal-first/post-tone-rc3-1791728421022595521`.
It contains 288 evidence files/2,739,943,875 bytes, including 26 accepted Tone
raws/2,600,000,000 bytes and eight closed GPSDO reference raws/128,000,000 bytes.
Metadata, control, decoder, analysis, close-in, original flags, source and
audit companions are retained. The previous clock copy's full closeout
controls and this copy's own full closeout controls are also durable.
The successful local receipt is
`build/phase14-closed-tone-copy-result-20261011.json`, SHA-256
`b4f46fe8689731f9dcffe5f9301575ac447e454d11d71885dbb2ca6a2cc3b00d`;
the archive's `retrieval-1791728421022595521.json` has identical bytes.

The copier independently verified full destination and unchanged source
contents and flushed the archive. A separate review then full-hashed every
source/destination evidence pair, verified retrieval and companion bindings,
recorded exact identities for all 34 raw pairs, and checked live restored
boards/settings/current cursors/GPSDO. Its local receipt is
`build/phase14-closed-tone-copy-independent-review-20261011.json`, SHA-256
`77b7340d1052af48ec0ad86d1bd74211751c95d648a7a53168663c6130f9a6a3`;
identical review bytes are retained internally and in the archive.

The earlier catalog refusal omitted eight reference companion raws and is
preserved; it stopped before samples, devices, copy or reservation. The
corrected copy includes those exact closed companions. Thirty-nine Linux
refusal checks passed before the actual copy. Preparation alone supplied no
archive proof; the closed copy and independent review supply that proof now.
Neither copy nor review may be repeated. All internal originals remain, with
zero bytes removed and no release entry.

The independently verified Tone transfer credits 2.6 GB once, leaving 72.9 GB
of unrecorded core transfer. The 128 MB reference retention remains inside the
existing other-work allowance and adds no capture credit. The separately
closed A carrier-search diagnostic remains negative and changes no original
acceptance flag. Final process/four-lock/UUID checks found no active campaign
or later queue, with about 58.584 GiB internal free. Mixed reliability remains
blocked by 4 m acceptance and requires more reserve; do not release raws now.
Any later redundant release still requires its own guarded, state-aware
operation, full durable verification and retrieval records before each unlink.

### October 11 13:27 UTC closed comparison and independent audit

The B-only continuation and all acquisition/analysis processes have ended.
Both normal-connection comparison frames retain their actual false expected
decodes, passing resources and zero receiver overflow/clipping. The independent
auditor has also ended after full-hashing only B's new 312,000,000 bytes and
reusing A's completed 312,000,000-byte independent audit with unchanged exact
source identities. Its receipt is
`build/phase14-action-prefix-independent-closed-audit-20261011.json`, SHA-256
`650c20dd93ecbdd22b4856afb7864a9238e031577fab3071cda829e9c0b7b90e`.
All raw/control/metadata/analysis/decoder/audio and original failed records
remain on internal NVMe; no raw was removed or transferred during this work.

Fresh process and four-lock closure checks passed with the actual internal
and external UUIDs and devices 66306/2049. The comparison adds 624 MB once to
pending finite retention, now 19.288 GB within the existing allowance. Its
full integrity audit creates no 4 m acceptance, capture credit or raw-removal
authority. Preserve the separate original failed reader, A audit, continuation
and whole audit; none may be blindly rerun. Any later archive still requires
its own guarded closed-evidence catalog, full durable-copy/source verification
and retrieval records. The verified 38.720 GB clock transfer credit and every
internal original remain unchanged. Mixed reliability remains blocked by
4 m acceptance; no long queue or raw-release operation is armed.

### October 11 13:11 UTC retained A and active B-only comparison

The original connection-action comparison is closed with its host INFO-prefix
reader failure preserved. A's acquisition and analysis completed; B had not
started. Its original zero-observation/error receipt remains unchanged. A's
separate independent audit full-hashed 312,000,000 unchanged bytes and bound
the original control, metadata, decoder/audio/stdout, resource and receiver
records. The audit process ended, and its receipt is
`build/phase14-action-a-prefix-independent-audit-20261011.json`, SHA-256
`b0094111e10601e62f91c40331e5d9bf9aaf85c8c509cc2655a1479cc080b520`.
The actual expected decode remains false. Preserve all original records;
this audit authorizes integrity reuse without mode acceptance or raw removal.

A separately identified continuation is active exactly once as
PID 3123957/start ticks 64186195, helper `a097f0b0`. It retains A's full audit
and acquires only the missing B recording/312 MB on internal NVMe. At the
13:11 UTC snapshot B is in its minimum 350-second idle period, and no new
observation has closed. All four locks, actual UUIDs and distinct devices
66306/2049 were checked at the preceding quiet boundary. No archive transfer
or source removal may overlap this acquisition or analysis.

The additional closed A recording adds 312 MB once to finite retention,
now 18.976 GB within the existing allowance. Add B's new 312 MB only after
its actual capture closes. A later independent recovered-comparison audit
is prepared but unqueued; it reuses unchanged A full-hash identities and
independently hashes only the new B recording after actual whole closure
and process termination. Neither integrity closure nor a diagnostic contrast
permits automatic 4 m acceptance or redundant raw removal. The verified clock
archive, its 38.720 GB transfer credit and every internal original remain
unchanged. Mixed reliability is still blocked by 4 m acceptance.

### October 11 12:49 UTC verified closed-clock archive

The copy-only `7b0e63a0` operation is now `INDEPENDENT_CLOSED_CLOCK_COPY_VERIFIED`.
Exact PID 3103666/start ticks 63759990 and its verification process have ended.
All 219 closed clock raws/38.720 GB and required companions, 1,726 files and
39,086,734,892 total bytes, have full independent destination and unchanged-source
hash verification and durable retrieval. The archive location is
`/mnt/phase14-testing/phase14-closed-internal-first/clock-rc3-1791719809192454023`.
Its `retrieval-1791719809192454023.json` is byte-identical to the terminal status,
SHA-256 `44efa33e035f255ac928afebc9e635ce41dc25fd31a1bd949b0dc17ee4bdf132`.
All internal sources remain; removals are zero.

The separate actual closure review is
`build/phase14-clock-copy-independent-closure-review-v3-20261011T1245.json`.
It reuses the completed raw hashes with unchanged exact source identities,
independently rehashes the 1,507 small companions/366,734,892 bytes, and validates
the actual compact inventory through stored full INFO/WTP control records.
Preserve its earlier inventory-wrapper and STATUS-field parser refusals. They
changed no archive, raw or original result. The copy's own full closeout-control
files remain retained internally and must accompany any later durable catalog
before redundant raw release.

The 38.720 GB closed core transfer is now credited once; pending core transfer
is 75.5 GB, including unrecorded mixed/memory captures and closed post-clock Tone.
No raw release is armed. Future release still requires a separately guarded,
state-aware operation, demonstrated reserve shortage, durable retrieval and
full independent archive/source/companion checks before each eligible unlink.
Mixed reliability remains blocked by 4 m acceptance.

After actual copy closure and fresh quiet checks, the bounded two-slot
connection-action comparison was dispatched once on internal NVMe as
PID 3117468/start ticks 64055343. No external transfer or source removal may
overlap its acquisition or analysis. Original failed settling recordings and
their independent audit remain unchanged; no automatic later queue exists.

### October 11 12:18 UTC closed-clock copy checkpoint

The copy-only `7b0e63a0` helper is now executing once, after the two-slot idle
diagnostic and its independent 624 MB audit closed and all acquisition/analysis
processes ended. Exact coordinator PID 3103666/start ticks 63759990 holds
workflow and all three bench locks. It copies the 219 closed clock raw files,
38.720 GB, and their original control/metadata/decoder/analysis/source/audit/
retune/review companions to
`/mnt/phase14-testing/phase14-closed-internal-first/clock-rc3-1791719809192454023`.
Both filesystems were verified as the recorded internal/external UUIDs and
distinct devices 66306/2049. Every internal original remains; the helper has no
raw-release entry.

The small checkpoint
`build/phase14-clock-companion-copy-live-20261011T1218.json`, SHA-256
`89068a4f928bdcb6dbe5afc46dc88749a694d9fdc2d1fafef1ba33d7e310f198`,
records 192 independently verified partial entries/33.468 GB, no errors and
zero removals. Whole-archive verification and durable retrieval publication
remain pending. Do not duplicate the copy or credit partial bytes as a closed
archive. No RF capture or analysis overlaps this transfer. The two failed idle
diagnostic recordings add 624 MB to pending finite retention within the existing
allowance; neither their complete raw audit nor their failed decode results
authorize sample removal or qualification acceptance.

Any subsequent RF stage requires this copy's actual successful terminal and
retrieval hashes, ended process and fresh ownership/storage checks. A future
redundant raw release still needs a separately identified guarded operation,
independent durable-copy checks and a demonstrated next-stage reserve shortage.
The mixed stage remains blocked by 4 m acceptance; no source removal or later
queue is armed.

### RC3 closed-clock companion preparation at 11:25 UTC

The current RC3 root is
`/home/pi/phase14-qualification-20261008/build/resume-tools-e95334a-internal-first`.
Its closed clock evidence includes 218 new recordings/38.374 GB and the
separately retained new A132 max-contention recording/346 MB. The latter was
omitted from the preceding transfer estimate; pending closed-clock raw is
38.720 GB. Including closed post-clock Tone and unrecorded mixed/memory raw,
pending core transfer is 114.220 GB. This corrects retention accounting without
adding capture credit or claiming any completed copy.

The original unexecuted `d54a18f6` copy helper omits the separately accepted
receiver-retune/review companions and retained max-job evidence. It remains
preserved; its copy entry is superseded by a copy-only helper `7b0e63a0`, SHA-256
`7b0e63a0290399819f79fde069039cd2d2deda8a6f523f3bb65129d05bb8a23d`.
The successor includes the closed full-audit directory, original successful
A4m receiver-only diagnostic, separately reviewed clock reconciliation and
retained max-job raw/control/analysis records. Eighteen isolated Linux guards
and 29 actual companion layouts/353,807,381 bytes were checked without campaign
IQ reads, device access, transfer or removal. Its positive campaign copy path
remains unexecuted and unvalidated.

Any later copy requires every acquisition, analyzer, audit and workflow process
to have ended, workflow/all three bench locks, actual idle RC3/138 MHz boards,
the actual internal/external UUIDs and sufficient external reserve. Independent
full destination and unchanged-source hashes, fsync and durable retrieval
records are required. The existing exclusive clock-copy reservation prevents
old/new helper duplicates. This successor has no raw-release entry and removes
no source files. A future redundant raw release requires a separately guarded
operation after an actual verified copy and demonstrated next-stage reserve
shortage, with durable retrieval locations and full independent checks before
each unlink. Do not transfer while the active two-slot settling diagnostic or
any later acquisition/analysis uses the bench. Current clock/Tone/finite copied
and removed bytes remain zero.

Three subsequent 156-second GPSDO-only captures on internal NVMe completed
with zero overflow/clipping and restored reference/USB-idle state. After their
process ended, 17 closed files/936,191,802 bytes were copied and independently
hash-verified on the external SSD in 32.19 seconds. All internal originals
remain. The external location is
`/mnt/phase14-testing/phase14-closed-internal-first/receiver-internal-20261010T2045`,
with a durable `retrieval.json` record. The local summary is
`build/phase14-internal-first-storage-result-20261010.json`. This validates the
storage workflow without identifying the earlier receiver/control failures.

The preceding external-aware wrappers required the external UUID and a
filesystem distinct from the system disk. Those acquisition wrappers are now
historical. Future acquisition checks require the recorded internal UUID;
closed-file archival checks independently require the external UUID.
Provisioning changed no active archive, RF settings or retained sample bytes.

Private receipts and prepared tooling are:

- `build/phase14-external-ssd-provision-20261010.json`
- `build/phase14-external-ssd-mount-verification-20261010.json`
- `build/phase14-ssd-staged-helper-verification-20261010.json`
- `build/phase14-next-clock-ssd-stage-prepared.py`
- `build/phase14-post-clock-tone-ssd-prepared.py`

The older relocation and clock/Tone wrappers remain historical prepared tools.
Both copy attempts closed with preserved timeout receipts. The separate
`9770a57e` verification-only recovery completed both full destination and
unchanged-source rehashes, retrieval publication and guard release at October
10 18:48:58 UTC. Its immutable final receipt is
`build/phase14-archive-verification-final-1791658138038212000.json`, SHA-256
`05e818ccbd9ed3dc6779bf5e6d90f5fe7af1d1b3b63500200eb0ec4398412058`.
It copied and removed no recordings. All source originals remain, and no source
relocation is needed. The stopped clock campaign stored its captures on
the external SSD. Subsequent live capture uses internal NVMe under the
operator amendment above; see the current [results](phase14-results.md). Receiver
continuity failures remain separate from filesystem capacity or verified
archive integrity. Original capture settings, failed flags and historical
recordings remain unchanged.

## Lossless raw retention

Use gzip for closed captures after their analyses and independent raw audit
have completed. Keep capture metadata, physical/control records, decoder
receipts, original failure flags and analysis results unchanged. Do not compact
files that an active acquisition, analyzer, verifier or relocation operation
still requires.

For each eligible raw file:

1. Check the declared complete capture, raw byte count and original SHA-256.
2. Compress into a separate temporary file while hashing the original bytes.
3. Independently decompress the temporary file and require the original byte
   count and SHA-256. Also check that the original file and metadata are unchanged.
4. Save and flush the compressed file and a retrieval record before removing
   the redundant uncompressed representation. The record contains both hashes,
   both sizes, the codec, original path and an exact restoration command.
5. Preserve every original receipt. A missing uncompressed filename is resolved
   through its retention record; it is not relabeled as an acquisition failure.

This is bit-for-bit retention. It does not change sampling rate, sample format,
recording duration, mode settings, accepted observations or thresholds. Reanalysis
can restore one recording at a time from its gzip file, verify the original
hash, run the original analyzer and remove only that temporary restored copy.

Maintain a working-space reserve for compression/restoration. Never remove
raw data before independent decompression verification and durable location
publication. A failed compaction leaves the original recording available and
requires inspecting the preserved partial output before retry.

## October 10 cleanup

The Mac's private project build directory occupied about 69.4 GiB. Removal of
109,424 CMake object/dependency intermediates recovered 5.72 GiB. Removal of
1,706 generated static-library, Ninja and disassembly outputs recovered another
10.86 GiB; corresponding CMake input and ELF files were retained. Initial Mac
free space rose from 3.93 to 20.75 GiB, without deleting captures, firmware,
source, SDKs or result records. Reconfigure these historical CMake directories before rebuilding; their
removed files are generated again. This cleanup does not install or rebuild
anything.

A separate compaction plan covers 267 complete historical Mac captures,
22.72 GiB in total, dated before October 8. The private helper is
`build/phase14-lossless-compact-closed.py`, identified by SHA-256
`b689e27618294bde16e42d58394e21814f466302e7499a84e4c0d5b677667e00`.
Its lossless round-trip, incorrect-hash preservation and symlink rejection
fixtures passed. Every actual conversion independently verifies full decoded
bytes and records the new representation beside the unchanged metadata.

Private receipts are:

- `build/phase14-mac-generated-intermediate-cleanup-20261010.json`
- `build/phase14-mac-generated-output-cleanup-20261010.json`
- `build/phase14-mac-lossless-compaction-20261010.json`

The compaction receipt records actual completion and freed bytes; prepared
work or an active compression is not counted as completed savings. No ongoing
RF job or the independent archive recovery is changed by this local cleanup.

All 267 planned historical captures completed verified lossless compaction,
recovering 10.53 GiB. Together with generated-file cleanup, the measured
reclaimed total is 27.11 GiB; Mac free space is about 30.94 GiB. Every original
capture metadata file still matches its retained hash, and all compressed
representations and restoration records are present. Firmware UF2 and ELF
counts and byte totals are unchanged. The final private summary is
`build/phase14-storage-reduction-summary-20261010.json`.
