# R3 A1g proposal: separate observer cadence from reply latency

**Approved and executed; failed before RF.** The user approved the prospective
observation rule and conditional two Tones. No RF or Wi-Fi cycle occurred because
network/clock admission failed. The rule is approved for future packets; A1f
retains its original failed scoring. See the [raw network diagnosis](phase11-5-r3-network-diagnosis.md).
The specification below preserves the original prospective wording and hashes.

## Criterion requiring agreement

The frozen older audit required an INFO reply to complete within two seconds
after every pressure case ended. A1f missed that criterion once: its next read
started 0.656231927 seconds after the case and took 1.606318998 seconds, yielding
a reply 2.262550925 seconds after the case. The read met the five-second deadline
and the observer met its two-second request-start cadence. This is an observation
criterion conflict, not a demonstrated firmware or RF deadline failure.

A1g proposes `request-cadence-and-roundtrip-v1`:

- INFO request starts remain at most two seconds apart; STATUS starts remain at
  most six seconds apart. The scheduled intervals stay one and five seconds.
- Every individual read must still complete within five seconds. Negative,
  missing, overlapping or incomplete raw exchanges cannot establish a bracket.
- Both case boundaries need a fresh completed observation, or a replacement
  read actually in flight within the existing five-second deadline.
- The following independent sample must begin by the next cadence deadline and
  complete within its five-second read deadline. Thus its completion may follow
  a case by up to seven seconds for INFO or eleven for STATUS. Every bracketing
  sample must prove the same boot, owned Running job and launch epoch.
- Whole-run raw reconstruction, observer coverage and individual transaction
  deadlines remain mandatory. Firmware 10/15/30-second mechanisms, the pressure
  deadlines, 15-second recovery bound, resource reserves and RF timing do not change.

The new code uses this policy only when the frozen packet explicitly names it.
Older packets retain their original scoring. A1f's alternate-policy evaluation
is labeled DIAGNOSTIC_ONLY and cannot confer acceptance. Agreement is requested
because this changes a frozen measurement criterion; ordinary permission to run
RF does not by itself resolve that scoring choice.

## Frozen artifacts and identities

- Packet: `build/phase11-5-r3-retained-a1g/stage/packet.json`, SHA-256
  `e512fac77302ee21f6fe7f9536d5c3215dcd997565770684906d4409cbdb0ed4`.
- Archive: `build/phase11-5-r3-retained-a1g/staging.tar`, SHA-256
  `23ba61adddb5f6fe39fcef4ced0a168855b1747e96b455fc0488b41d56009468`;
  706,560 bytes, 64 tooling/manifest files, nine private inputs copied only
  within wspr5. No private credential or Wi-Fi value is exported.
- Proposed fresh root: `/home/pi/phase11-5-r3-retained-a1g-20260912`.
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
Reuse the isolated wlan0 AP/wlan2 client and retained test input from A1f. Protect
eth0/wlan1 management, installed WsprryPi, permanent time.local/GPS-PPS services,
B, GPSDO, SDR and wspr5 GPIO4. Arm independent host cleanup before setup:
1,800-second fixture maximum plus 600-second cleanup, with 375 seconds remaining
before RF starts. Keep the unchanged conducted 60 dB, 50-ohm wiring described in
[the comprehensive prompt](phase11-5-r3-completion-prompt.md).

Fresh INFO/WTP admission must prove the exact firmware, boot, inactive/unowned
state, healthy resources, retained configuration, AP input match, address and
synchronized clock. No CONFIG saves, flash, reboot, heap probe or Wi-Fi OFF/ON
cycle is permitted. Network readiness failure stops without RF; no automatic retry.

Run two 100-second Tones at 135,500 Hz, at most 200 seconds RF total:
`ac093064beb6a416e510d30f674d0aa6` and `adf8d7cc233060c87a409a7ff06082f7`.
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

A1g can establish only the initial TLS/slot subset. The remaining R3 register,
including maximum allocations, USB/retained-state pressure and three measured
reclamation cycles, must still be completed before closing R3.

## Final preparation review

The first local A1g draft was retained under
`build/phase11-5-r3-retained-a1g-review1`; it was never staged or executed. The
current hashes above supersede it. Review found another R3 consumer with the old
freshness check and a 1.5-second blocking wait for completion INFO. The USB actor
now uses the same bounded in-flight rule and defers release to a later scheduled
STATUS sample until the current launch's completed INFO is available. It retains
owned Complete meanwhile; it neither releases early nor submits a replacement.
R3 STATUS is published before subsequent USB actor operations, so their latency
cannot be mislabeled as read latency and the sampled authority survives an actor
failure. R2 execution behavior is preserved. Regression tests cover delayed INFO,
old launch epochs, failed publication/read and a lost RELEASE reply.
