# Execute R3 P0 — bounded read-only admission

Status: **PREPARED; USB AUTHORIZATION PENDING.** No new hardware operations have
run. This packet is preparation for R3, not a physical acceptance test. The
[source review](phase11-5-r3-preparation.md) records what is ready and what remains.

Resume Phase 11.5 from R1 5/5 and R2 7/7 closed, using the current acceptance
ledger. Execute only this new P0 packet after the user authorizes its exact
read-only USB operations. Do not repeat R1/R2, activate a fixture or run RF.

Use SSH outside the sandbox. Host: `wspr5`, boot
`220e53ca-ca95-4206-9581-dbe28aa1eeb8`. Private staging root:
`/home/pi/phase11-5-r3-preflight-20260912`. The packet pins every staged helper;
record and verify its SHA-256 before dispatch. No credentials are needed.

1. Verify the root is private, helpers and schema match the packet, no run-intent
   exists, host boot matches, and no other process owns the two boards' USB
   endpoints. The inventory helper also checks endpoint ownership before opening.
2. Execute **A-before, B-before, A-after, B-after** in that order, exactly once.
   Each capture allows Console `INFO` once and WTP `HELLO`, `CAPS`, `GET_CLOCK`,
   `STATUS`, `PING` once. No other device command is permitted. The helper opens
   Console interface 00 and WTP interface 02, configures raw serial, asserts DTR
   while open and clears it when closing. One frozen logical WTP session is reused
   for each board's two captures; sessions differ between boards. These read
   operations may retain ordinary administrative session/replay entries. They
   do not write persistent configuration or authorize claims/jobs.
3. Pico A: serial `0BF4B4AEC9FFB344`, device
   `fd6127d11d6aca42a9905fa3fb1bf1d5`; expected original inhibited revision
   `802c91a7b86e-dirty`. Pico B: serial `CDDBF8767C506C07`, device
   `29f20b7342051ef947aa56cb9d4fab42`; expected inhibited revision
   `dbf1d86f0885-dirty`. B remains read-only.
4. Allow five seconds per request, sixty seconds per inventory and at most
   five minutes for the whole packet. Ordinarily this should take under a minute.
   Four INFO requests and twenty WTP requests are the entire device budget.
   Additional CONFIG writes: **0**; heap probes: **0**; RF jobs: **0**; firmware
   changes, resets, flash reads through BOOTSEL, journal erasure and fixtures: **0**.
   Cumulative counts remain CONFIG 34/34 and six probes.
5. Preserve every raw byte and failure. No automatic retry. A consumed packet
   cannot be run again. An active/faulted/changed board is evidence to retain,
   not permission to clear state. Changed boots require explicit reconciliation;
   output remains unknown if authoritative observations fail. Terminating this
   host reader closes its endpoints and does not establish inactive RF.
6. Audit raw Console and CRC-checked WTP frames against every summary; enforce
   exact request order, reply binding, source/session/board identity, sequence,
   deadlines and before/after order. Report unexpected original state and boot
   differences as blockers. Re-audit after the adversarial assessment.
7. Publish only sanitized findings to the Pico ledger/result and Pi report;
   private logs stay outside Git. Report four-capture progress separately from
   R3 physical acceptance, which remains zero. Commit/push completed scoped
   documentation after review, as already authorized.

The locally prepared packet is
`build/phase11-5-r3-preparation/packet.json`. Stage its exact bytes and the five
manifest entries without copying any old packet, result or authorization.
Frozen packet SHA-256:
`6695194cae5fbbf0611a2480e70074761be218da7e749f6c9f4b319fcf766119`.
After explicit approval, the execution command is:

```sh
sudo python3 /home/pi/phase11-5-r3-preflight-20260912/scripts/phase11_5_r3_preflight.py run \
  --root /home/pi/phase11-5-r3-preflight-20260912 \
  --packet-sha256 6695194cae5fbbf0611a2480e70074761be218da7e749f6c9f4b319fcf766119 --run
```

Verify the digest against the offline preparer output
and the accompanying preparation result. A hash or `--run` flag
is not itself user authorization. The preparer is hardware-free:

```sh
python3 scripts/phase11_5_r3_preflight.py prepare --root build/phase11-5-r3-preparation
```

It refuses to overwrite an existing packet. After execution, audit in a separate
copy if `preflight-result.json` already exists; the audit deliberately refuses
to overwrite derived results. Do not delete a result merely to rerun it.

Before the subsequent R3 A RF packet, finish its executor and independent audit,
record the disposition of the long-QRSS restriction, inspect original configuration
using separately authorized operations, reserve R5 schedule/rotation/restoration
writes (inspect journal position before freezing the R5 sequence), freeze finite
jobs/credentials/cadence and restoration inputs, reconcile wiring and request
the consolidated missing fixture/flashing/RF/configuration allowance. P0 does
not authorize any of those actions. The existing physical image remains
2e43110 / 138 MHz / divider 1 / RAM / listener on until a reviewed change is needed.
