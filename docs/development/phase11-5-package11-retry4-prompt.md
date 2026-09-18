# Phase 11.5 Package 11 Retry 4 — event-aware R6 closure continuation

## Objective

Run one bounded continuation of the Package 11 R6 physical campaign after the
Retry 3 host reducer rejected a valid, short-lived USB `complete` state that
occurred between five-second STATUS samples. Preserve every earlier failure and
charge. Use the repaired event-plus-STATUS reducer without changing firmware,
WTP, RF timing, the one-hour terminal replay retention, the workload, the
165,000-byte memory gate, the 1,024-byte resource-return limit or any Phase 11.5
acceptance criterion.

Close R6 and Phase 11.5 only if the complete fresh campaign passes the existing
independent audit. A stopped, interrupted or failed Retry 4 earns no R6 credit
and does not authorize another attempt.

## Repository and exact inputs

- Repository: `/Users/lbussy/GitHub/WsprryPico`, branch `devel`.
- Baseline before this continuation: `a19db5319520a7c609cd9947cb44942bace5a0f3`.
- Read `README.md`, `CONTRACT.md`, `docs/architecture.md` and
  `docs/development/README.md` before execution.
- Original prompt: `docs/development/phase11-5-package11-prompt.md`.
- Retry 1, 2 and 3 prompts and reviews under `docs/development/` remain part of
  the record.
- Retry 3 stopped result SHA-256:
  `9b02a77258a36739a3076f68ddf9b525cb6edf32c54bf5408f02e8340f956598`.
- Retry 3 adversarial result SHA-256:
  `5743412d23c14e59c0efa018b4071b94f4760bd7669878a159f7bd4f15cc3e1c`.
- Host-only USB reducer retest SHA-256:
  `9016f26d0f6d87c8743202cd2ffd4cba2be9473f6320c0e6f1064afe520f823b`.
- USB reducer adversarial result SHA-256:
  `e88f8ab10c8ad16e6fe80ed77990e299be7b7be67cdf56534ace86af2c252868`.
- The repaired `scripts/phase11_5_package9.py` SHA-256 is
  `5d9b268b65f9dcc01c962217d620603c0a55363639dc03a14fbb2d55c3ca7a3c`.
- The Package 9 and Package 10 auditors retain SHA-256
  `66e37d9ab331495b65d889831d437f9f94d5cd98002f968f771295571c26dbb1`
  and `59c6785bb97ab7a7f34f8efa05ab7525619174b64471a87db852732ca92e8960`.
- Fresh wspr5 credential retest:
  `docs/development/phase11-5-package11-retry4-credential-retest-result.json`,
  SHA-256
  `0bf89b6046b6fd7f2eed6f410044ae5556b1b1a2997c8493bdc3518151d13f3c`.
  It covers the exact Retry 4 fixture source and used six synthetic files, root
  ownership and no Pico, USB, network fixture, service, reservation or RF action.

The Retry 3 run passed credential and fixture readiness, terminal retirement,
the unchanged memory gate, reservation, eight warmups, the 360-second baseline,
one 600-second mixed interval and one 114.6-second production job. It stopped
before any post-N resource window because the host runner reduced only periodic
STATUS samples. The independent USB session had retained the full lifecycle,
including `complete`, and a matching complete/output-inactive terminal record.
The stopped record classifies this as a host harness defect, not a Pico, WTP,
RF, timing or resource failure. The repaired reducer accepts the exact private
evidence and rejects 22/22 mutations; the stopped-attempt auditor rejects 35/35.

## Candidate and two-host fixture

- Pico A: serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, source
  `91933c00970939e366d1bfcf3c1956b59be8f6c5`, UF2 SHA-256
  `5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446`,
  boot `ff719d304f1ba4ac23fddd93561b26f0`.
- Pico B: serial `CDDBF8767C506C07`, device
  `29f20b7342051ef947aa56cb9d4fab42`, source `8921a7008183`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- Pico A configuration: Pico 2 W/RP2350 Arm, 138 MHz, divider 1, GP2 PIO/DMA,
  RAM renderer, configured TLS listener and the existing attenuated conducted
  RF path.
- WsprryPi source: `21ae75ab9e38bd6237b1ae73f3e7ab8527324067`.
- `wspr5` is the USB/RF observer and independent client. Preserve `eth0` and
  `wlan1`; use `wlan2`, MAC `e8:4e:06:ae:d7:09`, only in the private namespace.
- `wspr4` is the separate AP host. Preserve `wlan0`; use `wlan1`, MAC
  `e8:4e:06:ac:f3:87`, temporarily as the channel-11 AP.
- `wspr5` publishes `time.local` at `10.77.15.2` from PPS-backed chrony. Pico
  owns all RF timing locally after each complete job is installed.
- Keep SSID, PSK, credentials, authenticated traffic, captures and raw payloads
  in mode-0700 private roots outside Git. Publish only aggregates and hashes.

Treat Bohica and Bohica-IoT router flaps as external events unrelated to the
test. If an external interruption prevents fresh evidence, preserve actual
accounting, restore the fixture and stop without assigning a product cause.

## Authorization and finite accounting

This prompt authorizes one Retry 4 run named
`PACKAGE11-TWO-HOST-R6-RETRY4` with:

- at most 16 new RF jobs and 356,800,000,000 planned RF ns;
- an absolute Retry 4 RF duration cap of 480,000,000,000 ns;
- zero flashes, BOOTSEL transitions, CONFIG writes, controlled Pico reboots,
  intentional Pico Wi-Fi cycles and allocation probes;
- one read-only retained-terminal gate bounded to 600 seconds; and
- temporary wspr4/wspr5 fixture operations with cleanup armed before mutation.

Charge a job's full planned duration only after ARM is accepted. Prior Package
11 accounting is 25 jobs and 138,600,000,000 planned RF ns: Attempt 1 charged
8/8 seconds, Retry 1 charged 8/8 seconds, Retry 2 charged 0/0 and Retry 3
charged 9/122.6 seconds. None produced an accepted R6 resource result. A fully
completed Retry 4 would make the cumulative accounting 41 jobs and
495,400,000,000 planned RF ns. Unused allowance cannot fund exploration or an
automatic retry.

## Preflight and frozen packet

1. Review all Package 11 results, the reducer repair, current source and git
   state. Run Python syntax checks, focused Package 9/11 tests, the documented
   host suite and `git diff --check`.
2. Bind the Retry 3 result, its adversarial review, both reducer artifacts, the
   fresh credential retest, all earlier attempt/repair artifacts, the exact
   Package 9/10 auditors, binary, observer, six credential contents, retained
   Wi-Fi, source inputs and host attestations in a fresh mode-0700 packet.
3. Reject any changed dependency, authorization, source hash, prior charge,
   restoration statement, credential, workload, gate or cumulative total.
4. Verify the shared reservation is released; both Picos match the frozen
   identity and boot and are empty, unowned and output-inactive; and both hosts
   match their fixed boots, management links, radios, services and timers.
5. Arm cleanup before radio mutation. Securely open every credential, rejecting
   symlink parents and final symlinks, and require one nonempty regular link,
   exact packet hash, effective UID/GID ownership and mode `0600`.
6. Establish the separate AP/client fixture and verify exact BSSID/channel,
   native `time.local`, PPS-backed NTP, authenticated WTP/HTTPS, capture startup
   and device authority before acquiring the RF reservation.

## Retained-terminal and memory gates

After pausing the installed WsprryPi service, use new packet-bound USB sessions
at 15-second intervals for at most 600 seconds. Require frozen identity and
boot, no owner, output inactive, schedules disabled, no more than eight unique
records, and every record complete and output-inactive. Reject any record whose
remaining one-hour retention exceeds the bounded wait. Continue only after a
fresh inventory reports zero records.

Then run the unchanged 360-second memory gate. Available heap must reach at
least 165,000 bytes before network readiness, reservation or RF. Do not merge
the two gates, lower either bound or infer readiness from prior evidence.

## Exact fresh workload

Run once, from the beginning:

1. three one-second 383-event production-class normalizers;
2. five one-second 512-event maximum-class normalizers;
3. one 360-second matched baseline;
4. three 600-second normal intervals, each containing one 114.6-second native
   WsprryPi FSKCW job, frozen browser cadence, independent network and USB
   observers and a 306-second application-quiet window;
5. five one-second maximum-class refresh jobs; and
6. one 360-second final equivalent quiet interval.

Before each cycle, poll a healthy synchronized-but-stale clock every two
seconds; reserve 30-second backoff for transport failures. Keep clock freshness
at ten seconds. The USB reducer must combine lifecycle events for transient
states with periodic STATUS authority, including the matching retained
complete/output-inactive terminal record. Require exactly 16 completed jobs,
three production and five maximum replay classes at every compared post-warmup
state, identical hashes within each class and the exact final three/five set.

## Acceptance gates

- Baseline, each of three post-N windows and final Q remain within 1,024
  allocated heap bytes of the matched baseline.
- Post-N span is at most 1,024 bytes and is not strictly increasing.
- Heap capacity minus allocator peak is at least 32,768 bytes.
- Both stack guards remain valid with at least 4,096 bytes reserve.
- Allocator and TLS allocation failures, DMA errors, unpaired refills, invalid
  reserves, engine diagnostics and recorded faults remain zero.
- Both timing metrics remain at most 2,849,391 ns with predecessor and tail
  evidence.
- Network and USB observers retain the required cadence and lifecycle evidence;
  packet captures have zero kernel drops.
- Both Picos finish empty, unowned and output-inactive; the reservation is
  released; both hosts, management links, recovery timers and installed
  WsprryPi service are restored.

A fixture interruption is neither a pass nor a product failure. A complete run
that misses a product gate keeps R6 open. Never infer inactive output from a
disconnect, lost acknowledgement, process exit or USB closure.

## Audit, repair loop and publication

Preserve raw evidence privately. Run the independent Package 11 auditor and
publish only credential-free aggregates and hashes. Report all four attempts'
charges separately and cumulatively. Bind the Retry 3 stopped result and both
host-only repairs into the final result.

Adversarially mutate candidate and host identity, fixture separation, exact
authorization, all dependency hashes, every prior charge, cumulative totals,
credential applicability, event/STATUS reduction, workload, lifecycle counts,
quiet intervals, replay classes, resource and timing gates, captures,
reservation and restoration. The intact result must validate and every
mutation must fail.

Repair each actionable in-scope finding, rerun affected checks and perform a
fresh adversarial assessment. Continue until no finding remains or preserve an
exact external blocker. Update the Package 11 result/review, completion matrix,
ledger, implementation plan and development index only from audited evidence.
Commit the final repository state to `devel`, push `origin/devel`, and verify
local HEAD, upstream and remote branch parity.
