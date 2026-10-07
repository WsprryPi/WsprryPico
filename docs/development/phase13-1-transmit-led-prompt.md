# P13.1 transmit LED execution prompt

Authorized by the operator on 2026-10-07. Work in `devel` in this repository.
Execute this prompt, repair actionable findings, perform another adversarial
assessment after repairs, then commit and push the reviewed work to `origin/devel`.

## Objective and boundaries

Complete the source and deterministic acceptance for the selected
[transmit LED requirement](transmit-led-backlog.md). Keep one indicator owner.
An enabled indicator must be solid throughout physical engine output activity,
including RF-producing warmup, all supported modes and shutdown. TX overrides
AP-ready and Identify on a shared onboard selection. An external selected LED
is TX-only: operational AP/Identify cues remain onboard and may blink there
while external TX stays solid. Resume the shared onboard cue only after confirmed
output inactivity. Loaded, queued and armed jobs alone, dry runs and RF-inhibited jobs
must not request TX. Preserve onboard default, external GPIO with either
polarity, disabled selection and exclusive pin ownership.

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md` and the
development guide. Inspect the branch, working tree and remote before editing;
preserve unrelated work. Do not change other repositories, implement Si5351,
enable GP14 by default or alter WTP/1. Preserve the Field-GATT/1 cue vocabulary.
Source results, cross-link results and physical evidence must remain distinct.

## Investigation and implementation

1. Trace the one shared JobService through standalone, USB, TCP, browser and
   BLE submission to the physical PIO/DMA owner. Establish activation,
   warmup, gate-off waveform intervals, normal completion, abort, stop,
   failed launch, failed shutdown and recovery behavior. The current PIO
   engine stays enabled while rendering zero samples in keyed mode gaps;
   those gaps are part of its active output interval, not separate launches.
2. Reuse `IndicatorController`. Check the interval before the first solid write,
   stale cross-core state, false success after output errors, suppressed polls,
   competing writers and acceptance-only priority exceptions. Repair
   demonstrated gaps with portable logic and Pico adapters kept separate.
3. If polling can permit RF before a checked solid write, add an identity-bound
   activation handshake. Request it at a valid local launch attempt, never
   merely at ARM. Core 0 writes the selected indicator; core 1 launches only
   after that request's acknowledgement. Do not call CYW43 from an RF IRQ or
   core 1. A missing acknowledgement must stay RF-inactive and expire inside
   the existing local start window. Disabled indication bypasses this gate.
   Cancel only on confirmed inactivity; stale acknowledgements must never
   authorize a subsequent launch. Explain the small indication lead during
   activation and the possible launch delay within the existing start window.
4. Retain checked-write retry and latched fault reporting. A failed write is
   unknown, not a successful on/off transition. RF shutdown must depend on
   engine/driver evidence, never LED state. Remove any Identify-over-TX exception.
5. Make the actual Pico indicator adapter testable for onboard checked writes,
   external polarity and glitch-free initial output, TX-only external routing,
   independent onboard operational cues, disabled output and
   invalid/conflicting allocations. Do not qualify electrical wiring from mocks.

## Deterministic validation

Add behavioral regressions for launch-before-LED, delayed/failed/recovered
acknowledgement, stale acknowledgement after cancellation/rearm, absent operator
or management polling, completion/abort/stop, failure retaining active output,
cue overlap/expiry, disabled indication, both external polarities and invalid
pin plans. Exercise actual sink/stream/controller integration where practical,
including warmup and all five modes. Check dry-run/inhibited behavior and retain
existing transport, pin ownership and Identify replay checks.

Run the documented macOS host workflow, `bash scripts/check_host.sh`, and
targeted sanitizer checks for the changed portable logic. Use only retained
pinned SDK/toolchain sources to cross-link the standard inhibited image and
`WsprryPico-StandaloneRF`; do not fetch or install dependencies. Check formatting,
Markdown links and `git diff --check`. Record exact commands, counts, failures
and limitations. Fix failures attributable to this change and rerun affected checks.

## Physical preparation and operator interaction

No flashing, USB device control, debugger, GPIO or RF action is authorized by
this software prompt. Complete source changes, deterministic checks, candidate
cross-links, hashes, review and a concrete physical packet before requesting
the exact necessary authorization. Historical RF budgets do not authorize
new tests. Prepare identity checks, backup, idle/admission gates, a finite RF
budget, automatic output cutoff, independent observation and restoration.

All operator gates are untimed: await readiness before a case, never require
a response within a countdown or a precisely timed button press. Automate
stimulus/collection and retain results for later inspection. Physical onset,
warmup, gaps and cutoff continuity need recorded optical/electrical evidence
if the operator cannot continuously observe them. Offer a visual plateau-only
scope with explicit edge/timing exclusions. A missed observation is incomplete,
not a pass or permission for another RF job. Do not keep RF running while
waiting for an operator reply. External configurations require exact wiring
and pin/polarity approval. Restore the prior inhibited firmware and retained
settings, verify output inactive and record restoration before reporting.

## Adversarial review and disposition

Perform an adversarial assessment of concurrency, activation ordering, stale
acknowledgements, unsafe cancellation, write-failure truth, skipped polling,
all output configurations, mode coverage, protocol compatibility and claims.
Track each actionable finding with its repair and regression evidence. Rerun
affected checks and conduct a fresh second assessment; iterate until no
actionable source finding remains. Document any remaining physical gates as
open and avoid claiming complete P13.1 target qualification.

Update the backlog, roadmap and development guide with the actual software
disposition and the physical packet. Commit only this slice, push without
force and independently verify `HEAD` against remote `devel`. Report the
prompt/review/packet paths, changes, validation, remaining qualification,
commit, remote parity and final working-tree state.
