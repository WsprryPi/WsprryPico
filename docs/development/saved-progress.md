# Saved progress contract

`transmitter-progress/1` is an additive, non-runnable saved draft. Discover it
through `capabilities.saved_progress`; absence keeps the legacy complete-save
workflow. Config v1, config-update/1, station/application v1/v2, Consumer-Radio/1,
Consumer-Recovery/1 and WTP/1 retain their complete/atomic semantics.

## Fields and persistence

The ten closed units are `callsign`, `locator`, `power_dbm`, `enabled`,
`schedules`, `expires_utc_s`, `pins`, `frequency_policy`, `wifi`, `ntp_ipv4`.
Station components validate independently with the existing station grammar and
exact supported powers (including zero). Frequency permissions are one two-flag
unit. Schedules are one complete array, pin allocation one operational plan,
and Wi-Fi one complete credential pair. Their existing validators remain the
authority. Hostname has its separate P15.10 operation.

Omission preserves a field. `null` records explicit absence and masks the applied
fallback; it never invents a default. False, zero and an empty schedule array are
values. Empty schedule enablement still cannot pass complete configuration
validation. Known invalid units return `invalid` while accepted siblings commit
in one verified append. Unknown/duplicate members or an invalid outer envelope
reject the whole operation. Identical accepted saves consume a sequence; A/B/A
cannot revive a revision. All-invalid batches do not write.

The sparse fields are limited to 1,400 serialized bytes; the update body to
2,048 bytes; a journal record is 2,048 bytes. The new two-bank region is
`0x3f0000..0x3f2000` on the supported 4 MiB layout. The diagnostic scratch sector
at `0x3f2000`, access, bonds, profile, operational configuration/cursor and final
boot sector remain at their existing addresses. The firmware linker limit is
`0x3f0000`. No legacy record migration write occurs: erased progress means no
draft, and existing complete records retain their validators and addresses.

A torn record/failed verification latches unhealthy storage, closes admission
through the attached Store, and never resurrects an older draft or enabled
configuration. Provisioning and full resets erase both draft banks through the
existing durable reset intent/resume path. Access-only reset retains device
progress. Authorized recovery is required for corrupt media. Erase verifies by
reloading; physical erase/program behavior still needs board qualification.

Wi-Fi draft passwords are bounded ordinary flash secrets, with no encryption at
rest claim. Readback always emits `password:null`; a submitted null password
preserves the prior draft password first, otherwise the applied password only
when no draft Wi-Fi/tombstone exists. Clearing Wi-Fi explicitly masks that
fallback. Provisioning/full reset removes historical draft credential bytes.
No draft/password enters URL receipts, logs or persistent browser storage.
Firmware rollback can leave this new reserved data on flash; older firmware
must not be assumed to erase or understand it. Reset with supporting firmware
before rollback if retained credential drafts must be removed.

## Authenticated API

- `GET /api/v1/progress`: authoritative redacted resource and common ETag.
- `POST /api/v1/progress/update`: exactly `schema`, `target`, `request_id`,
  `fields`; requires the current `If-Match`.
- `POST /api/v1/progress/apply`: exactly `schema`, `target`, `application`, where
  application has decimal-string `draft_revision` and `domain` (`station`,
  `network`, `radio`, `all`). Requires nonzero saved revision/current ETag.

Target is the existing full member/device/boot tuple. Existing authenticated
carrier, Host/Origin/CSRF, idle, pending-transaction, storage and profile gates
apply. Dispatch classifies these as Configure; raw WTP and unauthenticated,
blank/preclock ordinary management gain no new route.

Readback has a closed key set: schema/target; decimal-string draft, config and
profile revisions; fields; last receipt SHA-256 and outcomes; applied station;
station tuple with individual nulls; station completeness; full completeness;
boolean `apply_domains` for station/network/radio/all; WSPR plan or null;
schedule enabled/suspended observations; and `matches_applied`. An update adds
exact per-request `outcomes` (`saved`, `cleared`, `invalid`) and `request_id`.
A receipt hashes the original exact envelope and attributes only the bounded
last accepted batch. Matching values/login/status alone cannot identify a lost
write. Readback is not an automatic replay or subset retry.

`complete` means the merged full candidate parses as Config; `station_complete`
means the tuple is syntactically valid. WSPR encodability is separately reported
by the existing planner. None establishes access, clock, frequency/pin readiness,
schedule admission, ownership, output state or permission to transmit.

Application reconstructs only the selected domain over applied settings, then
re-enters complete config/2 authority and validation. Thus valid radio/network
progress can apply while an unrelated station draft is incomplete, retaining
the previous complete station. New station/all candidates require all three
station fields. An explicit null in the selected domain blocks application.
Consumer-owned station/network application cannot bypass transactional setup.
Drafts remain saved after application and never feed the scheduler, Console,
old APIs, previews, login/reconnect or boot. Saving cannot claim/load/arm, resume
STOP, clear faults, advance the consumed-slot cursor or activate network/pins.
An enabled schedule retains the previous applied values and suspension state.

## Public commissioning

Only the existing admitted fixed-AP network-only/consumer commissioning window
can use `GET /api/owner/v1/progress` and POST `/progress/start`, `/progress/submit`.
These expose only station fields/outcomes; receipt and scheduler observations
are null. There is no public credential-draft write or ordinary management.
Start binds the existing one-use ephemeral claim slot to the common revision.
Progress plaintext is bounded JSON (512 bytes), sealed with the existing
X25519/HKDF/AEAD transcript but distinct info string
`WsprryPico saved progress AEAD v1`. Legacy claim ciphertext remains distinct.
A draft save consumes the slot, verifies durable readback and performs no
profile/network trial or access-journal initialization.

Explicit `/api/owner/v1/claim/progress/start` applies the saved station through
the existing full claim transaction. The decrypted station and common draft
revision must still match at submit and immediately before commit. Existing
station trial, profile generation, request digest, delivery and restart rules
remain authoritative. Authenticated consumer setup forwards this closed route
under its existing session authority. AP availability never grants LAN/raw
commissioning access.

## Browser state

“Save valid fields” reports each accepted/invalid unit near its control. Blank
numeric text clears a draft; zero remains zero. Invalid numeric values beyond
the signed JSON range are sent as invalid field text so valid siblings can
still save. Invalid/newer browser edits remain visible. Explicit read/review
keeps edits; confirmed discard/reload adopts device-saved progress. Page-local
serials keep late acknowledgements from overwriting or marking newer edits saved.

“Apply saved…” is a separate action using device-saved values, current target
and revision. Complete save/plan, applied configuration, active boot network/pins,
STOP and operation readiness remain distinct. A missing/malformed/future reply,
conflict, expiry or interrupted write enters readback/review and disables another
save until explicit reconciliation. No automatic retry, credential persistence,
message library or durable raw-job store is introduced.

P15.15 adds independently negotiated [GPIO drive configuration](gpio-drive.md). Legacy resource shapes and unavailable declarations retain their prior meanings.
