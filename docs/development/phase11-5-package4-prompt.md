# Phase 11.5 Package 4 execution prompt

Execute only Phase 11.5 Package 4 in `/Users/lbussy/GitHub/WsprryPico`.
Do not change another repository or claim any Package 5/6 result. Preserve all
failed attempts and all existing Package 1-3 evidence.

## Objective

Close the two remaining Group 2 USB assertions on Pico A's installed
`ca3c5dce40360b7eea2f9c45618232caa68cdbb6` image:

- `2.3d`: actual USB parser pressure during independently observed finite RF;
- `2.3e`: actual unread USB output pressure during independently observed
  finite RF, followed by USB transport recovery.

Reconcile Packages 1-4 against the Group 2 matrix after both assertions pass.
Phase 11.5 remains open for retention/reclamation and final R3 closeout.

## Frozen target and boundaries

- Pico A: serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, boot
  `5e0d6bc3e383b8c1cb4b0db9ed636bf5`, Pico 2 W/RP2350 Arm, 138 MHz,
  PIO divider 1, GP2 PIO/DMA, RAM rendering.
- Installed UF2 SHA-256:
  `6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59`.
- Pico B is an unchanged inactive comparator: serial `E66141040343552F`,
  device `223dccf76bcdc1d14e213d5f0d0072af`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- Use the retained isolated wspr5 fixture, authenticated TLS 1.3 WTP/HTTPS
  credentials, durable two-Pico RF reservation and exact board-specific
  `/dev/serial/by-id` endpoints.
- Planned hardware budget: two 100-second finite Tone jobs, 200 RF seconds,
  zero flashes, zero configuration writes, zero controlled reboots and zero
  Wi-Fi cycles. An absolute repair ceiling permits at most one replacement job
  per assertion after preserving a harness-defect attempt: four jobs and 400 RF
  seconds total. Do not repeat a completed case for reliability.

## Source mechanisms to bind

1. The WTP frame parser accepts at most a 65,536-byte payload. Its exact
   maximum frame is 65,552 bytes including the header. `INFO` reports the
   endpoint-owned reservation as `wtp_input_reserved_bytes`.
2. USB service reads and writes at most 64 bytes per foreground call. The
   endpoint retains unaccepted output and closes itself after five seconds
   without output progress while continuing to service the job engine.
3. A WTP CDC DTR falling edge clears parser, input and output state. Reopening
   requires a fresh HELLO; service ownership and the RF job remain independent.

Confirm these mechanisms in current source and cover their decisive state and
failure paths with deterministic host tests before device execution.

## Prospective physical cases

Run each case in its own finite 100-second, single-event Tone job at
135.500 kHz. The authenticated network WTP connection must CLAIM, LOAD, ARM,
observe and renew the job. Console interface 0 must independently sample INFO.
Only the pressure worker may open Pico A WTP interface 2, and only once at a
time. Do not open Pico B's endpoint for Pico A control or observation.

### P4-USB-PARSER / assertion 2.3d

After network STATUS reports the exact Running job, boot, owner and active
output, require Console INFO to independently report the same boot, Running
state and active output. Console INFO does not expose job or owner identifiers;
do not invent those fields or infer them from the Console path.

1. Open Pico A WTP CDC exclusively and negotiate HELLO.
2. Send one correctly framed, CRC-32C encoded STATUS request with an exact
   65,536-byte JSON payload and 65,552 total wire bytes. Pace bounded writes so
   Console can sample the live reservation, while every write makes progress
   inside the parser's five-second deadline.
3. Require exact total write accounting, a direct
   `wtp_input_reserved_bytes >= 65552` observation during Running RF, a valid
   matching STATUS response, and a successful same-connection PING.
4. Close/reopen DTR, negotiate a fresh HELLO and require STATUS to show the same
   network-owned Running job. Treat any allocator failure, boot change, unknown
   output, foreign owner, incomplete response or missing reservation sample as
   failure.

### P4-USB-UNREAD / assertion 2.3e

After both independent authorities bracket the second Running job:

1. Open Pico A WTP CDC exclusively, negotiate HELLO and fully drain that reply.
2. Offer a bounded batch of distinct complete STATUS frames and perform zero
   application reads for at least the source-defined five-second output-progress
   deadline. Record exact offered and accepted bytes and complete request count.
3. After the hold, drain at most the declared capture bound. Require fewer
   complete responses than complete requests already accepted, proving the
   unread output path prevented progress before any possible trailing partial
   input could become the close cause. Require a same-session PING to remain
   silent while the physical CDC connection is still open.
4. Toggle DTR only after that proof, reopen with no stale bytes, negotiate a
   fresh HELLO, and require STATUS to show the same Running job and owner.
5. Maintain authenticated network STATUS with exact job/owner and Console INFO
   with exact boot/state/output through the entire unread interval and recovery.
   They, not USB silence, establish RF authority.

## Evidence and acceptance

Use a new immutable private evidence root and a hash-bound packet/helper
manifest. Retain raw USB writes/reads, decoded responses, network TLS frames,
Console INFO, host health, before/final inventories, reservation records,
fixture state/restoration and exact monotonic/UTC timestamps.

Accept each row only if an offline auditor reconstructs:

- exact packet, source/image/boot, device and endpoint identities;
- Running network STATUS and Console INFO immediately before, during and after
  the stimulus, with the same job, owner, boot and positive `output_active`;
- exact USB byte/request bounds and the case-specific trigger above;
- uninterrupted finite lifecycle, launch epoch increase, complete terminal
  state, inactive output before RELEASE, and Empty/inactive/unowned final state;
- no new allocator/TLS failure, valid 4 KiB stack guards and at least the
  existing 32 KiB allocator reserve;
- unchanged Pico configuration and unchanged/inactive Pico B;
- successful reservation release and exact host-fixture restoration.

The auditor must reject mutations to identity, endpoint role, RF bracketing,
parser reservation, byte accounting, unread response deficit, silence before
DTR recovery, fresh HELLO/STATUS recovery, final state and reservation release.
Source/unit evidence can identify the five-second mechanism; it cannot replace
the physical unread-output trigger or independent RF observations.

## Review, repair and reporting

After capture, perform an adversarial code/evidence review. Fix every actionable
finding within this slice, rerun affected deterministic checks, and rerun a
physical case only when the original evidence cannot satisfy an unchanged
prospective criterion and the replacement remains within the absolute budget.
Then perform a second adversarial assessment. Do not weaken a threshold after
observing a failure.

If both rows pass, write a Package 4 result and review, update the completion
matrix/progress/development index, and mark only assertions `2.3d` and `2.3e`
accepted. Record failures with zero credit. Commit the complete reviewed change
to `devel`, push `origin/devel`, verify local/upstream/remote parity, and report
the exact commit, checks, hardware charge, restoration state, limitations and
remaining Packages 5-6.
