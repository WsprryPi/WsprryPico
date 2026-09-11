# P3 allocator-instrumented RF diagnostic

Status: executed successfully; see [result](phase11-5-allocator-result.json). This repeats the previously bounded P2 diagnostic
on the changed allocator-instrumented image before the longer contention cases.
It is not full A3/N, stack acceptance, fragmentation acceptance or RF qualification.

- Pico A USB `0BF4B4AEC9FFB344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Clean source `3eac6ec030963a5318515ce5f4683acf6fa88506`, runtime `3eac6ec03096`.
- Physical PIO/DMA, GP2, 138 MHz, divider 1, SRAM renderer.
- UF2 SHA-256 `6b90e34843de1e7b0845f3585f966714521207e9010430bfad76c58e42281054`.
- Packet [phase11-5-allocator-pilot.json](phase11-5-allocator-pilot.json), SHA-256
  `a6a78dfc0c4b433c7a540584f87bf3dcb283ba10f42166a684a365a340578143`.
- Exactly three 10-second 135,500 Hz Tone jobs, 30 seconds maximum commanded RF.
  Complete once, release once, no automatic retry or abort/fault clearing.
- Confirmed 50 ohm / 60 dB attenuation / combiner / unfiltered GP2 conducted path.
  Pico B remains read-only. GPSDO, SDR, GPIO4, radios and existing services retain
  their configuration and state. No heap probe or network mutation is included.

Use the unchanged six helper/schema files hashed in the packet. Require a new
private `/tmp/phase11-5-p3-3eac6ec` directory and absent
`phase11-5-p3-3eac6ec.service`. Stage the packet, candidate and original inhibited
restoration image. Host boot must remain `220e53ca-ca95-4206-9581-dbe28aa1eeb8`.
The verified picotool path/hash and original-image hash are enforced by the
existing supervisor.

Register Type=exec, Restart=no, RuntimeMaxSec=600, TimeoutStopSec=420, UMask=0077,
with ExecStopPost installed before ExecStart. Maximum lifecycle is 17 minutes.
ExecStart is:

```text
/usr/bin/python3 /tmp/phase11-5-p3-3eac6ec/scripts/phase11_5_pilot_supervisor.py start --packet /tmp/phase11-5-p3-3eac6ec/packet.json --candidate /tmp/phase11-5-p3-3eac6ec/candidate.uf2 --restoration /tmp/phase11-5-p3-3eac6ec/restoration.uf2 --evidence /tmp/phase11-5-p3-3eac6ec/evidence --run
```

ExecStopPost uses the same arguments with `restore` replacing `start`. It takes
serial-bound inventories of both boards, backs up and verifies A's original
application, flashes the exact candidate, verifies configuration/clock/engine,
runs the finite jobs and records USB INFO at 1 Hz and host health at 0.2 Hz.
The original 25% descriptor reserve, 2,849,391 ns service-gap threshold and full
DMA/launch/tail counts remain enforced. The allocator counters are additionally
recorded for independent review; they do not themselves establish heap acceptance.

An unexpected fault, boot change, missing observation, failed job or failed
cleanup stops dependent actions. Restoration requires complete successful pilot
records plus fresh authoritative same-boot empty/unowned/output-inactive A and
unchanged B/configuration. Only then flash original inhibited image SHA-256
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10` and verify both
boards. Otherwise preserve the failure and block automatic device restoration.

Local packet/image validation passed with no `--run` and no hardware access.
