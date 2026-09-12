# R2 WSPR LOAD OOM: one-shot restoration

This packet reconciles the failed remaining-mode attempt, not an RF retry.
The failed packet SHA-256 is
`3bb5b7f640477062a9fc9e51866aaddd9c5d055e84f17ca7eb122304304e2a62`.
Its private root is `/home/pi/phase11-5-r2-modes-049cc92` on wspr5,
host boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`.

Pico A USB `0BF4B4AEC9FFB344`, WTP
`fd6127d11d6aca42a9905fa3fb1bf1d5`, now reports revision
`049cc929143b`, physical 138 MHz, recovery boot
`76e562d473a426c864d7cdb7bbee98f9`, fault stage 5, hash 3833354787,
PC/status zero. The hash matches the exact ELF's `Out of memory` panic.
The WSPR LOAD was not acknowledged; no WSPR ARM was sent. Fresh Console INFO
and WTP STATUS establish Empty, inactive, unowned, no job/terminal records.
Recovery deliberately leaves CYW43 uninitialized, hence an empty runtime MAC.
The saved station, schedule, watermark, hostname and control configuration match.

Run the separately recorded `scripts/phase11_5_r2_oom_recovery.py` once through
one new wspr5 supervisor with RuntimeMaxSec 450. It verifies frozen original
helpers, input hashes, both board inventories and exclusive endpoints. It writes
the disabled original CONFIG once (31 → 32 of 32 cumulative writes), records its
acknowledgement, repeats authoritative admission, sends guarded Console BOOTSEL,
and flashes only the original inhibited UF2 SHA-256
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`.
Original config SHA-256:
`2978a00337f174286085251ec12ea15d0e524652738e009af3eb64e3be4ca0bf`.
Verify original revision `802c91a7b86e-dirty`, empty/inactive/unowned state,
original configuration and unchanged Pico B
(`CDDBF8767C506C07`, baseline inhibited `dbf1d86f0885-dirty`).
Stop only the matching owned old restoration timer after successful restoration.
No RF jobs, new network fixture, GPSDO/radio settings or installed service changes.
Any changed boot, fault, output, ownership, unknown write or failed command stops
this helper without automatic retry. Preserve original failed logs and result;
write a separate recovery result.

Validation: dry run has no hardware access; the real preserved inventory passes
admission; twelve mutated identity/state cases fail. The source/packet binding
and operation accounting are checked before writes. Existing broad USB/flashing
and scoped restoration authority is retained; execution must record any additional
approval boundary imposed by automatic review.
