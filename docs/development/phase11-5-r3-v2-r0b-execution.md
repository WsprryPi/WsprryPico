# R0b: normalize the completed B4 job for remaining tests

Under accepted R3-COMPLETE-20260913-v2, retain A source f5502cf and boot
2d34c532eb46a11a6b2cede5eae8f796. After B4 finishes all original observers and
its evidence is collected, require fresh same-boot inactive/unowned Complete
for job 35250e73a194432aa90e24110a18110b (or already Empty).
Use at most one idle CLAIM and RELEASE, preserving terminal history and every
RF counter. Require final authoritative Empty/inactive/unowned and identical
configuration. No RF, flash, reboot, CONFIG, Wi-Fi or heap probe. Runtime 150
seconds. Do not access B; its independent zero-RF authorization remains separate.
This releases the prior current-job storage through the existing WTP lifecycle.
It does not erase replay caches, terminal evidence or the rejected QRSS result.
The helper verifies its full dependency closure before opening either A port;
three deterministic reconciliation tests passed. Do not replay the fresh root.

- root: /home/pi/phase11-5-r3-v2-reconcile-r0b-20260913
- packet_sha256: 13ed2ac1e8cfeeded4214f9da59eff5af0fecf2c9c4638fd331c1839b22d0308
- archive_sha256: d4db164fb23b2228d75c2935e2e6a5dc77726f8d9eb55649da4fcac56b61d670
- helper_sha256: 61c7a09af3b3b7a17ccef38fa1f365e571890881645bb6c5865c1cb3147c761d
- stager_sha256: f5b57069a10e97219eb9b98d68423dca66ddf12ca18728e76e3c88ea46141d76
