# Component 4: shared LOAD adjustments and reply admission

The software fix is complete: LOAD responses, active-job state and retained
history now share an immutable adjustment list. The exact C7 request produces
its complete reply under the two modeled memory-pressure cases that made the
previous implementation close the endpoint. Group 2 remains OPEN. This is a
host reproduction and software correction, not proof of the uninstrumented
branch taken on C7 or new physical acceptance.

The user-requested backlog cleanup was published first as
`495a647eaddef71e5970cff53ec6e335effecadb`; its
[review](phase11-5-r3-v2-backlog-review.md) records scope and validation.
The [execution prompt](phase11-5-r3-v2-component4-prompt.md) and
[machine-readable measurements](phase11-5-r3-v2-component4-result.json)
make this subsequent work reproducible.

## Exact request and reproduced path

`tests/load_reply_tests.py` reconstructs the C7 request from protocol fields.
Its 52,105 framed bytes were compared byte-for-byte with the offered LOAD bytes
in the private C7 `rf.jsonl`. SHA-256 is
`e5b48b92dd2abd74e670f2b2aed3d660c9b357bd4857be6b64b8affedbcee670`.
The original packet is
`8cfcdfeef0c4513f24fe4dff64eaef1f62bbeaa4054c33d2d6720a3481e4b908`.
The generated fixture contains protocol data, not credentials or raw captures.
The earlier logger's lack of individual write counts remains a limitation of
physical evidence.

The host driver uses production `FrameParser`, JSON decoding, `JobService`,
`StreamEngine`, frequency planning, response encoding, framing and `Endpoint`.
Only clock, identity, memory availability and the inactive block sink are host
adapters. It prepares E6's 512-event/3,600-second job, aborts/releases it, ages
request replay past 300 seconds while retaining its terminal job, then supplies
a synthetic HELLO/seven-STATUS/CLAIM prelude and the exact C7 LOAD. The prelude
models retained state; it is not a replay of every original session, timestamp,
network exchange or observer cache entry. Its assertions require Empty/owned
state and one terminal record before C7. No ARM is sent or sink started.

The response contains all 512 adjustments and is 54,916 bytes. Its admission
requires 54,916 + 1,024 scratch + 32,768 reserve = **88,708 available bytes**.
Under modeled pressure the old service accepts LOAD and caches its success;
`encode_load_response_buffer` then returns empty at its admission check, and
`Endpoint::enqueue` disconnects. The job remains Loaded and inactive. No reply
page allocation is attempted on that refusal path. This reproduces C7's
observable pattern without requiring an allocator NULL.

## Memory model and limits

The captured post-LOAD INFO snapshot reports linked heap 219,704 bytes,
`heap_allocated_bytes` 125,848, allocator live 129,200, allocator peak 165,464,
and TLS allocation 31,384. Both allocation-failure counters are zero. These
metrics have different accounting definitions. The firmware admission callback
uses `mallinfo().uordblks` (the heap-allocated metric), not the allocator peak.
The snapshot is after the failed exchange, not a measurement at encoder entry.
Its path and SHA-256 are recorded in the result JSON.

The driver counts requested C++ allocation bytes while production code runs.
Nullable reply pages are counted separately. It excludes host input-fixture
storage, allocator metadata and static engine buffers. Earlier input, JSON and
preparation admission checks are unrestricted; only post-LOAD reply admission
uses the modeled budget. This deliberately isolates the observed failure stage,
so passing does not qualify parser peaks, fragmentation, TLS concurrency, or a
whole-target heap lifecycle.

Relevant costs are:

| Lifetime | Cost and treatment |
| --- | --- |
| Input | 52,089 payload bytes in paged storage; released before preparation. Outside modeled reply admission. |
| Decoded job | 512 events; event payload is 20,480 bytes on this host. Released by the endpoint before encoding. |
| Active job | Its own retained 512-event vector remains during the reply. |
| Prepared RF plan | Production StreamEngine/plan/Waveform storage is included in counted dynamic allocations. Static buffers remain outside heap accounting. |
| Adjustment list | 512 × 24 = 12,288 event bytes on this host; separate copies previously existed in active state, returned Response and request replay. E6 also retained its terminal LOAD response. |
| Replay/history | Real service records are retained in the model. Synthetic prelude IDs and host ABI prevent treating their total as a target measurement. |
| Reply | Fourteen pages totaling 54,916 bytes, allocated only after encoder admission. |
| Reserve | Existing 32,768 bytes plus the existing scratch checks; unchanged. |

Two pressure cases bracket the hypothesis without double-counting TLS:

* **Calibrated net background, 18,168 bytes:** sampled target used 125,848 minus
  old host post-failure retained allocations 107,680. This net adjustment includes
  TLS plus ABI, allocator and unmodeled-context differences. It is a calibration,
  not an independently measured component. It is held constant across revisions.
* **TLS-only background, 31,384 bytes:** add the captured TLS cost to counted host
  allocations without calibrating other platform differences. This is a separate
  sensitivity case, not an exact physical heap prediction.

| Case | Old encoder available | Fixed encoder available | Old outcome | Fixed outcome |
| --- | ---: | ---: | --- | --- |
| Zero background control | 98,696 | 123,560 | Complete reply | Identical reply |
| Calibrated net background | 80,528 | 105,392 | Loaded, closed, zero reply | Complete reply |
| TLS-only background | 67,312 | 92,176 | Loaded, closed, zero reply | Complete reply |
| 100,000-byte background | 0 | 23,560 | Loaded, closed, zero reply | Loaded, closed, zero reply |

At encoder entry, counted C++ allocations fall from 121,008 to 96,144:
**24,864 bytes removed in this host scenario**. Fixed post-page enqueue
availability is 50,908 bytes in the calibrated case and 37,692 in the TLS-only
case, above the unchanged 33,792-byte enqueue requirement. These are modeled
values, not target free-space or largest-block measurements.

## Smallest correction and review

Only `job_service.hpp/.cpp` change production behavior. `AdjustmentList` owns
an immutable vector through shared ownership; preparation moves its vector into
that ownership once. Active state, returned responses, request replay and
terminal history copy the owner, not the 512 entries. Clearing or resetting one
owner does not invalidate another. Equality remains value-based. Preparation
still uses a mutable vector until validation is complete. Encoding, RF waveform
code, limits, admission reserves and protocol fields are unchanged.

Adversarial review covered cached and fresh-request LOAD retries, retained jobs,
request-ID conflicts, caller replacement, reset lifetime, independent-list
value equality, exact boundary admission, and every output-page failure in both
WTP and browser encoding. The existing endpoint test verifies reconnection and
STATUS after a failed reply allocation. No replay retry prepares or starts the
job again in the new lifetime test.

Review found that the first model placed CLAIM before the seven STATUS requests.
C7 had STATUS before CLAIM. The model was corrected, an initial-state assertion
and malformed-root guard were added, and calibration was regenerated from the
corrected baseline. A draft expected second frequency was also corrected against
the unchanged production planner output. Tests now require complete independent
frame decoding, schema validity, all adjustment values and the exact reply length.
A second assessment found no remaining actionable issue in this bounded fix.
The unmeasured physical branch and target concurrency remain explicit limits.

## Validation and source impact

* Full host build succeeded. CTest passed 70 of 71 targets in the sandbox; the
  existing loopback TLS server could not start there. The same TLS test passed
  with local loopback access, completing all 71 targets. It performs no device RF.
* Core tests pass 37/37, including shared replay lifetimes and all fourteen page
  failure positions in each of the two encodings. The two C7 regression tests
  pass. The corrected driver with production source from `495a647` fails the
  two pressure subcases; its unrestricted control passes.
* AddressSanitizer and UndefinedBehaviorSanitizer builds pass the core and C7
  regression targets. These checks cover shared-owner lifetimes and failed-page
  cleanup; they do not establish target heap behavior.
* Pico 2 W / RP2350 Arm StandaloneRF cross-build succeeds with local SDK 2.3.1,
  GCC 15.3.1, 138 MHz PIO and RAM rendering. Linked heap-hook and stack-guard
  checks pass. Renderer remains 660 bytes at `0x200012d8`; linked heap is 219,712
  bytes. This precommit build is not a published/qualified firmware candidate.
  ELF SHA-256: `e4a24f295f42736973fc17e1cc4a698446fffbc34ec383ef3677c0346e7ae8d8`.

Reproduce the portable checks with the documented host configure/build workflow,
then `ctest --test-dir build-host -R '^(load_reply_tests|wsprrypico_core_tests)$'
--output-on-failure`. To compare old production behavior, archive `495a647` into
an isolated build source directory, overlay the current driver/test and its
CMake target registration, and run the same regression. The stored before/after
model results contain no output capture bytes; their hashes bind the replies.
Local logs and private inputs remain under `build/phase11-5-r3-group2-component4/`.

This change affects shared service response retention for USB and browser/network
clients; it does not modify the waveform implementation, but the firmware image
and memory layout change. Historical Group 1/2 results retain their original
identities. No flash, USB command, fixture change, RF job, or new hardware counter
was used. The next physical gate is a newly authorized, bounded candidate build
and idle 512-event LOAD/reply check with the retained job and measured TLS context,
followed by affected Group 2 assertions only if admission succeeds. Existing
finite hardware allowances were not renewed by this host work.
