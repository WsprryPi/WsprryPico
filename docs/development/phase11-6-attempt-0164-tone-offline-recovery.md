# Phase 11.6 2200 m TONE acceptance: attempt 164

Attempt 164 completed its five-second 2200 m TONE emission, retained the full
SDRplay capture, overlapped the armed/running/complete lifecycle in the shipped
browser page, and reached an authoritative complete terminal before release.
The physical runner nevertheless stopped after capture because its host USB
reducer required every older terminal record to be `complete`. The older WSPR
browser job was authoritatively `aborted` and inactive, so that requirement
falsely rejected a safe settled predecessor.

The host-only reducer now accepts `complete`, `aborted`, `missed`, or `failed`
for older retained jobs only when `output_active` is false. It still requires
the current job to have the exact loaded/armed/running/complete lifecycle and a
single complete inactive terminal. Regression coverage also proves that an
older nonterminal or output-active record remains rejected.

Recovery was offline and caused no new network-to-Pico, USB, SDR, or RF access.
It reconstructed every controller request body from the immutable attempt and
compared the framed bytes to the retained wire hash, verified the post-ARM
disconnect and authenticated reconnect, matched network and independent USB
terminal authority, revalidated the capture and browser evidence, and matched
the reconciled empty/inactive state and released reservation. The RF analyzer
then passed the original 46,000,000-byte capture. One RF job and five planned
seconds remain charged; no retry or retransmission occurred.

This is accepted relative conducted evidence for the 2200 m TONE matrix row.
Its frequency axis is receiver-indicated and uncalibrated, its spectrum claim
is in-band and relative only, and capture timing does not independently
calibrate UTC. Sanitized immutable facts and private evidence hashes are in
`phase11-6-attempt-0164-tone-offline-recovery.json`.
