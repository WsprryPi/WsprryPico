# BF2 fragmented reply repair

BF2 on B, source `48ef82c7dedfa5b073c486dd0620afde33f71ab6`, preserved
its boot and inactive Loaded job when the nullable contiguous LOAD reply
allocation failed. It did not complete the required maximum LOAD response.
Checkpoint 019 preserves both the successful panic protection and the failed
functional assertion; checkpoint 018 preserves the preceding deployment.

The replacement stores large WTP and browser replies in at most sixteen
4096-byte pages. All pages are allocated before output begins, partial failure
releases them, and transport sends each page incrementally. The browser envelope
is encoded directly. WTP CRC is accumulated over the pages without changing the
wire representation. Total size and existing memory admission limits remain.
The reply still fails safely if the required pages cannot be allocated.

Adversarial assessment checked allocation failure after several successful pages,
page-boundary output consumed seven bytes at a time, exact comparison with the
existing WTP serializer, browser JSON structure, moved buffer ownership, total
length/CRC, and target header/body offset handling. A simulated allocator that
rejects every request larger than 4096 bytes completes both maximum replies.
All 62 host CTest groups pass. The actual serializer fixture was rebuilt and its
unchanged wire bytes verified before updating source provenance. Checkpoint 020
freezes the tested source and logs.

The B runner now retains authoritative inactive Loaded status when that status
fails the stricter Empty-state admission requirement. A changed boot or admission
failure remains a stopped test requiring diagnosis; missing or inconsistent
output authority remains unverified. Original BF2 output is immutable.

No actionable issue remains in this source assessment. Target heap/stack image
checks and a fresh B functional sequence are required before accepting this
repair physically. No A image change has occurred. Broader resource saturation,
reclamation, and affected final-image R3 acceptance remain open. No general
claim that every firmware allocation failure is now safe is made.
