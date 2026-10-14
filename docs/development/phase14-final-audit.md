# Phase 14 final assertion and adversarial audit

## October 14: Phase 14 completed within the declared scope

**9 of 9 original workstreams are closed (100%).** The operator explicitly
requested the 56 reviewed Phase14 files committed on devel, pushed to
origin/devel, independently checked for parity and closed out. Code/evidence
commit **74c73d548e2e05cf6f61978817d7de264da961ff** contains exactly those 56
files. Its push succeeded and a separate `git ls-remote` read matched that SHA.
This final documentation update changes no runtime or installed image bytes.
The final documentation commit and its independent parity proof are retained
in the private closeout receipt and reported in the chat; no self-referential
commit hash is fabricated here.

All 1,039 runtime/build/test blobs in the source commit match the frozen,
independently rebuilt and installed C96 candidate. The compiled identity remains
`dda8a6eb1e69-dirty`; it is preserved as build provenance rather than relabelled
with the later commit. Runtime SHA-256:
`c96eeeeb4871bdcec40aa5b8fbc1dce42507b5fac6b00ee3a8b41838d5836d64`.
Selected release artifact: consumer-radio-c96eeeeb4871, PIO/DMA GP2, 138 MHz,
divider1/RAM renderer. UF2 SHA-256:
`17065bc7945a91d210bf3e48aedf1c6f5772f4386e7b26c04f364553afc6adad`.
ELF SHA-256:
`0fa99101a76735ac1a319e951fd14774ee6f4ce1ba44015ffde38f8d023449f9`.
Independent 138 MHz ELF and UF2 builds are byte-identical.
The private UF2 is retained under local
`build/phase14-consumer-radio-arm-plain-admission-20261014/build-138/firmware/WsprryPico-StandaloneRF.uf2`;
its closeout manifest is local
`build/phase14-final-consumer-c96-closeout-manifest-20261014.json`.
No generated firmware, raw capture, credential or private profile is in Git.
No GitHub release or additional public artifact publication was performed.

The accepted matrix covers Tone, WSPR, QRSS, FSKCW and DFCW on both boards:
2200m,630m,160m,80m,60m,40m,30m,20m,17m,15m,12m,10m and6m, with historical
132/138/150 MHz comparisons and the selected138 candidate. All390 cells and602
accepted observations are bound to actual source/firmware/boot/job/capture
identities. Original nominal failures, receiver-only acceptance and keyed
human-copy amendments remain separate. 4m/2m are excluded for all modes;
8m/5m were outside the agreed matrix and remain untested.

The timing, spectra, reference, lifecycle, native/standalone, eight-hour mixed
and separate two-hour memory gates retain their actual reviewed scopes and
measurement uncertainties. Their full/closed source/control/raw/resource proofs
and both original retention scopes are accepted. Final source/coverage/
adversarial proof **912ea1c254067a193d0489707660510c9682a3ef082e5f6ccf019f3d388a9735**
retains every failed original. Consumer radio access, settings/persistence/
original restoration and all four smoke screens are independently accepted on
both boards, with narrow R189/C96 applicability preserved.

Final separately admitted readback verified both Picos C96/138, empty, unowned,
output-inactive, schedules disabled, synchronized clocks, ready consumer AP and
Plain LAN listeners, original settings and unchanged current cursors:
A **1791199541540946076**, B **1791705481000000000**.
Recorded boots remain A `4ac25bc51decbde2e1eb3f6cce6f75fa`,
B `67e58db2fc1a86d2f3f4add83e3cf146`. Subsequent Git-only closeout performs no
Device, flash, profile, config, cursor, RF or GPSDO mutation. Fresh process/
receipt checks show no active owned programme. Reference state is restored,
wsprrypi.service is active and wlan2 disconnected; management is preserved.
All four locks and exact source/durable presence histories remain bound.
Exactly164 CLOCK and three MIXED source absences remain separate, with all
retained copies, nonraw controls and failed evidence preserved.

The unfiltered conducted scope establishes no LPF, calibrated watts or antenna-
ready emissions. Absolute RF/timing calibration, consumer-image long endurance,
general leak freedom, hostile HTTP-page delivery and authenticated Plain LAN
remain unqualified. These are explicit retained limits, not new completion
claims. P13.1 stays complete; P13.2 Si5351 and GP14 default enablement stay deferred.
The unrelated implementation-plan bytes and Si5351 work are preserved.
Hourly reports remain ACTIVE until the final documentation push, independent
remote parity and closeout receipt are verified, then are stopped because this
Phase14 task is complete.

Earlier dated sections below are immutable historical boundaries; their old
pending/count/estimate/repository descriptions are superseded by this closeout.

This is the current audit record, not a release-completion claim. The original
nine workstreams remain the accounting units. The final accepted baseline is 8 of 9
closed within the recorded scope (88.9%). Only Git commit/push/parity and the
closeout report remain; allow 15–60 minutes after an explicit Git request. Core mixed and memory science and core
retention and the original finite retention are independently closed.
Consolidated final source, coverage and adversarial gates are accepted by
closed proof912ea1c2... and original-workstream reconciliation3732a330...; see
the [current ledger](phase14-closeout-ledger.md). Phase14 release closeout remains open.

## Final source and installed identity

Both Picos retain the independently rebuilt consumer-radio-c96eeeeb4871
138 MHz candidate, honest source identity dda8a6eb1e69-dirty, runtime
c96eeeeb4871bdcec40aa5b8fbc1dce42507b5fac6b00ee3a8b41838d5836d64.
UF2 SHA-256 is
17065bc7945a91d210bf3e48aedf1c6f5772f4386e7b26c04f364553afc6adad.
Independent ELF and UF2 bytes match. Installation independently compares mapped
application bytes and the complete protected tail, including CURRENT cursors.
The local final source audit verifies 1,039 runtime/build/test files against the
frozen installed snapshot; 51 RF/WTP/encoding/time files match DDA HEAD bytes.
Documentation updates after the snapshot do not change installed runtime.

The original current cursor watermarks remain A 1791199541540946076 and
B 1791705481000000000. B's original consumer restoration affected only the
required 24 KiB. Settings testing restored only the original 8 KiB configuration
journal per board. No archived historical cursor was written back.
Recorded current boots remain A 4ac25bc51decbde2e1eb3f6cce6f75fa and
B 67e58db2fc1a86d2f3f4add83e3cf146; future hardware actions must refresh them.
A current INFO equality is not a new full application-flash proof.

## Assertions and limits retained in the final assessment

| Assertion | Actual evidence and applicability | Final audit disposition |
| --- | --- | --- |
| Supported retained band/mode/clock matrix | Clock reconciliation 612ba1f6... and full audit e20c96c8..., actual external WSPR stdout, reviewed keyed human-copy screens, post-clock Tone 13efa688... | Accepted390 cells,602 observations; retain old source/image identities and narrow applicability. |
| 4 m and 2 m release support | Operator disposition ab6be5a5... and independent scope 0256bc69... exclude all five modes at all candidate clocks | Accepted exclusion. Preserve successful synthesis and failed decoding; no further RF/decoder work. |
| Timing/spectra/reference/compensation | Full spectra/compensation acceptance f04a8701..., original Tone gates and receiver/reference bindings | Original method/uncertainty assertions and final-source applicability verified. No calibrated transmitter power, new frequency/drift limit or LPF claim. |
| Finite native/standalone/lifecycle workloads | Native19 1d0c21f7..., standalone 3e877d52..., lifecycle 2305f220... including prior clock-loss full proof | Retain actual source/settings/boot/job identities and exact original failures. |
| Eight-hour mixed and separate two-hour memory | Full 014b4438... / closed77c6b727..., full3c5c5539... / closeda42de550... | Original science accepted separately. Neither receipt is relabelled as consumer-image endurance or general leak freedom. |
| Both consumer authentication/settings/persistence/restoration | Current C96 both page/read/control checks; R189 86-response settings/native restoration b259382e... with API/crypto/profile/store/cursor/main bytes unchanged in C96 | Bounded both-board consumer acceptance. Default/single/both opt-ins, revisions and immutable setup identity are exercised. |
| Final four consumer smoke screens | Full 824 MB proof f7915a80...: three actual R189 screens, one actual C96 B WSPR, normalized two-predicate Plain delta and otherwise identical target source | Narrowly accepted without RF, analysis or decoder replay. Both actual expected WSPR stdout records pass. |
| Core raw/source/result retention | Full1110d059... / closed4e4c2e9c..., 6,086 pairs / 15,829,335,463 bytes; all exact processes gone | Accepted. Original memory core14.58 GB credited once. References/smokes inside original other allowance. |
| Remaining original finite retention | Exactly237 existing raws /19.288 GB plus recursive nonraw/source/control companions, new state-bound scope and copy admission | Independently full/closed accepted at c081df4f... /6c818feb...; all exact processes gone. No new scientific acceptance or elapsed credit. |
| Release identity and Git | Exact dirty snapshot is identified and independently reproducible; current devel is ahead74 with source/docs/tests uncommitted | Final commit/push/parity awaits explicit human Git request. No publication or Git mutation authorized. |

## Attempts to disprove completion and actionable findings

- The whole current target receipt 5c1db64b... is failed, not a two-board PASS.
  Its A-only proof4c3d1a4b... and distinct B proof8a0d060f... supply their actual
  accepted scopes. B's existing TLS connection was preserved; B did not receive
  A's owned unfinished-handshake experiment. The copied admission descriptor
  does not broaden the actual B source/traffic evidence.
- Three smoke records are R189, not C96. The cross-source review checks every
  other target runtime byte and normalizes only two Plain activation predicates
  and their comment. Original source/UF2/boot labels stay unchanged.
- Consumer source5 intentionally disables USB WTP. README, CONTRACT,
  architecture and Consumer-Radio/1 now distinguish consumer Console inspection
  from Plain LAN/AP-local control and engineering USB WTP. The stale protocol
  statement and pending-smoke wording were corrected.
- The final source audit found missing project notices for the bundled Noble
  browser cryptography packages. Exact retained 2.3.0 package licenses were
  copied byte-for-byte and their provenance/distribution record added to
  THIRD_PARTY_NOTICES.md. Runtime/library/bundle bytes are unchanged.
- HTTP delivery of the radio page on the open setup AP can be substituted by
  an active attacker and expose entered credentials. Genuine-page traffic uses
  the saved passphrase, fresh X25519/HKDF/AEAD bindings and bounded sessions.
  This is not PAKE or authenticated page delivery; no production-security or
  hostile-AP-resistance claim is made.
- Plain LAN admits any reachable LAN client. It preserves the one JobService
  owner, complete-frame validation and local RF timing; encrypted AP management
  does not make the Plain LAN transport authenticated.
- Both heap readings derive from newlib allocation accounting at distinct INFO
  points, not independent allocation measurements. Original45s/expiry/growth
  AND spread thresholds and failed screens remain unchanged. Accepted bounded
  growth is not general leak freedom.
- Archive/source-retained flags before recorded unlinks remain historical.
  Exactly164 CLOCK and three MIXED source absences are separately checked.
  No whole-source closure that assumes all originals still exist is replayed.
- Qualification on an unfiltered conducted GPIO/combiner path does not establish
  LPF, calibrated watts or antenna-ready emissions. Relative fundamental power
  includes receiver/path response; the 6 m increase is not isolated transmitter
  output. Output filtering remains the operator’s responsibility.

Current corrected source checks and meaningful rejection/old-gate controls have
independent actual receipts. No further source defect was established in this
local review. The consolidated assertion/evidence applicability review is accepted by the
new closed proof. Both original retention scopes
have separate full-review and closed-acceptance proofs.
Any further actionable finding requires a distinct source/state-bound affected
check, preserving the original failure and every scientific/security limit.

## Repository and remaining gates

The working tree is on devel at dda8a6eb1e69539b7399cdd899d8830a2d199769,
ahead74, with an empty index. Owned C++/Python/CMake/browser/tests/doc changes
remain uncommitted. Unrelated implementation-plan SHA
20dc830b58eb1c08001162b4359e5ddba8e13fee85be6ec57e1bf7ca94a63ca7,
untracked Si5351 work and all six worktrees are preserved.
No initialization, staging, commit, push, publication, SDK/tool install or native
Mac C++ compilation was performed. The hourly automation stays ACTIVE at its
existing schedule and notification policy, with healthy hourly NOTIFY required.

Both original retention scopes are now full/closed accepted. The consolidated assertion/adversarial gates and fresh final host/state
boundary are accepted. The concrete result is reviewable; Git mutations still
require the explicit request specified in AGENTS.md. Final release completion requires authorized Git closeout
and independently verified remote parity.
