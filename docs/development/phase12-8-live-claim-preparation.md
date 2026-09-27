# P12.8 live claim preparation and adversarial review

Status: **CANDIDATE A FLASH AND READ-ONLY AP CHECK PASSED; PHYSICAL CLAIM AND
PHONE ACCEPTANCE OPEN** (2026-09-27). This is a continuation of
the approved [P12.7 Safari/SoftAP contract](phase12-7-decision.md), not P12.8
closure or a consumer release.

## Prepared slice

The RF-inhibited standard image now links the previously separate
[Owner-HTTP/1](../protocol/Owner-HTTP-v1.md) claim parser, physical claim slot,
X25519/ChaCha20-Poly1305 opener, checked station and SNTP trial, generated
per-device CA/server material, and single source-5 journal commit. Healthy
virgin blank, reset tombstone and same-device network-only profiles are the
only admitted sources. A healthy network-only generation 1 would advance to
consumer generation 2; a virgin blank generation 0 would advance to generation
1. A physically granted direct-blank claim initializes the internal access
journal before attempting station association so its next boot is not
misclassified as access recovery.

The AP-local page at `/owner.html` generates a P-256 owner key in Safari site
storage, reads it back and self-tests it before starting the claim. It binds
the full device, boot, source, generation, owner point, browser point and
nonce, prompts one ordinary BOOTSEL press/release, encrypts the Wi-Fi/station
submission, and reconciles an unknown submit result through read-only status.
The first Wi-Fi-only page links to it, and a healthy network-only AP serves it
as its root page. A saved source-5 profile is shown as **saved, with final owner
readback pending**. The page never shows “Setup complete” in this slice.

The submit reply leaves the AP TCP connection before the station trial begins.
After a verified commit or ambiguous write result, the server schedules a
normal restart after a delivered status response, or after a bounded 60-second
fallback. The boot-selected source-5 profile remains structurally admitted for
station time and public status only. Legacy USB, GATT and console mutation
authority is denied while a claim is pending and whenever source 5 is selected.

## Build and deterministic evidence

- Branch: `devel`; base commit before this preparation: `35415c3f8dba`.
  Source history and target acceptance are recorded separately.
- Candidate UF2: `build/pico2-w-claim-20260927/firmware/WsprryPico.uf2`;
  SHA-256 `c7187c9b828a23260334657beeae61c30aa474d4d9c32cad550c9ab44d5a0dcb`.
  The target link reports SRAM BOOTSEL callbacks and no linked core-1
  launcher/reader. This is a build/topology check, not a physical safe-sampler
  acceptance for the new route.
- `npm run build` and `npm test` under `src/network/bootstrap_web`: four
  browser/crypto tests pass, including owner-key storage, claim binding,
  encrypted submit, lost-reply reconciliation and no premature success.
- `bootstrap_http_tests`, `owner_claim_http_tests` and
  `consumer_claim_commit_tests` pass in `build/host-debug`.
  `owner_signature_tests` passes in `build/phase12-captive-host`.
- The standard `WsprryPico` Pico 2 W target cross-build passes with the
  project-pinned SDK/toolchain. The source/build review preceded the separate
  authorized Candidate A flash below.

## Adversarial findings and repairs

| Finding | Repair and reassessment |
| --- | --- |
| A direct blank claim could write source 5 while the access journal remained erased; the next boot would enter access recovery and skip station. | Initialize the default internal access record on the granted gesture, with failure cancelling the slot. Rebuilt the target and retained the direct-blank path as a separate target gate. |
| Restart timing used a pre-generation monotonic sample and could underflow after slow TLS generation; an ambiguous journal result could remain stuck in reconcile. | Use a fresh monotonic sample with an ordered subtraction and schedule restart for both verified and ambiguous writes. |
| Switching station inside the AP receive callback could disturb the response and reenter network handling. | Defer the switch to the main poll after reply acknowledgement, with a ten-second lost-reply fallback. |
| The locally bundled owner script exceeded the C++ literal size supported by the host compiler. | Split the pinned P-256 implementation and claim flow into two local static assets; both are below 64 KiB and the host/target builds pass. |
| A browser could mistake a reconcile state or later fault for durable success. | Keep it on the checking screen during reconcile, show saved only for source 5, and move to service on a fault. Browser flow tests pass again. |
| An invalid or torn consumer profile could expose an AP without the read-only recovery page, or public status could label the structurally invalid record healthy. | Admit the fault source to the read-only blank recovery surface and report `fault` with no owner authority. The owner claim gate remains closed. |
| A transient captive AP drop during AP/STA channel transition could cancel a consumed claim before its station trial resolved. | Preserve the Trial state across listener loss. The existing trial deadline and explicit station failure still cancel it; a new claim cannot start while it is pending. |

The second adversarial assessment checked the corrected fault and trial paths,
claim/legacy slot exclusivity, source-5 legacy authority shutdown, browser
unknown-result display, and reply-before-switch/restart ordering. No further
actionable source defect was found. AP/STA continuity and trial timing on the
Pico remain target gates; this assessment is a source review, not device
acceptance.

## Candidate A flash and read-only AP check

The operator authorized preflight and flashing this exact RF-inhibited UF2 on
Candidate A, leaving it installed. On `wspr5` boot
`ffe09284-0e6b-41ee-9fe7-092867f72107`, USB serial
`0BF4B4AEC9FFB344` identified the Pico 2 W / RP2350. Before writing, the
correct USB command console (`if00`) returned full device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`, revision `3f56f5e1aaa9`, healthy
network-only generation 1, healthy access generation 1, no recovery or
provisioning fault, and `STATUS` Empty with inactive output and the
`inhibited-standalone-simulator` engine. The open AP independently returned
that same device ID and network-only generation 1. A first console attempt on
the WTP CDC interface (`if02`) received no reply; switching to `if00` resolved
it without a device reset or write.

The UF2 hash matched the candidate value on `wspr5`. The Pico acknowledged a
USB software `BOOTSEL` command, then enumerated as bootrom with the exact USB
serial. Serial-targeted `picotool load -v -x` finished verification with `OK`
and rebooted the new image. An earlier malformed `picotool -f` invocation was
rejected by its argument parser before any flash write. The newer image was
left installed; no restoration or erase occurred. The firmware reports build
revision `35415c3f8dba-dirty` because it was built before the source commit;
the verified UF2 SHA-256 above identifies the flashed artifact.

Postflash USB `INFO` reported the same full device ID, healthy network-only
generation 1, healthy access generation 1, 150 MHz system clock, valid core-0
stack guard, fault stage/status zero and provisioning fault zero. `STATUS`
reported new boot ID `b195eb9d1da741db1c4af6b5911237e5`, Empty,
`output_active=false`, healthy storage and the inhibited engine. From isolated
`wspr5` `wlan2`, `/api/owner/v1/public-status` returned HTTP 200, source
`network_only`, profile source 4, generation `"1"`, no owner and
`claim_available=true`; `/owner.html` and both local owner script assets
returned HTTP 200. `wlan2` was disconnected and its temporary profile deleted;
`eth0` and `wlan1` remained connected. No button press, credential submission,
consumer journal write, phone or RF output occurred.

## Next physical gate and limits

When the operator returns to Candidate A, obtain action-specific authority
for the physical claim. Use the open AP and Safari page, request one untimed
press/release when the page prompts it, submit settings without copying the
Wi-Fi password into evidence, and compare full identity, request digest,
source and expected generation 2 before and after the scheduled reboot.
Preserve any failure as evidence; the read-only AP check does not qualify the
physical claim or iPhone flow.

P12.8 still needs post-clock cryptographic validation and activation of the
same persisted source-5 generation, authenticated encrypted owner sessions,
private readback and bounded station-client enrollment. Target TLS generation
latency, watchdog margin, heap/stack, AP/STA continuity and iPhone storage
behavior are unmeasured for this candidate. P12.9–P12.12 and Phase 13 retain
their distinct acceptance gates. The current image must not be represented as
a complete consumer commissioning path.
