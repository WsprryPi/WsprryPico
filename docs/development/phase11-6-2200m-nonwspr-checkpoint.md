# Phase 11.6 2200 m non-WSPR checkpoint

This checkpoint is partial. The 2200 m TONE row and all three QRSS submission
paths are accepted. FSKCW has accepted production-path evidence only. DFCW has
accepted production and compact-browser evidence only. WSPR remains failed and
is not included in this acceptance checkpoint.

The retained DFCW campaign convention is dot-high/dash-low. Nothing in the
repair changes that polarity, the frequency mapping, the RF renderer, symbol
timing, WTP authority, or the 32 KiB RF reserve.

Attempts 171 and 175 exposed two related admission defects. A compact six-event
FSKCW message was budgeted as if it needed the maximum 512-event allocation,
and the generic HTTP gate required a 16 KiB scratch allowance for small status
JSON while an RF job and TLS state were resident. Attempt 172 separately failed
before RF because the operator supplied the wrong capture-helper path. These
failures are retained; there are no automatic retries.

The source repair first measures the encoded event count and allocates only the
required event pages. It also uses an 8 KiB scratch allowance for the two JSON
status endpoints while retaining the 32 KiB RF reserve. Host regressions cover
the exact compact FSKCW allocation boundary and the reduced status threshold.
The complete host suite passed on macOS, and the focused build plus all Phase
11.6 Python tests passed from the copied source bundle on wspr5.

The repaired source has not been flashed. Before any affected campaign row can
be retried, a firmware image must be bound to the repaired source revision, the
concrete flash must receive separate authorization, and the affected Phase 11.5
compact-load/status behavior must be requalified. Each justified retest then
requires a new immutable attempt packet. The exact candidate identity and
requalification scope are in
`phase11-6-status-admission-repair-source-impact.json`.

The machine-readable companion records the accepted and retained attempts,
private-evidence hashes, RF accounting, repair impact, and limitations. The
checkpoint covers eight charged RF jobs totaling 302.000007 planned seconds.
Raw captures and transcripts remain private.
