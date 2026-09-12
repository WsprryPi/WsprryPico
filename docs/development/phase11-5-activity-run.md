# Activity snapshot candidate: bounded A2/A3 retest

Outcome: the user explicitly authorized the new two-hour network window and N1u
executed. Its inhibited conditioning interval failed the production STATUS
cadence audit; dependent A2/A3 work stopped and both device/host restoration
completed. [Exact result and evidence](phase11-5-n1u-result.json). No RF jobs
were submitted and no new acceptance case closed. The frozen plan below records
the approved scope; the earlier six-hour N0 deadline was not extended.

The source repair is clean `4058d3a4a95110326006a7db6e37eb4b562a500c`.
[All four linked images](phase11-5-activity-images.json) passed allocator routing,
stack guard, flash boundary and applicable SRAM-renderer checks. These are
compile-only results. The earlier A1/A2 passes remain attached to `8fb3894`;
the new candidate has no target acceptance evidence.

## Frozen scope

- Host: wspr5, boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`; Ethernet IPv6
  management, wlan0 isolated AP and wlan2 independent client. Temporarily pause
  the Wi-Fi recovery timer and install the same temporary chrony ACL. Preserve
  wlan1 and installed `wsprrypi.service`; no NAT or default test-network route.
- DUT A: USB `0BF4B4AEC9FFB344`, WTP
  `fd6127d11d6aca42a9905fa3fb1bf1d5`. Current restored boot must equal
  `5b336cccde0e8ce1389a333755cb84f3` before any mutation.
- Comparator B: USB `CDDBF8767C506C07`, boot
  `4e2fb851c08b278dd4b977104d2c2aaa`, read-only throughout.
- Physical image: `cb91912f7915db7828c5f58ea2a35c714c22728ee71f9ce04c7d034d22598154`,
  138 MHz, PIO divider 1, SRAM renderer. Inhibited image:
  `0a7d54673e7171ee10275272701de5fbb3cecdc91c097a18eeae496c0922c7b9`.
- Conducted GP2 path: confirmed 50 ohm load, 60 dB attenuation, no filters,
  existing combiner/SDR. GPSDO settings remain unchanged. No second-Pico RF,
  Pi GPIO4 output, band sweep or alternative-clock trial.

After serial-specific inventories and backup, flash the inhibited candidate,
configure the temporary network and run exactly one N180 conditioning interval
with USB240. Run the complete A2 Q360/controller180+USB240/N180+USB240/Q360
family. Independently review its raw USB and native TLS evidence before advancing.
Switch to the exact physical image and repeat that same conditioning/A2 sequence.
Do not reuse an older image's A2 result.

Only after both A2 families pass, freeze A3's measured boot/prerequisite digests
and run exactly three ten-second 135.5 kHz Tone jobs under N180 with USB240.
Each job requires independent Loaded/Armed/Running/Complete coverage, complete
hardware-counter deltas, output reconciliation and release. The 138 MHz full
buffer period is 262144000/69 ns; the 75-percent service/refill limit remains
2,849,391 ns, with at least 25-percent full/short predecessor reserve. Existing
stack, heap, USB, browser and production timing limits remain unchanged.

Restore original inhibited UF2
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`
and original configuration after authoritative idle checks. Verify both boards,
then restore networking and the recovery timer. An unexpected failure stops
dependent work; no automatic retry, fault clearing or journal erasure is included.
If device restoration admission fails, retain that block explicitly while the
independent host cleanup still runs. Do not infer inactive output from a lost
connection or supervisor exit.

The measured intervals total about 52 minutes; allow roughly one hour including
setup/review/restoration. The **two-hour ceiling is a cleanup bound**, not a
planned two-hour soak. Device runtime is capped at 5,100 seconds plus 600 seconds
for restoration. Host runtime is 6,600 seconds plus 600 seconds for cleanup.
Remaining-time checks must admit each operation. B1/F1 and the other unrun cases
are outside this retest packet.

## Artifact and review record

[The lifecycle packet](phase11-5-activity-packet.json) has SHA-256
`19c0161697bf0febfd9a459f2d0402aac8161aa6272d4853db485c6b982ac8d1`.
It binds current helpers, exact images, previous restoration evidence and
cumulative operation budgets (eight prior configuration writes).
The unchanged production binary is source `6f65d5c7d202`, SHA-256
`122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`;
the load driver is source `6703818`. Its observed-asset scheduling heuristic
remains subject to the actual cadence audit and does not excuse lateness.

The private local stage is `build/phase11-5-closure/n1u-stage`.
Use only reviewed archive `n1u-stage-reviewed.tar.gz`, SHA-256
`889e1c014032eb23544ad4c16038612111927219e43f2a3c9ad00059c1c3a6fa`.
Its workload manifest SHA-256 is
`6dee90b7f63d4b367f1a0b9101f6964045493c517c2e1632be9cc51015357b2b`.
The remote root is `/home/pi/phase11-5-n1u-4058d3a`; its failed conditioning and
restoration evidence are preserved. Retain all prior private roots and failures.

Preparation review corrected relative workload helper paths to absolute remote
paths, verified all staged hashes, and exercised default no-access entry points
against nonexistent roots. The repinned 55-test host suite passed in 22.92 s.
A follow-up review checked fresh-image prerequisite binding, unchanged finite
jobs, cumulative write counts, restoration identity and independent deadlines.
No further actionable preparation issue remains; physical A2/A3 are NOT_RUN.

Documentation Impact: development evidence, image identities, register and this
execution packet. No operator configuration or workflow change; no change to
the separate operator-documentation repository is required.
