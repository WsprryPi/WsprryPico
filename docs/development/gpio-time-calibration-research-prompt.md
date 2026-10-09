# Execution prompt: retained GPIO/NTP evidence research

Authorized and executed in this chat on 2026-10-09. Work in the existing
WsprryPico `devel` checkout. Produce repository documentation and a bounded
local, ignored evidence companion. Do not create a project, branch, commit or
publication. Read README.md, CONTRACT.md, docs/architecture.md and AGENTS.md;
inspect current Git state and preserve all unrelated work.

## Objective and selected scope

Execute a file-only investigation of already-recorded Phase 14 telemetry to
determine what it can establish about NTP observation quality, software UTC
corrections, oscillator-rate estimation and the need for future filtering or
discipline. Persist the three stages selected by the operator:

1. Assess NTP filtering and UTC clock discipline first.
2. Consider NTP-derived Pico calibration for GPIO transmissions second.
3. Consider optional GPS UTC + PPS third.

Si5351 remains a conditional future addition depending on ongoing GPIO RF
qualification. It is deferred and outside this work, including CLK2 feedback.
No hardware purchase or firmware implementation is selected by this prompt.

## Authority and prohibitions

Documentation creation/updates are authorized. Product source/tests, maintained
scripts, build definitions and configuration changes are not. One-off local data calculations are analysis,
not maintained application code; retain their reproducible method with the
research companion and document all assumptions.

Remote access is limited to read-only file listing, metadata, and reads of
explicit evidence files on wspr5. A read-only elevated file read is permitted
when campaign evidence is root-owned. Do not invoke campaign helpers, service
APIs, device commands, serial ports, USB, GPIO, RF, receiver/reference control,
network changes, packet capture, process control, scheduling or firmware loads.
Do not send another chat a message. Do not change the running campaign, add
requests or jobs, extend its durations, change thresholds or reinterpret an
original failure as a pass.

## Evidence selection and preservation

1. Identify the original closed eight-hour soak through its summary
   `build/resume-tools-dbf1f3e/build/follow-on-eight-hour-soak/result.json` under
   `/home/pi/phase14-qualification-20261008`. Verify CONTROL_COMPLETE, eight
   finite jobs, paths and original acquisition identities. Keep the browser-load
   failures as failures; closed acquisition alone is not acceptance.
2. Inspect summary and child-file metadata before transfer. Prefer that bounded
   cohort rather than scanning all captures. Exclude currently PENDING/RUNNING
   browser repeats and all raw IQ files. If local retained copies already exist,
   use verified copies to avoid additional host reads.
3. Copy only required closed regular files to a new ignored local research
   directory. Preserve exact source paths, byte sizes, SHA-256, collection cutoff
   and transfer identity. Check for symlinks/path substitution. Check source
   stability across the bounded read and verify copied bytes locally. Do all
   analysis on the Mac, not on the capture host. State actual transferred bytes.
4. Record acquisition firmware, tool snapshot, board, boot, nominal clock,
   mode/workload, job identity and reference/receiver evidence applicability.
   Do not equate current devel HEAD with the historical acquisition image.
5. Keep raw files private/ignored. Publish only necessary sanitized aggregate
   findings, hashes and reproducible method, with no credentials or private
   SSIDs, keys, certificates, backups or IQ.

## Source/schema verification

Read the acquisition tool/firmware source available through Git history or its
recorded snapshot. State whether the source-to-executed-bytes association is
attested by the intake, recorded elsewhere, or only contextual; do not infer
process identity solely from a directory name. Trace INFO event envelope, clock snapshots, counters,
RTT/uncertainty semantics and snapshot ordering. Distinguish host timestamps
from device UTC/monotonic timestamps. Enumerate schema variants, missing fields,
duplicates, truncation and timestamp/identity inconsistencies. Do not assume the
event payload is named `data` or `value` without inspecting it.

The current UTC model is offset-only. For a coherent valid clock snapshot,
derive anchor monotonic = device monotonic - sync age, and anchor UTC = device
UTC - sync age; offset = device UTC - device monotonic. Use integer arithmetic
for nanoseconds. Confirm the formula against the acquisition source. Do not
interpret unsynchronized/sentinel values as valid anchors.

Deduplicate anchors within each board/boot/firmware/clock/source partition.
Counters that advance by more than one imply potentially missed exchanges, not
one observed sample. Counter/clock fields need not describe the same instant;
identify mismatches instead of forcing joins. A latest RTT or sample uncertainty
can belong to a rejected exchange; use accepted-count transitions and available
clock information to determine what association is actually defensible.

## Analysis and decisions

- Report coverage, timestamps, observation cadence and gaps per board/job.
- Report valid clock-state/age/uncertainty distributions, peer changes and
  accept/reject counter deltas. Include failed acquisitions when relevant and
  separate acquisition completion from RF/browser acceptance.
- Report UTC-offset update sizes and source disagreement/recovery where visible.
  Compare Running/idle only where coverage supports the comparison; absence of
  idle evidence is a gap, not a zero effect.
- A preliminary rate fit may use distinct anchors over long spans. Compute
  Pico error = (delta raw monotonic / delta reference UTC - 1)*1e6. Inspect
  monotonicity, endpoint sensitivity, disjoint-window consistency, peer/source
  changes and timestamp uncertainty. Avoid epoch-scale floating-point loss.
  Label fits apparent rate only: network delay/asymmetry and drift can confound
  them. Missing source provenance precludes validated SNTP-only calibration.
- Quantify how timestamp errors translate into apparent PPM. Do not confuse
  sample spread, a regression standard error or receiver repeatability with an
  absolute oscillator uncertainty bound. Preserve conservative bounds.
- Cross-reference existing RF results only when board/boot/image/time and
  receiver/reference scopes actually align. Do not transfer RF qualification or
  infer thermal causation from unmeasured temperature.
- Decide separately whether the data justifies a bounded filtering prototype,
  UTC rate-discipline prototype, automatic RF calibration, or only further
  evidence. Do not presume every stage should be implemented.
- Preserve the current 500 ms/90-second launch gates. Describe future rate-aware
  forward/inverse UTC mapping, manual correction fallback, prepared-job freezing
  and optional PPS capture/holdover as proposals.

## Deliverables

Maintain `docs/development/gpio-time-calibration-plan.md`, create/update
`docs/development/gpio-time-calibration-research.md`, and retain this complete
prompt. Link the plan from the roadmap and reconcile the Si5351 backlog to the
operator's conditional deferral without changing historical acceptance records.
Include exact input inventory/hashes, source line references, checked numerical
results, missing evidence, prioritized follow-ups and a reproducible local
analysis companion. Leave all files unstaged and uncommitted.

## Adversarial review and closure

After drafting findings, deliberately challenge identity/time/source joins,
integer precision, duplicate-anchor counts, accepted-versus-rejected sample
association, uncertainty calculations, sampling bias, purported no-impact
claims, outcome preservation, Si5351 scope, secrets and repository changes.
Independently recompute consequential numbers using a second method. Inspect
documentation links and whitespace. Fix actionable research/documentation
defects, rerun affected checks, and perform another assessment after repairs.
Record findings, fixes and remaining evidence limitations. End with a scope-bound
review verdict and report actual Git state. Do not claim source tests or new
hardware qualification were performed.
