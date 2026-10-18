# mDNS responder integration

[Hostname management](hostname.md) boot selection may supply an explicitly saved consumer hostname instead of the MAC-derived default. It applies at restart to both station and AP naming; conflict latching, no auto-suffix, actual advertisement, listener coupling and bounded cleanup stay unchanged. The packet/adapter tests remain software evidence.

The [shared identity contract](network-identity.md) selects one certified IPv4
station hostname. Discovery runs only on core 0 in the existing foreground
CYW43/lwIP context. The later WTP DNS-SD extension advertises an admitted
station WTP listener as described below; there is no discovery client in firmware.
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
- The upstream responder does not emit Goodbye packets. Controlled disable uses
  upstream packet generation for the same A/PTR records, sets their TTLs to zero, then sends
  before disconnect. Submission is separate from
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

## WTP DNS-SD beta extension

The same pinned responder publishes `_wtp._tcp.local.` on the station netif
when an admitted WTP/TCP listener is active. It uses the station hostname label
as the instance name, the actual listener port in SRV, and exactly two TXT
entries: `txtvers=1` followed by `binding=tls` or `binding=plain`. The TXT version
does not version WTP/1. No WTP service is registered on the provisioning SoftAP.
See the [DNS-SD profile](../protocol/WTP-DNS-SD.md) for client and trust rules.

The foreground loop observes the listener after the server polls. A change to
the binding or port, or loss of admission, sends a zero-TTL service PTR goodbye
with zero-TTL SRV/TXT additions while the station is usable, drains for one
second, removes the old responder registration, and reprobes the current
hostname and service. Link or address loss quiesces the responder immediately.
If service allocation fails, registration is rolled back and the existing mDNS
failure state is reported; no partial service is announced. The one-service
limit matches the product's selected single WTP/TCP binding.

Pinned lwIP host tests inspect the emitted PTR, SRV target/port, TXT bytes and
service goodbye; adapter tests exercise station-only registration, binding/port
changes and removal. These tests do not establish physical Pico/CYW43 multicast
delivery or receiver cache behavior.

## Resource bounds and measurements

The firmware keeps its 32,768-byte lwIP heap and eight-packet pool. mDNS adds one
of three UDP PCBs (the others serve DHCP/SNTP), one netif client-data slot, IGMP
with three bounded group slots, and eight timeout slots beyond
`LWIP_NUM_SYS_TIMEOUT_INTERNAL`: probe, two delayed replies, three cooldowns and
two truncated-question slots. The responder keeps at most two incoming packets,
each admitted only up to 1,472 payload bytes. Output payload allocation is 512
bytes plus lwIP headers/metadata. `MDNS_MAX_SERVICES=1` preserves standard arrays
in upstream structures. The original hostname-only measurements below allocated
no service object; the WTP extension allocates one while the listener is
advertised. Search is disabled.
The fixed pools and packet parser bound memory use; hostile traffic can still
consume core-0 time, without establishing physical contention bounds.

Whole-image RAM, text, heap and compiler stack frames depend on the exact
firmware build. Fixed-pool growth reduces available heap; compile-time bounds
are not measurements of physical stack high-water or fragmentation. The
responder runs on core 0 and never on the RF worker stack. The TLS allocation
cap and shared application memory reserve still apply.

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
cache behavior.
