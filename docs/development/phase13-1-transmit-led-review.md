# P13.1 transmit LED execution and adversarial review

Date: 2026-10-07. Baseline: clean `devel`
`dbbaa62cc2c8c8fe92617e167ef4140902632b70`.
Disposition: **SOURCE/HOST COMPLETE; PHYSICAL ACCEPTANCE OPEN**.
The operator authorized execution, iterative adversarial review, commit and
push of the [comprehensive prompt](phase13-1-transmit-led-prompt.md).
No device control, flashing, GPIO action or RF was performed.

The operator subsequently revised the hardware-authorization policy: stating
that a named Pico is connected to the SDR authorizes RF testing for the task,
including necessary routine device control and restoration. `AGENTS.md`, the
execution prompt and physical packet now follow that rule; the earlier
separate-approval request is superseded. This policy change adds no physical
test result.

## Implemented behavior and evidence boundary

The application already had solid TX arbitration, but a main-loop snapshot
could leave the first RF interval unlit, and a failed solid-on write did not
prevent launch. The opt-in GP14 RF acceptance image also let Identify override
TX. Those gaps are repaired in the application image.

`PioDmaSink` now binds an `IndicatorGate` in the standalone RF worker. A valid
local launch attempt at or after its start publishes a unique ticket. Core 0's
one `IndicatorController` acknowledges only a checked selected-output on state;
RF stays inactive until that ticket is acknowledged. Cancellation cannot reuse
a stale acknowledgement. RF IRQs perform only atomic gate operations and local
timer rearming; no CYW43 call crosses to core 1. Missing acknowledgement expires
within the original WTP start window; no USB/network delivery sets symbol timing.

The selected indicator can lead RF briefly during activation, and wait for the
next core-0 poll to resume its non-TX cue after inactivity. This is deliberate
coverage of the whole engine-active interval. It can delay a launch within the
existing window or miss the job when the indicator owner is unavailable.
The physical timing/coexistence consequences remain unqualified.

As clarified by the operator during execution, an external selected pin carries
**only TX**, with AP/Identify continuing onboard. If no external selection is
present, onboard TX is solid ahead of its operational cues. Explicit disabled
selection remains supported and bypasses launch acknowledgement. A checked
onboard AP flash cannot acknowledge an external TX write. Each output has
separate known/on/fault state; a cue fault does not fabricate an external TX
fault. Fault reporting remains latched across successful retries.

The extracted Pico adapter is used by firmware and host tests. It checks the
full pin plan, sends operational cues to CYW43, reserves the selected external
pin for TX, and preloads the requested electrical level before setting output
direction for either polarity. Mocks establish adapter behavior, not actual
LED wiring, current drive or electrical continuity.

Cleanup inspects driver activity after halt, rejecting even a reported success
with active output. A failed stop retains the request while output remains
active; later independently observed inactivity clears it. The zero-tail
hardware stop can clear TX before a delayed completion IRQ. Dry-run images
never request TX. Normal/recovery loop paths share the same indicator poll.

All standalone and USB/TCP/browser/BLE application jobs converge on the same
JobService/worker/sink. Host tests exercise synthetic engine plans for Tone,
WSPR, QRSS, FSKCW and DFCW, including zero-rendered keyed intervals, along with
existing full encoder/service checks. A warmup tone is an ordinary RF job
through that gate. The application engine remains enabled during mode gaps;
the LED remains solid until it actually stops. Historical single-core RFBench
and RFWTP diagnostics do not use this application's indicator graph and are
outside this change's supported application scope. Their warmup capture
history adds no physical acceptance here.

## Adversarial assessment and repairs

The assessments were performed in this chat without delegated agents.

| Finding | Repair and regression evidence | Disposition |
| --- | --- | --- |
| RF could begin before a successful solid-on write; an LED error did not prevent launch. | Unique-ticket sink/controller handshake. Tests delay polling, fail/recover writes and exhaust the launch window without RF. | Closed in source |
| Acceptance-only Identify override violated TX priority. | Removed the override. Shared-onboard tests span Identify expiry and AP phase changes with no off write during TX. | Closed in source |
| Disabled selection still entered the new early-alarm path. | Disabled gates bypass the entire handshake branch; all-mode enabled/disabled integration checks pass. | Closed in source |
| An optional worker gate could permit future application construction without indication. | Application worker construction requires a gate reference. Bench sink's optional adapter remains explicit and outside application scope. | Closed in source |
| Halt success without inactive output could claim successful cleanup. | Check both halt result and activity. Regression injects false success with active output. | Closed in source |
| A failed stop becoming inactive later could leave the request stuck. | Failed-state polling clears the request only after inactive evidence. Regression exercises delayed physical stop. | Closed in source |
| Slow LED I/O could acknowledge a canceled/rearmed activation. | Non-repeating tickets and a regression that cancels/rearms during the actual controller write. The stale acknowledgement cannot authorize RF. | Closed in source |
| Routing all cues to the external selection violated the operator's clarified TX-only requirement. | One controller owns two outputs; actual adapter routing and controller regressions prove AP/Identify never light external TX, onboard on cannot acknowledge it, and cue faults remain distinct. | Closed in source |

A fresh final assessment checked launch/stop ordering, both output owners,
cross-core ticket lifetime, cue expiry, source graph, reset paths, default
inhibition, disabled behavior, wire compatibility, pin ownership and evidence
claims. No actionable finding remains in this source slice. Target acceptance,
electrical faults and physical timing remain explicit open gates.

## Reproduction and validation

macOS host workflow: `bash scripts/check_host.sh`. The final host build used
full Xcode and ran 155 CTest entries: **153 passed, two baseline failures**.
The changed indicator, field-access, RF-worker, PIO/DMA, pin, standalone and
transport tests pass. Additional PIO/DMA regressions cover pending cancellation,
clock rejection, missing/recovered acknowledgement, stale callbacks, lying or
failed stops, delayed tail IRQ, all five modes and both enabled/disabled choices.

The two failures were independently reproduced against an untouched `git
archive` export of the baseline in a temporary directory, using the same host
compiler. `capacity_pending_tests` fails its source-extraction fixture with
`NameError: https_authority is not defined`. `load_reply_tests` fails three
adjacent reply-reserve assertions (lines 213, 238, 263 of that baseline test).
Neither test nor implementation was changed to hide those results. They are
outside the LED slice; the full suite is not claimed green.

Configure the targeted sanitizer build with:

```sh
source scripts/xcode_env.sh
cmake -S . -B build/phase13-1-sanitize -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined'
cmake --build build/phase13-1-sanitize --target \
  pio_dma_tests indicator_output_tests field_access_tests rf_worker_tests
ctest --test-dir build/phase13-1-sanitize --output-on-failure \
  -R '^(pio_dma_tests|indicator_output_tests|field_access_tests|rf_worker_tests)$'
```

All four sanitizer entries pass. Both application firmware targets and
`field_access_pico_linkcheck` cross-link with retained SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, retained picotool
`6f6458d792b93685a11423b244a585eaa99eafcf`, GNU Arm 15.3.1 and 138 MHz.
The source uses a fresh `build/phase13-1-pico` directory because the previous
cache referenced a removed SDK-profile path. The retained picotool nested
precompiled-bootloader build files also needed regeneration. An attempted
fresh dependency location triggered an SDK clone attempt that failed on DNS;
no dependency was downloaded. Final builds reuse the existing retained source
and generated build tree. No SDK source or pin was altered.

```sh
source scripts/xcode_env.sh
PICO_SDK_PATH="$PWD/build/local-sdk-079c6f3" cmake -S . \
  -B build/phase13-1-pico -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF \
  -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH="$PWD/build/pico2-w/_deps"
cmake --build build/phase13-1-pico --target \
  WsprryPico WsprryPico-StandaloneRF field_access_pico_linkcheck -j 4
python3 scripts/check_standalone_image.py \
  build/phase13-1-pico/firmware/WsprryPico.elf
python3 scripts/check_standalone_image.py \
  build/phase13-1-pico/firmware/WsprryPico-StandaloneRF.elf
```

Both explicit linked-image/UF2 reservation checks pass, along with the build's
startup/stack/allocator/renderer checks. Changed C/C++ formatting, Markdown
local links, the seven prepared jobs against WTP/1 schema/semantics, and
`git diff --check` are checked. Logs and candidates remain in ignored
`build/phase13-1-*` paths. The physical packet has no automatic retries or
timed operator response requirements and remains **unexecuted**.
