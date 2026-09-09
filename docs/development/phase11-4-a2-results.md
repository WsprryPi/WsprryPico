# Phase 11.4 A2 device UTC acceptance

A2's remaining unsynchronized dependent-job rejection passed on 2026-09-09.
The actual Pico clock aged naturally while its Wi-Fi was disabled; an otherwise
valid owned Loaded job could not ARM. Expired holdover and excessive requested
precision also rejected at the intended clock gate. After real SNTP recovery,
a fresh one-second inhibited job completed. This closes bounded A2 in the
[joint matrix](phase11-4-plan.md), not all of Phase 11.4.

The [comprehensive execution prompt](phase11-4-a2-prompt.md) was prepared and
executed under the user's existing test, USB and Pico Wi-Fi authorizations.
No runtime defect or source change was required. There was no clock setting,
synthetic NTP, firmware flash, reboot, saved-configuration write, service pause,
router change, trust change, GPIO operation or RF output.

## Identity and method

- Pico 2 W / RP2350 on wspr5; USB serial `0BF4B4AEC9FFB344`, Console `-if00`,
  WTP `-if02`; device `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Installed standard firmware `23ac5b1aee66`, engine
  `inhibited-standalone-simulator`, boot `1c4730e38aa4e6f8549cbc8c475846bd`.
  The same normal boot persisted throughout. Deployment identity matched;
  storage was healthy. The C2 source-input manifest still matched current runtime
  sources; current Git base `4ef5246` added documentation only.
- Previously verified deployed UF2 SHA-256:
  `a7013feccf36abb9c9da17db057d4d12158942a019d74d787f56336f64a6c8f2`.
  This is retained deployment provenance, not a new flash/readback claim.
- Owner `bd4941645cc646d9a6091c11bd4c26cf`, session
  `b03a4019b9664a51b778dd05b12dc03c`. Exact remote USB helper hashes matched
  reviewed local source. The opt-in private runner sent no clock-source commands.
- Four fresh one-second `tone` jobs at nominal 3,570,100 Hz, within CAPS, with
  60-second leases and ten-second device-UTC ARM lead. Negative cases remained
  Loaded, owned and explicitly inactive, then were ABORTed/RELEASEd before the
  next case. Only the recovered positive job reached execution, still inhibited.

The unchanged discipline marks samples synchronized through 90 seconds, holdover
through 180 seconds and unsynchronized afterward. CAPS independently limits
permitted ARM holdover age to 90 seconds and uncertainty to 500 ms. WIFI OFF
cancels network sampling without invalidating or setting the retained clock.
Polling used real GET_CLOCK state/age as the oracle, not elapsed host sleep.

## Physical results

All observation times are UTC. Sample ages and uncertainty below come from
GET_CLOCK immediately after each negative reply; fresh pre-ARM samples and every
request/response are retained privately.

| Case | Exact observation |
| --- | --- |
| Excessive requested precision | At 14:01:54.718, job `193db3e9887645ad8e14f0988bf5768c` received `CLOCK_UNCERTAIN` for a 1 ns budget. Clock was synchronized, normal leap, uncertainty 149.025015 ms. Matching job stayed Loaded/inactive. |
| Expired holdover | At 14:02:25.061, job `4789da6b5c0c4e8880c23933cebb7233` received `CLOCK_UNSYNCHRONIZED`; clock was holdover, age 93.905771 s, normal leap, uncertainty 150.542175 ms. Its 500 ms budget was otherwise usable. |
| Unsynchronized clock | At 14:03:55.484, job `8d69628be01440329bb005664c650fe5` received `CLOCK_UNSYNCHRONIZED`; clock reported unsynchronized, age 184.329070 s, normal leap and uncertainty 155.063340 ms. Matching job stayed Loaded/inactive until cleanup. |
| SNTP recovery | WIFI OFF acknowledged at 14:01:54.875 and WIFI ON at 14:03:55.793: approximately 120.918 seconds, below the 210-second bound. At 14:04:04.843, accepted SNTP samples had increased from 24 to 25 and the same boot reported synchronized time with 215.707635 ms uncertainty. |
| Positive control | Job `9ced95b0755c47c89540306e1ccac78a` successfully armed for UTC ns `1788962654942815000` with the sampled mapping retained. At 14:04:15.998, authoritative STATUS and matching terminal record reported complete and output false. RELEASE then produced empty/null-owner/null-job. |
| Recovered HTTPS | At 14:04:35.845, authenticated GET `/api/v1/status` returned HTTP 200, matching boot, empty/inactive/unowned and synchronized clock. TLS 1.3, ALPN `http/1.1`, expected `wsprrypico-0a60df.local` with fresh USB address `192.168.1.47`; existing browser certificate/CA, no bypass. |

The HTTPS server certificate SHA-256 remained
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
The source-aging sequence retained an identical UTC-minus-monotonic mapping and
strictly increasing sample age across synchronized, holdover and unsynchronized
observations. It was not a substituted clock sample or host-time adjustment.

## Adversarial assessments and validation

**Round 1 — execution and oracle review.** Checked CAPS admission, full job before
ARM, error precedence, real sample aging, normal leap, usable request uncertainty
for both unsynchronized negatives, fresh starts, leases and exact identity.
Added full request tracing before execution so an error label alone could not
stand in for a valid submitted ARM. Reviewed unexpected-success handling: it
fails the negative case and enters same-owner ABORT/RELEASE cleanup. Finally
restores Wi-Fi even if job cleanup throws; failed authoritative cleanup cannot
produce the success marker. No blind mutation retry is present.

**Round 2 — independent evidence assessment.** Audited all 150 unique request IDs
against matching response operation/session/ID, exactly four LOADs/ARMs, the three
expected negative errors and only one successful ARM. Validated captured protocol
messages against the maintained WTP schema. Checked negative Loaded job IDs,
unchanged clock mapping, increasing age, same boot, SNTP accepted-count increase,
positive completion, terminal records and final unowned/inactive state. The
independent audit passed. No additional actionable runtime finding remained.

**Final scope review.** The original boot-unsynchronized observation, earlier
positive SNTP and 1 ns negative are preserved in the prior records. This run
closes the missing unsynchronized dependent-job behavior by natural sample aging;
it does not claim a fresh-boot race capture, unsynchronized TLS certificate
acceptance, calibrated UTC accuracy, physical leap-transition coverage, production
client recovery, overnight reliability or RF timing. No broader gate was closed.

Host `firmware_profile_tests`, `standalone_tests`, `endpoint_tests` and
`wsprrypico_core_tests` passed **4/4**, 2.81 seconds, after rebuilding their targets.
The initial build command incorrectly used the CTest name `endpoint_tests` as a
build target; its failure was retained and corrected to the existing
`endpoint_driver` target. No test or threshold was weakened. These deterministic
clock-boundary/ARM/standalone/endpoint tests remain separate from physical evidence.

Final USB cleanup at 14:04:16.069 proved the same boot, inactive/unowned empty
state, healthy storage, Wi-Fi enabled, and unchanged AA0NT/EM18/power20, disabled
120/0 schedules, expiry zero and watermark `1788714601000000000`. Time server
remains `pool.ntp.org`. Installed WsprryPi and its service were not modified.

Private evidence is ignored under `build/phase11-4-a2/`: invocation/source identity,
runner, wire log, original build-command failure, passing tests, independent audit
and recovered HTTPS. Wire-log SHA-256:
`36a2c44784785440c5be35608055d13e7ab68bddfa11eb342a6881eb1f80240c`.
Executed runner SHA-256:
`495dcef45210d15058df6138b353ccf682e14907161de8b4cc90fbad55729257`.
No credentials or generated firmware enter Git.

## Documentation Impact

Added the A2 execution prompt and this result/review record, and changed only
A2's matrix status. Existing operator behavior, protocol, firmware and companion
repository remain unchanged. All unrelated Phase 11.4 gates retain their earlier
status; resource qualification and RF acceptance remain later phases.
