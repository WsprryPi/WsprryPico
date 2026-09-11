# Phase 11.5 USB reply delivery repair

The physical A2 baseline at 138 MHz, PIO divider 1 and SRAM rendering failed
on clean firmware `6e2ddc9e476986046de74d18cbcc3a2f6b64d142`. A Console INFO
reply required 2.964660695 seconds during nominal browser and production
controller load. The raw receive trace shows multiple TLS processing gaps
between USB chunks; the server maximum poll was 805635 microseconds. Quiet
and controller-only intervals passed. No RF jobs had been submitted.

The standalone loop now defers TLS handshake steps while a Console reply is
queued, for at most 100 milliseconds per one-second period. Emptying and
refilling the queue does not renew that allowance. The pending check covers
both the software queue and TinyUSB transmit FIFO. USB retains its existing
64-byte service budget. Established connections, timeouts, link loss, service
reconciliation and the independent RF worker continue to run. Both inhibited
and physical standalone images receive the change. Existing timing thresholds
and clock selection are unchanged.

Adversarial source review checked continuous Console backpressure, queue
empty/refill, FIFO-only pending bytes, unsigned timer wrap, disconnect clearing,
established WTP progress, handshake resumption and timeout ordering. Hardware-free
USB tests pass; the pinned native TLS suite passes with a paused second handshake
and an established STATUS request. The first native test launch could not bind
inside the sandbox; the outside-sandbox loopback run passed. These are software
checks, not target acceptance. Both affected target baselines require repetition
on the exact new artifacts. No clock is accepted by this repair.

Pico A was restored to its original inhibited image, boot
`e5a4bc355fe7898a1e0b6d06be36fe9f`, with authoritative inactive output. Comparator
B remained unchanged. Host cleanup completed without failures; installed
WsprryPi PID 1957 remained active, and both captures reported zero kernel drops.
Private N1r archive SHA-256:
`b5c7e93eabae8e0149d7ee227fc540b2c1bf3e59d5830afd8e987296c7b3d82a`.

Documentation Impact: this development failure/repair record. WTP and browser
API contracts are unchanged. Phase 11.5 remains open pending physical acceptance.
