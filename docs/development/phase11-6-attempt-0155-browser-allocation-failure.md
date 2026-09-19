# Phase 11.6 attempt 155 browser-allocation failure

## Disposition

The first 2200 m WSPR group under plan v19 is retained as a failed attempt.
Sequences 155 through 157 are consumed and must not be reused.  The production
and disconnected-controller jobs completed, but the browser-owned raw LOAD did
not return an HTTP response and the Pico watchdog entered recovery before an
accepted ARM acknowledgement.  No result from this group qualifies a matrix
row and the three planned job durations remain charged conservatively.

Further Phase 11.6 RF is stopped until a repaired Pico image receives the
required operational authorization and the affected Phase 11.5 browser,
allocation, transport, and contention checks are requalified on that exact
image.  This record does not authorize a reboot, BOOTSEL operation, flash, or
new RF attempt.

## Preserved evidence

- Campaign root: `phase11-6-conducted-v30-20260919`
- Group evidence: `attempts/wspr-0155-2200m`
- Sequences: 155 production, 156 disconnected controller, 157 browser raw
- Group packet SHA-256:
  `f938c7089b9fa7c3e534aace5f9c4b106784f46c7f2d27701876f41fee1f0442`
- Plan canonical SHA-256:
  `a03a6b62eebe75202062c447b95498c3300b9e425796df96989fbe498796986a`
- Plan packet-file SHA-256:
  `7ff5013b23b016c49a0896554e8150b062d6e3393dd394f36b96208cb132b067`
- WsprryPi source:
  `c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf`
- WsprryPi executable SHA-256:
  `b8e63947e2e9780f43dc4247869db138f81cc6e2245c99c1fd02ad9de4b33ff6`
- Pico source: `210599d907acdb23278fc24244b674d62c820d7c`
- Prior normal boot: `e363bf9ae4528258563557b7d306efcd`
- Recovery boot: `1ab2d3ee391ec6c39fcd904f1c9dae01`

The original automatic reconciliation failure is also retained.  It selected
all USB mutation sessions rather than the session that last loaded a job and
reported `Ambiguous USB reconciliation principal`.  The later recovery
reconciliation evidence is in
`attempts/wspr-0155-recovery-reconciliation-v2`.

## Target diagnosis

Fresh physical USB inventory after the watchdog reset reported:

- `recovery_boot=true`;
- fault stage 14 and fault hash 3833354787;
- `fault_allocation_recorded=true`;
- requested allocation 33,335 bytes and a null return;
- authoritative WTP state empty, owner null, output inactive;
- schedules disabled; and
- networking uninitialized with no control listener.

The browser POST body was approximately 16.7 KiB.  `BrowserApi::job` reserved a
destination string but then assigned a chained string-concatenation expression.
That expression could allocate a geometrically grown temporary of 33,335 bytes
while the request body and destination remained live.  This contiguous
temporary failed in the fragmented target heap and triggered the recorded
watchdog recovery.  The evidence therefore identifies a firmware allocation
lifetime defect, not a clock-refinement rejection or a mere observer race.

## Repair boundary

The firmware repair appends each paged HTTP input span directly into one
pre-reserved WTP envelope.  It does not change WTP fields, job contents, RF
events, timing, frequency, DFCW polarity, the RF engine, or output authority.
A host regression constructs a WSPR-sized browser raw LOAD and caps individual
allocations at 20 KiB, proving that the envelope is accepted without the former
double-sized temporary.

The harness repair additionally:

- selects the last actual LOAD or LOAD_MESSAGE principal for reconciliation,
  ignoring later read/cleanup-only USB sessions;
- prefers a retained later browser LOAD envelope when present;
- records a browser mutation marker only after HELLO, CLAIM, LOAD, and ARM all
  return HTTP 200 and the accepted ARM lead remains at least eight seconds; and
- quiesces USB and Console observers only across that browser mutation burst,
  then resumes them for Armed/Running observation.

## Reservation restoration

The original reservation remained held after the failed automatic cleanup.
Fresh inventories proved both named boards empty, unowned, output-inactive and
with schedules disabled.  Reconciliation explicitly bound Pico A's exact
`e363...` to `1ab2...` watchdog transition and the fault fields above; Pico B
remained on boot `6684b4b197d80cfa0ce83b3aaf205cb0`.  The shared reservation
was then durably changed from `HELD` to `RELEASED`.  No reboot, flash, network
configuration write, or RF transmission was used for restoration.

## Requalification impact

Prior waveform and frequency measurements remain historical evidence for their
exact deployed images.  They are not relabeled as evidence for the repaired
candidate.  Before Phase 11.6 resumes, the exact repaired image must repeat the
affected Phase 11.5 checks for browser raw job submission, large/paged HTTP and
WTP payloads, allocation-failure diagnostics, retained heap reserve, browser
and USB/Console contention, authenticated terminal state, and inactive cleanup.
Unchanged RF synthesis and waveform logic do not by themselves justify another
unrelated RF family; any physical repeat remains bounded by a new explicit
deployment/requalification authorization.
