# R3 A1h: bounded rejoin with evidence captured before cleanup

**User approved the additional recovery cycle and conditional two Tones with
“I approve.” on 2026-09-12.** The packet was finalized before staging; local
`authorization.json` records the approval and exact final packet hash. The first
local draft is preserved under `build/phase11-5-r3-retained-a1h-review1` and was
never staged or executed. Final review added a read-only check that the diagnostic
capture service is alive; it does not enlarge the approved mutation scope.

**Execution outcome: FAILED before recovery and RF.** A transient JOINING sample
was rejected by the admission harness. Zero Wi-Fi commands and zero RF jobs ran;
A/B and host cleanup passed. The [raw diagnosis](phase11-5-r3-network-diagnosis.md)
retains the failure. [A1h2](phase11-5-r3-retained-a1h2-execution.md) continues the
unused approved allowance with a bounded read-only transient-state wait.

A1g failed before RF. Its AP completed the DUT's WPA handshake while all 25 DUT
samples lacked an address and clock synchronization, ending in BADAUTH. This
establishes a disagreement requiring better evidence, not a proven bad password
or a localized firmware defect. A1g performed no Wi-Fi cycle. A1h's additional
cycle is separately authorized by the user's latest approval.

The `request-cadence-and-roundtrip-v1` observation rule was already approved for
A1g and carries forward unchanged. See the exact rule in
[the A1g packet](phase11-5-r3-retained-a1g-execution.md). Old attempts keep their
original scoring and receive no retrospective credit.

## Frozen artifacts and identities

- Packet: `build/phase11-5-r3-retained-a1h/stage/packet.json`, SHA-256
  `e59ee91202eb01622fa0185fb0cb2102612ba428edd2a616eeabd82b799e89a9`.
- Archive: `build/phase11-5-r3-retained-a1h/staging.tar`, SHA-256
  `f873b8aa424e784153c64b7e48f53874104277984093f51de6cf834042d9cfb1`;
  716,800 bytes, 67 tooling/manifest files, nine private inputs copied only
  within wspr5. No private credential or Wi-Fi value is exported.
- Fresh root: `/home/pi/phase11-5-r3-retained-a1h-20260912`.
- Stager SHA-256:
  `788fb4c6595506916763229e900b6c9ccb0f7f941b0192eb282e1b2ad4e6830f`.
- Source: `2e43110f05304efdc2ae25c298baa0ef6426955b`, embedded `2e43110f0530`;
  physical UF2 `7e6e732cc7a9e196609413dfe228781a725ece56bed1b4a99a96d1cc8741baf6`.
  No firmware change or flash. Physical 138 MHz, divider 1, RAM renderer,
  listener enabled, GP2 PIO/DMA.
- Pico A serial `0BF4B4AEC9FFB344`, WTP `fd6127d11d6aca42a9905fa3fb1bf1d5`,
  boot `9c5aec394269e0b57ca16d73ad3d12b6`; last verified Empty/inactive/unowned.
- Read-only Pico B serial `CDDBF8767C506C07`, WTP
  `29f20b7342051ef947aa56cb9d4fab42`, boot `feffcd075ab6cb0b74e7e0c2fde6c87f`.
- wspr5 boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`; installed PID 1957 and
  executable hash `c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`
  remain protected. The separate RF-off production load uses source
  `6f65d5c7d202569102459ab68d7c9ea079b96f35`, executable hash
  `122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`.

## Exact work and stopping conditions

Stage into the new root and validate every frozen helper/input hash before setup.
Reuse the isolated wlan0 AP/wlan2 client and retained test input from the retained A1b input. Protect
eth0/wlan1 management, installed WsprryPi, permanent time.local/GPS-PPS services,
B, GPSDO, SDR and wspr5 GPIO4. Arm independent host cleanup before setup:
1,800-second fixture maximum plus 600-second cleanup, with 375 seconds remaining
before RF starts. Keep the unchanged conducted 60 dB, 50-ohm wiring described in
[the comprehensive prompt](phase11-5-r3-completion-prompt.md).

Fresh INFO/WTP admission must prove the exact firmware, boot, inactive/unowned
state, healthy resources, retained configuration, AP input match, address and
synchronized clock. No CONFIG saves, flash, reboot or heap probe is permitted. At most one idle
Wi-Fi OFF/ON cycle is authorized if the same-boot fresh state is inactive,
unowned, without an address and reports NONET/BADAUTH. If connected, skip the
cycle. Record write-ahead intent and exact OFF/ON acknowledgments; no retry of
an uncertain mutation. Network readiness failure stops without RF.

Start an owned DHCP/ARP/mDNS/NTP packet capture before activating the AP; require
the capture service active before AP activation and after fixture setup. Do not
capture EAPOL handshake traffic. Observe up to seven passive inventories at
five-second intervals before considering recovery, and save the AP journal and
live station state before recovery and before host cleanup. The journal filter
is restricted to this host boot, fixture interval, wpa_supplicant and wlan0.
The existing 25-sample network/clock admission still governs RF. Diagnostics
cannot excuse a failed readiness check or establish a specific firmware cause.

Run two 100-second Tones at 135,500 Hz, at most 200 seconds RF total:
`991dd802f9ca6a110bb960436ca972d7` and `073a6b5c8296c2bf1c101d7137262d5d`.
Each has one immutable event. Use separate CLAIM/LOAD/GET_CLOCK/ARM/complete/RELEASE
lifecycles, ARM ten seconds ahead with 500 ms maximum uncertainty, twelve total
60-second lease renewals at most. The second requires the first's pressure work
to finish successfully and fresh released idle authority.

Preserve the ten [A1 TLS/slot cases](phase11-5-r3-tls-execution.md): two positive
HTTPS controls; missing certificate and recovery; silent handshake and recovery;
held active/pending sockets, excess rejection and recovery; duplicate WTP and
recovery. Twelve pressure TCP connections total, no retries. The ordinary
production controller is RF-off for 300 seconds; no ordinary browser load.
The exclusive USB observer lasts 360 seconds. Preserve 32 KiB heap reserve,
both 4 KiB stack guards, unchanged unexpected failure counters, exact per-job
DMA/launch/tail checks and the original full/short-predecessor timing budgets.

On any worker, identity, deadline, resource or output-authority fault, stop
subsequent injections/jobs and preserve the original evidence. Keep the sole
observer through its bounded window where possible. Reconcile only known
Complete/inactive/unowned jobs; never infer inactivity from a closed connection.
Verify final A inactivity/ownership, unchanged B and restored host. Keep the user's
test configuration and retained terminal records, subject to normal expiry.

A1h can establish only the initial TLS/slot subset. The remaining R3 register,
including maximum allocations, USB/retained-state pressure and three measured
reclamation cycles, must still be completed before closing R3.
