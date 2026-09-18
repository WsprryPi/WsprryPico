# Phase 11.5 Package 11 Retry 3 — retained-state-safe R6 closure

## Objective

Complete the corrected Package 11 R6 campaign after preserving three stopped
attempts and repairing each demonstrated host-harness defect:

1. healthy synchronized-but-stale clock samples are polled every two seconds,
   while the 30-second retry remains limited to transport failures;
2. all six TLS credential files are content-bound, securely opened and owned by
   the effective campaign user before either host radio is mutated; and
3. prior complete terminal replay records must age to an empty set in a
   separately bounded read-only gate before the unchanged 165,000-byte memory
   gate begins.

Do not change firmware, WTP, the one-hour replay retention, workload, RF timing,
the 165,000-byte memory preflight, the 1,024-byte resource-return threshold or
any Phase 11.5 acceptance criterion.

## Bound evidence and prior accounting

- Repository: `/Users/lbussy/GitHub/WsprryPico`, branch `devel`.
- Original prompt: `docs/development/phase11-5-package11-prompt.md`.
- Retry 1 prompt: `docs/development/phase11-5-package11-retry1-prompt.md`.
- Retry 2 prompt: `docs/development/phase11-5-package11-retry2-prompt.md`.
- Attempt 1 packet SHA-256:
  `ed3255ba7811edef230a6e263e8de94cf13dbb0afbae6c51ee400a70f3622052`.
- Attempt 1 result SHA-256:
  `0bef1850d736535661e2c0ae1bc7519dbff2cfbf06ebacf1c64108b4831b6faf`.
  It charged eight one-second warmups, stopped at the aliased clock poll before
  cycle 1 and earned no R6 credit.
- Retry 1 packet SHA-256:
  `cc3bf2c66075112bccc93557173f256541c6fcecea9637972ada6e55312cec0a`.
- Retry 1 result SHA-256:
  `89a7a1f26b2aa084187d08b24749bde22bec95476a20cddfe397a62f25d9d1a7`.
  It charged eight warmups, completed the matched baseline, then stopped before
  a production ARM on the repaired credential-owner defect.
- Retry 1 adversarial SHA-256:
  `f9c83b32542f0843ca262fcd041c5a8e89b96fcff526917008d50757d61e28b8`.
- Retry 2 packet SHA-256:
  `6408d93a0d7b990c0cb40b5bafb8bc6bfd650b187bfb975984783572c898a1fb`.
- Retry 2 stopped result:
  `docs/development/phase11-5-package11-retry2-result.json`, SHA-256
  `4f4eaf27cd1ad84a84d72b7669e4f72822c25402768d5acc20eb33cc7412c7e1`.
  It verified the credential repair, then stopped before reservation and ARM
  after 360 seconds at 164,776 available bytes, 224 below the unchanged gate.
  It charged zero RF. Four complete/output-inactive Retry 1 terminal records
  remained inside their one-hour retention lifetime at reconciliation.
- Retry 2 adversarial result:
  `docs/development/phase11-5-package11-retry2-adversarial.json`, SHA-256
  `717a3aea894f10ae28881a98bc67b4cb12208a972bb30e1515593fc69a7330c5`.
  All 32 stopped-attempt mutations were rejected.
- Passed zero-RF clock-poll retest SHA-256:
  `92838e20c1de3a998bda67084f75b8deb728049633598ab9e2b5b18b2606fa68`.
- Current Linux host-only credential repair retest SHA-256:
  `b12474628bac9c07e93f86652f92f4c8dae47cb8464f00c06e93245e34aff59b`.

Cumulative Package 11 charge before Retry 3 is 16 RF jobs and 16 seconds:
eight jobs from Attempt 1, eight from Retry 1 and zero from Retry 2. No stopped
attempt produced an accepted R6 resource result. Every attempt ended with both
Picos authoritatively inactive on their original boots, the reservation
released and both host fixtures restored.

Treat Bohica and Bohica-IoT management-router flaps as external events unrelated
to Pico operation or RF behavior. If a new external interruption prevents fresh
evidence, preserve actual accounting and stop without assigning a product cause.

## Exact candidate and fixture

- Pico A: serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, source
  `91933c00970939e366d1bfcf3c1956b59be8f6c5`, UF2 SHA-256
  `5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446`,
  boot `ff719d304f1ba4ac23fddd93561b26f0`.
- Pico B: serial `CDDBF8767C506C07`, device
  `29f20b7342051ef947aa56cb9d4fab42`, source `8921a7008183`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- Pico A configuration: Pico 2 W/RP2350 Arm, 138 MHz, divider 1, GP2 PIO/DMA,
  RAM rendering and configured TLS listener.
- WsprryPi source: `21ae75ab9e38bd6237b1ae73f3e7ab8527324067`.
- `wspr5` is the USB/RF observer and independent client. Preserve Ethernet and
  `wlan1`; use `wlan2`, MAC `e8:4e:06:ae:d7:09`, only in the private namespace.
- `wspr4` is the separate AP host. Preserve `wlan0`; use `wlan1`, MAC
  `e8:4e:06:ac:f3:87`, temporarily as the channel-11 AP.
- `wspr5` publishes `time.local` at `10.77.15.2` from its PPS-backed chrony.
  Pico owns RF timing locally after a complete job is installed.
- Retain the admitted SSID, PSK, subnet, Pico address, TLS identities and
  attenuated conducted RF path. Keep credentials, captures and authenticated
  payloads in mode-0700 private roots outside Git.

## Authorization and finite accounting

Executing this prompt authorizes one fresh Retry 3 campaign with authorization
`PACKAGE11-TWO-HOST-R6-RETRY3` and:

- at most 16 additional RF jobs and 356,800,000,000 planned RF ns;
- at most 480,000,000,000 authorized RF ns for Retry 3;
- zero flashes, BOOTSEL transitions, CONFIG writes, controlled Pico reboots,
  intentional Pico Wi-Fi cycles and allocation probes;
- one read-only terminal-retention gate with at most 600 seconds of polling;
  and
- temporary bounded wspr4/wspr5 fixture operations with cleanup armed before
  mutation.

Charge a job's full planned duration only when ARM is accepted. The maximum
cumulative Package 11 accounting after a complete Retry 3 is 32 jobs and
372,800,000,000 planned RF ns. Do not use unused allowance for exploration or
another run. A stopped or failed Retry 3 requires new authorization.

## Preflight and frozen packet

1. Review the architecture contracts, all Package 11 prompts, all three stopped
   attempt records, both host-only repairs and their adversarial assessments.
2. Run syntax checks, focused Package 9/11 tests, the documented host suite and
   whitespace checks.
3. Confirm the reservation is released; both Picos match their frozen boots and
   are empty, unowned and output-inactive; and both hosts match their frozen
   boots, services, radios, management profiles and recovery timers.
4. Create fresh mode-0700 roots and freeze a new packet. Bind all prior results,
   adversarial assessments, six credential contents, exact source inputs, host
   attestations, binary, observer and retained Wi-Fi input by SHA-256.
5. After cleanup is armed and before radio mutation, securely open and verify
   each credential with real parent directories, final symlink refusal, one
   nonempty regular link, exact packet hash, effective UID/GID ownership and
   mode `0600`.
6. The packet must state each prior charge, Retry 2's zero charge, the fresh
   Retry 3 ceiling and the cumulative ceiling. Reject a missing or altered
   dependency, authorization, restoration claim, credential or accounting field.
7. Establish and verify the separate AP/client fixture, native `time.local`,
   PPS-backed NTP, exact BSSID/channel, authenticated WTP/HTTPS and device
   authority before any reservation.

## Retained-terminal and memory gates

After pausing the installed WsprryPi service, use fresh packet-bound USB
inventory sessions to observe Pico A at 15-second intervals for at most 600
seconds. Require the frozen identity/boot, no owner, inactive output, disabled
schedules, no more than eight unique records, and every retained record complete
and output-inactive. Reject any other state. Reject a record whose calculated
remaining one-hour retention exceeds 600 seconds. Continue only after a fresh
inventory reports zero terminal records.

Then run the unchanged memory gate for at most 360 seconds: available heap must
reach at least 165,000 bytes before network readiness, reservation or RF. Do not
substitute the terminal wait for the memory gate and do not lower either bound.

## Matched replay-state campaign

Run the unchanged workload once:

1. three one-second 383-event production-class normalizers;
2. five one-second 512-event maximum-class normalizers;
3. a 360-second matched baseline;
4. three 600-second normal intervals, each with one 114.6-second native
   WsprryPi FSKCW job, frozen browser cadence, independent observers and a
   306-second application-quiet window;
5. five one-second maximum-class refresh jobs; and
6. a 360-second final equivalent quiet interval.

Before each cycle, poll a healthy synchronized-but-stale clock every two
seconds and retain the 30-second delay only for transport failures. Keep clock
freshness at 10 seconds. Require exactly 16 complete jobs, three production and
five maximum replay classes at every compared post-warm-up state, identical
hashes within each class and the exact final three/five terminal set.

## Acceptance and restoration

Apply every still-relevant Package 9, Package 10 and Package 11 gate:

- baseline, all three post-N windows and final Q are within 1,024 allocated
  heap bytes of baseline;
- the post-N span is at most 1,024 bytes and is not strictly increasing;
- heap capacity minus allocator peak is at least 32,768 bytes;
- both stack guards remain valid with at least 4,096 bytes reserve;
- allocator/TLS allocation failures, DMA errors, unpaired refills, invalid
  reserves, engine diagnostics and recorded faults remain zero;
- both timing metrics remain at most 2,849,391 ns with predecessor/tail evidence;
- both Picos finish empty, unowned and output-inactive;
- the reservation finishes released; and
- both hosts, management connections, recovery timers and the installed
  WsprryPi service are restored with zero capture drops.

A fixture interruption is neither a pass nor product failure. A complete
campaign that misses a product gate keeps R6 open. Never infer inactive output
from a lost connection or process exit.

## Audit, adversarial review and publication

Preserve raw evidence privately. Run the independent auditor and publish only
credential-free aggregates and hashes. Report Attempt 1, Retry 1, Retry 2 and
Retry 3 charges separately and cumulatively. Preserve every stopped failure and
bind both host-only repair retests.

Adversarially alter candidate/host identity, fixture separation, admission,
clock and credential repairs, Retry 2 retention evidence, terminal-retirement
events, every prior charge, Retry 3 authorization, cumulative accounting,
replay classes, lifecycle counts, workload, quiet intervals, resource/timing
gates, reservation, captures and restoration. Every mutation must be rejected
while intact evidence passes.

Repair actionable findings, rerun affected checks and repeat adversarial review
until no in-scope finding remains or an exact external blocker is preserved.
Close R6 and Phase 11.5 only from a complete audited campaign. Then update the
result/review, completion matrix, ledger, plan and development index. Commit and
push `devel`, then verify local HEAD, upstream and remote branch parity.
