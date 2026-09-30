# GP14 unattended robustness target campaign

Status: **bounded automatic diagnostic section closed** (2026-09-30).
All thirteen repaired-image cases, settings preservation and B's accepted
runtime restoration passed.
This executes the bounded procedure in the
[source/build review](phase12-gp14-robustness-review.md), following the operator's
approval to run the prepared B campaign, preserve settings and restore the
accepted runtime. P12.7, P12.11 and Phase 12 remain open.

## Device, artifacts and preservation

- Candidate B: Pico 2 W / RP2350, USB/ROM serial `CDDBF8767C506C07`,
  application ID `29f20b7342051ef947aa56cb9d4fab42`, 4 MiB flash, 150 MHz.
- Host: existing Linux `wspr5`, existing Python 3/pyserial 3.5 and picotool
  2.3.0. No tools or dependencies were downloaded.
- B initially ran `fce8776f6f4e`, with healthy profile generation 2 and access
  generation 1, station Wi-Fi connected, inactive inhibited simulator output,
  released GP14 and no capture fault. Fresh read-only INFO was preserved.
- A was not controlled or flashed. Its last accepted image remains the
  separately recorded `fce8776`; no new A result is claimed.
- No external GPIO stimulus, jumper movement or RF operation was performed.
  The diagnostic substitutes sample bits inside PIO; GP14 stays an input.
  Both cores run the diagnostic's representative XIP workload. No network,
  RF engine or production settings writer is linked into that image.

A fresh verified 4,194,304-byte full-flash backup was copied privately to the
Mac before flashing. Its SHA-256 is
`5c37e691e8a19cf5fcd8a5ba06a84af3d82791357cc8cf1b8d0f629fef400da6`.
This preserves B's current generation-2 profile; no earlier profile backup
was restored. Private evidence lives on wspr5 and under ignored
`build/gp14-robustness-b-20260930/`. Captures, flash backups and firmware are
excluded from Git.

| Artifact | Identity | SHA-256 |
| --- | --- | --- |
| First diagnostic UF2 | `ae6fd97d71a6` | `d32f6b29005161f578ca6cd41f85a3ce21f78575705fb8aaa8ccaa0b9bbd7ed8` |
| Repaired diagnostic UF2 | `e33ee7c398de` | `1e92ac40ce6af6ce0c1da93c1121b07c4707320f1d47880601b530586d7489a7` |
| Repaired diagnostic ELF | `e33ee7c398de` | `fedb61002650c8db9910c248e8eb6ac689d36c0b0874bfb2a01b1ad40bc8f38f` |
| Accepted runtime UF2 for restoration | `fce8776f6f4e` | `716e165e1f74212bdf297ff6f50e467dba7f4cab55ca3e879f94dd271155d7f4` |

The repair's clean source commit is
`e33ee7c398dedf11cf517036c352629f9b5730dd`. Immutable local firmware, map and
manifest copies are in `build/gp14-robustness-e33ee7c/`. Linked text is
93,348 bytes, initialized data zero and BSS 35,784 bytes. Its build commands
are the source review's pinned configure command followed by
`cmake --build build/pico2-w-gp14-robustness --target WsprryPico-GP14Robustness -j 4`.
CMake was explicitly reconfigured after the clean source commit. SRAM,
both-core stack, XIP, reserved-flash and RF/network-exclusion gates passed.

## First attempt and repair

`campaign-01` passed the first eleven cases, including the 610-second hold,
flash blackout, capture-fault recovery and actual watchdog/hardfault recovery.
It stopped during BOOT_HELD when a partial status record remained valid JSON
but lacked required fields. The runner raised `KeyError: reads0`; no complete
campaign success was recorded. The raw failed record remains preserved.

The [repair review](phase12-gp14-robustness-review.md#target-discovered-telemetry-repair)
records the diagnostic USB timeout change from 1 ms to 100 ms and explicit
complete-record validation. Every missing field and invalid integer type now
fails closed with a descriptive error. No malformed evidence is skipped.
The repair passed all 91 host tests, eight focused runner/link tests, Python
compilation, whitespace checks and the pinned diagnostic build/link gates.
There were no C/C++ source changes requiring reformatting.

After the first attempt, guarded maintenance BOOTSEL and verified ROM readback
proved scratch, all settings partitions and the boot sector still exactly
matched the fresh backup. The repaired image was loaded with `picotool -v`;
another reserved-region readback was identical before starting it.

## Execution commands

On wspr5 the private campaign directory is
`/home/pi/gp14-robustness-b-20260930`. The committed runner was staged as
`gp14_robustness_campaign_e33ee7c.py`, retaining the first attempt's runner.
The exact second campaign command, inside that directory, is:

```sh
umask 077
timeout 1000 python3 -u gp14_robustness_campaign_e33ee7c.py \
  --run --serial CDDBF8767C506C07 --revision e33ee7c398de \
  --image diagnostic-e33ee7c.uf2 \
  --sha256 1e92ac40ce6af6ce0c1da93c1121b07c4707320f1d47880601b530586d7489a7 \
  --evidence campaign-02 > campaign-02.log 2>&1
```

The existing picotool is `/home/pi/phase11-4-e1/picotool-build/picotool`.
All its device commands bind `--ser CDDBF8767C506C07`. Backup used
`save -a -v b-before-flash.bin -t bin`; image loading used
`load -v diagnostic-e33ee7c.uf2`; application boot used `reboot -a`.
Reserved-region readbacks use
`save -r 0x103f2000 0x10400000 -v <fresh-file>.bin -t bin`.
Before each ROM transition the runner's connection verifies exact identity
and idle/released capture, then sends `ARM <serial> <installed-revision>` and
`RUN BOOTSEL`. Each transition has a private maintenance log.

## Results and restoration

`campaign-02` ran from 12:00:06 to 12:13:02 UTC (775.4 seconds) and exited
zero with all thirteen actions accepted. Independent
offline replay checked all 2,729 complete telemetry records, the action
outcomes, reset breadcrumbs, both-core/sample progress, unchanged checksums
and post-action continuity. Eight boot IDs correspond to the initial boot
plus seven requested reboots, including three capture-fault cleanup resets.
Transport interruptions occurred only within requested reset/recovery cases.
No telemetry record was malformed or omitted a required field.

| Case | Recorded result |
| --- | --- |
| SHORT | 200 ms, one `would_reset`, no stop/AP |
| MIDDLE | 600 ms, one stop on release, no reset/AP |
| LONG | 11.000 s, stop and AP requests observed while held, once each |
| STUCK | 610.000 s, stop/AP once each; observed held beyond 600 s; DMA blocks 1 → 19 |
| FLASH | Complete 149 ms gesture captured during flash-safe callback; one `would_reset`; pattern and restoration verified; maximum backlog 23 words |
| DMA_STOP | Expected sticky capture fault 7, then clean normal-reset recovery |
| PIO_STOP | Expected sticky capture fault 9, then clean normal-reset recovery |
| OVERRUN | Expected sticky capture fault 6 after suspended consumption, then clean normal-reset recovery |
| RESET | New boot ID, matching normal-reset breadcrumb, no watchdog-expiry or hardfault flag |
| WATCHDOG | New boot ID, matching watchdog-expiry breadcrumb, no hardfault flag |
| FAULT | New boot ID, watchdog recovery and hardfault record `0x80010000` |
| BOOT_HELD | New boot starts with 12 s synthetic low; release causes no stop/AP/reset action |
| RELOAD | 70 s both-core workload, DMA blocks 0 → 2, no capture fault |

Each successful case, or its fault-cleanup reset, has at least two seconds of
subsequent capture and both-core progress. Normal gesture backlog peaked at
three words; the deliberate overrun reached the 2,048-word ring limit and
was rejected. Settings FNV-1a stayed `2708295183` throughout both attempts.
The successful raw JSONL SHA-256 is
`e78d7a5a2de26e9428cabfa47ad50a6dde63dcf90ef9717c948dba5e8dc7c559`.

Verified ROM readbacks compared the full 57,344-byte range
`[0x103f2000,0x10400000)` against the fresh backup after the first diagnostic
load, first failed campaign, repaired load, successful campaign and accepted
runtime restoration load. Every comparison was byte-identical. This includes
scratch, access, BTstack, profile, standalone settings and the boot workaround
sector. No settings partition was restored or rewritten by the procedure.
Both UF2 loads and the final accepted-runtime load used picotool verification.

B was restored to the exact accepted `fce8776f6f4e` runtime. Thirteen read-only
INFO samples covered **61.496515 seconds** of one stable boot,
`5c749a5ecde515ab6488057b21f47a13`. GP14 capture progressed from 12,672 to
74,168 samples; its reported maximum backlog was 131 words. No capture fault,
held input, recovery boot, fault breadcrumb, stop/AP/reset event or additional
reboot appeared. Output remained inactive under the inhibited simulator.
Storage was healthy, profile generation 2 and access generation 1 matched
baseline, and the device remained connected at `192.168.1.53`. Persisted
station/schedule/watermark and configuration fields also matched baseline.

The private archive `gp14-robustness-b-20260930-evidence.tar.gz` is retained
on wspr5 and in the ignored Mac evidence directory. SHA-256 on both hosts:
`f4a6d371297e2a5143fece90abcc13ff1c0e3b9f73c573efafb5d0232cab925f`.
It contains both attempts, failure/result records, raw telemetry, actual
runner versions, maintenance and flash logs, byte readbacks, the fresh full
backup, restored INFO records and summaries. Local independent inspection
repeated all five raw byte comparisons from this archive successfully.

## Adversarial assessment and reassessment

The first failure was retained and repaired before rerunning the entire
campaign on a newly identified clean image. Review verified that no assertion
was relaxed, malformed status is fatal, image/serial/clock are bound, reset
causes and cleanup are checked, and neither diagnostics nor restoration
overwrite settings. The new schema regression and all affected checks passed;
the new complete physical run passed with no incomplete record.

Final review distinguished policy requests from actual RF/AP actions, checked
each expected fault and reset against raw evidence, and checked post-action
core/sample progress. Raw byte comparisons established settings preservation;
the 61.5-second runtime/network readback established bounded restoration
continuity. Reassessment found no remaining actionable issue
within this bounded diagnostic section. No broader production claim follows.

## Acceptance boundary

This campaign closes the bounded automatic synthetic-capture robustness
section. It covers
both-core XIP activity, capture across scratch flash writing, recurring DMA
renewal, long/stuck sample input and diagnostic fault/reset recovery.

The installed accepted runtime remains a separate artifact: restoring
`fce8776` does not deploy the new DMA renewal implementation. A later reviewed
runtime candidate must carry that implementation into integrated acceptance.
The default standard image still leaves GP14 off. The actual RF target's
dependency/stack obstruction, independent shutdown path and active/armed RF
latency measurements remain separate work. Live AP retention/expiry and real
pad/contact overlap with flash writing are not established by synthetic PIO
stimulus. This record does not close P12.7, P12.11 or Phase 12.
