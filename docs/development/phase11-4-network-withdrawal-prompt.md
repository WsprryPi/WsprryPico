# Phase 11.4 network withdrawal investigation prompt

Start by reviewing current capabilities, recent runtime changes and retained
physical evidence at Pico devel `e4ff40a561804cd90e9b823b659405fc7aa37275`.
Read README, CONTRACT, architecture, the acceptance matrix, C4 transaction
acceptance, mDNS integration and the B2/D2 repeat/same-SSID reports. Preserve
all failed attempts. Review only WsprryPico changes; do not modify SDK, Wi-Fi
recovery scripts, router reservations, credentials or other repositories.

Investigate two separate observations: (1) missing orderly mDNS goodbyes and
cached Linux addresses for at least 80 seconds, reproduced on Bohica-IoT with
host recovery paused; (2) intermittent ARP/TCP/NSS recovery failure while USB and
NTP remain responsive. Do not infer a memory leak, blame SSID separation alone,
or promote a successful retry into general reliability qualification.

Trace the exact current Console/HTTPS idle authority, ACK-gated deferred changes,
PicoNetwork polling/disable/re-enable, portable mDNS state, actual pinned lwIP
packet creation/IGMP/netif cleanup, CYW43 data submission and disassociation.
Identify what each success counter proves. Review recent settings/NTP and
concurrent-server changes and packet/pool lifetimes. Establish source-level
findings before implementing a narrowly scoped repair.

If confirmed source ordering permits immediate teardown after driver submission,
implement a bounded nonblocking withdrawal opportunity that suppresses further
mDNS responses while preserving the station and multicast membership until
final teardown. Do not sleep inside core-0 servicing or claim radio delivery from
a timer. Account for rapid OFF/ON, repeated OFF, physical link loss, conflicting
names, early startup, registration failure, permanent identity failure, timeout
cancellation, and pending HTTPS requests. Keep local job timing/authority and
RF inhibition unchanged. Add behavior-focused deterministic tests covering the
real pinned responder and the actual lifecycle integration, including failure
paths and resource stability. Do not alter immutable upstream sources.

Build/review an exact standard inhibited candidate with the existing approved
CA, hostname and saved configuration. Prepare the full board/image-specific
flash packet and obtain any still-required exact-image authorization before
flashing. Previous approvals cover bounded inspection, Pico Wi-Fi cycles,
packet capture and temporarily stopping wspr5's recovery timer/service with its
boot enablement preserved. Use only Pico serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, certified hostname
`wsprrypico-0a60df.local`. Require authoritative inactive/unowned state and
healthy preserved journals. No jobs, GPIO/RF or router changes.

For physical comparison, use the USB dongle wlan1 and retain onboard wlan0's
failed health baseline. Arm independent local restoration before stopping host
Wi-Fi recovery or moving Bohica to Bohica-IoT. Preserve reboot enablement;
record SSID/BSSID/profile throughout. Start complete native Mac observation
before the test, keep captures and credentials private and flush locally.
Measure goodbye submission versus observed TTL-zero A/PTR, negative cache
lookups, withdrawal interval, same-name probes/announcements, actual ARP,
resolution and authenticated HTTPS recovery, USB identity/state and memory.
Treat unexpected observer loss or path drift as an invalidated case, not a pass.
Retain short-run allocation differences without claiming overnight leak freedom.

After execution perform an adversarial review of implementation and evidence.
Fix actionable findings, rerun affected checks, then assess again. Preserve
unresolved radio/mesh causes and target qualification separately from source
correctness. Restore original connectivity and active boot-enabled host
recovery; verify final Pico identity/output/owner/settings and unchanged
installed transmitter service. Save a reviewed result, private artifact index,
updated current matrix and remaining items. Commit/push the requested changes,
verify clean remote parity, and report actual scope, tests and limitations.

## Prepared deployment packet

The reviewed standard inhibited candidate is
`build/phase11-4-withdrawal/firmware-ninja/firmware/WsprryPico.uf2`, SHA-256
`99ecfb665b0ed28137b660407fe0bb2e1276b67bcc3f607192c96a1e9ab62954`.
ELF SHA-256 is
`cc62297928a489c371682c226c219f93b63b376f66f0161746ef53a1c56cb4cd`.
Revision is `e4ff40a56180-dirty`; source inputs/diff must be retained alongside
this identity. Four affected host suites pass and four compiled lifecycle
mutations fail as intended. Stack/UF2 checks preserve both journals and the
RP2350-E10 reserved sector. Credentials are the existing approved short-name
server/CA/client deployment; no trust import or credential rotation is needed.

Bounded USB inspection confirms the current standard inhibited revision
`5ee5bcf93c56-dirty`, expected device/deployment, healthy storage, disabled
schedules and empty/inactive/unowned state. After image-specific approval, stage
only the candidate under a new owner-only path on wspr5, verify the transfer
hash, recheck that same authority, send Console BOOTSEL only to serial
`0BF4B4AEC9FFB344`, then use existing picotool `load -v -x --ser` without an erase.
Verify new boot/revision/HELLO/CAPS/STATUS, exact saved configuration and watermark,
same certificate/hostname, enabled Wi-Fi/power-save disabled and fresh resolution/
authenticated HTTPS before bounded withdrawal comparisons. Restore host Wi-Fi
and recovery as described above. No jobs, service installation or router edits.

Exact board/image approval is required by
[phase11-4-acceptance.md](phase11-4-acceptance.md), step 1:
“After authorization for the exact board/image”. The existing generic test
approval covers the other bounded operations, but does not name this new UF2.

## Diagnostic iteration after target watchdog

The first candidate produced a prompt native Mac removal callback, but
watchdog recovery interrupted the first actual OFF case. Recovery INFO records
stage 14 and boot `a076840ce0ec6f1887e86eb025e52ac9`; WTP confirms empty,
inactive and unowned. No allocation error precedes the failure. Do not promote
this candidate into accepted firmware or discard the failed target record.

A separately built standard inhibited diagnostic candidate adds only finer
watchdog breadcrumbs: 15 before mDNS final removal, 16 before station disable,
and 17 after station disable. UF2 SHA-256:
`524dd721ed6f67fbb21b1544546014fa174a4cb5d92d69d5fdfdbe5138f38664`.
The actual adapter test and linked-image stack/journal checks pass. Private
candidate/source identity is under `build/phase11-4-withdrawal/diagnostic-524dd721`.

After exact-image approval, preserve recovery INFO/WTP evidence, stage this image
under a new owner-only directory and flash the same serial with existing
picotool without erasing journals. Confirm saved disabled schedules, station,
watermark, original credentials/name and inactive/unowned state. Recovery-mode
suspension is volatile and may clear on the normal boot; saved schedules remain
disabled. Run one bounded OFF/ON case on the original Bohica client path with
USB, packet and native Mac logs. If it reboots, read the new fault and stop that
case; do not hide it with a retry. This is a diagnostic image, not an accepted
repair. No router, trust, jobs, GPIO or installed-service changes.


The user reaffirmed existing approval and directed continuation after the first
watchdog result. Diagnostic `524dd721...` was deployed to the same board without
another approval request. Existing all-tests authorization continues to cover
bounded diagnostic reproductions. Markers 15–17 refine the formerly broad
stage 14; they are not retrospective observations of the first failure.
