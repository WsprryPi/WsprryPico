# Phase 11.4 B2 discovery and reconnection execution prompt

Own B2 only: locate the retained Linux packet-delivery/recovery failure, correct
an evidence-supported cause, and demonstrate repeatable physical discovery and
authenticated reconnection. Execute this prompt, perform adversarial review,
repair findings and reassess, then commit/push the owned work and report actual
closure or the precise remaining blocker. Do not represent nonreproduction as a
root-cause repair. Phase 11.4 remains the scope and other cases retain their
existing bounded results.

Work in `/Users/lbussy/GitHub/WsprryPico`, initially devel
`dbf1d86f088536a4c6adebd180f2e51ca7f83976`. Read applicable AGENTS.md, README.md,
CONTRACT.md, docs/architecture.md and current development commands. Review the
joint Phase 11.4 plan/procedure, latest shutdown prompt/results/evidence, packet
trace and loop records, and E1 results. Inspect HEAD, staged/unstaged/untracked
state. Preserve the pre-existing shutdown-results edit and untracked soak files;
do not include them incidentally in this commit. WsprryPi and dependencies are
independent repositories; reading them does not authorize editing them.

Use Bohica-IoT for every network experiment. It is the user-described bridge
providing a stable 2.4 GHz radio, not a routed network. Preserve USB wlan1 on
wspr5, its current IoT profile and boot-enabled recovery. Never switch traffic
to unreliable onboard wlan0. The Mac's Bohica-IoT association was user-confirmed
in this session. Do not investigate the confirmed prior power outage again.
Do not start the eight-hour soak, alter DHCP reservations, rerun unrelated
browser/ownership/scheduling acceptance, or create new roadmap gates.

Identify and bind every operation to these Pico 2 W/RP2350 devices:

| Board | USB serial | WTP ID | MAC | Certified hostname |
| --- | --- | --- | --- | --- |
| A, original B2 subject | `0BF4B4AEC9FFB344` | `fd6127d11d6aca42a9905fa3fb1bf1d5` | `88:a2:9e:0a:60:df` | `wsprrypico-0a60df.local` |
| B, E1-provisioned comparator | `CDDBF8767C506C07` | `29f20b7342051ef947aa56cb9d4fab42` | `88:a2:9e:0a:9d:89` | `wsprrypico-0a9d89.local` |

Both are attached to wspr5; Console aliases end in `-if00`, WTP in `-if02`.
Never open an ambiguous tty index or the unrelated GPSDO/SDR. Rediscover addresses
and boot IDs rather than assuming `.47`/`.53`. Keep schedules disabled and RF
inhibited. Fresh Console INFO and WTP HELLO/CAPS/STATUS must agree on the exact
device, boot, inhibited engine and empty/unowned/inactive state before mutations.
Stop dependent work on unknown output, identity mismatch or recovery boot; retain
original reset breadcrumbs before any explicitly bound recovery operation.

The user authorizes executing this B2 investigation: bounded read-only USB/LAN
inspection/captures, idle Pico reconnection cycles, and exact serial/hash-bound
standard inhibited diagnostic/repair deployments needed to test a concrete
hypothesis. This never authorizes RF output. Prepare and verify each image before
flashing; preserve journals, station settings, schedules, watermark, certificates,
short hostname defaults and independent per-board trust. No trust-store or
installed transmitter changes are needed. Use the existing private pinned
picotool under `/home/pi/phase11-4-e1/picotool-build/picotool` after verification.

Hypothesis 1: prior failures may correlate with endpoint AP/radio association or
client receive behavior. Historical Pico RX plus successful driver submission
does not prove over-air or peer delivery. Add a bounded, opt-in USB diagnostic
for the actual station BSSID and RSSI using the pinned driver's public read APIs.
Keep driver queries out of ordinary INFO sampling and physical RF images. Reject
uninitialized/disconnected observations instead of returning stale success; test
driver error propagation and exact station interface use. Retain the watchdog
and immutable SDK/driver source. Build/check/hash and deploy only standard
inhibited images with existing per-board certificate bundles.

Establish a paired baseline with native Linux NSS and Mac mDNS, certificate/name/
fingerprint-verified HTTPS and WTP identity, independent USB status/NETTRACE, and
filtered Linux ARP/mDNS/TCP capture. Record client interface, MAC, profile, BSSID,
band/frequency, addresses and recovery/service state. Capture start/liveness and
drop statistics are prerequisites for packet-absence claims. Correlate exact
packet headers and bounded cross-clock alignment, not aggregate counters.
Use B as a separately identified comparator without interchanging its evidence.

If associations differ, prepare a single-variable comparison on the same confirmed
2.4 GHz BSSID while retaining Bohica-IoT. Before any temporary host reassociation,
stage an independent local restoration timer, snapshot the exact current profile,
bound runtime and preserve recovery-on-reboot. Restore the current IoT profile,
not the historical Bohica profile. Stop if reliable independent restoration
cannot be established. Do not make unrelated AP/router/service changes. A
sequential reassociation alone does not prove the AP was the cause.

Before changing behavior, state the concrete defect hypothesis, expected
observations and experiment stop rule. Initially allow at most three diagnostic
reconnection cases; stop sooner on an identified failure boundary, watchdog,
missing observation or the same unresolved result. Each case has an independent
local log and bounded identity-checked Wi-Fi restoration. Use complete idle
OFF/ON only as a reconnection trigger; do not claim D2 closure from these cases.
No ownership or job operations are required. Authentication/time failures remain
connectivity findings within B2; do not bypass certificate-time validation.

A candidate B2 repair requires source/configuration evidence supporting the
change and a meaningful regression or controlled before/after observation.
After repair, require eight consecutive complete cases on A with no failed or
invalid attempt in that acceptance series: native baseline, 40-second local
activation bound, successful native Linux resolution and authenticated recovery
within 120 seconds, and at least five successful checks spanning 30 seconds.
Retain the first failure; never restart the count merely to discard it. Stop
after three unresolved failures, any observer/identity/path defect, or the
eight-case bound. A clean series without a demonstrated cause is only bounded
nonreproduction. Comparator evidence and Mac observations must be labeled by
their actual scope. Do not weaken deadlines or conflate mDNS, ARP, TLS and WTP.

If a supported software defect is found, implement the smallest owned repair,
add a failing-before/passing-after behavioral regression, run affected host and
image checks, then deploy the checked candidate for physical verification. Keep
USB timing independent of slow network probes. Preserve all failed, invalid and
superseded attempts and every historical B2/D2 result. No speculative watchdog
extension, cache flush, static neighbor or certificate bypass may masquerade as
a repair. Read-only failed-state diagnostics precede any recovery intervention.

Use new owner-only ignored evidence directories locally and on wspr5. Record
UTC, exact command/arguments, source/image/tool hashes, result/exit status and
raw evidence paths for every attempt. Never print passwords or private keys.
Distinguish sandbox denials from real LAN failures; use approved native access
when necessary. Publish sanitized evidence summaries, not captures/credentials.

Adversarially assess cause attribution, changed variables, exact board/image
binding, parser/observer completeness, genuine native resolver use, failure
retention, deadline enforcement, independent restoration, certificate/time
validation, source regression strength and final output authority. Fix actionable
findings, rerun affected checks and repeat the assessment. Do not label an
external unresolved fault fixed to satisfy a completion request.

Finish with authoritative USB checks on both boards and actual Mac/Linux
reachability; verify wlan1 remains on the original current IoT profile and
recovery/service state is preserved. Stop all task observers and transient units.
Save the executed prompt, evidence-bound results and limitations; update B2's
status only as justified. Commit only B2-owned files, push devel, verify remote
parity and report repository state. Reprint the same five-row remaining-items
table; keep diagnostic findings within their existing items.

## Execution amendments retained with their triggers

The first diagnostic included BSSID and RSSI. Pico A later watchdog-reset during
`cyw43_wifi_get_rssi`, identified by marker 27 and a new recovery boot. Remove
that auxiliary query rather than increasing the watchdog or query deadline.
Retain BSSID-only NETLINK with marker 26; verify that the failed RSSI function is
absent from the final linked images. Preserve the original diagnostic images,
logs and reset evidence. Rebuild/check/hash and deploy the corrected inhibited
images with unchanged certificates and journals before reassessment.

Repeated NETLINK sampling was removed from the packet observer after a lost
response. Sample association at the boundaries of an experiment and state that
those samples cannot prove continuous absence of roaming. A later overlapping
follow-up USB read invalidated a separate observer run; prohibit additional USB
readers until its systemd unit has positively exited. Preserve both attempts.

A same-radio comparison stopped during its preflight when the RSSI watchdog
occurred, before any host reassociation. Its temporary non-autoconnect IoT clone
was deleted and original recovery verified. A further comparison is conditional
on repaired diagnostic validation and freshly observed endpoint associations;
never assume that reflashed boards retain their former BSSID or boot identity.
These amendments do not turn a diagnostic repair into B2 acceptance or authorize
RF output, broader acceptance or an eight-hour soak.

The BSSID-only image also reproduced the pre-existing stage-14 startup watchdog,
before NETLINK was invoked. Review of pinned SDK 2.3.0 and upstream repair
`48a5de2ddec1b7859ac59388cd8d024ef4161825` identified a supported candidate:
disable its RP2350 sleep optimization with
`PICO_SYNC_RP2350_SPIN_LOCK_WORKAROUND=0` on the standard inhibited target only.
This preserves SDK/driver files, software spinlocks, watchdog duration and RF
exclusion. The tradeoff is additional CPU polling while waiting. Require the
actual old semaphore image to fail, and candidate image to pass, a check that
rejects a direct WFE before the timeout helper. Do not promote this candidate to
a physical RF target or claim that it fixes historical over-air ARP loss.

After fresh candidate identity and boot checks, reassess association and the
controlled peer path. B2-only reconnection cases may use a two-second idle OFF
interval; they retain the original 40/120-second recovery and five-check/30-second
stability limits. They do not qualify D2 withdrawal or cache expiry. Stage an
independent exact-device WIFI ON restorer before each case; it must stop the
case's USB observer before opening the device. Retain every failed/invalid case
and stop the acceptance series at its first failure; eight clean cases are
required for its bounded pass. No automatic restarts of a failed series.

The user asked whether to update the SDK. Released SDK 2.3.1 (September 4,
2026), commit `079c6f39023649b154152db30f1d781e884879bc`, contains the upstream
repair and officially supports the existing GCC 15.3.1. Supersede the temporary
2.3.0 fallback with this exact released pin. Build in a fresh private SDK
checkout without altering the sibling SDK repository. Keep unchanged linked
TinyUSB, CYW43, lwIP and Mbed TLS pins. Remove the now-redundant manual PSA RNG
source and the synchronization override. Check actual emitted event-drain/IRQ
ordering, allowing the fixed SDK's deliberate WFE while interrupts are masked.
Rebuild all target variants for compile/link compatibility; flash only exact
standard inhibited images. Preserve the earlier fallback image and its one
complete passing B2-only case as superseded, bounded evidence. Repeat B2
assessment on the released SDK; do not attribute historical ARP loss to the
SDK defect without a demonstrated causal link.
