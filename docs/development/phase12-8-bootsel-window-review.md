# P12.8 BOOTSEL whole-gesture source review

Status: **SOURCE DIAGNOSTIC BUILT; PROVISIONED/CORE-1 PHYSICAL PRESS STILL FAILED/OPEN;
P12.8–P12.12 OPEN** (2026-09-27). This is a bounded step toward the approved
[P12.7 consumer contract](phase12-7-decision.md), not a consumer claim route or
Phase 12 acceptance.

## Reason and implementation

The earlier [core-1 physical-press run](phase12-wifi-only-bootsel-gate.md)
observed one pressed sample followed by a USB/AP loss and recovery boot with
`UFSR.INVSTATE`. The former sampler enters a flash-safe zone for only one
short level read, then lets core 1 and core 0 resume XIP even if BOOTSEL is
still held. The fault record does not prove the exact failing instruction,
but this is an unsafe topology for the approved provisioned/core-1 claim.

An opt-in `WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC=ON` build of the standard
**RF-inhibited** image now launches a continuously flash-reading core 1 on an
8 KiB explicit stack. It disables the old `BOOTSEL PROBE` command and all
Wi-Fi-only credential mutation in that diagnostic image. `BOOTSEL DIAG`
reports core-1 readiness and read counter; `BOOTSEL WINDOW` invokes one
five-second blocking flash-safe window and reports the result **after** it
ends. Neither command creates an owner or changes a profile. The default
production build has the option off, retains its original network-only
behavior and still rejects a linked core-1 launcher.

The new SRAM callback holds the QSPI CS output override and SDK flash-safe
zone through an entire press and stable release. It rejects a stale press,
requires 10 ms stable edges, accepts one 100–600 ms press, waits another
50 ms of release and rejects a second press before exit. It reads the RP2350
timer and GPIO registers and feeds the already configured eight-second
watchdog from a register during the window. If a button remains held past
the window plus two seconds, feeding stops; the watchdog resets rather than
returning to XIP with CS grounded. A reset during a held BOOTSEL may enter
ROM and is a failed diagnostic, never a claim grant. The routine pauses
network and USB servicing; Safari prompt delivery and AP recovery are
separate unsatisfied gates.

## Source checks

- Both opt-in core-1 and default RF-inhibited Pico 2 W builds linked with
  pinned Pico SDK 2.3.1 and Arm GNU 15.3.1. The opt-in build's linked
  stack checker found the per-core guard installer from `runtime_init` and
  `core1_wrapper`; the default build found `runtime_init` only.
- The linked topology checker requires the diagnostic core-1 launcher and
  reader when the option is on, rejects them when off, and locates the
  BOOTSEL callbacks in SRAM. It also rejects callback calls out of SRAM
  and literal XIP addresses. The diagnostic callback disassembly has no
  `bl` or `blx` instruction.
- The host suite had 98 passes in the Xcode-configured sandbox; its one
  loopback TLS test could not open its listener there and passed when run
  with loopback permission. Together these are 99 passing test cases, not
  one uninterrupted full-suite run. No target operation occurred.

## Adversarial findings, repairs and reassessment

| Finding | Repair and check |
| --- | --- |
| The first diagnostic link overflowed the SDK's core-1 scratch stack; an 8 KiB user stack alone did not remove the default allocation. | Set `PICO_CORE1_STACK_SIZE=0` only in the opt-in diagnostic, matching the explicit 8 KiB stack. The diagnostic cross-link and per-core stack-guard check pass. |
| The ordinary linked-stack checker expected only core 0 in the standard image and rejected the deliberate diagnostic core 1. | Select its existing `--physical` assertion only for the opt-in image. Both opt-in and default links pass their respective checks. |
| A linked guard installer alone did not prove the diagnostic worker entered with its explicit stack guarded. | Core 1 checks the live guard snapshot and exact stack bottom before announcing readiness. A failed check blocks the window command. |
| An indefinite hold could leave the callback in SRAM forever if it continued feeding the watchdog. | Stop feeding after the bounded window plus two seconds. The code never returns to XIP while a stable held level is observed. The linked callback has no calls out of SRAM. |
| A release edge arriving just after the deadline could be accepted if timeout was updated later in the same loop iteration. | Update the deadline before processing the edge; only a release inside the window can set `valid_press`. Rebuild and recheck the linked callback. |
| The diagnostic could accidentally admit the existing Wi-Fi-only transaction and invoke the brief sampler with core 1 running. | Disable bootstrap mutations and the old USB probe in the opt-in build; keep them in the default build. Both variants cross-link. |
| A future callback edit could add a flash call or literal XIP reference while retaining an SRAM entry point. | Extend the linked-image checker to inspect callback disassembly. Both variants pass. |

The second assessment found no further actionable source defect in this
**opt-in diagnostic**. It does not establish safe timing before the callback
starts, radio behavior during a five-second pause, physical core-1 safety,
or an end-user Safari prompt. The diagnostic must not be treated as a
shipping owner-claim implementation. Source pass cannot reverse the earlier
failed target run.

## Next bounded target gate

After a clean committed build provides an exact UF2 hash, request fresh
action-specific authority for Candidate A USB serial `0BF4B4AEC9FFB344`:
read identity/source/generation/output state, flash only the RF-inhibited
diagnostic, verify `BOOTSEL DIAG` advances, run one released-button window,
then one prompted 100–600 ms press/release window while isolated `wspr5`
loads the Pico AP. Allow at least 15 seconds for the USB command to return
after the five-second window. Read the window result, boot/recovery state, healthy
journals, empty/unowned job and inactive output; check AP service after
the pause. Leave the newer image installed if safe and do not restore an
older image. Candidate B, station credentials and RF output are excluded.
Any timeout, fault, unready core, wrong identity, storage anomaly or
unexpected output stops the attempt and remains in the result record.

If that target gate passes, P12.8 still needs a Safari-visible ready prompt,
safe window entry after response delivery, full owner HTTP/crypto, generated
trust and atomic activation. P12.9–P12.12 retain their own phone, recovery
and Stage A acceptance rows. The [execution prompt](phase12-7-12-execution-prompt.md)
keeps their order.
