# Phase 11.4 station shutdown repair prompt

Start from WsprryPico devel 677ec7fde2362c36235a0fe66733811427ae3bb7. Read README,
CONTRACT, architecture, development checks, the B2/D2 packet trace record and
actual pinned SDK/CYW43/lwIP shutdown implementation. Preserve the current
working state and all retained failures. Work only in WsprryPico; leave SDK,
credentials, router, installed transmitter and sibling repositories unchanged.

Investigate the stage-16 watchdog in the station-disable section. Add narrowly
scoped, reset-surviving breadcrumbs around network-interface deinitialization,
DHCP stop, netif removal, IGMP cleanup/filter programming and radio disassociation.
Use the existing watchdog scratch register and restore enclosing markers after
nested calls return. Preserve function order, arguments, return values and buffer
ownership. Keep the eight-second watchdog and RF inhibition. Verify actual linked
call interception; source wrappers alone are not proof that a call is observed.
Keep diagnostic code out of physical RF images and immutable dependencies.

Test callback ordering, nested marker restoration, failure return propagation and
out-of-scope calls. Build the standard inhibited candidate with the existing
private certificates, short name and port. Record exact source and ELF/UF2 hashes,
stack/journal checks and the board/image deployment packet before physical work.
Existing all-tests and diagnostic-deployment approvals cover this same-board
iteration: serial 0BF4B4AEC9FFB344, device fd6127d11d6aca42a9905fa3fb1bf1d5,
MAC 88:a2:9e:0a:60:df, hostname wsprrypico-0a60df.local, port18443, IP192.168.1.47.
Recheck authoritative inactive/unowned state and disabled schedules, flash with
existing picotool without journal erase, and verify identity/settings afterward.

Run bounded shutdown repetitions with independent USB/raw-WTP/capture evidence,
first with network clients idle and then with normal authenticated status traffic.
Retain reset INFO before restoring normal inhibited operation. Use evidence to
identify the failing operation. If a supported cause is found, implement the
smallest repair, add a failing-before/passing-after regression against the real
integration boundary, review it, build/deploy the exact new inhibited candidate
and repeat full B2/D2 cycles. Do not widen watchdog limits or infer a repair merely
from a successful retry. Stop an ineffective experiment and state its limitation.

Once shutdown/recovery are stable, compare original Bohica and Bohica-IoT paths
with wspr5's USB wlan1, never onboard wlan0. Arm independent local restoration
before changing the host profile or pausing recovery; preserve reboot enablement
and verify per-case association. Keep Mac on Bohica as a separate observer.
Preserve failed ARP reply-delivery and missing-goodbye evidence even when later
cycles pass. Successful linkoutput is submission, not proof of radio delivery.

After supported repair and bounded stability, run an independently supervised
8-hour connectivity/memory soak. Log locally so a control connection loss cannot
erase evidence. Check memory at comparable quiet states, allocator errors,
watchdog/boot identity, USB responsiveness, DNS/HTTPS and authoritative output.
Report a soak as running or incomplete until its full interval and final review
are complete; never substitute short tests for overnight stability.

Perform adversarial code/evidence review, fix actionable findings and rerun
checks, then reassess. Preserve exact failed attempts and distinguish source,
host, physical-network and RF qualification. Restore original host networking,
active boot-enabled recovery and normal inactive/unowned inhibited Pico state.
Save the complete report, private evidence index and current acceptance matrix.
Commit and push requested changes, verify clean remote parity and report actual
findings, repairs, checks, remaining work and any still-running soak explicitly.

## Diagnostic deployment packet

Standard inhibited candidate revision `677ec7fde236-dirty`, UF2 SHA-256
`b1921701ccffee8ca630cbf719f8328ddfa417c86e707f960ea84148862b79b3`.
Linked-call inspection verifies all six shutdown interceptions. Host marker and
image stack/journal checks pass. Stage privately on wspr5 and flash only the
previously identified board with existing picotool, preserving journals and
credentials. Preflight and postflight include authoritative WTP ownership/output
and saved configuration. No new trust, router, GPIO or RF changes.

## Additional hardware reported during execution

The user reports a second Pico connected to wspr5 for later E1. Leave it untouched
in this investigation. Use the original serial-specific by-id endpoints, device
identity and image-bound flash checks; never select an arbitrary enumerated Pico.
E1 now has reported hardware availability but no second-board acceptance evidence.

## Evidence-driven path comparison

After the first normal-traffic campaign reproduces ARP delivery failure but no
new watchdog, compare read-only observations on original Bohica, temporary
Bohica-IoT and restored Bohica without issuing any Pico WIFI command. Reuse the
serial-bound USB observer and packet trace. Independently arm a 600-second host
restoration timer before the bounded 540-second controller; leave boot recovery
enabled and touch only USB wlan1. Keep Mac on Bohica. Record profile/BSSID and
recovery state throughout, retrieve local captures after any management outage,
and distinguish restored host configuration from restored Mac-to-host delivery.
The comparison changes SSID plus radio/AP association and involves reassociation;
it cannot isolate one of those factors or count as a D2 shutdown cycle.

## Final shutdown repetition bound

The initial idle attempt and three normal-traffic attempts count toward the
investigation even when packet evidence is invalid. After the corrected-gate
idle retest, permit at most three more normal-traffic cases: eight shutdown
attempts total at most. Preserve every failure/invalid result. Stop sooner at a
new watchdog marker or ineffective observation. A mixed or incomplete series
never earns the existing eight-clean-case stability conclusion.
