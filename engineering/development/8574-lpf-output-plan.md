# 8574-based LPF output implementation plan

Status: ▧ not started. This document records proposed functionality, not an
implemented contract or qualified hardware capability. Saving this plan does
not authorize implementation, companion repository changes, deployment,
hardware/RF activity, commits, or publication.

## Objective and references

Extend the existing Pico LPF selector with an optional 8574-family I²C backend,
preserving complete-job frequency checks and local switching authority. Both
simple assignments and arbitrary eight-bit patterns apply to logic-output
breakouts and relay boards.

The functional reference is the
[developer proposal in WsprryPi issue #470](https://github.com/WsprryPi/WsprryPi/issues/470#issuecomment-6740811921).
Adapt it to Pico bus ownership, timing, and recovery rather than porting Linux
adapter discovery or hardware access. Existing behavior is documented in the
[LPF and band selector guide](lpf-band-selector.md).

Other references:

- [TI PCF8574 datasheet](https://www.ti.com/lit/ds/symlink/pcf8574.pdf).
- [Adafruit PCF8574 wiring guide](https://learn.adafruit.com/adafruit-pcf8574?view=all).
- [Adafruit breakout, product 5545](https://www.adafruit.com/product/5545).
- [KRIDA relay-board example, B083LFPCK8](https://www.amazon.com/dp/B083LFPCK8).

## 1. Supported hardware and modes

Initially support one PCF8574 or PCF8574A expander per Pico, providing eight
outputs. Select the variant, board mapping, and seven-bit address explicitly:
PCF8574 uses 0x20–0x27; PCF8574A uses 0x38–0x3F. Reject XL9535 and unrelated
expander protocols. Do not identify hardware through blind scans or probing
writes; an address response cannot identify a board.

Support both the Adafruit logic-output breakout and the issue's KRIDA relay
board as documented examples. Verify the actual purchased relay-board
revision's chip, channel mapping, polarity, and power arrangement before
claiming physical compatibility.

| Mode | Proposed behavior |
| --- | --- |
| Simple | Assign a frequency range to one of eight channels, or leave it explicitly unassigned. Multiple ranges may share a channel. All other channels are logically inactive. |
| Binary | Assign an exact logical byte, 0–255, to a frequency range. Permit zero, all eight outputs, and every intermediate combination. |

Define P0 as bit 0 and P7 as bit 7. These are arbitrary patterns, not BCD codes.
Preserve simple and binary assignments independently when changing modes.
Zero remains distinct from an absent assignment.

## 2. Selector model and coverage

At plan preparation, Pico supports five direct GPIO selectors and ten frequency
ranges. Retain its complete-job coverage boundary: every nominal and programmed
RF frequency must be covered by one consistent selected output pattern,
including modulation shifts and frequency correction. Multiple bands or
disjoint ranges may share a pattern. Reject conflicting overlapping
assignments. Unassigned required coverage refuses transmission.

Make routing explicit: fixed/manual, direct GPIO selection, or I²C selection.
Keep fresh installations fixed/manual and preserve existing direct-GPIO
configurations. Do not silently activate both selector backends.

Separate physical channel count from configured filter-path count. Binary mode
must not inherit the five-selector restriction. Reassess bounded mapping counts
and serialization budgets against full supported-band coverage, shared filters,
and custom ranges before finalizing the schema. Frequency mappings describe
filter coverage; they do not override RF engine or frequency-policy limits.

## 3. Polarity, mapping, idle state, and electrical behavior

Use a per-output inversion mask, with all-normal and all-inverted choices.
For identity channel mapping:

```text
physical_byte = logical_pattern XOR inversion_mask
```

Apply polarity exactly once, including initialization and cleanup. Represent
verified board-specific channel permutations separately. A logical one means
an asserted control line or energized relay, according to the selected board.

Provide an explicit idle pattern. Logical zero can be a valid filter code and
does not necessarily mean disconnected. Validate reserved idle/enable semantics.
Keep amplifier/PTT control separate from all eight pattern bits.

PCF8574 outputs are quasi-bidirectional and power up high, with weak high-state
sourcing. Use full-port writes, not direction-register initialization. Software
cannot guarantee a safe physical selection before initialization or after power
loss. Require suitable external circuitry and an independently safe transmit
enable arrangement.

Keep Pico SDA/SCL and pull-ups at 3.3 V. Verify input thresholds, board pull-up
rails, level translation, power paths, and ground or isolation requirements.
Provide adequately rated relay power without powering coils from GPIO or the
Pico 3.3 V rail. Logic outputs are not dry contacts or relay-coil drivers.
Document required buffering and cable loading, and keep I²C local where
practical. Do not connect two active controllers to one board without a
separately designed ownership scheme. General relay load ratings do not
establish RF switching suitability.

## 4. Pico I²C ownership and driver boundaries

The Si5351 bus adapter directly initializes and can deinitialize its controller
at plan preparation. Introduce one owner per physical I²C controller before
adding another device to that controller.

- Permit an expander alongside direct GPIO RF.
- Permit an expander and Si5351 on one shared SDA/SCL pair, with distinct
  addresses and serialized transactions.
- Permit separate controllers where the validated pin plan allows them.
- Reject incompatible pin-pair assignments on the same controller, duplicate
  address ownership, and all GPIO-role conflicts.
- Use 100 kHz initially, subject to every attached device's requirements.
- Centralize initialization, deadlines, faults, and recovery.

Keep the 8574 single-port-byte transaction separate from Si5351 register
transactions. Maintain a software shadow of the complete logical pattern and
physical latch byte. Do not reconstruct output latches from input reads or
write individual channels through separate transactions.

Keep portable pattern generation, coverage, and sequencing separate from Pico
SDK bus operations. Reuse Pi code only after inspecting exact provenance,
licensing, and suitability.

## 5. Local transmission lifecycle

Use this proposed preparation order:

1. Clamp RF and establish amplifier inactivity.
2. Honor the configured release interval.
3. Apply an optional documented disconnect pattern, if the circuit provides one.
4. Write the complete target byte.
5. Wait the configured settling interval.
6. Begin amplifier lead, then start RF at the scheduled time.

Perform bounded I²C work during preparation, outside symbol-timing interrupts.
Include worst-case transaction time and switching delays in minimum ARM lead
time. Refuse late preparation without shifting the RF window. Final timing
units, bounds, and preparation budgets require explicit schema and resource
review; do not silently relax existing limits.

Hold the pattern through the complete job, keyed gaps, and normal amplifier
tail. Initially return to the configured idle pattern after amplifier disable,
rather than adding implicit hold-last behavior.

Full-byte writes reduce software-created intermediate patterns but do not
guarantee simultaneous relay movement or glitch-free decoding. A disconnect
stage is meaningful only where actual hardware provides a disconnect code or
enable mechanism. Document and validate any required break-before-make sequence.

## 6. Failure handling and recovery

NACKs, timeouts, uncertain writes, or failed initialization prevent
selector-dependent transmission. On failure:

1. Clamp RF and release independently controlled amplifier/PTT.
2. Mark selector state unknown.
3. Attempt bounded idle cleanup.
4. Retain inhibition where cleanup cannot establish the required state.
5. Require successful reinitialization and existing fault-clear conditions
   before reuse.

STOP, ABORT, cancellation, missed launch, shutdown, maintenance, reset, and
recovery must invalidate pending operations so delayed writes cannot reassert
selection. Cleanup attempts must continue after earlier failures. Shared-bus
failure handling must account for both the expander and Si5351.

Distinguish configured pattern, last successfully written byte, and unknown
state. An ACK or port read does not verify relay contacts. Bus loss can prevent
idle cleanup and leave outputs latched; software cleanup is not a hardware
interlock. Recovery must preserve output inhibition and ownership when required.

## 7. Coordinated control, persistence, and interfaces

Extend the existing `filter-selector` resource. Do not add raw I²C commands or
filter-specific fields to WTP. Retain `Wsprry-Control/1` and its namespace under
the current prerelease policy, with one current schema and no historical views.

Coordinate Pico and WsprryPi selected-member controls in the same implementation
task, with authority to edit each repository established before execution.
Update descriptors, canonical schema, exact validators, generated assets,
serialization, runtime consumption, and paired test adapters together. Validate
document shape before field access and reject malformed or inconsistent
variant/address/profile combinations, limits, device/boot bindings, carriers,
and revisions before mutation.

Preserve saved, boot-active, and runtime distinctions. Selector changes retain
restart requirements and A/B/A output inhibition. Saving settings never operates
hardware or starts a job. Define journal upgrade and rollback behavior
explicitly, independently of control and transport versions. Unsupported
records must not silently become an enabled alternative configuration. Preserve
the selector domain across unrelated saves and reset only through its defined
authority. Measure aggregate journal, request, response, stack, and RAM budgets.

Both Pico and Pi interfaces provide simple channel choices and a binary
P7…P0 editor with numeric equivalents. Expose polarity, idle pattern, bus/pins,
address, and timing. Preserve drafts across reads, errors, and context changes;
require authoritative readback after uncertain saves. Use the applicable
Impeccable skill for UI implementation and review, including desktop/mobile
rendering, invalid input, and hardware-failure feedback.

## 8. Validation and completion criteria

Software acceptance covers both modes and board forms, all eight channels,
0x00, 0xFF, multi-output patterns, inversion, mapping, shared ranges,
complete-job coverage, persistence, malformed-input refusal before writes, and
preservation of direct-GPIO behavior.

Use the developer acceptance table from issue #470:

| Band or band group | Decimal | Logical P2 P1 P0 |
| --- | --- | --- |
| 160 m | 1 | 001 |
| 6 m | 2 | 010 |
| 60 m and 40 m | 3 | 011 |
| 30 m and 20 m | 4 | 100 |
| 17 m and 15 m | 5 | 101 |
| 12 m and 10 m | 6 | 110 |
| 80 m | 7 | 111 |

The developer table identifies code 1 as 160 m; the original report's first
entry says 60 m. Treat these as configurable pattern examples, not an assertion
of qualified Pico RF support on every listed band. Also demonstrate simple
one-channel selection and 0x05 asserting channels 1 and 3.

Use fake transport and observable RF/PTT events to exercise full-byte protocol,
startup, cleanup, faults, cancellation, shared-bus recovery, and preparation
deadlines. Reject unsupported families and variant/address/profile mismatches
before writes. Inhibited firmware and ordinary tests must not drive physical
I²C. Run affected deterministic, schema, persistence, UI, cross-build, and
resource checks, plus documentation/link and whitespace checks.

Both actual production source-pair integration suites in WsprryPi's
`.github/workflows/debian-non-hardware.yml` are mandatory:

- `wtp-network-loopback`: `wtp-network-runtime-test`,
  `wtp-network-interop-test`, and `wtp-config-interop-test`.
- `wtp-usb-management-pair`: build the actual Pico `usb_management_driver`,
  run `wtp-usb-pair-client-build` and `wtp-usb-management-test`, and run
  `WsprryPi-UI/tests/wtp_usb_pair_test.js` through the production pair.

Select exact intended candidate sources and pinned dependencies explicitly.
Failed, cancelled, timed-out, or skipped required checks remain unresolved.
Report source revisions, tested uncommitted changes, exact commands/results,
and relevant CI links. Companion updates must be available on the intended
paired refs before claiming delivery there.

Physical qualification is separate. With task-appropriate hardware authority,
verify actual startup levels, electrical compatibility, mapping, switching,
and fault behavior on both the breakout and relay board, initially with RF
disabled and safe loads. Record board, firmware, engine, clock, mode, setup,
and restoration. Software tests do not qualify relay contacts, RF filtering,
emissions, physical USB, or timing.

Update operator documentation on Read the Docs with separate wiring examples,
operating instructions, meaningful limits, and actual qualification evidence.
Keep other documentation repositories outside execution scope until authorized.

## Planning baseline and unresolved decisions

The read-only review used Pico
`aa8a9a0ef1322a37f773cf0005f19bc6002e840e` and WsprryPi
`caf8fd4602f1c5e4f2e2cf293ee6283138f2579c`. These revisions identify inspected
sources, not implementation or validation evidence for this feature. Reinspect
current sources and working state before implementation.

Resolve mapping limits, storage encoding, exact timing bounds, board-specific
permutations, and the purchased relay-board revision during implementation
design. No feature code or physical qualification is established by this plan.
