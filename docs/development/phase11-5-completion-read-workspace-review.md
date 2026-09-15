# Retained replay pass and bounded read workspace

**Phase 11.5 OPEN, 2/6 families closed.** [Result](phase11-5-completion-read-workspace-result.json).

## Physical regression

Clean b0254c5 firmware on A passed three maximum 512-event LOADs followed by a
fresh-ID replay of the third job, with no ARM or RF. Independent raw decoding
checks all request writes, CRC/schema/session identity and all 512 adjustments
per response. Exchanges took 2.114623334, 2.454966464, 2.577591429 and 2.613489643
seconds. One native TLS connection supplied 96 STATUS responses; 88 independent
INFO samples covered the workload. Peak allocation was 186,184 of 218,984 bytes,
leaving 32,800 against the unchanged 32,768-byte reserve. The 32-byte margin is
specific to this frozen workload and cannot establish supported combined load.

Both boards finished Empty/inactive/unowned with scheduling disabled and unchanged
configuration. The original reservation was released after raw final inventories.
A remains on boot 4dad3b38c27aad73da01cefc9e857cdb; B is unchanged. The fixture is
still ACTIVE within its original independent cleanup deadline. No host restoration
is claimed yet. Task charges are five flashes/BOOTSEL transitions, three RF jobs
and 384 planned RF seconds, two Wi-Fi cycles and zero configuration writes.

Two private audit tests accept this packet and reject altered replay write counts,
truncated native captures and changed INFO summaries. Final peak is included in
the reported maximum. Historical failed packets and their claims remain intact.

## Next demonstrated defect and repair

The actual endpoint/service/planner host allocation model reproduces refusal of a
65,536-byte padded STATUS request beside a maximum Loaded job and one terminal
record. The prior decoder requires 32 KiB workspace for every non-replay request,
even an empty-body read that never allocates an event array. At a fixed 18,168-byte
modeled background, the first maximum STATUS request waited five seconds and
closed the connection before this repair.

Bounded STATUS, CAPS and GET_CLOCK envelopes now use 6 KiB decoding workspace.
The existing 32 KiB safety reserve, full schema/identity validation, five-second
admission deadline and 32 KiB new-LOAD workspace remain. Protocol/type/operation
strings are bounded before the small-workspace classification. The replay hint
is passed only for an actual active LOAD replay, independently of read admission.

The new tests fail against the pre-fix source and pass after repair. They check
exact maximum STATUS responses and replay, unchanged Loaded state and preparation
count, real tracked input pages, reserve preservation, escaped operation names,
a large protocol envelope and deferred mutation recovery/expiry. A separately
declared 31,384-byte modeled background still refuses within five seconds while
preserving the reserve. Host backgrounds are not calibrated target acceptance.

Review corrected a new test that lowered its synthetic memory budget before the
frame-storage admission; it now lowers the budget after storage becomes resident,
while the separate allocation model tracks the whole lifetime. Six affected
checks passed initially. Actual TLS failed solely on an expired ephemeral host
server certificate; the failure was saved, fresh local-test credentials generated,
and TLS passed with certificate verification unchanged. All seven affected CTest
targets and eight reservation/cleanup tests pass.

No actionable source finding remains in this bounded repair. Target benefit and
RF coexistence remain unmeasured. The read-only classification leaves active LOAD
replay, terminal retention and RF logic unchanged; preserve the just-completed idle
regression with its original source/boot. Verify new linked layout and measure the
affected read path under the next finite RF packet before accepting capacity.
