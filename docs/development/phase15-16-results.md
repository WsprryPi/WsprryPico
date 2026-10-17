# P15.16 normal firmware default

Executed 2026-10-17. Complete within the software/build scope recorded here.
Independent adversarial review, repair, affected retesting and clean
reassessment are complete. This record does not
claim physical USB, RF, timing or release qualification for the new images.
The [executed prompt](phase15-16-execution-prompt.md) defines the bounded scope.

## Accepted baseline and unchanged contracts

Entry was clean `devel`, HEAD and local upstream both
`33f3d5ce7093a853a667f18dd157f46c8c945ecd`. P15.14 is accepted in the
[USB record](usb-control-results.md), including its later UTC follow-up.
P15.15 is accepted within the [hardware record](phase15-15-hardware-results.md):
Pico product `d6de1f3cf14dc49266c4401c3bca91b8ce9da688`, Pi companion
`fe701cf4c2b05e46cb84927188984084503d1cea`. Entry Pico HEAD contains that product
and the later tools/evidence closeout; Pi remains at that exact companion.
P15.15's failed numerical spectral screens retain their explicit nonblocking
operator disposition. They are not renewed RF evidence or a prerequisite here.

No application, encoder, RF renderer/worker/driver, USB implementation, saved
configuration, journal layout or protocol JSON was changed. In particular:

- WTP payload 65536 bytes; 512 events; complete-job duration 3600 seconds;
  Config 1800 bytes; scoped update 2048 bytes; profile 7168 bytes.
- Consumer session/pending capacity 3/1; ARM maximum uncertainty 500000000 ns;
  holdover maximum age 90000000000 ns; clock windows 90/180 seconds. Pi's new/
  missing-settings 100 ms default and explicit saved limits are unchanged.
- Existing 32 KiB control reserve, memory admission and WTP-priority reclaim;
  32 KiB core-0 stack with 4 KiB guard; dedicated 16 KiB guarded worker stack.
- Persisted `gpio_drive_ma`, explicit 4 mA default, 2/4/8/12 mA choices,
  immutable boot/pad observation and saved-versus-active restart semantics.
- Saved progress at `0x3f0000`, diagnostic scratch `0x3f2000`, access `0x3f3000`,
  BTstack `0x3f5000`, profiles `0x3f7000`, standalone `0x3fb000`, E10 `0x3ff000`.

RF capability uses the existing saved enablement, one JobService/scheduler,
frequency policy, ownership, clock, fault and output-admission controls. Changing
the build default does not independently enable a transmitter or schedule.

## Delivered build and artifact selection

| Selection | Target / artifact basename | Actual application |
| --- | --- | --- |
| Ordinary firmware `all`, `pico2-w` build preset, default helper, production recipe | `WsprryPico` | Complete normal 138 MHz PIO/DMA application; `pio-dma-gp2`. |
| Explicit diagnostic selection | `WsprryPico-Inhibited` | `DryRunEngine`, `inhibited-standalone-simulator`; no linked physical RF worker/driver/renderer. |
| Existing explicit RF command | `WsprryPico-StandaloneRF` | Same centralized RF application wiring, retaining its distinct compatibility artifact/program name. |

All three retain Console, WTP and management/time CDC roles, standalone, Wi-Fi,
network management, provisioning, storage, heap/pool instrumentation and guards.
The application constructor and common feature loops in firmware/network CMake
now wire every variant together. RF-only workers, libraries, definitions and
renderer/GP14/physical-stack checks apply to both RF targets. The inhibited
variant is excluded from `all`; host-only development still defaults to no SDK.
No release version was assigned; product remains `WsprryPico`, version
`0.0.0-devel`, with actual source revision and variant metadata.

Phase 12 candidate builders, role validators and live dispatchers now explicitly
require `WsprryPico-Inhibited` for inhibited roles. Their synthetic tests follow
that mapping. Current tools fail closed on old inhibited target labels; historical
manifests/images remain unchanged and must be interpreted with their recorded
source/tools. The existing `rf_ap` role retains `WsprryPico-StandaloneRF`.
The LED closeout builder likewise selects the explicit inhibited target for its
restore/stimulus roles and checks the actual ELF engine against each role before
exporting a manifest. Failed linked-role validation prevents manifest export.
Inhibited-only fault, session, physical-cut, BOOTSEL and flash-probe options make
RF application/bench target requests and ordinary `all` fail clearly before
linking. Explicit inhibited builds still work. Filename-dependent stack checks
recognize the new inhibited artifact without reducing the 32 KiB assertion.

New linked-engine checks reject wrong-role, mixed and incomplete images. Every
application build also checks actual stack/heap separation and UF2/flash bounds.
Existing heap, pool, guard, renderer and GP14 checks retain their assertions.
The helper selects the same normal application by default and accepts an
explicit target and task-specific directory. It consumes retained local
picotool source but uses private dependency build outputs in that directory.

## Reproduction and validation

All task artifacts/logs are ignored under `build/phase15-16/`. Previous firmware
and evidence directories were retained. SDK 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1 and picotool 2.3.0 at
`6f6458d792b93685a11423b244a585eaa99eafcf` remain pinned. No SDK download, package
installation or dependency upgrade was used; picotool came from local Git source.

From the repository root, the actual primary commands were:

```sh
source scripts/xcode_env.sh
export PICO_SDK_PATH="$PWD/build/local-sdk-079c6f3"
cmake --preset host-debug -B build/phase15-16/host
# Retained host environment and optional existing analysis/descriptor inputs:
cmake -S . -B build/phase15-16/host -DPython3_EXECUTABLE=/opt/homebrew/Frameworks/Python.framework/Versions/3.14/bin/python3.14 -DWSPRRY_PICO_TEST_TINYUSB_PATH="$PICO_SDK_PATH/lib/tinyusb" -DWSPRRY_PICO_HARNESS_PYTHON=/Users/lbussy/GitHub/WsprryPi-Qualification-Harness/.venv/bin/python
cmake --build build/phase15-16/host -j 4
ctest --test-dir build/phase15-16/host --output-on-failure -j 4
python3 scripts/validate_wtp_contract.py
cmake --preset pico2-w -B build/phase15-16/pico -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DPICOTOOL_FETCH_FROM_GIT_PATH="$PWD/build/phase15-16/picotool-deps" -DPICOTOOL_GIT_REPOSITORY_URL="$PWD/build/pico2-w/_deps/picotool-src"
cmake --build build/phase15-16/pico -j 4
cmake --build build/phase15-16/pico --target WsprryPico-Inhibited WsprryPico-StandaloneRF -j 4
PICOTOOL_FETCH_FROM_GIT_PATH="$PWD/build/phase15-16/picotool-deps" bash scripts/build_pico.sh WsprryPico build/phase15-16/helper-private
PICOTOOL_FETCH_FROM_GIT_PATH="$PWD/build/phase15-16/picotool-deps" bash scripts/build_pico.sh WsprryPico-Inhibited build/phase15-16/helper-private
```

| Check | Result |
| --- | --- |
| Complete host regression | 190 selected: 189 pass, one optional `config_update_schema` skipped locally; that check passes on Linux. Includes actual retained-SDK TinyUSB descriptors and all seven existing offline analysis checks. |
| WTP contract | 23 schema, 7 raw JSON, 1 framing and 8 transition cases pass. |
| Generated build graph / compile commands | `firmware/all` includes only normal `WsprryPico.elf`; physical definitions/worker for both RF images, inhibition only for the explicit simulator; 138 MHz, 32 KiB stack, normal GP14/LAN options unchanged. |
| Actual `pico2-w` build preset | Pass using an exact copy of the maintained preset in a task-local entry directory whose `build/pico2-w` resolves to the fresh validated firmware directory; no existing user preset build is overwritten. |
| Ordinary build, three linked application images | Pass all applicable engine, stack/heap, UF2/flash, BOOTSEL, pool, heap-wrapper, physical guard, GP14 and SRAM-renderer checks. |
| Controlled same-directory reconfiguration | Normal → accelerated inhibited session fixture → normal. RF target refuses clearly; explicit fixture links; restored configuration relinks all normal variants with no fixture definitions. |
| Focused failure regressions | Wrong/mixed/incomplete linked engines refused; canonical RF target name refused for inhibited candidate roles. Existing fixture/dispatch regressions pass. |
| Maintained helper | Normal and explicit inhibited targets pass with private picotool output directories. |
| Linux current Pico / exact accepted Pi | Fresh transferred Pico host driver and seven service/schema checks pass; actual UMP1 production/UI pair passes with GPIO feature required, default 4 mA and all choices. |
| Linux current network pair | Fresh Pico TLS/Consumer-Radio fixture with unchanged accepted Pi client; configuration/resources/legacy saves, drive controls and failure/reconciliation coverage pass. |

Linux checks are isolated under `/home/pi/p15-default-build-20261017/`, using the
accepted Pi client and read-only Pi sources retained at
`/home/pi/p15-gpio-drive-20261017/pi`. Before review, source hash comparison found zero mismatches across all 339
retained Pico `src/` files. The subsequent review repair changes only its
host-side LED candidate builder; every compiled firmware/service input remains
unchanged; Pi's accepted fixture
CMake preflight overlay is outside its unchanged runtime source. USB fixture
and native-client source hashes also match. The fresh network fixture reuses
that accepted Pi client library and configuration executable; no Pi source or
installed binary/service was changed. Hardware access is disabled.

Initial validation attempts retain their failures: sandbox loopback refusal
passed after socket access; the existing optional Python schema package is absent
locally and the Linux check passes. A retained TLS fixture startup attempt failed;
its later absolute-path retry passed. The fresh network build initially lacked
its Pi client archive; linking the existing accepted client completed it. An
attempt to start the fresh test before the build completed failed and was rerun
sequentially. The helper's prior shared picotool cache had missing nested build
files; private output directories repaired that reproducible helper failure.
An initial source-copy approval rejection was resolved by the operator's explicit
copy authorization; the fresh source transfer and checks then completed.

## Artifact and resource evidence

The [artifact manifest](phase15-16-artifacts.json) binds the actual dirty-source
revision, build inputs, product-source digest, ELF/UF2 hashes, resource values,
checks and exact changed-file inventory. It also retains repair-test and actual wrong-role
refusal log digests. Generated firmware is not tracked.
The immediate pre-change RF application was freshly built from an immutable
`git archive` of entry HEAD, rather than compared only with the smaller simulator.

| Image | text bytes | BSS bytes | Initialized SRAM data bytes |
| --- | ---: | ---: | ---: |
| Accepted pre-change RF application at entry source | 2296528 | 331440 | 13976 |
| Canonical normal RF | 2296464 | 331440 | 13968 |
| Compatibility RF | 2296488 | 331440 | 13968 |
| Explicit inhibited | 2281140 | 175492 | Separate inhibited layout |

Both RF images retain the 166176-byte worker, 660-byte SRAM renderer with 233
checked instructions at `0x200012d8`, dedicated guarded worker stack and 32 KiB
primary stack. The normal image's text is 64 bytes smaller and static BSS is
unchanged relative to the immediate RF baseline; initialized data is 8 bytes
smaller. Build labels/variant metadata and link wiring differ; these resource
numbers alone do not prove timing, dynamic heap sufficiency or RF equivalence.
No advertised capacity or timing/resource reserve was reduced to obtain a link.

## Independent review and delivery

Independent read-only adversarial review found one P1: the LED closeout builder
still selected canonical `WsprryPico` for roles it labeled inhibited. This could
export the physical RF application as a restore/stimulus simulator. The repair
selects `WsprryPico-Inhibited` and requires linked-role validation before manifest
export. The new builder regression executes mixed RF/inhibited role construction,
checks actual requested targets/audit roles and refuses manifest export after a
failed engine audit. Affected LED, image-checker and candidate-manifest CTests
pass (3/3). Both actual linked ELFs also refuse deliberately swapped expected
engine roles. No firmware implementation or build input changed in this repair.

The reviewer also identified the top roadmap status summary; all current
checklists/indexes now reflect software/build acceptance and retained physical
limits. A fresh independent reassessment of the complete repaired result found
no actionable findings. The reviewer independently reran 48 LED tests, two
engine-checker tests and 11 candidate-manifest tests, checked both real wrong-role
ELF refusals, and verified all 377 input hashes, 15 log hashes, six image hashes
and the complete 50-file inventory. Final acceptance/checklist wording is also
subject to an independent final reassessment before the authorized commit.

Delivery is the scoped `devel` commit containing this record and its manifest.
The execution report supplies the actual commit, non-force push outcome,
independently queried remote hash and final repository state; no release artifact
or clean-commit firmware qualification is implied by committing these tested
sources. The retained image labels/hashes above are the actual pre-commit dirty
builds, with final product-input hashes binding their source scope.

Changes are limited to application CMake wiring, explicit helper/fixture target
selection, linked-image checks and their regressions, current build contracts,
and this acceptance evidence. The manifest lists every attributable changed
path. Persistent formats, product implementation and other repositories remain
unchanged. No PR, tag, prerelease, installer, OTA, UI review or documentation-site
publication is part of this slice. P15.17–P15.20 remain unexecuted.

No Pico, debugger, GPIO, GPSDO, SDR or installed service was operated. Current
physical setup was not supplied; historical bench authority was not reused.
No device/settings restoration was necessary or physically verified in this run.
Historical RF/USB/timing acceptance keeps its exact source/image applicability.
