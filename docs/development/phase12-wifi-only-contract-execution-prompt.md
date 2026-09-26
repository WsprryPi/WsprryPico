# Phase 12 Wi-Fi-only bootstrap contract: execution prompt

Status: **EXECUTED FOR DESIGN AND HOST FEASIBILITY ONLY; IMPLEMENTATION GATE OPEN**.

Work on `devel` in `/Users/lbussy/GitHub/WsprryPico`. Read `README.md`,
`CONTRACT.md`, `docs/architecture.md`, the Phase 12 roadmap, the current
field-access contract, the Wi-Fi-only proposal and review, and the latest
generic first-run physical record. Preserve unrelated work. This prompt is
the bounded continuation after the true full-erase, read-only, passwordless
SoftAP result. It does not approve credential-accepting firmware by itself.

## Product intent and boundaries

Deliver a first-run, Wi-Fi-only path for an exactly unprovisioned generic Pico
2 W. The user joins its open SoftAP without a password. iOS may open the local
captive page; Safari at `http://192.168.4.1/` remains the fallback. The user
chooses Connect, confirms the identified device with one runtime BOOTSEL tap,
enters ordinary station Wi-Fi credentials, and sees **Network connected** only
after durable network-only generation and observed association plus DHCP.
No setup code, BLE, Bluefy, native app, certificate installation, USB command,
owner claim, station listener, job control or RF authority is part of this
slice. Encrypt the submitted SSID and password with fresh browser/Pico keys to
limit passive disclosure on the open AP; explicitly accept active page
replacement/relay as the operator chose.

## Execute the current contract gate

1. Inspect current source, storage, RF worker, flash coordination, AP DNS/HTTP,
   network activation and tests. Verify the selected source and current target
   evidence rather than inferring them from an older image.
2. Specify the one-slot start, physical grant, encrypted submit, status and
   acknowledgement state machine. Freeze exact JSON fields, binary transcript,
   KDF/AEAD parameters, input bounds and synthetic known-answer vectors in a
   versioned **proposed** wire document. Include duplicate, expiry, wrong-
   device, wrong-boot, wrong-slot, bad-tag, interruption and response-loss
   outcomes. Keep actual passwords out of logs and public status.
3. Select a locally bundled, licensed pure-JavaScript candidate for X25519,
   SHA-256/HKDF and ChaCha20-Poly1305. Record source provenance, version and
   build method before vendoring in an implementation slice. Do not rely on
   `crypto.subtle` on HTTP. Check random and crypto feature detection in the
   chosen iPhone captive sheet and Safari before showing a password form;
   until then, the browser result is an open target gate.
4. Audit runtime BOOTSEL sampling against flash/XIP, interrupts, core 1,
   flash journal writes and CYW43 scheduling. Identify a fail-closed candidate
   using SDK flash-safe coordination and RAM-resident sampling. Do not copy the
   stock single-core polling example into production. Measure on the exact
   RF-inhibited Pico before enabling it; refuse a tap if coordination fails.
5. Set network-only storage/source semantics: a first durable network record
   is generation 1 from a truly blank generation 0; a later full profile would
   be generation 2 if it upgrades that device. Full commissioning directly
   from blank may still yield generation 1. Avoid claiming the old P12.10
   generation-1 result for a Wi-Fi-first path. Keep tombstones, access journal,
   legacy configuration, scheduler and output gates fail closed.
6. Review the resulting contract adversarially. Fix actionable design gaps,
   rerun checks affected by each change and perform a second independent
   assessment. Commit and push the bounded design/feasibility artifacts on
   `devel`; record actual repository parity and remaining gates.

## Approval and implementation sequence

Present the complete exception to the operator for P12.7 approval. Before
that approval, do not add a credential form, mutating captive endpoint,
BOOTSEL grant, network-only journal writer or target network-join behavior.
After approval, implement the specified protocol and storage transition with
deterministic host failure tests, build the exact RF-inhibited Pico image, then
obtain separate target authority for flash, BOOTSEL, AP/STA use, credentials,
duration and restoration. On the target prove physical grant, encrypted form
in the selected iPhone captive sheet or Safari, durable generation readback,
reboot selection, failure/retry, AP withdrawal/fallback and inactive RF.
An isolated Pi can exercise the AP protocol and network path but does not
substitute for the iPhone browser result. Stage B RF coexistence and the
paused owner/Bluefy/native-app work remain separate.
