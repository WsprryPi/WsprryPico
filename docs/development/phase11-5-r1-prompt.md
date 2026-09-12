# R1 time.local execution prompt

Execution explicitly authorized by the user on September 12, 2026.
Disposition: executed; [R1 closed 5/5](phase11-5-r1-review.md), Phase 11.5 1/6,
with no full accepted configuration. The [completed time.local packet](phase11-5-r1-time-local-c-packet.json)
is separate from the preserved failed/unexecuted attempts. The authorization
below is the historical execution record; its finite lifetime has ended.

Execute Phase 11.5 family R1 using the permanent time.local service on wspr5.

EXECUTION TRIGGER AND AUTHORIZATION

This prompt is preparation only until I explicitly ask you to execute it.

When I ask you to execute it, complete the implementation, validation, bounded
hardware campaign, restoration, adversarial review, corrections, repeated
review, commits, pushes, and final report.

I explicitly authorize the bounded R1 fixture described below. Do not pause
for another permission request for actions already covered by this prompt,
including packet preparation, scoped repository changes, staging, serial USB
operations, flashing Pico A, the three idle heap probes, temporary fixture
network changes, guarded restoration, and committing/pushing scoped changes.

Prepare and validate the concrete packet before starting the fixture, then
execute it without an intermediate approval checkpoint.

Actual permission-system denials or conditions outside this scope must not
be bypassed. Stop affected actions, perform authorized cleanup where safe,
complete independent work, and report the specific blocker. Do not expand
scope or treat missing evidence as a pass.

OBJECTIVE AND BOUNDARY

Close R1: target memory, stack, allocation feasibility, and measurement
overhead for the exact selected firmware and clock configuration.

Work only on R1. Do not execute R2–R6, submit RF jobs, perform a band/mode
sweep, or investigate alternative clocks.

Phase 11.5 establishes resource/contention acceptance for clocks selected
for Phase 11.6. Phase 11.6 performs per-band/per-mode conducted RF acceptance.
Phase 13 owns systematic band × mode × clock comparison, final supported
configurations, filters, spectral qualification, and release firmware.

R1 closure alone does not accept a clock for all of Phase 11.5. Selecting
another clock later requires repeating the affected Phase 11.5 checks.

REPOSITORIES AND REQUIRED CONTEXT

Primary repository:
  /Users/lbussy/GitHub/WsprryPico

Related repository, only for necessary R1 host helper changes:
  /Users/lbussy/GitHub/WsprryPi

Inspect branch, worktree changes, remotes, and current instructions first.
Preserve unrelated work. Read each applicable AGENTS.md and, in WsprryPico,
README.md, CONTRACT.md, and docs/architecture.md before implementation.

Read the current development instructions and these WsprryPico documents:
  docs/development/phase11-5-plan.md
  docs/development/phase11-5-acceptance-ledger.md
  docs/development/phase11-5-r1-prompt.md
  docs/development/phase11-5-r1-review.md
  docs/development/phase11-5-r1-result.json
  docs/development/phase11-5-r1-packet.json
  docs/development/phase11-5-r1-admission-failure-packet.json
  docs/development/phase11-5-status-delivery-result.json
  docs/development/phase11-5-metrics.md

Inspect the R1 runner, network/device fixtures, observers, auditors, and
their tests. Inspect WsprryPi’s phase115 production-load and TLS-observer
helpers where relevant.

Previously recorded repository heads, to verify rather than assume:
  WsprryPico: 58ba01d7d251b3943b99de01d0971a704b900202
  WsprryPi:   2250ca3dd687979b9967372bc8b763351c67a447

Scoped harness, configuration, auditor, test, and documentation corrections
are authorized. Reuse the frozen firmware images. Do not introduce an
incidental firmware redesign or rebuild images merely because documentation
or host helpers have changed.

TIME.LOCAL UPDATE

The user reports that wspr5 permanently provides time.local using Debian
chrony, the attached GPS/PPS, and Avahi. Mac verification returned valid NTP,
stratum 1, reference PPS. The service serves 192.168.1.0/24, starts
automatically, and refreshes its alias after DHCP changes. Internet NTP
fallback and wspr5.local remain available.

Read this file on wspr5 before changing the fixture:
  /usr/local/share/doc/time-local/README.md

Use SSH outside the sandbox. Inspect the actual current chrony, Avahi,
publisher, addresses, and services read-only before selecting integration
details. Baseline and restore the current permanent time.local installation,
not the older pre-time.local host configuration.

For a chrony client, the configuration is:
  server time.local iburst

For the Pico’s existing saved configuration schema, use:
  wifi.ntp_ipv4: "time.local"

That field accepts a hostname despite its name. Do not put a chrony
directive into Pico configuration or configure wspr5 to synchronize to
itself.

The frozen candidate enables LWIP_DNS_SUPPORT_MDNS_QUERIES and resolves
the time-server hostname through the lwIP DNS API. Preserve that existing
capability. Source support alone is not evidence of successful resolution
on the target.

The R1 AP subnet is 10.77.15.0/24. Successful resolution or NTP responses
from the Mac on 192.168.1.0/24 do not establish fixture reachability.

Before flashing either candidate image:

1. Verify permanent time.local service health on the normal LAN.
2. Activate the authorized isolated fixture.
3. From the actual wlan2 client namespace, exercise native mDNS resolution
   and verify that time.local resolves to the reachable fixture address,
   10.77.15.1.
4. Verify a valid NTP response from that address with the required time
   quality, including the reported stratum 1/PPS identity.
5. Preserve packet evidence sufficient to distinguish discovery failure,
   address selection, and NTP request/response failure.

Use the existing Avahi installation. If necessary, add only a temporary,
fixture-scoped publication or interface exposure using a supported mechanism.
Track its ownership and remove it during cleanup. Preserve permanent alias
publication, DHCP refresh behavior, wspr5.local, and normal LAN discovery.

Add only the temporary chrony access needed for 10.77.15.0/24. Preserve the
permanent LAN ACL, GPS/PPS configuration, and Internet fallback.

Do not add routing or NAT to make an unreachable LAN address appear usable.
Do not substitute /etc/hosts, synthetic unicast .local DNS, or a literal IP
and count that as successful mDNS acceptance.

Update the runner, configuration guards, packet schema where necessary,
preflight, and auditors together. The old clock.phase115.test UDP/53 check
does not validate this mDNS path. Do not merely replace a hostname string.

Preserve the previous DNS failure evidence. A successful time.local run is
new evidence and does not prove the old failure’s root cause was repaired.

EXACT TARGETS AND FIRMWARE

Pico A, mutable R1 target:
  USB serial: 0BF4B4AEC9FFB344
  Device ID: fd6127d11d6aca42a9905fa3fb1bf1d5

Pico B, read-only reference:
  USB serial: CDDBF8767C506C07
  Device ID: 29f20b7342051ef947aa56cb9d4fab42

The user has rebooted the Picos between attempts. Obtain fresh serial-bound
identities, boots, firmware, configuration, ownership, and output state.
Do not reuse historical boot IDs as current admission identities.

Frozen candidate source:
  e20ae8bea2d5237af017dbd5f73bfe9332ce144e

Physical configuration:
  138 MHz system/PIO clock, divider 1, RAM renderer.

The 150 MHz inhibited configuration supplies shared-path regression evidence
only. It does not qualify physical transmission at 150 MHz.

Use all four exact image/layout identities from
phase11-5-status-delivery-result.json. “Network off/on” refers to the network
control listener variant; do not describe it as all Wi-Fi code being absent.

Network-control-on inhibited UF2 SHA-256:
  d4564a5c28db81e6e000542632cae3a4ae00f7a0263ecb4b2061f3f477c7e6e8

Network-control-on physical UF2 SHA-256:
  7a7306b8ad9dab694903434b86aec18e249c79dad0443645cd04ca857e9d4a04

Original Pico A inhibited restoration UF2 SHA-256:
  25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10

Verify available images, ELF identities, and restoration configuration before
mutation. Keep credentials and generated firmware out of source control.

Identify the actual isolated WsprryPi executable by source revision and
binary hash, separately from the current Mac checkout and installed service.
Do not replace or restart the installed WsprryPi service.

FIVE R1 ASSERTIONS

R1.1 — Layout and instrumentation identity
Revalidate or reuse the existing evidence for all four exact layouts:
allocator hooks, flash/RAM accounting, core 1 BSS stack, stack guards, and
the pinned CYW43 frame measurement. Reuse valid identity-bound evidence;
do not rebuild or repeat unrelated checks.

R1.2 — Inhibited shared-path regression
Run the revised N profile for 180 seconds with USB/health observation for
240 seconds. Require target time.local resolution and synchronized clock
before admitting the interval. Do not repeat the entire historical A2 suite.

R1.3 — Physical allocation feasibility
On the exact 138 MHz physical image, run warm N180/USB240 and determine the
largest necessary successful allocation.

Only while authoritatively idle, inactive, and unowned, perform exactly:
  required size → capacity + 1 → required size

Expect success, one intentional NULL result, then success. Verify allocation
release, no TLS allocation failure, no unexpected allocation failure, and no
fault/reset. Record the successful size as a demonstrated lower bound on
allocatable block size, not an exact fragmentation measurement.

R1.4 — Same-boot retention and recovery
On the same physical boot, using a persistent observer and comparable warm
state, run:
  Q360 → controller180/USB240 → N300/USB360 → Q360

Keep terminal history empty. Require the defined retained-memory difference
to be at most 1,024 bytes. No allocation failures beyond the single admitted
intentional probe failure are allowed.

If subsequent workload needs a larger successful allocation than the tested
probe size, leave the feasibility gate open rather than claiming coverage.
Do not compare a fresh reboot against warm state as evidence of a leak.
Do not add a 3,660-second wait for terminal history that was never created.

R1.5 — Measurement cost and stack integrity
Measure allocation sampling overhead, core 0 stack scanning/core 1 probing,
USB round trips, and host load for the exact image and clock. Account for
overlapping measurements without summing them as independent elapsed time.
Distinguish canary lower bounds from MSPLIM guard evidence.

Preserve the existing frozen overhead thresholds and definitions. Do not
choose thresholds after seeing the results.

COMMON LOAD AND ACCEPTANCE RULES

Use the revised N profile:

N180:
  initialize at 0 seconds;
  refresh at 20, 40, 60, 100, 130, 160;
  reload at 90.

N300:
  initialize at 0 seconds;
  refresh at 30, 70, 110, 190, 230, 270;
  reload at 150.

Initialize/reload each performs these four sequential GETs:
  /
  /api/v1/capabilities
  /api/v1/status
  /api/v1/config

Each interval contains eight actions, fourteen GETs, and six explicit
refreshes. Do not add recurring CSS/JS traffic from the legacy S profile.

Require action-start lateness ≤15 seconds, each fresh HTTPS request including
handshake ≤15 seconds, and each complete four-request page action ≤60 seconds.
All actions must finish within their interval.

Use the actual production persistent session:
  idle STATUS offered at 1 Hz;
  successful count ≥ interval seconds minus 2;
  maximum start gap 2 seconds;
  native SSL-write-entry-to-response ≤5 seconds.

Require INFO at 1 Hz with maximum gap 2 seconds, USB STATUS/health at 0.2 Hz
with maximum gap 6 seconds, and individual USB round trips ≤5 seconds.

Verify both physical stacks’ 16 KiB allocation, 4 KiB MSPLIM reserve, valid
guards, and zero faults. Preserve the 32,768-byte general heap reserve.
Do not double-count the TLS subset; account for static lwIP storage separately.

Bind every result to device, boot, image hashes, clock, listener variant,
configuration, observer, and measured interval. Preserve all other current
ledger gates without silently weakening them.

At 138 MHz, a 16,384-word/524,288-sample full block lasts approximately
3,799,188.406 ns; the 75% deadline is 2,849,391 ns. These are clock-bound
references, not R1 refill/launch acceptance measurements. Mark other physical
clocks, including 132 and 150 MHz, untested.

BOUNDED FIXTURE AND RESTORATION

Prepare code, tests, image checks, and packet artifacts before starting timers.

Authorized temporary host changes:
  pause the Wi-Fi recovery timer;
  use wlan0 as the isolated AP;
  use wlan2 as its independent client;
  add/remove the temporary chrony ACL;
  provide temporary fixture-scoped time.local mDNS exposure if required.

Preserve Ethernet management, wlan1, installed WsprryPi, GPSDO settings,
permanent time.local services, and unrelated services/radios.

Expected hardware execution is approximately 35 minutes. Bounds:
  device work: 45 minutes, plus 10 minutes reserved for restoration;
  host fixture: 70 minutes, plus 10 minutes reserved for cleanup;
  absolute host-fixture lifetime: 80 minutes.

These are maximum cleanup bounds, not required soak durations. Use independent
supervision. Start device work only with enough host lifetime remaining for
the full device allowance and cleanup margin. Do not extend deadlines.

Use a fresh attempt directory and packet. Preserve both prior failed packets,
results, logs, and reconciliation history. Do not rerun or overwrite them.

The last recorded cumulative configuration-write count is 24/32. Reconcile
it with current evidence; never reset it. Normal setup/restoration should
consume two writes. Reserve restoration before every write and preserve
remaining campaign budget.

Use exclusive serial-specific endpoint access. Unexpected boot, ownership,
output, transport, or identity changes stop dependent operations. Never infer
inactive output from disconnects, reboot reports, missing ACKs, or labels.

Restore Pico A’s verified original image/configuration using the guarded
procedure and authoritative state checks. Keep Pico B read-only. Verify both
boards and host restoration afterward, including continued permanent
time.local service and normal LAN access.

No RF jobs are authorized by this R1 packet or needed for its acceptance.

VALIDATION, ADVERSARIAL REVIEW, AND ITERATION

Use the repository’s documented commands. Validate affected runner,
configuration, mDNS/NTP admission, packet, cleanup, and auditor behavior
before hardware execution.

Test meaningful failure paths: unreachable/wrong mDNS address, invalid or
unsynchronized NTP, identity changes, expired budgets, cleanup ownership,
allocation-probe misuse, and false acceptance of incomplete intervals.

Preserve compatibility with historical evidence and legacy profiles.

After execution and restoration, perform an adversarial review of:
  scope and authority;
  exact image/clock/boot binding;
  mDNS and NTP admission evidence;
  interval completeness and timing;
  allocation and stack claims;
  observer effects and accounting;
  restoration and permanent-service preservation;
  failure retention and honest acceptance counts.

Fix actionable in-scope issues, rerun affected checks, and review again until
no actionable in-scope findings remain. Preserve each failed attempt. Any
additional hardware attempt must fit the original lifetime, write budget,
and finite scope; otherwise report the remaining gate without extending it.

Do not manufacture a pass to close a review finding. A blocked hardware gate
may remain blocked even when the implementation and documentation are sound.

ARTIFACTS, COMMIT, PUSH, AND REPORT

Update the durable R1 prompt, attempt packet, result, review, acceptance
ledger, and relevant development documentation. Preserve historical failures
as separately identifiable evidence. Keep private captures, credentials, and
firmware outside source control.

State explicitly whether R1 closed and which exact configuration its evidence
covers. Keep the full Phase 11.5 accepted-configuration list empty unless all
required families actually support acceptance.

Commit scoped changes in each repository actually changed and push to its
configured remote branch. Do not force-push or include unrelated work.
Verify the resulting local/remote commit identities.

The final report must include:
  R1 assertions closed, expressed as X of 5;
  overall family count, expressed as X of 6;
  exact accepted or still-pending firmware/clock scope;
  remaining failures or blockers;
  tests and adversarial review results;
  board, configuration, and host restoration status;
  permanent time.local verification;
  cumulative configuration writes;
  artifact paths, commit hashes, push status, and worktree state.

Do not claim Phase 11.5, RF qualification, or SDR frequency calibration from
R1 memory tests or GPS/PPS-backed NTP evidence.
