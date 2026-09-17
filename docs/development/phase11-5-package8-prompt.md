# Phase 11.5 Package 8 execution prompt

Status: **AUTHORIZED FOR EXECUTION** by
`phase11-5-completion-authorization-20260915.md`. This packet closes only R5,
and only if every mandatory row below passes. Preserve all earlier attempts and
keep Phase 11.5 OPEN if any row lacks direct evidence.

## Objective

Close the network, storage and autonomous-lifecycle family without turning the
work into an endurance campaign. Demonstrate one controlled address change and
one external AP loss during a finite RF job, then one saved autonomous WSPR job
whose preparation, durable watermark, physical execution and completion remain
local to the Pico while normal management observers compete. Cross exactly one
configuration-journal bank boundary with the fewest writes allowed by the live
journal position, and restore the retained disabled configuration.

Required assertion IDs:

- `R5.link-loss`: external isolated AP loss begins while RF is Running; USB
  independently proves uninterrupted local authority and one completion; the
  same boot returns to authenticated service.
- `R5.address`: dnsmasq changes the named Pico lease from `10.77.15.10` to
  `10.77.15.20`; the certified stable name resolves to the new address and
  authenticated WTP/HTTPS recover without changing certificate or device.
- `R5.wifi`: admit the already accepted current-source idle OFF/ON evidence only
  after an exact source-impact review. Do not spend another cycle merely to
  duplicate it.
- `R5.dns-sntp`: capture name resolution and SNTP traffic plus target counters
  while the RF/network lifecycle runs; require accepted time recovery and
  authenticated management recovery with no rejected time sample used as a
  substitute.
- `R5.persistence`: save only through the authenticated JSON API, reboot once,
  and prove the exact saved schedule/station/network values persist. During the
  autonomous job, an attempted Console `CONFIG` must return `busy`, leave the
  journal sequence unchanged and leave local RF authority intact.
- `R5.rotation`: read the live configuration-journal sequence, offset and record
  size before any save. Freeze either two or three total saves: one enabled
  schedule plus restoration when the next save rotates, or one disabled
  preparatory save, the rotating enabled save and restoration when it does not.
  Require the observed post-save offset to cross banks. Do not erase journals,
  reset counters or add writes.
- `R5.time-admission`: after the one reboot, observe the enabled schedule with an
  unsynchronized clock, unchanged watermark and no prepared job; then observe an
  accepted SNTP state before the same frozen occurrence is reserved.
- `R5.schedule`: acquire the shared two-board RF reservation before enabling the
  schedule. The Pico must reserve the occurrence, prepare and complete its local
  162-symbol WSPR job with a 135,500 Hz base and native WSPR tone shifts without
  USB/network `LOAD`, `ARM` or time
  injection. Retain the exact N/M observations, durable watermark and one
  terminal completion. Restore the original disabled configuration before
  releasing the reservation.

## Baseline and boundaries

- Work only in `/Users/lbussy/GitHub/WsprryPico` and the fresh private wspr5
  evidence root. WsprryPi is an observer/fixture dependency; do not edit its
  repository or replace the installed application.
- Candidate board A is serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`. Comparator B is serial
  `CDDBF8767C506C07`, device `29f20b7342051ef947aa56cb9d4fab42`.
- The physical configuration remains Pico 2 W/RP2350 Arm, 138 MHz, divider 1,
  GP2 PIO/DMA, RAM rendering, nominal 135,500 Hz conducted RF.
- Start from pushed `devel` commit `9fa5946553c0976307aafea3118961cc5169918c`.
  A initially runs source `2b25ca05c270819466a04498f9bc4894a4c5bace`,
  image `16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`
  and boot `80d558e5804547749eca849c53ba27e1`. B initially remains in boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- The retained A configuration is disabled, station `AA0NT` / `EM18` / 20 dBm,
  schedule `120/0`, expiry zero, isolated SSID `WsprryPico-Phase115`, time
  server `time.local`, and watermark `1788714601000000000` ns.
- Source credentials, raw wire data, packet captures and flash artifacts remain
  owner-only outside Git. Publish only hashes and redacted derived facts.
- One shared reservation covers both RF jobs and both boards. B may perform only
  read-only inventory while it is held.

## Pre-execution implementation and evidence controls

1. Review README, CONTRACT, architecture, development baseline, the current
   matrix/ledger, this prompt, the authorization, storage/scheduler/network code,
   and the historical standalone/network results.
2. Add one read-only Console `STORAGE` diagnostic exposing only journal health,
   sequence, latest relative offset and record size. It must not expose retained
   configuration or credentials, mutate flash, alter normal INFO, or add an RF
   code path. Test empty, populated and rotated positions.
3. Extend the existing isolated fixture only for the exact Package 8 authority:
   R5, retained `time.local`, two or three configuration writes, at most 7,200
   seconds execution plus 900 seconds cleanup. Preserve its write-ahead cleanup,
   host/radio identity checks, recovery-timer restoration and credential
   redaction.
4. Build the physical image with the pinned Pico SDK 2.3.1, GCC 15.3.1 and
   `WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ=135500`. Require `STATUS` to
   report base `135500000000000` nHz and every autonomous tone to remain inside
   135,490--135,510 Hz. Run the registered host suite and linked-image checks.
   Commit the candidate source
   locally so the embedded revision identifies an immutable tree.
5. Under a zero-RF deployment packet, inventory both boards as inactive,
   schedule-disabled and unowned; acquire the reservation; perform at most one
   A BOOTSEL transition and one verified flash; prove preserved configuration,
   healthy storage, expected 138 MHz/RAM/GP2 engine and unchanged B; release.
   A failed or uncertain flash leaves the reservation held for reconciliation.
6. Read `STORAGE` on the deployed image before any CONFIG. From record size 2048
   and two records per 4096-byte bank, freeze the exact write plan. If the live
   position cannot cross exactly one bank and restore baseline within three
   saves, stop R5.rotation OPEN without writing.

## Run A: network recovery

1. Create a fresh private fixture root with a 7,200-second work limit and
   separately armed 900-second cleanup. Verify host boot, Ethernet, wlan1,
   wlan0/wlan2 MACs, installed WsprryPi binary/service, recovery timer and
   permanent `time.local` publisher before mutation.
2. Start the isolated AP, independent wlan2 namespace, DHCP, permanent-source
   `time.local`, NTP allowance and lossless AP/client captures for mDNS, DHCP,
   NTP, ARP and TCP/18443. Use retained Wi-Fi credentials by hash.
3. Require A at `10.77.15.10`, synchronized, advertised under
   `wsprrypico-0a60df.local`, authenticated by the fixed server certificate and
   inactive. Require B independently inactive and schedule-disabled.
4. Acquire the shared reservation from fresh A/B inventories. Submit exactly one
   240-second, single-event 135,500 Hz Tone job through authenticated WTP and
   observe Running/output-active over USB.
5. While Running, change only the owned dnsmasq binding to `10.77.15.20` and HUP
   the owned process once. Then use the existing independently timed helper to
   bring the owned AP profile down for 15 seconds and back up. No Pico Wi-Fi
   command, reboot or job resubmission is permitted.
6. Maintain a persistent USB observer across the outage. Require the same
   job/boot/owner through loss, exactly one complete terminal record, no DMA,
   refill, stack, allocator, clock or reset fault, and inactive output afterward.
7. Require real DHCP packets for the new lease, name answers containing only
   `10.77.15.20`, two native resolver successes, authenticated HTTPS and WTP at
   the new address, accepted SNTP after recovery and capture drop counters zero.
8. Preserve any miss or ambiguous state as a charged 240-second job. Do not
   retry without source-impact review and an explicit corrective packet inside
   the standing ceilings.

## Run B: storage and autonomy

1. Keep the same fixture only after Run A is reconciled. Reconfirm both boards
   inactive and schedule-disabled, then reacquire or retain the same durable
   reservation with its exact packet identity.
2. GET the baseline configuration and ETag through authenticated HTTPS. Build a
   schedule for one exact UTC occurrence at least 240 seconds ahead, aligned to
   a 120-second phase in a 86,400-second period, with expiry at least 240 seconds
   after that occurrence. Keep network credentials and station identity exact.
3. If required by the frozen rotation plan, perform one disabled preparatory API
   save and verify one sequence/offset advance. Perform the enabled-schedule API
   save and require one bank crossing in `STORAGE`. No other save is permitted.
4. Request the one controlled software reboot through the authenticated API.
   Require a new boot with the exact saved configuration. Before accepted SNTP,
   record enabled scheduling, unsynchronized clock, unchanged watermark and no
   autonomous owner/job. Then require synchronized/normal time within the bounded
   readiness interval.
5. Do not send `TIME SET`, `LOAD` or `ARM`. Around the frozen occurrence, run
   independent USB, authenticated WTP and HTTPS observers. Require the local
   owner `eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee`, the expected occurrence-derived job
   ID, durable watermark before preparation, Armed/Running transitions, physical
   output and one Complete terminal.
6. During Running, submit the exact original configuration through Console and
   require `{"ok":false,"error":"busy"}`. Read `STORAGE` before and after;
   the sequence and offset must be unchanged. Continue all observers and prove
   the attempt did not disturb RF.
7. After completion and local owner release, save the original disabled
   configuration once through authenticated HTTPS. Require the expected final
   sequence/offset, original station/network/schedule/expiry fields,
   `enabled:false`, healthy storage, advanced watermark and inactive output.
8. Inventory B again and prove it never owned or activated output. Only after
   fresh A/B inactive, unowned and schedule-disabled evidence may the shared RF
   reservation be released.

## Fixed ceilings and stop rules

- RF: two planned jobs, 350.592 seconds total; each failed or uncertain
  submission is charged at full duration. Overall standing ceiling remains 16
  jobs / 14,400 seconds, but this packet may not spend the unused ceiling without
  a documented corrective amendment.
- Device mutations: one A flash, one BOOTSEL transition, one controlled software
  reboot, zero intentional Wi-Fi OFF/ON cycles, zero allocation probes, one DHCP
  binding change, one 15-second AP loss, and exactly two or three CONFIG saves as
  derived before the first save.
- Stop before mutation on identity/hash mismatch, non-empty/owned/active state,
  enabled schedule, unhealthy storage, unavailable cleanup timer, fixture drift,
  missing reservation, stale journal read, insufficient restoration writes or
  missed schedule timing.
- Stop after mutation on unknown output, changed boot outside the one reboot,
  storage fault, watchdog recovery, observer loss that removes authoritative RF
  continuity, a second journal rotation, unplanned write, schedule replay, or
  inability to restore disabled scheduling. Preserve the raw evidence and keep
  the reservation held until fresh reconciliation.

## Review, publication and closure

1. Audit raw files offline with hash binding. Reject mutations for wrong identity,
   lost captures, inferred address/name recovery, link loss outside Running,
   duplicate execution, missing unsynchronized gate, non-API persistence,
   inferred rather than observed rotation, worker write acceptance, wrong local
   owner, premature reservation release or incomplete restoration.
2. Perform an adversarial source/result review. Fix every actionable issue and
   rerun affected deterministic checks. If a fix changes target behavior, perform
   source-impact review before any bounded physical repeat; do not relabel the
   original attempt.
3. Publish sanitized Package 8 result, raw-evidence audit result, adversarial
   result, review narrative, matrix/ledger/development status and exact candidate
   identities. Retain failed attempts by digest.
4. Close R5 only if all eight assertion rows are accepted/applicable. Then Phase
   11.5 is OPEN at 5/6 families, with Package 9/R6 next and no accepted full
   configuration yet.
5. Run the full registered host suite, ensure the tree is clean except intended
   artifacts, commit, push `devel`, verify `origin/devel` equals local HEAD, and
   report budgets, physical evidence, restoration, review findings, commit and
   remote parity.
