# R3 v2 F1 fresh finite host fixture

Reviewed under accepted R3-COMPLETE-20260913-v2 and the user clarification
to retain the tested image except for a demonstrated code defect. B is read-only.

Execute only after H2b completes, all F0 child workloads stop, and F0's owned
cleanup is verified. This packet creates a fresh session; it does not extend F0.
Zero USB opens, RF, flashes, BOOTSEL, device Wi-Fi cycles, CONFIG saves or heap
probes. Reuse the same retained Wi-Fi input and fixed 60 dB physical wiring.

Use the established wlan0 AP/wlan2 client namespace. Preserve eth0/wlan1
management, installed WsprryPi, permanent timing/GPSD/PPS/Avahi configuration.
Arm owned cleanup before mutation: at most 28800 seconds execution and 900
seconds cleanup. Capture association/DHCP before AP activation. Record the
actual client PID, namespaces, setup identity and absolute cleanup deadline.
Future packet budgets must fit before that original deadline. Do not start RF
from fixture setup. Preserve and verify all owned cleanup at completion.

The existing v2 fixture runtime boundary tests pass; its previously exercised
F0 helper bytes are reused unchanged. Fixture setup itself earns no target RF
acceptance. Missing or changed helper/private-input hashes fail before setup.

- `packet_sha256`: `62eb27cfc8de9eb427f98aedb3c0382bc2971b5fd08206b2ebb5cd4ad335f432`
- `archive_sha256`: `c55264e692a20510908fdf97f6634ed578e1d769f9586faa94109dbdc3689aaa`
- `root`: `/home/pi/phase11-5-r3-v2-fixture-f1-20260913`
- `stager_sha256`: `1751e78a2527d5a912ae326218409f4ce864ba116f08d58d3eefd8d3b52f2e18`
- `runner_sha256`: `3d7f185ac3c058d6288a706acf768befa2e80ee0086ca8d94d8367d37913c531`
