# R3 v2 BD0 approved parallel B deployment

Execution under the accepted [parallel B plan](phase11-5-r3-v2-parallel-b-authorization.md)
and its separately recorded acceptance. H2b and E1 finished with independently
verified unchanged B; both audit hashes and stopped supervisor gates are frozen
in this packet and checked before any B endpoint opens.

B only: CDDBF8767C506C07 / 29f20b7342051ef947aa56cb9d4fab42.
One serial-specific BOOTSEL and verified flash of clean c5f00b6109cc, retaining
B's existing configuration and schedules disabled. Keep this RF-capable image
on B; it receives no ARM, LOAD, RF, Wi-Fi cycle or CONFIG write in this packet.
No A endpoint is opened. 300 seconds execution plus 150 seconds cleanup.
The image and all staging dependencies are hash-bound. Require fresh B identity,
new boot, 512-event/3600-second CAPS, inactive/unowned output, zero launch/DMA/
alarm/tail activity, 32 KiB reserve and intact stack guards. Independently audit
raw inventories and the verified serial-specific flash before functional work.

- `packet_sha256`: `9e491643982fb5c0480c866666143530ea7ccc612ba32a2a2692308eb44aa214`
- `archive_sha256`: `52df5c4c14a55fb8252df2233c09d7d373009b6aede733e658f4ffab934f49cf`
- `root`: `/home/pi/phase11-5-r3-v2-parallel-b-deploy-bd0-20260913`
- `stager_sha256`: `03d3f3d5073d49c71fb84da5f4333037c2047c88e443756892fe6a60546b3af3`
- `runner_sha256`: `80293892b285295f72e3bdbea4fc827aa7c83498b1cdb3298fa622a4ffa763ed`
- `image_sha256`: `b36f8d524cb0659107e82a41a3f8d15973fda80b843ef6909fe1a448b6ff3c6b`
