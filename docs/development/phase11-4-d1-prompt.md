# Phase 11.4 D1 execution prompt

Complete actual DHCP address-change acceptance, beginning from clean Pico devel
`bf6d000e821014724aecbf9eb4bdad41775d8db4`. Read README, CONTRACT, architecture,
the physical acceptance procedure and prior D1–D3 results. Preserve existing work
and failed attempts. Keep host simulations, physical inhibited observations and
RF qualification distinct. No additional board is needed for D1.

Use only Pico 2 W serial `0BF4B4AEC9FFB344`, attached to wspr5, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, standard inhibited simulator image. Refresh
Console INFO and one persistent USB WTP HELLO/CAPS/STATUS session. Require
matching deployment identity, healthy storage, disabled schedules and explicit
inactive/unowned state before each idle Wi-Fi control. Record firmware, boot,
engine, current IP/MAC, certified name, certificate fingerprint and saved state.
No firmware flash, trust import, GPIO or RF action is part of the baseline plan.

The specific D1 execution request and existing all-tests authorization cover the
following narrowly scoped test. The original handoff prohibits reserving an IP
to avoid address-change acceptance; the later plan's blanket prohibition was
overbroad. Use a temporary reservation only to cause a real DHCP transition, and
remove it afterward. It must never become a normal operational dependency.

1. Inspect the signed-in Orbi RBR850 at `192.168.1.1`. Verify current DHCP pool,
   reservations and attached clients. Before use, check proposed `.247` for an
   existing assignment/reservation and perform bounded duplicate-address probes.
   Do not treat lack of an ARP reply alone as proof that an address is free.
   Stage only `88:A2:9E:0A:60:DF` -> `192.168.1.247` with an explicit temporary
   test label. Preserve all unrelated entries, LAN/subnet/pool and AP policies.
   Stop if the router requires a global restart or disruptive unrelated change.
2. Before changing the lease, record Mac and Linux resolution of the current
   address, verified HTTPS and actual isolated WsprryPi startup at the hostname.
   Hash the exact production binary/source/config/client certificate. Retain
   observation-only TLS instrumentation if needed to prove no LOAD/ARM. With the
   authorized bounded service pause, verify provider output disabled, run the
   candidate with Transmit false and Enable on Boot Never, then restore the
   installed service and verify its binary/configuration hashes unchanged.
3. Begin bounded native Mac resolver and Linux packet/USB observations. Apply
   the one-device reservation, verify its exact saved values, then idle Console
   WIFI OFF/ON to acquire a real new lease. Retain DHCP transaction/client-MAC
   evidence, USB current address, same-name probing and cache-flush announcement
   at the new address. Record any unobservable unicast DHCP replies explicitly.
   Verify the device no longer advertises its old address after transition;
   distinguish stale peer caches from new device advertisements.
4. Measure Mac/Linux resolution convergence without hosts or resolver-cache
   changes. Verify the same CA, DNS identity, server fingerprint, WTP device and
   boot at the new IP. Reload actual Chrome at the unchanged hostname; a Python
   HTTPS read cannot substitute for a Chrome result. Reconnect the real isolated
   production client using the same hostname configuration, capture its resolved
   address and authenticated identity, and prove zero LOAD/ARM and independent
   inactive/unowned USB status. Preserve unknown output on failed observations.
5. Remove only the test reservation and verify the original reservation table.
   Reacquire ordinary DHCP with an idle Wi-Fi cycle, discover the actual resulting
   address, and verify peers/TLS/device again. Do not force the old IP through
   static configuration. Restore Wi-Fi and the installed service on exceptions;
   report router cleanup failures and retain the exact rollback action if UI
   access disappears. Bound captures and service pauses, retain all attempts,
   and keep credentials/captures/generated artifacts owner-only and out of Git.

Repair actionable in-scope source or evidence-tool defects. Perform adversarial
review of actual lease origin, packet source/TTL/identity, old-address silence,
client hostname usage, certificate/device equality, no hidden jobs, stale-state
handling, capture completeness and rollback. Reject missing or altered evidence.
Rerun affected checks, fix findings and repeat the assessment. Update prompt,
results, private artifact hash index, joint matrix and development/review entry
points. Do not turn unavailable observations into PASS or erase earlier failures.
Review the staged diff, commit and push each changed authorized repository to
origin/devel, verify clean parity, then report D1's actual result and the remaining
Phase 11.4 table. Keep D2 repeatability, D3, E1 and overnight stability separate.
