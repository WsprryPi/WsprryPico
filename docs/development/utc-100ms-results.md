# Accepted 100 ms UTC policy execution

Date: 2026-10-17. The user accepted the proposed 100 ms ordinary-operation UTC
uncertainty policy and authorized execution, adversarial repair/reassessment,
documentation, commit and push on `devel` in both repositories. The complete
[execution prompt](utc-100ms-execution-prompt.md) was saved before implementation;
its UI clarification records the persistence issue found during review.

Source bases: Pico `e8b5fb53691526c9cd5370fb334843fd6124220b`, Pi
`d43b4e305519fa4e1612c42c293849647d357e5c`. Concurrent unrelated Pico planning
edits were preserved and excluded from this change. The
[Pi implementation/review record](https://github.com/WsprryPi/WsprryPi/blob/devel/docs/development/utc-100ms-review.md)
contains exact host targets, UI evidence, first-round finding and closure.

## Outcome

WsprryPi now uses 100000000 ns (100 ms) for new and missing WTP settings over
USB, Plain LAN and TLS. This is product configuration/runtime behavior, not a
harness-only override. C++ construction, JSON missing-field parsing, generated
configuration/INI defaults, new catalog/discovery drafts and UI defaults agree.
Every explicitly saved valid limit remains exact, including 1 ms and custom
37/250 ms examples. No automatic migration guesses whether old 1 ms was deliberate.

In the active endpoint form, enter `100000000` in **Maximum UTC uncertainty (ns)**
and review Setup's normal autosave status. A saved-device editor additionally
has **Use 100 ms**, which edits only that profile draft; **Save device** persists
it and **Use this device** applies it to the active endpoint. Neither reading
nor choosing the profile preset silently adopts it in the running endpoint.

Pico firmware requires no functional change. The existing JobService, local
clock and engine already accept explicit per-job limits up to the unchanged
500 ms advertised ceiling and enforce them at ARM and local launch. New
`tests/firmware_profile_tests.cpp` cases use the production clock/service
profile and inhibited local engine:

| Case | Expected and observed |
| --- | --- |
| ARM uncertainty 99999999 / 100000000 ns, job limit 100000000 ns | Accepted. |
| ARM uncertainty 100000001 ns, job limit 100000000 ns | `ClockUncertain`; no physical output. |
| Launch uncertainty after one second's unchanged oscillator aging: 99999999 / 100000000 ns | Logical job runs on the inhibited engine. |
| ARM admits, then aged launch uncertainty becomes 100000001 ns | Job becomes `Missed`; physical output stays off. |
| Explicit 1000000 ns job limit with 1000001 ns clock | `ClockUncertain`; no physical output. |

The Pi's real application/scheduler/backend also admits an 18 ms scripted clock
with its new constructed default, refuses that same clock under an explicit
1 ms limit, refuses a clock above 100 ms and verifies the selected limit in the
serialized ARM request. The independently tested actual production USB
management/time pair runs over fragmented anonymous pipes with networking
disabled. This separates host policy, transfer accounting and local authority.

100 ms is the accepted engineering admission policy, not a WTP/1 requirement,
measured UTC error or symbol/edge jitter allowance. The original
[1 ms investigation](usb-time-uncertainty.md) and physical uncertainty
measurements remain dated evidence. No transfer error was clamped or relabeled.
No job/event/payload/duration/mode/session capacity, RF memory reserve, 64-byte
foreground budget, clock-step/leap/host qualification, oscillator drift,
holdover, ARM lead/horizon, missed-start deadline, STOP/recovery, ownership,
standalone scheduling, Wi-Fi CRUD/common-name or AP timeout behavior changed.

## Validation and review

Pico checks:

```sh
source scripts/xcode_env.sh
cmake --build build/host-xcode --parallel 4
ctest --test-dir build/host-xcode --output-on-failure
ctest --test-dir build/host-xcode -R '^(firmware_profile_tests|phase14_tests)$' --output-on-failure
/Users/lbussy/GitHub/WsprryPi-Qualification-Harness/.venv/bin/python -B tests/config_update_schema_tests.py build/host-xcode/config_update_tests
cmake --build build/usb-host-sanitize --target firmware_profile_tests --parallel 4
ctest --test-dir build/usb-host-sanitize -R '^firmware_profile_tests$' --output-on-failure
```

The full suite had 186 entries: initially 183 passed, two failed and one skipped.
The new profile test's first assertion incorrectly expected physical output
from an inhibited engine. Corrected it to check logical Running/Missed and
physical output-off separately; the rerun passed. Phase 14's loopback test was
sandbox-blocked, then passed with loopback access. The schema test's configured
Python lacked `jsonschema`; the same case passed using the existing harness
virtual environment, without installing dependencies. All 186 entries have
passing evidence across these runs. Focused new profile coverage also passed
under existing AddressSanitizer/UndefinedBehaviorSanitizer configuration.
A shared Ninja build emitted a recoverable premature-log warning; the target
rebuilt successfully and the separate sanitizer target passed.

Pi checks passed 5608 backend, 1337 application and 629 production runtime/config
checks, catalog persistence/discovery, USB management and actual USB pair,
Plain TCP, Node and rendered PHP/Chrome workflows. TLS's initial contract run
encountered an unreadable stale test rotation file; the unchanged test was
rerun in a fresh ephemeral directory and passed its credential/settings contracts
and all 34 actual TLS cases. Exact commands are in the Pi record.
Desktop/mobile and light/dark policy controls were inspected in two bounded
rounds; focus and overflow checks and the Impeccable detector passed.

First adversarial self-assessment found misleading host Save guidance: Setup
has autosave and no separate Save action. Removed the proposed active-form
preset, corrected guidance/docs, retained the fleet-only explicit-save preset,
and reran affected checks. Fresh second self-assessment traced all defaults,
old/custom-value preservation, real ARM requests, above-limit refusal and
prelaunch aging, save/apply semantics and unchanged timing/capacity source.
No actionable findings remain. This is self-review, not an independent review.

## Documentation and qualification boundary

Updated the investigation's policy status and USB management policy explanation.
The normative WTP protocol, firmware clock/engine and standalone architecture
remain unchanged because they already support explicit bounded job admission.
Pi updates its configuration, network, Pi operation, USB and review documents.
The separate WsprryPi-Docs operator repository was reviewed read-only; exact
INI/CLI/Transmitter page and screenshot follow-ups are recorded in the Pi review
and remain outside this two-repository write scope.

No physical board was flashed or armed in this pass; no RF, installed Pi
application/service, host clock or device settings were changed. A fresh physical
USB/inhibited ARM test remains separate optional acceptance. The earlier
17.686–18.235 ms USB uncertainty measurements do not qualify absolute UTC offset,
RF launch accuracy or a 1 ms path. Firmware release rebuilds are unnecessary
for this tests/docs-only Pico change. Publication hashes, verified remote
parity, working-tree state and fresh CI status are reported after push.
