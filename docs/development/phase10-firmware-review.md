# Phase 10 firmware software review and validation

The SNTP-enabled image pair now accepts five finite host modes with the existing
experimental planner's numeric limits. The standard image remains RF-inhibited;
the explicit StandaloneRF image is the later conducted-acceptance candidate.
Device clock policy, WTP/1, persisted autonomous schedules and the RF implementation
are unchanged. Joint physical target acceptance is not complete.

## Orientation and scope

Reviewed clean Pico `devel` / freshly fetched `origin/devel` at
`df3f889795af3ea98f7798dc374a7906982f677b` and WsprryPi
`codex/phase10-wtp-slice1` at `2819f0b8ccb05f12d7f978a4cee2cac830997bbf`.
The Pico delta from the host's `40812e7` reference concerns campaign/QRSS3
selection and evidence, not the WTP, time or physical RF C++ implementation.
The host's production client requires independently valid device time.

Findings driving implementation:

- SNTP-enabled firmware exposed only the old 80 m WSPR/TONE host profile.
- Its physical image advertised generic 512-event/24-hour limits despite the
  stream engine accepting only 162 events/110.592 seconds.
- WsprryPi's 1 ms default can reject a usable SNTP estimate. This is intentional
  strict admission, not justification for automatic budget relaxation.

The [execution prompt](phase10-firmware-execution-prompt.md) was prepared before
implementation. Only this Pico repository was changed. No UI, host source,
operator-manual repository, firmware device, network service or RF state was
modified. WsprryPi's original provenance pin remains untouched.

## Adversarial assessment and repair

First pass examined capability truthfulness, sample-clock propagation, build
inhibition, physical versus simulator semantics, clock aging, accepted-job
preservation, replay/boot boundaries and external source identity.

| Finding | Resolution |
|---|---|
| Existing autonomous end-to-end test used generic service defaults, so it did not prove the newly selected image profile preserved autonomous operation. | Use the same standalone service/clock profiles as firmware, including the selected sample-rate definition. Autonomous completion and aged-clock rejection pass. |
| Physical planner checks did not exercise frequency-adjustment results through the job service. | Added service/StreamEngine LOAD admission, explicit-adjustment rejection preserving the earlier job, and matching ABORT/inactive-state checks. Passes at all three clocks. |
| A simulator success could be mistaken for physical waveform or clock-rate acceptance. | Guide explicitly separates numeric simulation, NCO representability, physical clock, launch behavior and qualification. Standard ELF symbol checks prove physical RF classes are absent. |
| Optional host-source compilation needs retained attribution. | Recorded the exact host commit, unmodified external source and MIT notice location in THIRD_PARTY_NOTICES.md. |

Second pass reassessed the repaired implementation and tests. No remaining
known actionable finding in this software slice. This was an in-task adversarial
assessment, not an independent external review. Existing target USB-stall history,
physical timing/RF limits and unexecuted target gates remain open; they are not
closed by these tests.

## Commands and results

All commands ran locally, with outputs in new ignored build directories.

```sh
cmake -S . -B build/phase10-host -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_WSPRRYPI_SOURCE=/Users/lbussy/GitHub/WsprryPi \
  -DWSPRRY_PICO_HARNESS_PYTHON=/Users/lbussy/GitHub/WsprryPi-Qualification-Harness/.venv/bin/python \
  -DWSPRRY_PICO_TEST_TINYUSB_PATH=/Users/lbussy/GitHub/pico-sdk/lib/tinyusb
cmake --build build/phase10-host --parallel 4
ctest --test-dir build/phase10-host --output-on-failure
python3 scripts/validate_wtp_contract.py
```

Passed: 25 CTest checks, including existing optional offline campaign/analysis
and USB descriptor coverage, new profile tests and actual-client interoperability.
The WTP artifact validator passed 23 schema, seven raw JSON, one framing and
eight transition cases. Artifact validation alone is not implementation conformance.

The new wire test uses the real WsprryPi client against the current Pico endpoint,
SNTP parser, UTC discipline and inhibited image profile. It checks five modes,
1 ms rejection/explicit 500 ms admission, a complete synthetic WSPR frame without
post-ARM transport input, ownership expiry across that frame, lost LOAD/ARM/ABORT
responses, same-session reconciliation and refusal after a changed boot. It does
not execute the host application, Linux adapter, physical engine or a decoder.

For each RATE/DIR pair (132000000/phase10-132 and 150000000/phase10-150):

```sh
cmake -S . -B build/DIR -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_RF_SAMPLE_RATE_HZ=RATE
cmake --build build/DIR --target firmware_profile_tests --parallel 3
build/DIR/firmware_profile_tests
```

Both passed after repair; the default 138 MHz profile passed in the full suite.
DIR and RATE above are explicit substitutions, not literal build names.

```sh
cmake -S . -B build/phase10-sanitize -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_WSPRRYPI_SOURCE=/Users/lbussy/GitHub/WsprryPi \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined'
cmake --build build/phase10-sanitize --parallel 4
ctest --test-dir build/phase10-sanitize --output-on-failure
```

Passed: 17 checks, including instrumented current endpoint/client, physical planner
and autonomous tests; no sanitizer findings. This configuration intentionally
omits the eight optional Harness/descriptor checks present in the 25-check run.

```sh
cmake -S . -B build/phase10-pico -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF \
  -DPICO_SDK_PATH=/Users/lbussy/GitHub/pico-sdk \
  -DPICOTOOL_GIT_REPOSITORY_URL=/Users/lbussy/GitHub/WsprryPico/build/pico2-w/_deps/picotool-src
cmake --build build/phase10-pico --target WsprryPico WsprryPico-StandaloneRF \
  WsprryPico-RFWTP WsprryPico-RFBench rf_driver_linkcheck --parallel 4
```

All targets cross-linked with pinned SDK 2.3.0 and Arm GCC 15.3.1. Existing
picotool source was verified at `6f6458d792b93685a11423b244a585eaa99eafcf`
and supplied locally. No SDK/tool installation or device operation occurred.

For each of the four images, `python3 scripts/check_standalone_image.py
build/phase10-pico/firmware/IMAGE.elf` passed stack, heap and reserved journal/boot
region checks. `arm-none-eabi-nm -C` inspection found neither `PicoPioDma` nor
`StreamEngine` in the standard ELF and found both in each explicit RF image.
This proves software linkage, not measured electrical inactivity.

Other checks: changed Markdown links resolve; new C++ files pass clang-format;
`git diff --check` passes; `git diff --exit-code 40812e7 -- src/wtp docs/protocol`
confirms WTP implementation/specification unchanged. The actual-client verifier
passes the reviewed source and rejects a different revision and a non-root path.

Retained development attempts: the initial typed-service fixture omitted the
required payload digest, and the client fixture initially assumed a different
response-error accessor. Both were corrected before successful testing. The first
fresh cross-configure ignored a FetchContent source override and attempted remote
picotool retrieval, which failed at sandbox DNS. Reconfiguration with the verified
local repository succeeded; that failed configure is not a build pass.

## Build identity and remaining acceptance

Validated UF2s were built before commit and embed `df3f889795af-dirty`; do not
relabel them with the eventual source commit or treat them as release artifacts.

| Image | Validated UF2 SHA-256 |
|---|---|
| WsprryPico | `6d618690082eb374954b1b7a598ffccf7ddf31f74c4f037c19c06a527dcf9cee` |
| StandaloneRF | `ac8c2f204f99badaa23050ada00ecd337a16e7676f8cfad46ff0c39b6c70903f` |
| RFWTP | `283f20fffa839c38a8c6e3307786590bb7b195c11e9434982229f71c74a882af` |
| RFBench | `3db076e3f4ef66134090656117357fe6a6e766fd76dd92438c9fdae36a3b7bf8` |

Logs use `/private/tmp/pico-phase10-*`; generated artifacts are in the named
`build/phase10-*` directories. The next step is separately authorized Linux USB
acceptance with the standard inhibited image, followed by separately authorized
conducted RF work using exact rebuilt firmware identities and clock evidence.
See the [joint acceptance procedure](phase10-host-acceptance.md).

## Documentation Impact

Updated: README/development links, standalone host capabilities, Phase 10 roadmap,
source attribution, execution prompt, this review and the acceptance procedure.
WTP/1 and historical RF/campaign evidence are unchanged. The independent
Wsprry_Pi_Docs follow-up recorded by the host integration still applies; that
repository was not modified. Phases 11–13 remain planned.
