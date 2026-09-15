# Phase 11.5 Package 2 review and execution

**OPEN — no Package 2 assertion closed.**

## Scope

The [execution prompt](phase11-5-package2-prompt.md) targets only 2.2a and 2.2b.
Baseline repository: `14a2ddcfe55287d4635cbc758fbee65c7b3c62ad` on devel.
Firmware remains `8dd6f0812292e9264c2a72745078a95ee606c191`; no firmware
implementation, image, layout or RF renderer changed. Prior P1/R1/R2 evidence
retains its recorded applicability. R3–R6 and full Phase 11.5 remain open.

## Source orientation and reviewed profile

The input parser reserves the declared frame across bounded pages. It admits
input only with temporary processing workspace and the 32,768-byte reserve.
The HTTP parser independently budgets its declared body plus bookkeeping and
returns 503 `resource_exhausted` when that admission cannot fit. The preceding
repair frees execution input after acknowledged RF handoff; neither that repair
nor sequential P1 maxima establishes two-context simultaneous capacity.

Two separate packets establish the revised profile: one 32,768-byte valid WTP
STATUS payload held incomplete while small authenticated HTTP succeeds, and the
same resident input with a separately declared 32,768-byte HTTP body that must
be refused before body submission. Both require continuous real native TLS
observation, successful WTP completion within five seconds, authenticated HTTP
recovery, and unchanged RF/owner/resource gates. The final WTP byte remains
withheld until the complete HTTP response. Raw INFO must independently prove
at least 32,768 extra allocated bytes after warming the second TLS context.

## Findings and repairs

1. **INFO identity mapping.** INFO exposes scheduler state and boot, whereas WTP
   STATUS exposes owner/job identity. The first packet's helper queried absent
   INFO fields and failed before capacity input. Fixed separate checks; tests
   retain foreign WTP-owner rejection and model the actual INFO shape.
2. **Inactive predecessor admission.** A failed packet left a Complete/unowned
   current slot. A second attempt stopped before any mutation because Empty was
   assumed. Freeze the exact inactive predecessor and retained records; permit
   that identity only before this packet's LOAD. Regression checks reject foreign
   owner/job, active output and reuse after LOAD. History is never cleared.
3. **Supported maximum was infeasible.** A third packet warmed the second TLS
   context at 130,072 allocated bytes of 218,936. Maximum input admission cannot
   also preserve workspace and reserve. Only 4,096 host bytes were written;
   no resident allocation or HTTP stimulus followed and the original WTP timeout
   fired. This failed supported packet is retained without overload credit. The
   reviewed amendment freezes a distinct 32 KiB resident profile.
4. **Mid-exchange fault guard.** P2 USB writes now use the supervisor checkpoint
   throughout the exchange, preserving immediate stop of dependent stimuli when
   another observer fails. Independent readers retain their original deadline.
5. **Private staging.** Automatic approval review rejected duplicating private
   credential/configuration inputs into new packet roots. The repaired staging
   copies public helpers only and verifies references to original private files
   in place on wspr5. No credentials or authenticated payloads are published.

## Blocking target finding

The revised supported packet `d5d9b1a…` never reached ARM or capacity input.
Its 52,105-byte LOAD began at 85,624 sampled allocated bytes and was unanswered
at the original five-second deadline. INFO then timed out and USB reached EOF.
Independent final inventory found watchdog recovery boot
`4768a88991247131bdc7c0fc421dbe8f`, stage 5 (USB service), allocation hash
3833354787, a recorded 20,480-byte request and a null allocation result. This
matches the size of 512 `RfEvent` objects allocated by the codec at
`src/wtp/codec.cpp:188`; exact fragmentation versus transient occupancy is
unproven. Aggregate free-byte samples cannot establish a contiguous block.

**P2-LOAD-20480 remains blocking.** Reproduce that allocation with matching
retained state and native traffic, repair allocation/admission without reducing
reserve or hiding a timeout, and validate affected LOAD, replay and retention
behavior before a reviewed image and fresh physical packets. Another reboot
and identical retry is not a repair. This bounded attempt ends OPEN; the separate
overload packet was neither staged nor executed. The proposed 32 KiB profile
has no physical acceptance. No firmware change was made in this attempt.

## Evidence and adversarial closeout

The [immutable result](phase11-5-package2-result.json) binds all four frozen
attempts and their failures to raw hashes. Initial inventory staging failed
before device access due to a missing public schema; repaired staging passed.
Ninety seconds of addressless Wi-Fi readiness failure justified one separately
frozen OFF/ON cycle, independently audited successful before RF work.

| Attempt | Actual work | Outcome |
| --- | --- | --- |
| supported / 4c37acc5 | One 128-second job; no capacity input | INFO helper field failure; final Complete/inactive verified |
| supported2 / ce1fd541 | No device mutation or RF | Inactive predecessor admission stopped preflight |
| supported3 / 1dd195dc | One 128-second job; 4,096 maximum-WTP host bytes | Original WTP timeout; no HTTP; final Complete/inactive verified |
| supported4 / d5d9b1a | LOAD only; zero RF/capacity | Recorded allocation failure and watchdog recovery |

The affected helper suite passes 233 cases, with 48 expected private-capture
skips. Five focused combined tests cover profile scope, actual frame bytes,
INFO/WTP separation, predecessor lifetime, residence and fourteen altered
overlap cases. Four altered raw failure records (inventory, LOAD bytes, ARM
count and reservation state) were rejected; intact failure evidence passed
again. The durable `audit_phase11_5_package2_failure.py` adds explicit source and
LOAD-byte checks and independently reproduces the same intact result.

Adversarial review additionally tightened the native predecessor exemption to
before LOAD, and required the exact assertion ID for each declared profile.
No actionable helper finding remains in the reviewed slice. The target
allocation finding above remains unresolved; successful synthetic overlap
checks and failure reconciliation are not successful target qualification.
No physical P2 positive audit or positive-packet mutation assessment is claimed.

The host fixture was restored before its original deadline and independently
matched the host baseline, including installed WsprryPi PID 1957. Both boards
are fresh-inventoried Empty, inactive, unowned and schedule-disabled; the shared
reservation is released. B's source/boot/configuration are unchanged. A remains
on 8dd6f08 in network-free recovery; persisted configuration fields survived,
its runtime station MAC is uninitialized, and volatile terminal history was
lost in the reboot. Recovery inactivity is not restoration to the original boot.

Actual turn charges: two RF jobs / 256 planned seconds, one Wi-Fi OFF/ON,
one unplanned watchdog, zero flashes/BOOTSEL/configuration writes/controlled
reboots. Cumulative completion charges: nine RF jobs / 1,152 planned seconds,
nine flashes/BOOTSEL, four Wi-Fi cycles and two unplanned watchdogs. R1/R2 and
P1 retain their recorded scope; R3–R6 and full Phase 11.5 remain OPEN.
