# R3 retained-baseline A1c execution packet

This is the first concrete execution of the
[R3 completion prompt](phase11-5-r3-completion-prompt.md), under the user's
instruction to render and execute that prompt. It supersedes neither the frozen
A1/A1b attempts nor their failures. It can cover only the initial TLS/slot subset.

- New root: `/home/pi/phase11-5-r3-retained-a1c-20260912`.
- Packet SHA-256: `3167ff5d4c9e58b908ed0d5fcb64a278454a236857f5442ec0662e1e66fc5156`.
- Archive SHA-256: `bc66425349d8419ac4bf214b02f2d331825e2dde6219ac83b6e1adc0a349f686`.
- Archive: 655,360 bytes, 61 files; nine hash-bound private copies remain on wspr5.
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
`e5c0cc6f6d52afeb0cb589328f951293` and
`0811402294244ac759ca9e8a5c27dbe1`. Total RF ceiling is 200 seconds. The frozen
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
