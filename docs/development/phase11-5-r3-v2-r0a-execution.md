# R3 v2 R0A idle terminal reconciliation

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

- `root`: `/home/pi/phase11-5-r3-v2-reconcile-r0a-20260913`
- `packet_sha256`: `951e45b570756b4ea640a3efcdd4a21d935a0256ae29aaf2a72b3af55a4a6a25`
- `archive_sha256`: `aa1dc2a26df1f669afb69283db7a949713d5e2c5e4b180f83706a89b66881cc7`
- `helper_sha256`: `ba8717fc8fd8d4dd0064ce9478fc6af85229c3182b1240371fc310573bbe40a6`

## Corrected dependency closure

R0 failed before opening a device because its staged schema was missing. It
made zero CLAIM, RELEASE or RF attempts. Preserve its result and stderr.
R0a includes and hashes the schema; a mandatory dependency check runs before
any inventory or result marker. Two tests cover missing schema/manifest and
unsafe terminal admission. The staged dependency check passed locally.
