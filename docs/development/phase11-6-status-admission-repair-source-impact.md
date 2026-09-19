# Phase 11.6 compact-load and status-admission repair

Attempts 171 and 175 exposed firmware admission defects, not RF waveform
defects. The compact six-event FSKCW request was charged as if it required all
512 event slots and was rejected before RF. During attempt 175, the required
browser observer received four consecutive `503 resource_exhausted` responses
because the generic status gate required 49,152 free bytes while the observed
heap fell to 47,272 bytes with RF and TLS state resident. The DFCW job, capture,
and WTP terminal completed, but the required browser observer failed, so that
matrix row remains open pending its separately authorized replacement packet.

Commit `0e85ff90571c800450073f7b0bfafd70266f1f44` measures a compact message
before allocation and reserves only the event pages it needs. The two JSON
status endpoints use 8 KiB of request scratch while retaining the independent
32 KiB reserve. WTP authority, RF rendering, symbol timing, frequency mapping,
and the retained dot-high/dash-low DFCW polarity are unchanged.

The first image built from this source, UF2 SHA-256
`377f752bac87eb407172f6a4a3b3caf7e0a24502521f9a964fdcc9830095e6f0`,
was flashed once under its own bounded authorization. Its post-flash admission
correctly stopped before requalification because the image had been built with
network port zero and no network credential directory. That failed candidate
remains recorded as a build-configuration error; it performed no RF and was
not retried.

The corrected Pico 2 W StandaloneRF UF2 has SHA-256
`9ac5a40fe6d9a44a3a0156621b82801488efecafb9f472ba601dbcbb3e138398`.
It was built from the same clean detached source with port 18443 and Pico A's
validated credentials. The embedded revision, device ID, and hostname are
`0e85ff90571c`, `fd6127d11d6aca42a9905fa3fb1bf1d5`, and
`wsprrypico-0a60df.local`; linked heap-hook, stack-guard, and RAM-renderer checks
pass.

The corrected image was copied to wspr5 and flashed exactly once to Pico A
serial `0BF4B4AEC9FFB344`. The deployment used one BOOTSEL transition, one
firmware flash, zero configuration writes, zero RF jobs, and zero retries. It
preserved the retained configuration and admitted the expected authenticated
network identity. Pico A now has boot ID
`cab95d7eecad05047fcb1d6806cf9e86`; Pico B remained unchanged.

The required zero-RF check passed through the shipped browser. It performed
`HELLO`, `CLAIM`, `LOAD_MESSAGE`, `ARM`, `ABORT`, and `RELEASE` on the exact
six-event FSKCW compact request. Console and USB observers bracketed the browser
mutations; no RF ran; the final state was empty, unowned, and output-inactive.
The largest successful allocation was 16,693 bytes, allocator and TLS allocation
failures remained zero, stack guards passed, and 151,840 bytes of heap reserve
remained.

The single conducted requalification also passed. One 137.500 kHz TONE ran for
exactly 5.0 seconds with zero retry while the shipped browser completed eleven
manual status refreshes and overlapped Armed/Running. Independent WTP, Console,
and USB observers saw the lifecycle complete and release to empty with output
inactive. The SDRplay `2404058C60` capture retained 5,750,000 CF32 samples with
zero overflow and zero clipping. Offline analysis passed the relative frequency,
duration, contrast, and in-band spectrum checks. Absolute frequency remains
receiver-indicated and uncalibrated; the result makes no harmonic, absolute
power, regulatory, or independently calibrated UTC claim.

The RF allowance closed at one job, five seconds, and zero retries. Both board
reservations were released. The wspr5 client namespace and campaign services
and the wspr4 AP/capture services were removed or stopped, and both hosts were
restored to their recorded pre-fixture interface state. Exact hashes and private
evidence-root names are in
`phase11-6-status-admission-repair-requalification.json`.

The compact-load and status-under-resident-RF requalification gate is now
accepted. Fresh packets are justified for the FSKCW browser-compact replacement,
the FSKCW controller-disconnect replacement, and the DFCW controller-disconnect
replacement. This requalification carries no new matrix credit and does not
justify a WSPR retry.
