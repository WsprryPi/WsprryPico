# Phase 11.5 refill remediation execution and adversarial review

Status: software candidate prepared; physical verification OPEN. No clock is
accepted. The [execution prompt](phase11-5-remediation-prompt.md) was rendered to
`build/phase11-5/render/phase11-5-remediation-prompt.pdf`; all three pages were
visually checked. Private logs are in `build/phase11-5-remediation`.

## Failure and implementation

The [original physical result](phase11-5-pilot-attempt2.json) failed the frozen
25% reserve and 2,849,391 ns service-gap limits, then reported DEVICE_FAULT at
nominal end +1 us. No DMA error was recorded; that does not prove continuity.
The [separate recovery](phase11-5-recovery-result.json) restored inhibited A.

The terminal acknowledgement repair in 713cb16 is unchanged. Expanded tests
exercise zero, 100 us and excessive 1 ms allowances, local/nonlocal scheduling,
delayed completion, retained ownership and a stuck engine at the inclusive
100 us bound and one nanosecond beyond. Existing shutdown-failure tests remain
applicable. There is still no changed-image physical terminal pass.

The preserved 713cb16 ELF places the renderer in XIP at 0x1005f054, with a
564-byte symbol. Its active full-block loop is inline; RF-off/padding paths call
flash memset. This is linked evidence from 713cb16, not a reconstruction of the
overwritten ce1 ELF. The worst observed reserve overlapped INFO in the failed
ce1 run. These facts motivate an SRAM candidate but do not establish causation.

`WSPRRY_PICO_RF_RENDER_IN_RAM` defaults ON for physical firmware builds. It
places only `Waveform::render` in initialized SRAM and disables GCC loop-pattern
synthesis that would reintroduce flash memset calls. OFF selects an explicit,
unaccepted flash control. Portable host builds have no SDK placement dependency.
The waveform algorithm, tables, phase behavior, block size, clock, observer rate
and thresholds are unchanged.

The candidate renderer is 670 bytes with a compiler-reported 112-byte static
frame. Its full instruction body, including RF-off and padding, has no calls or
PC-relative data loads. Its worker object contains the plan, tables and double
buffers in SRAM. Other dispatch and IRQ code still executes from flash. This
is not a worst-case timing proof or removal of all bus contention. Exact clean
image hashes and heap capacity follow the implementation commit; dirty artifacts
are never candidates for flashing.

Every StandaloneRF link checks placement, initialized SRAM copy, complete
instruction coverage, internal branches and worker object location. The checker
rejects unreviewed instructions, calls, veneers, literal pools, computed jumps
and constructed addresses. It checks a reviewed pinned-toolchain subset, not
arbitrary machine-code semantics or dynamic pointer provenance. Existing stack,
heap, journal and UF2 checks remain separate.

INFO reports `rf_render_in_ram`. New pilot-v2 packets require a boolean placement
and matching full/short source revisions; admission and every INFO sample verify
placement. Historical v1 packets remain readable and bound to their original
helper hashes. They authorize no new execution.

## Timing and algorithm bounds

At 138 MHz, divider 1, a full 16,384-word predecessor provides
`16384 * 32 * 10^9 / 138000000 = 262144000/69 ns` (3,799,188.4058 ns).
The frozen service limit is floor(3/4 of that), 2,849,391 ns. Reserve must satisfy
`remaining_words * 4 >= predecessor_words`. The pilot's 2,312-word short
predecessor provides `36992000/69 ns` (536,115.9420 ns), with minimum passing
reserve 578 words. Short predecessors do not inherit a full-block deadline.

The lookup examines at most 32 boundaries per bucket: each of the 32 sample-bit
boundary pairs is separated by 2^31, while a bucket spans 2^22. Near DC/Nyquist,
many boundaries can share a bucket. The 135.5 kHz pilot does not bound that cost.
New independent bit-by-bit oracle cases exercise dense/bucket-adjacent increments,
wraparound, off spans, short tails, empty output, chunk sizes 1/7/16384 and no
render allocations. These establish algorithm behavior, not RF acceptance.

## Adversarial assessment 1 and repairs

| Finding | Severity | Disposition and retest |
| --- | --- | --- |
| Section annotation alone allows synthesized flash calls | High for this remedy | Disable loop-pattern synthesis; inspect linked body; reject calls/veneers |
| Partial disassembly could be accepted as complete | Medium | Account for each instruction byte; reject missing/truncated/oversized coverage |
| Runtime placement was not identified | Medium | INFO boolean and pilot-v2 identity guards; reject missing/numeric/string/inverted values |
| Terminal test omitted zero/valid allowances | Medium evidence gap | Expanded local/nonlocal and completed/stuck matrix; unchanged cap and ownership |
| Pilot frequency does not bound lookup density | Acceptance limitation | Oracle edge cases; resource-sensitive physical workloads remain OPEN |
| INFO overlap could be mistaken for causal proof | Claim defect | Explicit correlation-only wording; require exact-image target verification |

## Adversarial assessment 2

Re-examined the implementation after repairs. Linked addresses and bytes, not
just compile definitions, establish placement. An OFF control must fail a RAM
expectation. Initialization copy and static worker extent stay inside RAM. No
waveform arithmetic or duration changed. Repeated polls cannot extend the fixed
terminal allowance; nonlocal engines cannot use it.

Stream failure strings survive disable and clear on a successful prepare for a
new job. Worker Inspect/Metrics reports describe the initial completed poll;
a subsequent diagnostic probe does not make that state a later observation.
No additional authority is inferred from it. The original generic DEVICE_FAULT
cannot retrospectively identify a more precise physical cause.

This assessment also found that the inherited pilot packet guard allowed an
all-zero job ID, which the device would reject after flashing. The guard now
rejects it before hardware access. Added negative checks also reject a v2 full
source hash that disagrees with its runtime revision or includes a dirty suffix.
Seven pilot and five supervisor tests passed after repair.

## Adversarial assessment 3

Reviewed the final diff and reran the packet, linked-image and supervisor guards
after the second assessment's repairs. The baseline ELF passed an explicit flash
expectation; missing instruction coverage and alternate-address dependencies
remain rejected. No remaining actionable software defect was found. Physical
reserve, service-gap and terminal closure remain OPEN until authorized changed
hardware passes. Stack/heap capacity changes need affected resource checks. A
short pilot cannot close A-G, allocator transient/fragmentation coverage,
observer effects, sustained load or actual Linux address-rebind acceptance.

## Validation and current state

The development candidate passed 41 non-TLS host cases, nine affected ASan/UBSan
cases, two worker TSan cases and four SDK 2.3.1 network-on/off standard/physical
builds and layout checks. Native TLS and clean-pinned client interoperability
passed three tests in 98.28 seconds, including the actual scheduled wait.
The macOS actual second-address rebind skip remains a Linux gate.
Clean artifact/control builds and companion results are recorded separately.

Fresh P0 reads verified A revision 802c91a7b86e-dirty, boot
4571042e06f139bc185e862482082291, and B revision dbf1d86f0885-dirty, boot
4e2fb851c08b278dd4b977104d2c2aaa. Both were empty, unowned, output false, without
terminal records. No new flash/RF operation occurred. wspr5 boot/Ethernet matched;
installed transmitter PID 1957 and pi-wifi-recover timer active/enabled remained.
An initial read queried the wrong timer name; the corrected name was verified
without service changes.

## Documentation Impact

Updated: prompt, this review, development index, metric placement description,
and candidate/pilot records. Normative WTP, browser API, architecture and UI are
unchanged. Pi receives evidence/pin updates, with production behavior unchanged.
Wsprry_Pi_Docs remains read-only; the original review's manual operating-envelope
follow-up waits for physical acceptance.

Phase 11.5 owns exact firmware/clock resource acceptance: 138 MHz selected but
unaccepted, 132/150 MHz physically untested. Phase 11.6 owns per-band/per-mode
conducted tests, repeating affected 11.5 checks when selection changes. Phase 13
owns systematic band x mode x clock, filters, spectra and release configurations.
