# HTTP body allocation repair and preserved P1h failure

Phase 11.5 remains **OPEN, 2/6 families closed**. The
[result](phase11-5-completion-http-pages-result.json) records exact packet,
source, helper and private-evidence hashes. No P1h assertion is accepted.

## Failure and authority

P1h used e64ebb9, boot 0a6d95e11cf712a53e97a4c9938614e9, with one 128-second
512-event FSKCW job. Its two WTP boundaries completed after the polling repair.
The supported HTTP request wrote all 32,981 wire bytes, including its exact
32,768-byte body. Fresh raw INFO subsequently still reported Running. No HTTP
response was observed. Native and USB observations then failed; these failures
did not establish inactive output.

Fresh raw inventory established a new recovery boot,
cb429dd3964439e66e03bb0d93a9863b, Empty/inactive/unowned, with allocation failure
recorded for 32,769 bytes (stage 14, hash 3833354787). The runner's final original
boot check failed, but reservation release used those fresh actual inactive
inventories. Post-restoration inventories independently confirm both boards'
inactive state. Charge the full 128 seconds and retain the unplanned watchdog
reboot separately from controlled reboot allowances.

The failed allocation size matches the contiguous HTTP body string reservation.
The retained record does not identify the exact callsite or prove fragmentation.
Source-level reproduction establishes that this path requests 32,769 bytes;
it does not reconstruct the historical heap layout.

## Repair and review

The HTTP parser now reserves its complete body in nullable pages of at most
4,096 bytes. It reserves another 1,024 bytes for page metadata while retaining
the independent 32,768-byte admission reserve. Any page failure closes parsing
as resource exhaustion and immediately releases all partially allocated pages.
Copied requests retain shared body storage. The API reads JSON and hashes replay
identity directly from the pages; configuration materialization retains its
existing size, revision, redaction and storage rules.

The pre-repair valid maximum-HELLO regression reached a successful response but
failed the bounded-allocation assertion. With the repair, parser C++ allocations
remain within 4 KiB and the complete API operation remains within 8 KiB (the
existing host session/replay allocation is 7,424 bytes). These bounds describe
host allocations, not a target largest-free-block measurement.

Adversarial checks cover failure at each of eight page allocations, release of
partial pages, request lifetime after parser destruction/reset, bytewise input
across a page boundary, rejection before allocation above the HTTP limit,
zero-body allocation avoidance, reserve admission, flat/paged LOAD_MESSAGE
replay identity and changed-payload rejection, and paged configuration password
preservation. A configuration test initially exceeded the existing configuration
limit; it was corrected to test valid configuration input without changing that
limit. Seven affected CTest groups and the actual local TLS suite pass.

The independent failure audit reconstructs raw inventories, INFO, USB framing
and acknowledged LOAD/ARM, checks the full HTTP write record, and reconciles
fresh recovery authority, packet accounting, reservation release and fixture
restoration. Two tests pass, including rejection of altered write counts,
Running summaries, missing final inventory and false restoration. No actionable
finding remains in this host repair/failure-audit scope. Physical acceptance is
still outstanding.

## Applicability and next finite work

No RF renderer, worker, mode, timing, ownership, protocol or advertised job/body
limit changes. Preserve prior functional/RF evidence with its original identity.
The parser's storage and static layout change; previous resource margins do not
qualify this candidate. Recheck both linked firmware images, deploy a reviewed
fresh candidate and perform the affected maximum-body/recovery workload during
RF. Reassess retained-state/native LOAD resource behavior because the earlier
idle pass had only 32 bytes beyond the reserve. Do not promote host or old-image
headroom into current target acceptance.

The fixture is restored, scheduling disabled, visible saved configurations
preserved, and installed WsprryPi PID 1957 unchanged. A remains in inactive
recovery pending the reviewed repair deployment. No secret material or raw
payloads are published by this record.
