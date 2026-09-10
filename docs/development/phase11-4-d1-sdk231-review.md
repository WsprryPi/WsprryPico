# D1 orientation review at f11e216

Reviewed before D1 execution on 2026-09-10: project contracts, latest three
commits, `PicoNetwork`, mDNS state machine and lwIP wrapper, stable identity,
TLS admission/deadlines, and current component/adapter acceptance tests.

| Capability | Current implementation | Evidence and implication for D1 |
| --- | --- | --- |
| DHCP and link servicing | SDK CYW43/lwIP performs DHCP; core-0 foreground polling services network timers and retries association at 30-second intervals | D1 needs an actual server-assigned new address; Wi-Fi reconnection alone often preserves the lease |
| Address-change discovery | Extended netif callback quiesces mDNS; next adapter poll removes/re-registers the same label and probes the new address | State-machine and wrapper packet tests exist, but the adapter test did not exercise their automatic composition |
| Stable identity | Boot reads station MAC; default is `wsprrypico-` plus the final three MAC bytes; DNS certificate identity is independent of IP | Keep the same MAC, name, CA, certificate fingerprint and WTP device across the lease change |
| TLS and application access | TLS 1.3, mutual authentication, hostname/fingerprint checks, two application contexts, bounded handshake/HTTP lifetimes | Address availability alone does not mean TLS clock readiness or complete peer recovery |
| Resource and retransmission limits | Four TCP PCBs, bounded queues; lwIP retransmissions remain enabled; application deadlines can terminate requests | Ordinary packet loss is expected; observe failed attempts and recovery timing without assigning every failure to the bridge |
| Output authority | USB reference transport and shared job service; standard image remains inhibited | Require independent current USB state; a disconnected client does not prove inactive output |

## Recent changes

- `dbf1d86`: boot-derived short names and bounded two-board identity/trust evidence.
  It does not implement end-user provisioning or qualify a new DHCP address.
- `ea053f8`: pinned SDK 2.3.1 fixes RP2350 event/timeout waits; BSSID-only diagnostic
  replaces the failing RSSI query. B2 delivery failures remain recorded.
- `f11e216`: D2 observer waits for clock readiness and strictly audits the current
  shutdown interval. Four observed shutdowns had no reset; only one complete case
  passed. No firmware changed in that D2 slice and no causal watchdog closure follows.

## Findings and execution decisions

1. **Integration coverage gap:** component tests manually remove/re-add mDNS after
   a simulated address change. Add a hardware-free test using the actual
   `PicoNetwork::poll` with pinned lwIP, changing the netif address while the link
   remains up. Check suppression during reprobe, unchanged hostname, new A records,
   disappearance/reacquisition of an address and no radio disable. This qualifies
   software composition only, not DHCP server behavior or physical radio delivery.
2. **Stale physical runner assumptions:** the earlier private D1 runner embeds an
   old firmware revision, old controller location and 45-second immediate peer
   expectations. It must not be reused unchanged. Only prepare a current runner
   if router reassignment admission succeeds; use current identity and bounded
   clock-aware recovery without erasing original failures.
3. **Missing physical prerequisite:** earlier Orbi Apply returned HTTP 400. Verify
   the supported router operation before any new OFF/ON. A displayed reservation
   is insufficient. Stop dependent work if no safe effective reassignment exists.

No confirmed firmware DHCP defect was found in this orientation review. Do not
change firmware, increase timeouts, replace DHCP with a static address, or blame
AP forwarding solely to manufacture a D1 result. The
[execution prompt](phase11-4-d1-sdk231-prompt.md) preserves the full physical gate.

## Additional review and reassessment

Read-only review of the sibling WsprryPi checkout at
`89f23e5d10c8a46ead9f37c7cefa8867280ac4df` confirms `TlsStream::begin_open`
closes prior state and starts a fresh hostname lookup; connection establishment
uses returned addresses with a separate expected TLS identity. This is source
evidence, not a new physical production-client acceptance result.

Review of the new integration test found that its first packet observer inspected
only the first answer record. It now uses the pinned lwIP DNS name parser and
checks every answer, authority and additional record in response packets, with
bounds and cache-flush validation. This prevents an additional stale A record
from escaping the address check. The original software parser was not changed.

Two private, compiled implementation mutants are rejected at the new assertions:
a cached address with suppressed change notification cannot pass reprobe, and
retaining a nonzero address after address loss cannot pass withdrawal. An initial
mutant compile failure due to an unused variable was retained and not counted as
a behavioral rejection; the corrected generator produced both failing runtime
mutants. Seven relevant CTest targets and formatting checks pass after the final
changes. Final reassessment leaves no actionable finding in this test/document
slice; D1's physical lease-change gate remains independent.
