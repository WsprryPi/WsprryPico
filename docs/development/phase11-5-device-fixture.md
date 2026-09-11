# Phase 11.5 N1 device and management packet

Status: **AUTHORIZED AND EXECUTED; first attempt restored after an INI failure.**
See the [current continuation record](phase11-5-n1-progress.md). The body below
is the historical frozen N1 packet; its initial identities are not current state. The existing flashing/RF
authorization remains recorded. This packet consolidates the remaining network,
USB management and isolated-process operations required by section 5 of the
original request. It does not accept a configuration or close an A-G case.

The [frozen packet](phase11-5-device-fixture.json), SHA-256
`fa146299a79664c17b67385494950a3a326936062639a8e5848c37152a88cc87`,
binds the helper closure,
private input digest, exact images and separately built production executable.
The private prepared directory is `build/phase11-5-closure/n1-stage`; it was staged to wspr5 for the first attempt. Remote root: `/home/pi/phase11-5-n1-6e2ddc9`.

## Exact identities and limits

- Pico A: USB `0BF4B4AEC9FFB344`, WTP
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, initial inhibited boot
  `e3634081a2c5844524ab64eb2afeab71`.
- Pico B remains read-only: USB `CDDBF8767C506C07`, WTP
  `29f20b7342051ef947aa56cb9d4fab42`, inhibited `dbf1d86f0885-dirty`, boot
  `4e2fb851c08b278dd4b977104d2c2aaa`.
- Candidate source `6e2ddc9e476986046de74d18cbcc3a2f6b64d142`. Network-enabled
  inhibited UF2 `822a7c28617592c28f4f03996b009a66ee32199816a467756b314abf63e41a71`
  is the separate 150 MHz idle baseline. Physical UF2
  `ba74b33ec7fd7530a56cc679799d9f452f08d896d22930903ef8bba132387a4d`
  uses **138 MHz, PIO divider 1 and the SRAM renderer**, with an enforced 4 KiB
  MSP reserve on each active core. The [four linked image records](phase11-5-lifecycle-images.json)
  do not establish target execution. Physical 132/150 MHz remain untested.
- Original inhibited restoration UF2:
  `25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`.
  Verify its application blocks and the current CRC-valid configuration journal
  against the backup before loading a candidate. Never select the first USB board.
- wspr5 boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`; management uses verified
  Ethernet IPv6. Installed WsprryPi remains PID 1957 with its recorded binary/INI.
- The separately built application is source `fb0a2eb50c1ea1792324139412990341592db452`,
  SHA-256 `08af5ad6dd21592a7ff90d898dd971a1e740cbb3836f65e74ba3816b960f4507`.
  It was built with `BACKENDS=simulated ANCILLARY_GPIO=0`; explicitly select WTP
  at runtime. Its private INI disables startup transmission and all ancillary
  GPIO/selector functions, fixes correction at zero, and uses ports 31425/31426.
  The client namespace preserves singleton port 1234 without changing the check.

## Consolidated operations

1. Recreate the restored N0 topology in a fresh private root: wlan0
   `2c:cf:67:62:76:66` as the isolated AP and wlan2 `e8:4e:06:ae:d7:09` as its
   independent client. Preserve ordinary wlan1 and Ethernet. Temporarily pause
   the recovery timer and allow chrony only for `10.77.15.0/24`. Restore all
   owned host resources within six hours, including the original power saving.
2. Explicitly enable fixture DNS on `10.77.15.1` for
   `clock.phase115.test -> 10.77.15.1`, with 30-second local TTL, no hosts-file
   input, upstream resolver, forwarding or client default route. DHCP advertises
   that DNS address. This allows actual time-server DNS/SNTP competition to be
   observed. The completed N0 run used a numeric address and cannot prove it.
3. Back up A, load the clean inhibited candidate, save its temporary test Wi-Fi
   and clock hostname, and perform one acknowledged configuration reboot. Keep
   schedules disabled. After its idle baseline, switch once to the exact physical
   image, preserving configuration and watermark. Every intentional boot gets
   a new recorded admission inventory; an unexpected boot blocks transitions.
4. Permit at most **32 successful configuration journal writes**, including
   original restoration. The only temporary schedule variant changes its phase
   from zero to one second while keeping it disabled. Preserve station identity,
   expiration and watermark. Reserve the last write for restoration. E2's
   predeclared busy-state attempts must be rejected by firmware; a host-side
   refusal alone cannot count as target E2 evidence.
5. Permit three idle-only Wi-Fi OFF/ON cycles, 150 seconds OFF each, with recovery
   measured against 120 seconds. Permit at most 64 idle-only allocation probes,
   bounded by linker heap capacity plus one byte; the latter intentionally tests
   allocation failure. Never probe or perform management writes during an RF job.
6. Permit one fixture DHCP binding change `.10 -> .20`, retaining the certified
   name, and one external AP loss commanded for 15 seconds. The AP return has a
   separate owned timer armed before loss, plus an idempotent return path. No
   Pico reset or idle-gate bypass is used to manufacture these network cases.
7. Run the private production application, its opt-in TLS observer, and the
   authenticated browser load in the independent client namespace. Use the
   exact checked credentials, ordinary production STATUS policy and common N
   rates from the [matrix](phase11-5-plan.md). Keep USB and host-health observers
   independent. The load driver submits no RF jobs and requires an independent
   raw-wire/rate audit even after a clean process exit.

Device work is bounded to five hours, with ten minutes for restoration. The
host fixture cleanup is armed for 5 h 50 min, with ten minutes to finish. Device
admission refuses a host fixture lacking the full remaining restoration window.
The elapsed N0 window is therefore not reused. New units are confined to the
existing `phase115-closure-*` fixture family, its two owned link-return units,
and `phase115-device-n16e2ddc9.{timer,service}`.

## Execution and stop rules

Before staging, verify all frozen digests against the prepared directory and
confirm the restored host/Pico state. Stage private files with owner-only access.
The host fixture is created first; the device lifecycle then arms restoration
before its first BOOTSEL or configuration operation. The three lifecycle entry
points are `phase11_5_device_fixture.py start`, `switch`, and `restore`, each
requiring `--root /home/pi/phase11-5-n1-6e2ddc9 --run`.

The management helper checks exact boot, firmware, clock, engine, both relevant
stack guards, preserved fault indicators, authoritative empty/unowned state and
an active owned restoration timer. Administration reuses one recorded logical
WTP session with fresh request IDs; ordinary journal writes do not exhaust the
session table. It records intent before a write. Missing or
ambiguous replies block subsequent management; they are never interpreted as
successful configuration or inactive RF. The firmware's own idle gate also
handles ownership arriving after the host's last observation.

Run A2 and A3 before advancing through the remaining short cases. Keep each
case's workload, finite jobs, expected failures, observer identities and actual
payloads frozen before its execution. The full A-G case coordinators and raw
acceptance assessments remain work to execute; these prepared lifecycle/load
tools do not replace those cases. G1 remains conditional on passing A-F. The
existing RF authorization applies to the confirmed 50-ohm, 60 dB, unfiltered
conducted path and finite jobs in the selected 138 MHz campaign. N1 itself
contains no RF job submission or new band/clock sweep.

On an unexpected failure, stop dependent work and retain evidence. The device
restorer may proceed only on the last recorded boot with authoritative empty,
unowned, inactive state, unchanged watermark and no preserved device/RF fault
or ambiguous management write. It saves original configuration, loads the
original inhibited UF2 and verifies both boards. Otherwise it records a blocker
and does not reset or clear the device. Host-only cleanup remains independent.

## Validation and limits

The clean images pass linked stack/layout, allocator-route and renderer checks.
The actual production pair passes native interoperability in both directions.
The management/lifecycle tests reject changed identity/boot, missing guards,
faults, ownership, ambiguous outcomes, corrupt journals, exhausted write/probe
budgets and missing restoration admission. Host tests cover cleanup convergence,
ownership and explicit DNS opt-in. Installed dnsmasq accepts the isolated DNS
syntax without starting a server. The TLS observer passes eight concurrent
mutual-TLS streams and six corrupted-log cases; load tests retain failure after
an exception even when the child exits cleanly.

None of this is on-target N1 acceptance. The original P1 failure, later P2/P3
diagnostics and N0's first cleanup failure remain preserved. The accepted
configuration list stays empty until all required physical gates pass.

Documentation Impact: lifecycle packet, exact image records, host-fixture result,
joint plan/register/review and companion review. WTP, shared identity, browser
API and architecture contracts are unchanged. The operator-manual follow-up
paths remain those listed in the joint plan; that repository is unchanged.
