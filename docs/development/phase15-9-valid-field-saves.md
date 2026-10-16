# P15.9 — Independent valid-field saves

Status: **Pico supported software acceptance complete, 2026-10-16.**
Implementation, repairs, exact source-pair checks and publication are recorded. Overall P15.9 remains
subject to WsprryPi release checklist step 15 and its separate assessment.
WsprryPi coordinates; WsprryPico owns this implementation. No physical operation,
Pi feature/devel adoption, release, tag or PR is implied.

## Scope and source identities

The authorized saved prompt is WsprryPi's
`release_tools/P15.9 Valid Field Saves Prompt.md`. The prerequisite
[source review](phase15-9-execution-prompt.md) and repository contracts were read.
The operator explicitly selected an isolated Pico checkout, integrating after
P15.11. Initial isolated base was `7cbc9374218fe5d534b067216ca2c555a20240b9`;
implementation was three-way integrated onto P15.11 acceptance
`90b624b206d387187ca087b139a5cae4fd21ab00`, then fast-forwarded to its final
documentation closeout `f93f19bf5f6b8478d4428c07accf444390e4aa8c`.

Work checkout: `/private/tmp/wsprrypico-p159-integrated`, branch `devel`.
The primary Pico checkout subsequently acquired independent P15.12 changes;
those are preserved and excluded. Pi `devel` remains
`a84010d6c16ac416d52989053ac1f273390a8ab5`, with its existing modified
`release_tools/Release Punchlist.md`. No Pi files/pins/history are changed.
Accepted historical P15.8 companion:
`6d5e73430bfbacdb8cfc29c3fe41089aa8ae5fcb`. Existing compatibility history is
retained; no pin advance or historical-row rewrite is in this scope.

## Reproduction and selected model

A pre-change production HTTP/crypto fixture and its genuine served page reproduced
the callsign-only refusal: native required locator validation blocked submission
while blank QRSS controls were in a separate form. No profile write occurred.
`tests/progress_browser_reproduction.mjs` retains that manual baseline probe;
it is intentionally not a current-product CTest. Software reproduction does
not establish the cause of the original physical incident.

The preimplementation design selected a separate bounded journal because neither
complete Config v1 nor ConsumerProfile can safely represent partial identity.
It distinguished browser edits, durable incomplete/complete progress, applied
Config/profile, boot-active settings, schedule enablement/STOP, operation
readiness, ownership/job state and actual output. The implementation preserves
those distinctions. Completing, reloading, logging in, reconnecting, previewing
or rebooting a draft does not apply it. Enabled schedules retain their previously
applied values and suspension. Explicit application re-enters existing complete
configuration or transactional profile authority.

The [saved progress contract](saved-progress.md) specifies the selected units,
omission/null/zero/false semantics, byte and flash bounds, secret handling,
reset/rollback, additive discovery, closed read/update/apply resources, AP-only
AEAD commissioning, common revisions, explicit domains, and sent-once recovery.
The [structural schema](../protocol/transmitter-progress-1.schema.json) is
supplemented by production semantic validation; it does not claim to encode
all byte, field, uint64, authority or cross-field constraints.

## Implementation

- `standalone/progress.*`, storage health attachment, two reserved sectors and
  reset cleanup persist non-runnable valid fields in one verified accepted batch.
  Existing complete-record formats and flash addresses stay fixed. Diagnostics
  scratch `0x3f2000` remains reserved; new draft region is `0x3f0000..0x3f2000`.
- Browser API and every dispatch layer explicitly classify/read/save/apply the
  new negotiated resource. The scheduler, Console and old complete APIs never
  consume it. WSPR syntax/encoding, profile ownership, trials, delivery, frozen
  pairs, STOP, slot watermarks and restart/output admission remain authoritative.
- Public AP commissioning has station-only encrypted progress with distinct
  AEAD context, one-use/revision-bound slots and redacted readback. Explicit
  saved-station application uses existing claim/profile commit authority.
- Authenticated consumer and engineering pages report accepted, cleared and
  invalid units locally; keep invalid/newer edits; distinguish blank/zero;
  separate Apply; and require readback/review after uncertain writes. P15.11's
  task areas and history navigation remain. QRSS Load/arm remains separate.
- Generated assets stream UTF-8-safe literals below 64 KiB while CSP hashes the
  exact full executed script. Tests check storage-literal bounds at the generated
  C++ layer and exact full HTTP length/order/CSP at the transport layer.

## Validation commands and evidence

Host: macOS/Apple Clang 21 via `source scripts/xcode_env.sh`; Node 26.12.0;
Chrome `155.0.8059.40`. No WsprryPi C++ was compiled or linked on this Mac.
Retained Mbed TLS: `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` (clean).

```sh
source scripts/xcode_env.sh
cmake -S . -B build-host -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/Users/lbussy/GitHub/pico-sdk/lib/mbedtls \
  -DWSPRRY_PICO_TEST_LWIP_PATH=/Users/lbussy/GitHub/pico-sdk/lib/lwip
cmake --build build-host --parallel 3
ctest --test-dir build-host --output-on-failure
node tests/network_browser_tests.js
node tests/saved_progress_tests.js
npm --prefix src/network/bootstrap_web test
python3 scripts/validate_wtp_contract.py
node tests/progress_browser_integration.mjs build-host/consumer_bootstrap_driver OUTPUT
```

The final full host run passed all **199 executable groups** (200 registered;
`config_update_schema` skipped because optional `jsonschema` is absent), in
103.36 seconds. The new progress structural schema separately passed **44 checks**
against actual production read/ack resources using the existing repository
evaluator. Focused progress persistence/API tests passed **246 explicit assertions**.
Bootstrap/npm passed **17/17**. WTP/1 passed 23 schema, 7 raw JSON, 1 framing and
8 transition cases. Final genuine browser functional run passed with zero extra
captures; confirmation evidence is the separately inventoried 29-image pass.

Focused progress tests cover independent/mixed saves, exact powers, same-value/
A-B-A revisions, explicit clears, coupled-unit rejection, legacy atomic failure,
Console/preview/reconstructed-store non-promotion, domains, enabled/STOP/cursor
preservation, redaction/null-password preservation, corruption, invalid receipt,
reset and each interrupted page during append/bank rollover. Reset tests attach
actual Progress and reconstruct/resume all existing coordinator checkpoints plus
both draft-bank erase failures at provisioning/full levels, checking synthetic
secret absence. Genuine three-client progress sessions perform 35 assertions;
closed response/ack validation performs 32 assertions. Existing P15.8 and lifecycle
suites retain their planner, requested-call hash, frozen-pair, expiry, restart,
output and ownership coverage.

ASan/UBSan use a separate `build-sanitize` with both C/C++ flags
`-fsanitize=address,undefined -fno-omit-frame-pointer` and linker
`-fsanitize=address,undefined`. Both production carrier drivers and affected
executables are built. Run with `ASAN_OPTIONS=detect_leaks=0`
`UBSAN_OPTIONS=halt_on_error=1`; macOS LeakSanitizer is unsupported. All **12 affected groups passed** in 12.15 seconds. The affected
12 groups are progress, closed browser resource, progress sessions, bootstrap
HTTP, owner AEAD, consumer profile, reset storage, network API, commissioning,
consumer sessions, recovery and organization routes.

Exact affected sanitizer invocation (after configuring the same retained
Mbed TLS/lwIP paths as the host build, with the sanitizer flags above):

```sh
cmake --build build-sanitize --target progress_tests bootstrap_http_tests \
  owner_claim_crypto_tests consumer_bootstrap_driver consumer_session_driver \
  consumer_profile_tests reset_storage_tests network_tests --parallel 3
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
ctest --test-dir build-sanitize --output-on-failure \
  -R '^(progress_tests|saved_progress_browser_tests|progress_sessions|bootstrap_http_tests|owner_claim_crypto_tests|consumer_profile_tests|reset_storage_tests|network_tests|consumer_commissioning|consumer_sessions|consumer_recovery|organization_routes)$'
```

Firmware uses retained SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, Arm GCC 15.3.1, TinyUSB
`86ad6e56c1700e85f1c5678607a762cfe3aa2f47`, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`, Mbed TLS above, cyw43
`055d64274b014dd7b1c2fc94d26e8a18face7124`, and picotool
`6f6458d792b93685a11423b244a585eaa99eafcf`.

```sh
PICO_SDK_PATH=/Users/lbussy/GitHub/WsprryPico/build/local-sdk-079c6f3 \
cmake -S . -B build-pico -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH=/private/tmp/wsprrypico-p159-integrated/build-pico-tools \
  -DPICOTOOL_GIT_REPOSITORY_URL=/Users/lbussy/GitHub/WsprryPico/build/pico2-w/_deps/picotool-src \
  -DWSPRRY_PICO_FIRMWARE_VERSION=0.1.0-rc.3-p159-candidate
cmake --build build-pico --target WsprryPico WsprryPico-StandaloneRF --parallel 3
arm-none-eabi-size build-pico/firmware/WsprryPico.elf build-pico/firmware/WsprryPico-StandaloneRF.elf
```

Both immutable product images linked successfully. GNU `size` and map results:

| Image | text / BSS bytes | Flash end | Static heap span |
| --- | --- | --- | --- |
| Standard | 2,183,720 / 174,000 | `0x1020ca2c` | 301,424 bytes |
| StandaloneRF | 2,199,180 / 329,940 | `0x1021068c` | 145,484 bytes |

Both flash ends precede the new `0x103f0000` linker ceiling by more than 1.9 MB.
Main stack retains its 32 KiB reservation/28 KiB usable guarded contract. New
static frames include progress readback 3,264 bytes, save 840, and journal progress
save 688; these are per-function compiler figures, not a complete call-chain or
physical high-water proof. Linked flash, BTstack, heap-hook, stack-guard and RF
worker audits passed. Mac host linking retained existing duplicate-core-library
and section-alignment warnings; no source warning was hidden or promoted to a
physical result.

UF2 SHA-256 (local build outputs, not a release or flashing instruction):

- Standard: `f54c4d38ea84bb0b71d4524bf53969f245d3af853c0875b12a06efb226512c73`
- StandaloneRF: `66dfbc9aeaedb666edcdc69dcdc76ad25a0c693b693ebadf64ceabfba6536119`

Linker/static stack/heap instrumentation audits are software bounds only.
Physical heap/stack high-water, flash interruption, lwIP/TLS transport, GPIO,
RF timing, decoding, services, installation and board behavior are unqualified.

## Adversarial findings and repairs

Independent read-only review was repeated against integrated/repaired source.
No finding is closed merely by narrative; relevant current regressions execute.

| Severity / reproduction | Repair and regression |
| --- | --- |
| P1 malformed claim/progress submit could dereference an empty parse result | Guard before dereference; actual granted-slot malformed progress returns 400, wrong legacy operation 403; no crash/write |
| P1 progress opener bypassed authenticated decryption in initial implementation | Common real AEAD decrypt before decoding; independent Noble/Mbed TLS vectors, wrong tag/boot/generation/domain and second-use rejection; genuine browser encryption |
| P1 public save committed but strict acknowledgement rejected hidden outcomes | Public readback exposes filtered station-only outcomes and null receipt; actual callsign-only encrypted save confirms once and survives reconstructed boot |
| P2 null password selected applied secret over a newer draft secret | Prefer saved draft secret; tombstone masks fallback; regression verifies internal candidate and redacted response |
| P2 malformed/future resource or contradictory ack could appear saved | Closed semantic resource/ack checks and exact request/outcome binding; 32 assertions plus genuine future-reply readback/review without replay |
| P2 explicit reload retained serial edits/invalid annotations/preview | Confirmed discard clears edit/dirty/result state and validity, adopts saved progress and refreshes preview; genuine BAD-to-saved-EM18IG check |
| P2 late replies could label newer edits saved | Per-unit edit serials, unchanged text and explicit newer-unsaved feedback; held committed reply in real browser |
| P2 oversized numeric token rejected valid sibling saves at carrier JSON parser | Preserve parser bounds; encode invalid numeric units as text, retain exact native-valid integers including 3e1/30.0; genuine engineering and encrypted mixed-unit regressions |
| Evidence gap: reboot/reset fixtures bypassed new storage | Retain draft flash across runtime reconstruction; attach Progress to reset checkpoint/bank-failure tests, verify credential cleanup |
| UI misleading whole-draft-unsaved preview and checkbox feedback splitting label | Separate preview wording from partial outcomes; place checkbox outcome after complete label; bounded visual inspection and confirmation |

Earlier failed runs remain local evidence, superseded only by identified repairs:
scalar JSON-root misuse, overlong C++ literals, obsolete hardcoded asset-part
count, wrong test-layer script bound, fake event/query-selector gaps, baseline
loopback sandbox refusal, public ack mismatch, missing sanitizer driver,
unsupported LeakSanitizer, and fixture response-delivery/empty-GET synchronization.
The original bounds/identity/deadline assertions were retained at their correct
layer. None was weakened to obtain a pass.

## UI and Impeccable

Impeccable hardening/context/craft-floor guidance was used during implementation,
preserving incumbent navy/light native-control styling. A single batched visual
inspection and one confirmation pass each generated 29 images: seven states,
desktop 1280x900 and mobile 390x844 under light/dark preferences, plus 200% zoom.
This product has one light palette; dark preference is a compatibility check,
not a claimed dark theme. Representative blank/incomplete, mixed-error,
complete-unapplied, engineering and unconfirmed/recovery images were inspected.
Keyboard Tab to Apply and horizontal overflow assertions pass. Final small
preview-reload synchronization is additionally checked behaviorally.

Manual detector ran once across six affected HTML/JS/CSS targets. It reported
DEGRADED regex fallback because parser modules were absent, with seven advisory
palette/type/radius findings in unchanged incumbent CSS. They were inspected as
pre-existing design language, not new regressions; computed contrast was not
claimed. No additional visual redesign/polishing loop was performed.
Local evidence: `/private/tmp/p159-final-visual`,
`/private/tmp/p159-confirm-visual`, and `p159-*.log` under `/private/tmp`.

## Final source-pair and publication results

Immutable product commit: **`56821ac827c901b61f3af83887eb8c447520abb5`**.
Both clean-source guarded Linux pairs passed:

| Unchanged Pi source | Exact Pico source | Result |
| --- | --- | --- |
| Release `a84010d6c16ac416d52989053ac1f273390a8ab5` | `56821ac827c901b61f3af83887eb8c447520abb5` | PASS |
| Accepted P15.8 companion `6d5e73430bfbacdb8cfc29c3fe41089aa8ae5fcb` | `56821ac827c901b61f3af83887eb8c447520abb5` | PASS |

Environment: offline Docker `wsprrypico-p153-env:local`, image
`sha256:c7f2a891a6fff72e84bd1f2130b934881565f8b9ab489b20f35071f321ad219a`,
Debian 13.6/aarch64, GCC 14.2.0, CMake 3.31.6, OpenSSL 3.5.6. Pico, clean Pi
clones, original shared Git objects and retained SDK/Git metadata were mounted
read-only; only `/out` build products were writable. No network was available.
The first configure correctly refused an omitted Mbed TLS Git-metadata mount;
mounting the retained whole SDK read-only repaired the environment without
weakening exact-identity/clean-source guards.

The Pico-owned compatibility extension attaches an incomplete progress draft
before unchanged Pi AP/station read/save operations, verifies no promotion or
draft mutation, and preserves the complete original native suite. It changes
no Pi producer, pin or expected historical profile. Results include original
OpenSSL/Mbed TLS AEAD/recovery vectors, Type 2/3 readback, strict coordinator
admission, management-only behavior, hostname preservation and incomplete-draft
preservation through both authenticated carriers.

Inside that container (select `pi_root`/`pi_pin` from the table):

```sh
pico_root=/private/tmp/wsprrypico-p159-integrated
pico_pin=56821ac827c901b61f3af83887eb8c447520abb5
cmake -S "$pico_root/tests/hostname_pi_compatibility" -B "/out/$pair" \
  -DPI_SOURCE="$pi_root" -DEXPECTED_PI="$pi_pin" \
  -DPICO_SOURCE="$pico_root" -DEXPECTED_PICO="$pico_pin" \
  -DMBEDTLS_SOURCE=/Users/lbussy/GitHub/pico-sdk/lib/mbedtls
cmake --build "/out/$pair" --parallel 3
"/out/$pair/hostname_pi_compatibility" \
  "$pico_root/docs/protocol/Consumer-Radio-v1-vectors.json"
```

The exact runner and configure/build/test logs are retained under ignored
`build/phase15-9-linux/`; all other final logs are `/private/tmp/p159-*`.
Full host log: `p159-final-host-tests.log`; sanitizer: `p159-acceptance-sanitize.log`;
genuine browser: `p159-acceptance-browser.log`; firmware:
`p159-immutable-firmware.log`. Prior failed logs are superseded, not erased.

`git push origin devel` successfully published the product commit without force;
independent `git ls-remote origin refs/heads/devel` returned the exact product
hash. The immediate post-push GitHub queries returned zero checks/runs; a later
exact-head refresh found [Pages run 38983934693](https://github.com/WsprryPi/WsprryPico/actions/runs/38983934693)
completed successfully at that product hash, with successful build, deploy and
report-build-status checks. No checked-in software-test workflow exists; the
only remote workflow is GitHub's dynamic `pages-build-deployment`, not
firmware/test CI. **Only Pages CI success is claimed.** This evidence-only
closeout changes no tested product source. Its
own final push/parity and exact-head checks are reported in the coordinating
chat, avoiding a self-referential report-commit identity.

Independent reassessment after all source repairs found no remaining actionable
finding. It reran the 246 progress assertions, 32 closed-resource assertions and
35 session assertions and inspected confirmation desktop/mobile evidence. The
originating conversation's separately requested post-execution assessment still
has not occurred. No background work or cross-chat message was scheduled.

The isolated devel checkout was clean at product publication. The primary Pico
checkout remains on its own devel base with P15.12 edits; those are preserved,
not fast-forwarded over. Primary Pi retains its existing modified punchlist at
`a84010d`; no Pi commit/push, source adoption, compatibility-pin advance,
release/tag/PR, service operation or hardware activity occurred. Overall Pi
checklist step 15 remains a separate coordinating acceptance boundary.

## Documentation Impact

- Updated: this execution record, saved-progress contract, structural schema,
  browser API, architecture, root CONTRACT and development/roadmap references.
- Considered unchanged: frozen complete Config/profile/application v1/v2,
  config-update/1, management, Consumer-Radio/Recovery and WTP/1 contracts, whose
  operations retain their prior semantics; P15.10/P15.11 acceptance is preserved.
- Still required under P15.14: `WsprryPi-Docs/docs/User_Interface/Setup/Transmitter/index.md`
  and relevant setup/index screenshots must distinguish Pico standalone valid
  draft saves from Pi's complete atomic member editor; explain null/zero/mixed
  outcomes, saved tuple versus current invalid edits, explicit application,
  active boot/settings, enabled/STOP behavior and uncertain-write review. Current
  text near automatic WSPR planning (lines 560-562 when inspected) truthfully says
  the Pi member editor does not save incomplete drafts; preserve that distinction.
  Add new Pico standalone captures only when adopted documentation scope permits.
- Operator docs were inspected read-only at `WsprryPi-Docs`; the differently
  named `Wsprry_Pi_Docs` sibling is absent. No operator-doc build/publication,
  Pi release integration or originating conversation assessment is claimed.
