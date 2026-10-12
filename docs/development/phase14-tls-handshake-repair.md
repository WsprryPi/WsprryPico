# Phase 14 TLS handshake repair

Status: source repair and Linux validation complete; a clean Arm candidate,
installation and target validation remain. The installed boards still run
`2d67224dbddc` at 138 MHz. No mixed qualification acceptance is claimed.

The original failed mixed result remains immutable at
`repaired-source-mixed-service-guard-20261012T192001/result.json`, SHA-256
`9de8b772e92c3325b596d3c3357c8c5815e2c9d084e39ee8ea568dc03f1bf993`.
B completed 322 browser responses before its next TLS handshake exceeded the
unchanged four-second deadline. No HTTP request was sent for that failed
attempt. Saved INFO immediately after the timeout and before ABORT shows
974 TCP bytes pending, 29,163 TLS bytes allocated, one selected connection and
no allocation/stack/DMA faults. All original IQ, metadata and failure flags
remain preserved; no new IQ hash, transfer or removal occurred here.

## Observed receive defect

A distinct RF-off diagnostic retained 476 TCP-header packets, with no capture
drops, at
`b-tls-handshake-packet-clock-aware-diagnostic-20261012/tcp-headers.pcap`, SHA-256
`777c5a25f1df2896db97770fad0e19dc3a09ad4de04e743e00b7bf6144e94fe2`.
Its result SHA-256 is
`31b381e0d6e9a8fe0ea2026c110a0a7ae323f39c25cf542eb8c66029c63d899d`.
Twenty-two client handshakes completed; the next TCP connection timed out.
This diagnostic sent no HTTP, WTP or RF requests. Some trailing client
authentication data remained unacknowledged after the client's completed
handshake; final selected-connection cleanup was not established by its saved
immediate INFO, so its closeout assertion remains failed. The owned packet
collector and diagnostic parent are gone and the service was restored.

The client emitted a 1,507-byte ClientHello in 1,460- and 47-byte TCP segments.
Repeated traces acknowledge the first segment while the 47-byte tail requires
retransmission. The deployed `PicoServer::pending_receive()` always returns
`ERR_MEM` until foreground promotion, even with a free connection slot.
The exact SDK-pinned lwIP `tcp_in.c` drops subsequent data while
`refused_data` remains refused. This is a concrete reachable receive defect.
The trace does not prove that it alone caused the original 974-byte outgoing
stall or every observed packet loss.

Two earlier diagnostic outcomes are also preserved. The initial programme
refused before TLS because it incorrectly expected the aborted job to remain
present after the firmware's one-hour terminal expiry. Its distinct successor
attempted one connection while B's clock was unsynchronized and was reset by
the deployed admission rule. The clock-aware diagnostic required fresh
synchronization before TLS. None of these outcomes supplies qualification
credit or justifies a timeout/retry/cadence relaxation.

## Implemented repair and validation

TCP acceptance reserves an existing free connection's receive buffer.
Pending callbacks copy bounded input there without TLS setup or allocation;
foreground promotion selects that reserved slot. FIN, reset, admission closure
and pending cleanup clear the staged bytes. A reserved slot is skipped by
ordinary connection polling until promotion, including the SoftAP case.
When all slots are occupied, the existing bounded TCP-window refusal remains.
No additional receive storage, RF algorithm, scientific criterion or deadline
is introduced.

A noncapturing certificate-verification callback now explicitly converts to
its existing function-pointer type. This fixes GCC's rejection of the
lambda/null conditional expression without changing certificate policy.

Linux validation used the retained exact Mbed TLS revision
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, an independently hash-bound source
archive and new ephemeral test credentials. No SDK/tool installation or native
Mac C++ build occurred. Private fixture CMake replaces SDK Git-worktree checks
with the exact archive's full file hashes; production CMake is unchanged.
The original build's test-adapter declaration error, the missing-library
preflight and the later GCC callback error remain in their failed receipts.
Only the previously missing TLS archive link and separately corrected objects
were subsequently built.

The old receive implementation fails the new two-segment pending-input
regression. The candidate accepts all 1,507 bytes, clears them on both FIN and
reset, and leaves TLS allocation unchanged in callbacks. Actual TLS 1.3 mTLS,
ALPN, certificate rejection, HTTP and WTP tests pass, as do the separate Local
WTP and Plain TCP WTP suites. Their intentionally injected allocation failure
is a fixture result, not a target fault.
Closed result SHA-256:
`135888492025020a6d1979ef09ac284f4c54d76e622909a3284a8a91fe0c6344`.
Distinct source/log/process review SHA-256:
`b2ccd48655c7fab2c10d46691ef3d4c40d7f2f93ad2b696d52e581a8c449908a`.
Local fixed metadata is in
`build/phase14-tls-pending-receive-host-closed-20261012/`; credentials, binaries
and samples were not exported. All registered host processes and actual test
server processes were gone at review; the service remained active.

Next: clean 138 MHz candidate and independent rebuild/layout/source review,
finite settings/cursor-preserving installation, then independently admitted
target TLS/packet validation. A new mixed programme/live admission and actual
full storage reserve are still required before the original eight-job workload
can resume. Do not repeat the failed mixed entries or automatically chain the
memory follow-up. Progress remains 3 of 9 workstreams (33.3%); the recorded
15–37-hour estimate may extend. No partial, diagnostic, host or elapsed credit
is applied.
