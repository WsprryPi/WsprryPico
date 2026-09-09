# Phase 11.4 D3 execution prompt

Execute unexpected Wi-Fi link-loss acceptance for the specified Pico from Pico devel
`36180a24dbe5042a23644646a50051df23066982`. Read README.md, CONTRACT.md,
docs/architecture.md, the physical acceptance procedure, current joint matrix
and D1/D1–D3 results. Consult the later
[D3 Orbi research](phase11-4-d3-orbi-research.md) before choosing the fault. Preserve existing work and failed observations. Keep
physical inhibited results, host tests and RF qualification separate.

Use only Pico 2 W / RP2350 serial `0BF4B4AEC9FFB344` on wspr5, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, certified hostname
`wsprrypico-0a60df.local`. Refresh Console INFO and persistent USB WTP
HELLO/CAPS/STATUS, actual firmware/deployment identity, engine, boot, saved state,
clock, link status, mDNS state/counters, address and resource counters. Require
standard inhibited firmware, healthy storage, disabled schedules and explicit
inactive/unowned state before initial test admission. Use the previously
approved CA and clients; do not flash firmware or import credentials for this
baseline. A boot change, disconnect or failed network read never proves inactive
output.

The specific D3 request and existing all-tests authorization cover the bounded
Pico test and read-only peer/USB/capture observations. A physical fault requires
an available selective mechanism. Ask whether the operator can temporarily
shield only the insulated Pico in a metal container, leaving USB connected, or
has an actual per-station radio-disconnect control. Prepare recording before
requesting application of the fault. Blocking Internet access, orderly Console
WIFI OFF, stopping a client, dropping TCP, synthetic mDNS removal and simulated
callbacks do not establish unexpected Wi-Fi loss. The user subsequently authorized a brief Bohica-IoT outage. That permits
temporarily clearing and restoring only Enable IoT Network after recording is
ready. The user subsequently confirmed Ethernet was unavailable and explicitly
accepted possible loss of both wireless management paths. Use detached, locally
fsynced logging on wspr5 and a separate bounded Mac observer; retain any gaps. Preserve its name, credentials
and 2.4 GHz band selection. Do not disable another
SSID, AP, satellite or LAN; do not change credentials, isolation or unrelated
clients. If the selective mechanism is unavailable, record the physical gate as
blocked and finish the independent source/evidence preparation.

1. Establish actual Mac and Linux hostname resolution and certificate-verified
   HTTPS. Bind the server certificate, DNS identity and WTP device/boot. Preserve
   existing Chrome failures separately. Begin bounded native Mac dns-sd callbacks
   through a PTY, Linux resolver samples and Pico-related mDNS capture. Seed a
   positive A record and capture its source MAC, address, cache-flush bit and TTL.
   Derive expiry from the last observed positive answer, not from an assumed
   fixed TTL or the operator's wall-clock estimate. Keep each host's timing local;
   do not claim subsecond cross-host latency from unsynchronized timestamps.
2. Keep one USB observer session alive throughout the fault. For the finite-job
   subcase, check CAPS and actual clock admission, then submit exactly one complete
   inhibited job with an explicit owner/job ID and start lead. Observe Running
   before asking the operator to apply the shield/disconnect. Limit the job to
   the advertised maximum duration. Never falsify UTC, loosen admission limits,
   change schedules or submit another job after an ambiguous response.
3. Detect real unexpected loss from Console link_status while Wi-Fi remains
   enabled and no disable request was issued. Require same boot and continued USB
   responsiveness. Record mDNS withdrawal state and goodbye counters separately
   from packets. Capture absence of a successful Pico goodbye after the loss as
   a bounded receiver observation, not proof of all radio transmissions. If the
   shield only blocks traffic while link status remains up, retain that outcome
   as insufficient for D3; do not rename it a link loss.
4. Hold the verified selective outage through the last positive record's TTL plus
   a bounded observation margin (normally 150 seconds for a 120-second A TTL).
   Record Mac removal and Linux negative lookup outcomes, distinguishing timeout
   from a completed negative answer. Record any Mac/wspr5 management interruption without assuming continuity. Observe the same finite job progressing locally and reaching its
   terminal state during loss. Apply the WTP contract's lease-expiry rules:
   ownership persists through Armed/Running, then may release at terminal expiry.
   Do not require an expired owner to remain forever or interpret release as a
   duplicated job. Retain terminal evidence before any cleanup mutation.
5. Remove shielding or restore the approved IoT enable/band controls. Observe
   automatic link recovery, current DHCP address, same certified hostname,
   probing/announcement, peer convergence and authenticated status for the same
   boot/device. Do not assume the address stays fixed. Allow the existing bounded
   reconnection cadence; report timeout as failure. An additional orderly Wi-Fi
   cycle may restore an idle board under prior authorization, but that recovery
   must be separate from automatic D3 acceptance and must not erase its failure.
6. Bound operator readiness, fault detection, TTL hold and recovery separately;
   keep each recorder bounded to ten minutes. Record the actual outage duration
   and any gap if operator restoration outlasts the recorder. Stop observers and capture in
   finally paths. Ensure the operator removes shielding on any error or timeout.
   Reconcile authoritative USB output/owner/job state before cleanup. Preserve
   journals, station/schedule settings and watermark; release only owned terminal
   work or use the already authorized trusted Console recovery when required.
   Verify Wi-Fi enabled, installed service/provider unchanged and no residual
   reservation, access block or test process. Report any unresolved cleanup.

Review portable mDNS and pinned lwIP link-down behavior, particularly teardown
without goodbye, pending probe timers, same-name recovery and resource reuse.
Run relevant existing tests; fix actionable defects and add behavior-focused
regressions where justified. Do not introduce a speculative firmware workaround
or use a test-only image as acceptance of the installed standard image.

Adversarially assess the actual evidence: identity and boot continuity, real
link loss versus traffic filtering, native cache seeding/removal, last-answer TTL,
packet source and capture drops, finite-job owner continuity and terminal lease
rules, no duplicate LOAD/ARM, automatic versus assisted recovery and exact
cleanup. Reject missing, altered or contradictory evidence. Repair findings,
rerun affected checks and perform another assessment. Unavailable physical
observations remain open, irrespective of passing host tests.

Save a result and private-artifact hash index, update the joint matrix and review/
development entry points, and retain the original prompt and failures. Keep
credentials, captures and generated artifacts out of Git. Review the staged
diff, commit and push the authorized Pico changes to origin/devel, verify clean
remote parity, then report exact results and the remaining Phase 11.4 table.
The independent WsprryPi repository is unchanged unless a concrete, requested
production-client repair requires separate scoped work.
