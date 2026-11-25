# Engineering network identity

This contract describes certificate-based engineering deployments. Consumer port-80 access and editable saved names follow [consumer access](consumer-lan-access.md) and [hostname management](hostname.md). Discovery remains a destination hint, not identity or trust.

## Four independent identities

| Value | Source and use |
| --- | --- |
| TCP destination | Fresh system resolution of configured host, or explicitly configured IP; IPv4 Pico listener |
| TLS reference identity | Explicit configured expected identity, otherwise configured host; never reverse lookup or discovery-derived trust |
| HTTP authority | Canonical TLS reference identity plus listener port; server admits its certified deployment hostname and current IPv4 only |
| Device identity | Stable 32-character lowercase hexadecimal member ID. Management checks it with the current boot and carrier context |

Normal engineering deployment uses DHCP and `wsprrypico-<last-six-MAC-hex>.local`. The 17-character label comes from the station MAC read at Wi-Fi initialization. Name conflicts latch without automatic suffix changes. mDNS supplies an address hint. Verify the configured DNS SAN and the full member device ID. DHCP reservation is optional.

Hostnames are one 1–63-byte ASCII LDH label followed by `.local`, with no leading or trailing hyphen. Input accepts ASCII case and one final root dot; canonical form is lowercase without that dot. Wildcards, Unicode, empty labels, underscores, extra suffixes, whitespace, escapes, and authority syntax are rejected. The client may retain broader existing DNS host support; it applies equivalent DNS case/root dot canonicalization at connection time and preserves saved/draft spelling.

## Deployment source of truth

The server bundle's public `deployment.json` schema 1 carries `device_id`, `hostname`, `ipv4_sans`, and `certificate_sha256`. The certificate helper derives the default label from the observed `--mac-address`, or accepts an explicit `--hostname` alias. `--device-id` remains the full independent board identity. Firmware reports the observed `station_mac` and its derived `stable_hostname` after a valid read. Engineering names are credential-bound. A deliberate alias change requires a new bundle and explicit rebuild and reflash. The full device ID remains stable.

Build validation compares the exact DNS and IP SANs, SHA-256 fingerprint, chain, server purpose, validity, and private key with the manifest. The exact DNS SAN is required for a deployment hostname. Firmware verifies that the manifest's device ID matches the hardware before using the certified hostname.

Legacy manifest-less IP-only bundles remain buildable if their actual credentials validate and contain IP SANs but no DNS SAN. They have no mDNS deployment identity. Migrate by issuing a new hostname bundle under the existing per-device CA and rebuilding/reflashing explicitly. Existing client identities remain usable while valid. Runtime upload, ACME, automatic trust installation are unavailable through this deployment tool.

A DHCP address change does not require renewal for hostname access. Optional IP SANs support specifically listed literal-IP URLs. Explicit IP plus expected hostname connects to that IP, authenticates the configured DNS SAN, and sends the hostname HTTP authority. A literal-IP browser URL authenticates only a matching IP SAN; a hostname certificate cannot authenticate arbitrary changing IP URLs.

## HTTP policy

The server admits at most two authorities: its deployment hostname and its current IPv4, each with the configured port. Port 443 is omitted; other ports are required in canonical decimal form. No alternate/leading-zero ports, userinfo, forwarding headers, reverse DNS, arbitrary `.local` aliases, or URL syntax grant an authority. DNS case and one final root dot canonicalize before comparison.

Host and Origin are validated independently against that allowlist, then must identify the same canonical authority. Allowing hostname and IP must never allow cross-alias Host/Origin combinations. An Origin, when present on any request, must be HTTPS and same-origin; mutations require it. Duplicate headers, malformed headers, JSON intent and Fetch Metadata checks, mTLS, and no-CORS policy remain.

## mDNS lifecycle and bounded failure

Core 0 owns discovery in the CYW43/lwIP polling context on the actual station interface. Engineering HTTPS registers its hostname when its listener and IPv4 address are ready. The consumer listener can separately publish the [management service](mdns-responder.md#management-dns-sd-discovery). Successful probing permits reported advertisement. A changed address causes a cache-flush announcement and reprobe. Link loss removes stale registration. Controlled Wi-Fi disable attempts a goodbye while the link is usable.

Conflicts latch `conflict`, stop registration, and retain the configured name. Resource or initialization failures latch `failed`. Explicit idle-only disable and re-enable or reboot permits retry after the operator resolves the conflict. Discovery failures leave job ownership and execution unchanged. Recovery boots remain network-free. A wrong-board deployment requires corrected credentials.

Expose stable default hostname, configured hostname, advertised hostname (empty until active), current address, state/reason, and bounded cumulative diagnostics through INFO and the network API. The host separately reports configured target, resolved address, and last authenticated identity; failures do not imply current certificate success or inactive output.

The exact pinned responder needs narrow adapter support for nonasserting startup, complete timer/packet cleanup, and goodbye behavior. Keep upstream source immutable, retain license attribution, verify source pins, and exercise the actual responder in isolated host packet tests. Record resource costs and any deviations explicitly.
