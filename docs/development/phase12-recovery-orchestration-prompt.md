# Phase 12 unattended Recovery and Robustness execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Implement and execute a
fully orchestrated bounded RF-inhibited recovery campaign, then adversarially
review, repair findings and reassess, commit/push scoped work and verify remote
parity. Starting revision is `d665fd011047e16bd43af83799dfdcd764109a65`.

The user explicitly authorizes destructive Pico operations and directs no
additional approval prompts. This supersedes the earlier preparation packet's
per-case human approvals and Ready requirement for this recovery scope. Record
that authority once; do not manufacture human approvals or change production
confirmation/security contracts. Automation acts as the authorized operator
and sends both confirmations and the exact typed phrase through the ordinary
encrypted recovery protocol. Operator setup/physical RF, phone observations,
physical power cuts and arbitrary corruption are outside this campaign.

## Scope and safeguards

Read project instructions, README, CONTRACT, architecture, development guide,
prepared candidate manifest, fault fixture and reset/profile contracts. Preserve
six concurrent user documents byte-for-byte and exclude them from commits.
Candidate B only: serial CDDBF8767C506C07, device29f20b7342051ef947aa56cb9d4fab42,
Pico2W/RP2350. A and wspr4 remain untouched. Existing wspr5 USB host and retained
tools may be used. Pin temporary AP association to an unused network interface;
never replace the management route or unrelated network connections. No RF
image, jobs, GPIO/button simulation, SDR acquisition or RF acceptance is allowed.
Use existing pinned SDK/toolchain/tools, no incidental installs/downloads.

## Deliverables and execution

1. A deterministic hardware-free orchestration state machine and bounded opt-in
   live adapter. Implement exact candidate/hash/source binding, board-global
   exclusion, finite deadlines and case counts, durable write-ahead ledger and
   unique case IDs. No automatic repeat of a destructive POST or uncertain save.
   Restart reads the ledger and restores/verifies; it never silently resumes an
   unaccounted destructive operation. Separate target failure from observer or
   transport failure and preserve every failed case.
2. Preflight actual USB identity and inactive inhibited authority. Acquire a fresh
   full4MiB backup before alteration, retain/hash-verify a local copy, and verify
   restoration prerequisites. Back up before every case. Load only the reviewed
   inhibited candidates through serial-targeted picotool. Validate programmed
   application bytes, reserved/E10 invariants and freshboot/INFO before use.
3. Fourteen reset cases: provisioning/full levels × durable checkpoints1–7.
   Use ordinary open-AP recovery X25519/HKDF-SHA256/ChaCha20-Poly1305 requests,
   two confirmations and phrase. Fresh keys/nonces/boot/device/request binding.
   Prove one intended watchdog cut, bounded safe resume, exact clearing versus
   preservation, access epoch once and E10 unchanged. Each mutation/observation case <=300s, excluding its separately bounded restoration and at
   most two additional resume boots. Stop on unexpected stage/cold rearming,
   identity/output/storage/allocator fault; restore before any further case.
4. Three profile interruption cases8–10: one supported encrypted consumer save
   per stage, healthy stable seed with no pending TLS boot write. Preserve
   unrelated trust/settings. For8–9 previous committed authority or explicit
   fail closure; for10 reconcile exact durable request digest/generation without
   resubmitting. Record actual header/payload/commit evidence and clean restore.
   At most one save/cut per case, <=300s, same bounded resume rules.
5. Final restoration to exact standard inhibited `restore` candidate and original
   intended reserved settings. Preserve E10 byte-for-byte. Require programmed
   payload/readback, healthy journals, correct effective station/schedules/
   watermark/access, no reset pending/job/owner/output, disabled scheduling,
   ordinary session policy and stable actual network/time as applicable.
   Emergency restoration is finite and automatic when USB/ROM remains available;
   inability to verify restoration is a blocked physical result, never success.
6. Private permission-restricted raw evidence/backups/credentials and machine-
   readable result ledger; redacted repo report with exact image/source/board/
   boot/case/tool identities, hashes, durations, exceptions and restoration state.
   Compile/hash-only, synthetic or host passes do not become physical acceptance.
   Provide safe default plan/preflight and explicit live `--run` entry point;
   no interactive approval input is required by the runner.

## Validation, review and publication

Behavioral tests must exercise wrong board/hash/stage, duplicate execution,
uncertain POST/save, deadline and reboot exhaustion, failure during restoration,
ledger partial/truncated/corrupt state, concurrent campaigns, backup loss and
E10 preservation. Verify recovery/consumer crypto against actual reference
vectors and strict parser limits. Run affected tests, full host suite, meaningful
sanitizers, protocol/format/whitespace checks and offline candidate verification.
Perform adversarial assessment; repair findings and repeat assessment until
reviewed scope has no actionable issue. Then run authorized live work only if
preflight/restoration paths really work; report any external or hardware blocker
with retained evidence, without a repeated destructive attempt. Commit/push
scoped prompt, runner, tests and evidence report. Phase12 remains OPEN_PARTIAL
outside the exact accepted recovery scope; RF ledger remains16/11.

Final restoration acceptance includes five stable INFO samples, verified ordinary
session policy and closed network/BLE buffers. Standard GP14-OFF images do not
expose actual SoftAP adapter withdrawal, so that separate physical gate remains
open; do not infer it from zero sessions or station reconnection. Initial retained
615888e5364b firmware lacks the new pool/session telemetry: admit its exact known
revision for backup only, require full telemetry after candidate deployment.

Consumer USB intentionally rejects ACCESS SOFTAP. The fault fixture therefore
opens one ordinary 120-second join-grace AP window at boot, only with the existing
explicit RF-inhibited phase12 fault option. The standard restoration image has
no test window. Record this fixture distinction in image/INFO evidence; it does
not qualify a physical button or production AP activation path.
