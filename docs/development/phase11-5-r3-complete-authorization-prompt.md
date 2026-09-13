# Complete extended-job implementation and Phase 11.5 R3

Prompt ID: **R3-COMPLETE-20260913-v2**. This complete replacement supersedes
v1 and incorporates the selected QRSS-group roadmap decision in Pico commit
`880a6cb2d185eab8fb9c41c025500bf54b09f04e`.

**Preparation only until the user accepts this prompt.** Acceptance authorizes
the complete scope below: the prepared D0 diagnostic; the selected 32-character
and 60-minute product limits; necessary Pico firmware, browser and Pi WTP-client
implementation; diagnostic/repaired/final deployments; extended finite RF
acceptance; recovery; adversarial review; affected retesting; and commit/push.
Do not start those operations merely because this prompt has been written.

## 1. User instruction and effect of acceptance

Complete Phase 11.5 R3, saturation and reclamation, across WsprryPico and its
WsprryPi integration. Diagnose and repair the current allocation panic. Implement
the selected QRSS, FSKCW and DFCW message and duration limits before final R3
acceptance, so R3 is not closed against a superseded short-job implementation.
Complete every mandatory R3 assertion and the extended-job checks below on the
final applicable firmware and companion client. Perform an adversarial review,
fix actionable findings, and reassess until no actionable
finding remains. Commit and push the scoped changes, then report the actual
acceptance and repository state. A prepared image, passing subset or committed
report is not completion of R3.

**My acceptance of this prompt is standing authorization for all operations
listed here. It also confirms that the documented 50-ohm, 60 dB conducted wiring
remains unchanged.** If I identify a wiring change when accepting, reconcile it
before RF instead of assuming this confirmation.

This authorization remains effective through R3 completion, across turns,
compaction, source revisions, diagnostic findings and fresh execution packets,
unless I revoke it. It explicitly replaces the earlier requirement to obtain
another approval for each R3 firmware image, Wi-Fi recovery cycle or finite
retry. It includes the D0 packet identified below; no separate D0 approval is
needed after accepting this prompt. Acceptance explicitly includes the longer
RF jobs, expanded event capacity, new lease/observer/fixture budgets, required
message/duration UI changes and matching Pi client validation described below.
Do not treat these necessary implementation changes as new scope needing another
approval.

The old 40-job / 4,423.68-second aggregate envelope and spent per-attempt grants
remain historical accounting, but **are superseded as limits on this newly
authorized completion campaign**. There is no fixed aggregate number of jobs,
flashes, repair iterations or fixture sessions. Execute only work justified by
an outstanding R3 or selected extended-job assertion, a concrete diagnosis,
an affected regression or restoration. Every individual packet and RF job must
remain finite and within section 5. This is permission to complete the engineering work, not permission
for unattended endless transmissions or blind repetition.

Before each tranche, prepare and review its exact executable packet, hashes,
jobs, expected transitions, observations, counters and cleanup. Then execute
without asking me to approve it again. Newly built hashes are frozen by this
review process; future images do not need to have been knowable when I accepted
this prompt. Superseded prohibitions in older prompts, proposed allowances and
historical packet documents do not undo this authorization. Preserve those
documents and their failed results rather than rewriting their history.

Ask for additional input only for an action outside the fixed scope here, a
material unresolved product choice, conflicting user work that cannot be
isolated, unavailable physical access, or an output/identity condition that the
authorized mechanisms cannot reconcile. Do not promise that this prompt can
override platform enforcement. If automatic approval review rejects an action,
first show its connection to this accepted scope or use an equivalent permitted
method; if still blocked, identify the exact rejection and reason candidly.

## 2. Repositories, current evidence and required reading

Primary repository: `/Users/lbussy/GitHub/WsprryPico`, branch `devel`, last
observed commit `880a6cb2d185eab8fb9c41c025500bf54b09f04e`. At preparation this
prompt is untracked. Companion: `/Users/lbussy/GitHub/WsprryPi`, branch
`devel`, last observed commit `ef9a76a5be4d8223b89bcd64df1e1a376d48a0a5`.

These are orientation snapshots, not rollback targets or frozen build pins.
WsprryPi's newer Issue 446 legacy-GPIO work is independent of this WTP/Pico
campaign. Its currently modified `docs/issue-446-validation.md` and untracked
`docs/development/issue-446-rf/` belong to other work and must be preserved.
Refresh both histories and working trees before editing. Do not stage, commit,
reset, stash, overwrite or attribute unrelated work to this campaign.

Creating isolated `codex/` branches/worktrees is authorized when needed. Pi
implementation changes are explicitly authorized for its Pico-facing WTP job
compiler, encoders, message validation, capability negotiation, duration display,
progress/deadlines, cancellation/disconnect handling and associated UI/tests/docs
needed for the selected limits or an R3 defect. This is not a general refactor
or permission to impose new limits on unrelated Pi hardware backends. Preserve
Issue 446 changes and the legacy GPIO path. Do not modify other repositories
or `Wsprry_Pi_Docs`.

Read applicable AGENTS.md files, Pico README.md, CONTRACT.md,
docs/architecture.md, docs/implementation-plan.md (especially the selected
QRSS-group limits), and docs/development/README.md. In the Pico development
directory, read:

- `phase11-5-plan.md`, `phase11-5-acceptance-ledger.md` and
  `phase11-5-metrics.md`;
- `phase11-5-r3-completion-result.json` and
  `phase11-5-r3-completion-review.md`;
- `phase11-5-r3-a1h2-result.json`, `phase11-5-r3-b1-failure-result.json`,
  `phase11-5-r3-b2-result.json`, `phase11-5-r3-c0-failure-result.json`;
- `phase11-5-failure-triage.md` and
  `phase11-5-r3-allocation-d0-execution.md`;
- `phase11-5-r2-continuation-review.md` for assertion-level reuse boundaries.

Also inspect docs/protocol/WTP.md, its schema and docs/browser-api.md before
changing their implementations. Follow existing build commands and pinned
dependencies; do not invent commands or install an SDK incidentally.

Current acceptance is **R1 5/5, R2 7/7, R3 OPEN, R4–R6 not run**. No complete
Phase 11.5 configuration is accepted. R3 has five of fourteen register groups
complete, PROGRESS partial, and nine groups still requiring completion. A1h2
and B2 passed 24 pressure cases including their controls/recovery cases; these
are not 24 register groups. TLS-VALID, TLS-SLOW, TLS-FAIL, SLOT and HTTP-PARTIAL
are complete only within their recorded old-image scope.

Preserve all earlier failures. B1's early ACK filter was a confirmed harness
mistake. C0 recorded the target's pinned `Out of memory` panic, hash 3833354787,
stage 5, during a valid maximum-payload attempt. The exact failing allocation
and complete delivery of that request remain unknown. A fresh-boot success
alone cannot establish a fix for the failure following prior contention.
The roadmap change is documentation-only so far: current firmware still has
162 events / 110.592 seconds. The existing five R3 groups retain their old-image
credit; this does not pre-accept the forthcoming capacity/layout changes.

Evidence archive SHA-256 identities:

| Evidence | SHA-256 |
| --- | --- |
| A1h2 accepted subset | `6c6c34d81048bdd07a970899dfbff845711d3c52f924d373ae00756785fe63f3` |
| B1 failed attempt | `412c493b11eddfc8a5e51c7870f1917986ae0977eca40751f5565dbb78b507b2` |
| B2 accepted subset | `b2359326fe3faa870ec800e2f5f2a5a24fd709c25a5e073a4cff6c435de39c44` |
| C0 failed attempt | `7fea4b144454fc7c4ffe909dc61450f1078f2753f564ad4916229047602cd06d` |

Local evidence is under build/phase11-5-r3-retained-a1h2/,
build/phase11-5-r3-transport-b1/, build/phase11-5-r3-transport-b2/ and
build/phase11-5-r3-capacity-c0/. C0's separate reconciliation and host diagnostics
are bound by its failure-result JSON. Use the existing independent auditors;
never replace frozen evidence with a replay that happens to pass.

## 3. Fixed hardware, RF and host boundaries

Pico A is the sole mutable DUT: Pico 2 W / RP2350, USB serial
`0BF4B4AEC9FFB344`, WTP ID `fd6127d11d6aca42a9905fa3fb1bf1d5`, GP2 PIO/DMA,
138 MHz system/sample clock, divider 1, RAM renderer and TLS/HTTPS port 18443.
Keep the same per-device identity, credentials and certified name
`wsprrypico-0a60df.local` unless a documented R3 defect requires regenerating
expired test credentials for that same identity. Any new fingerprint must be
recorded prospectively and authenticated; do not bypass certificate checks
globally or convert identity failures into passes.

The last physical source is `2e43110f05304efdc2ae25c298baa0ef6426955b`, UF2
`7e6e732cc7a9e196609413dfe228781a725ece56bed1b4a99a96d1cc8741baf6`.
Last reconciled A boot: `bccea7c09794539c4f64bc22b0e76c56`, in recovery,
Empty/inactive/unowned. These are recorded facts, not fresh admission.

Pico B remains read-only: serial `CDDBF8767C506C07`, WTP ID
`29f20b7342051ef947aa56cb9d4fab42`, last boot
`feffcd075ab6cb0b74e7e0c2fde6c87f`, inhibited revision `dbf1d86f0885-dirty`.
Do not flash, reset, reconfigure or transmit from B.

Keep the documented 50-ohm conducted path: A's GP2 branch and the GPSDO branch
each have 20 dB before the combiner; combiner output has 20+10+10 dB to the SDR.
Do not change cabling, filters, attenuation, receiver tuning/gain/calibration,
GPSDO configuration/output, Pi GPIO4 or another RF output path. This is resource
and contention acceptance, not a new spectrum, band, clock or calibration study.
An affected R1 regression may also use the existing standard **RF-inhibited
150 MHz** configuration on A, with verified inhibition and its own image/clock
identity. Return to the admitted physical 138 MHz configuration before any RF.
This exception does not authorize physical RF at 150 MHz or another clock.

Use SSH host `wspr5` and its established authenticated management route. The
last host boot is `220e53ca-ca95-4206-9581-dbe28aa1eeb8`. Protect the installed
WsprryPi service and executable, previously PID 1957 and SHA-256
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`.
Do not stop, replace or restart that service, reboot the Pi, change its kernel,
or install an R3 build over its production binary. The PID/hash above are last
recorded provenance, not a demand to restore an older user-installed version.
Read and protect the current verified service/executable state. A changed PID,
boot or unrelated repository commit must be reconciled against actual identity
and relevant source impact; it is not by itself a reason to discard evidence or
request routine approval. Run qualification clients as separate identified
executables whose exact source, dependencies and hashes are recorded.

Preserve eth0 MAC `2c:cf:67:62:76:64` and wlan1 management MAC
`90:de:80:47:b9:da`. The isolated test radios are wlan0/AP MAC
`2c:cf:67:62:76:66` and wlan2/client MAC `e8:4e:06:ae:d7:09`, with AP/client/A
addresses 10.77.15.1/.2/.10; A's station MAC is `88:a2:9e:0a:60:df`.
Verify interfaces by hardware identity rather than assuming names survived a
re-enumeration. Protect chrony/GPSD/PPS, permanent Avahi/time.local configuration
and all unrelated host services and management routes.

## 4. Selected product contract and implementation requirements

Implement the user-selected roadmap, not an approximation:

- **32 characters including spaces**, uniformly for QRSS, FSKCW and DFCW.
  Count every supported character equally. Preserve the existing supported
  Morse alphabet, case/spacing semantics and WSPR framing; add no new alphabet,
  punctuation or prosigns. Do not silently truncate, split into smaller messages
  or reduce the character limit for complex Morse. Validate consistently at
  advertised message-entry routes, including the Pico-facing Pi client.
  Distinguish QRSS-group message text from WSPR station/callsign validation.
  Do not infer a character count from arbitrary raw-event jobs; those retain
  their explicit profile, event, duration and payload constraints.
- **3,600 seconds maximum total finite-job duration**, including all repetitions,
  inter-message gaps and required boundary/tail intervals. Message length and
  duration are independent limits. Show the calculated duration before submission
  and explain a duration/event/payload rejection using that actual limit. A
  supported 32-character message can still exceed 60 minutes at a chosen slow
  speed; reject that duration without inventing a smaller character cap.
- Derive the required event capacity from the worst-case supported 32-character
  message in every mode, including RF-on/off transitions and all required job
  boundaries. Do not guess that 162 events is sufficient, or that increasing
  only CAPS implements the feature. Publish the derived count and comparison
  with actual engine, service, protocol, schema and client limits.
- Resolve finite repetition representation as a documented engineering decision
  before implementing it. The 32-character message limit does not bound expanded
  repeat events. Use bounded expansion within negotiated event/payload limits
  where sufficient; reject impossible combinations clearly. Do not promise that
  every speed/repetition combination fits. If a compact representation is needed,
  keep the whole finite job resident before ARM, bound all repeat counts and
  arithmetic, negotiate/version any wire extension, and preserve existing
  `rf-events/1` semantics and old-client behavior. Selecting this implementation
  approach within these requirements is authorized without another approval.
- Preserve WTP/1's existing 512-event protocol ceiling for `rf-events/1` unless
  an explicitly versioned compatible extension is required and implemented in
  both repositories. Do not silently send a larger event array under the old
  profile. Keep WTP device-neutral and do not create a third protocol repository.
- Keep the fixed waveform buffers and local RP2350 timing. Do not allocate RF
  sample storage proportional to an hour of output, grow buffers simply to hide
  starvation, or stream per-symbol/per-repeat timing from a client. Audit total
  peak memory across JSON framing/parsing, job copies, replay/retained objects,
  RF plans and core handoffs. Avoid enlarged plan arrays or temporary copies
  exhausting either 16 KiB stack; retain the heap and stack reserve gates.
- Audit duration, nanosecond/sample conversion, event offsets, repeat/gap sums,
  DMA accounting, completion, terminal retention, progress percentages, timeouts
  and cancellation for overflow and narrowing. An hour at 138 MHz contains
  **496,800,000,000 samples**; do not assume 32-bit counts suffice or multiply
  nanoseconds by sample rate without proving intermediate bounds. Preserve
  intended modular phase arithmetic separately from elapsed-time accounting.
- Align advertised capabilities, engine enforcement, portable validators, native
  client compilation, browser/API behavior and displayed duration. The existing
  65,536-byte WTP payload, 32,768-byte HTTP body and 30,000-byte browser-file limits
  remain distinct constraints, not interchangeable message-length limits.
  Guarantee the selected 32-character capability on the message-entry routes
  advertised as supporting these modes; where necessary provide a bounded
  message-compilation path rather than requiring an oversized expanded JSON
  file. Raw event files remain subject to their documented upload limits.
  Do not silently raise transport limits to make a test pass.

Read current implementations rather than relying on these code pointers alone:
`src/rf/waveform.hpp/.cpp`, `src/rf/wtp_profile.hpp`, `src/rf/pio_dma_sink.cpp`,
`src/rf/pico/worker*`, portable job/encoder and standalone code, WTP codecs,
profiles/schemas, browser/API code, and the corresponding Pi WTP compiler and
execution backend. Update user-facing docs inside the two authorized repositories
where behavior changes. The standard inhibited variant must remain inhibited.

The extended feature's boundary, cancellation and transport-loss regressions
are in scope even where they overlap R2/R4 concepts. This does not authorize
running all R4–R6, Phase 11.6 per-band acceptance or Phase 13 endurance/spectral
qualification. The hour-long checks below are finite product-boundary and R3
resource acceptance, not a claim of long-term reliability.

## 5. Operations explicitly authorized by accepting this prompt

The following permissions are affirmative and include necessary SSH, sudo,
file transfer and process execution on the named Mac repositories and wspr5.
They do not authorize activity against another host or device.

| Operation | Authorized scope and finite limits |
| --- | --- |
| Source and tooling | Implement the selected limits in Pico and its Pi-facing integration, plus necessary allocator, parser, transport, retention, timing, UI, diagnostics, harness and auditor changes. Preserve existing supported behavior and the selected product limits. Necessary companion changes are authorized, not deferred for another approval. |
| Builds and delivery | Build standard inhibited and physical standalone variants from identified clean source. Stage source/helper/schema dependencies, test binaries and exact private firmware into fresh task-owned roots under `/home/pi/phase11-5-r3-*`. Read back hashes and run linked-image/flash-reservation checks. Do not replace the installed Pi application. |
| A USB and firmware | Exclusively open A's Console/WTP endpoints; collect diagnostics and private backups; issue BOOTSEL; load, verify and start reviewed diagnostic, repaired, final or recovery images. Each packet permits at most one flash sequence, one BOOTSEL transition and one additional controlled software reboot. Multiple reviewed packets are authorized as needed. A flash's load/start is recorded separately from an extra reboot. |
| Finite RF and modes | Authorize complete finite QRSS, FSKCW, DFCW and diagnostic Tone jobs of up to **3,600 seconds each**, including repeats, gaps and tail, after the deployed image advertises and passes idle admission for that duration/event capacity. Until then obey its smaller CAPS. WSPR retains its existing framing/duration. Nominal frequency is 135,500 Hz, with only native mode shifts inside 135,490–135,510 Hz. Record every event frequency or bounded repeat pattern before ARM. No continuous output or autonomous schedule is authorized. |
| Packet RF budget | At most **16 jobs and 14,400 seconds total planned finite-job duration per packet**, charging complete planned duration, including gaps, for failed/uncertain submissions. At most one job executes at a time. Four hours is a packet ceiling, not a target; use shorter jobs when sufficient. Multiple reviewed packets and necessary affected R1/R2/R3 retests are authorized without a campaign-wide quota. |
| Job control | HELLO, CAPS, clock/status/diagnostic reads, CLAIM, RENEW, LOAD, ARM, ABORT, RELEASE and required replay/admission checks through USB, production WTP and the actual browser. Bind every stateful action to exact device/boot/session/owner/job identity. Use the campaign owner for normal abort/release and the existing finite local completion behavior. |
| Isolated fixture | Create/use/remove the established AP/client namespace, temporary AP profile, DHCP/DNS/mDNS/time.local fixture processes, captures, scoped routes and task-owned systemd units. Temporarily pause and restore `pi-wifi-recover.timer` and its service using the established fixture. Temporarily allow and restore chrony access for 10.77.15.0/24. Preserve permanent service configurations and management connectivity. |
| Network recovery | While A is authoritatively inactive, perform up to three logged Wi-Fi OFF/ON cycles per packet and necessary owned-fixture cleanup/recreation after a diagnosed admission problem. Do not loop on a transient JOINING sample or treat a successful AP association as proof of device IP/clock readiness. |
| Fault injection | Against A and the isolated fixture only: bounded TLS failure/slow-handshake cases, partial and oversized input, stalled readers/writers, TCP close/reset or ACK suppression, slot/session/replay/terminal pressure, declared combined overload, long-job owner abort and post-ARM transport loss. Freeze exact bytes, tuples, counts, rates, trigger times and deadlines. Never turn unspecified traffic volume into a test. |
| Configuration | Keep the current test configuration with standalone scheduling disabled. Zero CONFIG saves by default. Up to two ordinary API saves per packet are authorized only if necessary to establish or restore that test baseline; record the actual need and count first. Do not restore an obsolete original configuration, erase journals, reset counters, perform endurance writes or deliberately exercise R5 rotation/scheduling. |
| Allocation diagnostics | Read-only metrics plus at most four reviewed finite allocation probes per packet, idle/unowned only, each size bounded by the linked heap capacity and a stated diagnostic hypothesis. No allocation probe during Loaded/Armed/Running work. A diagnostic expected panic must be idle, explicitly declared and scored as diagnosis, never supported-load acceptance. |
| Browser and dependencies | Automate the real target UI in existing Chromium with a task-specific profile and isolated test trust/credentials. Install missing user-space test dependencies in a task-local environment if necessary. Installation of `libnss3-tools` on wspr5 is authorized if needed for certificate handling. No general OS upgrades, incidental SDK/toolchain upgrades or unrelated packages. |
| Evidence and publication | Collect private raw evidence and image/tool/configuration hashes; publish sanitized source, tests, execution records, results and documentation. Commit and push attributable changes to each repository's `origin/devel` with ordinary non-force integration. Isolate conflicting work; do not require an unrelated user's checkout to become clean. |

Each physical fixture session is at most **28,800 seconds (eight hours) of
execution plus 900 seconds reserved for cleanup**. This accommodates three
hour-long reclamation cycles and their required expiry/quiet observations;
for example, three 3,600-second jobs plus three 3,660-second expiry windows
already require 21,780 seconds before other work. Freeze the actual smaller
schedule and storage/observation budget. Long jobs do not loosen per-request,
handshake, progress, abort or RF-service deadlines. Use independently supervised
processes and short monitoring calls so the assistant remains responsive.
Update old short-run validators, lease-renewal counts, record/capture limits and
supervisor deadlines in new reviewed tools/packet schemas; preserve consumed
packet bytes and historical scoring. Prove the expanded runtime bounds with
hardware-free boundary/failure tests before running the long cases.
Packets may share an already authorized session when its ownership and remaining
window permit it. For a further
session, finish and verify cleanup, then activate a fresh reviewed session under
this standing authorization. Do not silently extend an expired timer or replay
a consumed root. Expiry is an administrative boundary, not a firmware failure.

No aggregate counter resets are permitted. Starting historical totals in the
completion ledger are nine completed jobs / 900 seconds, four Wi-Fi cycles,
37 CONFIG saves, six heap probes, zero commanded flashes/reboots in that effort
and one unexpected C0 watchdog reboot. Preserve the earlier A1b job separately
in its existing campaign accounting. Record all new starts, uncertain outcomes,
completions and recovery operations without erasing those distinctions. Charge
an uncertain RF submission its entire planned duration until reconciled.

## 6. Admission, diagnosis and authorized recovery

Before physical mutation, verify A/B and host identity, source/image, saved
configuration, current authority, fixture ownership, observers, credentials,
space and clock readiness appropriate to the operation. Detect other live
campaigns using shared radios, ports or RF/receiver equipment; do not kill or
commandeer their processes. Clock synchronization
is required for ARM, not as an artificial prerequisite to an idle USB diagnosis.
Retain the test configuration; automatic Wi-Fi association after a normal boot
is included in the authorized image-start operation.

Arm independently supervised host cleanup before the first fixture mutation.
Cleanup must survive SSH loss and always attempt A and B reconciliation
independently. Before ARM, prove that the entire scheduled job, launch lead,
completion observation and guarded cleanup fit within the remaining session.
For long jobs budget observer records, capture storage and cleanup explicitly;
never let an old 300/360-second runner or renewal limit terminate an hour-long
measurement. Preserve the target's extended Armed/Running lease semantics and
its ability to finish after transport loss. The supervisor must stop new RF submissions if an observer dies,
the boot changes unexpectedly, an authority invariant fails or a declared
resource/timing gate fails. Preserve pending writes and primary errors;
secondary USB cleanup errors must not replace the original failure.

An unexpected fault stops that packet's dependent work, **not the entire R3
engineering campaign**. Preserve the evidence, classify the failure, obtain
authoritative state and fix or prepare a specific diagnostic hypothesis. Once
A is confirmed inactive and host/device identity is reconciled, controlled
reboot, diagnostic/repaired/recovery flash, idle Wi-Fi recovery and an affected
rerun are already authorized in a fresh reviewed packet. No further user
approval is needed. Do not rerun unchanged input merely hoping for a pass.

Disconnects, missing ACKs, terminal expiry, timeouts and changed counters do not
prove RF inactive. Observe the finite job and query authoritative state; use
the known campaign owner's ABORT where valid, then reconcile. A known completed
owned job may be released. Never replay an uncertain ARM with a new identity.
For a planned acknowledged BOOTSEL, verify the exact serial in the ROM loader
before flashing. A verified non-RF ROM state is distinct from an unexplained
USB disappearance. If neither runtime nor a verified non-RF state can be
established, stop device mutations and request the necessary physical help;
host cleanup must not reset an output-unknown Pico.

Separate fault classes in each result: confirmed firmware defect, confirmed
harness/assistant defect, environment/prerequisite failure, observation failure,
expected bounded rejection, authorization/platform block, or unresolved cause.
Use raw byte counts, CRC/schema, device/boot/owner/job identities, timestamps,
packet captures, target counters/panic records and independent final inventories.
Do not call an expiring test certificate a target bug or a target allocation
panic an AI error. This is authorized testing of the user's own equipment;
do not invent a cybersecurity prohibition or hide an actual tool rejection.

## 7. Execution sequence: diagnosis, extended implementation, then final R3

D0 is already prepared locally and is expressly included in this approval:

- Packet: `build/phase11-5-r3-allocation-d0/stage/packet.json`, SHA-256
  `349634192b03f8a79bc8ef72c43eb30b6da201b35a79d3cc35067380de70c25c`.
- Candidate source: `481da3c3ff171bae53d6c7d1d2e30525ae748f4b`, embedded
  `481da3c3ff17`.
- Candidate: `build/phase11-5-r3-allocation-d0/diagnostic.uf2`, SHA-256
  `5589b165b3cce03f2dc2f351088c88f08d7a5ebbf6c10702c17d0d38424bc534`.
- Public tooling archive SHA-256:
  `1bf25435cccbf03ba61d58c01fb6b7abb27723b1490576e0702f5cf3205e3527`.
- New host root: `/home/pi/phase11-5-r3-allocation-d0-20260913`.
- Existing host picotool: `/home/pi/phase11-4-e1/picotool-build/picotool`,
  SHA-256 `4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921`.

Revalidate those artifacts before delivery. D0's one flash and one idle
65,536-byte STATUS attempt retain their frozen 600-second scope, without RF,
CONFIG saves or Wi-Fi commands. Run it unless an independently established
diagnosis makes that physical probe unnecessary; record the reason for any
omission. Do not broaden the frozen D0 executable. Its stopping condition
returns control to this completion campaign, whose reviewed follow-on work is
already authorized.

The candidate records each core's last allocation size and NULL/non-NULL result
in tagged watchdog scratch when the SDK allocation panic occurs. It is not an
OOM repair. Audit the raw outcome, including partial writes and fresh recovery
INFO. Do not assume the failed allocation is 65,552 bytes or assume fragmentation
without evidence. If a fresh boot passes, reproduce or model the relevant prior
allocation/retention history before calling C0 repaired.

First establish and repair the C0 allocation mechanism, then implement the
selected limits with meaningful host failure-path and boundary tests. The work
may share a demonstrated memory/ownership repair, but retain separate causal
claims for C0 and the new feature. Do not present enlarged memory headroom or a
fresh reboot alone as the C0 repair. Establish the extended design and host
checks before broad final-image physical acceptance to avoid qualifying an
intermediate configuration that is about to change.

Preserve WTP/HTTP/browser transport limits, enlarge the engine's message/event/
duration support as selected, and update all affected contracts coherently.
Lowering selected limits, weakening reserve/timing gates or avoiding the
supported maximum is not closure.
Build and review exact ELF/UF2, allocator interception, heap/stack/flash layout,
RAM renderer/worker placement and normal startup before every changed image.
Firmware must preserve the configuration journals and ordinary output authority.
Keep image material and credentials private. Once reviewed, deploy and test
within the standing authorization; repeat diagnosis/repair/review as required.

Use a staged extended-image admission: fresh inactive identity/guards, minimum
finite-job smoke test, representative job beyond the old 110.592-second/event
limits, then the mandatory maximum and contention cases below. Freeze each
stage's acceptance first and preserve failed stages. A passing short smoke
test does not qualify the one-hour boundary.

For every source change, map affected assertions explicitly. Allocator/layout/
TLS lifetime changes can invalidate broad resource evidence. Refresh affected
R1/R2 measurements and already-passed R3 groups where necessary; reuse only
demonstrably unaffected evidence. Do not automatically rerun all R1/R2, and do
not transfer old-image physical measurements to a new image by changing labels.

## 8. Extended-job checks and mandatory R3 completion register

Complete and record these feature checks in addition to the fourteen groups:

1. **Message boundaries:** real production encoder/validator tests for 31, 32
   and 33 characters in all three modes, spaces included, supported alphabet,
   worst-case Morse complexity, and existing invalid/empty input behavior.
   Prove 32 succeeds whenever duration/event/payload constraints are satisfied;
   33 fails without truncation or silently splitting into multiple jobs.
2. **Duration boundaries:** below, exactly at and just above 3,600 seconds,
   using the actual representable API units and any required terminal tail.
   Include repeats/gaps and overflow attempts. Exactly at the limit succeeds;
   above-limit input fails atomically without RF or corruption. Verify displayed
   duration against the target's immutable job and actual compiled events.
3. **Events and memory:** derive and test the worst supported 32-character
   message in QRSS, FSKCW and DFCW, actual advertised event maximum and maximum
   plus one, repetition expansion/compact limits and peak live memory across
   each submission path. Distinguish the largest event count, largest wire body
   and longest duration; none alone proves the others. Use the real RF renderer
   and large-index arithmetic in host tests rather than wall-clock sleeps.
4. **Physical maximum duration:** complete at least one actual 3,600-second job
   in each of QRSS, FSKCW and DFCW on the final applicable physical image, with
   full-duration independent authority/resource observation and predeclared
   contention. Include real message/keying transitions through the interval;
   a short message followed by idle padding does not qualify sustained operation.
   Also execute each distinct worst-case 32-character plan; combine with the
   hour-long cases where valid without falsifying either maximum.
5. **Paths and lifecycle:** cover USB reference, native Pi production WTP and
   actual browser/API across the physical feature matrix, identifying what each
   path supports. Exercise successful complete jobs, owner cancellation in Armed
   and Running, and local completion after acknowledged ARM followed by transport
   loss, with correct retained result and same-session reconciliation. Cover
   source-distinct mode/path implementations; reuse generic paths only with
   an explicit impact/equivalence argument. Include abort after more than
   110.592 seconds on a long job. No abort/reset may be counted as a completed
   maximum-duration job. These selected-feature checks do not close R4.
6. **Compatibility:** preserve ordinary WSPR framing and old finite jobs,
   rejected-operation precedence, atomic LOAD and fixed local waveform buffers.
   Test new clients against old/smaller CAPS and old supported clients against
   the new target where applicable. No silent fallback that truncates duration,
   reduces message length, changes frequency or divides one atomic job into
   host-timed executions is allowed.
7. **Sustained resources and reuse:** connect these results to R3's maximum,
   overload, retained-state and three equivalent reclamation cycles. Host virtual
   time cannot replace the physical hour-long jobs; physical jobs cannot replace
   exhaustive arithmetic/boundary tests. This is finite acceptance, not Phase 13
   endurance qualification.

Document a matrix mapping each feature check and R3 assertion to exact
source/image, mode, submission path, job IDs, evidence and auditor. Counts for
feature checks and pressure cases are separate from the fourteen R3 groups.

Maintain all fourteen groups, with separate assertions for distinct mechanisms.
For each, record PASS, PARTIAL, FAILED or NOT_RUN; exact source/image/boot;
raw archive and auditor identities; and reuse rationale where applicable.

| Group | Required completion evidence |
| --- | --- |
| TLS-VALID | Valid authenticated production WTP and HTTPS positive controls, supported concurrency, current resource/timing evidence. Reuse A1h2 only where unaffected. |
| TLS-SLOW | Activated incomplete handshake with the actual handshake deadline and reclaimed authenticated reuse. Do not substitute pending-slot expiry. |
| TLS-FAIL | Distinct target failed-handshake alert acknowledgement and approximately one-second unacknowledged-alert lifetime. Preserve B2's prospective server-flight-first, zero-payload-ACK suppression policy and raw target/packet proof. |
| SLOT | Both active slots, the one-WTP restriction, pending admission and its independent ten-second expiry, excess rejection and fresh slot reuse. |
| HTTP-PARTIAL | Partial headers and partial bodies independently; 15 seconds from activation, not from last byte; exact incomplete bytes and recovery. |
| PROGRESS | Finish the established WTP 30-second inactivity and five-second endpoint/output-backpressure mechanisms alongside the separately covered HTTP sender/reader paths. An earlier timeout cannot prove a later one. |
| JOB-MAX | Use the final implemented limits, not the old 162-event/110.592-second profile. Prove successful idle admission and actual under-contention RF for the advertised event maximum, derived worst 32-character mode plans and 3,600-second maximum-duration jobs. Include event maximum plus one and over-duration atomic rejection. Combine cases only when each maximum is truly represented. Retain exact launch/DMA/short-predecessor/tail/terminal evidence; BUSY is not allocation proof. |
| WTP-MAX | Valid 65,536-byte payload succeeds; correctly framed/CRC-encoded 65,537-byte input is rejected at the intended framing layer, with same-connection recovery. Prove full writes, idle capacity, permitted competing traffic during RF and retained resource effects. |
| HTTP-MAX | Valid API operation in an exact 32,768-byte body succeeds; 32,769 bytes is rejected by the HTTP limit. Distinguish HTTP body size, the expanded WTP envelope, API validity and ownership. Use valid harmless operations such as HELLO; do not invent HTTP STATUS support. |
| BROWSER-MAX | Real Chromium and the target UI admit a real 30,000-byte valid job file and reject 30,001 bytes. Also validate relevant message-entry limits, calculated duration, long-job progress and cancellation UI against actual backend state. Preserve DOM/UI and network evidence, inspect rendered outcomes and distinguish file admission from job/RF submission. No Node-only or direct-HTTP substitute. |
| COMBINED | Declare supported simultaneous allocations and deliberately unsupported combinations using the final enlarged event/job plans and actual parser/TLS/retention costs. Prove successful supported allocation and bounded intended-layer rejection for overload, with preserved owner, RF service and recovery. Do not reuse old-size headroom as new-capacity evidence. |
| USB | Actual USB parser and unread-output pressure during finite RF, with a separate authoritative owner/observer path. Never open the same USB interface twice or depend on deliberately blocked output as the sole authority source. |
| RETAINED | Eight replay entries per session, sixteen logical sessions and eight terminal records: normal reuse, full occupancy, LRU/eviction, overflow, request-ID conflict, same-session replay and source/CAPS-defined expiry. Terminal overflow requires actual finite completions; aborted work is not completed work. |
| RECLAIM | Select the highest measured resource path after the extended implementation and pass three equivalent state cycles. Include the enlarged plan/allocation behavior and long-job lifetime wherever these are material to that path; duration alone does not prove highest memory use. Match image/boot, warm-up, terminal/session/replay cardinality, network/cache state and observer phase; prove resource return, no retained growth, actual expiry and authenticated reuse. |

The current source uses 300-second replay/non-owner idle-session expiry and
3,600-second terminal retention. Plan 360-second quiet windows where needed,
and explicit 3,660-second comparisons where terminal expiry is required. Use
target timestamps/CAPS and actual record content; normal expiry is not loss.
Do not compare a fresh reboot with a warm retained state as proof of reclamation.

Distinct saturation paths must overlap actual Running finite RF where the
contract allows them. Perform idle admission first for operations forbidden
during ownership. Distinguish supported nominal load from prospective overload.
Preserve raw evidence for each trigger and authenticated recovery, generally
within 15 seconds after reclamation, with the source-specific timeout and its
existing two-second observation allowance. Reconfirm exact mechanisms in source
rather than forcing one generic deadline onto all paths.

## 9. Evidence gates, deterministic validation and adversarial review

Preserve the approved `request-cadence-and-roundtrip-v1` policy: INFO request
starts within two seconds, STATUS/host-health starts within six seconds for
their five-second sampling, individual reads within five seconds, complete
observation and causal Running brackets. When deliberately blocking a transport,
predeclare the independent observation path and prove it; do not silently score
missing critical data as success. A new observation design must be prospective,
tested against real producer records, and preserve authority/timing assurance.
It is included in this approval; old failures keep their original scoring.

Require 32,768 bytes general heap recovery reserve, both 16 KiB stacks with
4,096-byte guarded reserve, valid guards and zero stack faults. Keep TLS heap
usage within total allocator accounting while distinguishing fixed lwIP pools
and static RF memory. Prove the largest required supported allocation and a
named fragmentation measurement or justified approximation. Existing largest-
allocation observations are evidence, not a substitute for advertised capacity.

Retain the 75% critical-path / 25% full-and-short-predecessor reserve rules. At
138 MHz, the conservative full-block critical budget is 2,849,391 ns. Derive
short-predecessor budgets from actual word counts, retain IRQ-entry effects,
and separately verify launch, exact DMA/link/tail accounting, TXSTALL and
authoritative shutdown. Do not add overlapping cumulative maxima or treat them
as per-job measurements. No resource delta or timing comparison crosses boots.

Use existing tolerances in the plan and frozen audits. If a required R3
reclamation comparison lacks a more specific tolerance, prospectively require
no monotonic retained growth and at most 1,024 bytes difference from the matched
post-cache baseline, while preserving capacity/reserve and exact cardinality.
Never choose a tolerance after seeing the result. A predeclared nullable
overload allocation may fail only with the required bounded recovery and RF/
authority invariants; a panic in supported load remains a failure.

Use deterministic host and recorded-evidence tests first. Cover malformed and
boundary inputs, partial transfers, cleanup after primary failure, source/boot
and principal mismatches, expired host test credentials, transient network
admission, counter epochs, timeout origin and actual browser producer shapes.
Register applicable tests in the normal build. Run current documented host
CTest, WTP contract and affected Phase 11.5 Python checks with the available
private archives, plus the corresponding Pi compiler/client/UI and compatibility
checks. For user-facing implementation, follow applicable UI review instructions
and inspect the real rendered result. Report skips and test-environment failures
separately. Do not lower long-job observation cadence or hide capture loss to
reduce the test's storage/runtime cost.

After every tranche, independently reconstruct raw requests/responses, lengths,
CRC/schema, partial writes, TCP sequence/ACK behavior, identity, clock mappings,
resource/timing observations, output authority and cleanup. A runner's PASS
label is not sufficient. Mutate raw/summary disagreement, missing bytes/samples,
wrong identities/principals, stale epochs, reset boundaries, incorrect deadline
origins, malformed filters, retained-state mismatch, 32/33-character counting,
repeat/tail duration errors, long counter overflow, contradictory CAPS/client
limits, incomplete hour-long coverage and false final inactivity.
Require the auditor to reject them, then audit intact evidence again.

Fix each actionable source, harness, auditor or documentation finding and rerun
affected checks. Obtain new physical evidence when a fix changes the measured
claim. Perform another adversarial assessment after repairs. Preserve historical
failures without letting an unrelated harness defect permanently block sound,
independently measured assertions. No predetermined retry count substitutes for
passing the actual mandatory checks.

## 10. Completion, restoration, publication and report

Close R3 only when the selected 32-character/3,600-second implementation is
complete, all extended-job checks above pass, and all fourteen R3 groups,
every mandatory distinct mechanism and the three equivalent reclamation cycles
have applicable passing evidence on the final source/configuration, with
justified reuse and completed affected R1/R2 checks. Do not close R3 for the old
short-job image while leaving the selected implementation for another task.
The C0 defect needs a documented cause/remedy or comparably strong causal
evidence and a relevant regression; a reboot that happens to pass is
insufficient. Final source should retain only justified diagnostics; removing
instrumentation is another source change requiring impact assessment.

Leave A on the final reviewed R3 image with the retained test configuration,
standalone scheduling disabled, no active RF and no owner. A safe known terminal
state may be released to Empty. Do not restore an obsolete original configuration
or automatically flash an old image solely to make a restoration field pass.
If final acceptance fails, an identified known-good recovery image may be
installed under this authorization only after safe admission; that recovery
does not close the failed gate. Keep the unresolved outcome explicit.

Restore all task-owned host changes, radios, temporary chrony ACL, paused
recovery timer and browser/test trust artifacts according to their recorded
before-state. Preserve permanent time.local/GPSD/PPS/Avahi, management paths,
the installed Pi service and B. Verify A and B independently. Record final
image/source/boot/configuration, output/owner state, actual operation counters,
host restoration and any remaining temporary artifacts. Never destroy raw
evidence or an unrelated user's work during cleanup.

Update the current acceptance ledger, machine-readable R3 register and extended-
feature matrix, execution and failure-triage records, source-impact/reuse review,
implementation roadmap, relevant protocol/API/UI and mode-limit documentation,
and `WsprryPi/docs/development/phase11-5-review.md`. Clearly distinguish the
implemented product limits and this exact resource/lifecycle acceptance from
pending per-band/per-mode conducted RF and Phase 13 qualification. Mark old
prompts as superseded for authority by this accepted prompt without editing their
frozen packet bytes or historical outcomes. Keep private credentials, backups,
captures, configurations, tool-local paths and generated firmware out of Git;
publish sanitized identities and reproducible audit instructions.

Commit only attributable, reviewed changes and push to the two `origin/devel`
branches without force. Fetch and integrate concurrent work in an isolated
worktree when needed, rerunning affected validation after integration. Verify
remote parity for the published commits. Preserve and explicitly report any
unrelated dirty state instead of trying to clean it. Do not stop at a proposed
commit or an unattempted authorized push.

Report: R3 closed or the precise unresolved gate; all fourteen group statuses;
the allocation finding and repair; implemented message/duration/event/repetition
limits and their client/UI behavior; actual physical and host validation;
adversarial findings, repairs and final reassessment; evidence/image/source
hashes; operation totals; final A/B/host state; commits, pushes and repository
state. If R3 closes, Phase 11.5 advances to **3/6 families closed**, with R4–R6
still open and no full accepted configuration. Do not claim Phase 11.5, Phase
11.6 or Phase 13 complete. The narrowly included extended-job cancellation and
transport-loss checks may support later reuse, but do not execute the remaining
R4–R6 or later qualification campaigns under this grant.

Suggested acceptance message:

> I accept R3-COMPLETE-20260913-v2, including the 32-character and 60-minute
> implementation, finite RF tests and complete work/recovery scope described.
> The documented 60 dB conducted wiring remains unchanged.

An unambiguous acceptance of this prompt is sufficient; do not demand that the
user repeat an exact incantation or separately approve each included operation.
