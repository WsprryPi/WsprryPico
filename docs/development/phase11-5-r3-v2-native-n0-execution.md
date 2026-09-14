# N0: actual native Pi QRSS submission

Accepted R3-COMPLETE-20260913-v2 / four-group Execute, Group 1.3. Browser Running
cancellation passed checkpoint 039. This is the first actual native RF packet.

Run one isolated bba4024 production executable, never the installed Pi process.
One first generated QRSS job contains 32 question marks, 383 actual compiler
events, 135500 Hz and exactly 143.250000 seconds. Charge the full duration before
starting the producer. Repeat period 60 minutes is outside the 600-second unit
work budget; the supervisor has a separate 150-second cleanup reserve. No flash,
CONFIG, Wi-Fi, heap probe, other RF job or B endpoint use is permitted.

Admission requires A source a740dbb / identified UF2 454e03e5, boot
2b4583bd3d79a38f030a08c82ed96939, exact B9 Aborted/inactive/unowned terminal
c5ec4d9753d0466c853494c85dd0aa27, disabled scheduling, fresh synchronized clock,
F2 namespace ownership/deadline, valid controller certificate, exact binary and
unchanged installed PID 1957. Existing WTP CLAIM/LOAD admits terminal state;
there is no separate cleanup claim or fabricated Empty assertion.

The real compiler exports were rerun and matched all three frozen native
templates. The companion branch advance to 7f8b041 changes CI/reference/docs
only; the bba4024 production implementation remains applicable. Independent
USB INFO/STATUS and host health accompany actual native API and raw OpenSSL
plaintext records. The producer binds its session/job while Waiting, with at
least 30 seconds before dispatch. Native host polling does not consume stale
USB samples or block while a new publication is in flight.

Prospective INFO uses single-flight-info-v1. Prospective native launch mapping
uses the raw ARM response clock and its immutable monotonic target, quantized
upward to hardware microseconds. Source job_service.cpp captures that mapping;
StreamEngine checks clock admission before launch, not continuously after it.
Later SNTP updates cannot retrospectively change the original mapping. B7/B8
historical observation/timing scores remain unchanged. Wrong mapping, target,
identity and uncertainty cases are rejected in focused tests.

The native transport-loss helper and auditor are implemented and tested with
framed deterministic evidence; loss is disabled in N0 and reserved for a fresh
DFCW packet. Hardware execution is not itself an acceptance result. Require
independent raw audit, adversarial mutations and durable checkpoint afterward.

Preflight: 87 v2 tests passed with 15 private-evidence skips; real native wire
fixtures cover all modes and the loss path. Packet import rehearsal passed.
The initial archive contained rehearsal bytecode outside its manifest; it was
preserved unexecuted. The reviewed archive contains only declared files and
staged successfully. Native and protected installed binary hashes and controller
certificate lifetime were checked live. Remaining F2 allowance was over 4500
seconds at host monotonic 331324.56, comfortably above this 750-second packet.

- root: /home/pi/phase11-5-r3-v2-native-n0-20260914
- packet_sha256: 2a3d8c11635c48dda176c006b668bc1286114bdb7398791c12be96cbc83ab029
- archive_sha256: ee44cfe3b7a39cd3b5f2a30ff34723d14924e9df0445e0885048cceeef7eabd2
- stager_sha256: f2358e2116bcfc90649cbf7ec92d520ae47ec33861afb3b7a88070fb44e448c4
- observer_sha256: 7d097999d7feebd9099d00ee97e74f2788e76bdabdc8e6f131c303b5e471b72e
- producer_sha256: 3eb1fcf7705a366cf93abc44159ab6eb4af3c2f564c26ed38d3555f049d53de5
- auditor_sha256: eefb9648a7b29e8f392121fbb231b4f5a3100da54e6232f6db99d3c1abd81b46
- planned_jobs: 1
- maximum_duration_ns: 143250000000
- archive_name: public-stage-reviewed.tar
