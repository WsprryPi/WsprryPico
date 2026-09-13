# Diagnose an interrupted qualification run before repeating it

A red run status does not identify a firmware defect. Record three independent
answers: what the device actually did, which test assertions have adequate
evidence, and what caused the interruption. Keep completed work visible even
when the overall acceptance case remains incomplete.

The read-only `scripts/diagnose_phase11_5.py` reconstructs registered attempts
through their raw auditors before assigning fault. Its current
[diagnosis register](phase11-5-r3-diagnosis.json) gives these results:

| Attempt | Device/test outcome | Supported attribution |
| --- | --- | --- |
| A1 | No RF or pressure injection; complete read-only observation and restoration | Assistant harness defect: Console INFO was treated as WTP STATUS. |
| A1b | One 100-second Tone completed; pressure unverified and observation incomplete | Confirmed assistant parser/observer defects. The failing HTTP bytes are missing, so the exact response and any concurrent target problem remain unknown. |
| A1c | No new RF; prior job reconciled; network prerequisite not established; cleanup passed | Authentication failure observed, underlying cause unresolved. Neither firmware nor assistant code is proved responsible for the rejoin failure. |
| A1d | Staged, never launched | Automatic approval review blocked the added Wi-Fi cycle. The user did not decline it. |
| A1e | One approved Wi-Fi cycle restored readiness; one Tone and full observation completed, second job unsubmitted | Confirmed assistant freshness bug: an INFO read was validly in flight. Load interruption and missing second job followed that stop. |
| A1f | Two Tones and all traffic completed; frozen audit failed | Three confirmed audit integration errors plus a separate completion-bracket miss. The read met its five-second deadline; a firmware timing violation is not established. |

| A1g | No RF; 25 readiness failures despite AP handshake completion; normal terminal expiry verified | Device join state disagrees with AP. Underlying firmware/driver/radio cause remains unlocalized. |
| A1h | No recovery command or RF; live AP authenticated/associated the DUT; recovery admission sampled JOINING | Confirmed harness defect: transient progress was rejected without a bounded wait. |

There is no confirmed firmware defect in these eight records. That statement does
not assert that the candidate is defect-free or that R3 passed.

## Read-only diagnostic command

From the Pico repository:

```sh
python3 scripts/diagnose_phase11_5.py \
  --evidence build/phase11-5-r3-retained-a1c/evidence
```

Use `--output` with a new path to retain a diagnosis without overwriting an older
one. The command opens no device, socket, fixture or credential file and never
retries hardware. A1/A1b/A1c/A1e/A1f/A1g/A1h raw auditors are its evidence adapters. An unregistered packet remains unclassified; its exception
message cannot assign blame. If raw audit fails, safety and attribution return to
unknown: an audit mismatch can be damaged evidence **or a different real outcome**,
so the tool does not automatically blame collection code either.

The result separates execution, acceptance, fault domain, confirmed firmware/
assistant defects, completed RF jobs, authoritative output, uncertainties and
next diagnostic actions. A1c additionally gets a chronological link/clock
transition summary and the exact prerequisite that did not converge. Its
25-check readiness limit is explicitly a **harness attempt limit**, not a
firmware deadline violation. No deadline is extended or acceptance threshold
changed by this diagnosis.

## Before another hardware attempt

Use actual producer output or recorded wire bytes to test consumers. The R3
parser tests already bind Console/WTP shapes to recorded inventories and HTTP
framing to source-generated serializer bytes. Synthetic fixtures copied from an
incorrect consumer are inadequate; that was the A1/A1b review failure.

Preserve raw responses before parsing, and keep independent finite-job observation
running after a pressure client fails where possible. Known completed owner expiry
is a normal terminal condition; it must not be relabeled as RF failure. The
retained lifecycle clears only an independently verified known completed job and
keeps the user's test configuration. A cleanup mismatch is reported separately
from a completed transmission or pressure result.

A timeout needs its phase, last observed state/progress, intended limit and
precondition evidence. For the current rejoin issue, establish the AP's active
password match while the fixture still exists, retaining only a boolean. A1c's
comparison was attempted after host cleanup, so it cannot settle that question.
Then collect link/AP authentication evidence. One approved OFF/ON cycle can show
whether recovery works; success alone does not prove why authentication failed.
Do not patch firmware, flash, or repeat RF just because a generic timeout expired.

Keep fixture lifetime and acceptance deadlines distinct. The reviewed continuation
reserves a full 375-second observation allowance before starting RF. It also marks
the overall attempt failed when required cleanup fails while preserving any
separately completed work. Permission is a fourth, administrative state: an
automatic-review rejection is neither a target failure nor a user refusal. Ask
for the concrete action explicitly instead of implying the user has withheld it.

## Validation and limits

Tests reconstruct five private attempts, preserve A1b's completed job, and
verify that arbitrary failure wording cannot blame firmware or the assistant.
They distinguish disabled Wi-Fi, missing address, authentication failure,
unsynchronized clock and a ready endpoint; reject reversed time; distinguish
automatic review from user refusal; and invalidate safety/attribution when raw
evidence is altered. Existing raw mutation audits remain mandatory for acceptance.

This is an evidence-based triage mechanism, not an automatic universal root-cause
oracle. New mechanisms need a corresponding raw adapter or remain unknown. The
remaining R3 physical cases and original rejoin cause are still open.

## One primary failure, multiple consequences

A1e's raw timeline identifies the pressure stop before load termination and the
observer's eventual unsubmitted-job report. Its INFO read took 1.739071744 seconds
and maintained the two-second request cadence. Those later messages must not be
counted as additional firmware failures. Reconstruct the causal order and label
primary defects, consequences and independently failed gates separately.

A1f demonstrates a different case: all workers completed, while three auditor
integration assumptions were wrong. Once repaired, the original two-second
INFO completion bracket still missed once. That remaining miss is preserved.
A separately labeled diagnostic checks the proposed request-cadence/read-deadline
criterion, but cannot grant old evidence acceptance. See the [prospective packet](phase11-5-r3-retained-a1g-execution.md).
Before another run, replay the complete observer, actual native production TLS
wire and pressure trace through the integrated audit, not just isolated helper
tests. Do not spend another RF run merely to discover an offline adapter error.

## Rejoin and retention evidence

The [network diagnosis](phase11-5-r3-network-diagnosis.md) records the AP/DUT
chronology and its limits. Distinguish AP authentication, target IP readiness and
clock synchronization. A positive AP handshake does not prove IP readiness; a
DUT BADAUTH label alone does not prove a wrong password. Capture DHCP/ARP before
AP activation and save live AP state before cleanup. A JOINING/NOIP sample is a
progress state: wait within a declared read-only bound, then apply the original
recovery gates. Never cycle on an unknown state or retry an uncertain ACK.

Retained terminal expiry uses the target clock and CAPS lifetime. A record that
has reached its advertised age is not a failed transmission or a reboot. Preserve
exact unexpired records and refuse certainty when expiry falls inside the
observation bracket. Earlier evidence files retain their original end timestamps.
