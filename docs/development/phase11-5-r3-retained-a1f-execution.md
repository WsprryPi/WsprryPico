# R3 A1f: corrected in-flight observation handling

**Executed and consumed.** Both Tones and all traffic workers completed; the
frozen audit failed. Three audit integration defects and a separate INFO
completion-bracket miss were reconstructed offline. Zero acceptance is awarded;
see the [causal review](phase11-5-r3-completion-review.md). Do not rerun this packet.

This is a fresh execution after A1e exposed a confirmed pressure-checkpoint
mismatch. A1e's INFO request completed in 1.739 seconds, within its five-second
limit, with request starts within the two-second cadence. The pressure tool
ignored the published in-flight read and stopped early. Its completed Tone and
full 360-second observation remain preserved; later worker stops were consequences.
The shared bounded-read admission is now used without changing any deadline or
offline acceptance threshold. Twenty targeted TLS tests pass, including in-flight,
expired, foreign-identity and wrong-operation cases.

Continue the original comprehensive R3 execution/repair instruction within its
finite Tone envelope. A1f adds **no Wi-Fi OFF/ON cycle**; the one cycle explicitly
approved for A1e has already run. Retain the recovered test configuration and
unchanged wiring. This new root and new job IDs do not replay A1e's failed packet.
If network admission fails, stop and diagnose; do not reset Wi-Fi again implicitly.
A1f can only cover the initial TLS/slot subset and cannot close all R3.

- New root: `/home/pi/phase11-5-r3-retained-a1f-20260912`.
- Packet SHA-256: `cc557f977c655ac974c60c8343f1e8ba52dbd40b7837fdac9eb8561a63910236`.
- Archive SHA-256: `9dd47e1866871a66a8f4fb24dfa5c215aab097d1401a035082b7a3518684b39a`.
- Archive: 675,840 bytes, 62 files; nine hash-bound private copies remain on wspr5.
- Staging helper SHA-256: `788fb4c6595506916763229e900b6c9ccb0f7f941b0192eb282e1b2ad4e6830f`.
- A remains physical `2e43110f0530`, 138 MHz/divider 1/RAM/GP2/listener on,
  boot `9c5aec394269e0b57ca16d73ad3d12b6`; B remains unchanged and inactive.
- Retained test Wi-Fi input SHA-256:
  `fc42b65f177e62afc6664ffc1f13bc14e7711d7cd51c9d191c2e0c580d620764`.
- Baseline inventory SHA-256:
  `b33591c493bbeed358cbcab5652809f02768ede2a403bcf5dfd1374706755e6e`.

Stage the frozen archive and copy the existing credentials, native TLS observer,
retained Wi-Fi input and baseline inventory into the new private root. Verify
all hashes before device or host setup. Use the already-confirmed unchanged
60 dB conducted path documented in the completion prompt.

Perform fresh read-only A/B inventory. If A is Empty/inactive/unowned, leave its
job state alone. If A still retains exactly the known completed A1b job, a
separate bounded CLAIM/RELEASE may clear current-job state only after fresh
STATUS proves Complete/inactive/unowned and retains the error-free completion.
Preserve terminal history. No ABORT, reboot or flash is a cleanup mechanism.

Create the isolated wlan0 AP/wlan2 client fixture with the retained password,
native time.local and the pinned RF-off Pi controller. Independently arm owned
host cleanup first. The host window is at most 1,800 seconds plus 600 seconds
cleanup; the normal controller window is 300 seconds and USB observation 360.

Submit exactly two 100-second Tones at 135,500 Hz, through the sole USB observer:
`7f0198663d01009631fb2c4f16c1249c` and
`04973b6fde7ea85c37075ffe60dacead`. Total RF ceiling is 200 seconds. The frozen
packet permits at most 12 renewals and 12 pressure TCP connections. Exercise the
existing ten independently named TLS/slot cases: two positive controls,
missing-client-certificate rejection and recovery, activated silent-handshake
timeout and recovery, active/pending/excess slot pressure and recovery, and
post-handshake duplicate-WTP rejection and recovery. Retain raw HTTP responses,
TLS events, target counters and independent RF epoch/job/owner brackets.

Stop new injections/jobs on any failed worker, stale identity, firmware fault,
resource violation or observer failure. Keep the finite-job observation alive
where possible; never infer inactivity from a socket closure. Audit the complete
run against the existing RF, resource, controller and TLS/slot gates. A partial
run cannot pass. Final reconciliation is limited to the exact prior/new completed
jobs. Verify inactive/unowned A, unchanged B, and restored host resources.

There are **zero CONFIG saves, flashes, reboots, heap probes or Wi-Fi OFF/ON
commands**. Keep the dedicated Pico's test configuration after the run.
