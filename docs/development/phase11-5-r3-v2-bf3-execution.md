# BF3 B paged reply functional acceptance

Under the accepted parallel B scope, repeat the bounded zero-RF functional
sequence after independently verified BD2. This is a fresh packet following the
diagnosed BF2 contiguous-allocation defect, with unchanged acceptance thresholds.
B serial CDDBF8767C506C07, device 29f20b7342051ef947aa56cb9d4fab42,
source 8921a70081839f168edef5926e92445f251d8e1d. Retain the image and configuration.

600 seconds plus 150 cleanup; 34 requests, six authenticated TLS connections,
one accepted inactive 512-event/3600-second LOAD. No ARM, RF, flash, CONFIG save,
Wi-Fi cycle or A device access. Exercise maximum HTTP body/replay/conflict,
oversize header rejection, malformed JSON/recovery, USB framing boundaries,
maximum LOAD and its 512-adjustment response, then Loaded ABORT/RELEASE.
Require unchanged boot, authoritative Empty/inactive/unowned final state and
zero allocator failures. Preserve raw full writes/responses and independent audit.
On failure retain known output authority separately from admission failure;
do not retry automatically or infer inactivity from missing acknowledgments.

- packet_sha256: `482ddb19074aff4190ffd5b2e432109d3926a2cd1c6829e29631e82f46b9983c`
- archive_sha256: `57f31a59f8a17a5d68fde6d4dc51242c87bd640c40d3e37bf0317eb56cb9372d`
- root: `/home/pi/phase11-5-r3-v2-parallel-b-functional-bf3-20260913`
- stager_sha256: `d81262d706323cc75a1467a9f8b0d896598976acae063664f40b72bdf6ea6712`
- runner_sha256: `7f2d5f80f70db786315934b2963a38ff066139da0dbc8c415a38b6dc6586683d`
- boot_id: `6684b4b197d80cfa0ce83b3aaf205cb0`
