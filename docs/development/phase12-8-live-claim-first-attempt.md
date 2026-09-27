# P12.8 first Safari claim attempt and recovery candidate

Status: **PHYSICAL CLAIM FAILED; SOURCE REPAIR BUILT, NOT YET FLASHED OR
TARGET ACCEPTED** (2026-09-27). The installed image remains the earlier
RF-inhibited candidate. The repaired UF2 SHA-256 is
`ad8778ae3b7d05a7ebb506f5e624fe700f58d57e24e1cc1db043b570d0bd1d3e`.
This record does not close P12.8 or Phase 12.

## Observed attempt

The operator authorized the Safari claim and one prompted BOOTSEL press on
Candidate A, Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344`, full device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`. The installed UF2 SHA-256 was
`c7187c9b828a23260334657beeae61c30aa474d4d9c32cad550c9ab44d5a0dcb`;
the firmware reported build revision `35415c3f8dba-dirty`, 150 MHz system
clock and the `inhibited-standalone-simulator` engine. Before the attempt,
USB `INFO` and `STATUS` reported healthy network-only generation 1, inactive
output and boot ID `b195eb9d1da741db1c4af6b5911237e5`. The open AP
reported `claim_available=true` for that same source and generation.

The operator opened the Safari page, saw its BOOTSEL prompt and pressed the
button once. The page closed, and the phone could not reconnect to the Pico.
No station settings were submitted. A subsequent `wspr5` read found the
application USB interfaces still present but no Pico AP advertisement.
Candidate A reported a new boot ID `d49de7a0fd1faf0906e90ec498b525b6`,
`recovery_boot=true`, raw fault stage `14`, fault PC `0x2007f1d8` and fault
status `0x00020000`. The profile was still healthy network-only generation 1;
access remained healthy generation 1; `STATUS` was Empty with inactive output,
healthy storage and the inhibited engine. No consumer journal write or RF
output was observed.

## Diagnosis and roll-forward repair

The source-linked claim route repeatedly used a short runtime BOOTSEL sample
while waiting for a press. It could return from its flash-safe callback while
the physical button was still held, before the release edge. That is a
credible cause of the observed fault; the raw PC/status do not prove a unique
instruction-level cause. The earlier whole-gesture diagnostic had kept flash
execution excluded until the button was released, but this claim route had
not used that API.

The repair removes short BOOTSEL sampling from owner start, identification
and submit. After the complete start response is queued, the server waits for
its acknowledgement, with a 500 ms lost-acknowledgement fallback, then enters
one SRAM flash-safe whole-gesture capture. New AP connections are rejected
between reply queueing and capture so a status poll cannot delay entry into
the safe zone. The callback returns only after release or a failed prompt
window; the portable
claim slot accepts the captured valid press without expiring a release at the
window edge. Safari displays a preparation screen first and delays its press
prompt for two seconds so the Pico can enter the safe zone. No human must time
the hold. Wi-Fi-only bootstrap retains its separate older sampler and is not
qualified by this owner-path repair.

Browser tests and focused portable claim, commit, HTTP and static-page tests
pass. The RF-inhibited Pico 2 W cross-build links the whole-gesture callback
and reports no linked core-1 launcher/reader. Formatting, diff and changed
documentation links pass. These are source/build results; the repaired owner
route has not survived a target button press. The final target hash above
binds this candidate, not an installed image.

An adversarial pass found that waiting indefinitely for a TCP acknowledgement
could show Safari the delayed prompt before the Pico entered its safe zone.
The bounded lost-acknowledgement path closes that source gap. A second pass
checked early connection loss, full-reply queueing, competing status requests,
gesture validity and timeout, submit without resampling, and no generation
change on the failed device. No further actionable source defect was found.
The two-second Safari preparation delay and 500 ms device fallback are not a
physical guarantee under all AP or phone failures; the next target attempt
must verify the actual prompt and whole-gesture behavior before any credential
submission is credited.

## Next gate

Do not ask the operator to press BOOTSEL on the installed image again. The
recovery boot is left untouched pending a reviewed replacement image. A new
flash needs action-specific approval for Candidate A and the exact UF2 hash
under `AGENTS.md`. Re-read the exact USB identity and preserved profile,
flash and verify only Candidate A, leave the newer image installed, then
check AP recovery without a button. A later prompted Safari press/release and
generation-2 journal readback remain separate physical acceptance steps.
