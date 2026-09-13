# R3 v2 E1 HTTP repair image idle admission

Reviewed under accepted R3-COMPLETE-20260913-v2 and the user clarification
to retain the tested image except for a demonstrated code defect. B is read-only.

The replacement RF-capable image c5f00b6109cc repairs the independently
reproduced maximum-HTTP outer-padding admission defect. It does not switch A
to an inhibited image. Both local builds pass linked-image checks; all 62 host
groups pass. The RF renderer is byte-identical at its prior RAM address and
checked heap/stack boundaries are unchanged. Physical HTTP/browser/contention
regressions remain required. Retain this repaired image after testing.

Execute only after H2b ends, its raw archive is preserved, and A/B are verified
inactive/unowned. The unchanged admission runner independently reads A/B before
one serial-specific BOOTSEL and verified flash, within 600 seconds. Require the
actual prior 7d183978 source and 8e777dadaa81f4618154d84de0df268a boot. Record the
new clean source/boot, unchanged saved test configuration and unchanged B.

Zero RF starts, Wi-Fi cycles, CONFIG saves, extra software reboots and heap
probes. Require 512-event/3600-second CAPS and the same 65536-byte WTP limit,
32 KiB reserve and stack guards. Exercise full 65536-byte STATUS and framed
65537-byte rejection with same-connection recovery. Reject 513 events and
3600 seconds plus one nanosecond. LOAD the complete 512-event/3600-second plan,
require 512 adjustments while inactive, ABORT Loaded, RELEASE, and verify
Empty/inactive/unowned. Never ARM. Preserve each assertion and final A/B/host
inventories. No automatic retry or restoration flash. A failure retains its
exact evidence and requires diagnosis under the existing recovery authority.

The credential-bearing UF2 is transferred separately, hash-verified and copied
with mode 0600 into the private task root. It is excluded from public staging
and Git. The public staging helper and dependency closure are frozen.

- `packet_sha256`: `5b61ffdf74ab0e1f5daa77bef59ea2c3e7d797c128cf8499d3d90c6178965ab0`
- `archive_sha256`: `7f732a469ad6120e95064b37fe3577018cfaf4806c9dc9ccc60597bccf7070cc`
- `root`: `/home/pi/phase11-5-r3-v2-idle-e1-20260913`
- `stager_sha256`: `2589a3b2f47bb205370a9e8a2e8e184855228757ac1449ce3abf28d880b2a8e7`
- `image_sha256`: `5f681b10d2c076309116cb9c20df1653d21e522ad19b6b33c1ee57efb3f54756`
- `source_revision`: `c5f00b6109cc1c692b3f6bf258c1a77dadef6639`
- `runner_sha256`: `0958e73ae7389eb06cfd7ab9c20907412f9133f48296050701348bbbd9ebb195`
