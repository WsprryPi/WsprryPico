# Phase 11.4 B2 association, delivery and timeout waits

B2 remains **open**. This investigation identifies actual endpoint AP associations,
preserves physical watchdog and observer failures, removes an unnecessary RSSI
query that stalled, and updates the project to released Pico SDK 2.3.1 with
upstream RP2350 synchronization and alarm-wait repairs. It does not establish a repair for
the historical ARP replies submitted by Pico but absent at Linux.

The [executed prompt and amendments](phase11-4-b2-delivery-prompt.md) record the
hypotheses, bounds, authority and changes made after findings. All testing used
Bohica-IoT, the user-described 2.4 GHz bridge. No routing/isolation assumption was
substituted for packet evidence. Phase 11.4, D1/D2 and the incomplete soak retain
their existing scope; E1 retains its bounded pass.

## Firmware change and regression evidence

The project now pins released [Pico SDK 2.3.1](https://github.com/raspberrypi/pico-sdk/releases/tag/2.3.1),
commit `079c6f39023649b154152db30f1d781e884879bc`. The upstream
[combined sleep repair](https://github.com/raspberrypi/pico-sdk/commit/48a5de2ddec1b7859ac59388cd8d024ef4161825)
is an ancestor of that exact tag. The four linked USB/network libraries retain
their existing exact revisions; GCC remains 15.3.1, now officially supported by
the release. The original sibling SDK checkout is unchanged. New SDK and build
directories preserve previous binaries and logs. The SDK's Mbed TLS source list
now supplies `psa_crypto_random.c`, so the project's duplicate addition was removed.

The temporary `PICO_SYNC_RP2350_SPIN_LOCK_WORKAROUND=0` fallback was superseded;
the project uses the released SDK's synchronization defaults. The eight-second
watchdog remains enabled. All four firmware variants compile and link against
the update; only standard inhibited images were deployed. Previous physical RF
qualification does not qualify these newly built SDK images.

SDK 2.3.0 restored IRQs before draining an unlock event. Its timed semaphore path
could execute a direct WFE before its timeout-aware helper, reached from the
polling CYW43 driver's wait. SDK 2.3.1 drains the event while interrupts remain
masked, then restores IRQs and uses the timeout helper. This is a verified SDK
defect repair, not attribution of all physical resets or ARP loss to that defect.
No debugger backtrace was captured on these boards.

`check_inhibited_sync_image.py` rejects the actual prior 2.3.0 image and accepts
both 2.3.1 images. It checks the emitted unlock-store/WFE/IRQ-restore order and
subsequent timeout helper. Tests reject misplaced/missing waits, restored IRQs,
wrong stores/helpers and missing symbols. This is a narrow pattern regression
for the pinned RP2350 toolchain, not a general ARM control-flow proof or physical
timing qualification. The new test exposed a parser bug: unrestricted whitespace
consumed the next instruction after operandless WFE. Horizontal whitespace fixes
that error; the operandless instruction fixture now exercises the real format.

USB `NETLINK` now reports only an identity-bound BSSID observation. It checks the
connection before and after the driver read and reports invalid/disconnected/error
results explicitly. The read uses marker 26, restoring its enclosing marker on
return. Neither ordinary INFO nor network polling invokes it. Host tests exercise
disconnected state, driver error, invalid BSSID, link loss during the read and
absence of implicit queries throughout the existing network lifecycle tests.
The mock has no RSSI implementation, and the final linked binaries have no
`cyw43_wifi_get_rssi` symbol.

Example, only for explicitly authorized inhibited-device diagnostics:

```sh
python3 scripts/standalone_console.py netlink \
  --port /dev/serial/by-id/usb-WsprryPi_WsprryPico_0BF4B4AEC9FFB344-if00 \
  --device-id fd6127d11d6aca42a9905fa3fb1bf1d5 --run
```

Require nested `association.valid:true`; top-level `ok:true` alone does not prove
a connected observation. BSSID is sampled at that instant. Equal samples before
and after a window do not prove that no intervening roaming occurred.

## Exact targets and images

Both boards are Pico 2 W/RP2350, engine `inhibited-standalone-simulator`, port
18443, with AA0NT/EM18/20 station configuration and scheduling disabled.
The standard target retains the SDK RP2350 150 MHz system-clock default; no RF
mode ran, and the separately configured experimental RF sample rate is not a
measurement of this inhibited target. Existing
per-board certificates, short names, independent CAs and configuration journals
were preserved. A's watermark remains `1788714601000000000`; B's remains zero.

| Identity | A, original B2 subject | B, comparator |
| --- | --- | --- |
| USB serial | `0BF4B4AEC9FFB344` | `CDDBF8767C506C07` |
| WTP ID | `fd6127d11d6aca42a9905fa3fb1bf1d5` | `29f20b7342051ef947aa56cb9d4fab42` |
| MAC | `88:a2:9e:0a:60:df` | `88:a2:9e:0a:9d:89` |
| Certified name | `wsprrypico-0a60df.local` | `wsprrypico-0a9d89.local` |
| Observed address | `192.168.1.47` | `192.168.1.53` |
| Candidate boot | `3bb4bd7cb18af1e396fa4bf3ad5e5da6` | `6a0eca7714ee24db9aff824dd8ffb11b` |
| Final UF2 SHA-256 | `06d18600a3605e874f71c8fa4e7e7df1a1ef5983b5e1dcf6d0b1e695f01716e5` | `93a8db32967db004ef26a8bd85fb9efb52e86802c8861976032622f77d293183` |
| Final ELF SHA-256 | `59a2253844f18e80a5d938133956bd4a2f63b407c8d26d7b46c2195cdaef88dd` | `8d245a321a90a80bdf1b6db4edeeef8870bbcbb6eb7f5d9fdd3db1d211954685` |

Runtime revision is `dbf1d86f0885-dirty`; distinguish the successive candidates
using their ELF/UF2 hashes and source manifests, not that shared revision string.
Final formatting and rebuild changed ELF debug metadata; both UF2 hashes remained
byte-identical to the deployed images. The manifest retains the initial ELF hashes
and distinguishes them from the final checked ELF files.
Final builds used SDK `079c6f39023649b154152db30f1d781e884879bc` (2.3.1), picotool
`6f6458d792b93685a11423b244a585eaa99eafcf`, Arm GNU 15.3.1 and Release `pico2_w`.
Each deployment checked fresh Console INFO plus USB HELLO/CAPS/STATUS, exact
serial and image hash. No RF engine, job, GPIO or unrelated USB endpoint was used.

## Preserved physical observations

Initially wspr5 used BSSID `42:98:b5:fe:36:a1`, then roamed to
`7a:cd:d6:f2:f6:c5`, retaining wlan1, Bohica-IoT and profile
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`. A was observed on
`1e:0c:6b:e7:4e:37`, then `7a:cd:d6:f2:f6:c5`. B was observed on
`42:98:b5:fe:36:a1`. These are distinct radios advertising the same SSID.
Firmware deployments subsequently changed boot/association observations again;
that is a confound, not proof that the AP caused a failure.

| Attempt | Retained outcome |
| --- | --- |
| Initial B diagnostic deployment | Startup watchdog, stage 14, recovery boot `66a94ea284e5368db13358d15b8f0649`; one recorded recovery followed |
| Read-only 01 | Three broadcast ARP replies delivered; later NETLINK response exceeded five seconds; incomplete observation, same A boot |
| Read-only 02 | Three replies delivered; a premature second USB reader interfered with the running observer; invalid full run |
| Read-only 03 | Complete read-only observation; matching mDNS A response, three delivered ARP replies, native Linux resolution and authenticated HTTPS; no OFF/ON |
| First Mac baseline | A passed; B had no matching native mDNS result within eight seconds; later independent checks passed, preserving the failure |
| Linux peer check at 12:24 UTC | Both names resolved; A's WTP/HTTPS passed; B's connections failed with `Errno 113` before TLS |
| Same-radio comparison preflight | Aborted before host reassociation: A reset in RSSI query, marker 27, recovery boot `8449cfc188e9b3aee984951b60c1cd30` |
| BSSID-only A deployment | Startup stage-14 watchdog before any NETLINK call; recovery boot `3db6f2fcdaa01e435ce2c05cd470d5d0`; one recorded recovery |
| First candidate runner admission | Missing helper import; rejected before USB access or a physical cycle; corrected and separately retained |

The three read-only ARP windows each have three exact request/reply pairs matched
between Pico trace and Linux capture. Driver submission took 83–89 microseconds;
Linux actually captured the corresponding replies. Clock-offset sample spreads
were 0.970, 0.441 and 3.597 ms. Those spreads are not packet-latency measurements
or a complete bound on systematic USB delay. Both captures in each run reported
zero kernel drops. Failed/incomplete later observation does not erase these
bounded positive windows, and the windows do not make the full failed runs pass.

Read-only 03 retained 167 INFO samples and 440 continuous trace events, sequences
1706–2145. Its mDNS capture contains A's correct address, cache-flush class and
120-second TTL. Mac native mDNS, certificate/name/fingerprint-verified TLS 1.3
WTP and HTTPS subsequently passed on both then-current boots. The read-only
runner deliberately terminates through its existing “no OFF/ON requested” result;
that is not a reconnection CASE_PASS.

Stage 14 spans work after the driver poll and later main-loop service/server
work before the next marker. It does not uniquely identify mDNS, TLS or a driver
function. Marker 27 identifies entry to RSSI, but does not prove the deepest
internal cause. Neither reset is evidence of the historical stage-16 shutdown
watchdog occurring again. All earlier B2/D2 ARP and goodbye failures remain open.

The aborted host comparison armed a separate 210-second restoration timer before
its 180-second controller. Its cloned IoT profile disabled autoconnect. The
preflight failed before recovery was paused or the profile activated. Cleanup
verified the original IoT profile and active boot-enabled recovery, deleted the
clone and stopped the timer. No router configuration changed.

## Released-SDK comparison and remaining B2 boundary

The superseded 2.3.0 fallback candidate completed one full B2-only case, on A
boot `0a1ad3ddcce2540825fad179ac9b7180`: 2.028-second OFF, 6.548-second local
activation, six successful recovery checks spanning 33.754 seconds, and total
recovery 44.779 seconds. Its offline audit checked 222 INFO samples, 44 WTP
frames and 652 continuous trace events. This was one bounded pass, not the
required eight-case series or D2 qualification. Its images, record and earlier
failures remain distinct from the released-SDK candidate.

Both 2.3.1 deployments booted normally. B initially had no address and later
joined through the existing automatic retry; no intervention or reset occurred.
Initial Mac and Linux native discovery plus authenticated WTP/HTTPS passed for B
and failed for A. Exact serial-bound USB inspection confirmed A was healthy,
empty and inhibited. This failure preceded any candidate reconnection cycle;
starting an eight-case acceptance series without its baseline would be invalid.

A was on BSSID `42:98:b5:fe:36:a1`; B and wspr5 were on
`7a:cd:d6:f2:f6:c5`. A controlled three-phase comparison changed only wspr5's
association within Bohica-IoT, using a clone of its current profile with
autoconnect disabled and BSSID set to A's radio. A separate 270-second restoration
timer was armed before the controller's 240-second deadline. The original
recovery timer was paused only during this comparison and restarted on cleanup.
Neither Pico was reset, reconfigured, flashed or cycled within the comparison.

The complete observation ran **2026-09-10 13:03:25–13:05:05 UTC**. Each phase
checked exact USB INFO and WTP HELLO/CAPS/STATUS, both Pico BSSIDs before and after,
wspr5's profile/interface/BSSID, native Linux NSS, certificate/name/fingerprint-
verified WTP/HTTPS, and a live Linux ARP/mDNS/TCP capture.

| Host radio / phase | A ARP replies / 3 | B ARP replies / 3 | A authenticated connections | B authenticated connections |
| --- | --- | --- | --- | --- |
| Original `7a:cd:d6:f2:f6:c5` | 0 | 2 | Failed before TLS | Passed |
| A's radio `42:98:b5:fe:36:a1` | 3 | 0 | Passed | Failed before TLS |
| Restored `7a:cd:d6:f2:f6:c5` | 3 | 3 | TCP timed out | Passed |

All three captures exited normally with zero kernel drops (53, 84 and 77 packets
respectively). Exact ARP reply packets within each probe's own time interval
match the recorded arping counts. The first B probe returned exit 1 despite two
replies; it is not mislabeled as a complete three-reply pass. Before reassociation,
A had no native name result; on the same radio it resolved and both authenticated
protocols worked. After restoration A's native name resolved, but that result
may use cache and does not prove a new multicast answer.

On the restored host path, the capture contains **14 SYNs sent to A and no A
SYN-ACK**, despite the three preceding delivered ARP replies. B had two TCP
handshakes and successful authenticated checks. This localizes the failed
observed attempt before TLS; it is not a certificate or application rejection.
The comparison did not continuously collect Pico packet trace or an over-air
capture, so it cannot prove whether these SYNs reached Pico or where a reply
was lost. Identical endpoint BSSID samples bracket each phase but do not rule
out unsampled roaming. Host reassociation also changes transient driver/AP/cache
state, so this is evidence of path dependence, not identification of a particular
bridge implementation bug, isolation setting or mesh hop. Bohica-IoT remains the
user-described simple bridge; no routed-network model was assumed.

B2 is therefore still **open**, with a narrower actionable boundary: investigate
unicast forwarding/client delivery between the two observed Bohica-IoT radios
before repeating A's eight-case acceptance series. The released SDK repair does
not resolve this observed failure. No radio lock, static neighbor, cache flush,
certificate bypass or router change was left as a purported repair. The earlier
stage-14, stage-16, RSSI and missing-goodbye observations retain their separate
attribution limits. D1, D2 and the eight-hour soak were not executed.

## Validation and review

Fresh host validation comprises all 35 configured tests: 34 passed with the TLS
socket test excluded, and the TLS test passed with native loopback access.
An accidentally selected older build directory failed configuration and TLS
validation because its ephemeral certificates had expired. Those failures are
retained. The fresh build generated valid test credentials without altering any
board certificate or bypassing validation. The initial
sandbox TLS bind rejection is retained as an environment limitation. Focused
adapter, console and observer checks passed after their changes. Both final
images passed stack/layout, shutdown-interception and timeout-wait checks;
symbol inspection confirms the inhibited engine and excludes physical RF engines.

Review findings closed in the implementation/workflow: remove the observed RSSI
stall path; stop repeated association queries in packet observation; prevent a
second USB reader until unit exit; keep the public current-IoT override read-only;
validate helper imports before physical admission; retain invalid runs; restrict
ARP matching to the broadcast-probe interval so later unicast replies cannot be
misattributed. A test-fixture extra poll disturbed its existing lifecycle setup;
the query-count assertion was moved onto the already exercised lifecycle without
weakening its assertions.

An early preflight reused E1 helper filenames on wspr5. The original local E1
copies still matched the committed E1 hash manifest. The new snapshots were
preserved under B2 `e1-helper-preflight`, and the remote E1 copies were restored
to their verified original content. Pre-existing dirty shutdown and soak files
were excluded from this work.

Private evidence is under `build/phase11-4-b2-delivery/` locally and
`/home/pi/phase11-4-b2-delivery/` on wspr5. Credentials, captures and firmware stay
out of Git. The sanitized [evidence manifest](phase11-4-b2-delivery-evidence.json)
binds source, images, attempts, checks and final observations.

## Final assessment and state

The second adversarial assessment rechecked the SDK tag/repair ancestry, unchanged
linked library pins, emitted code, complete host checks and four target builds.
It separately checked the raw HTTPS body length/status/boot, WTP HELLO/CAPS/STATUS,
TLS name/fingerprint/ALPN, exact device associations, capture liveness/drop counts,
ARP probe intervals, failure retention, and restored host state. The first audit
incorrectly treated Console INFO as a WTP STATUS object; the corrected audit checks
each schema separately against the recorded USB frames. A formatting-only rebuild
was also rechecked: final ELF debug information differs, while each deployed UF2
remains identical. Historical E1 remote files again match their committed hashes.

No actionable implementation or evidence-consistency finding remains in this
change. The unresolved B2 delivery failure is retained as an acceptance blocker;
a passed evidence audit does not turn it into a passing acceptance case. Further
work needs observation of forwarding/driver delivery between the recorded radios,
then the original complete reconnection series. No claim is made that all watchdog
causes, D2 withdrawal, target RF timing or eight-hour stability are repaired.

Final USB checks show both exact 2.3.1 boots, healthy storage, synchronized clock,
unchanged station/schedule/watermarks, no owner/job, empty state, disabled scheduling
and inactive RF output. Final Mac checks (13:11:07 UTC completion) resolved both
names and reached B through authenticated WTP/HTTPS; A's connections timed out.
Linux's restored-path result remains A TCP failure/B success. These are explicit
network limitations alongside authoritative USB output state.

wspr5 uses wlan1, MAC `90:de:80:47:b9:da`, original profile
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`, Bohica-IoT and BSSID
`7a:cd:d6:f2:f6:c5` at 2432 MHz. `pi-wifi-recover.timer` is active and enabled;
`wsprrypi.service` is active. The temporary profile was deleted, restoration timers
stopped, and no B2 transient unit remains active. No unrelated device, router, RF
output or user shutdown/soak work was changed.

| Item | Repository ownership | Status | Remaining work |
| --- | --- | --- | --- |
| B2 discovery/reconnection | WsprryPico; joint WsprryPi acceptance | Open | Resolve observed delivery between Bohica-IoT radios, then eight complete cases |
| D1 DHCP address change | WsprryPico; joint WsprryPi acceptance | Open | Actual new lease/address with unchanged identity and trust |
| D2 orderly withdrawal | WsprryPico | Open | Explain retained watchdog/goodbye failures and establish repeatability |
| E1 two-board identity/trust | WsprryPico; joint WsprryPi acceptance | Pass, bounded | Preserve the recorded scope; general end-user provisioning remains unimplemented |
| Eight-hour soak | WsprryPico; joint WsprryPi observation | Incomplete | Uninterrupted run after repair gates; prior power-outage investigation is closed |
