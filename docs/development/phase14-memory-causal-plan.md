# Phase 14 memory failure causal plan — October 12, 2026

Status: first bounded host diagnostic closed and recomputed; target cause
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

## Next capacity-attribution plan, unimplemented and unqueued

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
