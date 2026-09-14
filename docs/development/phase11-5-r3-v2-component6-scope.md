# Component 6: retained-image LOAD continuation

The user's “Fix it” on 2026-09-14 authorizes completing the pending target
validation after Component 5's observer defect, followed by review, repairs,
reassessment, commit and push. The earlier failed attempt remains immutable.
This continuation uses the corrected observer and the already installed image.

The fixed one-hour period begins at the first host preflight, with 45 minutes
for work and 15 minutes reserved for cleanup. No flash, BOOTSEL, reset, ARM,
RF job, Pico configuration write or Pico Wi-Fi command is allowed. The sole
new stimulus is the exact C7 512-event LOAD, followed only on success by one
identical replay and one fresh-request-ID replay. There is no failed-test retry.
The temporary host fixture uses the existing retained credentials and bounded
cleanup service; permanent host state and the installed WsprryPi application
must be preserved. Pico B receives read-only inventories only.

Fresh preflight found Pico A on `e256633304e03ab85998fde947360ccbaab6c68e`,
UF2 SHA-256 `b2983da197de0462f3ef4288355dc4b5ce5fe349b0b98d526dce0d6e526a9288`,
boot `11dac3985326cb81c49022efcdceb5d4`, USB serial `0BF4B4AEC9FFB344`,
device `fd6127d11d6aca42a9905fa3fb1bf1d5`. This is Pico 2 W / RP2350 Arm,
138 MHz GP2 PIO/DMA with RAM rendering and scheduling disabled. The physical
setup is unchanged. The same E6 Aborted terminal record remains present.

Reuse Component 5's successfully prepared E6 record instead of submitting another
preparation job. Its complete prior evidence is included under `prior/` and
bound into the new packet's file hashes. Admission requires the same host boot,
A/B boots, firmware revisions, saved configurations and terminal record. The
prior run has ended more than 310 seconds before the continuation, and a fresh
STATUS must still show exactly that record with Empty/inactive/unowned state.
Do not recreate the baseline silently if these conditions differ.

The primary remains byte-identical: 52,105 framed bytes, SHA-256
`e5b48b92dd2abd74e670f2b2aed3d660c9b357bd4857be6b64b8affedbcee670`.
Require complete writes and a successful 54,916-byte response with all 512
expected adjustments within five seconds total. Require matching replay replies,
then authoritative Loaded/inactive/owned STATUS, ABORT and RELEASE.

Use one persistent mutually authenticated TLS 1.3 WTP observer at five-second
STATUS intervals, four ordinary HTTPS status GETs at least 20 seconds apart,
and single-flight INFO near 1 Hz. Wait for the first healthy INFO before the
30-second prelude. Observe at least 30 seconds after the primary reply. Maintain
the existing heap reserve and stack limits. Compare actual TLS allocation near
LOAD with 31,384 bytes; retain pressure/cadence limitations instead of changing
the workload or granting unsupported credit.

The continuation's packet is
`f1af8394bf5854bdc85b856c1016ba48f69e4c702613d5917c4875ebab4373da`;
private evidence root is `/home/pi/phase11-5-r3-v2-load-reply-c9-20260914`.
No new firmware is built. `admit` cannot flash and the deployment entry point
rejects this scope. The observer now records INFO before checking health and
requires a healthy first sample before starting the observation interval.

Audit raw framing, CRC, schema, request/reply identity, write accounting,
operation counts, retained-state lineage, healthy observations, TLS/HTTPS
records, cleanup and independent final A/B inventories. Exercise altered-evidence
cases offline and fix findings before publication. Only this bounded idle LOAD
regression can close; broader Group 2/RF acceptance remains separate.

## Prerequisite correction within the same period

The first C9 fixture admission ended before any primary/replay LOAD: the TLS
socket reported `No route to host` while Pico A was still reconnecting. Both
boards and the host fixture were restored. This was a connection prerequisite
failure, not an offered LOAD or replay. Its complete failed trace remains under
`c9-evidence` and is included as `prerequisite/` in the corrected packet.

The corrected readiness gate reads Console INFO at two-second intervals, at most
90 seconds, and requires two consecutive healthy samples with link status 3,
address 10.77.15.10 and the control listener active before starting TLS. Its
regression includes a ready/not-ready transition, requiring consecutive samples.
The packet `9dd56b7e1780929819affe3dea024972b446f11c327ef8633ef3f397e11e8e01`
uses root `/home/pi/phase11-5-r3-v2-load-reply-c9a-20260914`. It preserves the
original C9 start and both deadlines. The aggregate primary limit remains one,
with two conditional replays; no second firmware or preparation LOAD is used.
