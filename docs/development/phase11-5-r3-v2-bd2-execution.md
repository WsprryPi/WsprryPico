# BD2 paged reply repair deployment

Run under the accepted parallel B plan and demonstrated BF2 functional defect.
B serial CDDBF8767C506C07, device 29f20b7342051ef947aa56cb9d4fab42.
Replace source 48ef82c7dedf, boot f4f3670094e95d3d143e4d4b20aefc24,
with clean source 8921a70081839f168edef5926e92445f251d8e1d.
One serial-specific BOOTSEL and verified flash; 300 seconds plus 150 cleanup.
Zero LOAD, ARM, RF, CONFIG saves, Wi-Fi cycles or A device access.
Retain the new RF-capable image and existing B test configuration.

The independently verified BF2 audit must be unchanged and BF2's unit inactive.
Read B before deployment, require inactive/unowned authority and the recorded
prior boot/source, then verify the new source/boot, stack/heap guards and saved
configuration. No automatic retry. Preserve the new raw evidence for an
independent audit before the separate functional packet. Host tests and linked
image checks pass; this deployment itself earns no RF or maximum LOAD credit.

- packet_sha256: `b7eb16dd88ab2867d5189ea3a3c1c49a7b47ab4e25fc82fa862f20a1962444a1`
- archive_sha256: `5f61eccd74dbb190e04e5b234d6e9653266a4e4fe26e817d543d491b9256d976`
- root: `/home/pi/phase11-5-r3-v2-parallel-b-deploy-bd2-20260913`
- stager_sha256: `d81262d706323cc75a1467a9f8b0d896598976acae063664f40b72bdf6ea6712`
- runner_sha256: `0ab3c0aaa5b0995bf3e82e801e51684d3e7c82800c8dbcabae2485ce1a265138`
- image_sha256: `67c27f20da8212097d60cd6b58fbbb4e774286df728ed7ea3e2746b5c6a59f58`
