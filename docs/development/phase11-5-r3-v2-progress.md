# R3 v2 execution progress

R3 remains OPEN. The user accepted R3-COMPLETE-20260913-v2 on September 13,
including implementation, finite RF, recovery, review and commit/push. Exact
acceptance and counters are in phase11-5-r3-v2-campaign.json. Historical packet
approval text is retained as history; v2 is the current standing authority.

## D0 completed

The frozen D0 packet was staged and executed unchanged. One acknowledged
BOOTSEL and one verified diagnostic flash installed clean source 481da3c3ff17.
A complete 65,552-byte frame carrying a valid 65,536-byte STATUS payload was
written in seventeen bounded writes and answered within its five-second bound.
Final A boot 1271822b30097b5539961a7a2fe49302 is non-recovery, Empty, inactive and
unowned. B retained its boot, source, saved configuration and inactive authority.
There were no RF jobs, Wi-Fi cycles, CONFIG saves or diagnostic heap probes.
The installed wsprrypi service remains PID 1957 with its recorded executable hash.

Raw private archive: build/phase11-5-r3-allocation-d0/evidence.tar, SHA-256
f0ecb9cdd32377100a24d9970f9473a2a49026f349819d5965eceddbd3b5d3f2.
Independent auditor: scripts/audit_phase11_5_r3_d0.py. The intact archive passes;
nine altered/missing-write, image, authority, boot, flash, B, source and fault
variants are rejected, followed by another intact pass. This is fresh-boot
maximum-input evidence, not a C0 repair or final R3 acceptance.

## Allocation mechanism and source repair in progress

Both C0's exact historical ELF and D0's ELF were executed in a hardware-free ARM
model using task-local Unicorn 2.1.4 and pyelftools 0.33. Only serialized allocator
lock/unlock entry points are stubbed. Allocation, free, trim, page-size, sbrk and
initialized allocator data use the linked machine code. No SDK or toolchain was
changed. The model script is scripts/phase11_5_r3_allocator_model.py.

A synthetic history leaves four separated free blocks and a free top chunk.
The allocator returns NULL for 65,552 bytes even though the top plus unextended
heap can satisfy it: this newlib requests a fresh 69,632-byte extension without
subtracting the old top. The extension exceeds the unextended heap. Returning
unused top pages with the linked _malloc_trim_r makes the same request succeed.
C0's recorded arena/top/unextended values are compatible with this mechanism;
its exact failed allocation and full host write remain historically unproven.
The synthetic history is not misrepresented as a replay of C0's exact history.

The source repair introduces a movable, fallibly allocated frame input buffer.
Large target input requests first return unused top pages, then use the nullable
newlib entry point. An unrecoverable NULL closes the input without dispatching
an operation or entering the SDK panic wrapper. Completed frames transfer their
storage to decoding. Fixed waveform buffers, transport limits and reserve gates
are unchanged. Trim attempts/releases are exposed separately in INFO.

Current checks: 41 hardware-free CTest groups passed after the storage-release
adjustment and extended-message/API implementation. Both provisional images
linked after the heap checker was updated to recognize only the new serialized
trim caller; seven checker tests pass, including rejected foreign callers.
The D0 evidence audit and nine mutation cases passed. Physical remediation and
all final-image acceptance remain outstanding. The immutable
phase11-5-r3-v2-validation-001.json checkpoint retains the software results,
logs and binary identities. Later changes require assertion-level impact review,
not resetting all validation to zero.

## Next work

Checkpoint v2-002 adds 62 passing host groups, Pi compiler/production runtime and
virtual-hour lifecycle checks, and eight reviewed local Chromium captures. The
independent UI review found rounded duration and a missing numerical event
ceiling; both are repaired and its reassessment accepted the scoped UI changes.
Two confirmed harness mistakes are retained with their corrected passing runs.
Physical acceptance remains outstanding. The HTTP body/internal-envelope limit
distinction found in source review now has an exact 32,768/32,769-byte regression.

Complete final repair review, build identified final
images, then execute internally reviewed finite packets under accepted v2.
Do not ask for routine image, Wi-Fi or RF reapproval. Preserve unrelated Pi work
and all prior failures. Run all fourteen final applicable R3 groups and seven
extended-feature checks, affected R1/R2 checks, adversarial repair/reassessment,
then complete the requested non-force commit/push sequence in both repositories.
