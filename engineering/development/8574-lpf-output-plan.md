# 8574-based LPF output implementation plan

Status: ▧ not started. This document records proposed functionality, not an
implemented contract or qualified hardware capability. The planned implementation
includes coordinated WsprryPi selected-member changes. The current task updates
this plan only; implementation, companion repository edits, deployment,
hardware/RF activity, commits, and publication have not started or been authorized
by this plan update.

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
outputs. Select the variant and seven-bit address explicitly; initial channel mapping is identity:
PCF8574 uses 0x20–0x27; PCF8574A uses 0x38–0x3F. Reject XL9535 and unrelated
expander protocols. Do not identify hardware through blind scans or probing
writes; an address response cannot identify a board.

Start with generic PCF8574/PCF8574A support and configurable polarity. Treat the
Adafruit logic-output breakout and the issue's KRIDA relay board as wiring
examples until their actual mapping and electrical behavior are verified.
Verify the actual purchased relay-board revision's chip, channel mapping,
polarity, and power arrangement before adding a verified board-specific profile
or claiming physical compatibility. Identifying that revision is a physical
qualification prerequisite, not a prerequisite for generic software work.

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

Separate backend from policy: backend is direct GPIO or I²C; policy is
fixed/manual or required. Fixed/manual retains the chosen backend configuration
but performs no automatic frequency selection. GPIO initializes inactive; I²C
initializes to the configured idle byte and holds it. Required policy enables
coverage admission and job-dependent selection. Fresh installations retain
fixed/manual with empty direct-GPIO settings. Preserve existing direct-GPIO
configurations. Do not activate both selector backends.

Separate physical channel count from configured filter-path count. Binary mode
must support all 256 byte values without allocating 256 selector records or
inheriting the five-selector restriction. Store patterns with the bounded
frequency mappings. Section 9 specifies sixteen I²C ranges and the serialization
and aggregate-storage checks required to validate that recommendation. Frequency mappings describe
filter coverage; they do not override RF engine or frequency-policy limits.

## 3. Polarity, mapping, idle state, and electrical behavior

Use a per-output inversion mask, with all-normal and all-inverted choices.
For identity channel mapping:

```text
physical_byte = logical_pattern XOR inversion_mask
```

Apply polarity exactly once, including initialization and cleanup. Defer
board-specific channel permutations as specified in section 9. A logical one means
an asserted control line or energized relay, according to the selected board.

Require an explicit idle byte for I²C selection. Logical zero can be a valid
filter code and does not necessarily mean disconnected. Represent an optional
disconnect byte separately from idle; absence means no disconnect stage, while
zero remains a valid configured byte. Treat idle and disconnect as logical bytes subject to the same inversion mask;
no byte is globally reserved. Circuit-specific disconnection is an operator
assertion, not something firmware infers from a byte.
Keep amplifier/PTT control separate from all eight pattern bits. Returning to
idle must not depend on all control lines being deasserted: a valid idle code
may leave lines asserted. Review admission, status, cleanup, ownership release,
and restart-readiness checks for that distinction. Confirmed RF/amplifier inactivity,
successful idle command, and physical filter disconnection are separate facts.

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

Shared ownership is required implementation scope, including adapting the
existing Si5351 client. A client must not independently initialize or deinitialize
a controller used by another client. Controller failure invalidates affected
device observations; recovery must reestablish both clients' required state
without silently restoring transmit readiness.

Keep the expander's pin-pair selection in its selector settings, separate from
the Si5351 pair in the existing hardware configuration. Validate their combined
saved plan on every affected selector or hardware/config save and again at boot.
Sharing the exact pair claims one bus with two named device clients; it is not
a duplicate GPIO-role error. Different pairs on the same controller remain
invalid. Address uniqueness is per controller. Include GPS/PPS, loopback, and
other existing pin/PWM owners in combined validation. Preserve the ordinary
Si5351 qualified profile's pin restrictions. Require a valid intermediate saved
configuration when moving devices between buses; do not silently mutate a
second resource or introduce a multi-resource save transaction in this slice.

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
2. If configured, write the documented disconnect byte and confirm transaction
   completion. Otherwise retain the previously established idle byte.
3. Wait the release interval, starting after the disconnect write completes or,
   without that stage, after RF/amplifier inactivity and known idle are established.
4. Write the complete target byte and confirm transaction completion.
5. Wait the settling interval, starting after the target write completes.
6. Begin amplifier lead, then start RF at the scheduled time.

Perform bounded I²C work during preparation, outside symbol-timing interrupts.
Include worst-case transaction time and switching delays in minimum ARM lead
time. Refuse late preparation without shifting the RF window. Retain whole
milliseconds, 20 ms release/settling defaults, and independent 0–250 ms bounds
unless documented hardware requirements justify a reviewed change. The release
interval supplies the optional disconnect dwell; do not add an implicit delay.
Use the transaction deadlines, no-retry policy, and preparation accounting in
section 9. Preserve scheduled RF times and each scheduler's existing lead
calculation; a two-second window is not universal for every job source.

Hold the pattern through the complete job, keyed gaps, and normal amplifier
tail. Initially return to the configured idle pattern after amplifier disable,
rather than adding implicit hold-last behavior.

This preparation sequence applies to required I²C selection. Retain the current
direct-GPIO release/select sequence and its advertised timing; do not charge
GPIO or fixed/manual jobs the I²C transaction allowance. Before the first expander
write at boot, establish the existing RF clamp and inactive amplifier, initialize
the bus owner, and quiesce the RF device before commanding selector idle.
Si5351 RF-off verification may itself use I²C; do not require a new GPIO gate
for the existing qualified profile or mistake bus initialization for RF-off.
If RF inactivity cannot
be established, leave the selector unknown and refuse transmission. Initial
idle success does not bypass the configured release/settling intervals of the
first required job.

Full-byte writes reduce software-created intermediate patterns but do not
guarantee simultaneous relay movement or glitch-free decoding. A disconnect
stage is meaningful only where actual hardware provides a disconnect code or
enable mechanism. Document and validate any required break-before-make sequence.
Without a disconnect byte, release time only waits with the previous idle
pattern applied; it does not release a connected filter. A circuit requiring
break-before-make must provide a verified disconnect/enable mechanism and the
necessary dwell. Reject documentation or UI wording that promises that property
from a delay or full-byte write alone. No additional enable pin is introduced
by this feature; amplifier/PTT remains a separate existing resource.

## 6. Failure handling and recovery

NACKs, timeouts, uncertain writes, or failed initialization prevent
transmission whenever the immutable boot configuration includes the I²C backend,
including fixed/manual policy; that policy must not bypass a hardware fault.
Returning to an empty GPIO backend requires a valid save and restart, not an
automatic fallback. Existing fault/ownership guards on saves still apply; a
failed boot device can require repair and a successful restart before that
save is available. Do not promise a browser bypass of a retained fault or
weaken the existing physical/USB recovery authority. On failure:

1. Clamp RF and release independently controlled amplifier/PTT.
2. Mark selector state unknown.
3. Attempt bounded idle cleanup only after RF inactivity is established.
4. Latch inhibition after an uncertain write, even if a later idle cleanup
   succeeds; cleanup alone must not automatically restore readiness.
5. Require a firmware restart and successful initialization of the validated
   boot configuration before reuse after a latched selector fault. Do not add
   a fault-clear endpoint or assume a service reset clears an engine latch.
   Automatic bus recovery and successful cleanup must not clear the fault.

STOP, ABORT, cancellation, missed launch, shutdown, maintenance, reset, and
recovery must invalidate pending operations so delayed writes cannot reassert
selection. Independent RF-clamp, amplifier-disable, and bus-quiesce attempts
must continue after earlier failures. Do not move the LPF while RF-off remains
unconfirmed: record idle cleanup as refused, retain unknown state and ownership
where required, and report unconfirmed shutdown. In particular, a successful
amplifier disable alone does not prove Si5351 output is off. Shared-bus
failure handling must account for both the expander and Si5351.

Distinguish configured pattern, last successfully written byte, and unknown
state. An ACK or port read does not verify relay contacts. Bus loss can prevent
idle cleanup and leave outputs latched; software cleanup is not a hardware
interlock. Recovery must preserve output inhibition and ownership when required.

Runtime readback must represent nullable selected logical pattern, nullable last
acknowledged physical byte, command state (`idle`, `disconnect`, `selected`, or `unknown`),
fault latch, and existing RF/amplifier observations separately. Invalidate
current command knowledge on uncertain writes, controller resets, and boot;
historical last-acknowledged values must never imply current knowledge.
`idle` means a successful idle command, not disconnected hardware. A selected
pattern equal to idle remains selected during the job. Replace the GPIO-only
`selected_id` assumption with a closed backend-discriminated selection value
in the one current schema and update every consumer together. I²C verification
uses the acknowledged command and fault/generation state; it must not perform
an input read or a repeated bus write at launch to claim latch verification.
Report `disconnect` only after that stage's acknowledged command; distinguish
it from successful target selection during release/settling. Runtime backend,
polarity, byte interpretation, and pin ownership always refer to `boot_active`,
even after a save chooses another backend. Saved settings never reinterpret
the running worker's observations. Publish these fields as one coherent locked
snapshot with RF/amplifier state, and test reads during preparation, cleanup,
pending restart, and A/B/A saves.

## 7. Coordinated control, persistence, and interfaces

Extend the existing `filter-selector` resource. Do not add raw I²C commands or
filter-specific fields to WTP. Retain `Wsprry-Control/1` and its namespace under
the current prerelease policy, with one current schema and no historical views.

Coordinate Pico and WsprryPi selected-member controls in the same implementation
task. Planned companion scope includes the production Pi client/coordinator,
selected-member API and Fleet editor, capability negotiation, exact descriptor
and resource validation, serialization/readback, generated assets, paired test
adapters, and affected Pi operator documentation. Both USB and network paths must
consume the current resource. Pi-native I²C filter selection is a separate
feature: this task controls Pico-owned hardware and does not implement the
Pi-local issue #470 proposal. Establish implementation authority for both
repositories before execution; including them in this plan starts no code work.
Update descriptors, canonical schema, exact validators, generated assets,
serialization, runtime consumption, and paired test adapters together. Validate
document shape before field access and reject malformed or inconsistent
variant/address/profile combinations, limits, device/boot bindings, carriers,
and revisions before mutation.

Preserve saved, boot-active, and runtime distinctions. Selector changes retain
restart requirements and A/B/A output inhibition. Saving never applies the new
bus, pins, polarity, or patterns and never starts a job. Existing inhibition
may invoke bounded cleanup using only the immutable boot configuration; it
must not initialize a newly saved device or select its idle byte. Account for
cleanup failure after a durable save as a committed change with pending restart
and a fault, not a rejected mutation safe to retry. Use the independent storage encoding and explicit
upgrade/rollback rules in section 9. Preserve existing direct-GPIO configurations
and fixed/manual defaults on upgrade. Unsupported or corrupt I²C records must
inhibit operation rather than silently become an enabled alternative
configuration. Restore the compatible defaults before downgrade as specified
in section 9; do not promise rollback that the older reader cannot perform
safely. Preserve the selector domain across unrelated saves and reset only through its defined
authority. Measure aggregate journal, request, response, stack, and RAM budgets.

Both Pico and Pi interfaces provide simple channel choices and a binary
P7…P0 editor with numeric equivalents. Expose polarity, idle pattern, optional
disconnect pattern, bus/pins, address, and timing. Distinguish commanded idle,
unknown state, and RF/amplifier inactivity in status and error feedback.
Preserve drafts across reads, errors, and context changes;
require authoritative readback after uncertain saves. Use the applicable
Impeccable skill for UI implementation and review, including desktop/mobile
rendering, invalid input, and hardware-failure feedback.

When creating an I²C configuration, require explicit selection of variant,
address, pin pair, inversion, and idle byte before save. The editor may suggest
values, but must distinguish an unset value from confirmed zero; it must not
silently choose zero as a disconnected state. The optional disconnect byte is
explicit null when disabled. Public settings use a closed discriminated backend
shape: GPIO excludes I²C fields and I²C excludes GPIO selector fields. Policy
never changes that shape or waives validation of retained assignments. Validate
both saved and boot-active shapes independently when their backends differ.

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
deadlines. Include nonzero idle codes, absent versus zero disconnect codes,
delay origins after acknowledged writes, uncertain-write fault latching, and
recovery of both shared-bus clients without automatic fault clearance. Reject
unsupported families and variant/address/profile mismatches
before writes. Inhibited firmware and ordinary tests must not drive physical I²C; model
initialization, writes, deadlines, and faults through fake bus adapters only.
The inhibited image must not instantiate an active physical expander client. Run affected deterministic, schema, persistence, UI, cross-build, and
resource checks, plus documentation/link and whitespace checks.

Include failed RF-off with a writable expander (no selector write permitted),
failed amplifier-disable with confirmed RF-off, disconnect-stage readback,
post-commit inhibition failure, and pending GPIO/I²C backend changes. Assert
that every physical write uses validated boot addresses and the current
operation generation, including boot, restart, shutdown, and cancellation.

Boundary fixtures must cover 0/16/17 I²C ranges, exactly eight channel labels,
missing/extra labels, channel 0/1/8/9, byte -1/0/255/256, null versus omitted
assignments, and variant/address endpoints plus out-of-range addresses.
Retain GPIO 5/6-output and 10/11-range boundary coverage. Include duplicate
names, wrong numeric types, fractions/exponents, unexpected keys, malformed
compact tuples, maximum valid name lengths, and request/response byte limits.
Labels identify channels by their fixed array position; require unique channel
labels within that array, independently of unique range names. Zero ranges
may be saved even with required policy, but grant no transmission admission.

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

## 9. Concrete design recommendations

These are proposed implementation limits and acceptance budgets, not measured
firmware results. Adopt them for implementation; any necessary change requires
updating the plan, the current schema/descriptors, both consumers, and affected
checks together. No firmware or control schema is changed by this document.

### Mapping limits and representation

- Retain five outputs and ten ranges for direct GPIO, preserving its existing
  valid configurations. Give I²C its own limit of eight channels and sixteen
  frequency ranges. Sixteen supports separate conventional band mappings plus
  shared-filter and custom coverage; it is not a promise of RF support for
  sixteen bands or of sixteen simultaneous filter paths.
- Use one bounded range list. Each I²C row contains a unique name, inclusive
  whole-Hz low/high bounds, a nullable simple channel (1–8), and a nullable
  binary pattern (0–255). Mode selection chooses which assignment is effective;
  retain both assignments on save. Null means unassigned and is distinct from
  binary zero. Do not duplicate frequency endpoints in two mode-specific lists.
- Retain the current 1–16-character ASCII name rules and 1–1,000,000,000 Hz
  bounds. Provide eight channel labels with the same name rules. P0 maps to
  channel 1 and bit 0, through P7/channel 8/bit 7. A simple channel generates
  exactly one logical set bit. Binary patterns need no separate selector table.
- Validate conflicting overlaps independently for each mode, including its
  retained inactive assignments; overlapping assigned rows must resolve to the
  same pattern. Null assignments confer no coverage. Check the entire job
  against the active mode, preserving nominal/programmed frequency guards.
- Replace the five-path coverage mask for I²C with a bounded 256-bit pattern
  set (32 bytes) or equivalent fixed storage, intersecting common patterns over
  the whole job. Multiple rows with equal patterns represent one candidate.
  No candidate or multiple distinct candidates refuse admission. Keep direct
  GPIO's existing unique-selector behavior. Check same-pattern disjoint ranges,
  corrected tones, absent assignments, and a selected zero byte explicitly.
- Start generic hardware with identity channel mapping and the per-output
  inversion mask. Defer selectable board permutations until verified; do not
  store an unverified KRIDA profile or expose arbitrary permutation editing.
- Retain only the selected backend's settings in the saved resource; switching
  simple/binary mode preserves both assignments, but switching GPIO/I²C does
  not promise a second persistent backend draft. The UI must explain replacement
  before an explicit save and retain the current unsaved draft on cancellation.

### Storage and upgrade policy

Keep the existing flash addresses, two 4 KiB configuration banks, 2,048-byte
record size, CRC/sequence transaction, and 1,984-byte aggregate payload ceiling.
Do not allocate another journal or move recovery/provisioning regions.

Use a new private `standalone-state/5` record for nondefault extended selector
settings. Its outer keys remain exactly `schema`, `config`, `message_schedule`,
`logging`, and `filter_selector`, retaining their current meanings except for
the compact selector value. Encode the selector as a versioned compact JSON object, separate from
the public control representation. Recommended storage keys are `v` (encoding
version 1), `b` (backend: 1 GPIO, 2 I²C), `p` (0 fixed/manual policy, 1 required),
`t` (release/settle pair), and backend-specific fields. For I²C use `i` as
`[pin_pair,variant,address,inversion,idle,disconnect]`, `m` as 0 simple or 1
binary, `c` as eight channel labels, and `r` as range tuples
`[name,low_hz,high_hz,simple_channel,binary_pattern]`. Variant 0 is PCF8574 and
1 is PCF8574A; nullable tuple members retain their exact null semantics.
For GPIO use `o` tuples `[id,name,gp,active_high]` and `r` tuples
`[name,low_hz,high_hz,selector_id]`, with no I²C-only keys. Validate exact keys,
tuple lengths, types, bounds, and cross-field semantics before using values.
This is storage encoding, not a new shared control version or raw-I²C API.

Cap the compact I²C selector at 1,280 bytes and the compact GPIO selector at
1,536 bytes. A conservative candidate I²C encoding with sixteen 16-character
range names, eight 16-character channel labels, ten-digit endpoints, null
assignments, and maximum-width metadata is 1,077 bytes. This is a serialization
calculation, not a semantically valid RF mapping or a firmware measurement.
It leaves 907 bytes of the aggregate ceiling for the state wrapper, station
configuration, logging, and message schedule; the 1,280-byte selector ceiling
alone guarantees only 704 remaining bytes. Neither figure guarantees that all
individually valid domains fit together.

Before every affected save, serialize and validate the complete proposed state
and refuse an oversized combination before flash mutation. Define a closed
selector-capacity error body with code `filter_storage_capacity`, integer
`required_bytes`, and integer `available_bytes` (1,984); update the canonical
error schema and both consumers together rather than appending unrecognized
fields to existing strict errors. Use this shape only for aggregate capacity
refusal and preserve other errors. Expose current aggregate usage/capacity in
selector readback so editors can show authoritative capacity feedback without
a successful save. Both fields count toward the GET budget.
Define `required_bytes` as the complete proposed serialized journal payload,
and `available_bytes` as total payload capacity, not free bytes. Current usage
means the durable selected payload length; it is not a prediction of an edited
draft. Use the same closed capacity-error shape for any coordinated save route
whose candidate aggregate state exceeds that capacity, including unrelated
station/config/message changes that preserve the selector. Update those strict
consumers and fixtures in both repositories; do not report a domain-size error
for aggregate overflow or label it flash corruption.
Never truncate names, discard inactive assignments, disable schedules, or drop
another domain to make a save fit. Both editors should show aggregate capacity
feedback; authoritative device validation remains decisive. The minimum useful
fit fixture is direct GPIO RF on GP2, expander pair 1 (GP4/GP5), required simple
selection, all eight channels used, sixteen nonoverlapping ranges, 16-character
range/channel names, both mode assignments retained, W1AW/FN31/10 dBm station
metadata, a 16-character SSID, a 63-character password, `pool.ntp.org`, and one
600-second WSPR schedule with station scheduling disabled (`Config.enabled`
false; individual WSPR entries have no enable field). Use otherwise fresh-install defaults, no
GPS/Si5351/message schedule, and specify exact serialized bytes in the fixture.
This case must fit without shortening names or changing the 1,984-byte ceiling;
failure is a design blocker requiring review before schema finalization.
Separately measure representative shared-Si5351, GPS, gray-line, and keyed-message
configurations and document which combinations exceed capacity. Maximum-size
aggregate combinations must be tested for clean refusal. Expanding
aggregate capacity is a separate design change if this practical case fails.

Read existing supported storage formats, converting the old direct-GPIO model
in memory without migration-related hardware operations or flash writes at boot;
normal initialization subsequently applies the validated immutable boot settings.
Write `/5` on
the next explicit save containing nondefault selectors; retain established
default/no-selector encoding when possible. Storage migration is independent of
the single current control representation. Unknown, malformed, or corrupt
latest records fail closed; never select an older enabled journal entry.

Before downgrade to firmware that lacks `/5`, use supporting firmware to restore
fixed/manual with the empty direct-GPIO backend and remove extended selector
settings; setting I²C policy to fixed/manual alone is insufficient. Verify the older
compatible encoding and inactive output, then downgrade. Existing direct-GPIO
assignments stored in `/5` also require this procedure. Unsupported older
firmware may refuse the record; it must not be described as preserving usable
settings. Interrupted migration, A/B/A saves, and downgrade refusal need explicit
storage fixtures using the real loaders.

### Transaction and switching timing

Use 100 kHz, one full-byte write per commanded pattern, and an absolute 5 ms
deadline per expander transaction, including bus acquisition. Permit no automatic
write retries: a timeout can leave the physical latch uncertain. Admission
must serialize other bus work so an unavailable controller refuses preparation
within that same bound. Boot initialization gets one 5 ms idle write. Fault
cleanup follows the episode-wide attempt limits below; none of these actions
are hidden retries in launch preparation.
Bounded cleanup recovery may reopen the owner-controlled bus and quiesce both
clients under a separate finite 100 ms total deadline with RF/PTT inhibited.
The bus owner gets one reopen attempt per latched fault episode; a failed cleanup
must not schedule repeated recovery loops. Cleanup success or expiry retains
the selector fault until firmware restart. Recovery never enables RF.
An episode starts at the first latched fault and ends only with firmware
restart. Later NACKs, timeouts, STOP requests, reads, or cancellation generations
do not reset its recovery allowance. Distinguish the no-retry rule for a failed
selection command from the separately permitted idle cleanup: never repeat the
target/disconnect write automatically. Within one episode, permit at most one
idle cleanup write before a necessary bus reopen and one after that sole
reopen, both subject to RF-off confirmation and the same total deadline. Do
not restart the budget or add cleanup attempts on repeated service polls.
The 100 ms is a total cap including initial failure handling, bus reopen,
Si5351 quiescence, and the permitted idle attempt, not an extra delay after
other cleanup. Honor `min(caller_absolute_deadline, cleanup_start + 100 ms)`
and pass that absolute deadline down every operation; the existing Si5351
10 ms callers and any shorter remaining budgets must not be extended. If
insufficient time remains, skip further bus work, report cleanup unconfirmed,
and retain inhibition. Fault cleanup and restart paths must not synchronously
wait for their own RF-worker command or hold a lock needed by its completion.
Use one RF-worker authority for both bus clients, with no I²C in alarm/interrupt
callbacks and no blocking cross-core lock acquisition from those callbacks.

Use release and settling of 0–250 whole milliseconds, each defaulting to 20 ms.
The release interval is the disconnect dwell when that stage is configured;
otherwise it starts after known idle and RF/amplifier inactivity. Settling
starts after the acknowledged target write. Include both 5 ms transactions in
the advertised worst-case I²C preparation budget even when disconnect is absent,
plus 1 ms local service margin. Thus selector preparation is
`release + settle + 11 ms`: 51 ms at defaults and 511 ms at maximum.
Do not spend unused transaction allowance by shortening configured dwell.

Budget the existing maximum 1,000 ms amplifier lead, the JobService's 3 ms
filter-chain admission margin, and, conservatively, the Si5351's separate
60 ms preparation allowance: 1,574 ms total at maximum, leaving 426 ms within
the existing 2,000 ms standalone window. The default 100 ms service minimum is
a floor, not another additive delay. This is a planning upper-bound sum;
implementation must trace actual engine/service composition without double
counting or assuming this remainder is all available. Retain any larger existing
minimum and advertise the resulting actual `minimum_arm_lead_ns` through WTP
and companion clients. Preserve the WSPR two-second preparation checks, but
retain the keyed-message scheduler's existing `max(2 s, minimum_arm_lead + 1 s)`
rule. A 1,574 ms advertised lead would yield a 2,574 ms keyed-message lead, not
a two-second cap; do not shorten the extra second to match this budget. Test
WSPR, keyed-message, gray-line, and external WTP producers at maximum delays,
including near-slot refusal and next-slot selection. Account for preparation
performed before ARM separately from ARM admission so LOAD work is not hidden
in the capability or double-counted. If WSPR no longer fits its existing
window, revisit the design before accepting the feature.

Keep expander I²C out of timing interrupts and do not change its pattern during
RF, keyed gaps, or normal amplifier tail. This restriction does not remove the
Si5351's existing register transactions for RF transitions. Serialize reference
maintenance and other Si5351 work through the shared owner without letting
background operations consume reserved launch/cleanup deadlines. After RF and tail, disable the amplifier before the
bounded idle write. Fault/abort cleanup bypasses normal tail and switching
dwells. Command generation checks must prevent pending writes after cancellation;
a transaction already in progress cannot be undone, so its result must be
accounted for before bounded idle cleanup. Measure simulated elapsed deadlines
and verify missed preparation refuses without moving the RF window.

### Control, memory, and image budgets

| Resource | Recommended acceptance ceiling |
| --- | --- |
| Public selector settings JSON | 2,816 bytes, including retained assignments |
| Complete selector PUT body | 3,072 bytes, including contract/schema/target wrapper |
| Complete selector GET body | 8,192 bytes, including saved, boot-active, runtime, and reserved pins |
| Compact stored I²C / GPIO selector | 1,280 / 1,536 bytes |
| Complete standalone journal payload | Existing 1,984 bytes |
| Additional resident selector/bus RAM | 16 KiB across both cores and retained copies |
| Transient selector management allocation | 24 KiB total additional live workspace per admitted operation |
| Additional stack use on an affected call chain | 1 KiB; no automatic full settings/document buffers |
| Firmware linked image growth | 64 KiB over the same-target baseline, still below the existing flash boundary |

The conservative candidate public I²C settings object corresponding to the
storage calculation is 2,183 bytes. The settings ceiling leaves 633 bytes for
final field choices; the PUT ceiling leaves 256 bytes beyond the settings
ceiling for its wrapper. Two maximum settings copies leave 2,560 bytes in GET
for all other fields. Verify exact canonical schemas and maximum target/error
shapes rather than treating this headroom as proven. Use streamed/owned response
sources to avoid multiple full body copies; do not preallocate these ceilings
per device, session, range, or RF job.

Add the runtime discriminant, fault state, and capacity fields to the same GET
budget, and include the new capacity-error shape in both carrier fixtures.
Set the transport-specific generated limit, API body check, Pi validator, and
browser validator from the same canonical resource limits; changing only the
current `maximum_bytes + 256` check is insufficient. Body-size limits count raw
UTF-8 JSON, including whitespace; descriptor examples use compact serialization.

These are resource-specific limits. Keep the existing 32,768-byte general HTTP
parser body ceiling (4,096 applies to selected resources, not all HTTP),
32,724-byte consumer plaintext ceiling, USB 32,768-byte request
and 65,536-byte response ceilings, and the inspected Pi configuration response
ceiling of 16,384 bytes unchanged. Update the smaller selector-specific limits
and exact descriptor expectations in both repositories. Check encryption and
USB JSON escaping envelopes separately; body limits do not include all framing.
Advertised capabilities must still fit their own existing budget after adding
these fields. No transport or WTP limit increase is implied.

Preserve the common 32 KiB allocation safety reserve, WTP decode/preparation
reservations, 32 KiB primary stack, and 16 KiB RF worker stack. The current
API scratch admission formula at a 3,072-byte body requests 22,528 bytes;
the 24 KiB workspace ceiling is a target to verify against actual overlapping
allocations, including journal serialization and save buffers, not permission
to count each allocation separately. Management serialization, parsing, and
flash writes remain outside the RF timing path. Pattern selection, queueing,
and launch use fixed bounded state without new heap allocations.

Capture a same-toolchain, same-target pre-change baseline and compare normal
and inhibited cross-build ELF/map sizes, compiler stack-usage output and call
chains, object sizes, and instrumented host allocator peaks. Exercise full
settings, two-copy readback, rejected saves, concurrent observers, and allocation
failure. Run existing image, heap, stack, and flash audits unchanged. The
incremental RAM, stack, workspace, and image numbers are proposed acceptance
guards, not current measurements or physical stack qualification; exceeding
one requires revising the design and documenting why before completion.

Serialize mutations with the existing application authority and preserve the
existing bounded observer/session capacity. Account for overlapping GET responses
and transport/encryption envelopes globally as well as the per-operation 24 KiB
ceiling. Include immutable saved/boot/worker copies, channel-name allocations,
response ownership, and both bus clients in the resident delta. Allocation
refusal before the commit must leave settings, revisions, drafts, and hardware
unchanged. Reserve required commit workspace before writing. A response allocation
or delivery failure after durable commit cannot undo that save: retain the
committed revision, require authoritative readback, and do not automatically retry
the mutation. Cover this distinction over both carriers. Do not
increase session counts or reduce the authority/RF reserve to fit the budget.

## Planning baseline and remaining verification

The original read-only review used Pico
`aa8a9a0ef1322a37f773cf0005f19bc6002e840e` and WsprryPi
`caf8fd4602f1c5e4f2e2cf293ee6283138f2579c`. These revisions identify inspected
sources, not implementation or validation evidence for this feature. Reinspect
current sources and working state before implementation.

The subsequent read-only recommendation review inspected Pico
`d503d5d00fc4a40b68a2053795d538c1273a64e2` and WsprryPi
`949a5c3e6dad6f4bbe465d92055c7243832052dd`, with both working trees clean.
It found a Pi-local implementation prompt but no PCF8574 implementation in the
searched production sources. The linked GitHub issue could not be retrieved
during that review; its acceptance table above remains a retained planning
reference, not newly verified upstream evidence.

The recommended scope is generic 8574 support, explicit idle and optional
disconnect bytes, shared bus ownership, the existing delay defaults/bounds,
latched uncertain-write faults, and coordinated Pico/Pi control changes.
Section 9 recommends concrete mapping limits, storage encoding and
upgrade/rollback rules, transaction deadlines without retries, and preparation
and resource budgets. Before schema finalization, verify exact serialization
sizes, a practical sixteen-range aggregate state, both engines' composed ARM
lead, maximum carrier envelopes, and baseline/candidate resource deltas. These
are implementation verification gates, not unresolved product choices.
Board-specific permutations and purchased-board electrical details require verification before
physical compatibility claims; they need not block generic implementation.
No feature code or physical qualification is established by this plan.
