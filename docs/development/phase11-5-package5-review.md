# Phase 11.5 Package 5 execution and adversarial review

## Outcome

Package 5 remains **OPEN**. `R3.RETAINED.replay` and
`R3.RETAINED.session` are accepted. Terminal capacity and LRU behavior pass,
but real terminal expiry was not executed. Three repaired maximum-workload RF
cycles pass their functional raw-evidence audits, but `R3.RECLAIM` remains open
because the post-cycle live-memory values differ by 12,384 bytes, above the
frozen 1,024-byte threshold.

The executed scope is the [Package 5 prompt](phase11-5-package5-prompt.md).
The [result](phase11-5-package5-result.json) preserves every failed attempt and
does not convert functional cycle passes into reclamation credit. A new
[bounded continuation prompt](phase11-5-package5-continuation-prompt.md) is
prepared but not authorized or executed.

## Source review and maximum LOAD repair

Review found that production USB and network adapters passed decoded requests
to `JobService` by const reference. A maximum request therefore copied all 512
event pages before admission. `JobService` also admitted 65,536 bytes of
temporary LOAD preparation while the shared memory gate separately retained a
32 KiB authority/RF reserve and paged serialization had its own bound. On the
current retained background this caused the real maximum LOAD to return
`INTERNAL_ERROR` with no allocator failure.

The repair adds an rvalue `JobService::handle`, transfers decoded Request and
Job ownership through both production adapters, and admits 32 KiB of bounded
preparation work. The unchanged memory gate retains the separate 32 KiB
reserve. Paged input and response serialization remain bounded. A deterministic
test proves that production transfer of a maximum LOAD does not allocate a
second event list. The repair checkpoint passed all 74 configured host test
groups. The final repository suite, after registering the Package 5 tests in
CMake, passed 68/68 CTest entries.

The final deployed RF image binds source
`2b25ca05c270819466a04498f9bc4894a4c5bace`, UF2
`16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`,
boot `80d558e5804547749eca849c53ba27e1`, SDK 2.3.1, 138 MHz and the
PIO/DMA GP2 engine. Three deployment failures remain in the record: an
inhibited 150 MHz target was selected first; the next corrective packet stopped
before flash because its prior-image gate was stale; the following RF image
omitted the lab TLS/hostname build inputs. The final corrective packet
`d9104d4...` flashed the intended RF/TLS image, preserved both configurations
and released the held reservation.

## Accepted replay and session rows

Packet `2039a76...` used the prior image and unchanged boot for two real
360-second application-quiet intervals. It admitted exactly 16 sessions,
rejected session 17 with `BUSY`, and reused an admitted session. It populated
eight replay entries, verified byte-exact replay and request-ID conflict,
touched the oldest entry, added a ninth, and proved the untouched LRU entry was
evicted while the touched entry remained. After the second quiet interval, old
sessions returned `HELLO_REQUIRED`, the formerly conflicting request ID was
admitted and the formerly refused session entered normally.

The browser runner incorrectly posted its final STATUS as a job operation and
received the exact expected HTTP 400 `unsupported_operation`. Independent audit
accepts the 34 completed core cases and requires separate status confirmation.
Packet `df03ad8...` supplied that authenticated read and proved Empty,
inactive, unowned authority. The current-image source repair affects LOAD
ownership and admission only; HELLO, STATUS, RENEW, replay LRU, session limits
and both prune paths are unchanged. That bounded source-impact review preserves
the replay and session results.

One target Wi-Fi recovery was required before the accepted retained run. Packet
`e1a29d2...` records the single bounded OFF/ON cycle, unchanged boot and
recovered `10.77.15.10` address. It receives no retained-capacity credit.

## Terminal capacity pass and expiry blocker

Packet `ed7db2e...` ran nine distinct actual one-second Tone jobs on the repaired
image. Every job traversed CLAIM, LOAD, ARM, Running, Complete and RELEASE.
After job eight it replayed job one's full LOAD to touch that retained record.
Job nine left exactly job nine, touched job one, and jobs eight through three;
job two was absent. The auditor reconstructs all nine launches, 561 Console
samples, 113 WTP status/health samples and exact terminal ordering.

The real 3,660-second expiry was not run. Failed reclamation packet
`0e959b6...` loaded a new job, received its LOAD response after 7.666 seconds,
timed out at the unchanged five-second gate and later recorded the job as
aborted. The frozen expiry packet requires eight complete terminal records.
Restoring that precondition requires additional RF completions beyond the
executed allowance, so the terminal row remains open.

## Reclamation evidence and failed gate

Three repaired packets (`7878985...`, `fc55afc...`, `a536693...`) each completed
one 512-event, 128-second FSKCW job. Independent raw audit verifies 32,784
resident WTP bytes, authenticated bounded HTTP 503 `resource_exhausted`, a
complete WTP response, authenticated recovery, continuous native/Console
authority, no allocator or TLS failure, and final inactive authority. Their
LOAD responses completed in 3.312, 3.223 and 3.274 seconds.

Those functional passes do not satisfy reclamation. Immediate pre/post live
allocations were 33,080/73,008, 35,944/60,624 and 40,272/64,480 bytes. The
post values span 12,384 bytes. The original plan held terminal cardinality at
eight but did not hold terminal content or replay/session cache phase equal.
Maximum-event histories progressively replaced one-event Tone histories, and
the immediate final inventories retained different short-lived responses.
The aggregate auditor correctly rejects the evidence instead of raising the
1,024-byte threshold.

Earlier attempts remain evidence. Packet `7184ad3...` ran one 128-second job but
missed the combined WTP deadline. Packets `17ecee8...` and `c9d0a5a...` used no
RF and exposed the maximum LOAD admission defect. Packet `0e959b6...` used no
RF but exposed the intermittent late LOAD response and contaminated the later
terminal prerequisite. No failed packet receives acceptance credit.

## Adversarial review

The first assessment found four actionable issues:

1. maximum LOAD ownership and temporary-memory admission failed on the actual
   retained background;
2. two deployment packets selected incomplete targets or inputs;
3. the first repaired cycle packet omitted the already-frozen TLS decoder from
   its helper manifest;
4. the reclamation comparison treated equal terminal counts as equal retained
   content and sampled before transient caches were in a common phase.

The source repair and final deployment close issues 1 and 2. The cycle-1 raw
packet remains immutable; its audit uses an independently pinned decoder SHA-256
`5cf41075...`, and later packets include the decoder in their staged manifest.
That closes issue 3 without rewriting evidence. Issue 4 cannot be repaired from
the existing captures without weakening the gate or repeating physical work.
It remains an explicit Package 5 blocker.

The [final adversarial result](phase11-5-package5-adversarial-result.json)
validates the published partial status and rejects ten mutations that change
identity, accepted retained rows, terminal expiry state, failed late-response
evidence, reclamation comparison, RF charge or restoration. No overclaim
remains. Package 5 is not marked complete.

## Hardware charge and restoration

The campaign charged 13 actual RF jobs and 521 seconds: nine terminal Tones,
one failed 128-second reclamation job, and three repaired 128-second cycles.
Other stopped attempts charged zero RF. It used three flashes/BOOTSEL
transitions, one Pico Wi-Fi cycle, zero configuration writes and zero controlled
reboots.

Final packet `a536693...` left A and B independently Empty, inactive and
unowned and released the shared reservation. Host fixture cleanup reports no
failures, restores the exact preflight interfaces and routes, protected time
service files and installed WsprryPi PID 1957 on host boot
`220e53ca-ca95-4206-9581-dbe28aa1eeb8`.

Package 5 has two accepted rows and two open rows. Capacity and pressure remains
the only closed revised Phase 11.5 family, so Phase 11.5 remains open at 2/6
families. Package 6 must not start until Package 5 is resolved.
