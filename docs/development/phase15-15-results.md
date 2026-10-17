# P15.15 GPIO drive execution record

Status: **hardware-free software acceptance complete**. Broad P15.15
acceptance remains open pending physical evidence. No hardware setup was
declared for this execution. No device load, pad observation or RF measurement
is implied by software results.

## Contract frozen before implementation

| Item | Selected contract |
| --- | --- |
| Owner and units | Standalone Config `gpio_drive_ma`, exact integer 2/4/8/12 mA; default 4; selected direct RF GPIO only. |
| Persistence | Existing Config journal; omit default to retain legacy canonical bytes; absent old records default to 4. Nondefault records require new firmware; unsupported downgrade fails closed. No flash address changes. |
| Discovery | Additive top-level capabilities `gpio_drive`, exact independently versioned descriptor; legacy application capability objects retain `unavailable:drive`. |
| Drive view | GET/PUT `/api/v1/gpio-drive`, `transmitter-gpio-drive/1`; saved, boot-active, verified pad, pending restart, error and target are distinct. |
| Config extension | GET/PUT config/3, POST config/update/3 with update/2 envelope. Legacy config and update views omit/reject drive while preserving saved drive on unrelated writes, while explicit replacement/Console CONFIG defaults omission to 4. |
| Hardware/application | hardware/2 and application/3 embed the independently versioned drive view. Prior closed shapes remain unchanged. |
| Progress | progress/2, update/2, apply/2 use transmitter-progress/2. Legacy views exclude drive and legacy apply never promotes a drive draft. Draft writes never program a pad. |
| Authority | Same identity, boot, If-Match, idle, ownership, profile and journal admission. One candidate and verified commit. No hot application. |
| Activation | Immutable boot pin/drive snapshot; explicit restart; hardware restart latch is sticky including A/B/A. Pad unknown until the RF adapter applies and verifies it. Inhibited image never reports physical programming. |

## Baselines

Both checkouts were clean `devel` with HEAD equal to their local upstream refs.
The accepted P15.14 product pair is Pico
`100e749c815f7485d5097c9086852d3b97adca9f` and Pi
`b2160ca39bed539dfd5d39a0c449dd64d37c53a2`; the USB execution record records
complete scoped acceptance and subsequent documentation/time-policy follow-ups.
The execution baselines are Pico `46b256c636fb44c8ed059000d7b3f3b94cceea9e` and Pi `411883266bfe4bcbf845b3b8f1caabd74851c23e`. Validation used the then-uncommitted implementation identified by its source manifest, not either baseline HEAD alone. The operator subsequently authorized committing and pushing this work on 2026-10-17; the manifest retains the validation baselines and exact tested file hashes.

## Validation and environment recovery

The full macOS host suite selected 189 tests: 188 passed and one existing
optional config-update JSON Schema check explicitly skipped because the optional
`jsonschema` package is absent. No dependency was installed for this task. The new GPIO schema check
uses the repository-owned validator and validates 12 actual service responses
plus legal and malformed vectors, without that optional dependency. The final
coverage also derives version-2 update envelopes from the unchanged legacy
vectors and exercises all four config/3 PUT and config/update/3 merge values;
the two affected checks passed after that test-only extension. Focused
configuration, progress, browser and engineering SoftAP checks are rerun after
repairs. Final commands, resource results and compatibility disposition follow below.

Both normal inhibited and StandaloneRF profiles cross-link with SDK 2.3.1,
Arm GNU 15.3.1 and 138 MHz. Immediate baseline images were independently rebuilt
from a Git archive of the clean execution HEAD. Resource values below are
from the final rebuild; no capacity/assertion reduction was made.

A disk-full failure interrupted the first Linux container and baseline build.
The requested cleanup removed 26,427 regenerable `.o`/`.obj`/`.d` files from old
temporary P15.3-P15.9 test trees and Pi generated object directories, about
7.18 GiB logical bytes. Sources, Git metadata, dependency checkouts, firmware,
captures and logs were retained. A deletion inventory is at
`/private/tmp/p15-cleanup-20261017.json`. The baseline rebuild subsequently passed.

Docker's engine did not recover promptly. Automatic approval initially rejected
a wspr5 source transfer; no source was sent by that rejected command. The
operator then explicitly approved the isolated source/dependency copy to
`/home/pi/p15-gpio-drive-20261017/`. Its deterministic Linux compilation is capped
at two jobs; no installed binary, service, system configuration or hardware is
changed. Source snapshots use Git-listed files; no project Git is initialized.
The loopback harness uses a task-local copy of its CMake preflight, replacing
clean-Git pin checks with recorded immutable archive/source manifests because
commits were not authorized during validation. All runtime/integration assertions remain.
This is explicit snapshot validation, not a passed clean-checkout CI job.
Mbed TLS source is the retained clean SDK submodule at
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`; the SDK and compiler were reused.

## Bounded visual review

Impeccable Operate mode preserved each incumbent interface. The actual Pico
consumer/engineering source document and Pi member section/shipped styles were
rendered at 1280px desktop and 390px mobile widths with connected, sticky pending
restart, failure and unsupported fixtures. Each actual editor dispatched exactly
three deliberate actions: a rejected save, a progress save and explicit progress
application. No selection-triggered write occurred. Draft retention,
unknown readback and horizontal overflow were checked. Visual fixtures do not
exercise crypto, physical USB, pad programming or RF.

The first visual pass found duplicate label/legend presentation and awkward Pi
desktop alignment. Those were removed, storage-error wording was clarified,
long identity readback was allowed to wrap, and the one final confirmation pass
passed on all four surfaces with no page errors. The 40 final captures and
request traces are in ignored `build/phase15-15-visual-final/`. Reviewed captures cover
Pico engineering connected mobile, consumer pending desktop/failure mobile and
Pi USB connected mobile/network pending desktop/unsupported mobile. Saved-progress
views were also inspected after the flex-layout repair. The final source was rendered again after the pending-read and descriptor
guards: all four surfaces passed with three explicit actions, no page errors
and no horizontal overflow. Earlier candidate captures remain retained in
`build/phase15-15-visual/`.

The source-owned bundle generator embeds the new editor into the actually
served consumer/engineering pages and aliases. No generated bundle is the sole
edited source. Wi-Fi bootstrap/owner commissioning pages gain no radio form.

## Adversarial self-review findings and repairs

This is a self-review, not independent review. No subagent was authorized.

- Exact SDK source shows gpio_set_function clears output overrides: initialize
  disabled PIO direction/output-low before function selection, restore forced
  low, and verify explicit named drive mapping before launch.
- Engineering field HTTPS used a separate closed route classifier: add the
  negotiated routes with Configure admission and test authenticated access and
  preclock/session refusal. Consumer and USB retain their existing authority.
- Explicit replacement must retain reset meaning: unlike ordinary legacy PUT,
  deliberate replacement defaults omitted drive to 4. Legacy progress apply all
  excludes drive drafts and preserves the currently saved selection.
- New schema generation initially duplicated legacy schema IDs and an unused
  hardware write variant: use unique new IDs, read-only extended hardware view
  and correct drive-field outcome types; validate actual service responses.
- Register the browser regression with the repository's actual Node variable.
- Saved progress needed a real station-independent browser path as well as the
  resource: add the shared draft save/explicit drive-only apply controls and
  exercise them through USB and protected network paths. A Linux compile found
  a C++ string/JSON comparison mismatch in receipt verification; compare a typed
  string and rerun the protected integration.
- Keep the Pi progress details outside its flex button row to avoid stretched
  desktop action buttons; confirm desktop/mobile views after the repair.
- Invalidate a pending progress read after a member/boot change before accepting
  its response. A dedicated interleaving regression proves the old response
  cannot revive editor authority. Rebuild both served firmware bundles.
- Require the complete descriptor in the Pico browser too, including units,
  engine, write method and every negotiated path; reject incomplete/mismatched
  descriptors in the shared browser regression.
- Include a differing drive draft in progress/2 matches_applied while preserving
  legacy-view meaning. Test false before explicit drive apply and true afterward.
- Legacy progress application must retain its old closed response too. Re-enter
  the old config route with drive omitted and preserved, and assert both the
  unchanged saved selection and absent drive response key.
- Watch the source-owned GPIO editor as a CMake configure dependency in Pico
  and the companion interop build, so regenerated embedded assets follow edits.

No physical board operation has been performed. Pad readback, real restart and
USB re-enumeration, output amplitude/spectra, representative nondefault-strength
RF behavior and setup restoration remain untested. Historical RF acceptance
retains its exact source/drive/setup scope. Broad P15.15 acceptance stays open.


## Software validation and source binding

The [source manifest](phase15-15-source-manifest.json) identifies both unchanged
HEADs, hashes the complete Git-listed product/test/helper trees, lists every
changed product file, and records protocol JSON hashes and immutable historical
archives. Its product tree hashes are:

- Pico: `70d1c51d8e44f52f860c43fcaa135b630921d772f28adc5f7d6dc40926c6f466`.
- Pi: `edc1e872c421c74685b00813b206a7f6f67120f89da06fa7fe624904fd112e5e`.

A file-by-file comparison of 2,033 local and Linux product files found no
mismatches, accounting explicitly for the task-local CMake preflight overlay.
The 957 retained Mbed TLS files match the clean pinned SDK submodule. All
18,234 regular files in the ten historical archives match their immutable Git
archive contents, with no mismatch or source patch.
Documentation is outside that product digest; protocol JSON has separate hashes.
Validation did not update source pins or establish a clean-checkout CI result.

| Check | Actual result |
| --- | --- |
| `bash scripts/check_host.sh` | 188 passed; one optional existing schema check skipped, 189 selected. Log `/private/tmp/p15-host-final4.log`. |
| `python3 scripts/validate_wtp_contract.py` | 23 schema, 7 raw JSON, 1 framing and 8 transition cases passed; WTP/1 unchanged. |
| Final affected configuration/progress/application and GPIO checks | 7/7 passed after the added observation, wrong-boot/unknown/duplicate atomicity, merge/latch and pending-read regressions. |
| Linux Pico selected service checks | Final 8/8 passed; drive, browser, schema, configuration, application and engineering SoftAP. |
| Linux Pi config/USB/shared API/full production | Passed, including 629 production checks with the full built-in backend profile. Expected cleanup-failure logs are injected failure-path cases. |
| Actual UMP1 pair | Passed with `WSPRRYPI_GPIO_DRIVE_REQUIRED=1`; all strengths, versioned large resources, progress save/apply, blank-member draft and existing USB management/time/configuration assertions. Host pipe framing, not physical USB. |
| Linux current pair | Passed engineering TLS, authenticated Consumer-Radio station/AP, all four strengths, drive-only progress, invalid mutation and lost encrypted reply with explicit session recovery. Existing full resource/Type 2/3/crypto concurrency checks passed. |
| Historical pair matrix | All 12 entries passed: current pair, nine retained Pico sources, immutable pre-change Pi with new Pico, and the old P15.14 UMP pair with new Pi. |

Linux host: wspr5, aarch64 Linux 6.18.34, GNU C++ 14, OpenSSL 3.5.7,
libgpiodcxx 2.2.1. All tests are isolated under
`/home/pi/p15-gpio-drive-20261017/`. Production checks use
`WSPRRYPI_DISABLE_HARDWARE_ACCESS=1`; no installed binary or service is exercised.
The metadata header was generated from the real local Pi checkout, then used
with `BUILD_METADATA_ENABLED=0` in the Gitless test snapshot.

Reproduction commands from that snapshot root:

```sh
cmake --build pico/build-host --target usb_management_driver gpio_drive_tests softap_api_tests config_update_tests application_resource_tests -j 2
ctest --test-dir pico/build-host -R '^(gpio_drive|gpio_drive_browser|gpio_drive_schema|softap_api_tests|config_updates|application_resources)$' --output-on-failure
make -C pi/src wtp-config-test wtp-usb-management-test wtp-api-test wtp-production-test wtp-usb-pair-client-build SUDO= JOBS=2 BUILD_METADATA_ENABLED=0
WSPRRYPI_GPIO_DRIVE_REQUIRED=1 node pi/WsprryPi-UI/tests/wtp_usb_pair_test.js pi/src/build/wtp-network/wtp_usb_pair_client pico/build-host/usb_management_driver
make -C pi/src wtp-config-interop-test SUDO= JOBS=2 BUILD_METADATA_ENABLED=0 PICO_SOURCE=/home/pi/p15-gpio-drive-20261017/pico MBEDTLS_SOURCE=/home/pi/p15-gpio-drive-20261017/mbedtls
node pi/WsprryPi-UI/tests/wtp_gpio_drive_interop_test.js pi/src/build/wtp-network
```

## Exact-pair compatibility

The current pair uses the final uncommitted product digests in the source
manifest. Historical Pico and pre-change Pi sources are immutable public Git
archives; their full revisions and archive SHA-256 values are retained there.
The companion test fixtures are current and explicitly distinct from those
historical product sources. No old schema, vector or source pin was rewritten.

| Partner | Immutable revision | Result |
| --- | --- | --- |
| legacy | `95aac22bf7cc31b67fe5773761708d743d8a6473` | Passed |
| extended | `dfffdd5220db8b7cf1acf5e74950dbd294283c55` | Passed |
| p152 | `87144d1364f36d04bfe0a714bd1c2f6deb974302` | Passed |
| p153 | `d6208dbc88005383041c5ec306b738db7ec22796` | Passed |
| p154 | `ddb00dd7960373cec271f7816c0e1b10117416e9` | Passed |
| p156 | `792b5b2f60e381a6bd8e7a7726eeffe24fc08519` | Passed |
| p157 | `26ae596b540e92f25da37f978321ba1ec5934bdc` | Passed |
| reference | `804e8a06585ec5a0e650e69fcd71ada398b6cc9f` | Passed |
| usb-old | `100e749c815f7485d5097c9086852d3b97adca9f` | Passed |
| old-pi | `411883266bfe4bcbf845b3b8f1caabd74851c23e` | Passed |

The retained profiles use their maintained `PICO_COMPAT_PROFILE` values;
`reference` and `usb-old` use `current` with their recorded source archives.
For each profile, the harness runs the actual UI/settings interoperability
test, the applicable native Consumer-Radio vectors, and supported resource and
browser-crypto cases, then the new unavailable-drive test. Older firmware
returns drive unavailable from capability discovery before an unsupported drive
write is sent; unrelated settings remain usable.

Representative commands, with `$profile`, `$build` and `$source` taken from
the row and task root described above:

```sh
cmake -S pi/src/tests/network -B "$build" -DPICO_COMPAT_PROFILE="$profile" -DPICO_SOURCE="$source" -DMBEDTLS_SOURCE="$PWD/mbedtls"
cmake --build "$build" -j 2
node pi/WsprryPi-UI/tests/wtp_configuration_interop_test.js "$build" "$profile" "$source"
node pi/WsprryPi-UI/tests/wtp_gpio_drive_interop_test.js "$build" --unsupported
```

Legacy/extended/P15.2 use `--engineering-only` for the last command. Other
profiles also exercise authenticated Consumer-Radio station/AP. The existing
Makefile conditions determine native vectors and resource/browser tests.

For the reverse pair, the untouched pre-change Pi client and UI fixture use
the final Pico TLS fixture. Its existing Console CONFIG grammar seeds each
drive value; actual unrelated UI saves must preserve 2/4/8/12 mA. This is a
harness executable with recorded generated metadata, not an old release build.

```sh
make -C compat/old-pi/src wtp-config-client-build SUDO= JOBS=2 BUILD_METADATA_ENABLED=0
node pi/WsprryPi-UI/tests/wtp_gpio_drive_interop_test.js compat/old-pi/src/build/wtp-network --legacy-ui compat/old-pi/WsprryPi-UI/tests/wtp_management_fixture.js
```

The test-only build directory contains the new Pico TLS server and its
ephemeral credentials alongside the immutable old Pi client. No product source
in the old Pi archive is patched.

The current-pair GPIO test also checks a fresh progress read between draft save
and apply. Its lost encrypted reply case explicitly expires the test session
and reconnects before reconciliation; it never retries the mutation. These
fixture corrections retain the existing read authorization and login guards.

The retained P15.14 driver passed the actual host UMP pairing test with the new
Pi client, including unavailable-drive handling and existing blank-member,
Wi-Fi/name, independent progress and UTC behavior:

```sh
cmake -S compat/usb-old -B compat/usb-old/build-host -DWSPRRY_PICO_BUILD_FIRMWARE=OFF -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build compat/usb-old/build-host --target usb_management_driver -j 2
WSPRRYPI_GPIO_DRIVE_REQUIRED=0 node pi/WsprryPi-UI/tests/wtp_usb_pair_test.js pi/src/build/wtp-network/wtp_usb_pair_client compat/usb-old/build-host/usb_management_driver
```

The current counterpart uses `WSPRRYPI_GPIO_DRIVE_REQUIRED=1` so missing new
support cannot be silently skipped. Neither pairing test uses a physical USB
device or network connection to a board. All matrix assertions remain enabled.
Logs, profile reports and exact task scripts are retained locally in ignored
`build/phase15-15-linux-logs/` and at the isolated wspr5 task root. The initial
failed test logs are retained separately from the final repaired-pair logs.

### Linked firmware and retained limits

Both immediate baseline and candidate use Pico 2 W, normal 138 MHz,
SDK 2.3.1 (`079c6f39023649b154152db30f1d781e884879bc`) and Arm GNU 15.3.1.
No dependency pin or numeric job/resource limit changed.

| Image | Baseline text / BSS bytes | Candidate text / BSS bytes | Static end to heap limit, baseline → candidate |
| --- | --- | --- | --- |
| Normal inhibited | 2,257,156 / 175,468 | 2,281,116 / 175,492 | 299,956 → 299,932 bytes |
| StandaloneRF | 2,271,816 / 331,404 | 2,296,496 / 331,440 | 144,020 → 143,984 bytes |

These are linked/static values, not measured runtime heap availability. GNU
size's separate data column is zero; the renderer check separately reports
13,976 initialized SRAM bytes. RF worker remains 166,176 bytes, renderer remains
660 bytes / 233 checked instructions, primary stack remains 32 KiB and RF worker
stack remains 16 KiB. Existing linked flash/UF2 reservation, heap-wrapper,
stack-guard, GP14 safety and SRAM renderer checks passed without weakening them.
The existing 512-event bound, AP/USB lifetime and timing admission remain.

Candidate UF2 SHA-256 (built, never loaded):

- Normal: `069319f8e0372cf4355458011a7e0a8a7b61e1f6c46af2a63be5afbc3726097e`.
- RF: `7b580faaa9bbcfd796837c2741ca80dee3dafc8f7a2448c8f7d7756423b6f971`.

Cross-build from the Pico root after the maintained `scripts/xcode_env.sh`:

```sh
export PICO_SDK_PATH="$PWD/build/local-sdk-079c6f3"
cmake -S . -B build/phase15-15-pico -G Ninja -DCMAKE_BUILD_TYPE=Release -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF -DPICO_BOARD=pico2_w -DPICOTOOL_FETCH_FROM_GIT_PATH="$PWD/build/phase15-15-picotool-deps" -DPICOTOOL_GIT_REPOSITORY_URL="$PWD/build/pico2-w/_deps/picotool-src"
cmake --build build/phase15-15-pico --target WsprryPico WsprryPico-StandaloneRF -j 2
```

The pinned SDK audit inspected `hardware_gpio/gpio.c`, its named drive enum,
RP2350 `hardware/regs/pads_bank0.h`, and PIO GPIO function selection. SDK enum
ordinals are 0/1/2/3; the product maps mA explicitly. Only the selected immutable
RF pin is programmed, before PIO output enable, with a sticky getter mismatch.
This source/linked evidence does not replace a target pad observation.

## Remaining physical acceptance

No board, image, cable/RF path, USB device, GPIO or receiver was changed by this
execution. There was no physical restoration attempt or verification.

| Evidence still required | Disposition |
| --- | --- |
| Real selected-pad getter/register for 2/4/8/12 mA, including explicit 4 mA initialization and no auxiliary-pad change | Not run; needs an identified connected board/setup. |
| Nondefault persistence, explicit restart, saved/boot/pad readback and physical USB re-enumeration | Not run; software boot/journal/framing checks do not prove it. |
| Startup/rearm/abort/cleanup behavior on the target, with inactive output and unchanged normal clock | Source and linked checks passed; target observation remains open. |
| Conducted 4 mA comparison with the immediate baseline and bounded loaded-output/spectral checks for the other strengths | Not run; no candidate RF qualification or power ratio claimed. |
| Original image/settings/STOP/schedules/watermarks/RF chain restoration and inactive-output verification after bench testing | Must be recorded with that future finite campaign. |

P15.15 remains open for physical acceptance. P15.16 and subsequent execution,
release publication and the separate documentation site remain outside this
run. The subsequent commit-and-push authorization does not change those gates.

## Final reassessment and repository state

Adversarial self-review was repeated after the repairs above. No actionable
in-scope software finding remains. This was not independent review. Final
software coverage includes host/service/schema/storage/lifecycle checks, the
full Pi production target, all supported management carriers, both linked
firmware profiles and the complete exact-pair matrix. The optional existing
full-Draft config-update schema test remains explicitly skipped; the new
repository-validator checks, including inherited update envelopes, pass.

At the end of validation, both repositories were `devel`, HEAD equal to local
upstream, with no staged files, commit, branch creation, push, PR, tag or
publication. Pico had 32 modified tracked paths and 13 untracked paths; Pi had
15 modified tracked paths and 3
untracked paths. The source manifest inventories product and documentation
paths. Concurrent planning edits in the three Pico planning/index files were
preserved, with only P15.15 status/evidence links added here. The broad checklist
remains in progress. PHP syntax checks and documentation-link/diff checks pass.

## Documentation Impact

Updated versioned GPIO/config-update/application/progress schemas and vectors,
configuration/progress/API/USB development contracts, this execution record,
companion Pi drive/USB documentation, and the
[P15.20 operator handoff](phase15-15-documentation-handoff.md). WTP/1 and prior
closed schema/vector fixtures remain unchanged. The separate documentation site,
release, default-target switch and later phases remain untouched. Concurrent
planning edits in the development index, plan and prompt index are preserved.
