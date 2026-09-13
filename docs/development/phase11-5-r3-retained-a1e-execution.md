# R3 retained-baseline A1e: bounded rejoin recovery and TLS/slot run

A1c was executed and stopped before LOAD/ARM: 25 readiness inventories never
established an address or synchronized clock, ending with CYW43 link status -3
(authentication failure). Its completed evidence archive is
`b5db3b325cc0b695eb99812241e7b6bddf6c38d9124b8356305c6be1f032a45f`.
A was reconciled to Empty/inactive/unowned, B was unchanged and the host restored.
No new RF, CONFIG save or flash occurred. A1c remains a failed attempt.

A1d was staged but automatic approval review rejected its launch because the
Wi-Fi OFF/ON cycle adds a hardware action. It performed no device or fixture
action. Adversarial review then added a full-observation fixture-lifetime gate
and corrected final status on cleanup failure. This A1e packet includes those
repairs and replaced A1d. The user explicitly approved A1e and it was executed.
One idle OFF/ON cycle restored readiness, then one Tone completed before a
confirmed harness freshness failure. The second job was not submitted. This
packet is consumed; see the [causal review](phase11-5-r3-completion-review.md).

This new packet adds at most **one idle Wi-Fi OFF and one idle Wi-Fi ON** as a
prerequisite recovery diagnostic under the user's R3 execution request. It changes
the original zero-Wi-Fi-action work specification prospectively for this packet
only. It supplies no R5 acceptance. No CONFIG save, flash, reboot or heap probe is
allowed. Keep the user's retained test configuration and confirmed 60 dB wiring.

- New root: `/home/pi/phase11-5-r3-retained-a1e-20260912`.
- Packet SHA-256: `27cd914815b8af8933fb134b44a923add1f09c8748afd0082115e4b1f202a518`.
- Archive SHA-256: `3e6c348436c63971fc547fcabc5b6e6dc4a1f9d2495ec040e29d0e2995495116`.
- Archive: 675,840 bytes, 62 tooling/manifest files. Nine private inputs are copied
  only between roots on wspr5; keys/passwords are not uploaded or exported.
- Staging helper SHA-256: `788fb4c6595506916763229e900b6c9ccb0f7f941b0192eb282e1b2ad4e6830f`.
- Finite job IDs: `d27689688f2f3e519a3836b775b3092b` and
  `4b579434a837cb8f7d371db85e9abd7f`.

All candidate, boot, board, host, baseline and private-input identities and the
physical envelope are unchanged from [A1c](phase11-5-r3-retained-a1c-execution.md).
The two jobs are each Tone 135,500 Hz for 100 seconds, total at most 200 seconds
RF. Preserve the same ten TLS/slot cases, 12 pressure connections, 12 renewals,
300-second RF-off production load, 360-second sole USB observer and independently
armed 1,800-second host fixture plus 600-second cleanup.

Before recovery, verify the running AP's PSK equals the retained private input,
recording only the comparison result. Fresh WTP/INFO must prove Empty, inactive,
unowned, healthy and same boot/configuration. If already connected, skip the
cycle. Otherwise require enabled/disconnected (-2 or -3), no address. Acquire the
exclusive Console endpoint, recheck INFO and issue one OFF with write-ahead
accounting. Require the exact successful ACK and settled disabled state. Repeat
that admission for one ON and require its ACK and settled enabled state. Do not
retry an uncertain command. No RF owner exists during this cycle.

Then perform the bounded network/clock readiness wait. If it fails, stop without
LOAD/ARM, preserve raw logs, verify A/B and restore the host. If it succeeds,
execute and audit the full TLS/slot run. Any fault, resource failure, changed boot
or unknown output stops dependent work. Final terminal reconciliation remains
limited to the known prior/new completed jobs; preserve the terminal history.
