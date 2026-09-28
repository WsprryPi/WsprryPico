# Phase 12 local-network WTP source review

Status: **SOURCE CANDIDATE; PHYSICAL AND WSPRRYPI CLIENT ACCEPTANCE OPEN**
(2026-09-28).

## Selected behavior

Infrastructure Wi-Fi, an IPv4 address and an accepted SNTP observation make
WTP/TCP available automatically. There is no client-certificate enrollment.
The existing engineering profile keeps mTLS. The consumer profile reuses its
validated device certificate. A Wi-Fi-only profile creates a temporary
per-boot device TLS identity after SNTP, with no profile-journal mutation.
Both LAN modes carry the unchanged WTP/1 stream through TLS 1.3 and ALPN
`wtp/1` to the same `JobService`; they reject SoftAP WTP and browser HTTP.
The setup page's editable time server remains the SNTP source, defaulting to
`pool.ntp.org`. The journal source label remains static; USB `INFO` reports
`lan_wtp_ready` separately.

The separate WsprryPi client currently requires CA, client-certificate and
private-key files. It cannot yet use this admission mode automatically. Its
client policy and configuration need a separately authorized change in the
WsprryPi repository. The Wi-Fi-only certificate changes on each boot, so a
client cannot rely on a stable certificate pin for that source.

## Checks

- The exact pinned Pico SDK 2.3.1 checkout and Arm toolchain cross-built the
  standard RF-inhibited `WsprryPico` target. This was a build, not a flash.
- The pinned Mbed TLS host driver exercised both original mTLS and the new
  certificate-free client mode. The latter completed WTP `HELLO` and `STATUS`
  over TLS 1.3/ALPN and rejected HTTP.
- The host mDNS test covered late configuration of the stable hostname, and
  the existing consumer TLS generator test covered on-device certificate
  generation/validation with the host adapters.
- The focused CTest selection `mdns_tests`, `network_tls_tests`,
  `network_local_wtp_tests` and `consumer_tls_generator_tests` passed 4/4.
- `scripts/validate_wtp_contract.py`, `clang-format --dry-run --Werror` on
  changed C/C++ files and `git diff --check` passed.

Host and cross-build evidence cannot establish target heap/stack margin,
station association, SNTP timing, live listener admission or WsprryPi
interoperability. No hardware operation was performed for this change.

## Adversarial assessment

| Finding | Disposition |
| --- | --- |
| A consumer journal has TLS material, but the old boot graph never supplied it to the listener. | Supplied stable views of the committed TLS material; post-SNTP validation gates start. |
| A Wi-Fi-only journal has no TLS material or configured station mDNS name. | Generate temporary material after SNTP, configure the already derived hardware hostname, and test late mDNS and TLS-credential configuration. |
| The old listener-status call treated pending Wi-Fi-only credentials as a permanent mDNS identity failure before the TLS generator could run. | Keep mDNS identity healthy while network-only TLS is pending; report listener readiness separately. |
| A network-local no-client-certificate listener could expose the existing browser API or SoftAP. | Require ALPN `wtp/1` and reject SoftAP connections. A real TLS host test checks the HTTP rejection. |
| A generated certificate can be briefly future-dated relative to SNTP, or a transient listener start can fail. | Retry the idle start at a bounded 30-second interval while valid Wi-Fi and time remain available. |
| Reusing `provisioning_source` as a readiness flag would change its meaning. | Keep the journal-source label and report a separate live `lan_wtp_ready` field. |

Second assessment found no further source-level blocker in this bounded Pico
slice. Physical behavior, resource margins and the independent WsprryPi client
remain open as stated above.
