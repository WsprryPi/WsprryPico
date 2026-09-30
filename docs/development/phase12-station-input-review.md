# Phase 12 station input review (2026-09-30)

Status: **SOURCE / HOST CHECKED; INHIBITED B DEPLOYED; PHONE SAVE OF NEW FORMATS OPEN**.

## Requested behavior

Accept four- or six-character Maidenhead locators and save extended callsigns
in full. The existing saved-value prefill acceptance remains scoped to the
operator's AA0NT / EM18 / 20 dBm phone check. This change does not promote that
observation into a six-character or extended-callsign physical save result.

## Implementation

- Callsigns: 3–12 uppercase letters/digits with nonempty slash-separated
  segments and at least one letter and digit. Examples include `AA0NT/P`,
  `PJ4/AA0NT`, `PJ4/AA0NT/P` and a seven-character ordinary callsign.
- Locators: `[A-R]{2}[0-9]{2}([A-X]{2})?`. Only lengths four and six are
  accepted; invalid fields/subsquares, lowercase wire values, punctuation and
  incomplete locators are rejected. The form normalizes typed letters.
- Both forms, encrypted claim builders/decoders, HTTP admission, Pico AEAD,
  consumer/standalone storage and public prefill preserve the complete values.
  The bounded plaintext capacity is 117 bytes; all admission and decryption
  buffers use the shared capacity. Existing four-character envelopes and
  station profiles retain compatibility.
- Station validation is independent of Type 1 transmission encodability.
  Standard callsigns with a six-character locator encode the same Type 1
  symbols as its four-character square. An unencodable callsign reports
  `UNSUPPORTED_MODE` before transmitter claim or watermark reservation, and
  is never silently reduced to a base call. Type 2/3 transmission is not added.
  The [ARRL WSPR specification](https://www.arrl.org/wspr) describes the
  standard message's four-character locator.

## Checks and adversarial assessment

**10/10 affected host groups** and **4/4 setup browser groups** pass. Checks
cover old/new plaintexts, maximum-length HTTP and real Noble-to-PSA envelopes,
bad lengths/characters/slash segments, six-character journal/reboot readback,
extended consumer updates, network-only replacement preservation, fresh-page
and privacy-refresh prefill, draft protection and unchanged Type 1 golden
symbols. Unsupported-call scheduling leaves engine, owner, flash and watermark
untouched. The four-owner/four-client storage budget includes maximum-length
station values.

Adversarial review found the remaining Pico ciphertext cap, old standalone
documentation and the JavaScript end-anchor newline case; each was repaired.
The new scheduler rejection is checked before claim/reservation. Reassessment
found no remaining actionable issue in this slice.

The full local host build encountered pre-existing signed-comparison warnings
treated as errors. The shared Wi-Fi decoder's offset arithmetic was changed
to `std::size_t` and its real crypto regression passes. The unrelated
`network_adapter_tests.cpp:95` warning remains outside this slice; no full-suite
pass is claimed. Earlier preparatory attempts also used an incomplete SDK,
the wrong BTstack revision and a stale SDK-path build cache. A fresh target
directory with the retained complete, clean SDK and BTstack pins resolves those
inputs; the repository Xcode environment resolves the host-tool SDK mismatch.

The inhibited Pico 2 W target builds with SDK 2.3.1 / Arm GNU 15.3.1 and GP14
runtime enabled. Linked stack, allocator and BOOTSEL topology checks pass;
shutdown interception passes. A clean exact-commit deployment packet follows
the source commit. No station Save, RF job, erase, A operation or wspr4 access
is included in this update.

## Clean image and B deployment

The clean committed source is
`615888e5364be169839ae879d6bb955c84518bab`, firmware `615888e5364b`.
The standard RF-inhibited Pico 2 W image uses SDK 2.3.1, Arm GNU 15.3.1,
150 MHz system clock and opt-in GP14 runtime. Diagnostic, robustness, flash
probe and BOOTSEL capture options are off. The clean build passes linked
stack, allocator, BOOTSEL topology, shutdown interception, flash reservation
and UF2 payload checks. The SDK timestamp refresh in the managed source
worktree required a filesystem permission retry; that retry completed.

Retained UF2: **3,368,448 bytes**, SHA-256
`81361b105def84231c23853507bad81f992426260b9c935061fab82081d5239f`.
B serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`, loaded and verified this image from
`8d0ad7273707`. A fresh 4,194,304-byte flash backup has SHA-256
`f4453feb106c80fb289fa26b04509f9f746a4b5d6807cfc32d03c7f33088f969`;
all **57,344 reserved bytes** were identical before and after loading.

Preflight observed a newer generation-5 record, **AA1NT / EM18 / 20 dBm**,
request digest
`1f8238e07c7413cbf3ac3df8c360f333b2a5b3498b1f7ab7713f52fc792546fe`.
The earlier generation-4 expectation stopped before any deployment action;
the deployment then bound to the actual generation-5 record. No inference is
made about the phone terminal result of that intervening save. New boot
`d6f6015528fef0239c373633a4099576` retains the entire saved-profile readback,
access generation 1, zero owners and unchanged independent standalone state.

Preflight time was unsynchronized; after deployment B rejoined
`192.168.1.53`, synchronized time and passed exact-device plain LAN
`HELLO`/`STATUS`. It remained empty/unowned with inactive output, healthy
storage, valid stack guards and zero allocator failures. This fresh-boot
result does not establish the cause or repair of the earlier AP/time issue.

The four firmware artifacts, manifest, fresh backup, USB/LAN readbacks and
verified `8d0ad7273707` restore image remain private under ignored
`build/phase12-station-input-b-615888e/` and its matching wspr5 directory.
The managed clean source worktree was archived after artifact retention.
No station Save was performed during this packet. Saving the new formats
on the actual phone remains open; P12.8/P12.10 and Phase 12 remain open.
