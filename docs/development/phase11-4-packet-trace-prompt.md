# Phase 11.4 packet-boundary investigation prompt

Review README, CONTRACT, architecture, current network adapters, pinned CYW43/lwIP,
USB Console bounds, and the retained repeated B2/D2 results at devel 7cbf638.
Preserve the two reproduced symptoms without assuming two independent causes:
missing orderly goodbye delivery and prolonged LAN recovery failure despite
responsive USB and accepted NTP. Keep the explained unsynchronized-clock TLS
admission gate intact. Do not substitute aggregate transmit counters for delivery.

Implement a bounded project-owned trace at station netif input/linkoutput, with
monotonic timestamps, sequence numbers, interface generation, packet metadata,
mDNS payload fingerprint, actual linkoutput result, lifecycle markers, overflow
and hook-integrity accounting. Forward callbacks exactly once and preserve return
values and pbuf ownership. No allocation, printf, blocking, payload logging or
upstream source edits in callbacks. Use fixed storage and bounded, cursor-based
USB Console pages; include device/revision/boot identity. Keep RF builds free of
this diagnostic overhead. Test chained/truncated packets, rejected submissions,
input ownership, ring wrap, rereads and interface recreation against pinned lwIP.

Extend the opt-in harness to collect trace pages independently of blocking
network reads, explicitly bind candidate revision/boot, retain original evidence
and reject trace gaps when claiming absent frames. Build and verify a standard
inhibited candidate using existing private credentials, short hostname and port.
The user's all-tests approval and repeated direction to deploy diagnostic
iterations cover this same-board diagnostic work; no additional trust import,
router, DHCP, installed transmitter, GPIO or RF changes are included.

Stage a hash-bound image privately on wspr5. Recheck Console and WTP identity,
empty/inactive/unowned state, disabled schedules and healthy journals. Flash only
serial 0BF4B4AEC9FFB344 with existing picotool without erase. Preserve config,
watermark and credentials; verify new image/boot and normal network recovery.
Retain pre/post identity and exact build/source hashes outside source control.

Run the existing bounded B2/D2 cycles with synchronized USB/native Mac/Linux and
packet evidence. Stop on a localized failure, three unresolved failed cases,
observer failure, or eight clean cases. Correlate exact ARP identities and mDNS
fingerprints at the Pico and client. A successful driver return proves submission,
not radio delivery. Distinguish pre-stack receive absence, stack reply absence,
driver rejection and loss after successful submission without overclaiming AP blame.

If still useful after this trace comparison, compare wspr5's USB wlan1 on Bohica
and Bohica-IoT, with independently armed restoration and per-case path validation;
never manipulate the unreliable onboard wlan0. Preserve host recovery enablement
and restore original profile/power/service state. Do not continue a comparison
when its path cannot be kept known. First locate and repair a supported defect;
then run bounded stability checks and prepare/run an independently supervised
overnight memory/connectivity soak if a repair is ready. Do not label short tests
as overnight or leak freedom; retain unresolved work when localization stops.

Perform an adversarial review of code and evidence. Fix actionable findings and
rerun affected tests, then reassess. Record the exact failure boundary or instrument
limitation, final authoritative device/host state, remaining B2/D2 and memory gates,
and a private artifact digest index. Commit and push requested repo changes only,
verify clean remote parity, and report actual results without erasing failed cases.
