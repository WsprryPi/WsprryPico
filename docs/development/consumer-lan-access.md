# Consumer LAN access and temporary setup Wi-Fi

## Everyday use

Keep your computer or phone on its normal Wi-Fi. Open `http://<current-Pico-IP>/`
or `http://<configured-hostname>.local/` in an ordinary browser. The page also
works at `/radio`. Use the hostname actually reported by the Pico; its default
is `wsprrypico-<last-six-station-MAC-hex>.local`. A network/client without local
multicast name resolution can use the current IPv4 address directly.

Log in with the Wi-Fi password saved on that Pico. Password fields use the
network setup page's eye control to show/hide what you type; they start masked.
The eye never retrieves a saved password. Radio settings, schedules,
pin assignments and job controls use the existing shared application API.
The shared main heading and browser tab identify the Pico by its reported
boot-active hostname, including when opened by IP. Before login the name is a
public observation; sign in separately to authorize access. Open **About this
Pico / Diagnostics** in either task area to select/copy the **full stable device
ID**. Use that ID to distinguish two devices with the same name. The boot ID is a
separate observation. Saved rename-pending names do not replace the active
heading; connection loss or logout labels it **Last confirmed**. If no name has
been observed, the page says **Hostname unavailable** and retains current-IP/
setup-Wi-Fi recovery guidance. Name discovery is reported independently. See [device presentation](device-presentation.md) for identity and freshness semantics.

**Station/Transmission** contains station identity, schedules, pins and explicit
job controls. **Wi-Fi/Host** contains network credentials, time server, hostname,
restart/reconnect and setup access guidance. Area links keep one login and all
drafts in the same document; `/station` and `/wifi-host` survive reload. Saved
state, output observations and recovery remain shared. On an available setup AP,
a fresh root selects Wi-Fi/Host. LAN root selects Station/Transmission.
The profile-owned network and station editors use their existing transactional
paths. Each has one visible editor in its appropriate area.
These changes preserve schedules, radio configuration and no-repeat cursors.
Saving can reconnect/restart the Pico. Keep the tab open or use **Continue at
the Pico’s hostname** after joining the saved network. Log in after it returns,
then select **Check saved result** before repeating an uncertain save.
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

Page access and authentication require only station association and a usable
IPv4 address. Internet access, public DNS, NTP and engineering TLS are not
admission prerequisites. Operations requiring valid UTC retain their checks.
Engineering certificate control and Plain LAN WTP remain separate surfaces.

## Setup Wi-Fi and the button

With healthy saved infrastructure Wi-Fi the consumer AP is normally off.
Factory button wiring is an active-low switch from **GP14 / physical pin 19
to GND**, with the internal pull-up. Delivered standard and standalone RF
builds enable the existing PIO/DMA capture adapter. A saved custom button pin
or explicit disabled/null selection takes precedence; pin roles stay exclusive.

- A debounced release under 0.4 seconds requests reset.
- Reaching 0.9 seconds held requests authoritative transmission shutdown.
  A release from 0.4 to under 0.9 seconds requests shutdown on release.
- Reaching nine seconds held requests setup AP after verified shutdown.
  Holding longer emits no repeated actions. The AP stays available while held.
- Every AP window ends ten minutes after actual activation. Button release,
  repeated requests, traffic and clients do not extend it. After expiry a new
  deliberate request can open another bounded window.

Join the Pico setup Wi-Fi and open `http://192.168.4.1/` for Wi-Fi-first setup,
or `/radio` for the same authenticated radio/setup workflow as the LAN page.
The saved infrastructure network stays configured and connected where possible.
The radio page displays the LAN hostname and current station IP for returning
to normal Wi-Fi. The explicit stop gesture retains its existing scheduling/RF
inhibition behavior; leaving the AP does not rearm a transmission.

A blank device starts setup AP automatically. A saved network unavailable for
60 seconds requests fallback AP without a button. Background station retries
occur at 30-second intervals; a latched failed join gets a one-second leave
interval before retry. Recovered association plus IPv4 must remain stable for
30 seconds before fallback is withdrawn. Fallback never extends the hard AP window. An unchanged outage cannot reopen
an expired window; stable recovery rearms a later outage. The AP coordinator
does not rewrite credentials, profiles or cursors during these transitions.

Activation/physical AP transitions are deferred while output is active,
unknown, armed, running or failed. Automatic outage recovery never invokes
the physical stop override or aborts an accepted local job. The next safe
state retries automatically. LAN status remains available throughout normal
loaded/armed/running operation; mutations retain BUSY and ownership checks.
An existing AP radio session loses admission when the RF policy withdraws its
surface. Page loss never aborts, releases, rearms or restarts a job.

At manual/recovery withdrawal, an existing reply gets at most ten seconds to
drain within the hard AP cap; new AP connections are refused during that drain. An idle connection
or page polling cannot retain the AP. Each HTTP connection has its existing
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
observation and rejects clients without the saved passphrase. It is not a PAKE.
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
