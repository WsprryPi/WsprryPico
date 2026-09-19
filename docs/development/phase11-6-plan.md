# Phase 11.6 conducted RF acceptance plan

Status: **OPEN — reconciled through immutable attempt 175; RF not authorized by
this reconciliation.**

The authoritative row ledger is
[`phase11-6-matrix.json`](phase11-6-matrix.json), and the exact minimum
remaining RF list is
[`phase11-6-closure-plan.json`](phase11-6-closure-plan.json). The expanded
[`phase11-6-plan.json`](phase11-6-plan.json) remains the immutable v23 execution
plan used by the retained attempt lineages. It is intentionally not rewritten:
changing it would change the digest to which historical packets are bound.

This reconciliation used `origin/devel`
`334b21547a96c3e5584aa4d980893774ac488606` and the retained wspr5 evidence
through attempt 175. It performed no flash, BOOTSEL transition, reboot,
configuration write, GPIO change or RF operation. No threshold was relaxed, no
failed attempt was retried, and no historical evidence was rebound to a later
source, image or boot.

## Authoritative matrix checkpoint

The 75 rows now contain 7 `PASS`, 8 `FAIL`, 19 `BLOCKED`, 31 `NOT TESTED` and
10 `UNSUPPORTED_CONFIGURATION` dispositions.

| Band | TONE | WSPR | QRSS | FSKCW | DFCW |
| --- | --- | --- | --- | --- | --- |
| 2200 m | PASS | FAIL | PASS | BLOCKED — 2 repair replacements | BLOCKED — 1 repair replacement |
| 630 m | PASS | BLOCKED — WSPR timing | BLOCKED — packet audit | BLOCKED — packet audit | BLOCKED — packet audit |
| 160 m | PASS | BLOCKED — WSPR timing | BLOCKED — packet audit | FAIL — coherence | BLOCKED — packet audit |
| 80 m | PASS | BLOCKED — WSPR timing | FAIL — coherence | FAIL — coherence | BLOCKED — packet audit |
| 60 m | PASS | BLOCKED — WSPR timing | FAIL — coherence | FAIL — coherence | FAIL — observer/resource gate |
| 40 m | PASS | FAIL — control path | NOT TESTED | NOT TESTED | NOT TESTED |
| 30 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 20 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 17 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 15 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 12 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 10 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 6 m | NOT TESTED | BLOCKED — WSPR timing | NOT TESTED | NOT TESTED | NOT TESTED |
| 4 m | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| 2 m | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |

`PASS` means the row has an explicit accepted disposition, not merely a runner
PASS label. `FAIL` is immutable and is not a request for a retry. `BLOCKED`
means either a zero-RF packet audit is absent, a source-impact-approved repair
replacement remains, or the frozen WSPR control-path timing proof prohibits a
further RF attempt. `NOT TESTED` means no retained row attempt exists through
sequence 175. At 138 MHz/divider 1, 4 m and 2 m exceed the direct synthesis
range and remain unsupported without ARM or RF.

The campaign DFCW convention remains **dot-high/dash-low**. This is the
retained WsprryPico/browser convention even though the common external DFCW
convention is dot-low/dash-high. No row may silently reverse the retained
campaign mapping.

## Evidence identities and binding

Every attempted-row claim in the machine-readable matrix includes its exact
sequence, source/image/boot lineage, plan digest where available, and retained
attempt, execution, run-result, capture, metadata and analysis hashes where
those artifacts exist. The principal lineages are:

| Lineage | Source | UF2 SHA-256 | Boot |
| --- | --- | --- | --- |
| Phase 11.5 initial | `91933c00970939e366d1bfcf3c1956b59be8f6c5` | `5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446` | `ff719d304f1ba4ac23fddd93561b26f0` or retained post-external-event boot `d2f657c2099c67a7af2ef390426bda10` |
| Clock refinement | `2eaa99945d21501cd4dbdac98c25be5fa146e479` | `af3f6917ba807a1526dca6e15f19fff1974410fc87ecc32fd6e9c4f07059525f` | `b72fed2c17583cc7aba0f1345f76a3b2` |
| Zero-tail | `210599d907acdb23278fc24244b674d62c820d7c` | `b01fecbe3d516dbe5a5e261955e376f062f92a9fe9f7c9b86135bb5f7e8b9811` | `be52153ea21a03f75067129f2bc2245f` or controlled-reboot boot `e363bf9ae4528258563557b7d306efcd` |
| Browser allocation | `7068b937240a7cbdfd0f0edbd7d347057604c0f0` | `f1d437261cb7aa3f9668f7624dad5806346a248202a45f15c553617e12e74a47` | `a12f61f7cd59557c1b5628b2568a52d5` |
| Current status-admission repair | `0e85ff90571c800450073f7b0bfafd70266f1f44` | `9ac5a40fe6d9a44a3a0156621b82801488efecafb9f472ba601dbcbb3e138398` | `cab95d7eecad05047fcb1d6806cf9e86` |

The current candidate passed the documented zero-RF compact FSKCW browser
check and one five-second conducted TONE requalification. That requalification
has no matrix credit. Its source-impact decision permits only three fresh
replacement paths: 2200 m FSKCW browser-compact, 2200 m FSKCW
controller-disconnect and 2200 m DFCW controller-disconnect. It does not
retroactively transfer later identity to older captures, does not justify a
WSPR retry and does not authorize retrying the retained coherence or
observer/resource failures.

The exact sanitized evidence references include:

- [`phase11-6-clock-refinement-attempt44.json`](phase11-6-clock-refinement-attempt44.json)
- [`phase11-6-160m-attempt45-51.json`](phase11-6-160m-attempt45-51.json)
- [`phase11-6-80m-60m-attempt53-67.json`](phase11-6-80m-60m-attempt53-67.json)
- [`phase11-6-attempt-0161-browser-arm-lead-failure.json`](phase11-6-attempt-0161-browser-arm-lead-failure.json)
- [`phase11-6-attempt-0164-tone-offline-recovery.json`](phase11-6-attempt-0164-tone-offline-recovery.json)
- [`phase11-6-2200m-nonwspr-checkpoint.json`](phase11-6-2200m-nonwspr-checkpoint.json)
- [`phase11-6-status-admission-repair-source-impact.json`](phase11-6-status-admission-repair-source-impact.json)
- [`phase11-6-status-admission-repair-requalification.json`](phase11-6-status-admission-repair-requalification.json)

Raw IQ, authenticated transcripts and private attempt roots remain on wspr5.

## Minimum remaining RF

The minimum list has **82 jobs** and an exact maximum of
**3260.000075 RF seconds**. It contains no WSPR job and no retry of an immutable
failed row.

| Scope | Jobs | Maximum RF seconds |
| --- | ---: | ---: |
| 2200 m repair replacements | 3 | 129.000003 |
| 40 m QRSS/FSKCW/DFCW, all three paths | 9 | 387.000009 |
| 30 m non-WSPR matrix | 10 | 392.000009 |
| 20 m non-WSPR matrix | 10 | 392.000009 |
| 17 m non-WSPR matrix | 10 | 392.000009 |
| 15 m non-WSPR matrix | 10 | 392.000009 |
| 12 m non-WSPR matrix | 10 | 392.000009 |
| 10 m non-WSPR matrix | 10 | 392.000009 |
| 6 m non-WSPR matrix | 10 | 392.000009 |
| **Total** | **82** | **3260.000075** |

The exact sequence allocation is 176 through 257 in the closure-plan JSON.
Each job requires a fresh immutable packet. TONE is one five-second
controller-disconnect job. QRSS and FSKCW are 45.000001 seconds for each of
production, browser-compact and controller-disconnect. DFCW is 39.000001
seconds for each of those three paths.

The plan permits zero flashes, zero BOOTSEL transitions, zero controlled
reboots, zero configuration writes, zero GPIO changes and zero automatic
retries. Admission must match the current candidate, companion, receiver and
conducted path exactly. Any identity, reservation, resource, observer,
lifecycle, capture, analysis, cleanup or restoration failure stops RF and is
retained.

## Zero-RF work and closure boundary

Existing passing path sets for 630 m QRSS/FSKCW/DFCW, 160 m QRSS/DFCW and
80 m DFCW still require independent packet audits. Every newly completed row
also requires its independent audit and exact hash reconciliation. Those audits
must not trust runner labels and must preserve the row's recorded lineage.

Executing every remaining RF job successfully does **not** by itself close
Phase 11.6. The retained FAIL rows and configuration-wide WSPR blocks remain.
Under the existing closure rule, a later explicit scope disposition is required
after the RF and zero-RF audits. This reconciliation neither supplies that
scope decision nor marks the phase closed.
