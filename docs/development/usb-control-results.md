# P15.14 production USB control execution record

Date: 2026-10-17. Complete within supported software and bounded USB/AP
acceptance. Independent adversarial reassessment passes; exact original flash
is restored. Transmitter RF/absolute timing was not exercised.

## Source and delivered behavior

The initially clean sources were Pico
`45f3367c89db00c20f06f119c58a06cc696f5fb5` and WsprryPi
`da0ef083644d30c800e6f7d421aecf96e764c735`. Both `devel` repositories participate;
no third protocol or documentation repository was changed. During execution,
Pico advanced to `9dee1ff177e65738d0e15e8b7ee35bd5ea8f400f` through an independent
documentation-only roadmap update. That commit and its revised P15.15–P15.18
sequence are preserved; the production source baseline is unchanged.

Both ordinary inhibited `WsprryPico` and `WsprryPico-StandaloneRF` expose the
existing Console and WTP interfaces plus USB-Management/1. Consumer USB WTP
uses local physical authority. Management, saved progress, configuration,
hostname, Wi-Fi lifecycle, restart and UTC adapt the existing application
services. They require neither a Pico network connection nor a commissioned
network session. USB application/capability views identify `usb_physical` and
management schema `transmitter-management/3`; network views retain their prior
shapes and schemas. The Pi validates the USB descriptor against the actual
management contract. RF events remain locally scheduled; USB never streams symbols.

The Pi discovers the management role by the selected WTP device's physical USB
parent, serial and interface role. Its verified common name is the Pico's saved
canonical Wi-Fi hostname. Full device/boot identity and saved/active/pending or
last-confirmed name states remain visible. Protected browser routes and the
ordinary Signal Setup USB settings panel expose these operations.

The [wire contract](../protocol/USB-Management.md) and
[local configuration authority](usb-local-configuration.md) define exact bounds,
delivery ACKs, revision checks, absent-network persistence, profile migration,
credential deletion and explicit application. Old firmware cannot consume the
new profile versions; migration is not a supported old-firmware rollback path.
Existing WTP clients retain WTP/1 framing and their interface role.

Every AP activation now has a non-sliding 600000 ms maximum from actual radio
enable. Held buttons, traffic, retry, reset/recovery handling and unchanged
blank/outage conditions cannot extend or reopen that window. Expiry withdraws
AP clients selectively, preserving station clients and USB. Fresh deliberate
requests and a new outage after stable station recovery can rearm it.

## Capacity, timing and resource comparison

No job, event, duration, mode, schedule, session or configuration limit was
reduced. WTP payload remains 65536 bytes, events 512, job duration 3600 seconds,
Config 1800 bytes, scoped update 2048 bytes and profile 7168 bytes. Consumer
session/pending capacity remains 3/1. Maximum ARM uncertainty remains
500000000 ns and maximum holdover age 90000000000 ns; synchronized/holdover
clock windows remain 90/180 seconds. Pi's existing configured uncertainty
threshold is preserved. A qualified USB observation can still be too uncertain
for that threshold; neither host nor Pico clamps it into admission.

The same retained Pico SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1 and normal
138 MHz configuration built the initial baseline and both new images.

| Image | Baseline text / BSS bytes | USB text / BSS bytes |
| --- | ---: | ---: |
| Inhibited | 2192032 / 174000 | 2257132 / 175468 |
| StandaloneRF | 2207500 / 329940 | 2271784 / 331404 |

Static RAM increases by 1468 bytes in the inhibited image and 1464 in
StandaloneRF. The RF worker remains 166176
bytes; the RAM renderer remains 660 bytes / 233 checked instructions at
`0x200012d8`, with 13976 initialized-data bytes. Existing linked heap, stack,
BOOTSEL and GP14 RF safety checks pass. This comparison does not qualify RF
timing, dynamic fragmentation or every concurrent resource combination.

Management buffers are paged and returned when idle. It retains the existing
32 KiB control reserve plus bounded workspace. Only authoritative WTP admission
can reclaim optional management pages and retry its original unchanged checks;
generic JSON/application memory queries remain side-effect-free. A reclaimed
session cancels its undelivered deferred effects and requires reconnect/readback.
Accepted UTC and durable settings remain authoritative. No RF timing reserve
or WTP workspace limit is reduced to keep management connected.

The initial conservative 140288-byte management reserve was rejected by real
RF-image hardware: idle free heap was 128824 bytes (144184-byte heap capacity).
Negotiation therefore timed out even though the inhibited image worked. This
finding is retained rather than accepted as a resource limitation. The repair
uses demand-based WTP priority instead of reserving multiple complete job
representations ahead of a small management request. Strictly validated large
JSON can also release redundant whitespace/ASCII-escape pages while preserving
its original wire SHA for exact replay identity; original decode/control checks
remain unchanged. Final regression/physical outcomes are recorded below.

## Software validation

- Full Pico host suite: 186 tests, zero failures, one optional
  `config_update_schema` skip because the Mac host lacks Python `jsonschema`.
  That check subsequently passed against the actual Linux Config handler in
  the retained offline image, where the package was already installed.
  Xcode environment and unrestricted local sockets were used. The initial
  wrong-toolchain/socket sandbox failures were rerun successfully; an obsolete
  unknown-profile-version test was corrected from newly supported version 2
  to unsupported version 3.
- The actual TinyUSB descriptor test passes against the retained SDK headers.
  Existing Console/WTP descriptors are preserved; management is instance 2,
  control interface 4, endpoints `85/06/86`.
- AddressSanitizer and UndefinedBehaviorSanitizer cover USB endpoint/time,
  local configuration/journals, AP policy/HTTP withdrawal and maximum event
  storage, including the tracked-heap endpoint capacity test. All six pass.
  Apple's runtime rejects leak detection; it is disabled explicitly.
- `python3 scripts/validate_wtp_contract.py` passes 23 schema, 7 raw JSON,
  1 framing and 8 transition cases. New frozen management vectors execute
  against the production endpoint driver.
- The production Pi USB client and protected browser/configuration adapters
  interoperate with the actual Pico management endpoint, LocalUsbApi,
  journals and TimeExchange over fragmented pipes. The browser test emits
  real settings requests for blank naming, Wi-Fi create/replace/delete-last/
  recreate, partial progress, explicit station apply, shared station edits
  and qualified software-fixture UTC. No network is opened. This qualifies
  wire/application interoperability, not target USB or RF timing.
- Pi production/runtime/application, USB pairing, framing, browser API and
  Node UI regressions run on Linux or their supported JavaScript runtime.
  Native macOS Pi C++ compilation was not attempted. See the companion
  WsprryPi USB record for final commands and counts.

Reproduction uses the repository's [development instructions](README.md).
The new focused tests are `usb_local_management_tests`, `usb_management_tests`,
`usb_management_vectors`, `field_access_tests`, `http_server_tests`,
`event_storage_tests`, `endpoint_capacity_tests`, `usb_transport_tests` and
optional `usb_descriptor_tests`.
The real-pair driver is `usb_management_driver`; Pi's
`make -C src wtp-usb-pair-client-build` builds its companion client.

## Independent adversarial assessment

Independent read-only review found and drove repairs for AP withdrawal closing
station clients, expiry skipped by recovery early returns, USB identity/boot
admission gaps, uninterruptible management cancellation, stale confirmed names,
inconsistent network restart reporting and concurrent first output-lease
acquisition. Regression checks cover those paths. A final lifetime review also
joins the worker while its callback mutex/state remain alive and protects the
fleet target pointer during cancellation. Physical RF-image testing then
exposed the management reserve failure described above. Its priority/reclaim/
compaction repair and the Pi's bounded reconnect path received a separate
independent reassessment and affected checks. No actionable source finding
remains from that assessment. Pi's production runtime passed 424 checks during the reconnect repair,
including reclaimed management between LOAD and ARM without mutation replay.
The final known-identity contradiction latch and explicit reconciliation
reporting pass independent reassessment; final normal and ASan/UBSan runtime
builds each pass 447 checks.

Four desktop/mobile and light/dark USB settings views were rendered and
reviewed, including saved-progress state. The final station-editor readiness
gate has DOM coverage; screenshots immediately preceding that final disabled
button-state change retain layout evidence rather than exact final state.

## Physical evidence and publication

Pico B is USB serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`, on wspr5. The retained host has a qualified
PPS/chrony clock. Checks use inhibited images and ordinary StandaloneRF at
138 MHz/PIO-DMA GP2 with its preserved disabled scheduler. No transmitter job
is armed and no transmitter RF evidence is claimed. The entire original 4 MiB
flash is backed up and verified twice in the private
`/home/pi/usb-control-20261017` directory. Raw backups/credentials stay outside
Git. The [source manifest](usb-control-source-manifest.json) binds tested source,
SDK/toolchain and exact UF2 hashes; the dirty revision label is explicit.

The repaired RF image passes real production-Pi USB negotiation, deletion of
the last network, explicit restart and no-network readback (empty station IPv4,
no SNTP queries), qualified USB UTC, hostname change, retained station/settings,
and a complete 65536-byte/512-event/3600-second LOAD. Management reconnects and
reads while that job remains resident; explicit ABORT and RELEASE complete
without ARM. This maximum job uses the finite Python WTP/1 bench producer;
management/time use the production Pi USB client and protected browser adapters.
It is not an installed-service or physical ARM qualification. Initial AP advertising is independently observed on the idle
wlan2 interface. AP withdrawal passed while USB read/time traffic continued. The last active
observation was at 583288 ms (17034 ms remaining); at 603902 ms it was expired,
off and at zero remaining. A fresh scan after 615376 ms no longer saw the
target AP, and the unchanged no-network condition did not reopen it. Exact
600000-ms boundary behavior has deterministic tests; the roughly 20-second
physical sampling does not measure absolute RF beacon-stop accuracy. USB
Wi-Fi recreation and replacement then both passed.

Earlier fixture corrections cover an incorrect inhibited-engine name, missing
protected hostname read before restart, the documented empty IPv4 string and
the required ABORT job ID. They are fixture issues, separate from the retained
real RF-image memory finding. Every stopped device run restored and verified
the exact original flash before the next load.

The [sanitized target result](usb-control-target-results.json) records every
AP observation, 31 accepted/selected controller-time exchanges without a
station network, and exact restoration. Observed UTC uncertainty was
56692620–70999115 ns; no existing Pi job threshold or Pico admission bound was
changed to accept it. A job with a stricter configured threshold still refuses.
The original firmware `7bff45c0f32f`, full-flash SHA
`02675b18ea96daca9ee52b95f41bd7f33dea0a5a739fee9fcc68e9e12cc73473` and
watermark match; final output is inactive and scheduling disabled. Pico ports
are released, the scan radio remains disconnected, and the installed Pi
service remains active with its original PID.

Historical Phase 11/14/P15.13 RF acceptance retains its exact image/setup
applicability. This change does not renew conducted RF, absolute launch timing,
blank/engineering/reset AP physical matrices, or unrestricted simultaneous
network/TLS/RF stress qualification. No installed Pi binary was replaced.

## Publication

Pico product `100e749c815f7485d5097c9086852d3b97adca9f` and Pi
`b2160ca39bed539dfd5d39a0c449dd64d37c53a2` are committed and pushed to `devel`,
with independently verified remote parity. The Pi dedicated USB CI pin selects
that exact Pico product; existing network and historical pins are unchanged.
Both normal Pico targets also rebuild from the clean product commit, label
`100e749c815f`; their separate hashes are in the source manifest. The eight-byte
text-size difference is revision-label metadata, not a different tested source.

Pico product [Pages deployment](https://github.com/WsprryPi/WsprryPico/actions/runs/39039281873)
passed. Pi [USB production-pair CI](https://github.com/WsprryPi/WsprryPi/actions/runs/39039613596/job/117416237007)
passed. All seven historical compatibility jobs, the macOS simulated profile
and strict I2C profile also passed in that run. At this record's publication,
the broader Linux release, non-hardware and network-loopback jobs are still
running; no full-workflow pass is claimed. This follow-up documentation commit
does not alter the product source or its exact USB compatibility pin.
