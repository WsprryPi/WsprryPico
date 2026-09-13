# R3 v2 BF2 repaired-image B functional acceptance

Covered by accepted parallel B work and demonstrated-defect recovery. The BD1
repair deployment and its independent audit are prerequisites. B only, source
48ef82c7dedfa5b073c486dd0620afde33f71ab6, boot f4f3670094e95d3d143e4d4b20aefc24.
Retain the image, existing TLS identity and saved configuration. Zero A access,
ARM, RF, schedules, flash, Wi-Fi cycle or CONFIG save.

Six authenticated HTTPS cases: full 32768-byte padded HELLO; exact replay;
changed-body request-id conflict; 32769 Content-Length headers-only rejection
with 400 invalid_http; malformed JSON; valid recovery. Thirteen USB exchanges:
HELLO, full 65536-byte STATUS, CRC-valid 65537-byte rejection plus same-connection
recovery, CLAIM, 513-event rejection and unchanged status, duration 3600 seconds
plus one nanosecond rejection and unchanged status, accepted 512-event/3600-second
inactive LOAD with 512 adjustments, Loaded STATUS, Loaded ABORT, RELEASE, STATUS.
Three five-request inventories make 34 total requests. Six TLS connections and
one accepted LOAD; execution at most 600 seconds plus 150 seconds final inventory.

Stop on the first failure and preserve raw evidence. The maximum LOAD is the
previously failing BF1 operation; it must now return its complete reply without
a reset, fault, allocation failure or lost authoritative state. Independent raw
wire audit and actual evidence mutations are required. Original BF0/BF1 results
and component passes remain unchanged. This does not replace A under-RF gates.

- `packet_sha256`: `e72a6130cf014515af75601b762c8df3cd93faa2d64440d22eef0f55137e17d5`
- `archive_sha256`: `51af90b364ed50b2dbfffa412851403d02ba7c97cddf640a6351d4d32ae7d6c2`
- `root`: `/home/pi/phase11-5-r3-v2-parallel-b-functional-bf2-20260913`
- `stager_sha256`: `91779f5c17fb2ca0ff6e40b768b53508364bb1dd383ef8cc1f979c8223f5af73`
- `runner_sha256`: `b39b8a48c4ceb4f094cee93f60edb19163449964083d75b55aad08a512c922fc`
- `boot_id`: `f4f3670094e95d3d143e4d4b20aefc24`
