# R3 v2 R0 idle terminal reconciliation

Authorized recovery under accepted R3-COMPLETE-20260913-v2. Execute only after
H1a's owned systemd group has stopped and its evidence archive is preserved.
150 seconds total; zero RF starts, aborts, flashes, reboots, Wi-Fi changes,
CONFIG writes or heap probes. A remains the same source/image/boot as H1a;
B is read-only and must remain unchanged. No host networking or service change.

Read A/B inventories. Only an authoritatively inactive, unowned Complete for
H1a job 53025ecfb22bb5e40dd194e07226a49b permits one fresh HELLO/STATUS,
one CLAIM and one RELEASE. If already Empty, no mutation occurs. The exact
state is checked again before claim; an active, unknown, mismatched or owned
state fails admission. Preserve terminal history, configuration and all RF
counters. Read and reconcile final A/B independently. The hardware-free
admission test rejects ten unsafe/mismatched cases and active Console output.
Prior H1a evidence remains immutable; this operation has its own journal.

- `root`: `/home/pi/phase11-5-r3-v2-reconcile-r0-20260913`
- `packet_sha256`: `45cbbb47291d6bc33de0d1f68acd7031cf27f2dc70ab25938faf2005cc1e5d97`
- `archive_sha256`: `a4c342785f24f42488f6a6eaf7f69551b1b22475ab62068edcbd45a9f8d43d5f`
- `helper_sha256`: `1c4f609cdcb5e705a995302a7d4afe1b93aac4c7645f24d7934f4f2571d6a776`
