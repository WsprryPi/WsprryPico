# Phase 11.5 Package 7 corrective amendment

The authorized Package 7 executor reached two state-transition harness defects.
Three preflight-only failures consumed no RF budget. The first direct RF job then
transitioned from Armed to Running during the final authenticated configuration
readback; cleanup aborted it before the intended lost-ABORT action. The first
production Armed case likewise transitioned to Running while redundant authority
and storage checks ran; process cleanup reconciled it inactive before any retry.

The Phase 11.5 standing authorization permits additional justified finite packets
when an evidence gap or newly discovered harness issue requires them. The first
corrective tail exposed an observer-schema error: Console reports Running and
active output but does not populate `last_job` while the job is live. The exact
USB WTP observation already bound the current job. The runner rejected the empty
Console field before sending ABORT, then observed normal completion and released
ownership. The next tail attached the receive-drop filter while a previously
decrypted Running event remained queued in the TLS socket. The zero-delivery gate
correctly rejected that stale event before it could accept the missing reply. The
device applied ABORT and was reconciled inactive; no lost-ABORT row is accepted
from that attempt. The first production Armed retry reached the exact host-owned
job, but the browser ABORT arrived before WsprryPi had refreshed its post-ARM
ownership and lease snapshot. The host correctly returned 409 and process
cleanup restored Empty before RF began.

Freeze an additional ceiling of six jobs / 135 planned seconds: three 12-second
Tone retries for the lost-ABORT tail and three 33-second QRSS `ETE` retries for
the production Armed/Running cases. Each retry must address only an observed
harness gap. Use WTP for exact live job identity, Console only for its documented
boot/state/output fields, drain the network event stream before attaching the
receive-drop filter, and require a reconciled WsprryPi ownership, lease and
remote-state snapshot before browser ABORT. The final result must charge every
reserved attempt individually even if it stops before RF output.

The production Running case then reached independently observed live RF, but the
harness incorrectly required a `job_id` field that Console INFO does not expose.
Process cleanup aborted and released the job. Preserve that attempt without row
credit. The original three-job, 78-second charge plus this amendment is nine jobs
and 213 planned RF seconds. This remains within the standing ceiling of 16 jobs and
14,400 seconds. Configuration writes, flashes, BOOTSEL transitions, controlled
reboots, target Wi-Fi cycles and allocation probes remain zero. Keep the same
shared RF-reservation, target, image, boot, fixture, frequency, restoration and
evidence rules. Preserve every failed attempt and accept no failed attempt as a
missing lost-ABORT or production-owner-abort row.
