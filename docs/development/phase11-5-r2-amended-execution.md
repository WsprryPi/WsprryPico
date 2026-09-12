# R2 amended-candidate execution

**Executed; these packet identities are spent.** See the
[review](phase11-5-r2-amended-review.md) and
[result](phase11-5-r2-amended-result.json): R1 5/5 and the three-Tone gate passed,
R2 remains 3/7, and boards/host were restored. Reuse applicable evidence and the
frozen firmware; do not replay these packets or repeat R1 automatically.

Execute the user's UTC-second launch-policy amendment on clean firmware
`049cc929143bdec6ec32817f6df0c73a9637cdf5`. Preserve the e20ae8b missed-start
attempt and its separate R1 closure. No result transfers across these images.
The [four linked layouts](phase11-5-r2-amended-builds.json) bind the current
physical 138 MHz/divider 1/RAM/listener-on image and inhibited 150 MHz regression
to their exact ELF/UF2 hashes. Listener-off images supply layout comparisons only.

The user explicitly requested execution of the amended prompt. Existing USB,
flashing, finite RF and bounded network-fixture authorization applies. Use SSH
outside the sandbox. Preserve Pico B, installed WsprryPi, Ethernet, wlan1,
GPSDO settings and permanent time.local/GPS-PPS/Avahi. The confirmed conducted
GP2 paths remain 50 ohms, 60 dB per input, without filters.

## Frozen execution sequence

1. Use new private root `/home/pi/phase11-5-r2-amended-049cc92` and fresh
   serial-specific inventories. Carry configuration count 28/32 and three
   historical heap probes forward. Preserve original image/configuration hashes.
2. Arm host and device restoration before mutation. Host work remains bounded
   to 70 minutes plus ten minutes cleanup; device work to 45 minutes plus ten
   minutes restoration. Do not extend these deadlines. Normal setup/restoration
   consumes two configuration writes, ending at 30/32.
3. Repeat the complete R1 baseline on the new image: inhibited N180/USB240,
   physical warm N180/USB240, three idle allocation probes, quiet360,
   controller180/USB240, physical N300/USB360 and quiet360. Retain all original
   resource, stack, matched-heap, time.local and raw-wire assertions. Probe count
   ends at six cumulatively; the intentional NULL is distinguished from an
   unexpected allocation failure.
4. Publish the R1-to-R2 handoff only after all six intervals and probes pass.
   Bind its source, boot, packet/result hashes, demonstrated allocation size
   and unchanged device deadline. No RF occurs during these intervals.
5. Under the same restored-state supervisor, run exactly three browser-owned
   ten-second 135.5 kHz Tone jobs with N300/USB360. Each complete finite job has
   its own frozen identity. Require at least 450 seconds remaining at admission.
   No replay, reset, concurrent USB reader or automatic RF retry is permitted.
6. Audit raw lifecycle, ownership, allocator/stack, complete DMA/refill/tail and
   timing evidence before any later mode. At 138 MHz, the full block is
   3,799,188.406 ns and its 75% budget is 2,849,391 ns. Compute short intervals
   from actual predecessor words and require at least 25% remaining reserve.
7. Remaining QRSS, FSKCW, DFCW and WSPR require a separately frozen finite
   packet and actual production-owned/USB-reference paths. They cannot be
   inferred from the three browser Tones. A later packet must fit the unchanged
   restoration deadline; an absent or failed packet leaves these assertions
   open and must not keep the fixture alive.
8. Restore only after authoritative safe-state admission. Preserve unexpected
   failed/unknown state for reconciliation; host cleanup proceeds independently.
   Verify original configurations, both boards, installed process/binary and
   permanent time.local after cleanup.

The R1 parent packet SHA-256 is
`0c880ce75a0eec23dbbf12ff6103fc5632fb9c310a30684fa5e5ffa29ea5802f`.
The reviewed Tone packet SHA-256 is
`11c3125e459083031e2756c09e053e16efb5744732ca8345529fc2e709873791`.
Its unexecuted pre-review predecessor, SHA-256
`bc4260f1d0deabcdd7a6370ced509674829e680e212ab5a01424551a65634e8b`,
is preserved separately. The intermediate telemetry-review packet
`6f75d214e023e57848815fd25a93c8e618177c576314b3ceaeabf568b695a65f`
is also preserved and unexecuted. Review corrected new-candidate telemetry
interpretation and ensured a completed-launch INFO snapshot before RELEASE.
These changes preceded RF and did not alter a running R1 helper or its packet.

## Review and publication

The pinned firmware checks its execution sample against the exclusive end of
the requested UTC second. Post-enable observation is diagnostic and may cross
that boundary after an admitted launch. Require nonnegative reported delay and
`launch_delay_ns = launch_observed_ns - launch_target_ns`; do not use diagnostic
bookkeeping to cancel or retrospectively reject an admitted execution. Missing
guarded completion, wrong epochs, clock-invalid launches or inconsistent raw
telemetry remain failures. Post-enable telemetry is not electrical-edge metrology.

Perform an adversarial assessment of source pins, handoff/deadlines, cumulative
counts, failed-path cleanup, raw evidence and reported closure. Repair actionable
tooling findings, rerun affected checks and assess again. Keep failures and
not-run subcases separate. Commit scoped helpers, tests and documentation,
push devel and verify remote parity. Never commit credentials, firmware or raw
captures. Publish family/job counts and remaining assertions explicitly; the
full accepted-configuration list remains empty until all six families pass.
Physical 132/150 MHz remain untested. A clock selected later in 11.6 requires
affected 11.5 checks; the systematic sweep remains in Phase 13.

## Remaining submission-path preparation

Source inspection of the unchanged production executable's `6f65d5c` paths
identified requirements for the later mode packet. `WtpApplication` generates
its own job prefix and sequence; a prospective production job must be bound
while its scheduler is Waiting and before dispatch. A custom authenticated TLS
client cannot substitute for that application. Waiting offers STATUS after five
seconds; executing offers STATUS after each completed response and a bounded
ten-millisecond pause, with lease renewal as needed. The idle one-hertz assertion
must not be imposed on these different production states or used to conceal
their actual request rate.

The production compiler also constructs its own events. Native ETE QRSS lacks
the diagnostic campaign's one-second quiet prefix/suffix, and native WSPR
truncates each symbol to integer nanoseconds. Freeze and audit the actual
source-derived events, exact duration and final buffer words before choosing
that job for the production path; do not silently identify a different event
list as the already frozen campaign job. The current three-Tone packet does not
resolve that selection.

USB-reference submission needs one owner of the WTP endpoint that both submits
and observes the finite job. The existing RF observer is a read-only endpoint
owner, and its raw auditor only admits HELLO/STATUS. A later runner/auditor must
explicitly admit and verify the bounded mutation sequence; opening another
reader or dropping that observation is not acceptable. These preparation
requirements remain distinct from the amended launch-policy Tone gate.
