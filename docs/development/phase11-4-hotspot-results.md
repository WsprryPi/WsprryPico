# Controlled-hotspot D1 execution — 2026-09-10

The router prerequisite is now removed: **two real DHCP address changes were
captured without Orbi**, and the actual WsprryPi client subsequently authenticated
Pico A at the new address. D1 is still open because the immediate independent
client checks failed and native Mac/Chrome acceptance was not performed. No
firmware, SDK, RF implementation or timeout policy was changed.

This continues the [D1 review/prompt](phase11-4-d1-sdk231-prompt.md) with the user's
explicit authorization to create a controlled hotspot and independent client.
The work starts at `b06b2e5c1d3dd0451b5868d8f967720b919a91a9`. The existing modified
shutdown-results document and untracked soak document/script remain user-owned.

## Test arrangement and execution

Management remained on wspr5's `wlan1`, MAC `90:de:80:47:b9:da`, profile
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`, Bohica-IoT, `192.168.1.117`.
The Mac remained on its existing Wi-Fi connection throughout. No Mac network
switch, driver installation, NAT, Internet sharing or Orbi operation occurred.

The temporary SSID was `WsprryPico-Test`, subnet `10.77.14.0/24`, server `.1`.
NetworkManager provided a WPA2/CCMP AP with an in-memory, non-autoconnect profile.
A dedicated dnsmasq instance bound only to the test AP supplied DHCP. There was
no DHCP service on Bohica-IoT and no bridging or forwarding between subnets.
The client had static `.2` inside a separate network namespace and a private
mount namespace containing its own Avahi socket. Native NSS could not use the
host's Avahi instance or a hosts-file substitution. Its wireless association
and namespace identity were recorded. GPS/PPS-disciplined chronyd temporarily
served time to only the test subnet; the previous deny policy was restored.

| Case | AP | Independent client | DHCP result | Immediate authenticated result |
| --- | --- | --- | --- | --- |
| 1 | Onboard `wlan0`, `2c:cf:67:62:76:66` | USB `wlan2`, `e8:4e:06:ae:d7:09` | `.10` → `.20`, actual REQUEST/ACK, unchanged boot | Native NSS found `.20`; TLS, HELLO and CAPS succeeded, then STATUS timed out |
| 2 | USB `wlan2`, same USB MAC | Onboard radio, same onboard MAC | `.10` → `.20`, actual REQUEST/ACK, unchanged boot | Native NSS found `.20`; TLS handshake timed out |

A was moved to the test SSID using its existing USB CONFIG command and one
intentional setup reboot. CONFIG used a single-line complete JSON document,
`enabled:false`, existing station/schedules/expiry, and the local time server.
Its station MAC, short hostname, device identity, certificate and saved watermark
were preserved. No image was flashed. Both DHCP transitions occurred in the same
boot, `81651dd109dc10c739abb37563c6556c`, without a Pico WIFI OFF/ON command.
Changing the server's MAC-specific binding and reloading dnsmasq made normal
renewal reject the old assignment and acquire the new one. Although the fixture
requested a 60-second lease, dnsmasq advertised a minimum two-minute lease; the
captured packets, not the requested duration, define the actual timing.

A second hardware arrangement was a controlled response to the first capture's
large delivery delays. Its AP change caused reassociation but no Pico reboot;
that boundary is separate from the subsequent DHCP-only transition. The first
case and all setup/client failures remain in the private evidence.

## What the captures establish

Both transitions have a captured new-address DHCPACK from `10.77.14.1`, a matching
Pico DHCPREQUEST/client MAC/transaction ID, USB INFO showing `.20` in the same
boot, and cache-flush positive A records for only `.20` after the ACK. The offline
[auditor](../../scripts/audit_phase11_4_hotspot.py) found four such records in case
1 and six in case 2. The captures contain 318/227 AP/client packets for case 1
and 172/116 for case 2; every tcpdump log reports zero kernel drops.

Case 1 retained substantial AP-to-client delivery gaps. Matching exact Ethernet
frames across the two captures on the same host clock found 99 matches, 42 with
more than one second between observations, and a maximum of 31.351244 seconds.
One retransmitted CAPS segment appeared at the client about 19 seconds after its
AP observation. These are capture-point gaps, not a radio-airtime measurement or
proof of a particular driver defect.

The swapped hardware had 56 exact-frame matches, none above one second; its
maximum observed gap was 0.304469 seconds. That does not imply delivery of every
packet: during the failed handshake, the AP capture contains Pico TCP ACKs that
do not appear in the independent client capture. The client retransmitted the
first 1460 bytes of its ClientHello until the bounded handshake failed. This
provides a concrete packet-delivery lead independent of Netgear. It does not yet
locate the loss between AP software, radio transmission and receiver processing.
TCP retransmissions were present in both failures; this is not evidence that the
stack lacks TCP retry behavior. No retransmission or application deadline was
relaxed.

### Explicit client ARP assessment

The subsequent review tested the user's stale-ARP hypothesis against both
independent-client captures. Case 1 received the `.20` reply from the correct
Pico MAC in 381.356 ms; case 2 did so in 126.018 ms. In each case the first TCP
packet for the new address followed that reply. All 30/24 captured outgoing
client TCP frames for `.20` used `88:a2:9e:0a:60:df` as their destination MAC.
Thus waiting for the client's initial ARP resolution, or a wrong destination
MAC in these observed frames, does not explain the later full timeout. This is
not a cache dump or a proof about every ARP state or forwarding hop. It also
does not erase the separately observed ARP failures elsewhere in the captures.

## Actual production-client result

The installed `/usr/local/bin/wsprrypi`, version `3.2.0-devel+48a9b92`, embedded
revision `48a9b92b4dfc553b61a19bdbc274d3550df6e854`, SHA-256
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`, ran in the
independent client's network/mount namespace with private configuration and
loopback listeners. The installed service was not stopped. Transmit was false,
Enable on Boot Never, and LED/amplifier/shutdown/band GPIO controls were disabled.

The first invocation exited before network acceptance because credential files
belonged to a different Unix user. Protected copies of the same credentials
fixed the fixture; no trust check was bypassed and no new certificate was issued.
The corrected invocation resolved `wsprrypico-0a60df.local` to `10.77.14.20`,
authenticated that same hostname and server certificate, and reported the exact
Pico device/boot with empty, unowned, inactive status. It exited normally on the
observer's SIGTERM.

A process-local observation library recorded accepted TLS I/O without replacing
resolution or verification. Strict CRC/schema/frame decoding found exactly
`HELLO, STATUS, CAPS, STATUS, STATUS`, with matching successful responses, and
zero LOAD/ARM. The observed server fingerprint remained
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
This later production pass does not erase either immediate-client failure or
establish continuous recovery within the failed case's deadline.

## Restoration and evidence limits

An independent systemd timer was installed before the first network mutation.
Its cleanup service was started explicitly after the production observation.
A's original Bohica-IoT configuration was restored through USB and one intentional
cleanup reboot. Final USB INFO/WTP proved `.47`, boot
`3c0a9c410301287ab5e9cf8500a9b418`, healthy storage, original station/schedules/
watermark/expiry, disabled scheduling, and empty/unowned/inactive status.
B's final independent USB sample showed `.53`, boot
`4e2fb851c08b278dd4b977104d2c2aaa`, inhibited and inactive. Its earlier cable
power cycle was user-reported; this run does not claim an unchanged B boot.

Temporary capture/client/DHCP processes, the AP profile, namespace, test route
and time-server allowance were removed. The first cleanup assessment sampled
NetworkManager before asynchronous route removal completed and failed; a bounded
teardown wait fixed that check, and the second assessment passed.

A TP-Link adapter was plugged in while the onboard radio was inside the namespace.
It occupied the free name `wlan0`, so the returning onboard radio became `wlan3`.
Cleanup was changed to identify the returning radio by MAC instead of assuming
its name. After the user removed the TP-Link, the onboard radio's original
`wlan0` name and previously observed power-save setting were restored. `wlan1`
remained the active Bohica-IoT connection in the final successful restoration
snapshot. A subsequent SSH reachability failure is tracked separately below;
restoration samples are not continuous host-availability evidence.

No current Mac/Chrome new-address acceptance was attempted: the immediate Linux
path was not consistently passing, and the Mac's EDUP had no attached network
driver. The Mac stayed on Bohica-IoT. No USB/RF mode, physical RF timing or emitted
output qualification follows from these inhibited tests.

## Post-cleanup management outage

After the last successful restoration snapshot, SSH, ICMP and native hostname
lookup stopped reaching wspr5. The user confirmed both EDUP adapters remained
connected and the Pi remained powered. The cause is unresolved; the successful
cleanup sample does not prove continuing host availability or exclude an effect
of the test setup/teardown.

The user then shut down the Pi with its Pi 5 button, waited for the red LED and
power-cycled it. Both attached Picos may also have power-cycled. Subsequent SSH
attempts at the hostname, `.117`, and the known adapter addresses `.94` and `.77`
failed. Those addresses came from a neighbor cache and are not fresh lease proof.
Those failed attempts did not establish the Picos' post-reboot state.

The user subsequently connected Ethernet. Native mDNS then advertised
`192.168.1.54`, and SSH succeeded there. Fresh USB INFO and WTP HELLO/CAPS/STATUS
matched both serial/device identities, reported healthy storage, synchronized
clocks, disabled scheduling and empty/unowned/inactive state. A and B reported
the same boot IDs as their pre-host-reboot cleanup samples; these are fresh
observations, not an assumption that USB power survived. Neither reported a
recovery boot. wsprrypi.service and pi-wifi-recover.timer were active. No hotspot
units, network namespace or test route remained; chronyd denied the test subnet.

The retained kernel journal provides a specific lead: at 10:41:40 CDT wlan1
lost AP `7a:cd:d6:f2:f6:c5`, then associated with `42:98:b5:fe:36:a1` at 10:41:41.
This coincides with the management outage. After reboot, wlan1 remained on the
latter BSSID, SSID Bohica-IoT, 2432 MHz, address `.117`. Interface-bound probes
reached the gateway twice but received no Mac reply in two attempts; SSH to
`.117` still failed while Ethernet SSH succeeded. These observations do not
establish the AP's physical identity or prove client isolation. At that stage
Wi-Fi management recovery remained unverified and Ethernet was the retained
management path. No Wi-Fi profile, routing policy or router setting had been
changed in that initial verification; the subsequent repair is recorded below.

## Host repair and independent Wi-Fi verification

When the user challenged the incomplete restoration, D1 experiments stopped.
The Mac's neighbor entry for Ethernet `.54` had changed from Ethernet MAC
`2c:cf:67:62:76:64` to wlan1 MAC `90:de:80:47:b9:da`; IPv4 Ethernet SSH also
became unreliable. SSH to Ethernet's link-local IPv6 address provided a stable
repair connection. No host/Pico reboot, Pico configuration change or router
operation was performed during the repair.

Two bounded corrections were applied:

- wlan1 was constrained to the original, freshly scanned Bohica-IoT BSSID
  `7a:cd:d6:f2:f6:c5`. A one-time AP selection did not hold: the interface joined
  another BSSID, so an explicit temporary profile binding was tested first.
  Wi-Fi SSH then recovered. The binding was saved after validation; only the
  BSSID and NetworkManager's timestamp differ from the saved original profile.
  This deliberately trades roaming across this SSID's APs for the verified AP.
- `arp_ignore=1` and `arp_announce=2` were set specifically for eth0 and wlan1,
  then saved in `/etc/sysctl.d/90-wspr5-interface-arp.conf`. A gratuitous Ethernet
  ARP announcement restored the Mac's `.54` entry to the Ethernet MAC. These
  settings restrict cross-interface address replies/announcements as documented
  by the [Linux kernel](https://docs.kernel.org/networking/ip-sysctl.html#arp-ignore-integer).

The corrections began with a ten-minute rollback timer. The original saved
management profile is protected on wspr5 at
`/home/pi/phase11-4-host-repair/original-management.nmconnection`; it contains
credentials and is not a repository artifact. The private
`/home/pi/phase11-4-host-repair/rollback-arp.sh` restores the original ARP values,
removes the owned sysctl file, restores that profile and reloads it. The timer
was stopped after validation; the script remains available for explicit rollback.

Six separate Mac-to-`.117` SSH sessions passed over approximately one minute,
each confirming the original BSSID. A targeted capture shows the SSH flow in
both directions on wlan1, so this Wi-Fi check did not silently use Ethernet.
Ordinary Ethernet IPv4 SSH also passed. Ethernet remained connected as a recovery
path. Fresh USB checks on both Picos again showed the same boot IDs, healthy
storage, no recovery boot, disabled scheduling and empty/unowned/inactive status.
WsprryPi and the Wi-Fi recovery timer remained active; chronyd was synchronized
to PPS. No test namespace or hotspot unit remained.

This restores bounded working Wi-Fi management and preserves the saved repair.
It is not a reboot-persistence test or proof of indefinite availability. The
alternate BSSIDs' physical identities and failed forwarding behavior remain
unresolved. In particular, the post-Ethernet ARP conflict cannot retrospectively
explain the original outage before Ethernet was connected. The capture evidence
still does not close D1's authenticated recovery or Mac/Chrome acceptance gates.

## Adversarial review

The delivered fixture now waits for WPA key negotiation and its control socket,
uses private client NSS, prevents concurrent primary controllers, logs complete
failed command results without command-line secrets, sends CONFIG as one line,
checks actual MAC identities, and waits for asynchronous radio/route teardown.
The original failures are retained. Cleanup targets only named fixture units,
its profile/namespace, exact radios and A's saved configuration.

Local review also removed a duplicate baseline probe, derives the client PHY
from its identified interface instead of a fixed phy number, prevents cleanup
without a setup marker, and removes password-bearing argv from timeout errors.
It also restores captured radio power-save settings, checks fixture service
termination and the time-server deny policy, and refuses optimized Python
execution that would disable assertion guards. These final refinements were
checked without hardware; they were not
re-executed against the unavailable host. The fixture records a returning radio
by MAC and does not automatically rename it. The manual rename during this run
is part of the retained setup history, not a proven-safe reusable recovery step.

Sixteen deterministic adversarial/refusal cases pass. They verify that missing ACKs,
mismatched DHCP transactions, an unexpected server MAC, changed boot identity,
stale positive A records, stale native resolution, wrong Pico identity and
active output samples are rejected. Events after
cleanup cannot close the transition, certificate changes are rejected, and real
DHCP evidence alone never implies authenticated recovery. Production evidence is audited separately
against exact request/response framing and certificate fingerprints. Neither
software checks nor later successful requests are promoted into a clean D1 case.

## Remaining work

D1's actual-DHCP prerequisite and a bounded new-address production observation
are established on the controlled rig. Immediate authenticated recovery,
repeatability and native Mac/Chrome remain open. B2/D2 delivery and shutdown
repeatability remain separate open gates; bounded E1 status is unchanged and the
eight-hour soak is incomplete.

After host restoration, the next D1 diagnostic would be a synchronized capture
including the Pico's own packet boundary trace, focused on the missing
ACK/ClientHello segment. The controlled rig demonstrated the required real DHCP
event. Future runs must preserve the repaired management path. Repeating router
UI operations or changing application deadlines is unnecessary.

The [sanitized evidence manifest](phase11-4-hotspot-evidence.json) binds the
observations to captured artifact hashes. Raw captures, credentials, local paths
and generated images remain outside version control. This is a diagnostic
engineering fixture, not the planned Windows end-user provisioning workflow.
