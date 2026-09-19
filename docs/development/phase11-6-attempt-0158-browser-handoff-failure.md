# Phase 11.6 2200 m WSPR repeat failure: attempts 158-160

The fresh v20 repeat group stopped without retry. Production attempt 158 and
controller-disconnect attempt 160 each completed one full WSPR emission, but
they are retained as noncredit because the required three-consecutive-slot
group did not complete. Browser attempt 159 made no browser mutation and no RF
transmission.

The failure was in the host acceptance harness, not the Pico. At
`1789814509096368876` UTC ns the USB observer was about 2.496 seconds before
the controller job's predicted terminal. Its old binary choice was either a
25 ms poll inside the two-second window or a five-second sleep outside it. The
five-second sleep crossed the window, and exact terminal/status/release
authority reached the already-open browser with only about 6.75 seconds before
the immutable third-slot target. The frozen plan requires at least eight
seconds, so the browser submitter correctly stopped before `HELLO`, `CLAIM`,
`LOAD`, or `ARM`.

The repair caps each long sleep at the entrance to the two-second terminal
window. For the observed 2.496-second offset it sleeps 0.496 seconds, then uses
25 ms polling. It does not lower the eight-second gate, alter RF payloads,
change firmware, or change the companion executable. A deterministic regression
test covers the exact observed offset.

The failed parent IQ capture is retained privately but is incomplete and earns
no row credit. Automatic reconciliation proved both boards empty and inactive,
then released the shared reservation. The sanitized immutable facts and private
evidence hashes are in
`phase11-6-attempt-0158-browser-handoff-failure.json`.
