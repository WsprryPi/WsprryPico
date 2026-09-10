# Phase 11.4 E1 two-board identity and trust

E1 **PASS, bounded** on 2026-09-10: two physical Pico 2 W/RP2350 boards expose
distinct MAC-suffix deployment names and full WTP identities, accept their own
credentials, and reject the other board's credentials. Three fresh-connection
rounds per board passed from each of macOS and Linux. Phase 11.4 remains open.
The [execution prompt](phase11-4-e1-prompt.md) incorporates the user's correction
that full-ID hostnames must not be the provisioning default. The
[sanitized evidence manifest](phase11-4-e1-evidence.json) binds private artifacts
and source files by SHA-256.

## Physical identity and deployment

| Property | A, original board | B, newly provisioned board |
| --- | --- | --- |
| USB serial | `0BF4B4AEC9FFB344` | `CDDBF8767C506C07` |
| Full WTP ID | `fd6127d11d6aca42a9905fa3fb1bf1d5` | `29f20b7342051ef947aa56cb9d4fab42` |
| Station MAC | `88:a2:9e:0a:60:df` | `88:a2:9e:0a:9d:89` |
| Certified/advertised hostname | `wsprrypico-0a60df.local` | `wsprrypico-0a9d89.local` |
| Observed DHCP IPv4 | `192.168.1.47` | `192.168.1.53` |
| Runtime revision | `677ec7fde236-dirty` | `54753341c6d6-dirty` |
| Final boot ID | `fce01d70d37fea213202037759ef682c` | `b32ed414cac5fd055929413f21e62c4a` |

Both use port 18443, independent per-device CAs and
`inhibited-standalone-simulator`. No jobs were submitted. No physical RF clock,
GPIO or RF output was exercised; the profile retains the existing 138 MHz
frequency limits without a physical RF engine. Both authoritative final USB
INFO and WTP HELLO/CAPS/STATUS agree on device/boot identity, empty/unowned state,
disabled scheduling and `output_active:false`; both clocks are synchronized.

All network testing used Bohica-IoT. The user confirmed the Mac's association
after the OS command failed to expose its SSID. Linux `wlan1` reported BSSID
`42:98:b5:fe:36:a1`, 2432 MHz and address `192.168.1.117`. The network is the
user-described 2.4 GHz bridge. No assertion is made that both Picos used the
same AP/BSSID as the client. A and B's neighbor entries agree with their station
MACs. B additionally reports its own MAC directly over USB.

A was neither reflashed nor reconfigured. Its old firmware still reports the
historical full-ID `stable_hostname`; its actual certificate and advertisement
already use the short name selected by the corrected default. B physically
demonstrates the new boot-derived default. This is not evidence that A runs the
new diagnostic implementation. The default derivation and full-ID trust boundary
also have independent host tests, including suffix collisions.

## Naming correction and provisioning

The certificate helper now requires an observed `--mac-address` when generating
a default hostname. It derives `wsprrypico-<last-six-MAC-hex>.local` and fails
before creating credentials if neither a MAC nor an explicit alias is supplied.
It rejects invalid, zero and multicast MACs. Explicit aliases, including old
full-ID names, remain supported. Renewal needs the observed MAC or explicit
alias; it never silently selects a full-ID name. The full WTP ID independently
binds the manifest to the actual board and is not truncated for authentication.

Firmware reads its own station MAC after Wi-Fi driver initialization at boot and
exposes `network.station_mac` and the derived short `stable_hostname`. A failed
or invalid read leaves both empty. This diagnostic does not override the
certificate's configured hostname. Network-free recovery boots remain free of
Wi-Fi initialization. Existing alias/conflict behavior and certificate checks
remain intact. Current setup, identity, mDNS and API documentation were updated.

B initially enumerated as an RP2350 A2/QFN60 in BOOTSEL with no application
metadata. Picotool's automatic-size backup failed without writing flash; an
explicit first-4-MiB backup then read and verified successfully. Backup SHA-256:
`ba6e681d2922d30029b15d866024b7a5cc26a29bf82aa0a0d3d5c039aa693683`.
All loads selected B's serial and verified written data; no journal erase was
requested. Separate inhibited bootstraps established B's WTP identity and
station MAC before its certificate-bearing image was generated. The initially
generated full-ID certificate/image was superseded before network deployment.

The new private CA and separate controller/browser identities live under
`config/local/network/phase11-4-e1-29f20b73/`. The final `server-short` bundle has
DNS SAN `wsprrypico-0a9d89.local`, no IP SAN, and server fingerprint
`9cc4967f0a263b4aa94069674837ddcdb8c1946f5a5b407584ce7eee6298cfac`.
B uses private Bohica-IoT settings, DHCP, `pool.ntp.org`, `enabled:false`, and a
retained 120-second schedule entry required by the configuration schema.

Build inputs: source HEAD `54753341c6d63dc210f4e0941a469d4a028bab0b` plus the
recorded naming changes, Pico SDK
`98a542c1a62fb549ffb5d66a3e5892b06276b670`, picotool
`6f6458d792b93685a11423b244a585eaa99eafcf`, Arm GNU 15.3.1, Release `pico2_w`.
Only the standard `WsprryPico` target was built for deployment. Final ELF SHA-256:
`6154b1ff557aa9bfa229dbdebdec885844e621e1bdd8f67153d99497dcc8cb11`;
UF2 SHA-256:
`d6e037d0729b4c70aa609458811c9f6c9815add164f1025ba580b6707c0a40c3`.
Layout/journal and shutdown-wrapper checks pass. Linked symbols include
DryRunEngine and exclude StreamEngine, PicoPioDma and start_worker. Generated
firmware and credentials remain private, outside tracked source.

## Trust results

Each target used its own CA, expected DNS name, exact server fingerprint and
full WTP identity. Negative cases changed one trust input at a time. No TLS
validation bypass, system trust-store change or browser import was used.

| Check | Linux | Mac |
| --- | --- | --- |
| Authenticated WTP HELLO/CAPS/GET_CLOCK/STATUS | 6 sessions pass | 6 sessions pass |
| Own-client HTTPS status, including controls around negatives | 24 pass | 24 pass |
| Other board's client, correct target CA/name | 6 reject with TLS `unknown_ca` alert 48 | 6 reject with alert 48 |
| Wrong server CA, correct client/name | 6 reject, verification code 20 | 6 reject, code 20 |
| Other board's DNS reference, correct CA/client | 6 reject, hostname code 62 | 6 reject, code 62 |

Linux completed 11:51:15–11:52:24 UTC; Mac completed 11:53:13–11:54:19 UTC.
Fresh WTP sessions and every successful HTTPS status agree with the fixed boot
identities above and inactive, empty/unowned output state. The records contain
12 WTP sessions, 48 HTTPS controls and 36 intended negative rejections in total.
These are direct physical TLS/WTP/browser-API observations, not new Chrome UI
or WsprryPi production-application acceptance. Their earlier bounded passes
were not rerun or expanded.

Linux native NSS resolved both names. The first bounded Mac window resolved A
but returned no answer for B. A later eight-second window resolved each name
on interface 14/en0 to the correct address; B answered at 11:55:38 UTC. The first
failure remains evidence against a general discovery-reliability claim.

## Retained failures and limits

- The unmodified bootstrap entered a watchdog recovery boot after initial Wi-Fi
  operation: stage 13, boot `2c462264e17a26d784d5c00e821b5b57`, with inactive
  inhibited output. Its trace was empty after recovery. A contemporaneous Linux
  ARP lookup was incomplete. The cause is unresolved. This is not proof of the
  historical D2 shutdown watchdog recurring, and the naming change is not a
  claimed watchdog fix. B's final image retained one boot through the acceptance
  matrix and final USB inspection; that bounded nonrecurrence does not close
  connectivity investigation.
- The first Linux matrix attempt correctly stopped on a server fingerprint
  mismatch because the harness selected A's older IP-SAN bundle. Authenticated
  inspection matched the actual server to the existing `server-mac-suffix`
  certificate (`06496fe4...fef46016`) before the corrected three-round run.
- The first B configuration omitted the schema-required schedule entry and was
  rejected as `invalid_config`; the corrected entry remains disabled. No job ran.
- Historical host tooling paths were absent. Pinned local picotool sources were
  staged and built privately on wspr5. Sandbox transfer denials, an approval-review
  timeout, the fresh build's attempted tool fetch, expired host-test credentials
  and the missing updated host mock are retained setup failures. Native access,
  the existing pinned source, fresh ephemeral certificates and the corrected mock
  resolved them; none is classified as a physical LAN fault.
- Guided Windows setup and runtime credential installation remain unimplemented.
  The proposed generic-UF2/USB provisioning flow in
  [network control](network-control.md#end-user-provisioning-limitation) is not
  delivered by E1. End users should not be expected to compile their own images.

## Validation and adversarial assessments

The fresh hardware-free build passed all 33 tests: 32 in the sandbox and the one
TLS loopback test with native access after its sandbox startup rejection.
Certificate tests cover default issuance/renewal, missing/invalid MAC rejection
before writes, explicit legacy aliases and existing trust/manifest constraints.
Adapter tests cover actual driver-boundary name generation and failed/invalid
MAC reads. Existing mDNS conflict/lifecycle, API and TLS tests remain passing.
The WTP contract validator also passes. No WTP wire contract changed.

The user correction drove the short-default change; the affected build exposed
the missing host driver mock/constructor update, which was repaired before
validation. The first adversarial assessment corrected an inaccurate documented
short-label length. The physical evidence audit independently checks operation
and session correlation, exact board/boot/server binding, positive controls,
intended TLS errors, three-round ordering and authoritative inactive status.
It passes both hosts and rejects seven mutations: wrong fingerprint, wrong board,
active output, timeout-as-rejection, missing positive control, truncated run and
wrong reference name. It does not accept runner `pass` labels alone.

The second assessment reran the evidence checks and inspected the final source,
documentation, JSON, links, whitespace, private-artifact boundaries and final USB
state. No actionable E1 implementation or evidence finding remains. The retained
connectivity faults and end-user provisioning gap are explicitly not closed.

Final wspr5 state: `wlan1` still on Bohica-IoT; `wsprrypi.service` active;
`pi-wifi-recover.timer` scheduled and boot-enabled. A's boot, station, scheduling
state, schedule entries and watermark match its pre-test USB record. WsprryPi's
repository and installed service/configuration were not changed. Existing local
shutdown-results edits and untracked soak files were excluded from this task's
commit.

| Item | Status | Remaining work |
| --- | --- | --- |
| B2 — Linux discovery/reconnection | Open | Locate and correct the packet-delivery/recovery failure; demonstrate reliable Linux discovery and reconnection with repeatable physical evidence. |
| D1 — DHCP address change | Open | Obtain an actual different DHCP lease/address; verify unchanged hostname, device identity and trust, followed by Mac/Linux and production-client reconnection. |
| D2 — Orderly withdrawal/recovery | Open | Resolve unreliable recovery and account for retained missing-goodbye/watchdog evidence; demonstrate orderly withdrawal, cache expiry and reliable same-name recovery. |
| E1 — Two-board identity/trust | Pass, bounded | None for the recorded two-board identity/trust scope; retained connectivity findings remain open. |
| Eight-hour memory/connectivity soak | Incomplete | Complete the already-requested uninterrupted eight-hour run and assess memory stability and connectivity using preserved, attributable evidence. |
