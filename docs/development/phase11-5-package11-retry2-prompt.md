# Phase 11.5 Package 11 Retry 2 — credential-safe R6 closure

## Objective

Complete the Package 11 corrected R6 campaign after preserving two stopped
host-harness attempts and repairing both demonstrated harness defects:

1. healthy synchronized-but-stale clock samples are polled every two seconds,
   while the 30-second retry remains limited to transport failures; and
2. all six TLS credential files are content-bound in the frozen packet and,
   after cleanup is armed but before any radio mutation, are securely opened,
   required to be nonempty single-link regular files, checked against their
   packet hashes, and changed to mode `0600` with the effective campaign user
   as owner.

Do not change the 10-second clock-freshness gate, firmware, WTP contract,
replay retention, workload, 1,024-byte resource-return threshold or any Phase
11.5 acceptance criterion. The credential repair is host-fixture tooling only.

## Bound evidence and prior accounting

- Repository: `/Users/lbussy/GitHub/WsprryPico`, branch `devel`.
- Original Package 11 prompt:
  `docs/development/phase11-5-package11-prompt.md`.
- Retry 1 prompt:
  `docs/development/phase11-5-package11-retry1-prompt.md`.
- Attempt 1 packet SHA-256:
  `ed3255ba7811edef230a6e263e8de94cf13dbb0afbae6c51ee400a70f3622052`.
- Attempt 1 result SHA-256:
  `0bef1850d736535661e2c0ae1bc7519dbff2cfbf06ebacf1c64108b4831b6faf`.
  It charged eight one-second warmups, stopped at the aliased clock poll before
  cycle 1 and earned no R6 credit.
- Retry 1 packet SHA-256:
  `cc3bf2c66075112bccc93557173f256541c6fcecea9637972ada6e55312cec0a`.
- Retry 1 stopped result:
  `docs/development/phase11-5-package11-retry1-result.json`, SHA-256
  `89a7a1f26b2aa084187d08b24749bde22bec95476a20cddfe397a62f25d9d1a7`.
  It charged eight one-second warmups, completed the 360-second matched
  baseline at 56,216 allocated bytes, passed the two timing limits at that
  baseline, passed corrected cycle-1 clock readiness, then stopped before any
  production ARM because root-run WsprryPi rejected mode-0600 private keys
  owned by `pi`. It earned no R6 credit.
- Retry 1 adversarial result:
  `docs/development/phase11-5-package11-retry1-adversarial.json`, SHA-256
  `f9c83b32542f0843ca262fcd041c5a8e89b96fcff526917008d50757d61e28b8`.
  All 31 stopped-attempt mutations were rejected.
- Passed zero-RF clock-poll retest:
  `docs/development/phase11-5-package11-clock-poll-retest-result.json`,
  SHA-256
  `92838e20c1de3a998bda67084f75b8deb728049633598ab9e2b5b18b2606fa68`.
- Passed Linux host-only credential repair retest:
  `docs/development/phase11-5-package11-credential-retest-result.json`,
  SHA-256
  `eda622ce6aac1b0d0cf2628dac179233138910628179f16a64f7c41ca2069238`.
  It changed six synthetic credential files from `pi` UID 1000 to campaign UID
  0, retained mode `0600` and preserved every content hash. It accessed no
  Pico, USB endpoint, network fixture, service or RF reservation and charged
  zero RF.
- Passed zero-RF admission result SHA-256:
  `fe4d7a9b84ec97f256b09f187005399685d0aefd556b129648608ea2a4cb1214`.
- Passed admission adversarial result SHA-256:
  `2b9e18c73cc7f53572f086b44c2d1fef9835009b129cb4b30c8b0c5db6317935`.

The cumulative Package 11 charge before Retry 2 is 16 RF jobs and
16,000,000,000 planned RF ns: eight jobs from Attempt 1 plus eight jobs from
Retry 1. Neither attempt produced an accepted R6 resource result. Both attempts
ended with both Picos authoritatively inactive on their original boots, the RF
reservation released and both host fixtures restored.

Treat the Bohica and Bohica-IoT management-router flaps as external events
unrelated to Pico operation or RF behavior. Do not turn them into product
failures or causes. If they interrupt fresh evidence, preserve the actual
accounting and classify that attempt as an external fixture interruption.

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
- `wspr5` is the USB/RF observation and independent-client host. Preserve
  Ethernet and `wlan1` management. Use `wlan2`, MAC
  `e8:4e:06:ae:d7:09`, only in the temporary client namespace.
- `wspr4` is the physically separate AP host. Preserve `wlan0` management. Use
  `wlan1`, MAC `e8:4e:06:ac:f3:87`, temporarily as the isolated channel-11 AP
  and restore its original NetworkManager connection afterward.
- `wspr5` publishes `time.local` at `10.77.15.2` and relays NTP only to its
  local PPS-backed chrony instance. The Pico owns RF timing locally after job
  setup; neither symbol timing nor an active RF job depends on WsprryPi or the
  site router.
- Retain the admitted SSID, PSK, `time.local` name, `10.77.15.0/24` subnet,
  Pico address `10.77.15.10`, TLS identities and attenuated conducted RF path.
  Keep secrets, private keys, captures and authenticated payloads in mode-0700
  private evidence roots outside Git.

## Authorization and finite accounting

Executing this prompt authorizes one fresh Retry 2 campaign with:

- at most 16 additional RF jobs and 356,800,000,000 planned RF ns;
- at most 480,000,000,000 authorized RF ns for Retry 2;
- zero flashes, BOOTSEL transitions, CONFIG writes, controlled Pico reboots,
  intentional Pico Wi-Fi cycles and allocation probes; and
- temporary bounded `wspr4` and `wspr5` host-fixture operations with independent
  cleanup armed before mutation.

Charge a job's full planned duration once its ARM is accepted. The maximum
cumulative Package 11 accounting after a complete Retry 2 is 32 RF jobs and
372,800,000,000 planned RF ns: the preserved 16 jobs and 16 seconds from the
two stopped attempts plus this 16-job, 356.8-second campaign. Package 10's
historical four seconds remain Package 10 accounting.

Do not use Retry 2's unused 123.2-second allowance for another campaign,
exploration or a further retry. A stopped or failed Retry 2 requires new
evidence-bound authorization.

## Preflight and frozen packet

1. Review `README.md`, `CONTRACT.md`, `docs/architecture.md`, both earlier
   Package 11 prompts, both stopped-attempt results, the clock-poll retest and
   the credential retest.
2. Run syntax checks, focused Package 9 and Package 11 tests, the documented
   host suite and whitespace checks.
3. Confirm the shared reservation is `RELEASED`; both Picos match their frozen
   boots and are Empty, unowned and output-inactive; the installed `wspr5`
   service is active; and both hosts match their frozen boots, radios,
   management profiles and recovery timers.
4. Create fresh mode-0700 roots on both hosts. Freeze a new campaign packet
   using authorization `PACKAGE11-TWO-HOST-R6-RETRY2`. Bind it by SHA-256 to
   the admission result and review, Attempt 1 result, clock-poll result, Retry 1
   result and review, credential retest, all six credential contents, exact
   source inputs, host attestations, WsprryPi binary, observer and retained
   Wi-Fi input.
5. Validate the six credential paths as the exact controller/browser CA,
   certificate and key set. After cleanup is armed and before stopping recovery
   timers or changing either radio, require every parent to be a real directory,
   securely open each file with symlink refusal, require a nonempty regular file
   with link count one, verify its
   packet-bound content hash, set its owner to the effective campaign UID/GID
   and mode to `0600`, then verify the open descriptor. Record paths, hashes,
   UID/GID and mode only; never publish credential contents.
6. The packet must state the fresh Retry 2 ceiling, each earlier attempt's
   charge and the cumulative Package 11 ceiling. Validation must reject every
   missing or altered dependency, prior charge, restoration claim, credential
   hash, authorization or cumulative value.
7. Establish and verify the independent AP/client fixture. Re-establish native
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
seconds while retaining the 30-second delay only for transport failures. Keep
the freshness limit at 10,000,000,000 ns. Require exactly 16 complete jobs,
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
only credential-free aggregate results and hashes. Report Attempt 1, Retry 1
and Retry 2 charges separately and cumulatively. Preserve the Package 9,
Package 10, Package 11 Attempt 1 and Package 11 Retry 1 failures and bind both
passed host-only repair retests.

Adversarially alter every closure-critical class, including candidate and host
identity, fixture separation, admission, clock-poll and credential-repair
dependencies, credential hashes and protection metadata, both prior-attempt
charges, Retry 2 authorization, cumulative accounting, replay-class
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
