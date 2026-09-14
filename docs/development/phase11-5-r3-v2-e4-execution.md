# E4: retain the repaired static-page image and verify idle boundaries

Execution under accepted R3-COMPLETE-20260913-v2; no additional approval is
required. B6 independently recorded GET / returning HTTP 503 resource_exhausted
before any controller operation or RF. Preserve that original zero-RF failure.
Source a740dbb8e7319beb20c4807b35f6672bf9fdfd27 replaces the obsolete triple-copy
static-page admission with the actual body plus 4096 bytes and fallible 4096-byte
output pages. The independent 32768-byte reserve remains unchanged. Allocation
failure publishes no partial page. All 62 host groups and both image checks
pass; the original implementation fails the new regression.

Deploy only the standalone RF image and retain it. Both images were built from
a clean detached checkout with existing SDK 2.3.1 and credentials. The RF static
layout is unchanged; 70 RAM functions match exactly and 27 differ, so whole-image
equivalence is not claimed. RF renderer source, encoders and job authority did
not change. Applicable earlier assertions remain preserved, with physical
source-impact mapping required before final closure.

A: serial 0BF4B4AEC9FFB344, device fd6127d11d6aca42a9905fa3fb1bf1d5;
prior source f5502cff9fa6b56747b2e1b1036a77fc0e270f6f and boot
2d34c532eb46a11a6b2cede5eae8f796. Read B only: serial CDDBF8767C506C07,
source 8921a7008183, boot 6684b4b197d80cfa0ce83b3aaf205cb0. Protect installed
Pi service PID 1957 and its recorded executable identity. Require the B6 audit
6843df6faa4d9eb3067c4bf504d0cf516075cf51e9609a6f8f629f7d6829bac8
and inactive supervisor, followed by fresh in-run A/B inventory before BOOTSEL.

The 600-second runner plus 150-second restoration allowance permits exactly
one acknowledged BOOTSEL and one serial-specific verified flash/start. Check
seven idle assertions: image identity, complete 65536-byte STATUS, 65537-byte
rejection/recovery, 513-event rejection, 3600-second-plus-one-nanosecond rejection,
512-event/3600-second inactive LOAD with adjustment replies, and ABORT/RELEASE.
Final A must be Empty/inactive/unowned. B and saved test configuration remain
unchanged. Zero ARM/RF, CONFIG saves, Wi-Fi cycles, heap probes or extra reboots.
Keep schedules disabled and unchanged 60 dB wiring. Preserve the deliberately
aborted Loaded record separately from completed RF jobs.

F1's original cleanup deadline is 306202695885000 host monotonic ns; require
750 seconds plus reserve before it and never extend it. Stop on failed admission,
retain raw evidence and independently audit before the next RF packet. This
fresh packet may run once; a stopped attempt is never silently replayed.

- packet_sha256: 4f2f3680f88021adfc14b32930eaea575cbbe291045bce3c5f3daa02807d2783
- archive_sha256: 4f3d690a86961da5365f652eda6ba55015d1c95e1d6381a40e14258235d53f37
- root: /home/pi/phase11-5-r3-v2-idle-e4-20260914
- stager_sha256: 73e972b3310f571d5ceb57019dfc49256f51d7643b47092ea757e7efedb5def0
- runner_sha256: 0958e73ae7389eb06cfd7ab9c20907412f9133f48296050701348bbbd9ebb195
- image_sha256: 454e03e5165143463d6b5f965ea8f1f3704138f08bfc7057704e3fef8f10ebe4
- source_revision: a740dbb8e7319beb20c4807b35f6672bf9fdfd27
- b_functional_audit_sha256: 9741d81f3cfc9497c9f33f32ec3591ab6c398b427842c642b5b4a734483ca936
