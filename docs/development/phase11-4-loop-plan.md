# Phase 11.4 B2/D2 repeated failure localization

## Review and execution prompt

Start from Pico devel `59c01ed35797adecfbe96f1832e6681cde599ed7`, preserving the
withdrawal investigation's failed observations. Review B2 Linux NSS and D2 orderly
withdrawal as separate gates. The installed standard inhibited diagnostic UF2 is
`524dd721ed6f67fbb21b1544546014fa174a4cb5d92d69d5fdfdbe5138f38664`, build revision
`e4ff40a56180-dirty`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`, serial
`0BF4B4AEC9FFB344`, boot `f40c48f2e8b61b0da9743f1504ae4f2e`. Verify that identity
and authoritative inactive/unowned state before each mutation. No firmware flash
is part of this campaign. Existing user authorization covers repeated inhibited
USB WIFI OFF/ON, read-only status, Linux captures and native Mac network reads.

The prior repair adds a one-second withdrawal opportunity; selected wire evidence
proves goodbye delivery but repeated peer recovery and one watchdog remain open.
Earlier synchronous DNS/HTTPS checks blocked USB sampling. The new harness must
sample Console independently, retain raw WTP bytes without allowing decoder
resynchronization to hide malformed input, and record Linux packets and native
Mac observations independently. Network failure must not stop USB evidence.

Run up to eight full cases, each with a 150-second OFF interval, six distributed
negative Linux lookups after the goodbye grace period, a 40-second local activation
bound, and at least five successful authenticated peer checks spanning 30 seconds
within 120 seconds of ON. Record the first failed lookup/read; subsequent recovery
never erases it. Use only INFO, HELLO, CAPS, STATUS and WIFI OFF/ON. Keep schedules
disabled and saved station, schedules, watermark, expiry and journals unchanged.
Keep the original wspr5 USB wlan1/Bohica profile, source address and recovery
service active/boot-enabled; observe association throughout and reject path drift.
Do not change onboard wlan0, router, reservations, trust, installed services or RF.

Before each case, require a native Mac Add callback and successful DNS plus
certificate-verified HTTPS baseline. During the case, retain native callbacks and
periodic DNS/direct-address HTTPS reads with certified hostname verification.
Linux captures mDNS and ARP/TCP/DHCP separately with startup-header/liveness checks
and final packet/drop counts. A separate USB thread samples INFO every 250 ms;
record actual gaps, errors and memory counters. Mac/Linux clocks are not assumed
synchronized for subsecond comparisons. Aggregate Pico counters are not packet
identity and cannot locate a frame inside the radio or AP.

After the first Linux failure, send three ordinary broadcast ARP requests and
three explicitly addressed unicast ARP requests, inspect the neighbor state and
probe TCP. Preserve the failing state before these diagnostic interventions.
Compare Linux failures with Mac authenticated observations and packet receipt.
Do not change neighbor entries, flush caches or promote the probe's success into
acceptance. A read-only post-case USB inspection must retain a new watchdog
breadcrumb if the device rebooted. A fresh recovery boot is never automatically
reset/flashed by the harness.

## Stop rules fixed before execution

- Stop with **failure point detected** only for an identity-bound watchdog at
  breadcrumb 15 (final mDNS removal) or 16 (station disable), or a captured valid
  unicast mDNS answer arriving at Linux during a failing NSS lookup. These locate
  an execution or delivery boundary, not necessarily the underlying root cause.
- Stop with **harness ineffective** for an observer/identity/path/capture defect,
  three unresolved failed cases, or exhaustion of the eight-case budget without
  either other conclusion. Explain the missing measurement rather than repeat
  the same evidence indefinitely. Repair actionable harness defects, test them,
  and begin a separately retained campaign if useful.
- Stop with **not reproduced in this bounded campaign** only after eight full
  clean cases with strict per-case acceptance audits. This is not permanent
  reliability or overnight leak-freedom proof. Preserve all historical failures.

## Implementation and supervision

`scripts/phase11_4_loop.py` runs on the Mac and stages only its Python helper
sources in a new owner-only directory below `/home/pi/phase11-4-acceptance`.
Each Linux case runs as a transient systemd unit with a 480-second runtime limit
and 20-second stop limit; it survives loss of the coordinating SSH connection.
Its own finally block attempts identity-checked WIFI ON and cleanup, and capture
children receive bounded INT/TERM/KILL escalation. Mac observers have independent
subprocess deadlines. Loss of USB authority or a recovery boot blocks automatic
mutation and is reported, not treated as proof of inactive output.

Raw captures, logs, firmware and credentials remain ignored/private. The maintained
record contains outcomes and a SHA-256 evidence index, never credential bytes.
The helper accepts only the explicitly named target and requires `--run`;
optimized Python is refused because the inherited target checks use assertions.

```sh
python3 -B tests/phase11_4_loop_tests.py
python3 -B scripts/phase11_4_loop.py --run \
  --output build/phase11-4-loop/campaign-1 \
  --credentials config/local/network/phase11-4-fd6127d1 \
  --boot f40c48f2e8b61b0da9743f1504ae4f2e
```

Execute network/native DNS/SSH operations outside the restricted sandbox. After
execution, adversarially inspect both implementation and retained evidence. Fix
and retest actionable findings, reassess, verify final device/host state, update
the matrix, commit and push the owned changes, and report the actual stop reason.


## Post-execution review clarification

The preserved automated stop counts failed cases, not identical root causes.
Review subsequently annotated a short TLS reset while USB clock samples remained
unsynchronized, matching the existing server admission guard. This annotation
requires a matching captured Pico reset and bracketing USB evidence and does not
turn the original failed case into PASS. The runner's recovery deadlines and the
existing acceptance auditor remain unchanged. New failed transient-unit state is
cleared only after evidence is retained, without resetting unrelated units.
