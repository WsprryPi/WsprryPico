# N3: native acknowledged-ARM loss and reconciliation

Fresh authorized Group 1.3 packet. Preserve N0 QRSS, N1 FSKCW and N2 DFCW
submission evidence; N2's socket loss FAILED because ss returned an error with
exit code zero and left the socket established. No N2 loss credit is granted.

One 155.750000-second, 383-event native DFCW job (32 question marks), dot
135500 Hz and dash 135505 Hz. Complete planned duration charged before actual
production process start. 600-second execution and 150-second cleanup bound;
no second dispatch, flash, CONFIG, Wi-Fi operation, allocation probe or B access.
A must remain source a740dbb / UF2 454e03e5 / boot 2b4583bd3d79a38f030a08c82ed96939,
Empty/inactive/unowned, scheduling disabled, synchronized, in the exact F2
namespaces before its unchanged absolute cleanup deadline. Verify protected
installed process and isolated bba4024 binary hashes at admission.

After raw complete ARM ACK and independent Armed/Running proof, verify the exact
native PID, socket descriptor and four-tuple. pidfd_getfd duplicates that socket;
its inode, local address and peer must still match before SHUT_RDWR. The native
process remains running. Linux aarch64 syscall 438 was rehearsed successfully
against a task-owned child process and loopback sockets: peer EOF, child alive.
No kernel configuration change or service restart is involved.

One loss attempt only. Continue independent USB observations through local
completion. Require the original native session to be blocked before explicit
/api/wtp/recover reconcile; then require same-session/device/boot recovery to
idle. Raw TLS must show two authenticated connections, exactly one CLAIM/LOAD/ARM,
no uncertain mutation, and no reconnect before the explicit reconciliation.

The revised harness rejects ss stderr even with exit zero. Wrong socket tuples
prevent shutdown, pidfd cleanup is tested, and partial/pending mutation/incorrect
ARM ACKs prevent a loss action. Fourteen focused native tests pass (one optional
actual-capture test skipped); N1's real archive and nine missing-evidence variants
also pass. Staged import/manifest rehearsal passed. N2's full audit and stopped
unit are prerequisites. Independent audit and a new checkpoint are required.

- root: /home/pi/phase11-5-r3-v2-native-n3-20260914
- packet_sha256: 5b074896a06d9bae022e89fcac58355e92b823fc43e6f5da12a4fdb970458d95
- archive_sha256: ab1dddbfca318cfe07a7768cbbfd70395a4a2aca7f6a13e3665729deb98d8cd4
- stager_sha256: f2358e2116bcfc90649cbf7ec92d520ae47ec33861afb3b7a88070fb44e448c4
- observer_sha256: 2a5cf555cba7c7ad59779d65f750b96578e05188002cc0258068d3851f40b99a
- producer_sha256: acd0173e8d08332cf2e15bfbe1733d1788c0bda24bdcf284f304ada6bac7a2e3
- auditor_sha256: c08df2429bc0301a5f1a6a39673d61eabbe300db934e8b5c8dc006938d55b5f8
- planned_jobs: 1
- maximum_duration_ns: 155750000000
