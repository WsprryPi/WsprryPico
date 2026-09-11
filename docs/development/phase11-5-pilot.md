# Phase 11.5 P1 instrumentation pilot

Status: **P1 FAILED BEFORE FLASH; revised helper packet pending.** This packet establishes an
initial physical instrumentation observation before the full A-G campaign. It
does not accept a clock configuration, heap envelope or conducted RF quality.
The [joint plan](phase11-5-plan.md) and [register](phase11-5-register.json) remain
OPEN. The [frozen packet](phase11-5-pilot.json) binds the clean source, exact
candidate hash, host boot, job IDs and all six helper/schema hashes. No change to the 11.5/11.6/13 division.

## Frozen operation limits

- DUT: Pico A, USB `0BF4B4AEC9FFB344`, WTP
  `fd6127d11d6aca42a9905fa3fb1bf1d5`. Pico B (`CDDBF8767C506C07`,
  `29f20b7342051ef947aa56cb9d4fab42`) receives read-only inventory only.
- Candidate: `WsprryPico-StandaloneRF`, `pio-dma-gp2`, 138 MHz configured system
  and sample clock, PIO divider 1, SDK 2.3.1 and Arm GNU 15.3.1. Same per-device
  credentials and stored configuration; no configuration/schedule write.
- Three complete Tone jobs, each nominal **135,500 Hz for 10 seconds**, with
  distinct frozen job IDs: **30 seconds total RF**, no repetitions or retries
  beyond those three jobs. NCO quantization is explicitly allowed; at the
  uncorrected configured clock the predicted realization is approximately
  135,500.002652407 Hz. This is not a measured electrical frequency.
- Each job is observed Loaded for 2 seconds, then armed about 5 seconds ahead
  using the device's existing synchronized clock, normal leap state and at most
  500 ms admitted uncertainty. No USB time setting, GPSDO or host-clock change.
- Console INFO at 1 Hz; one persistent USB WTP controller at nominal 1 Hz STATUS
  while executing; host health at 5-second intervals. Observe 10 seconds idle
  before the first job and after the last. The helper has a 180-second deadline.
- This is a USB/physical-engine diagnostic with ambient firmware networking.
  It adds no browser/production-network pressure or network observer and does
  not claim the full nominal workload N, matched quiet period Q or A-G coverage.
- No SDR capture or decoding; no wspr5 GPIO4, GPSDO or comparator activation.
  GPSDO outputs were already enabled at 10 MHz LOW and remain unchanged.

The user reports 50 ohm attenuator loads, no filters, 20 dB per combiner input,
then 20 + 10 + 10 dB after the combiner into the RSP1B: 60 dB fixed attenuation
per input plus combiner loss. Both Pico GP2 paths and one GPSDO path are connected.
The GPIO, finite DMA chain and two-core memory path are the real physical build.

## Stop thresholds and interpretation

At 138 MHz, the full 16,384-word interval is exactly `262144000/69` ns,
approximately 3,799,188.406 ns. The pilot's worker service-gap stop threshold is
2,849,391 ns (75% of that interval, rounded down). It already includes the prior
poll, so max_poll is not added. Every measured full or short predecessor must
retain at least 25% of its own original word count after successor installation.
The short-block interval is recalculated as `words * 32 * 1e9 / 138000000` ns.
The first three identical jobs end in 2,312-word partial data blocks.

Require zero invalid reserve observations, unpaired running refill observations,
exhausted predecessor links, DMA errors, device/protocol faults or changed boot.
Counters must show three launches, three tail completions, 7,902 handled DMA IRQs
and 7,896 running successor links. These counts follow from 2,633 data blocks
plus one zero-tail descriptor per job. Require observed Armed, Running with
active output, Complete with inactive output, then released/empty state for
every job. A Running/inactive transition immediately before terminal retirement
is allowed; it never establishes Complete by itself.

INFO starts must have gaps at most 2 seconds; host-health starts at most 6 seconds,
with no host boot change or throttling. Observer failure stops dependent work.
All frame bytes, decoded replies/events, observer failures, commands and exits
are recorded with sequence numbers and host wall/monotonic time. USB framing
corruption is not silently resynchronized. The target timer still resolves only
microseconds. The [metric definitions](phase11-5-metrics.md) retain the missing
IRQ-entry/electrical coverage and memory/stack limitations.

These are frozen pilot stop rules, not universal WCET or resource acceptance.
The helper's success marker says `DIAGNOSTIC_COMPLETED_NOT_ACCEPTANCE`. Allocation
exhaustion, true transient peaks/largest-block capacity, stack call-chain
allowances, independent network observers, diagnostic/deployment overhead
comparison, bus contention, additional modes and the sustained run remain open.

## Supervision and restoration

Run locally on wspr5 in one new private directory with a new transient systemd
unit. Use `Type=exec`, `Restart=no`, `RuntimeMaxSec=600` and
`TimeoutStopSec=420`. Arm the separate `ExecStopPost` restore process in the
same unit definition **before its start stage can change the board**. The two
stages use `phase11_5_pilot_supervisor.py start` and `restore`; each requires
`--run`, the same packet/candidate/restoration paths and a fresh evidence path.
The maximum unit lifecycle is 17 minutes; nominal execution should be much
shorter. No existing service is stopped, enabled, disabled or reconfigured.
No interface, namespace, route, resolver or trust-store change is part of P1.

The start stage:

1. Checks wspr5 boot, at least 1 GiB free space, all helper/schema/image hashes
   and the existing picotool executable hash. Takes serial-bound P0 inventories
   of A and B, requiring empty/unowned, explicit output false, disabled schedules,
   healthy storage and no recovery/fault state.
2. Requires A's original inhibited runtime `802c91a7b86e-dirty`, then sends its
   guarded Console BOOTSEL and waits for the same serial as `2e8a:000f`.
3. Uses existing picotool 2.3.0 at
   `/home/pi/phase11-4-e1/picotool-build/picotool`, SHA-256
   `4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921`.
   Saves and verifies all flash privately. Checks every application payload
   block against the original restoration UF2 before writing the candidate;
   the special RP2350-E10 boot block is outside that application comparison.
4. Performs one `load -v -x` with explicit `--ser 0BF4B4AEC9FFB344`.
   No erase-all, OTP access, debugger, force-reset or unqualified board selection.
5. Confirms candidate identity/clock/boot, empty inactive state and preserved
   station/schedule/watermark/name settings, then executes the reviewed finite
   pilot. An absent acknowledgement, failed command or wrong identity stops it.

ExecStopPost requires complete start/pilot finish records, matching candidate
boot and clock, fresh authoritative idle/unowned/inactive state, preserved
configuration and unchanged comparator. Only then may it perform the one
guarded restoration flash. It checks both boards afterward. The restoration
UF2 is the existing inhibited image:

`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`

Local source artifact:
`build/phase11-4-radio/firmware-a/firmware/WsprryPico.uf2`.
It restores the original qualified inhibited firmware; application writes do
not erase the saved journals. Raw flash backup is never used as an automatic
restore image. Candidate and restore images contain private deployment material
and must remain outside Git with owner-only access.

On failure, ExecStopPost refuses a blind reboot/reflash. Preserve the failure and
all raw evidence; do not clear a fault or retry a job to resume. The agent must
use the separately authorized read-only reconciliation and report actual board
state. If USB authority cannot be recovered, output remains unknown. Conditional
restoration can therefore remain blocked after an unexpected failure; successful
SSH return, process exit or USB disappearance never proves inactivity.


## Frozen artifacts and prepared command

Clean source: `ce1c339a976e795e90c38c4a57578f9c8ed75615` (runtime
`ce1c339a976e`). Candidate UF2 SHA-256:
`b9af965a012e1dcbad6310b36285fe386a89218ccf2fe9c263afaf84bfec356c`.
Candidate ELF SHA-256:
`8a6985ec803b86c59fd89b8272286c50316d5ef6ba0de22038e51b95f48b6a6f`.
Packet SHA-256:
`377bddc6554563ecdef36f72c8378abf1173a904a78cd8ee6d9d64c263f6ce87`.
All four build identities/layouts are in [image records](phase11-5-images.json).
Later documentation commits do not change this frozen firmware identity.

Private wspr5 directory: `/tmp/phase11-5-p1-ce1c339`. Its exact packet and images
passed the supervisor's default validation without `--run`; no device was opened.
Management Ethernet was up at 192.168.1.54, host boot matched the packet and the
installed transmitter service remained active. Before execution, check every
helper hash again and require that the new unit/evidence path does not exist.

The prepared launch is one `sudo -n systemd-run` for unit
`phase11-5-p1-ce1c339`, with the properties above and this ExecStopPost:

`/usr/bin/python3 /tmp/phase11-5-p1-ce1c339/scripts/phase11_5_pilot_supervisor.py restore --packet /tmp/phase11-5-p1-ce1c339/packet.json --candidate /tmp/phase11-5-p1-ce1c339/candidate.uf2 --restoration /tmp/phase11-5-p1-ce1c339/restoration.uf2 --evidence /tmp/phase11-5-p1-ce1c339/evidence --run`

ExecStart uses the identical arguments with `start` replacing `restore`.
The original P1 unit ran and failed before BOOTSEL or RF; see the preserved
[attempt record](phase11-5-pilot-attempt1.json). Any revised authorization covers
both guarded flash operations, the three finite RF jobs, read-only inventories,
flash backup, and this new bounded transient supervisor. P0 readback approval
alone does not authorize P1.
