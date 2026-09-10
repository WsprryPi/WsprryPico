# D1 native Linux/Chromium acceptance

**D1 passes for the user-selected Linux/Chromium scope.** On 2026-09-10, the
same native Chromium process and tab reloaded the Pico's certified hostname
following a real same-boot DHCP change from `10.77.14.10` to `10.77.14.20`.
Chromium retrieved and rendered fresh, certificate-validated status from the
new address in **2.80 seconds**. Native Linux resolution, authenticated reference
WTP/HTTPS and the actual production client also passed.

The user selected wspr5's browser instead of the Mac. macOS compatibility was
not exercised and is not claimed by this closure. The
[execution prompt](phase11-4-browser-d1-prompt.md) and
[sanitized manifest](phase11-4-browser-d1-evidence.json) define the scope and
identify the private evidence. Earlier setup diagnostics remain private; this
record documents the working arrangement.

## Working arrangement

| Role | Hardware/path | Configuration |
| --- | --- | --- |
| Independent management | wspr5 Ethernet `2c:cf:67:62:76:64` | Link-local IPv6 SSH; Mac stays on its ordinary network |
| Ordinary Wi-Fi management | USB wlan1 `90:de:80:47:b9:da` | Bohica-IoT, saved BSSID `7a:cd:d6:f2:f6:c5`, power save off |
| Controlled AP | Onboard wlan0 `2c:cf:67:62:76:66` | `WsprryPico-Test`, channel 11, WPA2/CCMP, `10.77.14.1/24` |
| Independent browser/reference/production client | USB wlan2 `e8:4e:06:ae:d7:09` | `10.77.14.2`, separate network/mount namespaces and native Avahi/NSS |
| Browser | Installed `/usr/lib/chromium/chromium` | Chromium 151.0.7922.137, native Linux headless execution, actual device page |

The browser used an isolated home with A's existing CA and existing
`wsprrypi-controller` client identity, limited here to reads. A private mount
provided certificate selection for only the exact certified URL. No certificate
warning bypass, fake resolver result, HTTP proxy or simulated page was used.
The NSS utilities were extracted into the private test directory; no system
package or global trust store was changed. The isolated home was removed after
execution. The setup follows Chromium's documented
[NSS certificate handling](https://chromium.googlesource.com/chromium/src/+/master/docs/linux/cert_management.md)
and [URL-specific certificate selection](https://chromeenterprise.google/policies/auto-select-certificate-for-urls/).

The 20-minute restoration timer was armed before AP/Pico changes. This case
required no firmware flash, router change, NAT, forwarding, bridge, host reboot
or RF/job operation. Both controllers and namespace children read one role file.

## Verified transition

Pico A is serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, certified name
`wsprrypico-0a60df.local`, TLS port 18443. It retained the approved standard
inhibited image reporting `802c91a7b86e-dirty`, SDK 2.3.1 and 150 MHz system
clock. Its previously verified UF2 SHA-256 is
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`;
[source correction and flash identity](phase11-4-radio-results.md) remain unchanged.

| Check | Result |
| --- | --- |
| Initial address | `.10`; native Linux reference, Chromium and production observations passed |
| Actual DHCP change | Pico REQUEST/ACK transaction `387b1291`, assigned by onboard AP `2c:cf:67:62:76:66` |
| Same boot | `9483d97a80991b23e49c9cec413a27b3` before and after the lease change |
| Name advertisements | Captured positive cache-flush answers after the ACK advertise only `.20`; independent peer capture corroborates the new address |
| Native Linux resolution and reference WTP/HTTPS | Passed at `.20`; complete reference pass 15.94 seconds after changing the binding, including lease-renewal wait |
| Native Chromium | Same process and tab `CA47A59349810D6DE07F89D70DED3796`; baseline status confirmation 5.02 s, changed-address status confirmation 2.80 s |
| Browser network evidence | Fresh HTTP 200 document, capabilities and status responses from the expected IP, marked secure; live JSON boot/address matches USB; rendered empty/inactive status |
| Actual production client | Passed at both addresses; each exchanged HELLO, STATUS, CAPS, STATUS, STATUS with five successful responses and zero LOAD/ARM |
| Stored state/output | Station, schedules, watermark, disabled state and expiry unchanged; healthy storage, inhibited engine and inactive/unowned state |

The browser URL and CA/server identity were unchanged. Both browser certificate
chains and production observations retain server SHA-256
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
The actual installed production executable remains SHA-256
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`, embedded
revision `48a9b92b4dfc553b61a19bdbc274d3550df6e854`. Its observations were fresh
connections at each address; the installed WsprryPi service remained active.

The browser observation ends after fresh status is rendered, while the
configuration-form read is still pending. It proves hostname/network/TLS/status
recovery, not completed configuration-form loading or management writes.
The browser process and tab persist through the transition; neither a cache
flush nor a browser restart was used to obtain the changed-address result.
Setup and restoration reboots are recorded separately from the same-boot DHCP
case. This is one bounded browser transition, not B2/D2 repeatability or a soak.

## Review and restoration

Offline review matched DHCP identity, both packet captures, native resolver
results, browser network events and certificate chain, live status/DOM, browser
process/tab continuity, production wire operations and final USB authority.
Thirteen refusal checks rejected altered boot/output, wrong browser address,
tab/process changes, incorrect trust, missing response evidence, truncated
captures and incomplete cleanup. The original evidence passed reassessment.
The report explicitly limits browser completion to the observed live status;
it does not promote the pending configuration read to a complete UI check.

Final Pico A boot is `1e4d80cfd9dbe41a50ff433d6d1811e2`, back on Bohica-IoT
at `.47`. B remains unchanged at `.53`, boot
`4e2fb851c08b278dd4b977104d2c2aaa`, runtime `dbf1d86f0885-dirty`. Fresh
serial-specific INFO and USB WTP checks confirm both inhibited, disabled,
healthy, empty, unowned and inactive.

The AP, namespace and browser processes are stopped, the test time allowance
is removed, original radio power settings are restored, and normal Wi-Fi
recovery/WsprryPi services are active. The saved management BSSID and disabled
power-saving setting are retained. Three ordinary Wi-Fi SSH checks passed in
0.59–6.22 seconds. The restoration timer was stopped after verified cleanup.
Existing shutdown and soak work remains untouched.

| Still open | Remaining work |
| --- | --- |
| B2 | Broader repeatable discovery/reconnection acceptance |
| D2 | Orderly withdrawal/cache-expiry and repeatable recovery acceptance |
| Eight-hour soak | One uninterrupted memory/connectivity acceptance run |
