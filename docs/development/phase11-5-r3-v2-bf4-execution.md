# BF4 B paged reply functional acceptance

Under the accepted parallel B scope, repeat the bounded zero-RF functional
sequence after independently verified BD2 and diagnosed BF3 connection failure. This is a fresh packet following the
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

BF3 reached no HTTP write or LOAD. Four bounded ICMP probes showed Ethernet
neighbor failure while wlan1 reached the correct B MAC and received both replies.
BF4 binds each socket to existing wlan1 / 192.168.1.117, retaining authenticated
B peer identity and all original thresholds. No route or interface configuration
is changed. Socket binding and failure cleanup tests pass. Record each actual
local and peer address for independent audit. No additional flash is involved.

- packet_sha256: `1ea8add9d2b07bf1306dc541a5e9bbc4e1c0717a4b6cdef3f977d1fd8727c04d`
- archive_sha256: `b0864bbd1777d8c87f6c1ce785811c20012f235da9d82093dd9722d64b64e1de`
- root: `/home/pi/phase11-5-r3-v2-parallel-b-functional-bf4-20260913`
- stager_sha256: `d81262d706323cc75a1467a9f8b0d896598976acae063664f40b72bdf6ea6712`
- runner_sha256: `2615e9b6e995aa489aa926bbb51e7f02857505aee9dc5877b48aed98c6b20010`
- boot_id: `6684b4b197d80cfa0ce83b3aaf205cb0`
