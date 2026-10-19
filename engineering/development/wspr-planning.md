# Wspr planning

## Delivered automatic behavior and bounds

| Stored station input | Selected complete plan |
| --- | --- |
| Ordinary encodable call + four-character locator | Identical existing Type 1 |
| Ordinary call + six-character locator | Type 1 with first four on air; all six retained |
| Supported compound + four-character locator | Type 2 single; no locator in that frame |
| Supported compound + six-character locator | Type 2 then Type 3, requested full identity/power |
| Explicit `<CALL>` + six-character locator | Type 3 single; hash excludes brackets |
| Explicit Type 3 + four characters or unsupported syntax | Explicit refusal before transmitter claim/reservation |

The stored token remains 3–12 ASCII characters, including explicit brackets.
Supported compound prefixes are 1–3 alphanumerics before a valid Type 1 base;
suffixes are one alphanumeric or two decimal digits after a valid base. A
prefix may itself be a base call (`W1A/AA0NT`). Maximum supported compound is ten
characters, or twelve with brackets. Empty/nested/malformed brackets, NUL,
non-ASCII, whitespace, unsupported multiple slashes, impossible base calls and
oversized affixes refuse without truncation/substitution. Existing broadly valid
legacy slash identities remain readable; unchanged identity bytes survive
unrelated complete settings saves even if transmission planning refuses them.

Locators require A–R, two digits, and optional A–X subsquare. Exact reported
powers remain 0, 3, 7, 10, 13, 17, 20, 23, 27, 30, 33, 37, 40, 43, 47, 50,
53, 57, 60 dBm. Power is message content, independent of RF drive/output.
Only automatic planning is exposed; no ignored preference selector or Type 1/3
pair was added. Host-produced finite WTP jobs remain independently supported.

`/00`–`/09` are supported, matching Pi's ambiguity policy. They share Type 2
bits with `/Q`–`/Z`; `/09` and `/Z` are the same Type 2 payload. The saved call
is unchanged, and paired Type 3 hashes the requested full call. Plan metadata
and UI disclose the alternate spelling/receiver ambiguity. No general receiver
collision/full-call resolution guarantee is claimed.

## Frozen pair and authority contract

A bounded portable plan owns at most two fixed 162-symbol arrays. The existing
JobService receives two separate complete 162-event, 110.592-second jobs in
adjacent even-minute UTC +1-second windows. Both arrays, identity/power and the
original Pico RF base frequency are frozen; there is no second policy decision,
Pi dial offset, per-symbol network dependency or second scheduler.

Nominal start separation is 120 seconds, RF-off gap 9.408 seconds and overall
span 230.592 seconds. Each frame retains its independent local UTC/holdover
launch guard and accepted launch second. Complete-pair expiry preflight includes
the entire final launch second and rejects monotonic/UTC overflow before claim.
These are software timing contracts, not measured physical launch results.

Before first LOAD/ARM, the existing durable watermark reserves through the
second slot's start. All intersecting configured occurrences through that slot
are conservatively consumed. A single 60-second owner lease, renewed every
30 seconds, spans both frames/gap. Configuration writes are busy while owned.
Continuation is volatile: reboot, rollback, STOP, changed generation, loss of
clock quality/ownership, missed preparation, journal/engine/allocation failure
or restart inhibition cannot replay a first half or resume a stray second half.
Failed cutoff retains failed/output-unknown authority for explicit recovery.
No catch-up or automatic retry is introduced. Existing core/RF/frequency/pin/
output-inhibit guards and the 32 KiB authority reserve remain.

A single 324-symbol timeline was rejected because the engine guards only its
initial launch; separate jobs permit the required second-window time check.

## API, station persistence and commissioning

Frozen application/1 and station/1 shapes and `wspr_type1` literal remain.
Existing release-Pi Type 1 workflows work. A selected encodable Type 2/3 station
or bracket form returns explicit `409 unsupported_station_encoding` on those
legacy projections. Unknown new support refuses rather than falling back.

The exact additive `application_resources_v2` descriptor advertises:

| Method | Path | Meaning |
| --- | --- | --- |
| GET | `/api/v1/application/2` | `transmitter-application/2`, station/2, `wspr_type123_auto`, plan |
| GET/PUT | `/api/v1/station/2` | Complete versioned station resource |
| PUT | `/api/v1/config/2` | Config v1 content with explicit new-format admission |
| POST | `/api/v1/config/update/2` | Existing config-update/1 envelope/omission semantics |
| POST | `/api/v1/wspr-plan` | Authenticated, bounded, pure authoritative preview |

The descriptor retains `/api/v1/hardware` and authenticated carrier policy.
`wspr-plan/1` contains supported state, known frame types/count, 120-second slot
separation, bounded rationale and explicit ambiguity/alternate call. Old full
config paths may preserve an unchanged new identity during unrelated edits but
cannot introduce a changed new format. ETags, target/boot binding, idle/storage
checks, password-null preservation, flags, pins, schedules and watermark remain.
`engineering/protocol/transmitter-application-2.schema.json` validates actual responses;
legacy schemas are untouched. WTP/1, management/1 and /2, Consumer-Radio/1 and
Consumer-Recovery/1 are unchanged.

Profile-owned station writes remain transactional setup, not ordinary resource
mutation. Existing owner wire/plaintext broad decoding remains readable; the
actual PicoBootstrapServer validates planning before trial/commit. The pure
`/api/owner/v1/wspr-support` descriptor exposes known support through existing
public AP GET or authenticated setup policy. Unknown/old firmware refuses new
setup syntax with an editable preserved draft. Sent-once receipts,
generation/readback/review, full-capacity recovery and healthy-peer continuity
remain. A status refresh/login never establishes an interrupted save's result.

## Source provenance and independent receiver observations

Packing/hash arithmetic is a bounded adaptation of MIT WSPR-Reference at Pi
`a2437d1`, principally `src/WSPR-Reference/src/wspr/wspr_ref_encoder.cpp`.
Attribution/license are retained in `src/encoding/WsprryPi-LICENSE.md` and
THIRD_PARTY_NOTICES. No desktop reference/decoder, JSON library or Linux hardware
code is linked into firmware. Existing Type 1 channel goldens remain identical;
six fixed Pi Type 2/3 vectors compare every symbol.

The independent oracle is official WSJT-X
`967c85a6119110788b0df3782cf796485b2cee14`, eight `lib/wsprd` source/header files.
Exact SHA-256s, 21 payload/symbol/receiver observations and 33 hash tails are in
`tests/wspr_oracle_vectors.json`. GPL implementation stays in temporary
validation storage; only numeric outputs/provenance are committed. Test-only
instrumentation prints the existing unpk result and supplies its byte parity
table; packing/decoding arithmetic is unchanged. Hash seed is 146 with explicit
15-bit reduction. The upstream empty-input early return is recorded both raw
and reduced; empty input is not a valid station. Tests cover all tail lengths,
unaligned/exact-length views and repeated alternating long/short inputs.

Cold Type 3 observes `<...>`; prior ordinary compound Type 2 resolves the recorded
PJ4 and W1A examples in that independent decoder. `/Z` and `/09` remain an
intrinsic Type 2 ambiguity and have distinct requested-full-call Type 3 hashes.
Pi's own unpacker retains alternates, while its correlator can clear ambiguity
after a base-call-hash pairing. The real compound paired test deliberately
observes different base/full-call hashes. Those reference observations do not
prove general receiver correlation or RF decoding.

Unchanged Pi's one-character prefix encoding (`W/AA0NT`) differs from WSJT-X:
its prefix branch shifts once, leaving space/W/NUL; correct packing needs two
leading spaces. Pico pads by exact prefix length and matches the independent
vector. This reference discrepancy is retained in `pi-one-prefix-rereview.log`;
no WSPR-Reference repair was made. Its reviewed unchecked copies, invalid-input
substitution and aligned-hash hazards were avoided; they are source observations,
not newly claimed runtime reproductions.
