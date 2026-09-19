# Phase 11.6 compact-load and status-admission repair

Attempts 171 and 175 exposed firmware admission defects, not RF waveform
defects. The compact six-event FSKCW request was charged as if it required all
512 event slots and was rejected before RF. During attempt 175, the required
browser observer then received four consecutive `503 resource_exhausted`
responses because the generic status gate required 49,152 free bytes while the
observed heap fell to 47,272 bytes with RF and TLS state resident. The DFCW job,
capture, and WTP terminal completed, but the required browser observer failed,
so the row remains open.

Commit `0e85ff90571c800450073f7b0bfafd70266f1f44` measures the compact message
before allocation and reserves only its required event pages. The two JSON
status endpoints use 8 KiB of request scratch while retaining the independent
32 KiB reserve. WTP authority, RF rendering, symbol timing, frequency mapping,
and the retained dot-high/dash-low DFCW polarity are unchanged.

The exact Pico 2 W StandaloneRF image builds with Pico SDK 2.3.1 and Arm GNU
15.3.1. Linked heap-hook, stack-guard, and RAM-renderer checks pass. Its UF2
SHA-256 is `377f752bac87eb407172f6a4a3b3caf7e0a24502521f9a964fdcc9830095e6f0`.
The image remains local and has not been copied to wspr5 or flashed.

One explicit serial-bound flash of Pico A is the next authorization boundary:
serial `0BF4B4AEC9FFB344`, current revision `7068b937240a`, current boot
`a12f61f7cd59557c1b5628b2568a52d5`. Deployment permits one BOOTSEL
transition, one flash, zero configuration writes, zero RF jobs, and no retry.
Pico B must remain unchanged.

After deployment, the affected Phase 11.5 behavior must pass before campaign
retests: first, the exact compact FSKCW browser LOAD/ARM/ABORT/RELEASE with no
RF; second, one bounded five-second conducted job with browser status refreshes
under resident RF/TLS state and independent WTP, Console, and USB observers.
Only then are fresh packets justified for the two open FSKCW paths and the open
DFCW controller path. WSPR is not retried.
