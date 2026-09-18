# Phase 11.5 Package 11 — two-host fixture and corrected R6 closure

## Objective

Address the two demonstrated shortcomings that prevented Package 9 from closing
R6:

1. compare resource windows with equivalent retained WTP replay-history classes,
   as designed in Package 10; and
2. remove Package 10's same-host AP/client coupling by qualifying a physically
   separate access-point host before any RF reservation or transmission.

Preserve Package 9 as a failed resource-return measurement and Package 10 as a
fixture-blocked attempt. Keep the resource-return threshold at 1,024 bytes and
make no firmware, protocol, replay-retention or product-capacity change. Close
R6 and Phase 11.5 only if the complete corrected campaign and independent raw
and adversarial audits pass.

## Exact candidate and fixture

- Repository: `/Users/lbussy/GitHub/WsprryPico`, branch `devel`.
- Pico A: serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, source
  `91933c00970939e366d1bfcf3c1956b59be8f6c5`, UF2 SHA-256
  `5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446`,
  boot `ff719d304f1ba4ac23fddd93561b26f0`.
- Pico B comparator: serial `CDDBF8767C506C07`, device
  `29f20b7342051ef947aa56cb9d4fab42`, source `8921a7008183`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- Pico A configuration: Pico 2 W/RP2350 Arm, 138 MHz, divider 1, GP2 PIO/DMA,
  RAM rendering and configured TLS listener.
- WsprryPi production source:
  `21ae75ab9e38bd6237b1ae73f3e7ab8527324067`.
- `wspr5` remains the USB/RF observation and independent-client host. Preserve
  Ethernet and `wlan1` management. Use `wlan2`, MAC `e8:4e:06:ae:d7:09`, only
  inside the temporary client namespace.
- `wspr4` becomes the physically separate AP host. Preserve `wlan0`
  management. Temporarily use `wlan1`, MAC `e8:4e:06:ac:f3:87`, as the isolated
  channel-11 AP and restore its original NetworkManager connection afterward.
- `wspr5` publishes `time.local` at the isolated client address and relays NTP
  only to its local PPS-backed chrony instance, so the Pico timing path has no
  dependency on the site router after setup.
- Retain the existing SSID, PSK, `time.local` name, `10.77.15.0/24` subnet,
  Pico address `10.77.15.10`, client address `10.77.15.2`, credentials and
  attenuated conducted RF path. Keep all secrets and authenticated payloads in
  mode-0700 private evidence roots outside Git.

## Authorization and finite accounting

The user's instruction to execute this prompt authorizes the two temporary host
network fixtures, read-only Pico inventories, authenticated WTP/HTTPS readiness,
one bounded corrected RF campaign, restoration, evidence review, scoped tooling
repairs, affected retests, commit and push.

The new Package 11 RF ceiling is:

- at most 16 RF jobs and 356,800,000,000 planned RF ns;
- at most 480,000,000,000 authorized RF ns;
- zero planned or permitted flashes, BOOTSEL transitions, CONFIG writes,
  controlled Pico reboots, intentional Pico Wi-Fi cycles and allocation probes.

Charge a job's full planned duration once its ARM is accepted. Do not use the
123.2-second remainder for retries, exploration or another campaign. Package
10's four charged RF seconds remain historical Package 10 accounting and do not
consume or enlarge this fresh Package 11 ceiling.

Temporary `wspr4`/`wspr5` radio and service operations are host-fixture actions,
not Pico Wi-Fi cycles. Arm independent cleanup on both hosts before the first
host mutation. Preserve management connectivity and permanent configuration.
Use one shared RF reservation across both Picos and acquire it only after the
zero-RF admission packet has passed and the complete campaign has independently
re-established readiness and device authority.

## Stage A — separate zero-RF fixture admission

Freeze and execute a credential-private admission packet before staging the RF
packet. It must use the same two hosts, radios, SSID, Pico, name, subnet and TLS
identities intended for the campaign. It may not acquire the RF reservation,
submit CLAIM/LOAD/ARM/ABORT/RELEASE, enable a schedule, or change Pico state.

Require:

- exact host boots and radio MACs;
- `wspr4` AP activation on channel 11 while `wlan0` management remains usable;
- `wspr5` `wlan2` association to the exact remote BSSID, in separate mount and
  network namespaces, with no default route;
- the Pico at `10.77.15.10`, native `time.local` resolution to the independent
  client at `10.77.15.2`, a valid stratum-1/PPS NTP response relayed only from
  wspr5's local chrony, synchronized Pico clock and active mDNS; the AP-to-client
  timing path must remain independent of the site router after fixture setup;
- six authenticated WTP STATUS and HTTPS status pairs over at least 180 seconds,
  with the same device/boot, no owner, no output, no terminal-set change and no
  recovery/safety fault;
- unchanged launch epoch and tail-IRQ counters between fresh before/after
  inventories of Pico A, plus a fresh inactive inventory of Pico B;
- packet captures from the remote AP and independent client, with zero kernel
  drops; and
- complete restoration of both host fixtures, both Picos inactive/unowned, the
  installed `wspr5` service active, shared reservation unchanged/released and
  both management paths healthy.

Audit the admission evidence independently. Any missing, stale, contradictory
or failed observation blocks Stage B and consumes zero RF.

## Stage B — corrected matched replay-state campaign

Only after Stage A passes and restores cleanly, freeze a fresh campaign packet.
Reuse Package 10's corrected workload without changing its meaning:

1. three one-second 383-event production-class normalizers using WsprryPi's
   actual 135,505 Hz mark and 135,500 Hz space sequence;
2. five one-second 512-event maximum-class normalizers;
3. a 360-second matched baseline;
4. three 600-second normal-load intervals, each with one 114.6-second native
   WsprryPi FSKCW job, the original browser cadence, independent Console, USB
   and host observations, and a 306-second application-quiet window;
5. five one-second maximum-class refresh jobs; and
6. a 360-second final equivalent quiet interval.

Require exactly 16 complete jobs, three production and five maximum replay
classes at every compared post-warm-up state, identical adjustment hashes
within each class, and the exact final three-production/five-maximum terminal
set. Preserve Package 9's browser actions, GET counts, production schedule,
observer cadence, deadlines, local Pico timing ownership and independent USB
lifecycle requirements.

## Acceptance gates

Apply every still-relevant Package 9 and Package 10 identity, resource, timing,
fault, capture, ownership and restoration gate. In particular:

- baseline, all three post-N windows and final Q are each within 1,024 allocated
  heap bytes of baseline;
- the three post-N values span at most 1,024 bytes and are not strictly
  increasing;
- heap capacity minus allocator peak is at least 32,768 bytes;
- both core stack guards remain valid with at least 4,096 bytes reserve;
- allocator failures, TLS allocation failures, DMA errors, unpaired refills,
  invalid reserves, engine diagnostics and recorded faults remain zero;
- `rf_max_service_gap_ns` and `max_refill_irq_to_ready_ns` remain at most
  2,849,391 ns, with the recorded full/short predecessor and tail evidence;
- both Picos finish Empty, unowned and output-inactive;
- the shared RF reservation finishes Released; and
- both host fixtures, management connections, timers and the installed
  WsprryPi service are restored.

A fixture failure is not a product pass or failure. A completed campaign that
misses any product gate keeps R6 open. Never infer inactive RF from a lost
connection or process exit.

## Implementation, audit and publication

Implement only the host-side Package 11 staging, two-host fixture, admission,
campaign wrapper, raw auditors, adversarial assessors and focused tests needed
for these packets. Reuse the reviewed Package 10 campaign logic where behavior
is identical. Do not modify firmware or normative protocol behavior.

Before physical execution, run syntax checks, focused tests and the documented
host suite. Stage fresh mode-0700 roots with exact input hashes and independent
cleanup deadlines. Preserve all raw evidence privately and publish only
credential-free aggregate results and hashes.

For each successful raw audit, adversarially alter every closure-critical class:
host/boot/radio identity, remote-client isolation, mDNS/NTP/TLS readiness,
zero-RF admission, packet identity and budget, replay-class composition,
adjustment hashes, lifecycle counts, normal workload, quiet intervals, resource
threshold, timing/fault gates, reservation state and two-host restoration. Every
mutation must be rejected while intact evidence passes.

Repair actionable findings, rerun affected checks and repeat the adversarial
assessment until no in-scope finding remains or a specific external blocker is
preserved. Then update the Package 11 result/review, completion matrix, ledger,
plan and development index from audited evidence. Commit and push `devel`, and
independently verify local HEAD, upstream and remote branch parity.
