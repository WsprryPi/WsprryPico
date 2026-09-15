# Component 7: authorized Wi-Fi recovery and repaired LOAD validation

On 2026-09-15 the user authorized the proposed single Pico A Wi-Fi OFF/ON cycle,
one replacement preparation LOAD if the retained record had expired, and the
pending primary/replay checks. The user also reported that an unrelated external
router reset occurred. Record that environment context without relabeling the
earlier unperformed LOAD checks as passes. The prior review/repair/reassessment,
commit and push request remains part of this work.

Use the unchanged installed `e256633304e03ab85998fde947360ccbaab6c68e` firmware:
Pico A serial `0BF4B4AEC9FFB344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`,
boot `11dac3985326cb81c49022efcdceb5d4`, Pico 2 W / RP2350 Arm, GP2 PIO/DMA,
138 MHz and RAM rendering. UF2 SHA-256 is
`b2983da197de0462f3ef4288355dc4b5ce5fe349b0b98d526dce0d6e526a9288`.
Pico B is read-only. Preserve configuration, physical RF setup and installed
host application. No flash, BOOTSEL, reboot, ARM, RF output or CONFIG write.

The new period is one hour from the first host preflight, with the final
15 minutes reserved for cleanup. Do not restart either deadline. The fixed
packet permits one Wi-Fi cycle, one primary LOAD and two conditional replays.
Fresh preflight verified the same A boot and an empty terminal-record list, so
exactly one E6 replacement preparation is selected. Original evidence remains
under `prior/`, bound by hashes; expired records are not treated as retained.

Establish the existing temporary host fixture with retained credentials and its
independently armed cleanup service. Require exact read-only A/B admission.
With A Empty/inactive/unowned and scheduling disabled, record one `WIFI OFF`
and one `WIFI ON` command, raw replies and actual state. Charge each command
before sending. Attempt ON in a finally path even if OFF's acknowledgment is
lost. Require final network enablement; do not issue extra recovery cycles.

Prepare the exact 512-event E6 job, verify its complete successful reply, then
ABORT/RELEASE. Wait at least 310 seconds for request-cache aging. Verify exactly
its Aborted terminal record and Empty/inactive/unowned state. Require two
consecutive healthy INFO samples showing address 10.77.15.10, link status 3 and
the control listener before starting the bounded network observer.

Send the exact C7 primary frame once: 52,105 bytes, SHA-256
`e5b48b92dd2abd74e670f2b2aed3d660c9b357bd4857be6b64b8affedbcee670`.
Require all writes and a complete 54,916-byte successful response containing
512 expected adjustments within five seconds total. Only then send one
byte-identical replay and one same-job LOAD with its frozen fresh request ID.
Require matching replies, Loaded/inactive ownership, then ABORT/RELEASE.
No failed primary or replay is retried.

One persistent authenticated TLS 1.3 WTP observer reads STATUS at five-second
intervals. A separate worker offers four HTTPS status GETs at least 20 seconds
apart. INFO is single-flight near 1 Hz, starting at least 30 seconds before the
primary and continuing at least 30 seconds afterward. Keep heap/stack reserves
unchanged. Measure TLS allocation around LOAD against the historical 31,384-byte
cost; do not add workload or relax thresholds to manufacture comparability.

The packet SHA-256 is
`056e4e3188c2b4f906eb6e8e1a70482e167ce84a7ba7823e791edc3514425e10`.
Private root: `/home/pi/phase11-5-r3-v2-load-reply-c10-20260915`.
The runner has 1,200-second supervision and a 600-second cleanup bound, both
inside the original hour. Stop dependent workload on the first unexpected
failure, preserve raw evidence and reconcile authoritative final state.

Independently audit raw framing/CRC/schema, actual write counts, deadlines,
retained-state preparation, Wi-Fi command counts, replies and observations.
Review adversarially, fix offline findings and reassess. Verify A/B and host
restoration independently. Publish only summaries/hashes, with no credentials,
raw captures or generated firmware. Close only the exact demonstrated idle
LOAD-reply regression; broader Group 2/RF acceptance remains separate.
