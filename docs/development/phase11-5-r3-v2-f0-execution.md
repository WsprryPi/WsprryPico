# R3 v2 F0 host fixture

Reviewed under accepted R3-COMPLETE-20260913-v2. This host-only packet has
zero RF, flash, BOOTSEL, Wi-Fi device cycles, CONFIG and heap-probe operations.
It creates the established isolated wlan0 AP / wlan2 client namespace using
the retained test Wi-Fi input, authenticated by its existing hash. Management
eth0/wlan1, installed wsprrypi and permanent timing configuration are preserved.

The existing ownership-recorded fixture now accepts the selected v2 runtime
only for this explicit schema and standing authority: at most 28,800 seconds
execution plus 900 seconds restoration. Old packet runtime limits stay unchanged.
Cleanup is armed before host mutation and owns only the temporary radios, AP
profile, namespace, chrony ACL, time.local override and recovery-timer pause.
It never opens USB or changes Pico output. Setup failure invokes owned cleanup.

Start the early association/DHCP capture before AP activation. Later finite RF
tranches receive their own reviewed packets and must fit the remaining fixture
lifetime. Do not extend a running fixture silently or treat its timer as RF
authority. A new fixture requires a new reviewed packet and reconciled cleanup.

Two pure runtime/legacy-scope tests pass. F0 grants no physical acceptance by
itself. Record actual verified setup and restore this fixture at completion.

- `packet_sha256`: `6f918d448f2aa9099a797408cceb0adff6e10f3ebeaec3d304ab18f524140695`
- `archive_sha256`: `6bbb89fef1160a45dc8f406490ab16277033f093a6d0589034edf768c15fa5a4`
- `root`: `/home/pi/phase11-5-r3-v2-fixture-f0-20260913`
- `stager_sha256`: `1751e78a2527d5a912ae326218409f4ce864ba116f08d58d3eefd8d3b52f2e18`
- `runner_sha256`: `3d7f185ac3c058d6288a706acf768befa2e80ee0086ca8d94d8367d37913c531`
