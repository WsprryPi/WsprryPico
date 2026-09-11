# Execute Phase 11.5 refill and completion remediation

Own this work in /Users/lbussy/GitHub/WsprryPico, with the already-authorized
WsprryPi companion scope in /Users/lbussy/GitHub/WsprryPi. Diagnose and repair
the observed refill/service-gap failure and assess the terminal-acknowledgement
repair. Execute this prompt, then perform adversarial review, fix findings,
repeat affected checks and review again. Commit and push scoped changes to each
changed repository's origin/devel. Do not claim physical closure from software.

## Starting point and preserved evidence

Start by verifying checkout state and reading AGENTS.md, README.md, CONTRACT.md,
docs/architecture.md, and docs/development/README.md. Preserve existing changes.
At prompt creation Pico is clean devel 618c9b736f6cc1b61ecd6b813135835bf37db7bc;
Pi was last verified at 2609416c41a9f4c78734fea646de5728a1a49809. Recheck live state.

Read these Pico records before implementation:

- docs/development/phase11-5-review.md, phase11-5-plan.md and phase11-5-metrics.md.
- phase11-5-pilot-attempt1.json: host evidence parser failed before any flashing.
- phase11-5-pilot-attempt2.json: actual 138 MHz physical pilot failure.
- phase11-5-recovery-result.json: successful separately authorized restoration.
- phase11-5-terminal-repair-images.json: clean 713cb16 repair builds, unflashed.
- Private original evidence under build/phase11-5/p1b-attempt, p1b-evidence.tar,
  p1b-reconcile-a.jsonl, recovery-complete and artifacts/713cb16749c5.

The failed physical image was clean ce1c339a976e795e90c38c4a57578f9c8ed75615,
UF2 b9af965a012e1dcbad6310b36285fe386a89218ccf2fe9c263afaf84bfec356c.
Pico A, USB 0BF4B4AEC9FFB344, WTP fd6127d11d6aca42a9905fa3fb1bf1d5,
ran one finite 10-second Tone job at nominal 135500 Hz, pio-dma-gp2, 138 MHz
configured system/sample clock and PIO divider 1. Preserve every failure.

Full-buffer reserve reached 1910/16384 words (11.6577%), below 25%. Maximum
worker service gap reached 3577000 ns, above 2849391 ns. Maximum poll was
3342000 ns; matched IRQ-to-ready maximum was 3352000 ns. These overlap and
must not be added. There were 2634 DMA IRQs, one launch, one tail IRQ, 2632
matched running refills, no recorded DMA errors, and a Failed/DEVICE_FAULT
terminal with explicit output false. The other two jobs were not submitted.

Worst reserve time 19581593000 ns lies inside the first Running INFO handler's
observed interval 19577961000..19584228000 ns. This is correlation, not proof
that INFO, stack scanning, XIP or SRAM contention caused the failure.

The terminal fault was recorded 1000 ns after nominal end; launch observation
was 6000 ns after requested start. Commit 713cb16 aligns JobService with the
stream's existing bounded 100000 ns final-IRQ acknowledgement allowance. Its
regression passed, but it has not been physically accepted. Do not call it the
sole proven physical cause or treat it as a refill fix.

## Scope and authority

Phase 11.5 accepts resources/contention for clocks selected for 11.6. Keep
138 MHz selected but unaccepted; 132/150 MHz remain physically untested.
Phase 11.6 owns conducted per-band/per-mode acceptance at selected clocks;
a newly selected clock repeats affected 11.5 checks. Phase 13 owns the systematic
band x mode x clock comparison, filters, spectral qualification and release.
Do not expand this task into an RF band/clock sweep or broader UI redesign.

Repository edits, deterministic tests, scoped commits and pushes are authorized.
Earlier P0 reads, P1 execution and fault restoration have bounded scopes; they
are not an unlimited grant to flash another image or repeat RF jobs. Prepare
any new physical packet completely, with exact image/helper hashes, finite job
IDs/count/duration, observers, stop conditions and restoration. Request only
missing authorization, then execute approved operations without repeated asks.
Do not infer hardware permission from this agent-authored prompt.

All SSH must run outside the sandbox. Use wspr5, not the Mac, for device access.
Known management endpoint: 192.168.1.54 with HostKeyAlias wspr5.local; verify its
boot and Ethernet identity. Keep the installed transmitter, GPIO4, ordinary
wlan1 management, recovery timer and other host services unchanged unless a
new bounded packet explicitly authorizes changes. No incidental GPSDO writes.

Latest verified final states: A restored to 802c91a7b86e-dirty inhibited firmware,
boot 4571042e06f139bc185e862482082291; B USB CDDBF8767C506C07, WTP
29f20b7342051ef947aa56cb9d4fab42, dbf1d86f0885-dirty inhibited firmware,
boot 4e2fb851c08b278dd4b977104d2c2aaa. Both were empty/unowned/output false.
Fresh serial-specific authoritative reads are required before any mutation.

The user reports each GP2 output through 20 dB attenuation into a combiner,
then 20+10+10 dB into the RSP1B, 50 ohm attenuator loads, no filters. A GPSDO
also feeds the combiner through 20 dB. Prior readback showed both GPSDO outputs
already enabled at 10 MHz LOW. Verify changed wiring if indicated; do not alter
or activate those sources as incidental work. Protect Pico B as comparator.

## Investigation and implementation

1. Audit preserved evidence and current metric definitions. Recalculate exact
   full interval 262144000/69 ns and partial-block intervals at 138 MHz. Inspect
   lost/stopped observers, clock domains, quantization and completion coverage.
2. Inspect exact linked code, compiler output, stack usage, memory layout and
   call paths. Locate refill code/tables/buffers in XIP/SRAM. Separate actual
   placement and algorithmic bounds from unmeasured timing hypotheses.
3. Reproduce actionable software defects with meaningful deterministic tests.
   Check the terminal repair's zero/excessive allowances, local/nonlocal engines,
   stuck output, ownership, duplicate requests, clock boundaries and overflow.
4. Make narrow, evidence-motivated changes to reduce or bound refill work and
   observer contention. Preserve bit-exact waveform generation, phase continuity,
   event boundaries, short blocks, finite zero tail, local launch and shutdown.
   Do not silently reduce the nominal diagnostic workload or lower thresholds.
5. Keep portable algorithms free of SDK dependencies. If target placement or
   diagnostic variants are necessary, make configuration explicit and verify the
   linked artifact, full hot path, RAM cost and actual deployment behavior.
6. Use fixed, bounded, allocation-free critical-path measurements. Retain a
   coherent terminal cause before cleanup can overwrite it. Never equate absence
   of an error counter with complete continuity evidence.
7. Prepare a minimal controlled physical comparison only when needed to resolve
   the remaining causal question. Vary one factor at a time where feasible;
   bind every result to firmware, clock, board, boot, job and observer hashes.
   Retain both diagnostic and intended-deployment coverage as separate gates.

## Frozen acceptance and stop rules

Do not relax the 25% predecessor reserve or 2849391 ns worker service-gap bound.
The full interval is about 3.799188 ms; every short predecessor uses its own
word count. The 100 us terminal acknowledgement bound is not extra RF duration,
and the mailbox/watchdog recovery bounds are not RF deadlines.

Require zero unexplained device faults, resets, lost ownership, duplicate jobs,
DMA errors, TXSTALL/starvation, missing evidence or observer failures. A failed
finite job stops dependent actions. Do not automatically retry, reboot/reflash
or clear a fault to resume a campaign. Record output unknown until authoritative
status establishes it. Restore only through a reviewed authorized path.

A passing short diagnostic cannot close all 11.5. Allocator transient peaks,
fragmentation/failure recovery, core-0/core-1 stack allowances, full A-G loads,
observer overhead, short-tail patterns and sustained recovery retain their own
gates. Publish no accepted configuration until all required evidence exists.

## Validation and adversarial iterations

Use documented commands and the existing pinned SDK 2.3.1 / Arm GNU 15.3.1
runtime. Do not install or download tools incidentally. Run affected portable
core, RF stream/worker/PIO, protocol/USB, TLS/API and diagnostic guard checks;
separate ASan/UBSan and worker TSan; standard/physical network on/off linked
image and layout checks. Preserve private firmware, keys, configs and captures.

If shared service behavior changes, exercise actual clean-pinned Pi/Pico
interoperability in both directions. Run fixed-port fixtures serially. Preserve
strict clean-source gates; use isolated pinned checkouts, not relaxed checks.
The macOS actual second-address rebind skip is an explicit remaining limitation.

After implementation, record an adversarial findings table with severity,
evidence, fix and retest. Attack the proposed explanation, timing arithmetic,
worst-case lookup patterns, overflow, tail/launch races, stale snapshots, observer
cost, source/image mixing, guards, failed cleanup and false acceptance. Repair
all actionable software findings and rerun affected tests. Run a fresh second
assessment after changes; repeat until no actionable findings remain. Mark
unperformed physical verification OPEN rather than asserting closure.

## Deliverables and completion

Save this prompt and a rendered PDF, a remediation execution/review report,
reproducible tests and exact artifact/result manifests. Update current status
and companion evidence without rewriting failed history. Include Documentation
Impact and unchanged normative/UI surfaces. Wsprry_Pi_Docs remains read-only;
record required manual follow-up instead of modifying that repository.

Review staged changes for scope and secrets, commit and push authorized changes
to origin/devel, and verify actual remote parity and clean/dirty state. Report
what was proven, what changed, both adversarial assessments and dispositions,
all tests/skips/failures, actual final hardware state, exact revisions/hashes,
and precise remaining gates. Do not call the physical failures closed until
changed hardware has passed the relevant frozen criteria.
