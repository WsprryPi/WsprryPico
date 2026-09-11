# Phase 11.5 N1 execution

Status: **OPEN; no accepted physical clock.** This September 11, 2026 record
supersedes the original packet's pending-authorization and live-state wording.
The user authorized N1 and directed continuation. The original six-hour host
deadline remains unchanged; continuation carries prior management-write counts.

The N1/N1r candidate firmware was clean `6e2ddc9e476986046de74d18cbcc3a2f6b64d142`.
Pico A's inhibited baseline runs at 150 MHz, with UF2 SHA-256
`822a7c28617592c28f4f03996b009a66ee32199816a467756b314abf63e41a71`.
The selected physical configuration remains 138 MHz, PIO divider 1, SRAM
renderer, UF2 `ba74b33ec7fd7530a56cc679799d9f452f08d896d22930903ef8bba132387a4d`.
That physical image failed nominal A2 USB delivery on boot
`28f0c1f98b19c6e2a8752e9f3fd881a3`. A 2.964660695-second INFO reply exceeded
the sampling bound; raw chunks show intervening TLS steps. Quiet and controller-only
physical intervals passed. No RF job followed. Pico A was restored to its original
inhibited image, boot `e5a4bc355fe7898a1e0b6d06be36fe9f`, with output inactive.
Host restoration completed without failures, B was unchanged, and packet captures
reported zero kernel drops. The complete private N1r archive SHA-256 is
`b5c7e93eabae8e0149d7ee227fc540b2c1bf3e59d5830afd8e987296c7b3d82a`.
The [USB reply repair](phase11-5-usb-priority.md) at `4ca4494` requires both
new-image target baselines. Physical 132 and 150 MHz are untested.
Selecting another clock during 11.6 requires repeating the affected 11.5 checks.

## Preserved attempts

1. Original N1 passed its 360-second inhibited quiet observation. The private
   production INI had lowercase keys, which the actual application's exact-case
   parser ignored. The executable exited before readiness. A and the host fixture
   were restored; B remained unchanged. The private archive SHA-256 is
   `2ebc508c1489b2f6350d7ee4023e6e864077137d4da0e596a67b73d54418aa59`.
   See [the first-attempt result](phase11-5-device-fixture-result.json).
2. N1r used canonical INI keys and passed a fresh quiet observation. Its actual
   `fb0a2eb` controller achieved only 175 nominal STATUS reads in 180 seconds.
   The rate audit failed. No browser or RF case followed that failure.
3. The corrected controller, clean WsprryPi
   `6f65d5c7d202569102459ab68d7c9ea079b96f35`, passed the controller-only interval:
   **179 nominal STATUS reads in 180 seconds**, one connection/session,
   maximum native-write-entry-to-response time **0.638055880 seconds**.
   Executable SHA-256:
   `122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`.
   The independent 240-second observer reconstructed 240 INFO and 48 USB STATUS
   samples, with unchanged boot `c2c2aa975f5d7d03c0c4cca5dea5154c`, zero observed
   faults and allocator peak 63,156 bytes. This is an inhibited result only.
4. That attempt's browser interval failed its five-second sampling schedule.
   The initial serial status/page/style/script requests took approximately
   1.430, 2.022, 1.497 and 1.488 seconds. Their 6.437-second total delayed the
   next status request beyond the frozen one-second scheduling tolerance.
   The coordinator stopped dependent work. The USB observer's subsequent SIGTERM
   is coordinator cleanup, not evidence of a device fault.

## Current bounded continuation

The `browser-priority` workload preserves the controller executable and firmware.
It services status first and fetches one page asset in each of the next three
five-second slots. All declared request counts and deadline thresholds remain:
36 status requests and six requests each for page, style and script per 180 s.
Regression tests use the observed reply costs and still reject overload.

Its manifest SHA-256 is
`fc789d562dfb1621c8eedc725a50b862f00b91f1fd771eaf5bf83be670abc23c`.
The continuation re-audits the previous passing quiet/controller raw evidence,
requires the same boot and executable, preserves the failed browser attempt,
and repeats the affected nominal interval followed by the 360-second quiet
comparison. The repeated combined interval passed: 179 controller STATUS reads, 36 browser
status reads and six requests each for page/style/script. Its maximum measured
controller write-to-response interval was 1.311965149 seconds; the independent
observer reconstructed 240 INFO and 48 USB STATUS samples. Allocator peak was
125,428 bytes on the inhibited image. The final quiet comparison passed: 360 INFO and 72 USB STATUS samples, with
17,228 allocated bytes versus 16,660 at the preceding quiet baseline, a 568-byte
difference within the frozen 1,024-byte limit. The inhibited A2 baseline passed.
The authorized physical switch completed successfully; A2 remains partial until
the physical baseline passes.

The private root is `/home/pi/phase11-5-n1r-6e2ddc9`; original frozen restoration
helpers and packet are preserved. No RF job has been submitted by N1. The
installed WsprryPi executable/service, comparator B and GPSDO settings are
unchanged. The fixture radios and temporary DNS/chrony access have been restored.

## Validation and remaining work

The current hardware-free Pico suite passed 54 tests. The host cadence repair
passed 39,834 application checks and 6,853 production checks. Five load-driver
tests cover exact INI keys, no-run behavior, failed process evidence and browser
scheduling. The opt-in TLS observer passed eight concurrent loopback streams,
including 65,552-byte writes, six corrupted-log cases, version-1 compatibility,
and write-entry/result lifecycle checks. These checks do not qualify physical RF.

A3 finite-job observers/coordinators are prepared and require their final review
and execution after both A2 baselines. B through G remain unrun. The systematic
RF band/mode/clock comparison and spectral/filter qualification remain Phase 13;
per-band/mode conducted RF acceptance at selected clocks remains Phase 11.6.

Documentation Impact: this record, the joint plan/register and frozen-packet
status pointers. The companion Pi development review records the controller
repair. WTP, browser API and operator contracts are unchanged; published operating
limits still require acceptance. The separate operator-manual repository remains
unchanged.

## Revised-image continuation N1s

The [frozen packet](phase11-5-usb-priority-packet.json), SHA-256
`7985786b1796c7a36ba510d39ee08df6c06222a11e1e36795ae40b29cff755c7`,
binds clean firmware `4ca44943e844465e6109719ad91b900159f9d84f` and the
[new linked image list](phase11-5-usb-priority-images.json). Both standalone
images include the reply-priority change, so both A2 baselines are repeated.
The previous failures and passing old-image evidence are retained.

The private root is `/home/pi/phase11-5-n1s-4ca4494`. The inherited original
absolute host deadline is unchanged. Device runtime is bounded to 9,000 seconds,
with 600 seconds reserved for restoration; the host fixture is bounded to
10,500 seconds plus 600 seconds for cleanup. These are supervisor ceilings,
not required test durations. Four prior configuration writes were carried into
the packet; candidate configuration is the fifth. No RF jobs are in this packet.
Pico A's inhibited admission boot is `62e9ec13007db1d3e619a31cb6d33e5b`,
at 150 MHz, synchronized through the isolated DNS/chrony fixture. B, the installed
service and GPSDO settings remain unchanged. A2 is running; zero of the twenty
full acceptance cases is closed at this checkpoint.

Adversarial review of the prepared A3 actor found that calculating an ARM time
before waiting for a browser slot could consume the intended launch lead. The
actor now chooses the finite start from a fresh device clock snapshot after
acquiring the slot, then verifies and records the returned exact start. This
prepared path has not executed on a target; it does not close A3.
