# Phase 14 memory failure causal plan — October 12, 2026

Status: bounded host diagnostics closed and recomputed; target cause
unisolated and no target successor admitted.
Progress remains 3 of 9 original workstreams (33.3%); estimated 15–37 hours
remaining, with repairs potentially extending that range.

## Preserved failure and counter interpretation

The closed mixed qualification failed B's unchanged 1,024-byte equivalent idle
growth screen: Tone +1,384 bytes and FSKCW +1,704 bytes. A measured zero and
minus 16 bytes. The independent failure reconciliation is
`build/phase14-mixed-resource-failure-independent-review-20261012.json`, SHA-256
`f6531bb570f4324fd6318f19893256d58c7ac1c6b283f06327459408add7e8f7`.
All original outcomes and the eight jobs remain unchanged and uncredited.

A new metadata-only counter inspection at
`build/phase14-mixed-idle-counter-inspection-20261012T0658.json` matched the
eight recorded idle-window hashes to that reconciliation. B's reported TLS
allocation stays at 4,397 bytes; A's stays at 3,861 bytes. Every selected idle
sample reports zero active/pending connections, buffered receive data, pending
TCP bytes, SoftAP sessions, active BLE connection and WTP input reserve.
B's FSKCW arena contracts by 4,096 bytes while allocated bytes grow.
These observations narrow candidates but identify neither a leak nor a cache
or browser cause. No raw samples or devices were accessed.

At exact source `8538564583f1cb67ce9882755d2464e6b2297600`, both
`heap_allocated_bytes` and `allocator_live_bytes` come from newlib
`mallinfo().uordblks`, sampled at different points in INFO formatting. They are
not independent logical allocation measurements. The wrapper refreshes its
snapshot after INFO has already allocated response strings. The portable WTP
service retains per-session replay responses for 300 seconds, with eight
entries per session, and terminal records for 3,600 seconds. Polling prunes
expired entries, while container capacity can remain allocated. Endpoint
disconnect clears its output deque and session/principal strings; this does
not promise that all container capacity is returned. The Pico HTTP close path
frees TLS connection state and resets the response and HTTP parser, but host
WTP tests cannot reproduce lwIP, the CYW43 stack or Pico newlib.

## Separately identified host experiment

The first successor is a Linux-only, hardware-free lifetime probe, compiled
against unchanged `job_service.cpp` and `sha256.cpp` plus their exact-source
headers. Its new host source and CMake wrapper are retained as
`build/phase14-wtp-lifetime-probe-20261012.cpp` and
`build/phase14-wtp-lifetime-probe-CMakeLists-20261012.txt`. No production file,
firmware, configuration, receiver setting or scientific driver is changed.

The probe substitutes a virtual clock and an engine that aborts if prepare or
begin is called. Only synthetic HELLO and STATUS requests are submitted. It
runs two fixed cases: one session and twelve sessions, each with four epochs
of 384 STATUS requests. All request/response temporaries are destroyed before
measurement. Each epoch samples immediately after traffic, after 45 seconds,
one nanosecond before the last request's 300-second expiry, at that expiry,
and after 350 seconds. These are virtual-clock boundaries, not RF acquisition
or a replacement for the blocked two-hour target memory workload.

A separate C++ allocation ledger measures requested live bytes and blocks,
including aligned allocation/deallocation. Positive retained-allocation and
release controls must pass before traffic. Sampling uses C output; its C
library allocations are outside the ledger. Complete service destruction
must restore the ledger's pre-construction baseline. Report every epoch and
container high-water plateau; do not assign the target's 1,024-byte threshold
to host allocator numbers.

The build is bounded to 600 seconds and each probe process to 120 seconds.
The complete host admission/build/diagnostic sequence has a 900-second bound.
Use the retained Linux compiler/CMake and a fresh internal build directory;
no SDK/tool download or installation is permitted. Admission must independently
bind this plan, probe and wrapper hashes; verify the linked exact source files
and transitive project headers; check Linux/no Pico or RF adapter linkage;
exercise ledger controls and reject unknown operations/missing bounds. Only
after that receipt may the separately reserved host probe execute once.
Preserve a failed build, control, admission or diagnostic receipt; inspect its
cause before preparing a distinct successor. Never restart a partial outcome.

## Interpretation and further admission

Expiry recovery plus a stable plateau would support bounded retention in this
portable path. Growing live blocks surviving full destruction would instead
require a source-specific repair investigation. Either result is scoped to
this host experiment and cannot establish Pico leak freedom or explain the
mixed failure by itself. This probe exercises neither 512-event job retention
nor browser HTTP/TLS/lwIP. Those remain separate candidate paths requiring
their own bounded causal plan if this experiment does not isolate the cause.

No new target diagnostic, RF job, decoder, memory qualification, image change,
archive or raw release is admitted by this plan. A later target experiment
requires a separately reviewed runner, fresh process/PID/start/argv and four
lock checks, actual filesystem UUIDs, exact live source/image/boot and preserved
settings/cursors, finite ownership/restoration, and an explicit causal question.
Keep 4 m and 2 m unsupported for all modes, the original 45-second workload,
growth/spread limits and science unchanged. The separate qualifying memory
follow-up remains blocked by the actual mixed failure; expiry never proves
leak freedom. Failed evidence and current useful firmware remain intact.

## Actual host result and preserved admission refusal

The original plan snapshot has SHA-256
`e99a01210a2fdb7b1dda45bb5a79bddf855403af32289de7d7b5360efbbc2501`
and remains unchanged in both internal host output directories. This document
adds the subsequent results. The first host build completed, but its admission
program rejected an ineffective loop-bound mutation guard: a substring check
for `epoch <= 4` also matched `epoch <= 400`. No diagnostic traffic executed.
The failed receipt remains
`build/phase14-wtp-lifetime-host-first-refusal-20261012.json`, SHA-256
`dba9de37524b366e6d63f4b658bb38fb252d5f7ef14faeb2cda95d8de621f260`.

A distinctly identified successor corrected that check to an exact numeric
boundary, passed all seven static acceptance/refusal cases, checked transitive
project dependencies and binary linkage, exercised allocation/release/alignment
controls and refused an unknown argument. Its separate admission receipt is
`build/phase14-wtp-lifetime-host-admission-20261012.json`, SHA-256
`c8a41ed462c0d16c3d1c7cb0c4c0f6f61e5c3196c75f288ac6da45f2c2947eb8`.
These are programmatic static, dependency, binary and control checks, not target
qualification or a general adversarial source review. The successor reused
the unchanged completed binary, SHA-256
`8a0943e0ac70c07f095a1cfcc70ae4cc653aaa96fe476503f89aeac98822d688`;
no build or accepted target job was repeated.

The probe then executed once and closed normally within the 300-second
successor bound, holding all four locks and leaving the owned service active.
Its actual receipt is `build/phase14-wtp-lifetime-host-result-20261012.json`,
SHA-256 `9c20517a50cf2759bf1e84e9c8029d679a6ad2d8f21f8c99315fed9e0474f661`,
identical to clean-root
`build/wtp-lifetime-host-admission-recovery-20261012/result.json`.
The original internal directory `build/wtp-lifetime-host-20261012` retains the
completed build and admission failure. Both reservations prohibit repeats.

| Host case | Epoch 1 live bytes at 350 s | Epochs 2–4 live bytes at 350 s | After service destruction |
| --- | ---: | ---: | ---: |
| One session | 2,769 | 2,769 | 0 |
| Twelve sessions | 4,809 | 6,089 | 0 |

Every 350-second sample retains nine C++ allocation blocks. The twelve-session
case has a 1,280-byte step between its first two epochs, then plateaus. These
data demonstrate bounded retained storage in the selected portable experiment;
they do not identify the individual container responsible or explain B's
target growth. A separate offline review independently checked original hashes,
admission-before-execution order, all 44 samples, expiry boundaries, arithmetic,
plateau and destruction results against the verbatim probe log. Its receipt is
`build/phase14-wtp-lifetime-host-result-review-20261012.json`, SHA-256
`0caf807dd90e2aeea1b7b27314fe64975833d72d94b8fe1a0630e05cf9818181`.

Source inspection also confirms that the existing browser workload rotates
read-only GETs over `/`, `/api/v1/status`, `/api/v1/capabilities` and
`/api/v1/jobs`, with `Connection: close`. The status/jobs views call
`JobService::status()` directly; these GETs do not populate the WTP replay cache
through `JobService::handle()`. Thus a host WTP retention step cannot be assigned
as the browser cause. No cause or target leak freedom is established, no
qualification credit is applied, and the original mixed failure and blocked
memory follow-up remain unchanged.

## HTTP preparation and actual closed result

The next distinct host runner was planned to test the portable HTTP/API response
and parser lifetimes for those four exact GET paths. Reuse the production portable
API and HTTP parser with source-bound fake clock/network/storage adapters;
abort on RF prepare/begin or any mutation. Retain two connection-slot objects
and mirror the production close/reset order. Use four epochs of 400 successful
GETs, rotating the four paths, virtual 10-second spacing and matching 45/350-second
idle observations. All response temporaries must be gone at sampling. Record
the same C++ ledger and prove full fixture destruction returns its baseline.
Keep source, paths, request count and close/reset semantics fixed after admission.

Admission was required to bind the new runner, exact source and reused fixture
hashes, reject non-GET or unexpected paths/mutations, validate ledger and close/reset
controls, and enforce at most 600-second Linux build, 120-second probe and
900-second whole bounds. A fresh unique reservation and actual separate
admission receipt were required before execution. The implementation and actual receipts
below supersede this earlier preparation state. It excludes Pico newlib, TLS,
lwIP and the 512-event job lifetime. No firmware repair is selected.

The first Linux build completed against unchanged clean853 portable sources,
but a fixture assertion aborted during separate admission. It had incorrectly
required production response closure to return immediately to the constructed
allocation baseline. No 1,600-GET diagnostic executed. The preserved parent
receipt `build/phase14-http-lifetime-first-refusal-20261012.json` has SHA-256
`9cc4b4e46ab3cdad637d04a769f840b9d60630e21c14e055b2503f0365df7a8b`.
The original build, binary, logs and reservation remain intact in clean-root
`build/http-lifetime-host-20261012` and must not be rerun.

A distinct, separately admitted assertion localization reused the immutable
portable library. It added source-location reporting and permitted only a
single bounded fixture invocation, refusing the larger experiment. The actual
abort identifies the post-close baseline assertion, before any GET fixture
traffic. Its receipt `build/phase14-http-controls-localization-result-20261012.json`
has SHA-256 `2ca8348863f29ecc21d242fe1e4ea522d0f75ec267c91f55e2da8ccf15cf7ca6`.
This localizes a host fixture assumption, without locating the target cause.

A separately identified capacity-aware successor kept the production close
order and original four-by-400 GET workload unchanged. Its new synthetic
control measures the response body capacity after closure: 4,097 requested
C++ bytes remain for the deliberately injected 4,096-byte body. Explicitly
swapping out that body in the control returns exactly to baseline; this swap
is absent from the workload close path and production firmware. The control
therefore distinguishes retained string capacity from destruction without
altering any target acceptance threshold.

Fifteen static acceptance/refusal cases, exact production close-order checks,
source/dependency/asset and immutable-library bindings, binary argument refusal,
allocation/alignment and capacity controls passed before the diagnostic ran.
The actual separate admission is
`build/phase14-http-lifetime-capacity-aware-admission-20261012.json`, SHA-256
`e02f76fe2a25bd93c62fbb75421e0556c30d2cd624c2a92f89407e0e1939edba`.
The successor compiled only its new host probe against the preserved library;
no production rebuild, target flash or accepted target job was repeated.

The main probe completed once: 1,600 successful rotating GETs with virtual
10-second spacing, two reused slots and four epochs. Construction retains
3,783 requested C++ bytes in 24 blocks. Every closed-400, 45-second and
350-second sample retains 7,233 bytes in 26 blocks, including all four epochs.
Full fixture destruction returns both counters to zero. The parent receipt is
`build/phase14-http-lifetime-capacity-aware-result-20261012.json`, SHA-256
`9c731733b978b0bbb36a2f9d756ea9f04e3c13d85573deb0d40948eafacdd568`.
A separate offline program verified original hashes, admission-before-probe
order and all 14 samples/time/count calculations against the verbatim log:
`build/phase14-http-lifetime-host-result-review-20261012.json`, SHA-256
`cf4ad02dc33f2990d2d8712b5387af539f71d9c34f3f018b8c29429140b95878`.

These results establish a plateau for the selected empty-job host fixture and
capacity retention in its synthetic response-body control. They do not assign
the main plateau to individual objects, reproduce Pico B's same-boot active
512-event workload, or isolate its newlib/TLS/lwIP memory failure. No leak
freedom, target repair, qualification, time credit or memory-stage admission
follows. All coordinators and children are gone, all four locks are available
and the owned service is active. No device, RF, decoder, raw sample, external
archive or removal action occurred.

## Capacity-attribution plan and actual closed result

The next distinct hardware-free runner should answer whether the portable
connection slots' response-body capacities account for their retained C++
allocation step. Reuse the pinned portable library and the same source-bound
empty-job fixture, fake clock/network/read-only storage and abort-on-RF/mutation
adapters. Do not repeat the completed four-by-400 workload or any completed
coordinator, admission control or localization.

Use exactly two slots and six GETs per slot, in this fixed order:
`/api/v1/capabilities`, `/`, `/api/v1/status`, `/`, `/api/v1/jobs`, `/`.
Record requested bytes/blocks and both slots' body size/capacity before requests
and after each production close. The static root response provides a contrasting
empty-body assignment after each dynamic response. After all twelve requests,
release each response body separately in the host attribution control and
record each exact ledger decrement; then destroy the whole fixture and require
the initial baseline. The explicit release is a causal host control, never a
firmware repair or altered production close. Sample printing must not retain
C++ allocations.

Require a fresh unique reservation, source/library/dependency/binary hashes,
exact-path/count/order refusal guards, and separate program admission before
execution. Bounds are at most 120 seconds for its Linux probe-only compile,
30 seconds for the attribution program and 300 seconds for the whole workflow;
hold all four locks and verify fresh quiet/UUID/service boundaries. Any outcome
remains scoped to the portable host implementation. A subsequent target/newlib,
TLS/lwIP or 512-event causal experiment needs a separate finite plan and admission
with fresh source/image/boot/settings/cursor/process/lock/UUID safeguards.
The qualifying memory follow-up remains blocked by the original mixed failure.

The twelve-GET runner has now executed once under a separate bounded
coordinator. Thirteen static acceptance/refusal cases verified its exact paths,
counts, timeout, unchanged fixture/ledger/close implementation and destruction
check. A separate admission program bound the source, dependencies, generated
assets, immutable library and new binary before any diagnostic GET; it refused
the old execution/control arguments. No completed predecessor calibration,
control, localization or 1,600-GET workload was invoked.

Actual parent `build/phase14-http-response-capacity-attribution-result-20261012.json`
has SHA-256 `89ec7137e28ca2793663f4aa07f9c24892d559ee9865ea809538d7dac7ec8df8`.
The separate program admission SHA-256 is
`75ac63cdda4eb8033c48ea4ced6fdc358d0c90957fe4076b7141d825ba6ab40a`.
The internal directory `build/http-response-capacity-attribution-20261012`
retains the source/plan/manifest, probe-only build, admission, verbatim log and
closeout. Its unique reservation prohibits repetition. All processes are gone
and the service remained active; no target or sample was accessed.

Each host slot retains 2,488 body-capacity bytes after the capabilities response,
then 960 after the status/jobs responses. The intervening static root GETs
preserve the preceding capacity even though the closed body's size is zero.
After all twelve requests, the fixture retains 5,705 requested C++ bytes versus
3,783 at construction. Releasing the two bodies individually reclaims 961 bytes
and one allocation block each, returning exactly to the constructed baseline;
full fixture destruction returns to zero. Every one of the 29 samples satisfies
the ledger equation: construction plus each heap-backed body's capacity and
terminator. This attributes the entire 1,922-byte step in this host experiment
to response bodies, without modifying production close behavior.

The separate offline hash/order/arithmetic review is
`build/phase14-http-response-capacity-attribution-offline-review-20261012.json`,
SHA-256 `859d62c488b6ce7bd4483284637a114cdc385264a01aa09a482045a0bcf72435`.
The earlier four-by-400 source schedule leaves one slot with a capabilities
response and the other with status/jobs; the measured capacities predict
`3783 + 2489 + 961 = 7233`, matching its recorded plateau. This is an inference
from the source schedule and the new attribution, not a previously recorded
per-slot measurement. Neither experiment isolates Pico B's newlib/TLS/lwIP or
active 512-event cause.

## Recorded B response context

A new metadata-only inspection bound the four original B physical records to
their existing independent failure-review hashes. It selected only the last
response for each of the four permitted browser paths, with no new HTTP,
device or raw request. Receipt
`build/phase14-browser-last-response-inspection-20261012.json`, SHA-256
`aabb9eeb1e42e31fbbb0889397829a7653b0a761683b7614a9babcccc135ede4`,
records these different end states:

| Mixed job | Mode | Last successful GET | Last response bytes | Job state in that response |
| --- | --- | --- | ---: | --- |
| 1 | Tone | capabilities | 1,301 | Not a status view |
| 3 | FSKCW | root | 38,461 | Static asset; preceding jobs view was running |
| 5 | Tone | status | 2,880 | Running, no terminal record |
| 7 | FSKCW | status | 3,006 | Complete, one terminal record |

Those are recorded payload lengths, not allocated capacities. Python compact
JSON reserialization matches the capabilities hashes, but does not reconstruct
the original status/jobs body hashes from their parsed values. Preserve that
limitation and the original hashes; no body or result was rewritten. The
different final paths and terminal state make retained response capacity a
specific target hypothesis, without assigning the failed 1,384/1,704-byte
growth to it or treating the unchanged comparisons as accepted.

## Target path-contrast plan executed October 12

The next distinct causal runner should test whether idle B's allocated heap
changes with its final read-only browser path while source, boot, configuration
and RF state stay fixed. This is a diagnostic of an idle engineering-profile
board, not the blocked qualifying two-hour memory workload or a reproduction
of active 512-event operation.

Use exactly six sequential authenticated B GETs in this order:
`/api/v1/capabilities`, `/`, `/api/v1/status`, `/`,
`/api/v1/capabilities`, `/`. The capabilities/status/capabilities sequence is
the causal contrast; root responses test persistence after empty-body
assignment. Use the existing credential-device, TLS 1.3, ALPN, certificate,
hostname, status-200 and content-length checks. Preserve each actual response
hash, length and parsed value, without canonicalizing it into replacement
evidence. Any additional raw HTTP-body retention needs a separately source-bound
host collector; it does not authorize IQ capture.

Record three B Console INFO samples before traffic and three samples one second
apart after the original 45-second idle following each completed response.
After the final root response, also sample three times at least 350 seconds
after completion. Keep both heap counters, TLS allocation and all connection,
input, resource/fault observations; the two heap counters remain the same
underlying newlib quantity. Record medians/spreads and the reversible path
contrast without converting them into release acceptance or leak freedom.

Require a fresh unique reservation and separate program admission before any
device access, followed by live admission before the first GET. Hold all four
locks throughout a maximum 900-second workflow. Bind the exact clean853 source
and 138 MHz artifact/installation proof, named A/B serial/protocol identities,
current expected boots, empty/inactive/unowned/disabled state and false flags.
Verify public durable settings/current watermark before and after; permit only
Console INFO and the six GETs. Do not use WTP HELLO/CLAIM/LOAD/ARM/RELEASE,
CONFIG, ROM, flash operations, reboot, GPIO, receiver, decoder or GPSDO requests.
Same-boot public cursor checks are not fresh full-flash byte proofs; preserve
that limitation. No profile/configuration/cursor write is permitted.

Keep the service's verified state unchanged and preserve the installed useful
images. Independently check runtime/import/source/credential bindings, refusal
guards, finite owned-process cleanup, actual filesystem UUIDs and a fresh quiet
boundary before dispatch. The separately implemented runner completed once under actual program and live
admissions, as recorded below. No target repair, changed firmware, threshold
relaxation, RF rerun, raw release or automatic memory-stage chaining is selected
or admitted.


## Actual idle B path contrast and independent closure

The six-GET target diagnostic completed once at 11:35 UTC on October 12 in
607.194409293 seconds, within the 900-second whole bound. Coordinator
`/tmp/phase14-idle-browser-path-contrast-owned-coordinator-20261012.py`, SHA-256
`04779a174319c27b1eae3c4ce0cad123ef04283e9a4ae1fe514d982a75884417`,
held all four locks. Parent PID 3386514/start 72210778, both registered launchers,
the actual probe and admission reviewer are gone. Preserve the unique
`build/phase14-idle-browser-path-contrast-dispatch-reservation-20261012.json`;
never repeat this coordinator, probe, admission, traffic or review.

The separate program admission checked 692 source bindings, the retained clean
138 MHz candidate and installation proof, Python/import/credential identities,
owned-process bounds and 19 static/fixture/refusal cases before device access.
Its SHA-256 is
`255a2496999f70755aac18cc89ccdb5e82f4bb9af22b8485a5d88127c87f5d8d`.
Separate live admission, SHA-256
`fc3a8bd7f297eb74410a2f860eadc20ec3e9f0cd6a82df4112412d7a33f104a8`,
verified the named A/B clean853/138 identities, expected boots, public durable
settings/current watermarks, empty/inactive/unowned/disabled state and false
flags before the first GET. Only 26 direct Console INFO commands and the six
specified authenticated B GETs executed. No WTP peer/fallback, RF, GPIO,
receiver, decoder, GPSDO, configuration, profile, cursor or firmware operation
occurred. The owned service remained active without a state change.

| Completed boundary | Heap median, bytes | Allocator median, bytes | TLS allocated, bytes |
| --- | ---: | ---: | ---: |
| Before traffic | 22,912 | 27,016 | 4,397 |
| Capabilities, then root, each after 45 seconds | 19,864 | 23,968 | 4,397 |
| Status, then root, each after 45 seconds | 22,416 | 26,520 | 4,397 |
| Capabilities, then root, each after 45 seconds | 19,864 | 23,968 | 4,397 |
| Final root after at least 350 seconds | 19,864 | 23,968 | 4,397 |

Every three-sample heap/allocator/TLS window has zero spread. Status raises the
heap median 2,552 bytes relative to capabilities; returning to capabilities
reverses exactly that step. Each root control preserves the preceding level,
and the final 350-second observation preserves the last capabilities level.
The initial capabilities response lowers the pre-traffic median by 3,048 bytes;
its prior retained state is not attributed to a particular container. All
selected connection/pending/RX/TCP/SoftAP/BLE/WTP-input counts are zero and
observed cumulative resource/fault counters remain unchanged. The two heap
counters retain a 4,104-byte offset because they sample the same underlying
newlib quantity at different INFO formatting points; they are not independent
allocation measurements.

Actual response lengths are 1,301/38,461/2,758/38,461/1,301/38,461 bytes. The two
capabilities hashes match, and all three root hashes match. Each actual
response hash, length and parsed value is retained; no raw HTTP body was
separately collected or reconstructed. The full Console RX/TX bytes are also
retained and independently bind all 26 parsed INFO observations.

Actual clean-root `build/idle-browser-path-contrast-20261012/result.json`,
SHA-256 `254bbe284a50f46f095789dcf6def69994f12a6a5d7d80aee125953a710220c1`,
is mirrored verbatim in local
`build/phase14-idle-browser-path-contrast-closed-20261012/result.json`.
The separate metadata-only hash/order/timing/arithmetic/source/settings/resource/
process/service review is mirrored as that directory's `independent-review.json`,
SHA-256 `75b235fac04cf28ebb9191003e4d548d73e239a6b15bfcc2c48695c46db5c018`.
It verified the actual 45/350-second boundaries, one-second sample spacing,
admission order, exact traffic counts, original Console bytes, median/spread
arithmetic and unchanged public settings/current watermarks, without making a
new device request. Fresh final quiet receipt
`build/phase14-idle-browser-path-contrast-final-quiet-20261012.json`, SHA-256
`9eac8b037003ffa6b40cfa40472216624e88884a33ac698bf9405c6afd068f5d`,
observed at 1791805104759786283 ns, verifies every exact registered identity gone,
all campaign processes gone, four locks simultaneously available, expected
filesystem UUIDs and active service. Internal free space is 10,625,249,280 bytes;
external free space is 943,881,781,248 bytes. No external transfer/removal occurred.

This establishes a reversible idle target heap dependence on the completed
browser path, consistent with the separately identified host response-body
retention. It does not measure an individual target container's capacity or
isolate the original active 512-event mixed failure. Same-boot/public cursor
checks are not fresh full-flash byte proofs. The original mixed failure and
1,024-byte acceptance limit remain unchanged; qualifying memory follow-up is
blocked. No leak-freedom, target repair or release acceptance follows. Counts
remain 3 of 9 workstreams (33.3%); estimated 15–37 hours remaining, with possible
repair extension and no diagnostic/elapsed-time credit.

## Selected source repair and completed host validation

The operator's direct request to fix the defect supersedes the historical
unselected-proposal limits below. Production source now has one shared
`HttpResponse::reset()` method that releases its dynamic body before resetting
response metadata. Connection closure and acknowledged keep-alive completion
call it after the existing mutation-finish and cookie-scrub operations.
Transport, TCP/TLS, parser cleanup, response contents and RF ordering remain
unchanged.

The distinct Linux regression rebuilt the changed portable core and passed six
affected test groups. Its 30 allocation cases return to construction baselines;
the separate previous-assignment control fails as expected. Actual parent
SHA-256 is `a367788c516ecf882af7a64913692487e07048217cc85700bee55d1a509467ab`;
offline source/log/order review SHA-256 is
`e6f609c2528a337599209baf1a882ba158fa583d529233024a30fc42dc2002ea`.
The completed harness and children are gone. No hardware or raw access occurred.
Do not repeat that validation or any previous closed diagnostic helper.

The selected repair commit is
`2d67224dbddc16b320e43c9fce3ccb74f8d102ce`. Its distinct clean-source 138 MHz
candidate and independent rebuild are now complete and ELF/UF2 byte-identical.
Actual build receipt SHA-256 is
`33a20e76b07234663c66dccd61400d30048fa913b4fd2135fbe21b04bea09cd7`;
independent exact source, artifact and layout review SHA-256 is
`8579cff2fd4055860c737201064ccf56a59709b529d982792e8d66a919d2656f`.
The reviewed UF2 SHA-256 is
`6d5ee077e711d008422a0b881f4912e17e7c2fad56abf47c9fc6bcd4ee974787`.
Both builders and all registered children are gone. Preserve the earlier
checksum and sandbox process-inspection refusals; neither compiled firmware.

Next stage the exact repaired source and reviewed candidate into a NEW internal
toolroot, verify every source/artifact/dependency binding, then implement a
distinct finite application-only installer and its independent program
admission before device access. Require both named boards empty/inactive,
unowned, disabled and default-false flags at their expected old boots. Preserve
their public durable settings/current watermarks before and after loading only
the reviewed application UF2; require exact new source revision, new boots,
138 MHz, unchanged settings/current watermarks and final idle state. Do not
write profile/config/cursor journals, perform RF jobs or issue GPSDO/receiver
requests. Keep all four locks and service state; bound each verified own
picotool child to 45 seconds, boot readiness to 90 seconds and whole install to
900 seconds. Closeout must restore only an owned service and prove exact
children gone. Public settings/cursor equality is not a fresh full-flash proof.

Preserve the old clean853 worktree and useful images. Installation and subsequent
read-only repaired-image contrast need fresh program/live admissions, exact
image/new boot/settings/current-watermark bindings, all four locks, filesystem
UUID checks, finite owned-process cleanup and unchanged-service proofs. Do not
infer original active-512-event acceptance from the idle contrast. A new mixed
qualification needs its own repaired-source admission and storage reserve;
there is no automatic memory follow-up, raw release or threshold relaxation.

## Historical unexecuted source-candidate proposal

A private, unselected proposal is retained as
`build/phase14-response-body-release-candidate-20261012.patch`, SHA-256
`c07cf49f0417fd8958afebac1f738f40225e400f05bf8a2f01ffac7c02a827fe`.
It adds only `std::string{}.swap(response_.body);` immediately before the two
existing `HttpResponse{}` resets in `Connection::close` and acknowledged
keep-alive completion. Existing TCP/TLS/acknowledgement, mutation-finish,
parser, cookie/header/principal cleanup and RF/service order remain unchanged
in this proposal. The patch is not applied to production, built or installed;
no target repair is selected. Exact original/candidate/patch hashes are retained
in `build/phase14-response-body-release-candidate-source-review-20261012.json`.

Next implement a distinct Linux-only candidate fixture and separate program
admission before execution. Reuse the pinned portable core and source-bound
fixture/ledger dependencies without rerunning any completed probe, calibration,
localization, four-by-400 workload or twelve-GET attribution. Use no GETs or
physical adapters. Five bounded synthetic cases exercise empty/static body,
15-byte body, 16-byte body, 1,301-byte body and 2,758-byte body across two slots;
verify response bytes remain unchanged while active, then compare complete,
partial/cancelled and acknowledged keep-alive reset boundaries. The unchanged
reset is a scoped control; the proposed reset must return each released body
allocation to its construction baseline. Record requested C++ bytes/blocks and
body size/capacity, and require complete destruction to return all tracked
allocations to zero. This qualifies only the private candidate's host behavior.

Require a fresh unique reservation, exact two-line source-delta and reset-order
acceptance/refusal guards, source/library/dependency/binary/runtime bindings,
separate actual admission, calibrated ledger/alignment checks appropriate to
the new fixture, fresh quiet/UUID/service checks and all four locks. Bounds:
120 seconds for probe-only Linux compilation, 30 seconds for the candidate
fixture, 300 seconds whole. Do not rebuild the portable core, install tools or
an SDK, touch firmware or select a target successor. Any later source change,
Arm build, installation, target repeat or RF/memory qualification requires its
own finite admission and source/image/boot/settings/current-cursor safeguards.
The useful installed clean853 images and immutable failed mixed evidence remain
unchanged; no automatic stage chaining or raw release is admitted.
