# Phase 11.6 2200 m WSPR timing-gate failure: attempts 161-163

The fresh v21 group stopped without retry. Production attempt 161 and
controller-disconnect attempt 163 each completed one full WSPR emission, but
remain noncredit because the required three-consecutive-slot group did not
complete. Browser attempt 162 completed the shipped page's `HELLO`, `CLAIM`,
raw `LOAD` and `ARM`; the Pico accepted that job only 2.439 seconds before its
immutable target. The frozen campaign threshold is eight seconds.

The sequence-159 terminal-poll repair worked. Exact authenticated predecessor
authority reached the already-open page with 9.236 seconds of lead. The four
browser mutations then consumed 6.798 seconds before the accepted ARM clock
sample. Even with authority at the controller waveform's exact terminal, a
110.592-second WSPR frame leaves only 9.408 seconds before the next two-minute
slot, or 1.408 seconds after retaining the required eight-second margin.
Production WsprryPi independently requires 13.1 seconds of preparation lead.
Therefore no ordering of the required production, browser-raw and disconnected
controller principals can meet all frozen gates in three consecutive slots on
this configuration.

The browser runner stopped after receiving the ARM acknowledgement, but the
accepted target subsequently reached `running` before reconciliation. Exact
authenticated recovery issued one abort and proved output inactive; Pico A is
retained in `aborted`, Pico B in `empty`, and the shared reservation is
`RELEASED`. The browser attempt is conservatively charged its full planned
110.592 seconds, making the group total three jobs and 331.776 seconds.

The threshold, payload, waveform, firmware and companion binary remain
unchanged. Another WSPR retry is not justified. This is a retained acceptance
failure; independent non-WSPR rows may continue. The sanitized immutable facts
and private evidence hashes are in
`phase11-6-attempt-0161-browser-arm-lead-failure.json`.
