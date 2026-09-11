# Phase 11.5 closure execution

Status: IN PROGRESS. Selected configuration remains physical PIO/DMA at 138 MHz,
SRAM renderer. P3 passed its allocator-instrumented diagnostic; full A-G acceptance remains open.
The accepted list is empty. This continuation does not erase any prior attempt.
Current state: N0 is restored; the clean 6e2ddc9 candidate and
[N1 lifecycle/management packet](phase11-5-device-fixture.md) are prepared.
N1 authorization and full A-G execution/evidence review remain outstanding.

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

At the first source milestone, host tests covered transient realloc overlap, failed realloc retaining its original
block, overflow, zero-size realloc, nullable failure, released probes and concurrent
recursive calls. An initial firmware link failed because SDK pico_wrap_function
sets INTERFACE options, which do not apply to the executable itself; explicit
PRIVATE linker wrap options fixed the build. No image had been flashed at that
source milestone; the later authorized P3 execution is recorded below.

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
matched the preserved campaign identities. Hardware execution had not yet begun
at that milestone. The subsequent stages below retain their own identities.

## P3 and N0 execution

Clean allocator-instrumented source `3eac6ec030963a5318515ce5f4683acf6fa88506`
passed three 10-second 135.5 kHz Tone jobs under the continuing flashing/RF
authorization. The [P3 result](phase11-5-allocator-result.json) binds its exact
138 MHz SRAM image, boot, jobs, raw evidence hashes and inhibited restoration.
The full/short minimum remaining-word reserves were 7,339/16,384 and 2,030/2,312;
maximum worker service gap was 2,060,000 ns against 2,849,391 ns. All three local
launch/tail/completion sequences passed with no DMA errors. The allocator peak
was 42,640 bytes versus a 27,496-byte sampled peak; no allocation failed.
Mallinfo sampling accumulated 23,888,402 microseconds in a 79.28-second diagnostic,
including timer quantization/interruption effects. Its full-contention cost
remains a gate. P3 is not full N, A3, stack, fragmentation or RF qualification.

Independent final reads confirmed A restored to inhibited `802c91a7b86e-dirty`,
boot `e3634081a2c5844524ab64eb2afeab71`, and B unchanged, inhibited and inactive.
wspr5 remained on its original boot and installed service PID 1957. Ethernet lost
its IPv4 lease after P3; NetworkManager reported a duplicate involving wspr5's
own wlan1 MAC. Read-only investigation verified working Ethernet IPv6 SSH.
No ordinary-LAN repair or sysctl change was made.

The separately authorized [N0 host fixture](phase11-5-network-fixture.md) is now
up: wlan0 AP at 10.77.15.1 and wlan2 independent client at 10.77.15.2, with distinct
network/mount namespaces and no client default route. Its independent six-hour
cleanup is armed, the Wi-Fi recovery timer is temporarily paused, and installed
WsprryPi PID/binary/INI and ordinary wlan1 management remain unchanged. N0 opens
no Pico endpoints and is not evidence that a device joined the fixture.

## Stack-reserve and production idle review

The linked stack review found a concrete `.su` limitation: PioDmaSink dispatch's
56-byte report omits eight bytes visible in its 64-byte linked prologue. The next
candidate installs the SDK's RP2350 Arm MSPLIM mechanism before each core's
runtime work, with an exact 4,096-byte reserve inside each 16 KiB stack. It
reports register/stack identity and sticky stack-fault state from the owning
core. Readbacks, startup routes and constants require exact-image validation;
the [metric contract](phase11-5-metrics.md) does not transfer P3 evidence to this
changed image or claim target execution from source tests.

N0's first adversarial pass found that a namespace-listing exception could skip
timer restoration. Cleanup now catches that failure independently and still
attempts to restore the recovery timer. Ten hardware-free ownership/deadline/
cleanup tests pass. Both linked network-on guard images pass startup/readback,
allocator-route and SRAM-renderer checks; guard policy and five image-mutation
test methods pass. Remaining image/host checks are recorded at the final freeze.

The actual Pi idle application had no periodic STATUS after startup, allowing
the Pico's five-second WTP idle timeout to expire. A scoped read-only poll now
uses the existing parent event loop and application serialization, at most once
per second while Idle/Ready. It does not poll during pending/active jobs, mutate
foreign ownership, reconnect a disconnected session or recover unresolved work.
Application and production regressions pass; the actual native TLS idle test
and final clean executable identity remain to be recorded.

The final guard source checks passed all 47 host tests, the separate ASan/UBSan
stack-policy and RF-worker tests, and the separate worker TSan test. All four
network-on/off standard/physical development images passed linked endpoint,
layout, allocator and stack-guard checks. Those development images were dirty
and were never flashed; clean artifacts and physical evidence remain required.
An adversarial recheck found no remaining actionable guard or idle-poll finding.
The guard is an enforced MSP reserve for this Arm target, not a measurement of
worst-case call depth or qualification of a different image.

## Lifecycle review before full-load admission

Both directions of actual-client interoperability passed against the reviewed
Pi idle-poll fix (`fb0a2eb50c1ea1792324139412990341592db452`). Pico's 46 other
checks passed on the reciprocal build; its two loopback tests initially could
not start servers inside the sandbox and then passed outside it. The original
startup-failure log is retained.

Review found physical firmware excluded the idle USB WIFI OFF/ON controls even
though HTTPS could disable that same network. Exposing the existing idle-only
Console branch in both images supplies the necessary local re-enable path for
D4. It does not change the scheduler's idle gate or expose inhibited packet
tracing in the physical image. The `598a5ad7fa82` four-image build is retained;
the new route requires another clean artifact identity before acceptance.

A guarded management helper and candidate lifecycle are being prepared. Their
state keeps ambiguous writes and unexpected boots blocked, reserves the final
configuration write for original restoration, checks both core guards, and
requires a separately armed owned restoration timer. They have not been staged
or executed. The N0 host-only authorization does not configure a Pico.

## Current source, fixture and adversarial disposition

The final runtime pair is Pico `6e2ddc9e476986046de74d18cbcc3a2f6b64d142` and
Pi application `fb0a2eb50c1ea1792324139412990341592db452`. Clean detached source
snapshots avoid circular metadata-only pin changes. Both actual interoperability
directions passed, including the eight-second idle session, unchanged 60-second
scheduled wait, partial I/O, lost-reply replay, ownership and identity recovery.
The Linux application built cleanly with ancillary GPIO excluded; its SHA-256
is `08af5ad6dd21592a7ff90d898dd971a1e740cbb3836f65e74ba3816b960f4507`.
It remains uninstalled and has not connected to a Pico in this stage.

The [four final linked records](phase11-5-lifecycle-images.json) preserve ELF,
map and UF2 identities. Physical network-on linker heap capacity is 218,408
bytes; each stack reserves 16 KiB with a 4 KiB enforced reserve. Capacity and
linked checks are not measured target headroom or contention acceptance. The
prior 3eac6ec and 598a5ad artifacts remain private and are not substituted for
this candidate. All 51 current host tests pass; earlier separate ASan/UBSan
stack/worker and TSan worker runs pass. No runtime C/C++ change followed the
final image freeze.

N0 setup and four independent verifications succeeded. Its first cleanup
checked NetworkManager before disconnected/address-removal convergence, then
skipped the second radio's power-save restoration. Read-only reconciliation
confirmed the transient state had settled and identified that remaining power
setting. The unchanged frozen helper then completed the already-authorized
restoration. Final independent checks show both test radios disconnected with
power saving on, test namespace/addresses removed, chrony access denied, recovery
timer active/enabled, and installed WsprryPi PID 1957/binary/INI unchanged. The
future helper waits at most twenty seconds for convergence without replaying a
mutation. Its cleanup/ownership/deadline/DNS tests pass.

The [N0 result](phase11-5-network-fixture-result.json) retains both attempts.
An independent auditor reconstructs final P0 Console and WTP bytes, frame CRCs,
request/response identities and state. It also checks staged helper hashes and
separate final host evidence. Seven corrupted evidence variants were rejected.
A and B retain inhibited boots `e3634081a2c5844524ab64eb2afeab71` and
`4e2fb851c08b278dd4b977104d2c2aaa`, respectively, empty/unowned/output false.
No Pico configuration, firmware or GP2 operation occurred during N0.

The next lifecycle restores only a known safe boot and original configuration;
ambiguous writes and preserved firmware/RF faults block reset. Its journal
verifier was repaired to reject a corrupt record instead of selecting an older
configuration. Management now reuses one logical session, preserving the
separate deliberate exhaustion case. The next fixture explicitly supplies
`clock.phase115.test` without upstream DNS so time-server resolution is actually
part of the workload; completed N0 used a numeric address.

Pi's opt-in TLS observer passed eight concurrent mutual-TLS streams, complete
plaintext reconstruction and six malformed-log variants. Its first loopback
fixture omitted mutual client authentication and stopped at the required peer
certificate check; the corrected mutual-TLS fixture passed. The production load
driver was repaired so a raised exception cannot become a successful finish
merely because its child exits zero. Scope/INI and exception-path regressions
pass. Logging adds synchronous host work and remains part of the measured
workload; a clean capture still requires independent rate and WTP wire audit.

Repeat adversarial assessment found no further actionable source/evidence
finding within this prepared scope. Physical N1 admission, exact per-case
workload coordination, all A-G resource/contention results and their adversarial
assessment remain open. Section 5 of the original request requires missing
network/USB-management authorization; N0 explicitly excluded Pico control.
The consolidated N1 packet is prepared locally and has not been staged/run.
Existing flashing/RF authorization remains recorded.
