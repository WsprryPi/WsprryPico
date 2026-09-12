# R2 WSPR upload memory repair

## Executable repair prompt

Continue R2 from its preserved evidence in `phase11-5-r2-remaining-prompt.md`.
Keep the completed three Tone jobs and production QRSS evidence tied to source
049cc929143bdec6ec32817f6df0c73a9637cdf5, physical 138 MHz, PIO divider 1,
RAM renderer and listener enabled. Do not rerun R1 automatically. FSKCW and DFCW
completed but their shared N300/USB360 interval failed; WSPR was never armed.
Do not count these three jobs as accepted or publish any fully accepted clock.

Preserve the failed packet, raw USB/load streams, kernel reenumeration and fresh
recovery inventory. Establish the panic identity from the exact tested ELF.
Repair avoidable WTP upload memory peaks without reducing advertised limits,
altering job encoding, relaxing acceptance criteria, or changing RF scheduling.
First demonstrate meaningful regressions on the previous implementation. Test
WSPR-sized single-byte reception, maximum legal frames, combined and fragmented
feeds, resynchronization, SHA padding boundaries, protocol digest compatibility
and absence of hashing allocations. Run affected protocol/endpoint tests and
build the target with the pinned SDK/toolchain and unchanged configuration.

Review adversarially for unchecked lengths, allocation admission bypasses,
CRC/digest changes, repeated/tail blocks, changed timing/resource lifetimes and
false acceptance of failed evidence. Fix actionable findings and repeat affected
checks. Preserve exact previous evidence instead of rewriting failed attempts.
Commit and push the reviewed scoped work and record actual repository identities.

Target validation of the repair requires a new exact firmware binding and the
specific affected resource assertions: updated layout/static stack path plus
physical stack guards and heap/request headroom during WSPR LOAD under N.
Use the remaining mode jobs to collect that evidence. Reuse unchanged R1
allocator-probe semantics, ownership, controller/browser idle and expiry results
only with an explicit source-impact argument; do not relabel the old image's
measurements as new-image physical evidence. Repeat affected launch/refill checks
for the new image, at the same 138 MHz clock and freshly computed job deadlines.
No band/clock sweep; Phase 11.6 and Phase 13 retain their documented ownership.

The known-fault restoration packet is `phase11-5-r2-oom-recovery.md`. It restores
the original inhibited image/configuration without RF and consumes the last
reserved CONFIG allowance (32/32). Any subsequent physical campaign must first
freeze its exact images, finite jobs, current board boots, restored host fixture,
new configuration-write allowance and independent cleanup. Do not silently reset
cumulative counters or reuse a spent packet. Consolidate only missing campaign
authorization after the concrete packet is reviewable; continue local work first.

## Source findings and verification

The recorded fault stage 5/hash 3833354787 matches `Out of memory` in the exact
049cc929 ELF. The last successful operation was CLAIM followed by a 16,684-byte
WSPR LOAD with no response. No WSPR ARM was sent. The precise failing allocation
was not captured, so the repair addresses two demonstrated memory spikes without
claiming either has been individually localized as the target panic site.

FrameParser doubled the WSPR frame's storage to 32,768 bytes. Once its header is
validated, it now reserves the declared frame size (16,684 bytes here), while
retaining space for a batched feed's trailing bytes and existing admission checks.
SHA-256 previously copied 16,668 input bytes and reallocated to 33,336 bytes when
appending padding. It now reads full blocks directly and uses a fixed 64-byte
stack tail; it performs no heap allocations. Digest semantics are unchanged.

Both new allocation assertions failed on the old code and pass after the repair.
The target panic itself is not yet demonstrated fixed. Host tests qualify these
source behaviors, not target allocator fragmentation, Wi-Fi contention or RF.
