# R3 retained-baseline A1d: bounded rejoin recovery and TLS/slot run

Historical: staged only; automatic approval review rejected the launch. No
hardware action ran. Use the reviewed [A1e packet](phase11-5-r3-retained-a1e-execution.md)
for any future execution, after approval. Do not launch this superseded packet.

A1c was executed and stopped before LOAD/ARM: 25 readiness inventories never
established an address or synchronized clock, ending with CYW43 link status -3
(authentication failure). Its completed evidence archive is
`b5db3b325cc0b695eb99812241e7b6bddf6c38d9124b8356305c6be1f032a45f`.
A was reconciled to Empty/inactive/unowned, B was unchanged and the host restored.
No new RF, CONFIG save or flash occurred. A1c remains a failed attempt.

This new packet adds at most **one idle Wi-Fi OFF and one idle Wi-Fi ON** as a
prerequisite recovery diagnostic under the user's R3 execution request. It changes
the original zero-Wi-Fi-action work specification prospectively for this packet
only. It supplies no R5 acceptance. No CONFIG save, flash, reboot or heap probe is
allowed. Keep the user's retained test configuration and confirmed 60 dB wiring.

- New root: `/home/pi/phase11-5-r3-retained-a1d-20260912`.
- Packet SHA-256: `d7ec7deba7bd0a62666f805b06104b2cb21ab012fb677b1b2f42b7ec820e408d`.
- Archive SHA-256: `d82deba62136e53dee67bc2207ae858b52e18df154105600f515d7ba8afc93cc`.
- Archive: 665,600 bytes, 61 tooling/manifest files. Nine private inputs are copied
  only between roots on wspr5; keys/passwords are not uploaded or exported.
- Staging helper SHA-256: `788fb4c6595506916763229e900b6c9ccb0f7f941b0192eb282e1b2ad4e6830f`.
- Finite job IDs: `cc44aac70aa03dd771d3a625461b97d6` and
  `ee6aa1ec84633d13b3f35bb61cae24a8`.

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
