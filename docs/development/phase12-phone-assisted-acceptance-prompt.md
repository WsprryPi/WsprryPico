# Phase 12 phone-assisted RF-inhibited acceptance execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Starting state and purpose

Begin from clean `devel` at
`c65a0ddbea6c74165fe9a30bc8adbacf00fc5fb1`, equal to `origin/devel` at the
start of this continuation on 2026-09-23. Inspect the branch, status, HEAD,
upstream and remote-tracking reference before editing or operating hardware.
Preserve later work; do not reset, stash, discard changes, rewrite history or
switch to another checkout.

This continuation addresses only the remaining Phase 12 assertions that need
the operator's actual iPhone, private station inputs or direct physical
observation. It follows the complete
[Phase 12 physical plan](phase12-physical-acceptance.md), the
[field-access/security contract](phase12-field-access-contract.md), the latest
[production review](phase12-production-acceptance-review.md) and the bounded
[SoftAP physical review](phase12-softap-physical-review.md). Phase 12 is active,
not closed. The prior native-Pi BLE and SoftAP evidence is useful admission
evidence but is not iPhone, Safari, Bluefy, offline-cache, credential-transfer,
LED or reset acceptance.

Do not add a pre-freeze drift sentinel. Source may change only to repair an
actionable finding. Freeze each physical candidate as a clean commit before
building it, record the exact source and UF2 hash, and repeat affected rows if a
repair changes firmware or the checked-in Bluefy release.

## Authority and hard boundaries

This prompt authorizes repository review and changes needed for the admitted
phone-assisted rows; deterministic hardware-free tests and retained pinned
cross-builds; a clean serial-targeted flash of Candidate A; BLE, Wi-Fi and
SoftAP operation; bounded controller-time and LED checks; one deliberate
credential transfer and delivery-safe network-only activation; private
temporary controller configuration; bounded reboots; and final RF-inhibited
restoration. It authorizes adversarial review, repairs, evidence documentation,
commit and push to `origin/devel`.

It does **not** authorize RF output, `LOAD`, `ARM`, Stage B, dependency
downloads, App Store installation or purchase, arbitrary endpoint scans,
permanent phone or host trust-store mutation, disclosure of credentials or
private keys, destructive reset gestures that are not implemented and selected,
or replacement of missing phone evidence with a Raspberry Pi or mock. The
standard image must report the inhibited engine, authoritative inactive output
and empty/unowned state before and after every admitted operation. Stop on
wrong identity/image, output unknown/active, unexpected RF, unhealthy storage,
trust resurrection, unrecoverable network state, resource fault or exhausted
finite budget.

Private Wi-Fi passwords, certificate private keys, session cookies, raw access
sectors, authenticated packet captures and the complete credential bundle stay
outside Git, chat, screenshots and credential-free evidence. The operator
enters secrets directly into the accepted phone page or a private local input;
do not echo, log or paste them into a command line retained by shell history.

## Exact known equipment boundary

- Candidate A Pico 2 W USB serial: `0BF4B4AEC9FFB344`.
- Candidate device ID: `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Station MAC: `88:a2:9e:0a:60:df`.
- BLE address last observed: `88:A2:9E:0A:60:E0`.
- SoftAP SSID: `WsprryPico-0a60df`.
- Certified hostname: `wsprrypico-0a60df.local`.
- Comparator USB serial `CDDBF8767C506C07` is observation-only and must not be
  flashed, reset, paired, provisioned or otherwise mutated.
- `wspr5` retains management on Ethernet and its existing infrastructure Wi-Fi.
  Only the otherwise unused isolated interface may receive a temporary SoftAP
  profile, which must be deleted before restoration.

The previous operated image was clean source `0ecf9c170384`, UF2 SHA-256
`6261e322884a280afcd997537d6248fbbf0033b879fab1b2a661acd3a3575e23`.
Do not silently reuse that identity for a newly built HEAD. Build and record the
exact clean current candidate before the phone session.

## Read and inspect before mutation

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `SECURITY.md`,
`docs/architecture.md`, `docs/implementation-plan.md`,
`docs/development/README.md`, the Phase 12 plan/contract/physical plan and all
P12.3-P12.6 reviews. Review the current access/profile/reset journals,
`LocalAccessController`, BLE command/GATT path, Bluefy release and service
worker, controller-time arbiter, indicator, SoftAP coordinator/admission/API,
delivery-safe activator, runtime profile overlay, CYW43 ownership, one
`JobService`, scheduler and output authority.

Before using the phone, determine which requested rows are actually backed by
production source. In particular, do not ask the operator to improvise a reset:
SoftAP access administration and the exact three physical reset gestures remain
source/product gaps unless this continuation explicitly implements and reviews
them. Record those rows as `NOT_EXECUTED_SOURCE_GAP`, not as phone failures.

## Admission and operator inputs

Create a private credential-free evidence directory outside Git. Record exact
source, pinned SDK/BTstack/picotool/Arm toolchain revisions, configure options,
UF2 path/hash, serial/device/MAC/boot identities, profile/access/config/
watermark generations, output and job authority, private-evidence location and
the restoration plan.

Obtain these facts from the operator before the first phone-dependent row:

1. Exact iPhone model and hardware identifier if available.
2. Exact iOS release and build.
3. Exact Bluefy App Store application identity and installed version.
4. Whether Candidate A appears in iOS Bluetooth settings and whether the
   relationship is believed to be new, provisional or retained. Do not infer a
   fresh password check from a retained bond.
5. Confirmation that the checked-in Bluefy page is already available in
   Bluefy. Do not install or update an application under this prompt.
6. Availability of the intended private station SSID, password, time server,
   exact TLS hostname/port, device server certificate/private key and client CA.
   Secrets are entered locally, never reported.
7. The operator's ability to observe the onboard LED and to disable both
   infrastructure Wi-Fi and cellular data for the bounded offline test.

If any prerequisite is unavailable, continue independent admitted work and
mark only the affected rows `NOT_EXECUTED` with the exact missing prerequisite.

## Clean candidate preparation

Run the documented host build/CTest suite, WTP validator, Bluefy release and web
tests, focused supported sanitizers and all affected target linkchecks. Build
the standard RF-inhibited image only from clean committed HEAD with the retained
pinned dependencies and the already ignored Candidate A device-bound network
configuration. Record flash/RAM use and retained symbols. Hash the UF2. A build
or link is not phone, radio, target-runtime or RF evidence.

Re-identify both connected boards by serial. Flash and verify Candidate A only.
Re-establish full device ID, station MAC, build revision, boot ID, inhibited
engine, output inactive, empty/unowned state, preserved profile/station/schedule/
watermark/access state and healthy journals. Do not proceed from a disconnect,
reboot or missing acknowledgement alone.

## Joint phone sequence

Preserve every attempt and timing; do not replace a failed first attempt with a
later pass.

1. **Client identity and release.** Record the exact iPhone/iOS/Bluefy facts and
   the page's visible release identifier. Verify that its manifest and visible
   release match the checked-in deterministic release. Reject the wrong origin,
   release, device ID or certificate warning.
2. **Online load and offline reuse.** Load and verify the accepted page online.
   Confirm the page reports its offline cache ready. Disable infrastructure
   Wi-Fi and cellular data, close/suspend as required by the accepted procedure,
   reopen the same page in Bluefy and demonstrate that the exact release remains
   usable without network delivery. Re-enable only what the next admitted step
   requires. A checked-in service worker alone is not acceptance.
3. **Exact-device BLE connection.** Open one confirmed 120-second enrollment
   window only when a new pairing is required. Select Candidate A, verify the
   full device ID, observe Just Works behavior and distinguish new pairing from
   retained-bond admission. Wrong password, cancellation and disconnect must
   leave no provisional authority. A retained bond is ordinary authority but
   not fresh-password proof.
4. **Fresh password.** Enter the current local-access password into the page and
   prove that the target actually validates it as a fresh, one-use proof bound
   to the exact staged profile, apply request and current generation—even when
   the connection uses a retained bond. While the public default is active, use
   `ACCESS CONFIRM PROFILE <full-device-id>` on Candidate A's USB console within
   the same 30-second provisioning session. A mismatch, timeout, cancel or
   disconnect must invalidate the proof and staged session.
5. **Phone time and indicator.** Submit authenticated phone time, retain the
   challenge-to-submit interval, and verify source, age, uncertainty and the
   unchanged 500 ms admission bound. Observe the five-cycle Identify pattern
   and the actual-ready SoftAP heartbeat separately, including priority and
   termination. Do not infer LED timing from source tests alone.
6. **BLE local control.** Through the unchanged WTP/1 BLE stream perform only
   `HELLO`, `CAPS`, `STATUS`, `CLAIM`, `RENEW`, `RELEASE` and terminal/status
   observation needed for acceptance. Do not send `LOAD` or `ARM`. Verify the
   exact device/boot/session/principal and one-`JobService` ownership semantics.
7. **Credential transfer and activation.** Only if the fresh-password and any
   public-default USB/physical-confirmation requirements are genuinely met,
   enter the complete replacement profile on the phone, transfer it through the
   production BLE provisioning service, validate it, commit one new generation
   and allow the delivery-safe activator to run once after the terminal response
   or bounded timeout. Never place secret values in evidence. If the current
   page does not complete the required fresh step-up, stop this row rather than
   weakening the contract.
8. **New runtime.** After the required reboot, prove the new generation alone is
   selected; station association, DHCP, certified mDNS and new server/client
   trust work; superseded station/TLS authority does not return; and station,
   schedules and watermark have their intended preserved values.
9. **SoftAP and station withdrawal.** Request/join the SoftAP from the phone and
   verify manual Safari navigation, exact certificate identity, wrong/correct
   password behavior, cookie attributes, local status and logout. Maintain a
   usable station connection continuously for at least 30 seconds with no live
   token, reply, join grace or other AP cause, then prove the AP withdraws in a
   bounded scan. A still-unavailable station is a missing prerequisite, not an
   AP-withdrawal failure.
10. **Recovery/reset.** Execute only reset or recovery operations exposed by a
    reviewed production surface with selected unambiguous gestures and an armed
    restoration plan. Do not use ad hoc flash erasure or substitute USB commands
    for a missing product gesture. Preserve profile/station/schedules/watermark
    according to the selected reset level and prove all journals, bonds and
    access epochs. Otherwise record these rows as source/product gaps.

## Bounded negative, resource and restoration checks

Exercise wrong device, wrong password, offline wrong release, malformed/oversize
commands, disconnect/cancel, replay, competing BLE connection, four SoftAP
sessions plus rejected fifth, controller-time replay/over-budget cases and
resource reclamation only where they do not expose credentials or create RF
work. Record heap, largest free block where supported, stack guard, lwIP/BTstack
pools, TLS allocations, session counts, journal health and final return to
baseline. A fault harness must be separately identified and may qualify only its
named branch.

Log out and disconnect Bluefy, remove temporary controller profiles, disconnect
the isolated interface and clear volatile SoftAP causes. End with the exact
standard RF-inhibited image, authoritative inactive output, empty/unowned state,
provisioning closed, intended station/trust state, healthy journals and SoftAP
stopped unless an explicitly recorded unavailable-station fallback still
applies. Record any such limitation; do not disable a valid fallback merely to
make a restoration row pass.

## Adversarial review and publication

Review source, tests and evidence as an attacker and failure analyst. Check
device/client/release misidentification, retained-bond claims presented as fresh
password proof, offline-cache substitution, principal crossover, replay,
session fixation, provisional-bond persistence, profile/source rollback,
superseded trust, response-before-activation ordering, callback generation,
secret retention, reset ambiguity, SoftAP cause withdrawal, controller-time
uncertainty, LED overclaiming, resource exhaustion, output inference and
cleanup/restoration.

Repair every actionable finding within the selected contract and rerun affected
checks. If firmware or Bluefy source changes, commit a new candidate, rebuild,
rehash, reflash and repeat every affected physical row. Perform a fresh second
adversarial assessment. Do not call Phase 12 closed while a mandatory production
surface, source gap or Stage A row remains unexecuted or failed.

Update the Phase 12 plan, physical and production reviews and credential-free
machine-readable result to the exact observed boundary. Run formatting, JSON,
link, `git diff --check`, private-material scans and a final complete diff
review. Commit only attributable changes, push `devel`, independently verify
HEAD/upstream/remote parity, and report exact implementation, phone and target
evidence, failures, adversarial findings/repairs, restoration, commit and the
remaining gates. Stage B remains separate and requires new explicit RF
authority.
