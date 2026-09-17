# Phase 11.5 Package 8 execution and adversarial review

## Outcome

Package 8 is **COMPLETE** and R5 is **CLOSED 8/8**. Phase 11.5 advances to
**5 of 6 families closed**: R1-R5 are closed in their recorded scope; R6
remains open. No complete Phase 11.5 configuration is accepted.

The [execution prompt](phase11-5-package8-prompt.md) froze two bounded physical
runs: one network recovery job and one retained autonomous job. The
[machine result](phase11-5-package8-result.json) binds the accepted evidence,
the [raw audit result](phase11-5-package8-raw-audit-result.json) records the
offline assessment, and the
[adversarial result](phase11-5-package8-adversarial-result.json) records the
final mutation assessment. Raw evidence remains outside Git under
`build/phase11-5-package8/evidence/`; its credential-free archive SHA-256 is
`cfe88bd9cb8852640a4044fcd67b8baf240aaa8b546dd248bb5644df7adfd82b`.

## Candidate and source impact

The accepted candidate is Pico A source
`7c5296471250cc06416c79a73c9627aed0eb3624`, UF2
`c73e0714572cb0edd7f3ba4c6c0c9e3b3a8ac500aca7a7edea23fc4b32cb9e87`
and final boot `f93fe05254d1523e50b16b0ad248a44a`: Pico 2 W / RP2350 Arm,
138 MHz, divider 1, GP2 PIO/DMA, RAM rendering and autonomous WSPR base
135,500 Hz. Pico B remained on source `8921a7008183` and boot
`6684b4b197d80cfa0ce83b3aaf205cb0`.

The exact production/source range from the Package 7 candidate `2b25ca0` to
`7c52964` changes five paths: top-level host-test registration, read-only
storage-position accessors, build-selectable/reportable autonomous base
frequency, and the Pico network reconnect state. The diff hash is
`6e724bf7ddfdb072008439fe2240eeba28e0c16d56b83b484a671b9b4aab79a6`.
The RF renderer, PIO/DMA timing, WTP ownership and request semantics, protocol
limits and physical mode compilers are unchanged. Package 8 directly exercises
the changed scheduler/storage observations and repaired reconnect state. R1-R4
remain applicable; the earlier R5 idle Wi-Fi OFF/ON result remains accepted
without being relabeled as a new measurement.

## Implemented changes

- `STORAGE` exposes journal health, sequence, relative offset and record size
  without returning retained configuration or credentials.
- The autonomous WSPR base is a pinned build value and is reported in status.
  The physical candidate used 135,500 Hz.
- Failed or stalled CYW43 join states now perform a bounded leave, allow one
  second for driver polling, and then issue the next rate-limited join. A
  working `NOIP` association remains available for DHCP recovery.
- The Package 8 runner freezes packet, helper, source, image, boot, reservation,
  configuration-write and RF budgets. Its storage retry admits one exact
  authorized boot transition only after fresh two-board inactive evidence.

## Network run and repair

The first pre-CLAIM attempt stopped on a harness interpretation error and
submitted no RF. The corrected original-candidate attempt submitted one
240-second 135,500 Hz Tone. USB proved the job ran and completed locally during
the address/AP fault, but the Pico stayed in CYW43 `BADAUTH` after the AP
returned and never reacquired an address. That packet is retained as a real
product failure; it receives no R5 recovery credit.

The reconnect repair was built, linked-checked and deployed with one additional
zero-RF flash/BOOTSEL packet. On source `7c52964`, the bounded retry passed:

- USB recorded 1,047 Running/output-active samples for the same job, owner and
  boot, followed by one Complete terminal and inactive output.
- dnsmasq changed the owned lease from `10.77.15.10` to `10.77.15.20`; the AP
  was externally down for 15 seconds and restored once while RF remained local.
- The stable certified name resolved natively to only `10.77.15.20` twice.
  Authenticated WTP and HTTPS recovered on the same device/boot and HTTPS
  returned 200.
- SNTP reported eight accepted samples and zero rejected samples at closure.
  AP and client captures reported zero kernel drops.

The post-recovery HTTPS check first encountered a harness-only Python name
collision after every physical network condition had passed. A zero-RF,
zero-mutation continuation renamed the helper, revalidated the preserved raw
RF/network evidence, performed the missing authenticated HTTPS check and
released the held reservation. The completed RF job was not repeated.

## Storage and autonomous run

The original storage attempt saved the enabled schedule at sequence 69/offset
0, rebooted once, observed the unsynchronized admission gate and advanced the
occurrence watermark. Its network observer had been opened minutes before it
was needed; the device correctly closed that idle connection before the
autonomous occurrence. The runner stopped the Armed job before output, restored
the disabled configuration at sequence 70/offset 2048 and retained the failure.
It consumed two configuration writes and one reboot but **zero RF jobs**.

The corrective packet froze that exact failed log and state. It authorized one
110.592-second autonomous job, two configuration-write attempts and one reboot,
with zero direct `LOAD`, `ARM`, time command, flash, BOOTSEL or Wi-Fi cycle. It
opened separate authenticated network observers only at Armed and Running. The
retry passed:

- sequence 70/offset 2048 advanced to the enabled sequence 71/offset 4096 and
  the restored sequence 72/offset 6144, crossing the planned bank boundary;
- after reboot, the enabled retained configuration was first observed with an
  unsynchronized clock, unchanged watermark, Empty state and inactive output,
  then with synchronized time before occurrence reservation;
- the expected local owner and occurrence-derived job appeared at Armed and
  Running. USB recorded 21 Armed, 462 Running/output-active and one Complete
  sample; authenticated WTP saw both Armed and Running and HTTPS returned 200
  in both states;
- the one Console configuration attempt during Running returned `busy`; journal
  sequence/offset stayed at 71/4096 before and after it;
- the job ended in one Complete terminal with output inactive. The durable
  watermark advanced to `1789607761000000000`, and the original disabled
  `AA0NT` / `EM18` / 20 dBm / `120/0` baseline was restored with no suspended
  state.

## Aggregate budget and restoration

Across every Package 8 attempt, three RF jobs were charged for 590.592 planned
seconds: the failed-candidate network Tone, the repaired network Tone and the
accepted autonomous WSPR job. The campaign used four configuration writes, two
controlled reboots, two flashes and two BOOTSEL transitions. Storage execution
used no direct LOAD, ARM or time injection, and the campaign used no intentional
Pico Wi-Fi cycle.

Final independent inventories show A Complete/inactive/unowned with scheduling
disabled and B Empty/inactive/unowned on its unchanged image and boot. The
shared reservation is Released. Fixture cleanup restored the original host
interfaces, routes, permanent `time.local` files/services and recovery timer;
cleanup reported no failure.

## Adversarial review and repair

The first adversarial assessment found two actionable evidence-publication
weaknesses:

1. the raw auditor relied transitively on the successful runner for the Running
   configuration rejection instead of independently decoding the Console reply
   and the journal reads around it; and
2. the sanitized-result validator accepted the measured counts but did not bind
   every exact network job, storage occurrence, deployment identity, retained
   failure hash and complete source-impact decision.

The auditor now reconstructs all Console exchanges, requires the single exact
`busy` result, proves the unchanged 71/4096 journal views, checks the complete
network WTP operation sequence and binds all 21 critical raw files by exact
hash. The result validator now requires the full identities, deployments,
failure set, source-impact decision and evidence map. The second adversarial
assessment rejects all 46 altered cases and then accepts the intact result
again.

## Validation

The host checks cover the reconnect state machine, scheduler/storage behavior,
bounded retry validation, exact reservation boot-transition reconciliation,
raw/sanitized evidence validation and adversarial reproducibility. All 69
registered host tests pass. Focused checks pass 8/8 Package 8 tests, 13/13 RF
reservation tests, 4/4 Package 6 tests and 7/7 Package 7 tests. The candidate
also passes its linked stack, heap-separation, RF-renderer and flash-layout
checks. The hardware observations above are the physical evidence; host tests
are not used as substitutes for them.

## Remaining boundary

Package 9 is next. It owns R6's bounded mixed workload: 30 cumulative normal
minutes, finite demanding launches, three comparable post-warm-up windows,
interleaved quiet periods and final equivalent-state resource gates. Phase 11.5
remains OPEN at 5/6 and `accepted_configuration` remains null until R6 closes.
