# Group 2 component 3: physical admission and bounded retest

Component 3 finished with a pre-ARM LOAD reply failure. Group 2 remains OPEN;
no additional Group 2 assertion closed. E6 passed all seven idle admission
checks on candidate `4dad112c8a4c0ce4e5be77ecba5c3c460496472c`. C7 did not reach
RF or its maximum-input exchanges. Historical C2/C3/C6 failures and checkpoint
048 remain unchanged and bound to their original images.

## Exact physical scope and result

One flash installed the Component 2 Standalone RF image on Pico A, serial
`0BF4B4AEC9FFB344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`. Its UF2 SHA-256
is `4b4ddd6c9108d20cb7718756da047e4ddd0d4948e6c432d3aa1329d55150d08a`.
The new boot is `b512a9e82baeee7580de50adf888d32b`. The engine remains GP2
PIO/DMA, 138 MHz, RAM rendering, on the retained conducted 50-ohm/60-dB setup.
No configuration or Wi-Fi commands were issued.

E6 independently verified clean image admission, a complete 65,536-byte WTP
payload, 65,537-byte framing refusal with same-connection recovery, atomic
513-event and over-duration refusals, a 512-event/3,600-second idle LOAD, and
Loaded ABORT/RELEASE. This was an idle admission test, not a one-hour execution.

C7 was frozen for one 128-second FSKCW job containing 512 alternating
135500/135495-Hz events of 250 ms. A persistent native TLS/WTP observer and
three HTTP boundary opportunities were planned. The maximum USB input was to
wait for a fresh native Running observation. Its original packet and acceptance
auditor were frozen before execution; no retry or threshold change occurred.

The first failure was the five-second **LOAD response timeout**. The logged
request frame is 52,105 bytes; independent raw INFO then shows Loaded, but the
host records no USB response bytes after LOAD. A later STATUS request also
timed out. There was no ARM, no launch interrupt, no maximum USB stimulus and
no HTTP capacity case. The independent Console captured 300 INFO samples,
all with inactive output. The Loaded job expired with its owner lease and
left an Aborted terminal record, then Empty/inactive/unowned state.

The raw transcript records offered LOAD bytes, not individual host write counts.
The target's Loaded state corroborates admission; this record does not invent
full-write accounting that the ordinary Peer logger lacks.

| Observation | E6 idle admission | C7 pre-ARM attempt |
| --- | ---: | ---: |
| Allocator peak bytes | 140392 | 165464 |
| Linked heap bytes | 219704 | 219704 |
| Allocator failures | 0 | 0 |
| Core 0 measured stack use | See raw inventory | 8700 bytes |
| Core 1 measured stack use | See raw inventory | 940 bytes |
| RF jobs charged/launched | 0 | 0 |

Both stack guards remained valid with zero stack faults. Each stack retains
its existing 16-KiB allocation and 4-KiB guard reserve. These idle/pre-launch
measurements do not establish Running stack, refill or timing acceptance.
The C7 peak leaves 54,240 bytes of total heap capacity, which is not a
measurement of the largest available allocation or of free space at a
particular response-encoding branch.

## Diagnosis and next component

C7 differs from C6: no allocator NULL was recorded, and the failure occurred
while returning the 512-event LOAD response, before maximum input or RF.
`encode_load_response_buffer` refuses when the full response plus scratch and
the existing reserve cannot be admitted; an empty response closes the endpoint.
E6's comparable reply is 54,916 bytes, requiring 88,708 available bytes for that
check. This makes reply admission a concrete source-based hypothesis. C7's
sampled totals cannot prove which branch closed the connection.

The next component should reproduce the exact C7 LOAD and reply lifecycle in a
hardware-free test using the real service/encoder and the measured network and
retained-memory costs. Identify the refusal/closure path, then review the
smallest justified correction. Another physical firmware candidate requires a
new explicitly bounded scope: this period's one repair candidate and one
flash have been used. The original four-hour clock was never reset.

## Review, restoration and publication scope

Before C7, review added a candidate-specific packet policy and a fresh native
Running prerequisite for the USB stimulus. Existing C5/C6 scope checks remain
intact. The ordinary HTTP boundary runner and capacity auditor changes already
present in the working tree are adopted as directly related prerequisites;
C7 provides no successful physical exercise of those HTTP cases.

After C7, a separate stopped-run auditor reconstructs raw Console and WTP data,
exact packet/board/boot identity, the two unretried timeouts, zero ARM, lease
expiry and final authority. Its first draft omitted the producer's `seconds`
field from the expected start record; that expectation was corrected to match
the full producer shape. Twelve corruptions of raw bytes, summaries, identity,
failure reports, final inventory and RF counters are rejected. E6's existing
raw-evidence mutation tests pass. Reassessment found no remaining actionable
finding in this bounded harness/evidence publication. The firmware's physical
LOAD reply failure remains explicitly unresolved.

F7 was restored. Independent checks verify protected files, the installed
WsprryPi process/hash, permanent time.local/chrony/GPSD/Avahi services, and
inactive temporary services. Post-restoration inventories confirm both Picos
Empty/inactive/unowned with scheduling disabled, A on the candidate and B
unchanged. This component used one BOOTSEL and flash, zero extra reboots and
zero RF seconds. Period 3 totals remain one charged C6 job/128 RF seconds;
772 RF seconds remain subject to the original wall-clock budget.

The [machine-readable result](phase11-5-r3-v2-component3-result.json) contains
packet, image, archive, frozen-auditor and restoration identities. Private
captures remain under `build/phase11-5-r3-v2-idle-e6/`,
`build/phase11-5-r3-v2-capacity-c7/` and
`build/phase11-5-r3-group2-component3/`. No credentials or firmware are published.

Reproduce the new failure assessment with:

```sh
PHASE115_R3_V2_C7_EVIDENCE=build/phase11-5-r3-v2-capacity-c7/evidence \
  python3 -B tests/phase11_5_r3_v2_c7_stopped_tests.py
```

The isolated publication tree passed 122 of 151 R3 tests; 29 skipped because
their separate private evidence archives were not supplied. E6 and C7 private
evidence tests ran. The WTP contract checks also passed. All 115 unrelated
pending files retain their original bytes.

The normal CMake R3 unittest-discovery target includes this test. The new
record, relevant runner/auditor changes and tests are the publication scope;
unrelated browser/native work remains untouched. WsprryPi is unchanged.
