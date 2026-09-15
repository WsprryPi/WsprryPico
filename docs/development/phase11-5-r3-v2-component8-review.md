# Component 8: LOAD replay allocation correction

The decoder no longer retains a 512-element vector of JSON views alongside
input pages and decoded events. Both identical and fresh-ID LOAD replays now
pass the unchanged reserve in the calibrated host regression. The primary reply
is unchanged. This closes the demonstrated software allocation overlap; the
component 7 physical reserve failure and bounded target replay acceptance remain
OPEN pending a new image and physical measurements.

The [prompt](phase11-5-r3-v2-component8-prompt.md) defines this software-only step.
The [results](phase11-5-r3-v2-component8-result.json) preserve before/after
measurements, source and log hashes, test outcomes and build identity.
No device, host fixture, network configuration or RF state was changed.

## Reproduction and allocation lifetime

The earlier regression modeled only reply admission. It did not measure the
input/decoder overlap while a Loaded job and retained E6 response were present.
The extended driver feeds the exact 52,105-byte C7 frame through the production
FrameParser, JSON parser, decoder, JobService, StreamEngine, response encoder and
Endpoint, then sends the identical request and one fresh-ID same-job request.
The fixed request hash is unchanged from component 7.

Preparation uses the existing E6 job contents and synthetic session/prelude,
retains its Aborted terminal response, and ages its request replay past 300
seconds. Ordinary C++ `new` allocations during production operations are counted from
service construction onward. Input/output page allocations are counted and
removed at actual release. The paired buffer deallocation callback defaults to
`std::free`; the driver installs its tracking pair before any buffer exists.
This avoids accumulating freed pages across consecutive exchanges. The driver
uses an inactive sink and a forwarding counter around the real StreamEngine.

During replay, the existing job remains Loaded while input pages, a newly decoded
512-event vector and the old temporary JSON-view vector coexist. Replacing only
the decoder traversal reduces each host replay peak by exactly 16,384 bytes.
The production service still processes the complete decoded request and digest;
no replay shortcut skips validation or changes request/job-ID conflict rules.

| Host allocation measurement | Before | After |
| --- | ---: | ---: |
| Primary peak | 151,564 | 151,564 |
| Identical replay peak | 184,673 | 168,289 |
| Fresh-ID replay peak | 184,673 | 168,289 |
| Live input pages at replay peak | 52,105 | 52,105 |
| C++ requested bytes at replay peak | 132,568 | 116,184 |
| Calibrated replay headroom | 29,288 | 45,672 |

All sizes are bytes. Host peaks exclude allocator bookkeeping, alignment overhead,
fixture input storage, reporting buffers, static engine buffers and unmodeled
platform context. The clock is synthetic; no five-second target latency acceptance
is inferred from host execution. The prelude does not reproduce every captured
TLS/HTTP/INFO observer cache entry or its scheduling.

## TLS calibration and limits

Component 7 measured allocator peak 190,424, heap capacity 219,712 and TLS
allocation 31,384. The pre-fix host replay peak is 184,673. The fixed net background
is therefore 5,751 bytes. It includes TLS, host/target ABI differences, allocator
accounting and omitted platform context. It is calibrated to one physical peak,
not independently measured background memory. It remains unchanged before/after;
TLS is not added to this calibration again.

With that fixed net background, the old regression fails at 29,288-byte headroom
and the new one passes at 45,672 bytes. A zero-background control also passes.
A separate sensitivity model adds all 31,384 TLS bytes directly to the 64-bit
host allocations. That stricter model rejects replay at endpoint admission before
decoding on both versions. Its primary succeeds; its replay refusal remains
expected. This limitation prevents claiming general target memory sufficiency.

The RP2350 compiler independently reports `sizeof(json::Value) == 16` and
`sizeof(RfEvent) == 40`. The removed target view-vector payload is therefore
8,192 bytes; the host view is 32 bytes and removes 16,384. The model's reduction
must not be presented as measured target savings. Removing an allocation overlap
is proven in source and the host model; the exact captured target peak site,
other transient peaks, fragmentation and TLS concurrency remain unmeasured.

## Correction and adversarial reassessment

`Value::next_element` traverses one validated array without retaining a container
of views. LOAD first counts at most 513 entries, rejects empty/over-limit arrays,
reserves exact event storage, and traverses again to decode the fields. Existing
JSON validation still runs first. This adds one traversal while removing the
large temporary allocation; target latency remains a physical check.

Review covered empty, one-event, 512-event and 513-event arrays in both contiguous
and paged storage, event order and values, nested/empty array elements, escaped
strings crossing a page boundary, and repeated end-of-array access. Existing
protocol, malformed-input, request/job conflict, retained-response lifetime,
partial-page allocation failure, endpoint, USB and browser tests remain active.

The new end-to-end regression requires all 512 exact adjustments, complete frame
and CRC decoding, schema validity, response size, request/job identity and identical
replay contents. It verifies E6 retention, Loaded state, zero RF starts and exactly
two preparations (E6 and primary). Both replays add no preparation. Every exchange
returns tracked page use to zero. Overload still refuses and releases its pages.

Review corrected the evidence model's lifetime accounting: the earlier reply-only
page counter was unsuitable for repeated input/output allocation. The new paired
tracker measures live pages; legacy reply tests retain their separate model.
Review also required explicit calibration and host/target ABI distinctions and
retained the stricter TLS-only refusal rather than representing every model as a
pass. Reassessment found no remaining actionable defect in this bounded software
change. Physical replay acceptance remains an explicitly separate open gate.

## Validation and next step

The full host build succeeds. All 72 configured CTest targets pass across the
sandbox run and the existing TLS test rerun with local loopback access; the
initial sandbox TLS-server failure is preserved in the log. The exact updated
regression fails on isolated pre-fix production source at the reserve assertion.
AddressSanitizer and UndefinedBehaviorSanitizer pass the core and replay suites.
The Pico 2 W / RP2350 Arm cross-build succeeds with local SDK 2.3.1, GCC
15.3.1, 138 MHz and RAM rendering. Linked allocator-hook, stack-guard and
renderer checks pass; heap capacity remains 219,712 bytes. This is a precommit
ELF labeled `ba28bd5ff0ba-dirty`, not a published or flashed candidate. The
renderer remains 660 bytes at `0x200012d8`. Local `PICO_NO_PICOTOOL=1` matches
the prior cross-build and avoids fetching packaging tools; no UF2 is claimed.
The exact ELF hash is in the result.

Reproduce with the documented host configure/build workflow and:

```sh
ctest --test-dir build-host -R '^(load_reply_tests|wsprrypico_core_tests)$' --output-on-failure
```

For the pre-fix comparison, archive `ba28bd5` into an isolated source directory,
overlay the current driver/tests and paired buffer-allocation instrumentation,
then build `load_reply_driver` and run `load_reply_tests`. Keep the original
`codec.cpp` and JSON traversal there. Private logs and model output are under
`build/phase11-5-r3-group2-component8/`; published results contain hashes and
summaries only.

Next is a newly bounded candidate validation on Pico A: verify exact image/boot
and retained state, then the primary, identical and fresh-ID LOAD replies under
measured TLS pressure and the full observation interval. Preserve the 32-KiB
reserve and five-second reply deadlines. Do not reuse the exhausted component 7
allowance or label its failed replay a pass. Broader Group 2 remains OPEN.
