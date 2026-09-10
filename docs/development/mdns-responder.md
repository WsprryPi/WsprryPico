# Phase 11.3 mDNS responder integration

The [shared identity contract](phase11-3-identity.md) selects one certified IPv4
station hostname. Discovery runs only on core 0 in the existing foreground
CYW43/lwIP context. There is no DNS-SD service advertisement or discovery client.
The stable default uses the final six hexadecimal digits of the station MAC
read by the Pico after Wi-Fi initialization: `wsprrypico-0a60df.local`, for
example. It is empty before a valid MAC read. The full WTP ID independently
binds deployment credentials. Legacy IP-only builds report the short default
after initialization but do not advertise it.

## Pinned implementation and narrow wrapper

SDK 2.3.0 commit `98a542c1a62fb549ffb5d66a3e5892b06276b670` supplies lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`. The linked responder is its maintained
`src/apps/mdns/mdns.c`, `mdns_out.c` and `mdns_domain.c`. The dependency gate
verifies the pin/clean SDK. The host test independently verifies clean lwIP and
the same pin. No SDK or third-repository file is modified. The upstream
[BSD notice](../licenses/lwip-mdns.txt) is retained alongside the existing
[lwIP license](../licenses/lwip.txt).

Initial review found three API gaps in this exact source:

- `mdns_resp_init()` returns void and asserts on allocation or port binding
  failure. The adapter initializes its private state with checked failures.
- `mdns_resp_remove_netif()` cancels only the probe timer. Five delayed IPv4
  reply/cooldown callbacks still dereference the freed helper, and truncated
  questions retain packet chains and timers. Removal cancels all six netif
  timers and every retained question/answer for that interface before freeing.
- Goodbye packets are an upstream TODO. Controlled disable uses upstream packet
  generation for the same A/PTR records, sets their TTLs to zero, then sends
  before disconnect. The later Phase 11.4 investigation splits submission from
  teardown: replies/timers and retained questions are quiesced immediately, while
  membership and the station remain until a nonblocking one-second withdrawal
  interval finishes. CYW43 bus-write success does not establish radio completion.
  Diagnostics count attempts and local send errors; they do not assert reception
  by another host.

`src/standalone/pico/mdns_lwip.c` includes the immutable pinned responder
translation unit to access that private state. It compiles the other two source
files normally; it must not also link `pico_lwip_mdns`. An upstream upgrade needs
review of these internal seams and the packet/cleanup tests before repinning.

## Lifecycle and bounded failure

`network::Mdns` is portable and owns state, latching and counters. `PicoNetwork`
uses `cyw43_state.netif[CYW43_ITF_STA]`, never the default routing interface.
One global mDNS UDP PCB and client-data ID are initialized once per boot; repeated
Wi-Fi disable/re-enable retains these fixed reservations. Per-registration heap,
IGMP membership, all timers and retained packet chains are removed each cycle.
CYW43 partial startup failure unwinds before any mDNS initialization.

A usable station address and configured/listening certified deployment permit
registration, probing and announcements. The name-result callback publishes
active state only after probing succeeds. Address/link callbacks immediately
quiesce timers and replies; foreground polling removes the old registration and
reprobes the same name against the current address. New unique A announcements
carry cache flush; receivers following RFC 6762 expire superseded values after
one second. This does not prove an operational LAN cache updated correctly.

Both probing conflicts and upstream's established-name conflict/reprobe path
latch `conflict`. Callback teardown is deferred until the responder returns;
the callback immediately quiesces it to prevent intervening replies. No automatic
rename occurs. Probe/tiebreak activity is bounded by a 30-second deadline.
Initialization/registration/probe-timeout errors latch `failed`; normal polling
does not retry. Explicit idle-only off/on retries the same name. Wrong-board
identity failure is permanent until a corrected build/reflash or reboot with
correct credentials. None of these failures modifies a WTP owner or finite job.

During orderly withdrawal, `withdrawing` has an empty advertised name. The
foreground loop continues driver polling and USB/job servicing without rejoining
or answering mDNS queries. Final removal releases retained registration/membership
before station teardown. Repeated OFF does not extend the bound; rapid ON waits
for final teardown before recreating/reprobing. The one-second interval is an
engineering transmission opportunity, not a protocol delivery guarantee.

Physical loss removes local state without pretending a goodbye was sent.
Already cached remote records can remain until their TTL expires. Recovery boot
does not initialize Wi-Fi, TLS or mDNS. Network-control-disabled builds allocate
no mDNS PCB or host helper and make no discovery announcements.

## Resource bounds and measurements

The firmware keeps its 32,768-byte lwIP heap and eight-packet pool. mDNS adds one
of three UDP PCBs (the others serve DHCP/SNTP), one netif client-data slot, IGMP
with three bounded group slots, and eight timeout slots beyond
`LWIP_NUM_SYS_TIMEOUT_INTERNAL`: probe, two delayed replies, three cooldowns and
two truncated-question slots. The responder keeps at most two incoming packets,
each admitted only up to 1,472 payload bytes. Output payload allocation is 512
bytes plus lwIP headers/metadata. `MDNS_MAX_SERVICES=1` preserves standard arrays
in upstream structures, but no service object is allocated. Search is disabled.
The fixed pools and packet parser bound memory use; hostile traffic can still
consume core-0 time, which remains a physical contention gate in 11.5.

The isolated 64-bit host reports a 224-byte host helper and 56-byte retained
packet descriptor. Its normal peak lwIP heap use is 1,744 bytes; forced startup
exhaustion is excluded from that highwater (the failure test intentionally fills
all 32,768 bytes). The measured timeout peak is nine slots including core-stack
timers; one UDP PCB remains after cleanup. Host sizes are not RP2350 sizes.

The pinned Arm GNU 15.3.1 compiler emits constants of **192 bytes per host** and
**40 bytes per retained-packet descriptor**. In the linked ARM image, the two-slot
descriptor pool occupies 83 bytes including alignment allowance; the IGMP group
pool is 51 bytes, and the timeout pool increases from 83 to 227 bytes. The
`PicoNetwork` static object grows from 176 to 320 bytes. Total image BSS growth is
568 bytes in all four variants; remaining growth includes netif client data,
callback/PCB pointers, flags and diagnostics. UDP and lwIP heap/pbuf pool sizes
remain unchanged. Fixed pools remain reserved even in network-control-off images.

The software build snapshot after implementation, compared with the preserved
11.2 baseline ELFs, is:

| Image | Control | Text bytes | BSS bytes | Linker heap span bytes |
| --- | --- | ---: | ---: | ---: |
| Inhibited | Off | 955,408 | 82,436 | 413,244 |
| StandaloneRF | Off | 977,684 | 268,404 | 226,948 |
| Inhibited | Hostname TLS | 980,280 | 82,480 | 413,184 |
| StandaloneRF | Hostname TLS | 1,002,532 | 268,448 | 226,896 |

These text sizes include all Phase 11.3 changes and ephemeral credential material,
not only the responder. The reviewed baseline text/BSS pairs were 924,552/81,868,
946,556/267,836, 948,232/81,912 and 970,244/267,880 respectively. Credential renewal
can alter text size. The original 11.2 physical network heap span was 227,464
bytes, so the fixed growth leaves 13,904 bytes beyond the previously enumerated
212,992-byte simultaneous maxima/reserve sum. As in 11.2, that is insufficient to
promise all maxima together once other allocations/fragmentation are considered.

Compiler `.su` records include a 2,104-byte `mdns_handle_probe_tiebreaking` frame,
1,112-byte response frame and 856-byte sorted-answer frame; call chains add their
callers. `PicoNetwork::status()` has a 2,128-byte frame. These are individual static
frames, not a measured stack highwater; the 16-KiB core-0 stack is unchanged.
The responder never runs on the RF worker stack. Physical stack/allocator and
contention acceptance remain open in 11.5.

Measurements used `build/phase11-3-firmware-off` and
`build/phase11-3-firmware-on`, `arm-none-eabi-size`, `arm-none-eabi-nm`, the
`wsprry_mdns_{host,packet}_bytes` object disassembly and compiler `.su` outputs.
Whole-image final checks and exact committed inputs are recorded in the joint review.
The existing TLS allocation cap, application scratch reserve and shared memory
admission remain unchanged; static-pool growth reduces the linker heap span.

## Reproduce deterministic acceptance

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DWSPRRY_PICO_TEST_LWIP_PATH=/path/to/pico-sdk/lib/lwip
cmake --build build-host --target mdns_tests mdns_lwip_tests network_adapter_tests --parallel
ctest --test-dir build-host -R '^(mdns_tests|mdns_lwip_tests|network_adapter_tests)$' --output-on-failure
```

The actual responder target also derives the lwIP sibling when the pinned
`WSPRRY_PICO_TEST_MBEDTLS_PATH` is supplied. Tests inject DNS payloads through the
real bound UDP callback with an isolated lwIP netif/clock and capture generated
IPv4 packets in memory. They exercise real probing/announcements, cache-flush A
replacement, zero-TTL A/PTR goodbyes, established conflicts, truncated retention,
PCB/bind/heap/IGMP failures, malformed/cyclic-compression/oversized packets,
immediate link/address quiescence, 100 full registration/cleanup cycles and ten
real lwIP netif removal/recreation cycles matching station disable/re-enable.
The `network_adapter_tests` target links the actual PicoNetwork implementation
and pinned lwIP with mocked SDK operations. It models delayed radio delivery,
checks continued polling and retained multicast membership, and exercises rapid
ON/OFF, cancelled HTTP changes, link loss and 50 resource-stable cycles. It does
not model real synchronous driver IOCTL timing or establish target reliability.
Portable tests cover disabled/legacy/identity failure, 30-second probing limits,
conflict deferral, explicit retry and address-change accounting.

These are actual pinned-responder parser/packet and simulated netif lifecycle
results. They use no sockets or operational multicast and prove neither system
NSS resolution nor physical Pico/CYW43 multicast delivery, RF timing or receiver
cache behavior. Those acceptance steps remain 11.4–11.6.
