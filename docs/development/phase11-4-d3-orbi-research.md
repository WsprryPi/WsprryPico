# D3 testing opportunities on the RBR850/RBS850 mesh

Research date: 2026-09-09. **D3 can be tested with this mesh, but the usual
per-device Pause control is not a demonstrated Wi-Fi disconnect.** The useful
choices are a bounded IoT-network outage, a Pico-only physical shield, or a
separate test access point. The first affects other IoT clients; the latter two
can preserve the household network. The IoT outage was subsequently authorized and executed; see the
[D3 result](phase11-4-d3-results.md). Other options remain proposals.

## What the 850 system provides

RBS850 is the satellite in the user's mesh; the previously inspected controller
is RBR850. NETGEAR's [RBS850 data sheet](https://www.netgear.com/media/RBS850-DS_tcm148-92180.pdf)
lists the RBR850 as its required router. A spare RBS850 therefore should not be
assumed to offer an independent, separately configured laboratory AP.

The exact-model [850-series manual, pages 53 and 58–59](https://www.downloads.netgear.com/files/GDC/RBK852/RBK852_UM_EN.pdf)
documents a separate IoT enable checkbox and IoT band selection. It also says
main-network channel/AX changes apply across the Wi-Fi networks. Those broad
radio settings are poor controls for a single-Pico test. The manual is dated
2022; prior live UI inspection confirmed the IoT checkbox/band controls on the
installed RBR850 firmware `V7.2.8.2_5.1.18`. IoT Apply subsequently caused real link loss and restoration in D3; the
separate LAN/DHCP Apply operation previously returned 400.

NETGEAR's [Orbi Pause instructions](https://kb.netgear.com/000053868/How-do-I-pause-Internet-access-on-a-device-connected-to-my-Orbi-router)
describe stopping Internet access and explicitly include RBR850/RBS850. Its
[access-control instructions](https://kb.netgear.com/24830/How-do-I-use-access-control-to-allow-or-block-devices-from-accessing-the-Internet-on-my-Nighthawk-router-or-Orbi-system)
also distinguish blocked Internet access from continued local-network access.
These controls could test upstream DNS/NTP failure. They cannot be credited as
D3 without an independently observed loss of the Pico's Wi-Fi link.

## Experiments and what each can establish

| Opportunity | D3 suitability | Practical limits |
| --- | --- | --- |
| Temporarily disable Bohica-IoT, then restore it | Strong native candidate for actual station-link loss | Disconnects every client of that SSID. Use only after identifying affected devices and approving that outage, or proving the Pico is its sole client. Main-SSID continuity during Apply must be measured, not promised. |
| Shield only the insulated Pico while USB remains connected | Best fit for the existing Pico-only scope | No firmware/network configuration change. The enclosure must actually cause USB-observed link loss; traffic loss alone is insufficient. Remove shielding on completion or timeout. |
| Turn off the serving RBS850 | Useful satellite-loss/roaming experiment; conditional D3 value | Other attached clients are affected, and the Pico may reconnect to another mesh node before stale records expire. Current placement does not isolate the Pico. |
| Dedicated 2.4 GHz test AP connected by Ethernet to the LAN | Best repeatable laboratory arrangement | Give only the Pico access, then stop that AP/radio. Requires supported AP hardware and reviewed Pico provisioning if its SSID changes. This qualifies the recorded test topology, not Orbi-specific forwarding. |
| Orbi per-device Pause / Block | Useful upstream-loss test; not sufficient for D3 | Verify local reachability and link state; do not infer association loss from an app's “blocked” label. |
| Disconnect only satellite Ethernet backhaul | Backhaul-path experiment; not sufficient for D3 | The Pico-to-satellite radio may remain connected, and an alternate backhaul may exist. |

The last two limitations are experimental distinctions, not claims that every
firmware behaves identically. NETGEAR documents both automatic wireless and wired
[backhaul arrangements](https://kb.netgear.com/000051205/What-is-Ethernet-backhaul-and-how-do-I-set-it-up-on-my-Orbi-WiFi-System).
A backhaul interruption therefore cannot substitute for observing station-link
loss. The [Orbi Network Map](https://kb.netgear.com/000060885/How-do-I-view-the-devices-connected-to-my-Orbi-WiFi-System)
shows clients by router/satellite and connection type. Use it to identify the
actual affected clients before a satellite experiment; do not assume association
can be pinned or that turning off one node guarantees a sustained outage.

A main-versus-IoT comparison is also useful for the intermittent connectivity
investigation: hold the Pico firmware, credentials, AP placement and client
software constant, and change one client path at a time. For example, a wired
Linux observer on the router versus its current wireless path can separate some
mesh forwarding effects. Joining a client to the IoT SSID tests a different
path; it does not automatically force the same band or satellite. Existing
cross-SSID HTTPS successes rule out a universal inability to communicate, but
not intermittent forwarding problems. This comparison does not itself close D3.

## Router-side observations available now

Read-only inspection of `http://192.168.1.1/debug.htm` in the signed-in Chrome
session confirmed a **Debug Log Capture** page with:

- an unchecked **Enable LAN/WAN Packet Capture** control;
- **Start Capture** and **Save Debug File** buttons;
- an unchecked capture-at-boot option and CPU/memory information.

No capture or setting was enabled. This is direct UI evidence on the user's
router, not an assumption based on another Orbi model. A bounded router capture
could add the DHCP-server and bridge viewpoint missing from Mac/Linux captures.
It must first be scoped: this UI does not expose a Pico-only capture filter, and
a router-wide capture can include other clients. LAN/WAN capture also does not
promise 802.11 management frames or visibility into all traffic switched locally
by a satellite. Treat it as an additional observer, not proof of radio delivery.

## Proposed D3 measurement

Prepare USB, peer resolver observations and captures before the fault. Observe
one complete inhibited finite job Running, record the last positive mDNS answer
and TTL, then apply the selected fault. Require Wi-Fi still enabled but real
link loss, the same boot and uninterrupted local job progress. Hold the outage
past the observed TTL plus margin, record native cache expiry, then restore the
fault and measure automatic same-name recovery. Follow terminal lease-expiry
rules rather than requiring indefinite owner retention. No lost response may
trigger a duplicate LOAD/ARM.

The user subsequently authorized a brief Bohica-IoT outage and explicitly
accepted Wi-Fi-only management. Two outages established actual D3 link loss,
cache removal and automatic recovery; the second also established finite-job
continuity. Restoration required operator assistance and final correction of
the UI-default band selection. A separate AP remains the stronger arrangement
for repeated future fault tests with less household disruption. The
[result](phase11-4-d3-results.md) preserves actual timing, observation gaps and
remaining reliability limits.
