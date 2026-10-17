# P15.9 originating post-execution adversarial assessment

Date: 2026-10-17. Lead: WsprryPi. Implementation and repairs: WsprryPico.

## Decision and source boundary

The originating assessment is complete within the supported software scope.
One P1 and three P2 findings were reproduced, repaired and reassessed. A fresh
independent reviewer found no unresolved actionable finding in the repaired
software diff. This closes WsprryPi item 15's originating-assessment gate.

Reviewed starting Pico `devel` was
`156dfa16fb73cb599c96409388c34fde4cfa594a`, independently matched to upstream
and remote. Original P15.9 product `56821ac827c901b61f3af83887eb8c447520abb5`,
execution record `29542e40e131b3e0faa5be5522d220f906de4b0f` and P15.12 merge
`227e73c71c0bbda7e1d84565d7d520e0d7a3f1a0` are ancestors. The assessment
examined their actual current implementation and relevant contracts, not only
checklist status. The four pre-existing Pico documentation edits were preserved
and reconciled with this assessment; no unrelated implementation was replaced.
The final repair inputs are hashed below and committed with this record.

Pi remained at `a84010d6c16ac416d52989053ac1f273390a8ab5` during software
validation, with only its pre-existing release checklist edit. Its current
Pico interoperability pin remains P15.8
`804e8a06585ec5a0e650e69fcd71ada398b6cc9f`. No Pi producer, component, UI,
test, fixture, workflow, pin or historical compatibility row was changed.
Pi adoption of saved-progress operations is a separate decision. The two
unchanged Pi pairs recorded in the original execution evidence apply to exact
Pico product `56821ac`; they are historical evidence, not newly tested pairs
for this repair or the later P15.12 integration.

## Findings, reproductions and repairs

| Severity | Finding and reproduction | Repair and regression | Disposition |
| --- | --- | --- | --- |
| P1 | A failed real progress-journal append latched `Progress`/`Store` unhealthy, but direct qualified-band WTP LOAD could still reach preparation. The new test failed before repair at the accepted-LOAD assertion. | `FrequencyPolicyEngine` now refuses unhealthy preparation and rechecks health at schedule/begin. Five direct modes at qualified 3,570,100 Hz cannot reach raw prepare/schedule/begin after failure. A fault between preparation and launch also refuses output; disable, poll and output observation remain available. Applied config and watermark are preserved. | Closed |
| P2 | With a delayed invalid or cleared acknowledgement and a newer browser edit, both pages claimed the earlier value was saved. The real `saveProgressFields` path reproduced the invalid case before repair. | Shared outcome presentation retains saved/cleared/invalid truth alongside the newer-unsaved qualification. Current text/edit serials remain retained; earlier rejection does not mark the new value invalid. Real production engineering and public AEAD browser workflows hold and release invalid/clear replies. | Closed |
| P2 | Authenticated consumer reported-power selection contained only numeric options, preventing an operator from explicitly clearing an existing value. The new native-option assertion failed before repair. | Add the existing empty-choice pattern. The actual select saves null, blocks incomplete application, preserves profile/config/restart state, and subsequently accepts explicit 0 dBm. | Closed |
| P2 | After an uncertain public callsign-only save, readback preserved edits but omitted all present saved values when the station was incomplete. Review could enable a new save without showing the saved callsign. | Summary always displays the authoritative station tuple and explicit missing components. A second actual public commissioning browser changes saved callsign to BB1BB; first page retains DD3DD edits and displays saved BB1BB before review. Read/review repeats neither save and does not attribute the lost reply. | Closed |

No new schema, journal format, flash allocation, complete-config validator,
profile authority, scheduler or WTP wire operation was introduced by these
repairs. No global WSPR-station requirement was added to externally encoded
jobs. Existing STOP, expiry, ownership, frozen-pair, consumed-slot and explicit
application boundaries remain in force. The admitted operation still needs its
own valid configuration; saving progress does not establish readiness.

## Validation and exact commands

Hardware-free execution used macOS with the repository's Xcode setup for Pico
host code, Node 26.12.0 and Chrome 155.0.8059.82. No WsprryPi C++ was compiled
or linked on macOS. Logs and screenshots are retained under
`/private/tmp/wsprrypi-p159-postreview`; they are local evidence, not committed
release artifacts. The source regressions below are durable and reproducible. Commands use
`P159_MBEDTLS_PATH`, `P159_LWIP_PATH`, `P159_SDK_PATH`,
`P159_PICOTOOL_PARENT` and `P159_PICOTOOL_SOURCE` for the verified retained
checkouts rather than committing local SDK paths. Actual resolved paths and
invocations remain in the retained configure/build logs.

```sh
source scripts/xcode_env.sh
cmake -S . -B /private/tmp/wsprrypi-p159-postreview/host -G Ninja   -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON   -DWSPRRY_PICO_BUILD_FIRMWARE=OFF   -DWSPRRY_PICO_TEST_MBEDTLS_PATH="$P159_MBEDTLS_PATH"   -DWSPRRY_PICO_TEST_LWIP_PATH="$P159_LWIP_PATH"
cmake --build /private/tmp/wsprrypi-p159-postreview/host --parallel 3
ctest --test-dir /private/tmp/wsprrypi-p159-postreview/host --output-on-failure
node tests/saved_progress_tests.js
node tests/network_browser_tests.js
npm --prefix src/network/bootstrap_web run build
npm --prefix src/network/bootstrap_web test
node tests/progress_browser_integration.mjs   /private/tmp/wsprrypi-p159-postreview/host/consumer_bootstrap_driver   /private/tmp/wsprrypi-p159-postreview/visual
```

Final results: 200 executed host groups passed out of 201 registered (one optional schema group skipped). Shared closed-response/outcome checks passed
43 assertions; network browser checks passed; all 17 bootstrap Node test groups
passed. Genuine served-page carrier/crypto tests passed, including callsign-only
beside blank QRSS, mixed errors, null versus zero, explicit application,
reconstructed journal/runtime reload, future malformed replies, delayed
saved/rejected/cleared replies, second-browser concurrent changes and sent-once
recovery. The engineering mTLS and board/TCP boundaries remain explicit doubles.
These are not target transport or physical RF observations.

The same host configuration in `sanitize` added
`-fsanitize=address,undefined -fno-omit-frame-pointer` to C/C++ flags and
`-fsanitize=address,undefined` to linker flags. The affected executables and both
production carrier drivers were built. With `ASAN_OPTIONS=detect_leaks=0` and
`UBSAN_OPTIONS=halt_on_error=1`, all 13 groups passed:

```sh
cmake --build /private/tmp/wsprrypi-p159-postreview/sanitize --target   frequency_policy_tests progress_tests bootstrap_http_tests owner_claim_crypto_tests   consumer_bootstrap_driver consumer_session_driver consumer_profile_tests   reset_storage_tests network_tests --parallel 3
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 ctest --test-dir /private/tmp/wsprrypi-p159-postreview/sanitize --output-on-failure   -R '^(frequency_policy_tests|progress_tests|saved_progress_browser_tests|progress_sessions|bootstrap_http_tests|owner_claim_crypto_tests|consumer_profile_tests|reset_storage_tests|network_tests|consumer_commissioning|consumer_sessions|consumer_recovery|organization_routes)$'
```

LeakSanitizer is unsupported here. The optional `config_update_schema` CTest
remains skipped because Python `jsonschema` is unavailable; the separate progress
schema checks use real production read/ack samples (44 checks). Existing nested
fixture prerequisite skips remain as reported by their own suites.

## Firmware and resource bounds

Both images compiled/linked with retained SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, Arm GCC 15.3.1 and picotool
`6f6458d792b93685a11423b244a585eaa99eafcf`. Retained dependencies are the
same pins recorded by the original execution: Mbed TLS `0bebf8b`, lwIP
`77dcd25`, cyw43 `055d642`, TinyUSB `86ad6e5` and BTstack `eb0bb8b`.

```sh
source scripts/xcode_env.sh
PICO_SDK_PATH="$P159_SDK_PATH" cmake -S . -B /private/tmp/wsprrypi-p159-postreview/firmware -G Ninja   -DCMAKE_BUILD_TYPE=Release -DWSPRRY_PICO_BUILD_FIRMWARE=ON   -DWSPRRY_PICO_BUILD_TESTS=OFF -DPICO_BOARD=pico2_w   -DPICOTOOL_FETCH_FROM_GIT_PATH="$P159_PICOTOOL_PARENT"   -DPICOTOOL_GIT_REPOSITORY_URL="$P159_PICOTOOL_SOURCE"   -DWSPRRY_PICO_FIRMWARE_VERSION=0.1.0-rc.3-p159-review
cmake --build /private/tmp/wsprrypi-p159-postreview/firmware   --target WsprryPico WsprryPico-StandaloneRF --parallel 3
```

| Image | Text / BSS bytes | Flash end | Margin below `0x103f0000` | Static heap span |
| --- | --- | --- | --- | --- |
| Standard | 2,192,032 / 174,000 | `0x1020eaa4` | 1,971,548 bytes | 301,424 bytes |
| StandaloneRF | 2,207,492 / 329,940 | `0x10212704` | 1,956,092 bytes | 145,484 bytes |

Both retain the 32 KiB main-stack reservation/28 KiB guarded usable contract.
Build-time stack/pool checks passed. These static results do not measure runtime
heap, stack, concurrency, timing, electrical behavior or RF. Existing picotool
C++17-extension and duplicate-library warnings, and host duplicate-library /
section-alignment linker advisories, are retained in the logs.

## Impeccable and adversarial reassessment

Impeccable 4.1.1 context/hardening/craft-floor guidance was applied. Existing
navy/light native-control styling was retained. The genuine browser run captured
41 images across desktop 1280x900, mobile 390x844, light/dark OS preferences and
200% CSS zoom. Representative recovery, delayed-error, mixed-error and complete
states were inspected; keyboard Tab/focus and horizontal-overflow assertions
passed. This product has one light palette; dark preference is not a new theme.
No physical-device, screen-reader or native browser-zoom certification is claimed.
The manual detector on the three changed authored JS files returned `[]`.

Separate independent backend and browser reviewers challenged the original
committed state and reported the four findings above. After repairs, a fresh
independent reviewer audited the full product diff and relevant authority,
persistence, dispatch and recovery boundaries; it independently reran all 43
shared JS assertions and whitespace checks. Final source reassessment found no
unresolved actionable finding. Its source review is distinct from the lead's
compiled/browser/sanitizer/firmware runs. Test-harness-only synchronization and
concurrent-browser extensions were then exercised successfully without changing
reviewed product inputs.

## Failed attempts and corrections

- The new qualified-band admission regression failed before the health repair;
  the native empty-power option assertion failed before the UI repair.
- Initial browser/direct-session commands selected `consumer_session_driver`,
  which correctly lacks the public bootstrap surface; the documented
  `consumer_bootstrap_driver` was then used.
- New recovery cases initially left a newer unsaved edit before the separate
  reload case, triggering the real navigation guard. The test now explicitly
  clears/saves that edit; it does not bypass the guard.
- The old keyboard assertion initially followed an intentionally incomplete
  cleared draft. It now verifies Apply is disabled, explicitly completes the
  draft, then verifies keyboard access to enabled Apply.
- An attempted ordinary consumer login during network-only commissioning was
  correctly refused. Concurrent recovery now uses a second actual public AEAD
  commissioning page, preserving that authority boundary.
- One full host invocation omitted `source scripts/xcode_env.sh`; three groups
  failed with the known CLT TAPI/linker mismatch. The corrected full invocation
  is recorded separately. No test assertion, timeout, schema or identity guard
  was weakened to obtain a pass.

## Documentation Impact and residual scope

Updated: this originating record, the original P15.9 execution status, technical
handoff metadata and development/implementation-plan references. The Pi record,
saved coordinating prompt metadata and release checklist close the originating
gate separately. Original execution history remains source-bound and historical.

Considered unchanged: saved-progress schema/contracts already require the repaired
health and truthful-state behavior; complete APIs and profile authority retain
their existing semantics. Pi code, its P15.8 pin/history and Docs repository
remain unchanged. The nonblocking P15.8 Type 1 explanation wording follow-up is
still separate and was not broadened into this repair.

Still required separately: a Pi/Beta adoption disposition before affected freeze,
P15.14 operator text/screenshots for standalone draft/saved/applied/readiness and
uncertain-write recovery, and P15.13 physical qualification. Exact operator-doc
follow-ups remain in the original execution record. This assessment does not
publish operator documentation, advance Pi adoption or establish Beta readiness.
No hardware, flashing, installation, service, GPIO, RF, release, tag, PR or
other-conversation message was performed.

## Final reviewed software inputs

| Path | SHA-256 |
| --- | --- |
| `src/standalone/frequency_policy_engine.cpp` | `c0e394308ddfe33cfaefb37a7d9daac2d84a2b85d323bdf576d9edfb3666c5a8` |
| `src/standalone/frequency_policy_engine.hpp` | `2b54367d5e85b1ddd2b49f1edb97cece346d4cc4196bd1a9f4eb14228047728a` |
| `src/network/web/app.js` | `72d231d4d4afe8bc1e7bc5705da5f959a3db9777faa34a021dbbbc476e451a9b` |
| `src/network/web/saved-progress.js` | `eafe6ce2722aea27873c5971400d760719f46e373faae2aa7bd515b21531dab4` |
| `src/network/bootstrap_web/owner-app.js` | `d30e768b8db7b0031b8e5b57fa88345016bd77622738aaa6646dd093fddfd34a` |
| `src/network/bootstrap_web/owner-bundle.js` | `fa2d76a0254ca6547ccec1ab7ab705b9384c7cca976bed47baaae9449450d9f1` |
| `tests/frequency_policy_tests.cpp` | `cd937118c32579f37f654533bea64fa810b8155bd334383bbf2a5b6c3140ba7c` |
| `tests/saved_progress_tests.js` | `c0b6d972d0d4a73f5a9a5c6bc88d7412cc4e28b5ee287bca1e405b9a3356db23` |
| `tests/progress_browser_integration.mjs` | `3df3c73f02773e3653d30e67cbffd24962c86e5bef0e597ad9153d12639a2712` |
