# Browser B2 final-image acceptance on Pico A

This packet uses the accepted R3-COMPLETE-20260913-v2 authority and unchanged
60 dB conducted wiring. B2 is a browser packet label; it controls Pico A only.
A source 8921a70081839f168edef5926e92445f251d8e1d, boot
fc90d1a04eb0acc703de907917277921, 138 MHz/divider 1/RAM/GP2. No B access.
Use the existing F1 client PID 491605, net:[4026532629], mnt:[4026532725],
with unchanged absolute cleanup deadline 306202695885000 ns. Require the full
900-second execution and 150-second cleanup allowance before that deadline.

Run real Chromium against the target-served UI with its private existing trust
and full authenticated requests/responses. No application-function replacement.
Verify the server certificate and source-served asset hashes independently.
Maximum 250 requests and four jobs, charging at most 452.250003 seconds before
ARM. Frequency 135500 Hz with only the frozen 135495 Hz mode shift.
No CONFIG save, Wi-Fi cycle, flash, reboot or heap probe.

Check 31/32/33-character previews and spaces in QRSS, FSKCW and DFCW. Reject a
real 30001-byte file before job submission. Complete the real 30000-byte valid
10-second Tone file. Complete a 32-character FSKCW plan lasting 143.250001
seconds. Cancel a 143.250001-second QRSS plan while independently observed
Armed. Cancel a 155.750001-second DFCW plan only after at least 120 seconds
independently observed Running. Preserve the complete planned durations for all
four charges, including canceled jobs. No canceled job counts as completion.

Independent one-second INFO and five-second STATUS/host-health observers guard
all mutations. Require inactive/unowned admission, correct boot/owner/job binding,
actual duration/progress, stack/heap reserves and finite timing. Capture screenshots
and exact DOM/state for visual review. A failure stops future producer mutations;
readers continue to the original deadline. Reconcile final authority explicitly.
Preserve each completed assertion and perform independent raw/visual review.
Do not replay this packet or change an executed packet's bytes.

- packet_sha256: `21569af32117cd0ea8bb1117446e3cdf55584325429b5a88abc6b55a3723db5e`
- archive_sha256: `6c20bb4248f81864e8fd2bc06fa62873d1959783deb5f2adf8bdf4a90526a58b`
- root: `/home/pi/phase11-5-r3-v2-browser-b2-20260913`
- stager_sha256: `d81262d706323cc75a1467a9f8b0d896598976acae063664f40b72bdf6ea6712`
- observer_sha256: `bc71eb08e36d0491148d514748d7ad3ad49cd3e1bc5a072b90ac4e0bb7671792`
- producer_sha256: `56a27e9f37f7791777fc8ada8cf24a2ede6f3cfb79b5cda642ff798c05705f04`
- guard_sha256: `0b685c30c41a86b9c825a4754ef852a11e627b2151211f96b28c53406b6eb218`
- planned_jobs: `4`
- rf_duration_ns_charged_maximum: `452250003000`
