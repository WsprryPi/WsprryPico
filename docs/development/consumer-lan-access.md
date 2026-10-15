# Consumer LAN access and temporary setup Wi-Fi

Selected feature slice, 2026-10-14. Implementation and acceptance are tracked
separately from the closed Phase 14 and LED records. See the
[implementation/acceptance plan](consumer-lan-access-plan.md).
Implementation, bounded target acceptance and final adversarial review are
complete within the acceptance record below.

## Everyday use

Keep your computer or phone on its normal Wi-Fi. Open `http://<current-Pico-IP>/`
or `http://<configured-hostname>.local/` in an ordinary browser. The page also
works at `/radio`. Use the hostname actually reported by the Pico; its default
is `wsprrypico-<last-six-station-MAC-hex>.local`. A network/client without local
multicast name resolution can use the current IPv4 address directly.

Log in with the Wi-Fi password saved on that Pico. Password fields use the
network setup page's eye control to show/hide what you type; they start masked.
The eye never retrieves a saved password. See the
[password-control review](password-visibility-review.md). Radio settings, schedules,
pin assignments and job controls use the existing shared application API.
The separate **Wi-Fi and station setup** section changes the profile-owned
network or station identity through their existing transactional paths.
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
- The ten-minute manual lease starts on the debounced release. Repeated
  requests during that lease do not extend it. A later distinct gesture can
  request another window. Polling or connected clients cannot renew it.

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
30 seconds before fallback is withdrawn. Any valid manual lease still wins.
Manual expiry during an outage leaves fallback available. The AP coordinator
does not rewrite credentials, profiles or cursors during these transitions.

Activation/physical AP transitions are deferred while output is active,
unknown, armed, running or failed. Automatic outage recovery never invokes
the physical stop override or aborts an accepted local job. The next safe
state retries automatically. LAN status remains available throughout normal
loaded/armed/running operation; mutations retain BUSY and ownership checks.
An existing AP radio session loses admission when the RF policy withdraws its
surface. Page loss never aborts, releases, rearms or restarts a job.

At manual/recovery withdrawal, an existing reply gets at most ten seconds to
drain; new AP connections are refused during that drain. An idle connection
or page polling cannot retain the AP. Each HTTP connection has its existing
ten-second total deadline, one request and bounded buffers. One consumer login
slot is shared between AP and LAN, with existing login/session expiry bounds.

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

## Acceptance record — 2026-10-14

This slice is complete within the bounded acceptance below. It preserves the
closed Phase 14/P13.1 records and does not select a new broad RF campaign.
Sensitive inputs, captures and detailed INFO/browser records remain private in
ignored `build/consumer-lan-*` directories and on wspr5 under
`/home/pi/consumer-lan-acceptance-20261014` and
`/home/pi/consumer-lan-browser-20261014`.

### Source and delivered artifacts

The tested candidate is `0.1.0-rc.3-consumer-lan-ae8e703e5afd`, built from
`devel` baseline `49e8d5ebe1f0fca40521661e746640449cf6d177` plus this slice.
Its INFO revision is `49e8d5ebe1f0-dirty`: it was built before the feature
commit. The private manifest records all 727 firmware-source files; each
recorded file hash was rechecked against the final source. Documentation and
host/browser test harnesses are outside that firmware-source manifest.

| Identity | SHA-256 |
| --- | --- |
| Firmware-source manifest identity | `ae8e703e5afd14ecfd5d99a0591efb153c7adfc1618f1293b9c10235678b2072` |
| `WsprryPico.uf2` | `a51aa67eade585ab506b61da3a5c9f225d56ce7d1c16c3f4d0764fe74ab2fd3c` |
| `WsprryPico-StandaloneRF.uf2` | `6170b612e22ded1ef8cdb4c4239a7e12c66dec0099c080fad91f4d06d7dcd36c` |

The retained SDK is 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`; the installed cross compiler is
Arm GNU Toolchain 15.3.Rel1, GCC 15.3.1. Both Release images cross-link with
configured button capture enabled. Linked-image checks pass for RF button
safety, absent BOOTSEL sampling, stack guards, heap/BT allocation routes and
RAM placement of the RF renderer. No SDK/tool installation was required for
these final builds.

### Checks and target evidence

| Area | Result and scope |
| --- | --- |
| Hardware-free regression | All 182 CTest checks pass, including actual pinned TLS/lwIP adapters, consumer crypto, origin/interface/session/replay/expiry, setup delivery, persistence, button/AP timers and shared ownership. Final serial run: 110.84 seconds. All 11 browser package tests and bundle generation pass. |
| Ordinary infrastructure browser | Chrome `155.0.8059.40` on the Mac visits A and B at their actual IP and hostname, rejects wrong passwords, authenticates, reads private state and changes/restores a radio opt-in with schedules/output disabled. A's run used `80dfc027832a`; B also passes on final `ae8e703e5afd`. No JavaScript exceptions; desktop/mobile views checked. |
| Physical temporary AP | B's existing GP14 button was held for an observed 11.078 seconds and released. Exactly one setup event; AP access worked while LAN remained available. Withdrawal was observed about 599.05 seconds after the first observed release, with two-second USB observation cadence, consistent with the 600-second lease. No timer-calibration claim. Persistent evidence: `B-physical-button-80df/result.json`. |
| Actual AP browser | Chromium `151.0.7922.137` on wspr5's isolated wlan2 client opens B's `http://192.168.4.1/radio`, rejects wrong login, authenticates and reads private state. The task-owned client profile was removed. Evidence: `B-AP-browser/result.json`. |
| Blank Wi-Fi-first setup | A starts its AP automatically with only access/profile pages blank. A real wlan2 client gets the setup page and a valid public setup start is admitted without pressing the button. Only those affected pages were retained/restored; config and current cursor pages were untouched. Evidence: `A-blank-80df-2`. |
| Transactional save without UTC | B saves the isolated WPA2 network, commits generation 4 and restarts. Its genuine HTTP page/private API work with an unreachable test NTP address and unsynchronized clock. Chromium verifies the exact save receipt after moving to the new IP origin, and visits its newly resolved hostname. |
| Automatic outage and boot recovery | B opens fallback after an actual infrastructure loss (67.25 seconds observed, including detection/adapter setup), and after reboot with saved infrastructure absent. A wrong hotspot password retains fallback and the same profile/cursor. Correcting it restores station access and withdraws fallback after 29.88 seconds observed stable connectivity. No button is used. |
| DHCP and session boundary | B moves from `10.77.14.23` to `10.77.15.23`. An old authenticated mutation receives HTTP 401; networking stays enabled. Fresh authentication and an ordinary transaction restore Bohica at generation 5. Complete original effective configuration and current cursor compare equal. Evidence: `B-network-ae8e-1/result.json`, PASS/restored. |
| Setup/ownership interlock | Actual WTP HELLO works before setup; the prepared setup transaction closes WTP admission. Private reads continue while ordinary configuration mutation returns 409. Deterministic tests cover stale delivery acknowledgements, lost replies and competing mutations. |
| RF and page loss | Final-candidate B runs one 15-second, 137,500 Hz Tone at 138 MHz, PIO/DMA GP2. Chromium reads Loaded/Armed/Running; configuration and foreign CLAIM receive BUSY. The page closes while output is active; WTP disconnects too. The same complete local job finishes and output becomes inactive. RSP1B `2404058C60` captures one 15.000-second nominal burst and quiet tail; receiver count/hash/cleanup checks pass. Evidence: `B-rf-ae8e-1/result.json`. |
| Resource bounds | The RF row's 19 INFO samples retain at least 119,888 bytes available, valid stack guards and no new allocation/DMA/flash/refill faults. Maximum refill IRQ-to-ready is 1,985,000 ns against a 3,799,188 ns buffer period. This is bounded sampling, not a normalized idle-growth or long-endurance claim. |

The physical button/AP and blank rows use predecessor
`0.1.0-rc.3-consumer-lan-80dfc027832a`, RF UF2 SHA-256
`69448ffe6f7e5b48b9225d2d5e9e6a998908d006e9e7072beb279ef71e913a8b`.
The subsequent final changes add the nonsecret browser save receipt and avoid
allocating for unchanged listener context; the button, AP coordinator and blank
admission policy are unchanged. Those physical rows were not repeated after
these final changes. Final images retain healthy configured capture and pass
the linked/host checks; final B has the browser/network/RF evidence above.

The first physical window lost its timing log during a wspr5 outage and is not
used for exact expiry evidence; the explicitly approved persistent repeat is.
The isolated hotspot initially advertised WPA1 and was corrected to WPA2 before
the accepted network run. A's failed network trials did not commit a replacement.
An interrupted A application load was recovered with the application-only image,
with current reserved settings/cursor inspected and preserved. The first RF
offline validator rejected the pre-commit `-dirty` revision format; the unchanged
original capture was assessed with exact dirty revision, candidate tag, source
manifest and UF2 hash checks. No additional RF job was run for that repair.
These fixture/recovery records remain retained and are not counted as passes.

### Adversarial review and repairs

The final reassessment covers public commissioning isolation, incoming netif
classification, exact authority/Origin checks, address changes between polls,
session/replay/expiry bounds, delivery-triggered changes, setup versus scheduler/
WTP races, AP expiry/drain, persistence, browser behavior and RF authority.
Actionable findings were repaired and affected checks rerun:

- Bind native browser `fetch` to Window; real HTTP-origin Chrome now works.
- Bind sessions and pending delivery to the admitted interface, raw authority
  and exact transport transaction; refresh live addresses at dispatch.
- Close competing WTP admission inside setup dispatch and pause new scheduled
  launches while setup is pending; retain private status reads.
- Require delivered setup replies, reuse a healthy association for station-only
  updates and retain the narrow factory-blank recovery exception.
- Preserve an uncertain save's nonsecret receipt through reload/origin change;
  require authentication and explicit result readback, with no mutation replay.
  Treat inexact legacy numeric generations as unconfirmed.
- Bound AP reply drain and remove client/poll renewal of the manual lease;
  avoid repeated hostname allocations on stable main-loop polls.

The repaired full host suite, final cross-builds, native browser checks,
network transitions and single RF row pass. No actionable finding remains in
this completed slice. The UI detector reported no findings in degraded regex
mode because parser dependencies were absent; it did not provide contrast
validation. Native desktop/mobile inspection supplements it.

### Retained state and limits

| Board | Serial / device | Current access | Profile / cursor |
| --- | --- | --- | --- |
| A | `0BF4B4AEC9FFB344` / `fd6127d11d6aca42a9905fa3fb1bf1d5` | `http://192.168.1.47/`, `http://wsprrypico-0a60df.local/` | generation 5; cursor `1791199541540946076` |
| B | `CDDBF8767C506C07` / `29f20b7342051ef947aa56cb9d4fab42` | `http://192.168.1.53/`, `http://wsprrypico-0a9d89.local/` | generation 5; cursor `1791705481000000000` |

Both retain final `ae8e703e5afd` RF firmware, 138 MHz, original saved values and
station identities, disabled schedules, healthy button capture, no owner,
inactive output, station web ready and AP off. B's profile advanced from 3 to 5
through the two intended network commits; restoring values does not restore an
older journal generation or cursor. A's firmware and reversible settings/setup
work occurred earlier; after the operator's A message, further mutations
were held and remaining tests used B. Final A inspection was read-only.
The task-owned test hotspot/client profiles are removed and wsprrypi.service is
restored active. GPSDO `0673ED0FA107` is locked and retains its original 10 MHz
output settings.

HTTP page-substitution risk and local-network Plain WTP authority remain the
security boundaries described above. New iOS/Safari/Android interoperability,
calibrated absolute timing/power, filter/emissions qualification and renewed
consumer-image endurance are outside this slice's evidence. Bounce, duplicate
requests, unavailable-network manual expiry, hostname replacement, lost replies
and RF-deferred automatic AP changes have deterministic coverage; they are not
claimed as additional physical campaigns here.
