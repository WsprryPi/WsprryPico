# Phase 11.6 conducted RF acceptance plan

Status: **OPEN — further RF is blocked after attempt 52.** The corrected timing
candidate remains installed, but the 80 m TONE controller-disconnect job ended
in a preserved inactive `DEVICE_FAULT` after its zero-tail hardware stop. The
shared reservation remains held and Pico A remains in failed/inactive state;
no retry or boot-changing recovery has been performed. A narrow source repair
and discriminating hardware-free regression are prepared but not deployed.
See the [attempt 52 checkpoint](phase11-6-80m-attempt52.json).

Before that stop, attempts 42, 43 and 45
are preserved as zero-RF harness/orchestration failures, and attempt 44 passed
the armed clock-refinement corrective gate. The three 160 m QRSS paths and the
three reverse-profile DFCW paths now pass their individual physical and IQ
checks. Attempt 48 retains an unrelaxed 160 m FSKCW production-path coherence
failure; its other two paths were not spent. Remaining matrix paths, packet
audits and bands are pending.** This phase is per-band/per-mode operational
acceptance for the configuration closed by Phase 11.5. It is not the Phase 13
band x mode x clock, filter, harmonic, calibrated-power or release campaign.

Attempt 52 launched its immutable 80 m UTC request after an accepted clock
refinement; this was not a stale-target or uncertainty rejection. The final
data IRQ established a zero-tail chain with 936 of 1,156 predecessor words
remaining, the tail IRQ count advanced, PIO output was inactive, DMA errors and
invalid/unpaired refill counts remained zero, and the 2,168,000 ns maximum
service gap stayed below the frozen 2,849,391 ns gate. The failure is the sink's
software completion rule: it waits for tail IRQ service even though the chained
hardware stop has already executed. The prepared repair recognizes that
authoritative inactive hardware state after the final-data IRQ. It changes no
sample, frequency, tail length, 100 microsecond acknowledgement bound or frozen
service-gap limit. The original sink fails the new regression and the repaired
sink passes it. Because this is an RF lifecycle firmware change, affected 11.5
checks and the affected 11.6 row still require exact-candidate physical
requalification after separately authorized recovery/deployment.

The reproducible packet generator is `scripts/phase11_6.py`; the initial public
matrix is [`phase11-6-matrix.json`](phase11-6-matrix.json). The canonical plan
successor SHA-256 is
`8a52e4d9b3f252097bca0112c08b3b1e41792905775624940bcbf313b5cb072b`.
The immutable predecessor plan SHA-256 is
`9324f6057ae8f4e552375919836bbe4e0c30176405eedaf3915f0ab67d929556`.
The expanded private packet is intentionally generated from maintained source
rather than committing 1.6 MB of repeated WSPR and keyed events.

## Source and accepted configuration

The repair and its companion production-client support were committed and
verified at their upstream `devel` branches before the corrected build:

- WsprryPico repair `2eaa99945d21501cd4dbdac98c25be5fa146e479`;
  planning/deployment record baseline
  `8d84dbe567cdb4e3814281c4792c6d544ee2b711`.
- WsprryPi `3b046ebe3eaa19ae764706d844fa7354033c32df`.

The installed candidate remains distinct from repository HEAD. The DUT is Pico
A serial `0BF4B4AEC9FFB344`, WTP device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, repaired source
`2eaa99945d21501cd4dbdac98c25be5fa146e479`, UF2 SHA-256
`af3f6917ba807a1526dca6e15f19fff1974410fc87ecc32fd6e9c4f07059525f`
and boot `b72fed2c17583cc7aba0f1345f76a3b2`. The original Phase 11.5
accepted boot remains `ff719d304f1ba4ac23fddd93561b26f0`; the last
pre-repair campaign boot was `d2f657c2099c67a7af2ef390426bda10`. The candidate configuration is
Pico 2 W / RP2350 Arm, 138 MHz system/sample clock, PIO divider 1,
`pio-dma-gp2`, GP2 and RAM rendering with the network listener configured.

Fresh zero-RF USB inventory after deployment confirmed the exact A identity,
135,500 Hz retained standalone base, valid stack guards, at least 32,768 bytes
of heap reserve, zero allocator/TLS/DMA/fault counters, empty state, no owner,
inactive output and disabled schedules. Authenticated hostname/TLS WTP `HELLO`,
`CAPS`, `STATUS`, `GET_CLOCK` and `PING` then passed without a mutation. Pico B serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`, source `8921a7008183` and boot
`6684b4b197d80cfa0ce83b3aaf205cb0` was independently empty, inactive and
unowned. The shared reservation is `RELEASED`; the WsprryPi service is inactive.

The initial campaign changes were host planning, capture, analysis, audit and
documentation only. Attempt 41 then confirmed that a normal armed-interval
clock refinement is rejected by the accepted image's immutable local timer
projection. The [clock-refinement repair preparation](phase11-6-clock-refinement-repair.md)
preserves that failed attempt and accounting, identifies affected Phase 11.5
assertions and records the repair and both deployment attempts. Historical
evidence remains bound to its recorded images. R1.1/R1.5, the shared R2 launch
path and the R6 timing/resource gates transfer to the repaired candidate only
after an observed armed-interval refinement completes the bounded corrective
job without `MISSED_START`.

One authorized repair flash subsequently installed clean source `2eaa99945d21`
but was rejected before acceptance because its build omitted the accepted
135,500 Hz standalone-base override and reported the generic 3,570,100 Hz
default. The device remained inactive, no RF or CONFIG write occurred, and the
held reservation was released only after fresh A/B reconciliation. A corrected
135,500 Hz UF2 is built and privately staged but not deployed; its exact record
and the fresh-authorization boundary are in the
[deployment attempt result](phase11-6-clock-refinement-deployment-attempt1.json).

A separately authorized serial-bound flash then installed the corrected
135,500 Hz image once. It produced boot
`b72fed2c17583cc7aba0f1345f76a3b2`; exact source, UF2, 138 MHz/RAM/GP2,
retained configuration and network identity checks passed, Pico B remained
unchanged, no CONFIG or RF operation occurred, and the reservation was released
after fresh inactive A/B authority. The sanitized result is
[`phase11-6-clock-refinement-deployment-attempt2.json`](phase11-6-clock-refinement-deployment-attempt2.json).

This second amendment changes accepted source/image/boot identity but not RF
job payloads. Attempts 1-41 remain bound to their recorded predecessor plans.
Attempt 42 and later attempts use the current plan without recasting earlier
evidence.

Attempt 42 stopped before capture, production-client startup, `LOAD`, `ARM` or
RF because the isolated browser namespace could not resolve the retained Pico
hostname. Both boards were reconciled inactive and the reservation was
released. The browser tools now deterministically map the frozen hostname to
the already-pinned fixture address while retaining hostname-based HTTPS and
the pinned peer certificate. A browser-only validation passed page load,
authentication and manual refresh against the corrected boot. The
[sanitized attempt record](phase11-6-clock-refinement-attempt42.json) preserves
the failure, zero-RF accounting and tool hashes. Attempt 43 then passed browser
readiness but exposed an incorrect `--capture-helper` selection before capture
or production startup. Its
[sanitized record](phase11-6-clock-refinement-attempt43.json) preserves that
second pre-RF failure and reconciliation. Retained successful requests bind the
reviewed native capture helper and its SHA-256; a receiver-only readiness check
with that exact executable is required before proceeding, and the production
entry point rejects a different helper before reservation. The corrective entry point is
rebound to fresh sequence 44 with the same one-submission, zero-retry and
45.000001-second RF limits; attempts 42 and 43 may not be reused.

The required receiver-only check then passed at 1,813,100 Hz with the exact
native helper and RSP1B serial `2404058C60`: 500,000 retained CF32 samples,
zero overflow, zero clipping, first-read discard and verified device cleanup.
No RF output was requested. Exact IQ and metadata hashes are retained in the
attempt 43 record.

Fresh sequence 44 then completed the one authorized 45.000001-second corrective
RF job. A lower-uncertainty sample was accepted while the same job remained
Armed, the corrected image reprojected the local alarm, launched once and
completed without `MISSED_START`. Browser overlap, independent USB lifecycle,
retained Phase 11.5 health gates, capture integrity and physical-result-bound IQ
analysis passed. The
[sanitized attempt 44 result](phase11-6-clock-refinement-attempt44.json) records
the exact measurements, hashes, accounting and limitations. Cumulative RF
accounting is 42 RF attempts and 1245.000029 charged planned seconds; the two
pre-RF harness failures do not add RF charges.

At the corrective checkpoint, attempt 44 supplied only the production path for
the 160 m QRSS row. The continuation below adds the browser-owned and
controller-disconnect results, but the ordinary packet still cannot receive
packet-level audit credit until all jobs and restoration assertions are
present. No Phase 11.6 phase-closure claim is made.

## 160 m continuation checkpoint

After the timing requalification, sequence 45 was preserved without RF when a
manual `nsenter` invocation used a relative runner path. The runner never
started, the output root was absent, the reservation remained released and no
Pico request or capture occurred. Its packet was not reused. Fresh sequences
46 and 47 passed the browser-owned and controller-disconnect QRSS paths, so all
three QRSS submission paths now have passing physical and independent-IQ
results. The ordinary 160 m packet audit remains pending.

Sequence 48 completed the 160 m FSKCW production waveform and lifecycle, but
the independent analysis failed the frozen 0.15 rad phase-coherence threshold:
the 21-second low state measured 0.167284 rad RMS. Its +5.018197 Hz separation,
transition timing, carrier continuity, amplitude and contrast otherwise passed.
An offline diagnostic found a smooth approximately 0.040 Hz drift across that
state, not a dropout. Because the receiver axis is uncalibrated, the retained
evidence cannot assign that relative drift solely to the Pico or receiver. The
limit was not relaxed, the attempt was not repeated, and the browser/controller
FSKCW paths remain unspent.

Sequences 49 through 51 then passed the production, browser and controller-
disconnect DFCW paths. These packets and browser requests explicitly preserve
the project image's reverse dot-high/dash-low profile; conventional external
DFCW remains dot-low/dash-high. The full sanitized checkpoint, exact evidence
hashes, RF accounting and restoration state are recorded in
[`phase11-6-160m-attempt45-51.json`](phase11-6-160m-attempt45-51.json).

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
