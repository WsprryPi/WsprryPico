# Consumer LAN access and temporary AP slice

Selected 2026-10-14. Baseline: `devel` at `49e8d5e`; tracked files clean,
with unrelated `tests/hardware/si5351-i2c/` retained. This is a new feature
slice; Phase 14 and P13.1 remain closed within their recorded scopes.

## Initial review

The consumer radio adapter, port-80 connection classifier, page and admission
checks currently require the AP address. The main loop treats every consumer
profile as a blank profile, which requests the AP indefinitely. Station mDNS
readiness depends on the engineering/Plain LAN listener. The existing station
adapter already retries asynchronously every 30 seconds and handles DHCP
without discarding saved credentials. The AP coordinator already has a
60-second outage threshold, 30-second recovery hysteresis, and ten-minute
manual lease. Session/client activity can currently extend AP availability.
The configured button pin is already exclusive and defaults to GP14, but its
capture adapter is excluded by the default build option.

## Implementation

- Serve the consumer radio document at port-80 `/` and `/radio` on a usable
  station interface and on an available AP. Keep engineering TLS independent.
  Accept only the current station IPv4 or configured local hostname on station;
  accept only the AP address on AP. Bind each volatile session to its admitted
  interface and authority. Address, hostname, link or AP changes invalidate
  affected sessions and pending delivery actions. Preserve the Consumer-Radio/1
  bytes and vectors; any added logical routes are explicitly documented.
- Keep private reads and radio mutations behind saved-Wi-Fi-password login.
  Add authenticated commissioning routes inside that encrypted adapter, reusing
  the existing network trial/profile commit and station claim machinery.
  Public AP commissioning never becomes a public LAN route. Keep Wi-Fi,
  station identity and radio settings distinct in the consumer UI.
- Deliver pages over HTTP with the existing pinned Noble libraries, which use
  `getRandomValues` rather than secure-context-only WebCrypto. Explicitly retain
  the page-substitution risk: encrypted application traffic cannot authenticate
  HTTP-delivered JavaScript. No CA or client-certificate enrollment is required.
- Advertise station hostname and `_http._tcp` when consumer HTTP is ready,
  independent of UTC, SNTP, public DNS and engineering TLS. Retain conflict
  handling and direct-IP fallback. Reprobe on DHCP/hostname/listener changes.
- Deliver the configured active-low button capture by default. Factory pin is
  GP14 (physical pin 19) to GND; custom pins and explicit null stay authoritative.
  Retain reset under 0.4 seconds on release, stop at 0.9 seconds, and setup at
  nine seconds after authoritative shutdown. Do not add BOOTSEL sampling.

## AP transitions and bounds

| Situation | AP | Station / HTTP |
| --- | --- | --- |
| No saved network | Automatic setup AP | No station web |
| Saved network boot / outage | Automatic fallback after 60 seconds | Bounded background reconnect |
| Associated with usable IPv4 | Normally off | Consumer web immediately, independent of UTC |
| Manual setup gesture | Held gesture plus ten minutes after release | Retain station connection |
| Manual expiry, station unavailable | Remain fallback | Keep reconnecting |
| Station recovered | Withdraw fallback after 30 stable seconds and manual lease | LAN web available |
| Polling / connected client | Does not renew lease | Status stays available |
| Reply in flight at withdrawal | At most ten seconds to drain existing reply | No new AP work during drain |
| Armed/running/unknown RF output | Defer AP changes until safe; no implicit abort | Keep LAN status and operation-specific ownership checks |
| Profile replacement / reboot | Existing journal activation and restart rules | Invalidate old-generation sessions |
| DHCP / hostname change | Independent AP context | Invalidate old station context and reprobe |
| Explicit network disable | Fallback remains available when RF-safe | Withdraw station listener and records |

Only an explicit physical stop/reset/setup gesture may invoke the existing
local RF override. Automatic outage handling must preserve accepted local jobs,
schedules, station identity, credentials and no-repeat cursors.

## Acceptance and closeout

1. Deterministic state-machine, authority, session, deferred-delivery, button,
   persistence and RF-ownership checks; existing crypto vectors and host suite.
2. RP2350 cross-build and linked-image checks, including delivered button capture.
3. Finite target checks on identified A/B, preserving settings/cursors: real
   infrastructure IP and `.local` browser page/login/read/settings; AP normally
   off; manual hold/release/expiry; unavailable saved network, outage/recovery,
   wrong credentials, DHCP/name lifecycle, lost responses and RF-state access.
   Use real browser acceptance, not HTTP-client results as a substitute.
4. Record exact source/image/board/interface/browser/test identities privately
   where sensitive. Request an untimed physical press only when necessary.
5. Adversarial assessment, repair and affected recheck, then reassessment.
   Update contracts, README, architecture, development guide and roadmap.
6. Review and stage only this feature, commit on `devel`, push `origin/devel`,
   and independently compare the remote SHA. Report unresolved acceptance
   honestly; host checks alone do not close target or browser requirements.

## Disposition

Implemented and complete within the [bounded acceptance record](consumer-lan-access.md#acceptance-record--2026-10-14). Final source/image identities, physical
row applicability, browser/network/RF results, review repairs and retained limits
are recorded there. Phase 14/P13.1 remain closed and unrelated Si5351 work is
preserved.
