# Phase 11.5 N0 host network fixture

Status: AUTHORIZED AND RUNNING; AP/client isolation and cleanup timer verified.
The frozen JSON packet retains its preparation-time status; current execution
is recorded here and in the closure work log.
This packet supplies the host fixture for the A-G matrix in
[the joint plan](phase11-5-plan.md). It does not itself pass any contention case.
The user's continuing flashing/RF authorization is recorded separately.

Use a new private root `/home/pi/phase11-5-n0-3eac6ec` on wspr5, boot
`220e53ca-ca95-4206-9581-dbe28aa1eeb8`. Stage the exact hashed helper closure
listed in `phase11-5-network-fixture.json`; credentials, generated PSK, network
configuration and raw captures remain owner-only and outside Git. Default helper
invocation performs no host or device access. Linux/root plus `--run` is required.

The bounded host changes are:

- Verify Ethernet MAC `2c:cf:67:62:76:64`, carrier and the working IPv6 management
  path `fe80::2ecf:67ff:fe62:7664`. IPv4 forwarding must already be disabled.
- Pause `pi-wifi-recover.timer` and its currently inactive service. Preserve boot
  enablement; restart the originally active/enabled timer during cleanup.
- Use wlan0 (`2c:cf:67:62:76:66`) as a channel-11 WPA2/CCMP test AP, temporary
  unsaved profile `phase115-closure-ap`, generated private PSK, address
  `10.77.15.1/24`. Its initial disconnected/power-save state is recorded.
- Move wlan2 (`e8:4e:06:ae:d7:09`) into `phase115-closure-client`, with a private
  mount namespace and `/run`, separate wpa_supplicant/Avahi, and `10.77.15.2/24`.
  The client has no default route. Preserve wlan1's ordinary management role.
- Run a fixture-only dnsmasq with a 60-second test lease for Pico A's MAC,
  initially `10.77.15.10`. Temporarily allow chrony access from this isolated
  subnet, then deny it again. No NAT, forwarding, trust-store or installed
  executable/configuration change is part of N0.
- Reserve only the named `phase115-closure-{client,dhcp,capture-ap,capture-client,
  campaign}.service` units and `phase115-closure-cleanup.{timer,service}`.
  Setup rejects any existing name. Each created worker carries a private
  ownership token; cleanup refuses to stop a unit whose token changed.

The independent cleanup timer is armed before the first host mutation. Setup
has a five-minute command budget. The fixture expires after 21,000 seconds
(5 hours 50 minutes), reserving ten minutes for cleanup within a six-hour total
window. Worker units have the same runtime ceiling and a ten-second stop bound.
Setup failure attempts cleanup immediately; the independent timer survives SSH
loss. Cleanup returns wlan2 by MAC, restores NetworkManager ownership and both
radios' power-save settings, removes its AP/profile/namespace/ACL, and confirms
the original WsprryPi process and ordinary management connection remain intact.

N0 never opens a Pico endpoint, changes its Wi-Fi configuration, flashes it,
submits RF jobs or clears a fault. The device campaign and final device
restoration are separate guarded operations. Automatic host cleanup cannot
establish inactive RF, and must never reset a device to conceal uncertainty.

The actual production application is separately built from clean WsprryPi
`7cb8e849b1293267d6921cbf493e0be685a4df95`, with `BACKENDS=simulated` and
`ANCILLARY_GPIO=0`. Its private executable SHA-256 is
`76ed15c662f45439127d2538c4bf3eccfdb1ab2b59a5337d5cf3c2fac46bd148`.
It will run only under a later reviewed campaign invocation in the client
namespace, accounting for singleton port 1234 as well as separate web/socket
ports. It has not been installed or run by N0 preparation.

Ten hardware-free checks cover default non-execution, preflight failure without
mutations, durable cleanup/ownership intent before ambiguous command outcomes,
foreign-unit rejection, absent-unit handling, command deadlines and credential
redaction. Actual setup and independent verification passed: AP/client routes,
different namespace inodes, active cleanup timer, and unchanged installed service
PID 1957 and INI hash. Final restoration evidence remains pending.
