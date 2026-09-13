# R3 v2 BD1 demonstrated-defect B recovery

Authorized by the accepted parallel B plan's demonstrated-source-defect recovery
scope and R3-COMPLETE-20260913-v2. BF1 independently confirmed an allocation
panic; its frozen fault audit must match before any device endpoint opens.
The reviewed repair is source 48ef82c7dedfa5b073c486dd0620afde33f71ab6.

B only: CDDBF8767C506C07 / 29f20b7342051ef947aa56cb9d4fab42. Require current
recovery boot de3aa3fcb1e87d5db95985509cd10110, retained configuration and
fresh Empty/inactive/unowned status. One acknowledged BOOTSEL and one verified
serial-specific flash, 300 seconds execution plus 150 seconds final inventory.
Zero LOAD, ARM, RF, scheduling, Wi-Fi cycle, CONFIG save or A endpoint access.
Keep B's existing TLS identity and test configuration. Require new non-recovery
boot, 138 MHz/RAM/512 events/3600 seconds, valid guards and zero fault/allocation
failure telemetry after flash. Retain the repaired image.

Two scope/prerequisite unit tests pass. The actual deployment must pass its
independent raw audit and mutation checks before BF2 functional execution.
The repair's host checks and known limitations are recorded in the BF1 review.
No physical repair acceptance or R3 closure is claimed by staging or flashing.

- `packet_sha256`: `83b483a76b03466616ccb852d93555554ffa1d6839b5ed5cdef452c4b3e2a349`
- `archive_sha256`: `137dba95435fbe90692efc4467f4910220a2edd08aecb0356bf303c479cb0484`
- `root`: `/home/pi/phase11-5-r3-v2-parallel-b-deploy-bd1-20260913`
- `stager_sha256`: `91779f5c17fb2ca0ff6e40b768b53508364bb1dd383ef8cc1f979c8223f5af73`
- `runner_sha256`: `dbd8ca59268a68c9492d249708751ece561fa1c7f18f46574eb83df4c11f4d93`
- `image_sha256`: `10c3ae9445d5f508604ae732dda15eb00cd28fcf964167cd96f75e7f50fd9929`
