# Phase 11.4 D1–D3 execution prompt

Address DHCP reassignment, orderly discovery withdrawal and unexpected link loss
from clean Pico devel `16b54128feb4fb260f3bfb0306399d88e68e950c`. Inspect current
work and read the project contract, architecture, acceptance matrix, network
adapter, mDNS lifecycle and pinned lwIP tests. Preserve prior failed attempts.
Keep changes within Phase 11.4; read the independent Pi repository before any
necessary production-client repair. Do not change unrelated repositories.

Use only the Pico 2 W on wspr5, USB serial `0BF4B4AEC9FFB344`, WTP device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, standard inhibited simulator firmware and
certified name `wsprrypico-0a60df.local`. Refresh Console INFO, USB HELLO/CAPS/STATUS
and authenticated network status. Bind firmware, boot, engine, device, hostname,
certificate fingerprint, addresses and interfaces. Require healthy storage,
disabled schedules and inactive/unowned status before idle network changes.
Use a persistent USB session; treat unavailable network status as unknown.

1. **D1:** identify the actual router and its supported per-client lease control.
   Prepare a concrete Pico-only operation before changing the real lease. Record
   real old/new DHCP addresses and packets, unchanged certified name/CA/server
   fingerprint/device, withdrawal of the old advertisement and fresh probing
   and advertisement of the new address. Measure Mac/Linux resolver convergence,
   reload Chrome at the same hostname, and reconnect the actual isolated
   production WsprryPi client without duplicate LOAD/ARM or false inactive claims.
   Restore any temporary lease policy. A synthetic address callback, rogue DHCP
   responder, hosts edit or static-IP substitution cannot close this case.
2. **D2:** seed and observe actual Mac and Linux resolver paths; capture Pico
   mDNS packets before, during and after authorized idle Console WIFI OFF/ON.
   Hold the orderly outage through the advertised positive TTL if necessary.
   Distinguish device goodbye attempts, captured Pico TTL-zero records, peer
   removal callbacks and bounded negative lookups. Verify fresh same-name probes,
   current-address announcement, resolver recovery, authenticated reads and
   unchanged boot/configuration/schedules/watermark. Preserve counter-only or
   missing-packet failures; investigate and repair actionable implementation
   defects before retesting with a properly identity-bound candidate.
3. **D3:** use an identified, bounded Pico-only AP/link fault that leaves the Mac,
   wspr5 and unrelated clients connected. Record unexpected loss independently
   over USB, no invented successful goodbye after loss, stale peer TTL and actual
   expiry, followed by recovery and coherent address/name. For a complete finite
   inhibited job, bind original owner/job and local progress across the fault;
   reconcile authoritatively and never resubmit work on ambiguous transport loss.
   Orderly WIFI OFF is not unexpected loss. Missing selective AP/router access
   remains an explicit prerequisite, not a simulated pass.

Existing authorization covers all tests, scoped USB controls, packet capture,
Chrome reads and bounded installed-service pause/restore. Resolve missing router
identity/control information while progressing independent D2 work. Preserve
shared LAN settings, trust stores, journals, installed binaries/configuration and
unrelated hardware. Never introduce RF/GPIO operations or global AP outages.
Keep credentials, captures and generated images private and out of Git. Bound
all captures and observers; restore Wi-Fi in finally paths after authoritative
idle checks. Report cleanup failures instead of hiding them with a retry.

Run relevant portable and pinned lwIP tests and independently audit physical
packet/cache evidence. Adversarially challenge identity, timing, packet origin,
counter-versus-reception claims, capture completeness and cleanup. Fix actionable
findings, rerun affected checks and repeat the assessment. Save results, private
artifact hashes and exact remaining prerequisites, update the joint matrix and
development entry points, review the staged diff, commit and push each changed
authorized repository to origin/devel. Verify actual remote parity and print the
remaining-items table without promoting unexecuted or failed cases to PASS.
