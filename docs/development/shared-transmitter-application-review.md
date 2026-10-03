# Shared transmitter application review and validation

## Scope and repository baseline

Work is isolated in branch `codex/shared-transmitter-application`, based on
`codex/pin-allocation` at `251ed992245f3b95611de767cc732f3cb1bbb34d`. The
[execution prompt](shared-transmitter-application-execution-prompt.md) records
the authorized implementation, review and publication scope. The
[foundation guide](shared-transmitter-application.md) defines supported API
behavior; the [fleet contract](../transmitter-application-contract.md) retains
the complete application direction and later implementation gates.

The original shared contract and its README/CONTRACT/architecture/browser links
were carried surgically from the uncommitted devel checkout. Newer pin-branch
implementation documentation was retained. SHA256 comparison verified the five
original source documents remained unchanged in that checkout during this task.
No other repository or Phase 12 source, scripts, evidence, build or hardware was
changed by this work.

Phase 12 was checked before implementation and before final validation. The chat
`Close Phase 12 acceptance` remained active, with no completed final turn;
committed devel remained `1dab547e17cd01e0562bab5b6b2ee4d652fd7b3a`, already an
ancestor of the pin baseline. Its uncommitted work was not imported. Integration
of its final committed changes remains pending before a later devel integration;
this branch does not close Phase 12.

## Implementation disposition

The foundation supplies GET application and GET/PUT station/hardware resources,
explicit member/device/boot targets, common durable-generation revisions,
supported pin projections, station power metadata, saved/active reporting,
closed schemas, 21 request vectors and 20 Pi hardware-inventory coverage rows.
All writes converge through the existing scheduler, whole-configuration validator
and journal. WTP/1, Field-GATT/1, default Config v1 serialization, flash layout,
credential provisioning and transmitter timing remain unchanged.

The existing normal field HTTPS cookie/session policy now admits these resources
and the existing pin-review routes as Configure operations. Blank, pre-clock and
unauthenticated access remain denied. No listener or new configuration carrier
was introduced.

## Adversarial findings and repairs

The first assessment covered source, actual API behavior, schemas, persistence,
ownership, boot identity, capability claims and access-carrier wiring.

| Finding | Repair and evidence |
| --- | --- |
| Content-only revisions could revive an old token after A-to-B-to-A saves; cloned boot/config observations also needed device binding. | Revisions now include device/boot identity and durable journal sequence. Tests cover A-B-A, identical saves, boot change, cross-route writes and different device identity. |
| Field HTTPS's operation allowlist would reject the new authenticated resources and pin review. | Classify them through existing Configure admission. Tests verify normal authenticated reads/writes and refusal before clock readiness or without a cookie. |
| Pin conflicts were placed in HttpResponse's ETag member, leaving an empty JSON body. | Correct both hardware and legacy config paths. Tests check conflict role/owner/GP in the body, with no error ETag. |
| A hardware save could commit before output-disable confirmation failed, and later configuration could continue despite that unresolved application failure. | Return `output_disable_failed`, retain saved versus active plans, latch output inhibition and a scheduler configuration fault, expose `application_error`, and block subsequent configuration/admission until a new boot. Fault injection and actual-response schema checks cover this path. |
| A configuration created after an unconfigured boot must not be reported as boot-applied hardware. | Capture healthy boot configuration explicitly and report null active plan/revision when absent. Blank and later-write fixtures cover it. |
| The carried contract still described fixed GP2 and all new management routes as proposals. | Update the supported pin/API subset, budgets, transport policy and coverage map while retaining unimplemented Pi, recurrence and hardware gates. |

Compilation caught two test-only API-name/type mistakes, which were corrected.
The maximum-response test also used an expiry beyond the existing Config v1
signed JSON integer bound; it now uses the largest accepted integer and all eight
valid schedule entries. No stored-configuration or WTP numeric grammar was changed.

The second assessment rechecked the repaired mutation ordering, field admission,
structured responses, saved/active/fault observations, schema vectors, retained
credentials/enablement/schedules/expiry/watermark/STOP state, and absence of a new
ownership or transport authority. No remaining actionable findings were found
within this foundation. This is a source/behavior assessment, not an independent
external review or hardware qualification.

## Validation evidence

C++ validation used GCC 14.2.0 on Linux `wspr5`, from private source-only snapshots
under `/tmp/wsprrypico-shared-application-01a0f2e4`. No Mac native C++ compiler
retry, SDK/tool download, flashing, device access or RF operation occurred.

The final broad selection is reproduced from its configured Linux snapshot with:

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure -E \
  "^(phase11_5_package[678]_tests|phase11_7_closure_tests|recovery_web_tests|load_reply_tests)$"
```

The final selection passed **99/99 tests**, including actual application resources and
schema conformance, legacy network/pin/scheduler behavior, normal field HTTPS,
storage/recovery, protocol/encoder and image-checker tests. The focused six-suite
application/network/pin/standalone/SoftAP rerun passed after repairs. Schema tests
check all 21 positive/negative request vectors and emitted configured, blank,
pending, unhealthy and configuration-fault responses.

The four excluded Git-history suites passed locally against this feature's real
repository: package 6 (4 tests), package 7 (7), package 8 (8) and closure (4).
Recovery-web checks passed locally with existing pinned dependencies, without
installation. They require dependency context absent from the Linux snapshot.
Python syntax, closed JSON artifacts, C++ formatting, WTP contract validation,
documentation links and diff whitespace were checked.

The full 105-test source-only snapshot suite is not claimed green. Its four
Git-history suites and recovery-web suite require context outside the snapshot.
The remaining load-reply suite has the same three failures on the exact unchanged
pin baseline archive `251ed99` and this feature: maximum status/terminal retention,
reply-reserve refusal, and uncalibrated TLS sensitivity. Both pass its other four
tests. Those baseline failures are not reclassified as feature acceptance.

Both `WsprryPico` and `WsprryPico-StandaloneRF` cross-linked with the pinned clean
SDK 2.3.1 at `079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1. The
existing prebuilt pioasm was used; `PICO_NO_PICOTOOL=ON` avoided downloads and
native helpers, so this check produces linked ELF evidence rather than a packaged
UF2. Linked heap, BTstack pool, stack-guard and RF-renderer gates passed on the
affected final build. Build-selected RF inhibition and clock choices were retained.

## Remaining gates

This branch delivers the Pico configuration/API foundation. Pi mapping and fleet
controller consumption, durable recurrence transfer, expanded autonomous jobs,
drive/calibration, amplifier/LPF adapters and Pico Si5351 remain unimplemented.
Physical GPIO/control behavior, timing, resource coexistence, conducted RF and
release acceptance remain separate explicitly authorized gates. Host and linked
image results do not qualify those behaviors. Phase 12 integration remains pending
as recorded above.
