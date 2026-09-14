# E2 A paged reply repair admission

Proceed under accepted R3-COMPLETE-20260913-v2 and the instruction to retain
RF-capable images except when a demonstrated defect requires repair. BF1 proved
an allocation panic; BF2 proved the first safe repair could not return the maximum
LOAD. BF4 independently validates the paged repair on B, including all 19 cases
and the complete 512-adjustment response with zero allocation failures.

Deploy source 8921a70081839f168edef5926e92445f251d8e1d to A serial
0BF4B4AEC9FFB344, device fd6127d11d6aca42a9905fa3fb1bf1d5, replacing c5f00b6
boot a0badc7b54480767c3d3f907e0962dc7. One BOOTSEL and verified flash, 600 seconds
plus 150 cleanup. Zero RF/ARM, CONFIG saves, Wi-Fi cycles and heap probes.
Keep the test configuration and repaired image. B stays idle and read-only during
this short comparator gate; no concurrent B functional runner may remain active.

Require both boards inactive/unowned and the installed Pi service unchanged.
Run the existing seven idle admission assertions: full 65536-byte STATUS,
65537-byte rejection/recovery, 513-event and overduration rejection, maximum
512-event/3600-second LOAD, then Loaded ABORT/RELEASE. Verify new boot/source,
heap/stack guards, final inactive authority and saved configuration. Preserve raw
evidence and independently audit before any RF packet. No automatic retry.

Both identified targets pass linked checks. The 660-byte RF renderer remains at
0x200012d8 with unchanged bytes; 61 checked RAM functions match. Other runtime
functions contain relocated literals/veneers, and server static storage grows
560 bytes from c5f00b6. This is not whole-image equivalence: affected physical
contention/timing checks remain required; prior mode-hour evidence is preserved
with its original source and reuse assessment.

- packet_sha256: `37a6cd1d990e0c79cc8510a7e5b7fc81e3ac13316de76cabc65b4d2dfa7f7207`
- archive_sha256: `a98878dd99e8ba2417d8aa701134308ca2542cf85ad8617bb91259c3566c25ff`
- root: `/home/pi/phase11-5-r3-v2-idle-e2-20260913`
- stager_sha256: `d81262d706323cc75a1467a9f8b0d896598976acae063664f40b72bdf6ea6712`
- runner_sha256: `0958e73ae7389eb06cfd7ab9c20907412f9133f48296050701348bbbd9ebb195`
- image_sha256: `3899b498d05ca5b39e23a45e455c44b2784bcf2aca35f62a8ef4db644cc7241b`
- source_revision: `8921a70081839f168edef5926e92445f251d8e1d`
- b_functional_audit_sha256: `9741d81f3cfc9497c9f33f32ec3591ab6c398b427842c642b5b4a734483ca936`
