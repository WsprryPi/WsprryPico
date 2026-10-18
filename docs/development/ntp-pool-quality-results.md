# NTP pool quality and extended history: paused

This record describes the earlier pause. The subsequently authorized
[compact-status and bounded-USB follow-up](ntp-pool-usb-results.md) resolves
that resource boundary and records its separate B run. The restoration below
is the state at this earlier pause, not the latest installed image.

The 2026-10-17 follow-up implements pool quality selection and up to two hours
of original NTP history in the working tree. It is **not accepted or deployed**
after the test pause. The [evidence manifest](ntp-pool-quality-evidence.json)
binds the candidate normal image, checks, short live run and restoration.
The earlier [NTP results](ntp-work-results.md) and its live manifest remain
separate historical evidence.

## Implemented scope

Only configured `pool.ntp.org` enables four independently bound associations:
the configured root and `0`, `1`, `2.pool.ntp.org`. Other names and literals
retain single-peer behavior. Ranking uses the worst original uncertainty of
the last two admitted samples. A healthy source changes only for at least
25 percent improvement supported by two candidate observations, with a
30-minute hold after selection. Loss permits a fresh alternate sooner.
Scouting sends six initial requests at least 64 seconds apart, then at most
one per 15 minutes, with a strict twelve-send rolling two-hour ceiling.
Ordinary selected-source polling and bounded loss retries remain unchanged.

A fixed 32-record spread history expands toward two hours through time-only
compaction. It retains original observations without averaging, uncertainty
reduction or residual-based selection. A separate dense recent history
preserves the existing RF estimator. Every admitted arrival is checked for
epoch, monotonicity, gap and phase discontinuity before compaction.

The original sample, span, endpoint, uncertainty, disjoint-window stability,
held-out, source, age and arithmetic gates remain. Extended UTC qualification
also requires usable recent stability evidence and compatible centers.
The extended model describes a window-average rate. The RF consumer uses its
independently qualified dense recent estimate; a narrow extended UTC interval
cannot grant RF eligibility. Independent physical RF acceptance remains false.

Admitted active-source NTP phase updates UTC immediately. Probe replies train
only their own association and cannot change or invalidate global UTC. A fresh
probe is explicitly arbitrated before promotion. Qualified extended UTC rate
may apply before two hours; an unqualified estimate supplies no correction.
No learning writes settings or changes a running waveform.

## Checks and interim benefit

The normal `WsprryPico` target built with the retained pinned SDK and Arm tools.
Focused NTP/replay/standalone checks and affected network, management,
consumer-radio, RF-worker/failure and time-local checks passed. Existing replay
coverage includes 235 exact mapping cases and 15 common-input traces. Added
checks cover compaction, original-sample integrity, early qualification,
late wander, probe authority, quality selection and the rolling scout budget.
Host helper configuration required full Xcode after the default Apple linker
failed; the successful target build used the corrected task-local environment.

An additional known-truth replay used unchanged 12 ms sample uncertainty,
64-second observations and probes 32 seconds later. Steady +/-10 ppm traces
first used a qualified rate at 4,992 seconds (83 minutes 12 seconds): matched
phase-only projection error was 320 microseconds; rate-adjusted error was zero
on those noiseless synthetic probes. With bounded jitter, first use was at
5,056 seconds; matched median error changed from 720 to 591.792 microseconds.
A late-wander trace briefly admitted a small window-average adjustment before
qualification was withdrawn. Interim adjustments therefore can help stable
clocks but do not guarantee improvement under changing rate or asymmetry.
These are software replay results, not measured absolute UTC or RF accuracy.

## Live test and UI conflict

Only B received the candidate normal image, `0.0.0-ntp-pool-r1`; A was never
claimed or flashed. B joined saved `Bohica`, accepted pool time and synchronized
UTC immediately. The read-only collector recorded six admitted observations
and zero rejected observations in 159.4 seconds: three active-source UTC
updates and three scouts. All retained full and compact fields matched
independently seen per-peer originals, without missing admitted IDs in these
short cohorts. Neither rate had enough history to qualify. No RF jobs ran.

The independent reviewer identified a conflict with routine UI status delivery.
Full 32+32 histories were included in every network/status response. B's saved
idle snapshot had 102,000 heap bytes available with only three records in each
history. A synthetic full-history response using the saved scalar widths and
production response shapes was 23,465 bytes; its radio envelope was 23,499.
The unchanged radio admission check needs
`2 * 23499 + 4096 + 32768 = 83862` free bytes **after retaining the body**.
Even optimistically subtracting only the body and terminator leaves 78,534
bytes, a 5,328-byte deficit before session and allocator overhead. This is a
reproduced resource-budget incompatibility. An actual full-history UI failure
was not exercised or observed.

The user required a pause on a UI conflict. The collector was stopped by a
process-bound signal; its raw prefix and stop receipt were preserved. Its
last status is not an automatic-firmware query stop. A later pre-restoration
read recorded eight queries/eight accepted and five UTC updates at 217.198
seconds uptime, still within the declared two-hour/128-query ceiling. The
experimental image was removed so autonomous history growth could not expose
the UI conflict during the pause. The two-hour target test, live source
promotion, live interim rate and full-history radio/resource tests remain
incomplete. The collector also needs stronger general provenance-gap,
endpoint-event, independent-model and stop-margin handling before reuse.

## Restored state and resume boundary

B is restored to the previous normal image `0.0.0-ntp-peer-retention-r1`,
boot `f4bfa0a0e3919af2783cb08cece1993d`, receiving `pool.ntp.org` and synchronized.
A remains on original boot `70810de1c28e94df31343e54c74b19f9`, receiving
`time.local` and synchronized. Supported management reads verified unchanged
saved configuration and `Bohica` settings on both. Both are inactive and
unowned with schedules disabled. Both B loads preserved the reserved 64 KiB
byte for byte. Services and the conducted RF path were unchanged; zero RF
starts occurred.

The proposed resume boundary keeps ordinary status compact, retaining named
model summaries, source identities and counters. Full originals belong behind
an explicit bounded engineering USB diagnostic, or small paged GET. Every
page must bind device, boot, firmware, endpoint, clock epoch and estimator
generation, rejecting mixed generations while preserving original values.
The existing UI memory reserve and all timing/calibration gates stay unchanged.
After that change, repeat host checks, load B, verify full-history normal-status
radio delivery and diagnostic reconstruction, then restart the finite test.
No further implementation is authorized across this pause until the user
resolves this UI boundary. No commit, staging, push or publication occurred.
