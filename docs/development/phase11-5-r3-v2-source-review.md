# Extended-job source review and evidence applicability

Accepted authority: R3-COMPLETE-20260913-v2. This implementation review does not
close physical R3 acceptance. Checkpoints v2-001 through v2-003 retain the actual
software results, evidence hashes and their historical scope.

## Findings and repairs

1. The pinned newlib allocator can fail a large contiguous input request after
   a fragmented allocation history despite sufficient top-plus-unextended space.
   The exact linked allocator model demonstrates the mechanism and successful
   top-page trimming. C0's exact failed request remains unknown. Input allocation
   now trims before a large request and uses a nullable route. Failure closes
   input without dispatch; no SDK-wide panic policy was weakened.
2. Enlarging the plan's inline array would consume excessive stack space. Plans
   now reserve bounded heap segments during preparation; the engine retains a
   streamed canonical job digest. The two fixed waveform buffers remain fixed.
3. A maximum LOAD could retain its input and unnecessary full adjustment-reply
   copies simultaneously. Decoded fields own their data; completed input and
   the internal browser envelope are released before preparation. WTP queues
   separate header/payload storage and the browser reuses response storage.
   A 512-adjustment, seven-byte partial-output test verifies framing and one
   large response allocation. Physical peak memory remains an acceptance gate.
4. Local UI previews rounded a duration violation away and omitted the numeric
   event ceiling. Both interfaces now retain exact nanosecond-derived duration
   and show required/maximum events. Independent screenshot review accepted the
   repaired scope. These captures use simulated responses, not physical RF.
5. HTTP's expanded internal WTP envelope was checked against the HTTP body
   ceiling. It now uses WTP's separate limit. A valid 32,768-byte HELLO with
   internal-body padding succeeds; HTTP parser and API reject 32,769 separately.
6. Allocator duration telemetry previously excluded the new trim call. Its
   maximum serialized-entry duration now includes trim and allocation together.

The reassessment checked owned-field lifetimes after input release, partial
output framing/CRC/deadlines, immutable plan use, digest compatibility, duration
overflow, real-mode message complexity, retained drafts, owner/replay semantics,
and old/smaller CAPS behavior. No further actionable source finding was identified
in this pass. This is not a final adversarial assessment of physical acceptance.

## Assertion-level impact

| Evidence | Disposition for this implementation |
| --- | --- |
| R1 5/5 and R2 7/7 on the recorded historical image | Preserve the passes and their image/clock scope. Heap layout, preparation, frame storage and allocator timing are affected; new-image resource, guard, launch/refill/tail and reclamation measurements are required. |
| TLS-VALID, TLS-SLOW, TLS-FAIL, SLOT, HTTP-PARTIAL historical passes | Preserve original protocol-mechanism evidence. Final-image memory/timing and transport lifetime claims need current measurements. Do not relabel the old archives. |
| WSPR vectors, clock conversion, hardware-independent protocol precedence | Preserve passing assertions where changed dependencies are covered by the current host rerun. No inferred physical timing or spectrum credit. |
| v2-002 compiler, RF arithmetic, WTP endpoint, Pi runtime and browser checks | Retain their scoped credit. The later HTTP-envelope and allocator timing changes require the v2-003 focused rerun and physical follow-up, not a reset of unrelated software checks. |
| D0 maximum input | Preserve as fresh-boot 65,536-byte success on source 481da3c3ff17. It does not prove C0 repaired or qualify the new image. |

For each physical tranche, freeze the exact packet, source/image/boot, setup,
assertions and raw-evidence identities. Checkpoint independently audited passing
assertions before the next mutation. Record failed or missing observations at
their actual scope; retain prior passes even when a later packet stops. Reuse
requires an explicit dependency and runtime-impact argument. The final register
must still contain applicable evidence for every mandatory assertion.
