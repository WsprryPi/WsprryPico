# Phase 11.3 shared network identity contract

Status: accepted implementation contract, 2026-09-08. WsprryPico owns this
application-level contract; normative WTP/1 is unchanged. Initial reviewed inputs:
Pico `a34a9a4342013d41379242f1e456ca3e3760b8db`, Pi `07a7a8b` (both clean devel,
origin refreshed). See [execution and acceptance](phase11-3-plan.md).

## Four independent identities

| Value | Source and use |
| --- | --- |
| TCP destination | Fresh system resolution of configured host, or explicitly configured IP; IPv4 Pico listener |
| TLS reference identity | Explicit configured expected identity, otherwise configured host; never reverse lookup or discovery-derived trust |
| HTTP authority | Canonical TLS reference identity plus listener port; server admits its certified deployment hostname and current IPv4 only |
| WTP device identity | Existing stable 32 lowercase hexadecimal device ID; HELLO/device/boot/session checks remain independent |

Normal deployment uses DHCP and `wsprrypico-<last-six-MAC-hex>.local`. The label
is 17 ASCII bytes, derived from the station MAC read at Wi-Fi initialization,
never a boot ID, USB serial, WTP-ID truncation or DHCP address. Suffix collisions
remain subject to ordinary conflict handling; no automatic suffix is added. No DHCP reservation is required. mDNS supplies address information,
not trust. A client must verify the configured DNS SAN and the WTP device ID.

Hostnames are one 1–63-byte ASCII LDH label followed by `.local`, with no leading
or trailing hyphen. Input accepts ASCII case and one final root dot; canonical
form is lowercase without that dot. Wildcards, Unicode, empty labels, underscores,
extra suffixes, whitespace, escapes and authority syntax are rejected. The client
may retain broader existing DNS host support; it applies equivalent DNS case/root
dot canonicalization at connection time and preserves saved/draft spelling.

## Deployment source of truth

The server bundle's public `deployment.json` schema 1 carries `device_id`,
`hostname`, `ipv4_sans` and `certificate_sha256`. The certificate helper derives
the short default hostname from required observed `--mac-address`, while
`--device-id` remains the full independent board identity. Without a MAC or
explicit `--hostname`, issuance fails; full-ID names remain supported only as
explicit aliases. Firmware exposes the observed `station_mac` and derives the
same short `stable_hostname` at boot after driver initialization. Both diagnostics
are empty until a valid read; they never override the certified configured name.
An explicit `--hostname` is a build-time deployment alias. There is no runtime hostname editor or stored-config
migration. A deliberate alias change requires a new bundle/certificate and an
explicit local build/reflash. It does not change the board's WTP identity.

Build validation compares the actual certificate's exact DNS/IP SANs, SHA-256
fingerprint, chain, server purpose, validity and private key with the manifest.
No CN or wildcard substitutes for the exact deployment DNS SAN. The resulting
hostname/device ID are embedded with credentials, and firmware must reject
hostname operation when the embedded device ID differs from its actual WTP ID.
An independently supplied name cannot override the manifest.

Legacy manifest-less IP-only bundles remain buildable if their actual credentials
validate and contain IP SANs but no DNS SAN. They have no mDNS deployment identity.
Migrate by issuing a new hostname bundle under the existing per-device CA and
rebuilding/reflashing explicitly. Existing client identities remain usable while
valid. Runtime upload, ACME, automatic trust installation and provisioning remain
outside this slice.

A DHCP address change does not require renewal for hostname access. Optional IP
SANs support specifically listed literal-IP URLs. Explicit IP plus expected
hostname connects to that IP, authenticates the configured DNS SAN, and sends the
hostname HTTP authority. A literal-IP browser URL authenticates only a matching
IP SAN; a hostname certificate cannot authenticate arbitrary changing IP URLs.

## HTTP policy

The server admits at most two authorities: its deployment hostname and its
current IPv4, each with the configured port. Port 443 is omitted; other ports
are required in canonical decimal form. No alternate/leading-zero ports, userinfo,
forwarding headers, reverse DNS, arbitrary `.local` aliases or URL syntax grant
an authority. DNS case and one final root dot canonicalize before comparison.

Host and Origin are validated independently against that allowlist, then must
identify the same canonical authority. Allowing hostname and IP must never allow
cross-alias Host/Origin combinations. An Origin, when present on any request,
must be HTTPS and same-origin; mutations require it. Duplicate headers, malformed
headers, JSON intent and Fetch Metadata checks, mTLS and no-CORS policy remain.

## mDNS lifecycle and bounded failure

Only core 0 and the existing CYW43/lwIP polling context own discovery. Use the
pinned maintained responder against the actual station netif. IPv4 only, no
DNS-SD service enumeration or TXT credentials. Register/probe only with a usable
address and a valid hostname-enabled listener deployment. Successful probing
permits reported advertisement. Address change replaces records with cache-flush
announcements and reprobes; link loss removes stale registration. Controlled
Wi-Fi disable attempts a goodbye before losing the link. Never report a goodbye
as delivered after link loss (a send attempt is not receiver evidence).

Conflicts latch `conflict`, stop registration and never auto-rename. Resource or
initialization failures latch `failed`. Normal polling does not repeatedly retry
latched failures. Explicit idle-only disable/re-enable or reboot may retry the
same certified name after the operator resolves the conflict. Discovery failure
does not reset TLS/WTP ownership, claim inhibition, or interrupt a finite job.
Network-off and recovery boots remain network-free. A wrong-board deployment is
an identity failure and cannot be cured by a retry.

Expose stable default hostname, configured hostname, advertised hostname (empty
until active), current address, state/reason and bounded cumulative diagnostics
through INFO and the network API. The host separately reports configured target,
resolved address and last authenticated identity; failures do not imply current
certificate success or inactive output.

The exact pinned responder needs narrow adapter support for nonasserting startup,
complete timer/packet cleanup and goodbye behavior. Keep upstream source immutable,
retain license attribution, verify source pins, and exercise the actual responder
in isolated host packet tests. Record resource costs and any deviations explicitly.

## Standards and evidence

[RFC 6762](https://www.rfc-editor.org/rfc/rfc6762) informs probing, conflict,
cache-flush and goodbye behavior; [RFC 9525](https://www.rfc-editor.org/rfc/rfc9525)
provides the reference-identity and SAN verification rules. No service browsing
is added. Packet/lifecycle tests, injected resolver tests, actual TLS tests,
system NSS resolution and physical Pico acceptance are separate evidence classes.
Loopback name injection proves neither operational LAN mDNS nor Linux NSS setup.
