# Phase 11.6 conducted RF acceptance plan

Status: **OPEN — physical execution is paused at the corrected-candidate
authorization gate after preserved attempt 41 and one rejected deployment
build.** This phase is per-band/per-mode operational
acceptance for the configuration closed by Phase 11.5. It is not the Phase 13
band x mode x clock, filter, harmonic, calibrated-power or release campaign.

The reproducible packet generator is `scripts/phase11_6.py`; the initial public
matrix is [`phase11-6-matrix.json`](phase11-6-matrix.json). The canonical plan
successor SHA-256 is
`9324f6057ae8f4e552375919836bbe4e0c30176405eedaf3915f0ab67d929556`.
The immutable predecessor plan SHA-256 is
`ea512b70a786c46fbe15f769b327139d69ad3b0cae984b3622d79f145a076c53`.
The expanded private packet is intentionally generated from maintained source
rather than committing 1.6 MB of repeated WSPR and keyed events.

## Source and accepted configuration

Both clean `devel` heads were fetched and equal their upstream branches before
planning:

- WsprryPico `f34a606391bca048af902e120d214462dd5f55b3`.
- WsprryPi `21ae75ab9e38bd6237b1ae73f3e7ab8527324067`.

The installed firmware identity remains distinct from repository HEAD. The DUT
is Pico A serial `0BF4B4AEC9FFB344`, WTP device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, source
`91933c00970939e366d1bfcf3c1956b59be8f6c5`, UF2 SHA-256
`5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446`
and original Phase 11.5 accepted boot
`ff719d304f1ba4ac23fddd93561b26f0`. The configuration is
Pico 2 W / RP2350 Arm, 138 MHz system/sample clock, PIO divider 1,
`pio-dma-gp2`, GP2 and RAM rendering with the network listener configured.

Fresh zero-RF USB inventory on 2026-09-18 reconfirmed that exact A identity and
boot. Pico B serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`, source `8921a7008183` and boot
`6684b4b197d80cfa0ce83b3aaf205cb0` was independently empty, inactive and
unowned. The previous shared reservation was `RELEASED`. A's retained test
network was disconnected after restoration, so its clock was unsynchronized;
this blocked ARM until the accepted fixture restored `time.local`, but was not
a firmware regression.

After attempt 31, the production-browser startup collision was repaired but
had latched 16 allocator failures and eight TLS allocation failures. The
operator authorized one authenticated same-origin restart on 2026-09-18. The
accepted successor boot is `d2f657c2099c67a7af2ef390426bda10`; fresh
post-restart inventory retained the exact device, source, UF2, 138 MHz clock,
divider, engine, RAM renderer and GP2 output configuration, with zero allocator
and TLS allocation failures, no fault/DMA errors, empty state, no owner and
inactive output. No flash or configuration write occurred.

This boot-only amendment did not change RF content. Canonical comparison of
the two plans gives the same packet SHA-256
`e0ab3cd4a039a88786bc677a7fc66be1c7dca1e30877859ccc71dd8bba547893`
and flattened-job SHA-256
`35ad0d4165171c158a4e99f92128be8052a86eec79e5cccd6930c19b8e09b88b`.
Attempts 1-31 therefore remain bound to the predecessor plan and later attempts
are bound to the successor without recasting earlier evidence.

The initial campaign changes were host planning, capture, analysis, audit and
documentation only. Attempt 41 then confirmed that a normal armed-interval
clock refinement is rejected by the accepted image's immutable local timer
projection. The [clock-refinement repair preparation](phase11-6-clock-refinement-repair.md)
preserves that failed attempt and accounting, identifies affected Phase 11.5
assertions and records the source-only repair. No repaired firmware has been
deployed; Phase 11.5 evidence remains bound to its recorded image and transfers
only through the documented source-impact decision and required candidate
checks.

One authorized repair flash subsequently installed clean source `2eaa99945d21`
but was rejected before acceptance because its build omitted the accepted
135,500 Hz standalone-base override and reported the generic 3,570,100 Hz
default. The device remained inactive, no RF or CONFIG write occurred, and the
held reservation was released only after fresh A/B reconciliation. A corrected
135,500 Hz UF2 is built and privately staged but not deployed; its exact record
and the fresh-authorization boundary are in the
[deployment attempt result](phase11-6-clock-refinement-deployment-attempt1.json).

## Frozen content and frequency convention

The supported direct-synthesis points are 2200 m through 6 m from the requested
matrix. At 138 MHz/divider 1, 4 m and 2 m exceed the 68,999,999 Hz direct range;
all ten of those rows are `UNSUPPORTED_CONFIGURATION` and receive no ARM or RF
attempt.

The keyed message is `ET E`. It deliberately includes a dot, dash, character
gap and word gap while keeping the campaign bounded. QRSS3 uses 3 s dots, 9 s
dashes, 3 s intra-element gaps, 9 s character gaps and 21 s word gaps. FSKCW
uses the listed nominal frequency as its low space and nominal +5 Hz as its high
mark. This accepted image uses a **reverse DFCW profile**, high dot and low
dash; conventional DFCW is dot low and dash high. The label is explicit so the
matrix does not imply that the retained image defines the external convention.
QRSS and DFCW gaps are silent; FSKCW gaps remain on the low state. Each
compact job includes the implemented 1 microsecond final-off event.

WSPR freezes `AA0NT EM18 20`; the power field is encoded content, not measured
power. The listed nominal is the WSPR RF center. Its four production-compatible
tones are nominal -2.197265625, -0.732421875, +0.732421875 and +2.197265625 Hz,
with 162 canonical 682,666,666 ns symbol cells. A separate 32-character QRSS case on 20 m uses
`E T ` repeated eight times, including its trailing counted space, to retain
word-space and boundary evidence without duplicating an hour on every band.

## Assertions and numeric tolerances

These operational tolerances were frozen before physical results:

- requested versus receiver-indicated frequency: within 100 Hz, explicitly
  uncalibrated for absolute frequency;
- WSPR adjacent-tone spacing: within 0.05 Hz of 1.46484375 Hz; per-symbol
  residual no greater than 0.1 Hz; three complete independently decoded frames
  in consecutive nominal two-minute slots;
- keyed state separation: within 0.2 Hz of 5 Hz, with correct FSKCW and DFCW
  polarity;
- Tone duration: within 0.02 s; keyed edges and gaps: within 0.05 s at 1 ms
  analysis resolution;
- signal contrast: at least 10 dB without clipping or overload;
- at least 1 s of leading and trailing quiet, no extra burst, hidden dropout,
  unwanted tail or carrier in commanded-off intervals.

Each row reports decoding/readability, frequency/spacing and envelope timing,
network/lifecycle behavior, capture validity and diagnostic in-band spectrum
separately. A decode alone cannot pass a row. Spectrum observations are
diagnostic only and make no harmonic, calibrated-power or regulatory claim.

## Packet schedule and accounting

Each supported band has one ordinary immutable packet with the 13 primary
jobs. The 20 m packet also contains the single 32-character semantics case.
Thus ordinary packets contain 13 jobs, or 14 on 20 m, and charge 723.776009
seconds, or 1,134.776010 seconds on 20 m. Tone is a documented production-
interface gap: the Pi maintenance operation is start/stop controlled rather
than a bounded scheduled production mode, so the finite laboratory controller
supplies that row.

Primary path allocation is:

- Tone: direct network controller, deliberate transport disconnect after ARM;
- WSPR: production WsprryPi, browser raw-job owner, then direct controller
  disconnect, in consecutive slots;
- QRSS/FSKCW/DFCW: production WsprryPi, browser `LOAD_MESSAGE`, then direct
  controller disconnect.

Every job includes actual browser page load/manual refresh interaction while
Armed or Running. Each non-Tone row therefore receives production operation;
all rows receive real page lifecycle coverage and one completion after control-
transport loss. Direct
disconnect closes transport only; it never removes Pico USB power.

Three integration packets at 2200 m, 20 m and 6 m add nine jobs. They cover all
five modes, production/browser/controller ownership, owner abort,
foreign-principal rejection and physical Console ABORT, with IQ retained through
cessation and trailing quiet.

The complete frozen plan is 179 jobs and 10,248.68011968 planned RF seconds. The
estimated CF32 volume, including four seconds of per-job capture allowance, is
21,929,360,239 bytes. This is below the campaign ceilings of 300 jobs and 18,000
seconds. Every ordinary packet is below 16 jobs and 1,800 seconds. Accepted,
rejected, aborted, uncertain and completed submissions are charged separately;
any possibly accepted submission reserves its full planned duration. No blind
retry or threshold change is permitted.

## Fixture, receiver and safety boundary

Use the accepted two-host topology: wspr4 USB `wlan1`
`e8:4e:06:ac:f3:87` as the channel-11 AP, and wspr5 USB `wlan2`
`e8:4e:06:ae:d7:09` as the isolated client/time broker. Preserve wspr4 `wlan0`
management and wspr5 `eth0`/`wlan1` management. Reinventory boots, interfaces,
routes, service and executable hashes at setup and restoration. Keep recovery
timers enabled except for the bounded fixture interval and arm cleanup before
network changes.

The operator-confirmed path is Pico A GP2 through its existing 60 dB attenuated
branch into the common SDR combiner, with no antenna and no external filter.
Do not operate the GPSDO or wspr5 GPIO RF branches. Preserve the path, drive and
zero correction setting. Contradictory evidence stops RF.

The receiver is the freshly inventoried SDRplay RSP1B serial `2404058C60`, CF32
at 250 ksample/s, 200 kHz bandwidth, 20 dB gain, AGC and bias tee off, zero
receiver correction and center 25 kHz below nominal. Run a receiver-only
readiness capture before the first job and after any relevant retune. Every
capture binds settings, sample count, helper/driver identity, overflow, clipping
and cleanup. Raw IQ and authenticated material remain in a mode-0700 private
root outside Git.

Before reservation/ARM, both boards must be freshly authoritative, schedules
disabled, B unowned/inactive, A exact-image and healthy, SDR and independent
USB observers ready, and all other combiner sources inactive. Unknown output
holds the shared reservation and blocks both boards. Release requires fresh
inactive/unarmed/unowned proof and disabled schedules on both boards.

## Audit and closure

The independent audit must not trust runner PASS labels. It rehashes the packet
and evidence inventory, checks exact board/image/boot/clock/receiver identities,
reconciles LOAD adjustments and actual jobs, reruns IQ analysis, validates page
overlap and disconnect/abort evidence, enforces RF accounting, and requires
terminal records plus fresh output-inactive authority. Synthetic mutations must
reject wrong identity/band/message, truncated capture, polarity reversal,
missing/extra elements, missing quiet, false page overlap, duplicate submission,
premature reservation release and changed thresholds.

Rows use only `PASS`, `FAIL`, `BLOCKED`, `NOT TESTED` or
`UNSUPPORTED_CONFIGURATION`. Phase 11.6 closes only when every mandatory
supported row and integration assertion passes, or an explicit later scope
revision disposes of a failure. Failed attempts remain immutable.
