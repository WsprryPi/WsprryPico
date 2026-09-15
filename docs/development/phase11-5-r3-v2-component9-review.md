# Component 9: bounded retained-state LOAD replay validation passes

**The bounded LOAD/replay regression is CLOSED on the recorded Pico A image and
setup.** The exact primary request, identical replay and fresh-ID replay each
returned all 512 adjustments within five seconds under comparable measured TLS
pressure. The full observation interval and unchanged resource gates passed.
Group 2 remains OPEN for its broader RF, capacity, timeout and USB-pressure
assertions. Earlier failed attempts retain their original results.

The [prompt](phase11-5-r3-v2-component9-prompt.md) defines this newly authorized
period. The [result](phase11-5-r3-v2-component9-result.json) records exact
identities, counters, measurements, final states and private-evidence hashes.

## Candidate and execution

Clean source is `98f5797d77fb2bc4c11a4e80f6ff35d7ad16a5b5`. The build uses local
SDK 2.3.1 and GCC 15.3.1, Pico 2 W / RP2350 Arm, 138 MHz GP2 PIO/DMA and RAM
rendering. Linked allocator-hook, stack-guard and renderer checks pass. The
renderer remains 660 bytes at `0x200012d8`; heap capacity remains 219,712 bytes.
The pinned host picotool converted the ELF and verified the single serial-specific
flash. UF2 application boundaries were checked before deployment.

Pico A serial `0BF4B4AEC9FFB344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`,
now runs that image on boot `b1c0af7bef6ef0bef8f5e44130182149`. The allowance
charged exactly one BOOTSEL and one flash. Admission verified a changed boot,
the new source, unchanged configuration and all resource/capacity prerequisites.

One E6 preparation LOAD completed, followed by ABORT/RELEASE. Its Aborted record
was retained while request-cache aging reached 310.056 seconds. The existing
host fixture used retained credentials and independently armed cleanup. Two
healthy network samples confirmed link 3 and 10.77.15.10 before TLS started.
No Wi-Fi recovery cycle or Pico configuration write was needed.

| Exchange | Request bytes written | Response payload bytes | Total elapsed seconds |
| --- | ---: | ---: | ---: |
| Exact C7 primary | 52,105 | 54,916 | 2.245072864 |
| Byte-identical replay | 52,105 | 54,916 | 2.260196109 |
| Same-job fresh-ID replay | 52,105 | 54,916 | 2.297352585 |

Elapsed time includes request writing. Independent reconstruction verifies all
framing, CRC, schema, identities and 512 exact adjustment values. Replay responses
match the primary apart from the fresh request ID. Loaded/inactive ownership was
verified before acknowledged ABORT/RELEASE.

## TLS and resource evidence

The persistent authenticated TLS/WTP observation lasted **90.004 seconds**, with
four successful HTTPS status GETs at the required spacing. There are 89 complete
single-flight INFO samples; their maximum completion gap is 1.455 seconds.
Baseline observation exceeds 30 seconds before the primary, and the final sample
is more than 30 seconds after the fresh-ID replay completes.

Each exchange has INFO samples bracketing its start and completion. The sampled
TLS allocation is at least **31,384 bytes** in every bracket. The fresh-ID bracket
also includes a 54,494-byte sample during overlapping network activity. No lower
pressure result was substituted for the specified comparison.

Peak allocator use is **182,752 bytes**, leaving **36,960 bytes of headroom**:
**4,192 bytes above** the unchanged 32,768-byte reserve. Allocation failures and
TLS allocation failures remain zero. Both stack guards pass; final core 0/core 1
stack use is 8,700/940 bytes. Fault and RF counters remain zero.

This is direct target evidence for the repaired bounded workload. The old
190,424-byte peak and new peak come from different boots and complete observation
histories; their difference is not an isolated allocation-site measurement.
No broader saturation, fragmentation, RF coexistence or repeated-cycle claim is
made from this single validation.

## Adversarial review and reassessment

The new v2 scope binds the repaired source without changing historical v1,
continuation or Wi-Fi-recovery packet identities. It allows one flash and no
Wi-Fi cycle. Source identity checks follow the selected packet throughout
candidate admission, INFO observation and final inventory.

Audit review added per-exchange TLS brackets, full network duration, explicit
replay payload length, and post-observation coverage measured from the last
replay. Deployment auditing connects the frozen packet to the raw BOOTSEL
command/acknowledgment, verified flash, changed boot and candidate inventory.

The first altered-evidence tests exposed a limitation in their helper: a USB
event can start in the primary's final read and finish during the replay's first
read. The helper now reconstructs the entire USB stream and preserves each
frame's completing read before applying semantic mutations. The production
runner and auditor already retain that stream across exchanges. No physical
retry or firmware repair was needed for this test correction.

The final new suite checks successful bounded acceptance, limits an otherwise
successful lower-pressure trace, and rejects 23 altered-evidence cases. These
cover each reply's adjustment values, replay size and deadline, request/job and
owner identity, allocation/stack/reserve violations, stale firmware, premature
cache aging, flash and replay counts, BOOTSEL bytes, deployment identity,
TLS/HTTPS integrity, shortened observation and final restoration authority.
The affected eight CTest targets and 14 runner cases pass. Original failed-capture
suites continue to preserve their outcomes and reject their recorded alterations.
Reassessment found no remaining actionable issue in this bounded validation.

## Restoration and closure

Independent post-restoration verification completed **752.627 seconds** after the
new period began, within its fixed work and cleanup deadlines. Both Picos report
Empty, inactive, unowned and scheduling disabled. Configuration is unchanged.
Pico A retains the new E6 and C7 Aborted records on the tested image. Pico B
remains source `8921a7008183`, boot `6684b4b197d80cfa0ce83b3aaf205cb0`.

The fixture is restored, including protected host services/files, management
interfaces and radio state. Installed WsprryPi PID 1957 and executable hash are
unchanged. Captures, credentials and generated images remain private.

The repaired idle LOAD reply and both replay gates are now closed for this
recorded retained-state/TLS scope. No full normative Group 2 assertion gains RF
or maximum simultaneous workload credit from this check. Resume the remaining
assertion-level Group 2 work from this successful prerequisite, with a separately
bounded physical packet for the selected next workload.

```sh
python3 tests/phase11_5_load_reply_validation_audit_tests.py \
  --evidence build/phase11-5-r3-group2-component9/evidence
```
