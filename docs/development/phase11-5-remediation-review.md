# Phase 11.5 refill remediation execution and adversarial review

Status: P2 physical diagnostic PASS; full resource acceptance remains OPEN.
No clock is accepted. See [the exact result](phase11-5-remediation-result.json).
The [execution prompt](phase11-5-remediation-prompt.md) was rendered to
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
applicable. At software freeze there was no changed-image physical terminal pass;
P2 subsequently supplied the bounded pass recorded below.

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
remain rejected. No remaining actionable software defect was found. At that
pre-execution assessment, physical reserve, service-gap and terminal closure
awaited an authorized changed-image run. Stack/heap capacity changes need
affected resource checks. A
short pilot cannot close A-G, allocator transient/fragmentation coverage,
observer effects, sustained load or actual Linux address-rebind acceptance.

## Validation and current state

The development candidate passed 41 non-TLS host cases, nine affected ASan/UBSan
cases, two worker TSan cases and four SDK 2.3.1 network-on/off standard/physical
builds and layout checks. Native TLS and clean-pinned client interoperability
passed three tests in 98.28 seconds, including the actual scheduled wait.
The macOS actual second-address rebind skip remains a Linux gate.
Clean artifact/control builds and companion results are recorded separately.

Clean source `0d9bb44a6b91679bd174c39ac068d5d9cc74e9c5` then built all four
standard/physical network variants and a network-off flash-renderer control.
All five passed linked layout checks. The physical SRAM variants passed complete
renderer checks; the flash control passed its flash expectation and correctly
failed a RAM expectation. [Exact hashes](phase11-5-remediation-images.json) bind
all ELF/UF2/map artifacts, preserved privately under
`build/phase11-5/artifacts/0d9bb44a6b91` before build-directory reuse.

Physical linked heap capacity is 218,732 bytes with networking and 218,784
without it. Compared with 713cb16's matching SRAM-data footprint, the renderer
adds 672 bytes including alignment; this is linked capacity, not measured free
heap. Standard inhibited images remain 377,832/377,892 bytes. The 670-byte
renderer and its 112-byte compiler frame still require target resource checks.

Pi's actual-server fixture passed against clean Pico 0d9bb44, including its
60-second wait. Its first invocation used the repository root and found no Make
target; the documented src invocation passed. The macOS address-rebind skip is
retained. Companion production code did not change. The [P2 packet](phase11-5-remediation-pilot.md)
was frozen before separate authorization; its completed execution is recorded below.

Pre-P2 P0 reads verified A revision 802c91a7b86e-dirty, boot
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

## Authorized P2 execution and evidence review

The user explicitly authorized flashing/RF for the frozen P2 packet. Bundle,
packet, helper and image hashes matched before the one new wspr5 transient unit
started. Its pre-registered conditional restoration completed successfully.
No helper, image, threshold, clock or job was changed during execution.

All three 10-second 135.5 kHz Tone jobs completed on Pico A with clean
0d9bb44a6b91, SRAM renderer, 138 MHz and PIO divider 1, boot
1d2366afcc2a37d459f1844394eea2e5. There were exactly three LOAD, ARM and RELEASE
requests, each job followed Loaded/Armed/Running/Complete, and no fault event,
retry or ABORT occurred. Seventy-nine INFO samples covered the 78.44-second pilot.

| Observation | Original P1b failure | P2 result | Frozen criterion |
| --- | --- | --- | --- |
| Full predecessor reserve | 1910/16384 (11.66%) | 7674/16384 (46.84%) | At least 25% |
| Short predecessor reserve | 2109/2312 (91.22%) | 2060/2312 (89.10%) | At least 25% of actual length |
| Maximum worker service gap | 3.577 ms | 2.176 ms | At most 2.849391 ms |
| Maximum poll | 3.342 ms | 1.942 ms | Component timing, not added to service gap |
| Maximum matched IRQ-to-ready | 3.352 ms | 2.016 ms | Matched diagnostic, not added to service gap |
| Terminal completion | DEVICE_FAULT, first job | Complete, all three jobs | No unexplained failure |

P2 recorded 7,902 DMA IRQs, three launches, three tail completions, 7,896 matched
running refills (7,893 full and three short), and zero DMA errors, unpaired
refills, invalid reserves or exhausted successor links. Sampled stack usage
was 7,556 bytes on core 0 and 5,568 on core 1; sampled heap peak was 27,476 of
218,732 linked bytes. These remain sampled observations, not worst-case stack,
allocator or fragmentation acceptance. IRQ/probe and other metrics remain in
the [exact result](phase11-5-remediation-result.json).

Adversarial evidence assessment independently reconstructed all 73 transmitted
WTP requests and 91 received messages from raw framed bytes, including CRC,
request/reply identity and the 18 ordered lifecycle/owner events. It reconstructed
all Console JSON from raw receive bytes and matched the 79 emitted INFO values,
checked every frozen threshold and clock/placement/boot identity, command-output
hashes, full backup/application match, restoration admission and final independent
readbacks. Six mutated copies (missing record, wrong clock, false placement,
lost tail, false completion and corrupted wire bytes) were rejected. The second
assessment checked the result manifest against preserved raw evidence and
verified the acceptance register still contains zero accepted configurations.
No actionable finding remained; no repeated physical run was needed.

The local private audit script, output and complete raw evidence are hash-bound
in the result manifest. Original P1/P1b failures and their units/logs remain
untouched. P2 establishes that the observed failures did not recur within this
bounded changed-image diagnostic; it does not isolate a causal XIP effect,
because the image also includes the terminal acknowledgement repair.

Final independent reads verified A back on 802c91a7b86e-dirty inhibited firmware,
new boot 0b1cb103440c63757e5f326660be75d2, empty/unowned/output false. B remains
on dbf1d86f0885-dirty, original boot 4e2fb851c08b278dd4b977104d2c2aaa, likewise
empty/unowned/output false. Host boot, Ethernet and wlan1 addresses, installed
transmitter PID 1957, recovery timer and throttle state matched preflight. The
P2 unit is inactive/dead with Result=success and ExecMainStatus=0.

Remaining: exact-image full A-G resource/contention matrix, worst-case memory
and stack margins, diagnostic observer parity, resource-sensitive lookup and
short-tail patterns, sustained operation and native Linux rebind. No additional
clock is selected or accepted; no conducted RF spectrum/frequency/filter or
other band/mode qualification is claimed.
