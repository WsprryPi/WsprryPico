# Three-radio DHCP/TLS diagnosis and host restoration

Execute from WsprryPico devel `802c91a7b86e655488ba1c23253e95cc97350de9`.
Read AGENTS.md, README.md, CONTRACT.md, architecture and current development
commands. Preserve the modified shutdown record and untracked soak record/script
byte-for-byte. Do not edit sibling repositories. Commit and push only reviewed
owned changes and sanitized evidence after execution and adversarial review.

## Objective

Locate the first failed delivery boundary behind retained immediate WTP/HTTPS
recovery failures, repair demonstrated in-scope defects, and rerun affected
acceptance. A successful DHCP ACK or eventual connection is not full D1 closure.
Keep raw diagnostic evidence private. Document the working configuration and
verified outcomes concisely; identify unverified acceptance without a failure
chronicle. Do not promote eventual success beyond its measured acceptance bound.

## Hardware, authority and management

The user authorizes all three wspr5 Wi-Fi radios for controlled testing:
USB wlan2/e8:4e:06:ae:d7:09 as AP; onboard wlan0/2c:cf:67:62:76:66 as an
independent client; USB wlan1/90:de:80:47:b9:da as a passive monitor with an associated, unnumbered station interface on the
same radio to supply its channel context. Validate
actual MAC/PHY identity and monitor delivery, not only advertised capabilities.
The Mac stays on its existing network. Manage wspr5 through Ethernet link-local
IPv6 `fe80::2ecf:67ff:fe62:7664` with the Mac's en0 scope and its existing SSH
host key. Do not rely on IPv4 replies choosing Ethernet while Wi-Fi is active.

Before radio changes, snapshot the repaired Bohica-IoT profile UUID
921301fe-cdfd-4965-8ac7-c96e9d908ea6 and BSSID 7a:cd:d6:f2:f6:c5,
interface modes/power settings, services, namespaces and routes. Preserve the
saved ARP correction. Arm an independent bounded systemd restoration timer
before suspending the Wi-Fi recovery timer or making wlan1 unmanaged. Keep the
installed WsprryPi service active. No host reboot, router change, credential
replacement, trust bypass, firmware flash or RF/job/LOAD/ARM operation belongs
to this experiment. Source/build work is allowed; flashing requires a separate
explicitly reviewed execution boundary if a firmware defect requires it.

Pico A: serial 0BF4B4AEC9FFB344, device fd6127d11d6aca42a9905fa3fb1bf1d5,
MAC 88:a2:9e:0a:60:df, certified name wsprrypico-0a60df.local, TLS 18443.
Pico B: serial CDDBF8767C506C07, device 29f20b7342051ef947aa56cb9d4fab42;
read-only comparator. Verify fresh INFO and USB WTP, standard inhibited engine,
healthy storage, disabled scheduling and empty/unowned/inactive state. Record
exact runtime revision, boot IDs and existing firmware artifact identities.
Pico A alone may receive temporary complete CONFIG and one setup reboot to
join the private test AP, followed by original CONFIG and one cleanup reboot.
Neither DHCP transition may be represented as a reboot-free test if boot changes.

## Ordered experiment

1. Render this prompt and validate fixture refusal/restoration behavior locally.
   Create a fresh mode-0700 private evidence directory. Exclude credentials,
   captures, firmware and local private configuration from Git.
2. Arm restoration, suspend Wi-Fi recovery, prepare the monitor radio,
   and create a WPA2/CCMP test AP with a dedicated MAC-specific DHCP service on
   10.77.14.0/24. No DHCP, forwarding, NAT or bridge on the ordinary LAN. Serve
   test time from the existing PPS-disciplined chronyd and restore its deny rule.
3. Start a station association on the third radio using the private test
   credentials, without an IP address or default route. Add its passive monitor
   interface with control/other-BSS reception on the same PHY. Association fixes
   its channel to the test AP. Put the onboard client in its own network and mount namespaces, with its own
   Avahi/NSS socket. No host resolver, hosts-file or literal-address substitution
   counts as native discovery. Use a locked fixed-role fixture, not concurrent
   controllers. Validate actual AP/client association and monitor capture before
   mutating Pico A. If monitor mode cannot supply usable frames, restore and
   report that boundary instead of running the old incomplete experiment again.
4. Start AP, independent-client and monitor captures before association. Drain
   Pico NETTRACE over the serial-specific console with sequence-gap detection;
   align Pico monotonic time with host timestamps and retain uncertainty.
   NETTRACE records stack/driver boundaries, not successful radio delivery.
5. At the unchanged initial lease, run bounded authenticated reference and actual
   WsprryPi production-client observations serially with the same identity and
   credentials. Record TLS/ALPN, TCP segmentation, native discovery, complete
   WTP/HTTPS status and authoritative USB status. No timeout relaxation. If a
   baseline fails, analyze it before any DHCP mutation.
6. Once admitted, reload only A's DHCP binding from .10 to .20. Capture matching
   REQUEST/ACK, native resolution, ARP and same-boot INFO. Run unchanged reference
   and actual production-client checks. Track first missing TCP sequence/ACK
   across the client, AP, radio capture and Pico trace. Missing monitor frames
   alone do not prove loss. Reject trace gaps, clock ambiguity and mismatched
   frames rather than attributing them to firmware.
7. Fix only a demonstrated observer, client, driver-boundary or firmware defect.
   Add meaningful refusal/regression coverage. Repetition must test a specific
   correction or discriminatory hypothesis; preserve prior failed cases. Do not
   replace failed deadlines with eventual passes. Keep native Mac/Chrome D1
   acceptance explicitly open unless executed through a real native test-network
   connection with independently preserved Internet/management access. A proxy
   or Linux resolver is not native Mac acceptance.
8. Restore Pico A's original configuration, all three radios' modes/power/NM control,
   the repaired BSSID binding, Wi-Fi recovery active/enabled state, time policy,
   routes and namespace state. Remove only owned test services/profiles. Verify
   repeated Mac-to-wlan1 SSH, packet direction if ambiguous, Ethernet access and
   fresh A/B USB authority. Cancel restoration timer only after verification.

## Adversarial assessment and delivery

Review parser/clock/trace completeness, encrypted radio observation limits,
actual DHCP identity, client destination MACs, TLS hostname/fingerprint, exact
production binary and no LOAD/ARM, cleanup after each partial setup failure,
controller exclusion, secret handling and preservation of host/user state.
Fix actionable findings, rerun affected checks, then assess again. Separate
closed code findings from open physical acceptance or unlocated failures.
Save results and a sanitized evidence/hash manifest, update the development
index, commit, push origin/devel and verify remote parity. Report the actual
outcome, host restoration, checks, limitations and remaining user changes.

## Concrete correction prepared during execution

The capture exposed Pico reauthentication/reassociation during a real DHCP
address transition. Review of the exact SDK and adapter found that `NOIP`
means the Wi-Fi association remains usable, but the application's expired
30-second reconnect timer nevertheless started another join. Exclude `NOIP`
from that join decision, retaining retry behavior for actual link loss. The
actual-adapter test must reproduce zero-address DHCP handling beyond that timer,
verify no join or stale address advertisement, then verify genuine link-loss
reconnection. Correct the mock to follow the pinned SDK's zero-address semantics.

Build the standard inhibited Pico A image with the existing SDK 2.3.1,
GCC 15.3.1 and its existing MAC-suffix certificate. Candidate UF2 SHA-256:
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`.
The flash reservation, linked endpoint, shutdown interception and SDK wait
checks must pass. After explicit flash authorization, bind BOOTSEL and verified
picotool loading to serial `0BF4B4AEC9FFB344`; preserve both flash journals and
Pico B. Obtain fresh authoritative USB identity/inhibition status immediately
afterward. Repeat the admitted baseline and same-boot DHCP transition on the
same controlled setup, with unchanged client deadlines. Restore Bohica-IoT and
host management before concluding. Physical improvement remains unverified
until that execution is complete; source tests alone cannot establish it.
