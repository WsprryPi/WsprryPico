# Issue 447 implementation and adversarial review

Date: October 15, 2026. Scope:
[WsprryPi #447](https://github.com/WsprryPi/WsprryPi/issues/447), implemented in
WsprryPico from `dfffdd5220db8b7cf1acf5e74950dbd294283c55` on
`codex/issue-447-config-preservation`. The
[execution prompt](issue447-execution-prompt.md) records the selected contract.

## Delivered behavior

Ordinary legacy Config v1 PUT preserves omitted saved pins, both advanced
frequency flags, expiry and the Wi-Fi time server. Initial setup, durable
decoding, canonical serialization and Console CONFIG replacement retain their
previous defaults. Explicit supplied false/default values still reset settings.

Capabilities advertise `POST /api/v1/config/update`, independently versioned
`transmitter-config-update/1`, merge/replace modes, 2,048-byte request and
1,800-byte complete-result limits. Merge preserves omitted known fields and
station/Wi-Fi leaves. Arrays replace atomically; pins remain complete plans.
Replace intentionally defaults omitted optionals. Password null preserves
existing credentials in both modes. No generic null deletion or PATCH exists.

The complete candidate passes existing validation, profile authority and
Scheduler CONFIG/verified journal persistence. Existing revision/target,
ownership, activity, fault, pending transaction, STOP, cursor and pin-restart
boundaries remain authoritative. Post-commit output-disable failure now returns
its actual application error on every configuration route.

The [migration and behavior table](configuration-updates.md),
[closed schema](../protocol/transmitter-config-update-1.schema.json) and
[22 vectors](../protocol/transmitter-config-update-1-vectors.json) define the
contract. The existing signed 32-bit integer-token bound is retained; this
feature does not change the shared WTP JSON parser.

## Evidence and compatibility boundary

The legacy producer fixture is byte-identical to Pi revision
`8454e21429c89401b1b9fb5f47a5e15276b86763`,
`WsprryPi-UI/data/wtp-management.js`, SHA-256
`08639d74049de9c9f66890423bd339cc86eaf328bce9a9004a42aeaec628f963`.
MIT attribution is retained; provenance metadata and a runtime hash check bind
the fixture. Its actual registered Load/Save JavaScript handlers receive the
actual Pico GET response and ETag, edit callsign and emit their legacy request.
That request reaches the actual BrowserApi and flash-journal test adapter;
authoritative reload verifies pins, flags, password and consumed-slot cursor.
DOM and HTTP delivery are mocked. No Pi adapter, physical flash or browser
rendering is represented by that software test.

Additional tests remove every optional individually and in combination, check
actual advertised capabilities, password preservation in explicit replacement,
complete-result validation and exact request boundaries. They exercise paged
input, duplicates including escaped duplicates, unsupported values/versions,
stale/ABA/reboot/target contexts, serialized stale writers, ownership and active
jobs, pending network/restart/setup, consumer profile identity, blank/preclock
field admission, uncertain output and post-commit failure. Nine journal-program
cut points distinguish unchanged old records, rejected torn records and fully
committed reload while preserving cursor bytes.

| Source pair or carrier | Evidence |
| --- | --- |
| Unchanged Pi producer at `8454e21` to new Pico handler | Actual emitted request, complete validator and journal reload pass |
| Engineering BrowserApi | Actual request handling, capabilities, admission and persistence tests pass |
| Authenticated field Configure | Existing authenticated dispatch tests include the new POST and blank/preclock denial |
| Consumer-Radio | Existing authenticated inner dispatch includes POST, profile-owned identity rejection and setup exclusion |
| Updated Pi adapters / old and new Pico combinations | Not implemented or claimed here; [#448](https://github.com/WsprryPi/WsprryPi/issues/448) remains open |
| Firmware / physical transport / RF | Not exercised by this change; no qualification claim |

WTP/1 schemas, framing, messages and job semantics are unchanged. USB, BLE and
plain LAN WTP do not become JSON configuration carriers. No Pi source, UI
presentation, canonical interoperability pin, provisioning, RF engine or SDK
source changed.

## Validation

All C++ compilation and execution used isolated Linux ARM64 checkouts with
history preserved for history-aware regressions. No native macOS C++ build,
tool installation, dependency download, firmware load, service change, Pico
operation or RF transmission was used.

The documented baseline command was:

```sh
CMAKE_BUILD_PARALLEL_LEVEL=2 bash scripts/check_host.sh
```

Baseline result: 162/164 passed before resolving a retained JavaScript dependency
gap. Supplying the existing pinned `@noble/curves`, `@noble/hashes` and
`@noble/ciphers` 2.3.0 packages made `recovery_web_tests` pass on both baseline
and candidate. Packages were copied from existing dependencies, not installed.
The remaining baseline failure is described below.

The expanded candidate configuration reused clean retained Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` and lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95` through
`WSPRRY_PICO_TEST_MBEDTLS_PATH` and `WSPRRY_PICO_TEST_LWIP_PATH`.
This enables existing real TLS and pinned lwIP host checks. The final commands
from the candidate root were:

```sh
cmake --build build/host-debug --parallel 2
ctest --test-dir build/host-debug --output-on-failure
```

Final result: **185/186 pass**, with the same baseline RF-adapter fixture failure
below. There are no skips in this run. Compiler: Debian GCC 14.2.0; CMake 3.31.6;
Node 20.19.2; existing jsonschema 4.19.2.

Focused checks use:

```sh
cmake --build build/host-debug --parallel 2 --target \
  config_update_tests consumer_radio_tests softap_api_tests
ctest --test-dir build/host-debug --output-on-failure \
  -R '^(config_updates|config_update_schema|config_update_legacy_pi|consumer_radio_tests|softap_api_tests)$'
```

All five entries pass, including all 22 schema/raw-handler vectors and the
unchanged Pi producer. The schema test uses the existing Python jsonschema
installation; if unavailable it reports an explicit CTest skip (77), never
installs it. Node availability controls registration of the real-producer test.
Both were available and ran here.

Following the existing targeted sanitizer workflow:

```sh
cmake -S . -B build/issue447-sanitize -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined'
cmake --build build/issue447-sanitize --parallel 2 --target \
  config_update_tests consumer_radio_tests softap_api_tests application_resource_tests
ctest --test-dir build/issue447-sanitize --output-on-failure \
  -R '^(config_updates|config_update_schema|config_update_legacy_pi|consumer_radio_tests|softap_api_tests|application_resources)$'
```

All six targeted ASan/UBSan entries pass, including the final additional
capability, individual-omission and replacement-password assertions.

Retained complete-run log SHA-256 values (logs remain outside Git):

| Run | SHA-256 |
| --- | --- |
| Original baseline | `96a18fe30c152b12e7ff601a71b1450e29fd8f8eb9edbc3c9f3cf6c646f94a55` |
| Final expanded candidate | `277479e1df8511d3c038e79587526daa37878331cb89fe87e3bb021cc7287353` |
| Final affected sanitizers | `c9520e35f059fea1c7c31e5d9befb3845c452968e40acc95cbadc03120eb9a27` |

Other checks pass:

- `python3 scripts/validate_wtp_contract.py`: 23 schema, seven raw JSON,
  one framing and eight transition cases.
- `node --check tests/legacy_pi_config_request.js` and Python syntax checks.
- JSON syntax, changed-document local link targets and `git diff --check`.

### Retained baseline failure

`phase12_rf_adapter_tests` fails on both unchanged baseline and candidate when
its Python source-extraction fixture compiles an obsolete minimal stand-in
`PicoBootstrapServer`. Current unchanged dispatch refers to consumer LAN/setup
members absent from that stand-in, including radio/network/transaction state
and response helpers. The fixture compiler exits 1 before its assertion runs.
No affected source path or fixture was changed to conceal it. The full suite
is therefore not claimed green. This does not invalidate passing WTP,
configuration, storage, transport, TLS or sanitizer checks, but remains an
aggregate validation limitation.

## Adversarial assessment and repairs

Implementation testing found and corrected two issues before independent review:

1. Legacy request bytes must include trailing whitespace in the 1,800-byte
   bound. Check the actual incoming body before candidate reconstruction;
   the oversized whitespace case now rejects atomically.
2. A draft schema allowed expiry beyond the existing parser's signed 32-bit
   token limit. Retain the parser, correct the schema/documentation and add
   both the largest accepted token and rejected out-of-range vector.

An independent read-only reviewer inspected the full tracked diff, new source,
tests, exact producer provenance, schemas/vectors and documentation. It
challenged omission/reset behavior, nested/closed validation, duplicates and
bounds, target/revision/ABA, consumer/field authority, ownership/restart/STOP,
cursor/journal ambiguity, redaction and capability claims. The reviewer
independently verified the fixture SHA against the actual Pi Git object.
Its first assessment found **no actionable in-scope findings**.

A fresh assessment of the final added capability, individual-omission and
replacement-password assertions also found **no actionable findings**. The
reviewer did not rerun C++ tests or operate hardware; runtime results are from
the separate Linux runs recorded here. Final record/merge claims are checked
before publication.

## Documentation Impact and remaining gates

Updated: browser API, standalone defaults/flags/expiry, pin persistence,
shared-application contract, configuration-update schema/vectors/migration,
development index, P15.1 implementation status and this prompt/review record.

Considered unchanged: WTP/1, durable Config v1 parsing/bytes, existing
provisioning and historical physical acceptance. No UI presentation changed;
Impeccable rendering is not applicable to a byte-identical test producer.

The separate Wsprry Pi operator-documentation repository was inspected for
impact but not modified. In WsprryPi-Docs,
`docs/User_Interface/Setup/Transmitter/index.md` and
`docs/Advanced_Operations/ini_configuration/transmitter_backends.md`, plus
applicable desktop/mobile screenshots, should be reviewed with #448's actual
client/UI adoption. Current Pi UI controls have not changed here.

Pico-owned implementation is complete. Paired Pi adoption, old/new supported
version evidence and the canonical integration-pin refresh remain #448 gates.
Keep #447's joint integration closure open until that linked evidence exists.
This record grants no firmware, hardware, RF or general release qualification.
