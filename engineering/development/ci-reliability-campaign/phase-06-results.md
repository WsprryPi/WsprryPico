# Phase 06 deterministic synchronization

Implementation, local adversarial verification, and both full production
source-pair recipes passed. This phase is accepted for the candidate below.

## Timing and synchronization contracts

| Former assumption / wait | Replacement or retained role |
| --- | --- |
| 20 ms after TLS control writes | Correlated SYNC sequence after command effects and normal foreground polling; original diagnostic facts are retained and bounded |
| TLS 30/50 ms cleanup sleeps | Observe actual active/pending connections and completed callbacks; refuse stale, late, missing, or unconsumed control facts |
| 50 ms overlap assumption | Observe both in-flight connections behind a real paused gate, including the valid active-plus-pending-handshake case |
| 100 ms pause observation | Observe actual queued TLS bytes, paused servicing, and successful independent WTP/Plain STATUS progress |
| Five-times host clock | Explicit monotonic microsecond test clock; ordinary companion/default fixtures retain real monotonic time |
| 400 ms until Running and 2.2 s until Complete | Advance to just before/at the requested start and completion boundaries, and inspect actual job state, including completion while link is off |
| Hostname 2.2 s cancellation observation | Hold the actual product countdown callback, cancel through the page, execute that callback, await its real continuation, and prove no reschedule or additional restart |
| Admission 5 ms poll pacing | Retained bounded polling of actual admitted connection and queued ClientHello bytes; it is not readiness evidence by itself |
| Driver 100 microsecond idle pacing | Retained foreground CPU pacing; SYNC and state effects, not elapsed pacing, qualify progress |
| Socket/pipe/CTest timers | Independent real failure watchdogs, bounded by enclosing monotonic budgets; no performance assertion or product deadline inflation |

The test clock uses an atomic mode flag and protected time value so it adds no
64-bit atomic linker requirement to existing hosts. Firmware never links this
socket adapter. Advances reject overflow and cannot move backwards. Driver input
is bounded, partial oversized lines are discarded without interpreting a prefix,
and unknown/noncanonical/stale/overflow controls fail explicitly before effects.

TLS certificate validation retains its actual disciplined UTC mapping and the
existing missing/rogue/expired-certificate alert assertions. CLOCK OFF still
refuses unusable time and CLOCK ON coherently restores it. Protocol monotonic
time, UTC, and certificate authority are not substituted for one another. Product
session, transport, and RF timing constants remain unchanged. Host-only exact
checks cover the one-second fatal-alert retention and fifteen-second HTTP deadline,
plus requested two-second job lead and 10.24-second completion.

Socket reads/writes and TLS acquisition now carry their fixture's absolute real
watchdog, reject late success, and preserve acquisition/cleanup failures. HTTP
accumulation uses the existing one-MiB fixture safety bound; the current largest
served document is below 500 KiB. It is not an advertised product limit. The
existing 90-second TLS CTest cap contains an 80-second operation scope and cleanup.
Nagle/admission use eight-second scopes inside fifteen-second CTest caps;
local/plain use 23-second scopes inside thirty-second caps. The existing six-second
fixture teardown therefore has reserved room. No outer CTest cap was inflated.

## Adversarial findings and proof

- Initial controlled-clock checks incorrectly required two active connections;
  observed transport state correctly showed one active plus one pending handshake.
  The oracle now qualifies the actual two-connection state instead of waiting longer.
- The old ownership refusal asserted HTTP 409 alone. An isolated production API
  variant appended a real configuration journal entry and still returned 409.
  The former response-only oracle passed; the new independently observed revision
  and saved-value checks reject that hidden write.
- The former paused-Plain admission test sent no ClientHello. It now emits actual
  OpenSSL TLS 1.3 input and requires retained bytes and independent successful
  Plain WTP progress, eliminating a vacuous negative observation.
- Strict reply correlation initially exposed legitimate asynchronous WTP events.
  The reader now validates current WTP schemas, exact session/boot/event bindings,
  monotonic event identifiers, and replies. Advisory gaps explicitly obtain STATUS
  authority. Duplicate or stale replies cannot disappear behind a successful reply.
- The operator monitor's resynchronizing decoder was inappropriate as a test oracle.
  A dedicated strict network framer retains partial frames but rejects bad magic,
  header/version/flags/length/checksum, junk prefixes, and bad frames followed by
  valid frames. The operator monitor's intended recovery behavior is unchanged.
- New native clock tests force assertions on in release builds. Bounded native
  parser tests cover oversized partial input and canonical counter/time refusal.

Four isolated compiled variants demonstrably entered their altered behavior and
failed the intended oracle: delayed HTTP timeout comparison, delayed completion,
hidden persisted write, and an unfinished TLS handshake blocking independent Plain
admission. The first attempted duplicate-admission variant never reached its
altered guard because an upstream guard correctly refused it; it was excluded
from accepted sensitivity evidence. A separate allowed-loss variant dropped the
first two advisory events, triggered an actual STATUS read, and passed the full
TLS suite. Candidate sources and normal object outputs were not replaced by mutation code.
The mutation compiler commands initially retained normal dependency-file paths.
Those outputs were isolated, and four identified generated normal objects and
their dependency records were rebuilt from actual candidate sources before the
final positive checks. One diagnostic gap invocation omitted the configured v4
credential suffix and failed before qualification; the corrected invocation uses
the generated CTest command. These diagnostics are counted separately from
required-suite success.

Hostname sensitivity deliberately invalidated the cancellation token after the
actual cancel action. The scheduled continuation was detected rescheduling; the
intended assertion failed. An independent parent verified both native driver groups
and Chrome's group were dead and the private profile was removed. The normal
hostname run passed all obligations and retained its 66 captures.

## Validation and accounting

All ten affected registered network/control suites passed locally, with zero
skips (11.03 seconds after dependency-record repair; the final four-suite budget
subset passed in 9.96 seconds). This includes 25 new Python
methods, the native clock case, the native control-parser case, and all five
existing real TLS/Nagle/local/plain/admission suites. Frozen changed executable
inputs and accounting are in [phase-06-measurements.json](phase-06-measurements.json).
There are 637 net added physical executable lines across eighteen changed paths,
including eight new helper/regression files and five CTest registrations. No code
reduction credit is claimed. Mutation compiles, links, counterfactual runs, extra
HTTP observations, and state/control round trips are additional qualification work.

The same warmed local container observed 16.13 seconds for the pre-clock TLS suite
and about 9.7 seconds after these changes. Coverage and assertions increased;
this does not attribute savings to one change or establish hosted CI speedup.
The actual partner recipes retain real transport time, including the scheduled
sixty-second integration case. No physical device, installation, GPIO, or RF
qualification was performed.

Ignored build/campaign-phase06-* logs retain diagnoses, commands, mutation source
hashes, and results. Reassessment closed the actionable findings above. Remaining
inner-framework discovery/skip qualification and other reader adoption belong to
phase 07; build reuse and execution scheduling remain phases 08 and 09.

## Source-pair acceptance

Pico 0b24fd5c5a129d6b6436c0459b1737b8d2389c0e and Pi
1e15b2485ac6e1b9cbb6ff435afc0f0232528804 passed both complete recipes with
recursive MbedTLS 0bebf8b8c7f07abe3571ded48a11aa907a1ffb20. The candidate
was committed and clean; no tested uncommitted input is hidden in this gate.

Network commands were wtp-network-runtime-test (916 checks),
wtp-network-interop-test, and wtp-config-interop-test. USB commands were
wtp-usb-pair-client-build, wtp-usb-management-test, wtp_usb_settings_test.js,
and wtp_usb_pair_test.js with the actual candidate usb_management_driver and
WSPRRYPI_GPIO_DRIVE_REQUIRED=1. PICO_SOURCE explicitly selected this campaign
worktree; MBEDTLS_SOURCE selected /deps/mbedtls-pinned. Network build output was
explicitly /home/campaign/pair-network. WSPRRYPI_DISABLE_HARDWARE_ACCESS=1
remained set. Full outputs are build/campaign-phase06-network.log and
campaign-phase06-usb.log. These are hardware-free software results.

[Canonical phase 06 run](https://github.com/WsprryPi/WsprryPico/actions/runs/42094622087)
completed successfully. Independent download verification checked all 28 command
receipts and log digests, and the exact 231-suite CTest inventory without failures
or skips. Aggregate command elapsed was 847.579 seconds; the verify job took
971 seconds. Its actual merge source a66bb83af52ea0ec7af183fc00c5362b15639100
has the verified parents c9fd28ef57265c942900bdfe0595f90a31926ff9 and the
accepted candidate 0b24fd5c5a129d6b6436c0459b1737b8d2389c0e. This source
binding was checked independently against the GitHub commit API. The evidence
remains version 1 command evidence; phase 07 adds source-bound inner discovery
counts. The prior phase 05 result is independently verified in its result record.
No merge, release, deployment, or physical qualification was performed.
