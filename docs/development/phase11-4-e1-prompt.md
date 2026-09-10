# Phase 11.4 E1 two-board identity and trust execution prompt

Execute only E1 in WsprryPico at `/Users/lbussy/GitHub/WsprryPico`.
The user requests execution, adversarial review with repair/reassessment, and
commit/push. This authorizes E1 identification, private credential generation,
inhibited provisioning of the second Pico, bounded USB/network checks and the
necessary private host tooling. Keep all RF inhibited and schedules disabled.
Do not change the WsprryPi repository, installed service, router, other devices,
system trust stores, or the already provisioned original board as incidental work.

Read applicable AGENTS.md, README.md, CONTRACT.md, docs/architecture.md,
docs/development/README.md, phase11-4-plan.md, phase11-4-acceptance.md,
network-control.md and phase11-3-identity.md before implementation. Inspect
branch, HEAD and dirty files; preserve existing shutdown/soak work. Phase 11.4
stays open regardless of E1 outcome. Existing bounded passes remain intact.

Use Bohica-IoT for all network testing. It is a bridge providing a stable
2.4 GHz radio, not a routed network. Preserve wspr5's USB wlan1 and recovery
configuration. Do not revisit the confirmed prior power outage or run B2, D1,
D2, conflict, or soak campaigns. Check current interfaces and actual addresses;
do not assume an SSID proves AP association or packet delivery.

Original board A is Pico 2 W/RP2350, USB serial `0BF4B4AEC9FFB344`, WTP ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`, deployed alias
`wsprrypico-0a60df.local`. Its private bundle is
`config/local/network/phase11-4-fd6127d1`. Rediscover its current deployment,
engine, boot, address and certificate. The second board B is initially unknown;
inventory USB descriptors and picotool metadata before opening or flashing it.
Never select by ttyACM index, first matching device, or an ambiguous mount.
Exclude the GPSDO and SDR. Record exact serial and USB location at each transition.

Hypothesis: observed station MACs generate distinct short default names for these boards;
separate per-board CAs admit their own clients and reject the other board's
clients, independently of the TCP destination and DNS name. The original short
alias is intentional: retain its existing certificate and firmware, and test each actual certified
deployment name. Record A's historical full-ID diagnostic as old firmware behavior.
The user corrected the default during execution: update certificate tooling,
firmware diagnostics, current documentation and focused tests so the default
is always MAC-derived. Do not change the full WTP device identity.

Create a new owner-only ignored evidence directory. Record UTC, arguments,
exit status, output files and SHA-256 for every attempt. Retain failed/invalid
attempts. Keep credentials, raw captures, generated UF2s and private keys out of
Git and tool output. Use existing pinned tooling; if unavailable, prepare a
private pinned build with available dependencies. Distinguish execution or
sandbox failures from LAN/device failures.

If B has no application, build a network-disabled standard inhibited bootstrap,
verify image layout and linked DryRunEngine with no physical engine symbols,
and flash only its positively identified BOOTSEL serial. Back up existing flash
when supported before replacement; never erase journals. Obtain B's actual WTP
ID through matched Console INFO and WTP HELLO/CAPS/STATUS. Stop on identity
ambiguity, non-inhibited engine, active/unknown output, ownership or schedule.

Generate B's independent CA, server and controller/browser client bundles in a
new private directory. Read B's own MAC after bootstrap Wi-Fi initialization,
then generate its short default hostname with --mac-address and port 18443, with no
invented IP SAN. Validate manifest, chain, SAN, lifetime, fingerprint and keypair.
Build only standard WsprryPico using pinned SDK/toolchain; record source revision,
dirty scope, ELF/UF2 hashes and inhibition checks. Recheck B's identity before
BOOTSEL, program/verify by serial, and cross-check the resulting boot/deployment.
Provision only B with private Bohica-IoT credentials, DHCP, usable SNTP and
disabled scheduling. Preserve A unchanged. Never expose passwords in argv/logs.

For both boards, require deployment_identity_matches, distinct device IDs,
distinct observed MACs and short deployment names, matching
certified/configured/advertised names,
usable actual UTC, inhibited engine, empty/unowned state and output_active=false.
Record native Mac/Linux resolution of both deployed names on Bohica-IoT.
Resolver/connectivity failures remain failures, not trust rejection evidence.

Run three bounded fresh-connection rounds per board using TLS 1.3 with mandatory
certificate/hostname/time validation. Bind successful HTTPS status and WTP
HELLO/CAPS/STATUS to the expected certificate, device and boot. For each target:
verify its own CA/client succeeds; use the other board's client with the target's
correct CA/name and require an explicit certificate rejection; use the wrong
server CA and separately the wrong expected hostname and require the intended
verification error. Place successful own-client controls around negative checks.
A timeout, reset without an attributable TLS alert, DNS error or socket failure
cannot pass a trust case. At most one new diagnostic attempt follows a failed
case after a concrete explanation; preserve the original failure and stop if
the same prerequisite remains unavailable. No jobs, ownership mutations or
certificate-validation bypasses are needed for E1.

Use per-invocation trust files; no Keychain/browser CA import is required for
the E1 trust matrix. Distinguish direct TLS/browser-API observations from actual
Chrome or production-client evidence; do not repeat their previously passed
acceptance suites or imply newly obtained coverage.

Collect final independent USB state for both boards and record wspr5 wlan1 and
service/recovery state. Leave B correctly provisioned and inhibited; retain A's
boot/configuration and certificate. If a prerequisite prevents closure, report
the exact blocker without manufacturing a pass.

Adversarially review target binding, boot MAC derivation and explicit alias compatibility, bidirectional
trust coverage, validity and hostname checks, alert attribution, positive controls,
failure retention, final output authority, evidence hashes and secret exclusion.
Fix actionable findings, rerun affected checks, and repeat assessment until no
actionable issue remains or an external blocker is explicit. Publish sanitized
prompt/results/evidence and update only E1 in the joint matrix. Validate links,
JSON and whitespace; run meaningful affected software checks if code changes.
Commit only this task's files, push the current branch, verify remote parity and
report commit, tests, limitations and preserved dirty work. Reprint the same
five-item remaining-work table with E1's evidence-backed status.
