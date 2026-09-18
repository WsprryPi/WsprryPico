# Phase 11.5 Package 11 Retry 1 — clock-poll repair and R6 closure

## Objective

Complete the Package 11 corrected R6 campaign after preserving the first
Package 11 attempt as a stopped harness failure. The first attempt completed
the eight one-second warm-up jobs and the 360-second matched baseline, then
stopped before cycle 1 because the harness reused a 30-second transport retry
delay while polling healthy but stale clock samples. That sampling interval
aliased the Pico's roughly 60-second local SNTP update cadence and missed every
unchanged 10-second freshness window.

Use the repaired harness, which retains the 30-second delay for transport
failures and polls a healthy synchronized-but-stale Pico clock every two
seconds. Do not change the 10-second clock-freshness gate, product behavior,
firmware, WTP contract, replay retention, workload, 1,024-byte resource-return
threshold or any Phase 11.5 acceptance criterion.

## Bound evidence and prior accounting

- Repository: `/Users/lbussy/GitHub/WsprryPico`, branch `devel`.
- Original Package 11 prompt:
  `docs/development/phase11-5-package11-prompt.md`.
- First-attempt packet SHA-256:
  `ed3255ba7811edef230a6e263e8de94cf13dbb0afbae6c51ee400a70f3622052`.
- First-attempt published result:
  `docs/development/phase11-5-package11-attempt1-result.json`, SHA-256
  `0bef1850d736535661e2c0ae1bc7519dbff2cfbf06ebacf1c64108b4831b6faf`.
- First-attempt charge: 8 RF jobs and 8,000,000,000 planned RF ns. It
  produced no accepted R6 resource result. Both Picos, the reservation and both
  host fixtures were authoritatively restored.
- Passed zero-RF admission result SHA-256:
  `fe4d7a9b84ec97f256b09f187005399685d0aefd556b129648608ea2a4cb1214`.
- Passed admission adversarial result SHA-256:
  `2b9e18c73cc7f53572f086b44c2d1fef9835009b129cb4b30c8b0c5db6317935`.
- Passed zero-RF clock-poll retest:
  `docs/development/phase11-5-package11-clock-poll-retest-result.json`,
  SHA-256
  `92838e20c1de3a998bda67084f75b8deb728049633598ab9e2b5b18b2606fa68`.
  It began with a 29,328,286,000 ns-old Pico clock sample, polled 17 times over
  36,702,052,738 ns and accepted a 2,027,972,000 ns-old sample. It used only
  `HELLO`, `CAPS`, `STATUS` and `GET_CLOCK`, acquired no RF reservation and
  charged zero RF.

Treat the Bohica and Bohica-IoT management-router flaps observed during tooling
work as external events unrelated to Pico operation or RF behavior. Do not
convert them into product failures or causes. If a fresh fixture or evidence
stream is interrupted, discard that campaign attempt as an external fixture
interruption and preserve its actual accounting.

## Exact candidate and fixture

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
  Ethernet and `wlan1` management. Use `wlan2`, MAC
  `e8:4e:06:ae:d7:09`, only in the temporary client namespace.
- `wspr4` remains the separate AP host. Preserve `wlan0` management. Use
  `wlan1`, MAC `e8:4e:06:ac:f3:87`, temporarily as the isolated channel-11 AP
  and restore its original NetworkManager connection afterward.
- `wspr5` publishes `time.local` at `10.77.15.2` and relays NTP only to its
  local PPS-backed chrony instance. The Pico owns RF timing locally after job
  setup; neither symbol timing nor the active campaign depends on WsprryPi or
  the site router.
- Retain the admitted SSID, PSK, `time.local` name, `10.77.15.0/24` subnet,
  Pico address `10.77.15.10`, credentials and attenuated conducted RF path.
  Keep secrets and authenticated payloads in mode-0700 private evidence roots
  outside Git.

## Authorization and finite accounting

Executing this prompt authorizes one fresh Retry 1 campaign with:

- at most 16 additional RF jobs and 356,800,000,000 planned RF ns;
- at most 480,000,000,000 authorized RF ns for Retry 1;
- zero flashes, BOOTSEL transitions, CONFIG writes, controlled Pico reboots,
  intentional Pico Wi-Fi cycles and allocation probes; and
- temporary bounded `wspr4` and `wspr5` host-fixture operations with independent
  cleanup armed before mutation.

Charge a job's full planned duration once its ARM is accepted. The maximum
cumulative Package 11 accounting after a complete Retry 1 is 24 RF jobs and
364,800,000,000 planned RF ns: the preserved 8-job first attempt plus this
16-job retry. The historical four-second Package 10 attempt remains Package 10
accounting.

Do not use Retry 1's unused 123.2-second allowance for another campaign,
exploration or a second retry. A stopped or failed Retry 1 requires a new
evidence-bound authorization.

## Preflight and frozen packet

1. Review `README.md`, `CONTRACT.md`, `docs/architecture.md`, the original
   Package 11 prompt, the first-attempt result and the zero-RF clock-poll result.
2. Run syntax checks, focused Package 9 and Package 11 tests, the documented
   host suite and whitespace checks.
3. Confirm the shared reservation is `RELEASED`; both Picos match their frozen
   boots and are Empty, unowned and output-inactive; the installed `wspr5`
   service is active; and both hosts match their frozen boots, radios,
   management profiles and recovery timers.
4. Create fresh mode-0700 roots on both hosts. Freeze a new campaign packet
   using authorization `PACKAGE11-TWO-HOST-R6-RETRY1`. Bind it by SHA-256 to
   the admission result, admission adversarial result, first-attempt result,
   zero-RF clock-poll result, exact source inputs, host attestations, binary,
   observer, credentials and retained Wi-Fi input.
5. The packet must state both the fresh Retry 1 ceiling and cumulative Package
   11 accounting. Validation must reject any missing or altered dependency,
   attempt charge, restoration claim, clock-poll result or authorization.
6. Establish and verify the independent AP/client fixture. Re-establish native
   `time.local`, PPS-backed NTP, Pico synchronization, authenticated WTP/HTTPS,
   exact BSSID/channel association, device authority and fresh clock readiness
   before acquiring the shared RF reservation.

## Corrected matched replay-state campaign

Run the unchanged Package 10/11 workload once:

1. three one-second 383-event production-class normalizers using WsprryPi's
   actual 135,505 Hz mark and 135,500 Hz space sequence;
2. five one-second 512-event maximum-class normalizers;
3. a 360-second matched baseline;
4. three 600-second normal-load intervals, each with one 114.6-second native
   WsprryPi FSKCW job, the frozen browser cadence, independent Console, USB and
   host observations, and a 306-second application-quiet window;
5. five one-second maximum-class refresh jobs; and
6. a 360-second final equivalent quiet interval.

Before each cycle, poll a healthy synchronized-but-stale Pico clock every two
seconds while retaining the 30-second backoff only for transport failures.
Keep the freshness limit at 10,000,000,000 ns. Require exactly 16 complete jobs,
three production and five maximum replay classes at every compared post-warm-up
state, identical adjustment hashes within each class and the exact final
three-production/five-maximum terminal set.

## Acceptance and restoration

Apply every still-relevant Package 9, Package 10 and original Package 11 gate:

- baseline, all three post-N windows and final Q are each within 1,024 allocated
  heap bytes of baseline;
- the three post-N values span at most 1,024 bytes and are not strictly
  increasing;
- heap capacity minus allocator peak is at least 32,768 bytes;
- both core stack guards remain valid with at least 4,096 bytes reserve;
- allocator failures, TLS allocation failures, DMA errors, unpaired refills,
  invalid reserves, engine diagnostics and recorded faults remain zero;
- `rf_max_service_gap_ns` and `max_refill_irq_to_ready_ns` remain at most
  2,849,391 ns with required predecessor and tail evidence;
- both Picos finish Empty, unowned and output-inactive;
- the shared reservation finishes Released; and
- both host fixtures, management connections, recovery timers and the installed
  WsprryPi service are restored, with zero capture drops.

A fixture interruption is neither a product pass nor a product failure. A
completed campaign that misses any product gate keeps R6 open. Never infer
inactive output from a lost connection or process exit.

## Independent audit, adversarial review and publication

Preserve raw evidence privately. Run the independent raw auditor and publish
only credential-free aggregate results and hashes. The result must separately
report first-attempt charge, Retry 1 charge and cumulative Package 11 charge.
It must preserve Package 9, Package 10 and Package 11 attempt-1 failures and
bind the passed zero-RF clock-poll repair.

Adversarially alter every closure-critical class, including candidate and host
identity, fixture separation, admission and clock-poll dependencies, first-
attempt accounting, Retry 1 authorization, cumulative accounting, replay-class
composition, adjustment hashes, lifecycle counts, workload, quiet intervals,
resource threshold, timing/fault gates, reservation state, captures and
two-host restoration. Every mutation must be rejected while intact evidence
passes.

Repair actionable findings, rerun affected checks and repeat adversarial review
until no in-scope finding remains or an exact external blocker is preserved.
Close R6 and Phase 11.5 only from the complete audited campaign. Then update the
Package 11 result/review, completion matrix, acceptance ledger, implementation
plan and development index. Commit and push `devel`, and independently verify
local HEAD, upstream and remote branch parity.
