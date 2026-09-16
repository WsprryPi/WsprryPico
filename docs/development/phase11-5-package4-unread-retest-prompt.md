# Phase 11.5 Package 4 assertion 2.3e bounded physical retest

Execute one focused physical retest of **2.3e USB unread-output pressure** in
`/Users/lbussy/GitHub/WsprryPico`. Preserve the accepted 2.3d result and all
failed Package 4 attempts. This packet must produce either accepted 2.3e
evidence or an exact open blocker; it must not infer acceptance from a response
deficit alone.

## Frozen target and allowance

- A: serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, source `ca3c5dce4036`, image
  `6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59`,
  boot `5e0d6bc3e383b8c1cb4b0db9ed636bf5`.
- B remains the unchanged comparator: serial `CDDBF8767C506C07`, device
  `29f20b7342051ef947aa56cb9d4fab42`, source `8921a7008183`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- One 100-second 135.5 kHz Tone on A, with one durable two-Pico reservation.
- Zero flashes, configuration writes, controlled reboots and Pico Wi-Fi cycles.
- Use the isolated host AP/client namespace, retained target configuration and
  authenticated TLS 1.3 WTP controller identity. RF timing remains local to A.
- Do not rerun 2.3d, Package 5, Package 6, or any hour-long mode job.

## Required stimulus and evidence

1. Start fresh named A/B inventories and require both boards to be Empty,
   inactive, unowned and schedule-disabled on the frozen identities.
2. Acquire the durable shared reservation before CLAIM/LOAD/ARM.
3. Own and observe the job through the independent authenticated network WTP
   path. Continuously sample Console INFO on USB interface 00. The USB pressure
   connection on interface 02 must not own the RF job.
4. After the exact job is Running and both observers agree that output is
   active, open one USB WTP session and offer at most 1,024 complete STATUS
   requests for at most three seconds without reading responses.
5. Perform zero application reads for 12 seconds. Then drain at most 1 MiB for
   at most three seconds and require fewer complete responses than complete
   requests accepted. Retain the raw bytes and any bounded trailing frame.
6. While DTR remains asserted, discard only unsent host-to-device tty output
   with `tcflush(TCOFLUSH)`. Record that action. Do not close or reopen the USB
   endpoint before the silence proof.
7. Write one exact PING using the unchanged USB session and require zero received
   bytes for two seconds. This is the required proof that the target endpoint
   closed for no output progress; inability to write the probe is a failed
   retest, not evidence of closure.
8. Toggle DTR only through the normal exclusive-port close/reopen. Require no
   stale output, then require a fresh HELLO and STATUS on a fresh session while
   the same network-owned RF job is still Running.
9. Continue independent observation until local Complete. RELEASE through the
   authenticated network owner and require Empty/inactive/unowned authority.
10. Collect final named A/B inventories, verify configuration and failure
    counters, release the shared reservation and restore the host fixture.

## Acceptance and stopping rules

Accept 2.3e only if raw audit reconstructs the offered/drained USB bytes, the
response deficit, the exact same-session PING, two seconds of pre-DTR silence,
fresh post-DTR HELLO/STATUS, continuous independent Running authority, one local
RF completion, final Empty authority, unchanged B/configuration/failure
counters, released reservation and exact host restoration.

Stop after this single RF job regardless of result. If the assertion fails,
allow the already armed finite job to complete, release/reconcile authority,
restore the fixture and report the exact missing acceptance fact. Do not relax
the silence, recovery, identity, timing, resource or restoration gates and do
not substitute host or simulated evidence for the physical retest.
