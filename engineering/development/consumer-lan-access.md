# Consumer LAN access and temporary setup Wi-Fi

## Operator entry points and transaction authority

The [connection guide](../../docs/connect.md), [configuration guide](../../docs/configure.md)
and [recovery instructions](../../docs/maintain.md) are the canonical operator
procedures. This record specifies listener, transaction, interface and AP timing
behavior. The default hostname is `wsprrypico-<last-six-station-MAC-hex>.local`;
identity/freshness semantics are defined in [device presentation](device-presentation.md).
The two task areas share a document, authentication slot and drafts. LAN root
selects Station/Transmission; committed-consumer AP root selects Wi-Fi/Host.

An explicit setup transaction pauses new scheduled launches and rejects
competing radio/settings/WTP mutations until it completes or expires. Status
reads remain available. Setup starts only with idle, unowned RF authority;
it cannot interrupt an accepted job. The saved schedule and cursor are retained.
The continuation URL fragment retains only the change kind, device ID,
expected generation and request digest. It carries no password, keys or submit
packet, and the browser does not send fragments in HTTP requests. A reloaded
page can authenticate and check that receipt; it cannot replay a save from it.
For clients without hostname resolution, retain the fragment when replacing
the hostname with the current IP address. The tab also retains the receipt
in memory and never automatically repeats a mutation.
An inexact numeric generation in the legacy setup status remains unconfirmed;
it is never reported as a failed save based on rounded JavaScript arithmetic.

Page access and authentication accept the saved source-4 Wi-Fi-only profile as well as source-5 consumer profiles, with station association and a usable IPv4 address. No station claim or runnable configuration is manufactured. Internet access, public DNS, NTP and engineering TLS are not
admission prerequisites. Operations requiring valid UTC retain their checks.
Engineering certificate control and Plain LAN WTP remain separate surfaces.

## AP and button coordination

The active-low GP14 capture adapter, configurable exclusive pin plan and
single-action debouncing retain the gesture timings specified in the
[operator button table](../../docs/connect.md#request-setup-wi-fi-with-the-external-button).
AP requests follow confirmed local output shutdown and never rearm a job.
An associated Wi-Fi client retains every AP activation. The final disconnect starts a ten-minute inactivity interval. Initial unjoined access lasts ten minutes, or 120 seconds for Console join grace; the grace begins at actual activation. Browser traffic and login slots do not substitute for association. The driver samples CYW43 associated stations once per second and refreshes the sample at expiry. Saved network
credentials, profile and no-repeat state are not changed by AP coordination.

A blank device starts setup AP automatically. A saved network unavailable for
60 seconds requests fallback AP without a button. Background station retries
occur at 30-second intervals; a latched failed join gets a one-second leave
interval before retry. Recovered association plus IPv4 must remain stable for
30 seconds before fallback is withdrawn, and an associated AP client retains access through that recovery. An unchanged outage cannot reopen an expired window; stable recovery rearms a later outage. The AP coordinator
does not rewrite credentials, profiles or cursors during these transitions.

Activation/physical AP transitions are deferred while output is active,
unknown, armed, running or failed. Automatic outage recovery never invokes
the physical stop override or aborts an accepted local job. The next safe
state retries automatically. LAN status remains available throughout normal
loaded/armed/running operation; mutations retain BUSY and ownership checks.
An existing AP radio session loses admission when the RF policy withdraws its
surface. Page loss never aborts, releases, rearms or restarts a job.

At manual/recovery withdrawal, an existing reply gets at most ten seconds to drain; new AP connections are refused during that drain. HTTP connections and page polling cannot retain the AP without a Wi-Fi association. Each HTTP connection has its existing
ten-second total deadline, one request and bounded buffers. Three fixed consumer login slots are shared between AP and LAN, with at most
one pending ordinary login and the existing expiry bounds.

## Authority, discovery and security

Station accepts only its current IPv4 or configured local hostname on port 80.
AP accepts only `192.168.4.1` on port 80. TCP admission uses the actual incoming
interface, and accepted PCBs bind replies to that interface. Mutations require
the exact same-origin header pair, the application request header, no cookies
and absent/same-origin Fetch Metadata. Arbitrary, malformed, foreign and
cross-interface authorities are rejected. Sessions are bound in server memory
to their starting interface and authority; DHCP/link/name changes invalidate
station sessions, and AP withdrawal invalidates AP sessions. Matching transport
transaction acknowledgement still controls deferred actions. An old reply cannot
authorize a successor transaction.

The stable station hostname and `_http._tcp` service are advertised when the
consumer listener is ready, independently of engineering TLS and SNTP. DHCP
changes reprobe; link loss or listener withdrawal removes the records. Existing
name conflicts latch and require resolution/retry; the Pico does not silently
choose a different name. Configured hostname changes take effect through the
existing profile/deployment activation and reboot policy.

Consumer HTTP requires no CA, client certificate or special browser. Pinned
Noble X25519/SHA-256/HKDF/ChaCha20-Poly1305 code uses browser randomness available
on ordinary HTTP LAN origins. The native browser `fetch` function is bound to
its Window receiver. **HTTP does not authenticate the delivered page.** An active
page-substitution attacker can steal an entered password; encrypted application
payloads do not fix that risk. The genuine page protects traffic against passive
observation and rejects clients without the Pico password. It is not a PAKE.
Plain LAN WTP remains reachable by any client admitted by the local network.

AP public commissioning remains physically local to that interface. LAN
commissioning exists only inside the authenticated Consumer-Radio envelope;
it does not expose the public AP mutations on the station listener. The
[Consumer-Radio/1 contract](../protocol/Consumer-Radio-v1.md) specifies the
additive logical routes. Its handshake, packet format, cryptographic transcript
and fixed vectors remain unchanged.

## Reproduction

Use `bash scripts/check_host.sh` for the standard host suite. The optional
locally retained SDK Mbed TLS/lwIP checks use the commands in
[network control](network-control.md#hardware-free-validation).
Use `source scripts/xcode_env.sh` before standalone macOS CTest invocations.
Consumer browser unit/bundle checks are `npm test` and `npm run build` in
`src/network/bootstrap_web`.

The opt-in real-browser check is:

```sh
node tests/hardware/consumer_lan_browser.mjs --run \
  --private-input build/private-browser-input.json \
  --output build/consumer-lan-browser-result --settings
```

The owner-only input contains `password`, full `device`, current `ip` and
`hostname`. The checker uses installed Chrome without disabling browser
security, verifies real system hostname resolution, visits both actual HTTP
origins, rejects a wrong password, logs in, reads private state and captures
desktop/mobile views. `--settings` requires disabled schedules/inactive output,
changes one radio opt-in and restores the complete original config. The input,
screenshots and evidence remain private and ignored. This is explicitly live
device access; without `--run` the checker prints usage and exits.
An already connected AP client can use `--ap` with `ip` set to `192.168.4.1`;
that checks the authenticated `/radio` page on the actual AP interface.
An optional `receipt` object (`kind`, `device`, `generation`, `digest`) checks
read-only save recovery after login and captures the pending-receipt view.
