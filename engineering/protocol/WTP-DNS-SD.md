# WTP DNS-SD discovery profile

Status: implemented in WsprryPico for public beta. This document defines the
discovery profile for the device-neutral [WTP/1 protocol](WTP.md).
It does not change WTP frames, USB CDC, TCP admission, or transmitter authority.

## Service type and scope

WTP means **WsprryPi Transmitter Protocol**. WsprryPico uses the project-defined
service type `_wtp._tcp.local.` and TCP port 31417 as its default. These values
are not reserved for exclusive WTP use.

The default port supports direct WTP/TCP connections when DNS-SD is unavailable,
such as on routed or multicast-filtered networks or in manually configured
headless installations. A stable default also permits common firewall rules
without per-device port coordination. TLS and Plain LAN bindings use the same
project default; each listener may use another configured port.

A DNS-SD browser on a local link browses `_wtp._tcp.local.`. The name describes
the WTP service, not WsprryPico hardware; another WTP server may use the same
service type. This profile covers mDNS on operational local links. It does not
specify discovery across routed links. WsprryPico advertises only on its
infrastructure station link, never on its provisioning SoftAP.
Multicast is used only by mDNS discovery on those links; WTP control traffic
uses the discovered TCP endpoint.

Each advertised instance represents one active WTP/TCP listener and one
explicitly selected TCP binding. If an implementation supports both TLS and
Plain LAN listeners under its applicable
[WTP transport contract](WTP.md#13-transport-bindings-and-trust),
they need separate instances with their own SRV ports and TXT binding values.
Discovery alone does not make Plain LAN a conforming binding.
The instance label is a user-facing name; clients must not treat it as a
durable device identifier.

## Advertisement lifecycle

An implementation of this profile advertises an instance only
on an operational interface where its WTP/TCP listener is actually bound and
admitting connections, after its product-specific readiness gates pass. It
withdraws the instance when the listener stops, the interface or address
is lost, or admission closes. WsprryPico must not publish its WTP listener on
SoftAP. A cached DNS-SD result may outlive withdrawal, so a client must handle
failed connections and remove stale candidates from its live
discovery list. An advertisement says nothing about RF readiness, job ownership,
clock quality, or permission to transmit; WTP `HELLO`, `CAPS`, and `STATUS`
remain the sources for those facts.

## Resolution and connection

Resolve the selected instance's SRV record, then resolve its target hostname
and connect to the **SRV port**. TCP port 31417 is the project default for
direct connections without DNS-SD. This default does not override a discovered
SRV port, and a WTP listener may use another configured port. Read the TXT
record before choosing the explicitly supported binding below.
The client must not silently try the other binding after a connection,
authentication, ALPN, or WTP failure.

DNS-SD is a way to find candidates, not to authenticate them. A TLS client must
still validate the device-specific server identity and use TLS 1.3 with ALPN
`wtp/1` as required by the selected WTP binding. Where an applicable WTP
contract permits Plain LAN, a client uses raw WTP/1 on the discovered port
only when its operator or saved configuration has explicitly selected that
binding. Any host that can reach such a listener can issue WTP control
requests under its shared local-network principal. An untrusted
TXT record must never enable Plain LAN or weaken TLS policy. In either binding,
the client performs `HELLO` and checks the returned `device_id` before
associating a candidate with a saved catalog entry. On Plain LAN, that ID is
not cryptographic proof of identity; an existing trusted catalog entry must
not be silently replaced on the strength of discovery or `HELLO` alone.

## TXT format, version 1

TXT format version 1 defines two required keys, with ASCII values:

| Key | Value | Meaning |
|---|---|---|
| `txtvers` | `1` | Version of this TXT format, not the WTP wire version. It is the first key. |
| `binding` | `tls` or `plain` | Selected TCP binding; `plain` requires separate WTP transport permission. |

The listener's target hostname and port belong in the SRV record. They must
not be duplicated in TXT under
[RFC 6763 section 6.3](https://www.rfc-editor.org/rfc/rfc6763.html#section-6.3);
`txtvers` remains `1` if the configured port changes.

Clients may ignore unknown keys. They must not automatically connect when
`txtvers` is absent or unsupported, `binding` is absent or unknown, or a key
appears more than once. The WTP application version is negotiated by `HELLO`;
the TXT record does not claim WTP/1 support or advertise capabilities. Do not
put credentials, device IDs, certificates, job state, or RF settings in
TXT records. Keep TXT small enough for a normal mDNS response.

The TXT version follows
[RFC 6763 section 6.7](https://www.rfc-editor.org/rfc/rfc6763.html#section-6.7).
DNS-SD instance structure, SRV resolution, and TXT records follow
[RFC 6763](https://www.rfc-editor.org/rfc/rfc6763.html).
