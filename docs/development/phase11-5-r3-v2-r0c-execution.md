# R0c: normalize the completed B4 job for remaining tests

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

- root: /home/pi/phase11-5-r3-v2-reconcile-r0c-20260913
- packet_sha256: ec07a3f4909ed039d04dbafcb17b4c5ef6fe31d2de38f6dbc4f0cd35b23783e4
- archive_sha256: 188d53dcc7142869d86f2239be5ebf3711e13cd1e30f58def66befdf88617fb1
- helper_sha256: 61c7a09af3b3b7a17ccef38fa1f365e571890881645bb6c5865c1cb3147c761d
- stager_sha256: 73e972b3310f571d5ceb57019dfc49256f51d7643b47092ea757e7efedb5def0
