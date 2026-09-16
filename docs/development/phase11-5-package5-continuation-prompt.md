# Phase 11.5 Package 5 bounded continuation prompt

Execute only the unfinished Phase 11.5 Package 5 gates in
`/Users/lbussy/GitHub/WsprryPico`. This prompt requires a new explicit hardware
allowance because the original Package 5 execution consumed its RF budget and
left one aborted terminal record. Preserve every existing pass and failure. Do
not claim Package 6, R3 family closure or Phase 11.5 closure.

## Fixed starting evidence

- Retain `R3.RETAINED.replay` and `R3.RETAINED.session` from packet
  `2039a76c119c23ebd7cdf36e8052252e58b9fc4b5a7d3283b51018690c829ccc`
  plus final-status packet
  `df03ad86f412a0c6586c2a25075408b88d5439dc794ca119301a5e5ea6dd9e5b`.
- Retain terminal capacity/LRU from packet
  `ed7db2e3a386b47855b3bb5a06c19c3d65b3c8af1b0eee92a74cb769f5130149`.
- Retain the three complete maximum-workload RF/overload captures
  `7878985...`, `fc55afc...` and `a536693...` as functional evidence only.
  They do not receive reclamation credit because their immediate post states
  differ by 12,384 bytes.
- Retain failed late-response packet `0e959b6...`, including its 7.666-second
  LOAD response and aborted terminal record. Do not convert it into a pass.
- Pico A must still identify source `2b25ca05c270819466a04498f9bc4894a4c5bace`,
  image `16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`
  and boot `80d558e5804547749eca849c53ba27e1`. Pico B must remain the unchanged
  inactive comparator. Stop if any identity differs.

## Additional finite allowance requested

Authorize at most eleven RF jobs and 392 RF seconds:

- eight one-second, 512-event cache-normalization jobs;
- three 128-second measured reclamation jobs.

Authorize zero flashes, controlled reboots, configuration writes or Pico Wi-Fi
cycles. One new isolated host fixture and its exact restoration are allowed.
Every failed attempt consumes its actual RF charge; do not replace a failed RF
job without a separate authorization.

## Repair the comparison design before RF

The original comparison held terminal cardinality at eight but allowed unlike
retained content: small Tone histories were progressively replaced by
maximum-event histories, while short-lived sessions and replay responses were
still present. That does not establish equivalent cache phase.

1. Add a deterministic normalizer that creates eight distinct complete
   one-second jobs. Each job must contain exactly 512 events and use the same
   alternating 135.500/135.495 MHz frequency sequence as the measured
   workload, so retained adjustment content is equal to the later cycles.
2. Each normalizer must traverse CLAIM, full LOAD, ARM, Running, Complete and
   RELEASE under the two-Pico reservation. The unchanged five-second LOAD
   response deadline applies. Stop on any timeout, abort, missed job or
   allocator/TLS failure.
3. Confirm that normalization leaves exactly eight complete terminal records
   and has evicted the known aborted record.
4. Perform a real 360-second WTP/HTTPS application-quiet interval. Allow only
   Console INFO and required host health. Freeze a raw Console baseline after
   replay and session entries have expired.

## R3.RECLAIM

Run three new hash-bound Package 2 bounded-overload packets. Each must use the
same 512-event, 128-second FSKCW plan, 32,784 resident direct-WTP bytes,
authenticated bounded HTTP `503 resource_exhausted`, five-second WTP exchange
deadline, 15-second authenticated recovery deadline, observer policy, TLS
identities and terminal cardinality.

After each RELEASE, perform a 360-second application-quiet interval and record
the post state from raw Console INFO before starting the next packet. The post
state must have exactly eight complete, maximum-event terminal histories and no
session/replay entries from the completed packet. Compare live allocated bytes,
allocator/TLS failure counters, stack guards and retained cardinalities. Require
all of the following without adjustment:

- each job completes with continuous native and Console authority;
- WTP residence is at least 32,768 bytes and HTTP refusal/recovery is exact;
- final authority is Empty, inactive and unowned;
- at least 32 KiB reserve remains;
- the three equivalent post values do not grow monotonically;
- maximum equivalent-post difference is at most 1,024 bytes.

## R3.RETAINED.terminal expiry

After the third measured RELEASE and its accepted post snapshot, freeze the
exact eight complete terminal records. Start a 3,660-second application-quiet
interval. At its end, issue one fresh authenticated HTTPS HELLO and one status
read. Require an empty terminal list, cleared old job identity and
Empty/inactive/unowned authority on the unchanged boot. Bind every record's
device-monotonic age to the 3,600-second source TTL.

## Review and completion

Run the full deterministic suite and independent raw-evidence auditors. The
adversarial assessment must reject altered identity, normalizer event count or
duration, LOAD deadline, quiet duration/traffic, terminal type/order,
resident-WTP amount, HTTP outcome, recovery, memory comparison, expiry,
authority, reservation and restoration evidence. Fix actionable findings and
repeat the assessment.

Only if both remaining rows pass, mark `R3.RETAINED.terminal` and `R3.RECLAIM`
accepted, mark Package 5 complete, keep Package 6 and R3/Phase 11.5 open, commit
to `devel`, push `origin/devel`, and verify local/upstream/remote parity.
