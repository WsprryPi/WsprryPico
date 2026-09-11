# Phase 11.5 closure execution

Status: IN PROGRESS. Selected configuration remains physical PIO/DMA at 138 MHz,
SRAM renderer. P2 passed its bounded diagnostic; full A-G acceptance remains open.
The accepted list is empty. This continuation does not erase any prior attempt.

## Initial findings

- INFO/mallinfo sampling does not capture intervening allocation peaks.
- SDK panic-on-null prevents the TLS allocator from handling actual exhaustion.
- Linked newlib `_malloc_r` is also called directly by stdio and other libc
  routines. Those calls bypass the SDK's outer malloc mutex. Its linked
  `__retarget_lock_acquire_recursive`/release functions are no-ops in the pinned
  toolchain, so they cannot be relied upon for coherent cross-core observation.
- Largest contiguous allocation and both stack call-chain/IRQ allowances still
  need target evidence. A 16 KiB reservation or sampled high-water mark alone
  does not certify the required 4 KiB headroom.
- The old plan reused P2 as a future network-fixture label. P2 now denotes the
  completed SRAM pilot; new closure packets must use distinct names.

## Work underway

Instrument the pinned newlib entry points `_malloc_r`, `_calloc_r`, `_realloc_r`
and `_free_r` using linker wrappers, including nested realloc/calloc work and
libc entry paths. Serialize these and mallinfo/snapshots under an SDK recursive
mutex; keep the original allocator and SDK panic behavior for ordinary callers.
A separate nullable entry is available only to TLS and guarded idle allocation
probes. No SDK/toolchain source is modified or installed.

Record every allocator-entry post-state, cumulative/live peak, largest request,
failures, recursive depth and measurement/entry cost. Prove the linked call
coverage and the ordering of nested allocate-before-free paths before claiming
transient coverage. Do not count nested entries as independent application
requests or add overlapping entry times. The instrumentation's own load must be
part of the exact accepted image/configuration.

`HEAP PROBE <bytes>` proposes one allocate/free while idle, bounded to linked
capacity plus one byte. It retains no allocation; it does not run during owned,
Armed, Running or Failed state. Failed requests use the nullable allocator and
must leave the board available for subsequent authoritative operations. Its
actual target execution belongs in a frozen closure packet.

Host tests cover transient realloc overlap, failed realloc retaining its original
block, overflow, zero-size realloc, nullable failure, released probes and concurrent
recursive calls. An initial firmware link failed because SDK pico_wrap_function
sets INTERFACE options, which do not apply to the executable itself; explicit
PRIVATE linker wrap options fixed the build. No image has been flashed in this
continuation.

## Remaining execution sequence

Finish allocator/link/probe checks and stack audit; prepare clean standard and
physical images, exact jobs and production-controller identity. Assemble bounded
A-F packets with the normal controller/browser/USB rates, failure classifications,
radio/configuration restoration and separate evidence workers. Run short cases
before the 30-minute G1 mixed-load run. Stop on an unexpected failure, repair it,
retain the attempt and rerun affected checks on the new exact configuration.

Publish the accepted configuration only after all nine gates and all 20 cases
have reviewed evidence. Leave 132/150 MHz physically untested unless selected.
11.6 owns per-band/mode conducted RF; Phase 13 owns the systematic clock matrix,
filters, spectra and release qualification.

## Source review and checks before candidate freeze

First adversarial pass found that failed oversized requests would contaminate a
single largest-request metric, and that checking only unconditional linked calls
could miss a bypass. Added a separate largest-successful-request metric, direct
conditional-branch checks, internal mallinfo/trim routing checks and mutations
which must be rejected. Extracted the Console probe's admission so host tests
prove rejected malformed/non-idle requests make zero allocator calls.

The second source review checked nested calloc/realloc and free ordering, the
original SDK panic path, nullable TLS allocation/free compatibility, automatic
recursive-mutex initialization, absence of allocation from the RF worker's IRQ
path, probe release and failed-realloc preservation. No remaining actionable
source finding from that pass is claimed closed by hardware evidence. Target
cost, stack allowances and real allocation-failure recovery remain gates.

Checks executed against the closure source: 43 non-network host tests, three
native TLS/client interoperability tests (including the 60-second idle wait),
focused heap/probe ASan+UBSan and heap ThreadSanitizer. All passed. Both standard
and physical images with network control on/off link and pass heap-call routing,
heap/stack/flash/journal/UF2 checks; both physical renderers pass the SRAM check.
The six heap-routing test methods include bypass, missing nested/stdio path,
indirect allocator call and unserialized mallinfo mutations. Build outputs remain
private. These are software/build results, not completion of A-G.

The all-source physical network-on stack reports contain 2,710 records and no
unbounded dynamic frame. Their largest compiled frame is 3,056 bytes in network
status formatting. This is a preliminary inventory: unused functions must be
excluded and linked call chains, assembly/library paths and IRQ/exception costs
reviewed before assigning a numeric unobserved-stack allowance.

A clean WsprryPi `8a4f01f13517eb20eed90726c7612bc0d3b9eace` Git bundle was staged
under `/home/pi/phase11-5-closure-8a4f01f/source` on wspr5. Its isolated release
build uses `BACKENDS=simulated ANCILLARY_GPIO=0 SUDO=`; it has not been run or
installed. The previously documented Phase 11.4 source directory is absent on
the current host and was not assumed reusable. Host boot and picotool hash still
match the preserved campaign identities. No USB, flashing, RF, radio, service or
GPSDO action has occurred in this continuation.
