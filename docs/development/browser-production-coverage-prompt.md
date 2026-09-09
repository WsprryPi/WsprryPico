# Browser and production-client coverage execution prompt

Complete the browser and production-client portion of Phase 11.4 on the existing
RF-inhibited Pico. Execute the work, retain original failures, repair actionable
findings, repeat adversarial assessment, then commit and push the scoped changes
to WsprryPico `origin/devel`. Do not describe the whole phase as closed.

## Starting scope and authority

- Work in `/Users/lbussy/GitHub/WsprryPico`, initially clean `devel` at
  `f88fa71eef5e4513d75a618837ab684ca9845ea6`. Read AGENTS.md, README.md,
  CONTRACT.md, architecture, development checks, browser API, WTP and the current
  Phase 11.4 joint matrix and single-board record before implementation.
- The user explicitly included bounded acceptance on the currently inhibited
  Pico. Use that authority for browser/production job and settings coverage.
  Prepare any necessary installed-service pause/restoration as a concrete packet
  and obtain separate authorization before changing that service.
- Initially use the reviewed production source at
  `2e47641f6ebdff104e32999f5194f2e0dc408e06`. The user subsequently authorized
  fixing the exposed scheduled-wait timeout in an isolated WsprryPi checkout,
  with scoped commit/push to `origin/devel`, and then requested a rebase after
  committing their own work. Use `/private/tmp/wsprrypi-browser-coverage-20260909`
  on `codex/browser-production-coverage`, based on latest `devel` at `89f23e5`.
  Preserve the original checkout. Verify source and binary hashes before
  corrected-client acceptance. Do not silently update interoperability pins or
  use a synthetic client as evidence for the production application.
- The user approved the prepared service pause/restoration packet. Run only
  bounded settings/completion/cancellation cases and necessary repaired-case
  retests, checking inactive output and restoring the installed service after
  each. Keep the installed binary and configuration unchanged within each run.
- Use only Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344`, full device ID
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, attached to wspr5. Console interface is
  `/dev/serial/by-id/usb-WsprryPi_WsprryPico_0BF4B4AEC9FFB344-if00`; WTP is
  the same alias ending `-if02`. Never open the adjacent GPSDO.
- Starting installed revision is `f88fa71eef5e`, standard inhibited UF2 SHA-256
  `7345d87f8816b8890971bc6ce785778f273ff8d6fbe470d9fdd005714ca2b751`.
  Reconfirm INFO, HELLO, CAPS and STATUS; require deployment match, healthy
  storage, inactive output and exact device/boot identity before mutations.
- Use existing distinct browser/controller identities and certified hostname
  `wsprrypico-0a60df.local:18443`. Keep TLS 1.3, mTLS, ALPN, SAN, Host/Origin
  and full WTP identity checks. Do not alter trust, credentials or network settings.
  An address selected from fresh device evidence with the expected DNS identity
  is an explicit-IP transport test, not a hostname-resolution pass.

## Required coverage

1. Make a subcase matrix tied to C2/C3/G1/G2 in the existing joint matrix. Separate
   actual Chrome, production application, direct HTTPS/WTP and deterministic
   fixture evidence. Preserve all historical partial/failed results.
2. Exercise the shipped Chrome UI for finite job completion and cancellation.
   Check its own owner indication, Armed/Running/terminal states, disabled foreign
   owner controls, release behavior and inactive output. Loaded-only coverage
   must state whether it is observable through the shipped combined load/arm UI.
3. While the actual production client owns a finite job, observe Chrome status
   in every reachable Loaded/Armed/Running state and prove foreign mutations do
   not take ownership or stop the job. Use authoritative correlated job IDs and
   terminal reports; a disabled button alone is not server rejection evidence.
4. Exercise production management reads and revision-controlled settings writes.
   Test a stale revision, secret redaction/preservation, Chrome draft preservation
   across external writes, explicit reload, and exact saved-value restoration.
   Change only station power temporarily from its fresh baseline by a valid small
   delta; preserve passwords, SSID, time server, scheduling and watermark.
5. Cover production cancellation through the supported production control path,
   retaining the actual execution report and independent Pico status. Do not
   call a direct WTP ABORT production cancellation.
6. Strengthen deterministic browser/client acceptance checks for newly exposed
   failure paths: unsuccessful reads become unknown, partial/lost mutations are
   not retried automatically, identity changes stop dependent actions, ownership
   is preserved and failed cleanup cannot be reported as a pass.

## Bounded execution and cleanup

Use at most 16 finite inhibited jobs, each at most 30 seconds, total duration at
most 480 seconds. Use nominal 3,570,100 Hz with a CAPS-valid complete tone or
finite QRSS plan. Never use continuous Test Tone. Reconcile CAPS and synchronized
clock with at most the negotiated 500,000,000 ns uncertainty. Choose enough
preparation lead; reject a missed start rather than silently rescheduling.
RP2350 owns event timing; complete LOAD must precede ARM. No RF-capable firmware,
GPIO, services outside a separately approved packet, router faults or reboot.

Record request/session/job/boot IDs and expected observations. Preserve the
original result of every attempt, including timeouts. Never retry ambiguous
mutations. Reconcile matching authoritative status before owner cleanup; avoid
clearing another client's job. On exit, restore only the approved settings delta,
stop the isolated client, restore an approved paused service in an independent
cleanup path, and prove inactive/unowned output and retained settings. A lost
connection is output unknown, never proof of successful cleanup.

Keep private evidence in a new ignored `build/browser-production-coverage/`
directory with attempt-specific files. Record UTC, commands, exit codes, source
and executable hashes, firmware identity and public certificate fingerprints.
Do not commit keys, passwords, generated firmware or private captures.

## Validation, review and publication

Run documented affected browser, HTTP/API, actual-TLS and pinned production-client
checks. Keep loopback test servers sequential when they share a port. Use the
installed Chrome for actual UI evidence, and label local fixtures accurately.
Add meaningful behavioral regression tests for defects, not tests that merely
repeat the implementation. Cross-build and check image layout if firmware changes;
deployment of a new candidate requires an identified, separately approved image.

After implementation and execution, adversarially challenge wrong/stale identity,
unobserved transient states, output-unknown handling, duplicate submission,
revision races, password leakage, false production/Chrome evidence, unbounded jobs,
cleanup failures and overwritten attempts. Fix actionable findings, rerun affected
checks, and perform another assessment. Record each round and its disposition.

Commit a sanitized execution/review record and update only the relevant joint
matrix subcases. Leave DHCP, second-board trust, certificate rotation, transport
faults, overnight reliability and RF qualification open unless separately proven.
Review the complete staged diff, commit and push without force, verify remote
parity, and report actual tests, physical results, limitations, final device/service
state, changed files and commit. Never infer remote CI results.
