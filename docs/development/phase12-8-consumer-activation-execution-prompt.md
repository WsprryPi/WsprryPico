# P12.8 consumer activation and AP claim execution prompt

Status: **ACTIVE EXECUTION PROMPT; P12.8 AND PHASE 12 OPEN** (2026-09-27).
Work on `devel` in this repository. The accepted
[P12.7 decision](phase12-7-decision.md),
[Owner-HTTP/1](../protocol/Owner-HTTP-v1.md),
[Consumer-Profile/1](../protocol/Consumer-Profile-v1.md) and
[Phase 12 roadmap](phase12-plan.md) control the design. The operator asked
for implementation, adversarial review, repair, commit and push. This prompt
is not authorization to flash, control USB/GPIO, press BOOTSEL or emit RF.

## Objective and sequencing

Complete the P12.8 foundation so a physically granted Safari claim can
trial Wi-Fi, establish bounded UTC, generate device trust, commit one consumer
profile and survive reboot into the owner authority model. No live route may
write source 5 until the boot path can safely select it. Preserve the
independently accepted Wi-Fi-only bootstrap and its network-only source.

1. Inspect the actual branch, worktree and current source. Read `AGENTS.md`,
   `README.md`, `CONTRACT.md`, `docs/architecture.md`, this prompt and the
   linked contracts. Preserve unrelated changes and existing journal data.
2. Implement consumer boot selection in the portable runtime with exact
   device identity, source/generation and structural profile checks. Treat
   structural admission only as a pre-clock state. With no trusted UTC,
   malformed profile, reset intent, wrong device, invalid cert/key or failed
   safety gate, grant no owner, station client, legacy password, BLE, USB job
   or RF authority. Join station only to obtain time and provide recovery.
   After bounded UTC, validate the persisted CA/server identity and client
   allowlist before any authenticated service starts.
3. Build the AP-local public-status, claim/start, claim/status and
   claim/submit handlers against exact Host/Origin/body admission. Bind one
   slot to full device/boot/source/generation, checked P-256 owner point and
   X25519 transcript. Deliver the physical prompt before entering the
   flash-safe BOOTSEL window. Accept an ordinary press/release without a
   human-timed hold. Consume the slot and ephemeral key on the first
   complete submit, including failed AEAD. Keep all secrets off public
   status, logs and errors.
4. Trial submitted station credentials and DHCP without changing the journal;
   preserve the previous network-only path on failed trial. Obtain fresh,
   bounded trusted UTC; generate and validate the per-device CA and server
   material; recheck output, access journal, source/generation, clock, station
   and slot at the write boundary. Commit exactly one canonical source-5
   generation. Return a terminal receipt only after verified journal readback
   and the response boundary; unknown writes require read-only reconciliation
   by request digest, never replay.
5. On consumer boot, expose the AP owner session and authenticated readback
   while denying engineering password/cookie, GATT and USB mutation paths.
   Retain station/schedule/watermark data outside the claim transaction. Do
   not start station mTLS job control until its CA and explicit client
   allowlist are validated. Keep one JobService and the existing WTP/1 and
   browser API architecture.
6. Add deterministic failure tests for wrong device/source/generation,
   malformed owner point, competing claimant, stale gesture, AEAD mismatch,
   lost station/clock, TLS generation failure, journal cuts, reboot and
   response loss. Check canonical browser/Pico vectors and the existing
   Wi-Fi-only path. Build the RF-inhibited Pico 2 W image and inspect BOOTSEL
   topology and resource margins. Host or cross-build evidence is not target
   acceptance.
7. Perform an adversarial review of the exact changed graph. Repair each
   actionable finding, rerun affected checks and reassess. Record source,
   test and remaining target gates honestly. Commit and push to `devel` only
   a validated, truthful state; independently verify remote parity.

## Physical gate

Before calling P12.8 accepted, prepare one exact RF-inhibited image and a
bounded Candidate A plan for BOOTSEL, AP continuity, entropy/key-generation
time, heap/stack, journal reboot and owner readback. Ask for action-specific
hardware authorization under `AGENTS.md`; keep Candidate B and RF output
untouched. A physical press is not a timed performance task for the person.
P12.9 Safari UX and P12.10–P12.12 acceptance remain separately gated.
