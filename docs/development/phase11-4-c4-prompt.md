# Phase 11.4 C4 completion execution prompt

Complete the remaining deferred network-change physical acceptance in C4. Prepare
and execute this prompt, adversarially review the implementation and evidence,
fix actionable findings and repeat the review, then commit and push the scoped
result to `origin/devel`. Preserve earlier failures and all unrelated open gates.

## Boundaries and identity

Read README, CONTRACT, architecture, development checks, Browser API network
transaction semantics, WTP ownership, the acceptance procedure and joint matrix.
Inspect the working tree. Git base is `d1db0f0`; installed standard inhibited
runtime is `23ac5b1aee66`, boot last observed
`1c4730e38aa4e6f8549cbc8c475846bd`. Verify, do not assume, both identity and state.
Pico 2 W/RP2350 on wspr5: serial `0BF4B4AEC9FFB344`, full device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, Console `-if00`, WTP `-if02`.
Standard UF2 provenance SHA-256:
`a7013feccf36abb9c9da17db057d4d12158942a019d74d787f56336f64a6c8f2`.
Use `inhibited-standalone-simulator` only; never touch the adjacent GPSDO.

Existing grants authorize bounded tests, Pico USB and Wi-Fi operations, and
Pico-related capture. This slice needs no RF jobs, clock writes, saved settings,
firmware flash, trust import, router/firewall configuration or installed-service
change. Use existing Linux Python/OpenSSL/socket facilities and tcpdump. No tool
installation is needed. Keep WsprryPi untouched. Run LAN operations outside the
sandbox and retain environmental failures separately from device failures.

## Reviewable physical mechanism

Use existing client credentials and verified TLS 1.3, HTTP ALPN, certified
`wsprrypico-0a60df.local:18443`, expected server fingerprint
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`, and the fresh
USB-reported TCP address. Start with explicit inactive/unowned healthy state,
disabled standalone schedules, synchronized clock and normal deployment.

After a normal TLS handshake, a classic BPF filter may temporarily reject inbound
packets on only the newly created test TCP socket. A separately filtered AF_PACKET
observer captures that exact four-tuple; the TLS MemoryBIO receives reassembled
captured ciphertext using the same authenticated session. This lets the test
inspect a real response while the kernel TCP receiver has not acknowledged it
completely. Already authenticated incomplete prefixes may be acknowledged so
the peer can send subsequent chunks; hold the response-completing suffix.
Do not inject packets, impersonate another endpoint or alter TLS checks. Attach
no global filter. Closing the socket removes its filter automatically.

First prove the mechanism on read-only GET: complete decrypted HTTP response,
no covering wire ACK while held, then detach the socket filter and observe an
ACK after retransmission. If this control fails, stop dependent mutations and
repair the harness/oracle; do not count an ordinary socket close as cancellation
of an unacknowledged response. Limit held response intervals to eight seconds
where practical, inside the server's 15-second HTTP connection lifetime. Bound
each helper run, preserve original attempts and close all helper sockets/capture
handles in finally.

## Acceptance cases

1. Record private owner-only evidence under ignored `build/phase11-4-c4/` and
   unique remote run directories. Bind exact request, revision, response, socket
   tuple, TLS fingerprint, sequence/ACK ranges, USB monotonic timestamps and boot.
2. Canceled response: read a fresh network ETag, request only `enabled:false`,
   receive the complete response with its ACK held, and independently observe
   USB `enabled:true`, `requested_enabled:false`. Reset the initiating socket
   before a covering ACK. Require pending state clears and Wi-Fi remains enabled,
   with same boot and inactive/unowned status. Later authenticated GET must work.
3. Idle recheck: repeat the held response, then acquire a fresh USB WTP lease
   while no job exists. Require matching owner and inactive output. Release the
   ACK; pending change must cancel because the service is no longer idle. Wi-Fi
   remains enabled. RELEASE that same USB owner and verify empty/unowned status.
   No LOAD or ARM is required. If feasible, close an unrelated read-only HTTPS
   connection during the pending interval and prove it cannot finish the change.
4. Acknowledged response: repeat while continuously idle; prove full response and
   pending state before the ACK. Detach the socket filter, observe the covering
   ACK, then require actual Wi-Fi disabled and no pending change over USB. Do not
   infer disable from lost network access. Restore with Console WIFI ON promptly.
5. Use fresh ETags for each mutation; never retry an ambiguous PUT. The consumed
   network revision need not revert after cancellation. Compare original saved
   station, schedules, watermark and time server, not transaction counter equality.
6. Finally resolve same-owner USB authority, close the test socket/filter and
   restore Wi-Fi if this test disabled it. Require same boot, explicit inactive/
   unowned state, enabled Wi-Fi and recovered authenticated HTTPS status. If a
   check fails, preserve the outcome and complete authorized cleanup before review.

## Validation and adversarial review

Review complete-response ACK accounting versus TLS close-notify, RST/FIN ordering,
unrelated connection transaction tokens, late ownership and timeout cancellation.
Challenge capture reassembly, retransmissions, sequence wrap, partial responses,
wrong connection/boot, socket-filter limitations and false passes from automatic
kernel ACKs. Require zero kernel capture drops and agreement between kernel packet counts,
recorded packets and independently parsed PCAPs. Prefer actual packet sequence
evidence plus USB pending-state observations. Deterministic mocks remain separately labelled; they cannot replace
physical canceled-response evidence. Use relevant existing network and actual-TLS
checks with verified build/test names. If a runtime defect is found, add meaningful
regression coverage, repair it and rerun affected checks before deployment claims.

Write a sanitized execution/review record, update C4's status with precise limits,
and preserve the earlier failed GET/capture attempt. No DHCP, unexpected AP loss,
goodbye/cache reliability, reboot, resource or RF gate closes by inference.
Check documentation links, whitespace and staged contents; keep credentials,
captures and generated files private. Commit and push without force, verify clean
checkout and remote parity, then report the actual device state and remaining
limits. Do not claim production-client or Chrome behavior from this direct TLS
transport test.
