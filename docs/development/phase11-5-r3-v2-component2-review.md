# Group 2 component 2: firmware candidate build and review

Component 2 is complete for its hardware-free scope. Group 2 remains OPEN.
No physical assertion closes from this build. Neither image was flashed, and
no device, fixture or RF operations occurred in this component.

The selected source is `4dad112c8a4c0ce4e5be77ecba5c3c460496472c`, built from a clean detached
checkout. The embedded revision is `4dad112c8a4c`. The candidate
uses Pico 2 W / RP2350 Arm, Pico SDK 2.3.1, GNU Arm 15.3.1, the existing
per-device TLS configuration on port 18443, GP2 PIO/DMA at 138 MHz, and RAM
waveform rendering. Existing dependencies were reused; no tools were installed.

| Image | UF2 SHA-256 |
| --- | --- |
| Standalone RF | `4b4ddd6c9108d20cb7718756da047e4ddd0d4948e6c432d3aa1329d55150d08a` |
| Standard inhibited | `cec51688467c7e5c7014bfb9ade261e3eee640af9de921ebe17051993562fe25` |

Full ELF, UF2, map, source and check-log identities are in the
[component 2 result](phase11-5-r3-v2-component2-result.json).
Generated images remain outside Git under
`build/phase11-5-r3-group2-component2/firmware/firmware/`.

## Review and correction

The initial target build exposed increased stack use from recursive key sorting
with the larger paged JSON views. The selected correction uses iterative heap
sorting and const-reference comparisons, preserving decoded-key ordering and
duplicate detection. A paged test checks a wide object at the depth limit,
escaped duplicate keys and rejection beyond that limit. The final target JSON
stack report contains no recursive introsort helper.

The reassessment found no remaining actionable issue within the selected
source/build scope. The component 1 record remains historical; component 2 adds
the sorting correction and its regression test.

## Memory and RF applicability

The Standalone RF linked heap changes from 220328 to 219704
bytes, a 624-byte reduction. Both primary and worker stack allocations remain
16 KiB with the existing 4 KiB guard reserve, leaving 12 KiB usable per stack.
Compiler-reported frames include main 2664 bytes, FrameParser::process 768 bytes,
Endpoint::payload 1352 bytes and recursive JSON value validation 264 bytes.
These are individual static frames, not a complete call-chain or interrupt bound.
Live stack high-water measurements remain required.

RF source paths and build configuration are unchanged relative to C6. The
660-byte RAM Waveform::render function is identical in address and bytes.
Other linked routines, relocations and static addresses differ; this comparison
does not transfer full timing or allocation acceptance to the new image.

## Validation and next component

All eight affected host test groups passed, including 35 core cases. Four
AddressSanitizer/UndefinedBehaviorSanitizer groups passed. WTP contract checks,
heap-hook checks, stack-guard checks, RAM renderer validation, flash/UF2 boundary
checks, and inhibited shutdown/synchronization checks passed.

The next component is a separately bounded physical admission and C6 workload
retest using this exact candidate. It must obtain fresh device and fixture
identities, preserve the current authorization/budget limits, and record stack,
allocator, timing and final authority evidence. F6 is restored and cannot be
reused as an active fixture. Historical C2/C3/C6 failures remain preserved.
