# P2 SRAM renderer verification packet

Status: AUTHORIZED AND COMPLETED; bounded diagnostic PASS and inhibited
restoration verified. See [the exact result](phase11-5-remediation-result.json).
This records a completed packet and does not authorize repeating it.
This is a new physical packet,
not continuation authority from the failed P1 or completed fault recovery.

Purpose: check whether the unchanged 25% refill reserve, 2,849,391 ns worker
service-gap and finite terminal completion criteria pass with the reviewed SRAM
renderer and existing 100 us acknowledgement repair. A pass is a bounded
three-Tone diagnostic, not acceptance of 138 MHz or closure of Phase 11.5.
No band/clock sweep or GPSDO/SDR setting change is included.

## Exact identity and operations

- Device: Pico A USB 0BF4B4AEC9FFB344, WTP fd6127d11d6aca42a9905fa3fb1bf1d5.
- Clean source/helper revision: 0d9bb44a6b91679bd174c39ac068d5d9cc74e9c5.
- Runtime revision: 0d9bb44a6b91; StandaloneRF, pio-dma-gp2, system/sample clock
  138000000 Hz, PIO divider 1, renderer SRAM ON. INFO must report that placement.
- Candidate UF2 SHA-256: abb92721dbcdb0c96909b4f5c23aa680733ba4509aaf02ee9d7214c4af8f1247.
- Local preserved image: build/phase11-5/artifacts/0d9bb44a6b91/on-WsprryPico-StandaloneRF.uf2.
- [Machine packet](phase11-5-remediation-pilot.json) SHA-256:
  ab49bd3c3309c8767f43fb474473c58036efa2af6ac2fe383c124f1139e658ff.
- Host wspr5 boot: 220e53ca-ca95-4206-9581-dbe28aa1eeb8, Ethernet 192.168.1.54.
- Exactly three distinct 10-second Tone jobs at nominal 135500 Hz:
  75ea80a046594a909168b3c8af0b711d,
  ea0d5a2b06e74806a8500e96705a539f,
  bf691b6fdf6841798c36d6734b93a273.

The user-confirmed path remains GP2 through 20 dB into the combiner, then
20+10+10 dB to the SDR: 60 dB per input plus combiner loss, 50 ohm attenuator
loads, no filters. The already-connected GPSDO and Pico B remain unchanged.
No SDR capture is part of this resource diagnostic.

Authorization covers staging the exact private bundle, dry validation, one new
transient supervisor, serial-specific inventories, one guarded A BOOTSEL and
full flash backup, one candidate flash, the three jobs, authoritative final
reconciliation, and conditional restoration of the original inhibited image.
Pico B USB CDDBF8767C506C07 is read-only throughout. No existing host service,
radio, GPIO4 route, interface, station/schedule configuration or GPSDO changes.

The original [P1 supervisor and stop rules](phase11-5-pilot.md) apply unchanged:
INFO every second, persistent WTP/status observations, host health every five
seconds, finite LOAD/ARM once per job, completion before RELEASE, 10-second
initial/final idle observations, no retry, no automatic ABORT/fault clearing.
An observer, reserve, service-gap, identity, ownership, output, DMA or terminal
failure stops dependent actions and preserves evidence. This may prevent
restoration; failure does not grant permission to reset or reflash the DUT.

## Restoration and supervision

Use only new private directory /tmp/phase11-5-p2-0d9bb44 and unit
phase11-5-p2-0d9bb44. Require both absent before staging/execution. The bundle
contains the six helper/schema files hashed in the packet, packet.json,
candidate.uf2 and restoration.uf2. Do not alter helpers in place after freezing.

Use Type=exec, Restart=no, RuntimeMaxSec=600, TimeoutStopSec=420. Register
ExecStopPost before starting the unit; maximum unit lifecycle is 17 minutes.
The helper also enforces its own bounded subprocess/USB/pilot deadlines.

ExecStart:

```text
/usr/bin/python3 /tmp/phase11-5-p2-0d9bb44/scripts/phase11_5_pilot_supervisor.py start --packet /tmp/phase11-5-p2-0d9bb44/packet.json --candidate /tmp/phase11-5-p2-0d9bb44/candidate.uf2 --restoration /tmp/phase11-5-p2-0d9bb44/restoration.uf2 --evidence /tmp/phase11-5-p2-0d9bb44/evidence --run
```

ExecStopPost uses those same arguments with `restore` replacing `start`.
No automatic restart or repeated invocation is allowed. On successful full
pilot evidence only, restoration requires fresh same-boot idle/unowned/inactive
A, unchanged B and configurations, then guarded BOOTSEL and one verified flash
of original inhibited UF2 SHA-256
25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10.
Verify both boards afterward. Raw backup is evidence, never an automatic image.

Local packet and image validation passed without --run or hardware access.
The latest authorized P0 reads confirmed A's restored boot
4571042e06f139bc185e862482082291 and B's original boot
4e2fb851c08b278dd4b977104d2c2aaa, both empty/unowned/inactive. Fresh inventories
inside the supervisor remain mandatory. Previous failed units/logs stay intact.
